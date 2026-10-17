# Research & Technical Decisions: Incremento 3 TaskControl

**Feature**: `003-task-organization-priority` (Organización y priorización de tareas)  
**Date**: 2026-10-07  
**Status**: Completed  

---

## 1. Modelado y Gestión de Prioridad de Tareas (HU-07)

### Contexto y Requisitos
El requerimiento HU-07 exige que toda tarea tenga una prioridad asignada dentro de los niveles `'high'` (alta), `'medium'` (media) y `'low'` (baja), con un valor por defecto explícito. El listado de tareas debe permitir ordenamiento por prioridad descendente (alta $\rightarrow$ media $\rightarrow$ baja) sin perder los filtros por estado ya existentes.

### Decisión
1. **Representación en Base de Datos**:
   - Columna `priority` en tabla `tasks`: `String(20)`, con `nullable=False`, `default='medium'` y `server_default='medium'`.
   - Valores canónicos permitidos: `'high'`, `'medium'`, `'low'`.
   - Mapeo de ordenamiento numérico para consultas SQL:
     ```sql
     CASE priority
         WHEN 'high' THEN 3
         WHEN 'medium' THEN 2
         WHEN 'low' THEN 1
         ELSE 0
     END DESC, created_at DESC
     ```
   - En SQLAlchemy se utiliza `case({ 'high': 3, 'medium': 2, 'low': 1 }, value=Task.priority).desc()`.
2. **Índice de Optimización**:
   - `ix_tasks_user_id_priority` sobre `(user_id, priority)` para garantizar respuesta inferior a 100 ms al ordenar o filtrar por prioridad.
3. **Validación en Dominio (`TaskService`)**:
   - Constante de dominio: `ALLOWED_PRIORITIES = {'high', 'medium', 'low'}`.
   - Si se envía un valor no reconocido, se rechaza lanzando `InvalidPriorityError` (HTTP 400).
   - Se permite cambiar la prioridad en cualquier momento mediante método dedicado `set_task_priority(user_id, task_id, priority)` o en `update_task`, registrando el evento inmutable de auditoría `TASK_UPDATED` con metadatos `old_priority` y `new_priority`.

### Justificación frente al Principio V (Simplicidad)
- *Alternativas rechazadas*:
  - **Tabla relacional separada de prioridades (`priorities`)**: Introduciría joins innecesarios para solo 3 valores estáticos bien definidos, violando la simplicidad (YAGNI).
  - **Prioridad como entero libre (1 a 100)**: No aporta claridad semántica para el usuario final y complica los controles de interfaz.
- *Solución elegida*: Columna de texto con restricción de dominio y ordenamiento ponderado con `case()`. Máxima legibilidad y rendimiento óptimo.

---

## 2. Entidad `Category` y Desvinculación sin Cascada (HU-08)

### Contexto y Requisitos
El requerimiento HU-08 exige que los usuarios puedan crear categorías para agrupar tareas. Una tarea puede pertenecer a máximo una categoría o a ninguna. Regla innegociable de negocio: eliminar una categoría **nunca** debe eliminar en cascada sus tareas; las tareas deben desvincularse y quedar sin categoría (`category_id = NULL`). Asimismo, se debe admitir el renombrado de categorías y un tope de 50 categorías por usuario.

### Decisión
1. **Separación Estricta de Capas (Principio II)**:
   - Capa de Modelos: `Category` (`src/taskcontrol/models/category.py`).
   - Capa de Dominio: `CategoryService` (`src/taskcontrol/services/category_service.py`).
   - Capa HTTP: Blueprint `categories` (`src/taskcontrol/blueprints/categories.py`).
2. **Estructura de la Entidad `Category` y Validaciones**:
   - `id`: Entero, PK.
   - `user_id`: Entero, FK a `users.id` con `ON DELETE CASCADE`.
   - `name`: `String(50)`, `nullable=False`.
   - `created_at`: `DateTime(timezone=True)`.
   - Restricción única compuesta y normalización: comprobación en minúsculas (`case-insensitive`) tras trim por usuario.
   - Límite de capacidad: máximo 50 categorías creadas por usuario.
   - Renombrado seguro: `update_category` permite cambiar el nombre emitiendo `CATEGORY_UPDATED` (`old_name`, `new_name`) y preservando intactas las tareas asociadas.
3. **Clave Foránea en `Task` y Política de Eliminación**:
   - `category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)`.
   - A nivel DDL de base de datos relacional, la regla `ON DELETE SET NULL` delega en el motor relacional la desvinculación automática de tareas al eliminar la categoría.
   - En la capa de servicios, `CategoryService.delete_category(user_id, category_id)`:
     - Valida propiedad de la categoría.
     - Remueve la categoría y emite el evento de auditoría `CATEGORY_DELETED`.
     - SQLAlchemy y el motor de base de datos actualizan automáticamente las tareas asociadas a `category_id = NULL`.
     - Todas las tareas asociadas permanecen íntegras y activas.

### Justificación frente al Principio V (Simplicidad)
- Delegar la desvinculación en la cláusula nativa de integridad relacional `ON DELETE SET NULL` del motor SQL es el mecanismo estándar, más simple y robusto. Evita bucles manuales en código Python para actualizar cada tarea individualmente y previene condiciones de carrera o transacciones inconsistentes.

---

## 3. Cálculo de Vencimiento de Tareas Exclusivo en Backend (HU-09)

### Contexto y Requisitos
El requerimiento HU-09 exige indicar si una tarea está vencida cuando su fecha límite ha sido superada y no se encuentra completada. El cálculo debe realizarse **exclusivamente en el backend** para evitar inconsistencias por husos horarios del cliente (Principio III). Además, tareas completadas o eliminadas lógicamente nunca deben marcarse como vencidas.

### Decisión
1. **Atributo Calculado en el Servidor (Propiedad Derivada)**:
   - **No se persiste** como columna física en la base de datos relacional. Persistir un booleano `is_overdue` requeriría jobs periódicos nocturnos (cron/Celery) que violarían el Principio I (monolito sin procesos en segundo plano desacoplados) y provocarían desincronización de datos.
   - Se implementa como propiedad calculada `@property` en el modelo `Task` y en la serialización de servicios:
     ```python
     @property
     def is_overdue(self) -> bool:
         if self.is_deleted or self.status == 'completed' or self.due_date is None:
             return False
         return self.due_date < date.today()
     ```
2. **Evaluación de Fecha Determinista**:
   - Se compara la fecha de calendario `self.due_date` contra `datetime.now(timezone.utc).date()`.
   - Una tarea cuya `due_date` es el día de hoy **no** está vencida mientras transcurre el día; pasa a considerarse vencida en el backend al inicio del día calendario posterior.
3. **Exposición en Contrato HTTP (Principio III)**:
   - En las respuestas API/JSON, cada tarea incluye el campo booleano explícito `"is_overdue": true|false`.
   - En las plantillas Jinja2, se evalúa `task.is_overdue` para inyectar insignias visuales (badges de advertencia de vencimiento) en el renderizado del lado del servidor.

### Justificación frente al Principio V (Simplicidad)
- Una propiedad calculada en memoria durante la consulta tiene costo computacional prácticamente cero ($O(1)$) y garantiza precisión temporal absoluta sin requerir tareas programadas en segundo plano ni esquemas de almacenamiento redundantes.

---

## 4. Extensión de Consultas y Compatibilidad hacia Atrás (HU-02)

### Contexto y Requisitos
El endpoint existente `GET /tasks` debe admitir ordenamiento por prioridad y filtrado por categoría sin alterar su compatibilidad con clientes existentes ni romper los filtros de estado (`status = all|pending|in_progress|completed`).

### Decisión
1. **Parámetros de Consulta (Query String)**:
   - `status`: `'all' | 'pending' | 'in_progress' | 'completed'` (por defecto `'all'`).
   - `category`: `'all' | 'uncategorized' | <int>` (por defecto `'all'`; soporta alias retrocompatible `category_id` y valor `'none'`).
   - `sort`: `'created_at' | 'priority'` (por defecto `'created_at'`; soporta alias retrocompatible `sort_by` y valor `'created_desc'`).
2. **Composición Dinámica en `TaskService.get_user_tasks`**:
   - Base query: `Task.query.filter(Task.user_id == user_id, Task.is_deleted == False)`.
   - Filtro de estado: si `status != 'all'`, agrega `filter(Task.status == status)`.
   - Filtro de categoría:
     - Si `category in ('uncategorized', 'none')`: agrega `filter(Task.category_id.is_(None))`.
     - Si `category != 'all'`: si es ID numérico válido, agrega `filter(Task.category_id == category_id)`.
   - Ordenamiento:
     - Si `sort == 'priority'`: aplica `order_by(priority_case_weight.desc(), Task.created_at.desc())`.
     - Si `sort in ('created_at', 'created_desc')`: aplica `order_by(Task.created_at.desc())`.

---

## 5. Estrategia de Migraciones sobre Esquema Existente (Principio VI)

### Contexto y Requisitos
Se deben incorporar la nueva tabla `categories` y las columnas en `tasks` garantizando que los datos existentes de los Incrementos 1 y 2 no sufran corrupción ni pérdida.

### Decisión
1. Script de migración de Alembic: `xxxx_add_categories_and_task_priority.py`.
2. **Garantía de Compatibilidad**:
   - `tasks.priority`: se agrega con `server_default='medium'` y `default='medium'`. Todas las tareas preexistentes adquieren inmediatamente el valor `'medium'` de forma transparente.
   - `tasks.category_id`: se agrega como nullable sin valor por defecto, quedando en `NULL` para todas las tareas preexistentes.
   - Creación de tabla `categories` con clave foránea a `users.id` e índice único en `(user_id, name)`.
3. Ejecución directa mediante `flask db upgrade`.
