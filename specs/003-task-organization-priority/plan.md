# Implementation Plan: Organización y Priorización de Tareas (Incremento 3)

**Branch**: `003-task-organization-priority` | **Date**: 2026-10-07 | **Spec**: [spec.md](file:///C:/Users/Kreilt/Downloads/SDD-Tecnologias-Disruptivas-main/specs/003-task-organization-priority/spec.md)

**Input**: Especificación funcional desde `specs/003-task-organization-priority/spec.md` (cubre HU-07, HU-08 y HU-09 del backlog, construyendo sobre los modelos y blueprints de los Incrementos 1 y 2).

---

## Summary

Implementar el tercer incremento funcional de TaskControl (Organización y Priorización de Tareas) respetando estrictamente los 8 principios constitucionales del proyecto y consolidando la arquitectura monolítica en 4 capas ya establecida:
1. **Prioridad de tareas (HU-07)**: Incorporación del campo `priority` (`'high'`, `'medium'`, `'low'`) en el modelo `Task` con valor por defecto canónico `'medium'`, ordenamiento ponderado descendente por urgencia (`high` $\rightarrow$ `medium` $\rightarrow$ `low`) con desempate por fecha de creación descendente, y endpoint dedicado para actualización rápida de prioridad.
2. **Entidad y gestión de Categorías (HU-08)**: Nueva entidad `Category` vinculada al usuario (`user_id`), con validación de nombre obligatorio (1-50 caracteres) y restricción de unicidad por usuario. Implementación de relación opcional en `Task` (`category_id` nullable) configurada a nivel de base de datos relacional con `ON DELETE SET NULL`, garantizando que eliminar una categoría jamás elimine sus tareas en cascada sino que las desvincule de forma segura y transparente.
3. **Indicador de tareas vencidas calculado en backend (HU-09)**: Cálculo del indicador `is_overdue` resuelto exclusivamente en el servidor (en memoria como `@property` y en la capa de servicios), nunca persistido como columna física de base de datos para no requerir procesos asíncronos en segundo plano (Principio I y V). Exclusión estricta de tareas completadas (`status = 'completed'`) o eliminadas lógicamente (`is_deleted = True`) del cálculo de vencimiento.
4. **Extensión del listado de tareas (HU-02)**: Ampliación de `GET /tasks` para soportar ordenamiento por prioridad (`sort_by=priority`) y filtrado por categoría (`category_id=all|none|<id>`) en composición ortogonal, sin romper ni alterar los filtros de estado existentes.
5. **Migración versionada con integridad total (Principio VI)**: Script incremental con Flask-Migrate que utiliza `server_default='medium'`, garantizando que todas las tareas preexistentes de los Incrementos 1 y 2 permanezcan intactas y funcionales.
6. **Desarrollo Test-First (TDD) bloqueante (Principio IV)**: Pruebas automatizadas a nivel de modelo/servicio que certifican el ordenamiento por prioridad, la desvinculación sin cascada al borrar categorías y la imposibilidad de que una tarea completada o eliminada se catalogue como vencida.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flask 3.x, Flask-SQLAlchemy 3.x, Flask-Migrate (Alembic), Flask-WTF 1.2+ (`CSRFProtect`), python-dotenv 1.0+, Werkzeug 3.x, Jinja2  
**Storage**: Base de datos relacional gestionada vía SQLAlchemy ORM (SQLite local para desarrollo y pruebas; PostgreSQL compatible para producción)  
**Testing**: `pytest`, `pytest-cov` (ejecución de pruebas de servicios y dominio con base de datos SQLite en memoria `:memory:`)  
**Target Platform**: Servidor web monolítico ejecutable localmente en Windows y Linux  
**Project Type**: Aplicación web monolítica con renderizado en servidor Jinja2 y JavaScript vanilla auxiliar  
**Performance Goals**: Tiempo de respuesta menor a 100 ms para consultas de listado filtrado, ordenado y operaciones CRUD de categorías  
**Constraints**:
- Cumplimiento estricto e innegociable de los 8 principios constitucionales.
- Monolito estricto: cero microservicios, cero colas de mensajería asíncronas o workers en segundo plano (Principio I).
- Separación nítida de responsabilidades en 4 capas: Modelos, Servicios, Blueprints, Presentación (Principio II).
- Contratos de endpoints rigurosamente tipados con protección CSRF en todo POST (Principio III y VII).
- TDD obligatorio y bloqueante antes de escribir lógica de negocio (Principio IV).
- Simplicidad y YAGNI priorizados (Principio V): sin jobs nocturnos para recalcular vencimientos, sin tablas intermedias innecesarias para prioridades.
- Integridad referencial y migraciones reproducibles con Alembic (Principio VI): `ON DELETE SET NULL` nativo en base de datos.
- Seguridad por defecto (Principio VII): validación en backend, aislamiento estricto por usuario autenticado en categorías y tareas (`@login_required`).
- Observabilidad mínima viable (Principio VIII): eventos inmutables en `audit_logs` para cambios de prioridad y ciclo de vida de categorías.  
**Scale/Scope**: Incremento 3 focalizado exclusivamente en HU-07, HU-08 y HU-09. Quedan explícitamente fuera de alcance: asignación de tareas a otros usuarios (HU-10), notificaciones internas (HU-11), interactividad asíncrona sin recarga de página (HU-15) y reordenamiento manual drag-and-drop (HU-16).

---

## Constitution Check

*GATE: Evaluación técnica previa y posterior al diseño contra la constitución de TaskControl.*

| Principio | Estado | Justificación y Cumplimiento en el Plan |
|---|---|---|
| **I. Monolito por diseño** | **PASS** | El sistema continúa operando como un proceso web monolítico único con una única base de datos relacional. El cálculo de vencimiento se resuelve dinámicamente en tiempo de petición en memoria, descartando por completo cron jobs desacoplados, Celery o Redis. |
| **II. Separación en capas** | **PASS** | Organización estricta en 4 capas: `models/category.py` y `models/task.py` (persistencia); `services/category_service.py` y `services/task_service.py` (dominio y reglas de negocio puras sin contexto HTTP); `blueprints/categories.py` y `blueprints/tasks.py` (controladores HTTP); y `templates/` + `static/` (presentación). |
| **III. Contrato explícito backend-JS** | **PASS** | Contratos detallados en `contracts/category-contracts.md` y `contracts/task-organization-contracts.md`. Especifican rutas, métodos, payloads con CSRF, esquema JSON con propiedad calculada `is_overdue` y catálogo determinista de respuestas 2xx/4xx. |
| **IV. Test-first en lógica de negocio** | **PASS** | TDD mandatorio y bloqueante: se definen pruebas en rojo (`tests/unit/test_category_service.py` y `tests/unit/test_task_service.py`) antes de codificar la lógica de ordenamiento por prioridad, eliminación segura de categoría y reglas de exclusión de `is_overdue`. |
| **V. Simplicidad sobre generalidad prematura** | **PASS** | Filosofía YAGNI: (1) Prioridad como columna de texto con ponderación SQL `case()` en vez de crear tablas de catálogo relacional redundantes; (2) Desvinculación de categorías resuelta con la cláusula SQL estándar `ON DELETE SET NULL`; (3) Vencimiento calculado como `@property` en memoria ($O(1)$) sin esquemas de almacenamiento periódico. |
| **VI. Integridad de datos y migraciones** | **PASS** | Clave foránea nullable con política `ON DELETE SET NULL` a nivel DDL de base de datos. Script de migración con Flask-Migrate con `server_default='medium'`, asegurando que ninguna tarea existente de los Incrementos 1 y 2 sufra inconsistencias o pérdidas. |
| **VII. Seguridad por defecto** | **PASS** | Validación estricta en backend: nombre de categoría limpio y recortado, verificación de unicidad por usuario, validación de que un usuario no pueda asignar categorías de otros usuarios (prevención de IDOR), y protección CSRF obligatoria en todos los métodos POST. |
| **VIII. Observabilidad mínima viable** | **PASS** | Ampliación del log estructurado de auditoría en `audit_logs` con nuevos eventos inmutables: `TASK_PRIORITY_CHANGED`, `TASK_CATEGORY_ASSIGNED`, `CATEGORY_CREATED`, `CATEGORY_UPDATED` y `CATEGORY_DELETED`. |

---

## Project Structure

### Documentation (este incremento)

```text
specs/003-task-organization-priority/
├── spec.md                              # Especificación funcional validada (HU-07, HU-08, HU-09)
├── plan.md                              # Este plan técnico de implementación
├── research.md                          # Decisiones técnicas y justificaciones de arquitectura
├── data-model.md                        # Modelo relacional de Category y extensión de Task
├── quickstart.md                        # Guía de validación y escenarios extremo a extremo
├── checklists/
│   └── requirements.md                  # Checklist de verificación de requerimientos
└── contracts/                           # Contratos de interfaz HTTP explícitos (Principio III)
    ├── category-contracts.md            # Contratos de CRUD y asignación de categorías
    └── task-organization-contracts.md   # Contratos de prioridad, filtros combinados y vencimiento
```

### Source Code (Repositorio Monolítico)

```text
src/
└── taskcontrol/
    ├── __init__.py                      # Application Factory (registro de blueprints categories y tasks)
    ├── config.py                        # Configuración por entornos
    ├── extensions.py                    # Instancias de SQLAlchemy, Flask-Migrate y CSRFProtect
    │
    ├── models/                          # Capa 1: Persistencia relacional
    │   ├── __init__.py
    │   ├── user.py                      # Modelo User existente (id, email, password_hash)
    │   ├── category.py                  # NUEVO: Modelo Category (id, user_id, name, created_at, uq_user_name)
    │   ├── task.py                      # EXTENDIDO: Modelo Task (+priority, +category_id, @property is_overdue)
    │   ├── password_reset_token.py      # Modelo PasswordResetToken existente (Incremento 2)
    │   └── audit_log.py                 # Modelo AuditLog (soporte para nuevos eventos del Incremento 3)
    │
    ├── services/                        # Capa 2: Lógica de negocio y dominio (TDD bloqueante)
    │   ├── __init__.py
    │   ├── auth_service.py              # Servicio de autenticación
    │   ├── category_service.py          # NUEVO: CategoryService (crear, listar, eliminar con desvinculación)
    │   ├── task_service.py              # EXTENDIDO: get_user_tasks(sort_by, category_id), set_task_priority, assign_category
    │   ├── recovery_service.py          # Servicio de recuperación de claves
    │   ├── email_service.py             # Emulación de correos
    │   └── audit_service.py             # Auditoría estructurada JSON
    │
    ├── blueprints/                      # Capa 3: Controladores HTTP y protección CSRF
    │   ├── __init__.py
    │   ├── auth.py                      # Rutas de autenticación y reseteo
    │   ├── categories.py                # NUEVO: Blueprint /categories (GET /categories, POST /categories, POST /<id>/delete)
    │   ├── tasks.py                     # EXTENDIDO: POST /tasks/<id>/priority, POST /tasks/<id>/category, GET /tasks ampliado
    │   └── decorators.py                # Decorador @login_required
    │
    ├── templates/                       # Capa 4A: Presentación Jinja2 con CSRF
    │   ├── base.html                    # Layout base con enlace a Categorías en navbar y meta csrf-token
    │   ├── categories/
    │   │   └── index.html               # NUEVO: Vista de gestión de categorías y creación
    │   └── tasks/
    │       ├── index.html               # ACTUALIZADO: Controles de orden por prioridad, filtro por categoría y badges
    │       ├── new.html                 # ACTUALIZADO: Selectores de prioridad (default Media) y categoría opcional
    │       └── edit.html                # ACTUALIZADO: Selectores de prioridad y categoría
    │
    └── static/                          # Capa 4B: Recursos estáticos
        ├── css/styles.css               # Estilos para badges de prioridad (alta/media/baja) y badge de vencida
        └── js/main.js                   # JavaScript vanilla para peticiones fetch con X-CSRFToken

migrations/                              # Scripts versionados de Alembic / Flask-Migrate
├── versions/
│   ├── xxxx_initial_schema.py           # Incremento 1: users, tasks, audit_logs
│   ├── yyyy_add_soft_delete_and_reset.py# Incremento 2: is_deleted, deleted_at, password_reset_tokens
│   └── zzzz_add_categories_and_task_priority.py # NUEVO: tabla categories, columnas priority y category_id en tasks

tests/
├── conftest.py                          # Fixtures de aplicación, cliente y BD de prueba
├── unit/                                # Pruebas unitarias de dominio (TDD bloqueante)
│   ├── test_category_service.py         # NUEVO: Pruebas de unicidad, borrado seguro y desvinculación
│   ├── test_task_service.py             # EXTENDIDO: Pruebas de ordenamiento por prioridad y cálculo de is_overdue
│   ├── test_auth_service.py
│   ├── test_recovery_service.py
│   └── test_audit_service.py
└── integration/                         # Pruebas de integración HTTP y contratos
    ├── test_category_routes.py          # NUEVO: Pruebas de endpoints /categories con CSRF
    └── test_task_routes.py              # EXTENDIDO: Pruebas de filtros combinados, POST /priority y POST /category
```

**Structure Decision**: Se mantiene de forma irrestricta la arquitectura monolítica en un único proyecto (`src/taskcontrol/`) con capas bien diferenciadas, asegurando continuidad total con los Incrementos 1 y 2.

---

## Estrategia de Implementación Detallada por Capas

### 1. Extensión del Modelo `Task` (Punto 1 del Requerimiento)

El modelo de datos `Task` (`src/taskcontrol/models/task.py`) se amplía con las siguientes definiciones:

```python
from datetime import datetime, timezone, date
from src.taskcontrol.extensions import db

class Task(db.Model):
    __tablename__ = 'tasks'

    # Columnas existentes de Incrementos 1 y 2:
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, server_default='0', nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # NUEVAS COLUMNAS INCREMENTO 3:
    priority = db.Column(db.String(20), default='medium', server_default='medium', nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True, index=True)

    # RELACIÓN CON CATEGORY:
    category = db.relationship('Category', backref=db.backref('tasks', lazy='dynamic', passive_deletes=True))

    __table_args__ = (
        db.Index('ix_tasks_user_id_is_deleted', 'user_id', 'is_deleted'),
        db.Index('ix_tasks_user_id_priority', 'user_id', 'priority'),
    )

    # PROPIEDAD CALCULADA DE VENCIMIENTO (NO PERSISTIDA):
    @property
    def is_overdue(self) -> bool:
        if self.is_deleted or self.status == 'completed' or self.due_date is None:
            return False
        return self.due_date < datetime.now(timezone.utc).date()
```

- **Valor por defecto de prioridad**: Configurado tanto a nivel de aplicación (`default='medium'`) como a nivel de DDL relacional (`server_default='medium'`).
- **Valores canónicos admitidos**: `'high'`, `'medium'`, `'low'`.
- **Relación con Category**: Relación muchos-a-uno opcional (`category_id` nullable). El parámetro `passive_deletes=True` en SQLAlchemy instruye al ORM a no cargar innecesariamente en memoria todas las tareas hijas cuando se elimina una categoría, permitiendo que la base de datos relacional ejecute el `ON DELETE SET NULL` de manera nativa y directa.

---

### 2. Modelo de Datos de `Category` y Desvinculación Segura (Punto 2 del Requerimiento)

La nueva entidad `Category` (`src/taskcontrol/models/category.py`) se modela con los campos mínimos requeridos:

```python
from datetime import datetime, timezone
from src.taskcontrol.extensions import db

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship('User', backref=db.backref('categories', lazy='dynamic', cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uq_categories_user_id_name'),
    )
```

#### Regla de Negocio y Comportamiento a Nivel de Base de Datos al Eliminar una Categoría
- **Mecanismo de Implementación**: Clave foránea nullable `category_id` en la tabla `tasks` con cláusula `ON DELETE SET NULL`.
- **Qué ocurre exactamente en el motor de base de datos**:
  1. Cuando un usuario solicita eliminar una categoría y se ejecuta `DELETE FROM categories WHERE id = :category_id;`, el motor relacional (SQLite con claves foráneas habilitadas o PostgreSQL) intercepta la eliminación.
  2. Debido a la regla declarativa `FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL`, el motor actualiza automáticamente en cascada inversa las filas referenciadas en la tabla `tasks`, asignando `category_id = NULL` a todas las tareas que apuntaban a dicha categoría.
  3. **Ninguna fila de la tabla `tasks` es eliminada**: ni física ni lógicamente. Las tareas preservan su identificador, título, descripción, estado, prioridad, fechas y log de auditoría.
  4. En SQLAlchemy, al configurarse `passive_deletes=True`, el ORM no emite instrucciones `DELETE` hacia las tareas hijas, respetando íntegramente la delegación en la base de datos.
  5. En `CategoryService.delete_category(user_id, category_id)`:
     - Se valida que la categoría exista y pertenezca al usuario (`user_id`).
     - Se invoca `db.session.delete(category)`.
     - Se emite el evento de auditoría `AuditService.record_category_event(actor_id=user_id, action='CATEGORY_DELETED', category_id=category_id, details={'category_name': category.name})`.
     - Se confirma la transacción con `db.session.commit()`.

---

### 3. Contrato de los Nuevos Endpoints y Extensión del Listado (Punto 3 del Requerimiento)

#### 3.1 Cambiar Prioridad de una Tarea: `POST /tasks/<int:task_id>/priority`
- **Controlador**: `src/taskcontrol/blueprints/tasks.py` delegando en `TaskService.set_task_priority(user_id, task_id, priority)`.
- **Seguridad**: `@login_required` + validación obligatoria de token CSRF (`csrf_token` o `X-CSRFToken`).
- **Payload**: `{ "priority": "high" | "medium" | "low", "csrf_token": "..." }`.
- **Reglas de Dominio**:
  - Tarea debe existir y pertenecer al usuario autenticado.
  - Tarea no debe estar eliminada (`is_deleted == False`).
  - Prioridad debe ser una de `{'high', 'medium', 'low'}`; cualquier otro valor arroja `InvalidPriorityError` (HTTP 400).
  - Emite auditoría inmutable: `TASK_PRIORITY_CHANGED` con `previous_priority` y `new_priority`.
- **Respuesta**: `302 Found` (redirección a `/tasks`) o `200 OK` JSON con `{ "status": "success", "data": { "id": task_id, "priority": "high" } }`.

#### 3.2 Crear Categoría: `POST /categories`
- **Controlador**: `src/taskcontrol/blueprints/categories.py` delegando en `CategoryService.create_category(user_id, name)`.
- **Seguridad**: `@login_required` + token CSRF.
- **Payload**: `{ "name": "Nombre de categoría", "csrf_token": "..." }`.
- **Reglas de Dominio**:
  - `name`: cadena no vacía tras `.strip()`, longitud entre 1 y 50 caracteres.
  - Unicidad por usuario: si ya existe una categoría con ese nombre para el usuario (comparación case-insensitive), se lanza `DuplicateCategoryNameError` (HTTP 409 o 400).
  - Emite auditoría: `CATEGORY_CREATED`.
- **Respuesta**: `302 Found` (redirección a `/categories`) o `201 Created` JSON con `{ "status": "success", "data": { "id": 1, "name": "..." } }`.

#### 3.3 Listar Categorías: `GET /categories`
- **Controlador**: `src/taskcontrol/blueprints/categories.py` delegando en `CategoryService.get_user_categories(user_id)`.
- **Seguridad**: `@login_required`.
- **Respuesta**:
  - Navegador: Renderiza plantilla `categories/index.html` con listado de categorías y conteo de tareas activas.
  - JSON: `200 OK` con `{ "status": "success", "data": { "categories": [...], "total": N } }`.

#### 3.4 Eliminar Categoría: `POST /categories/<int:category_id>/delete`
- **Controlador**: `src/taskcontrol/blueprints/categories.py` delegando en `CategoryService.delete_category(user_id, category_id)`.
- **Seguridad**: `@login_required` + token CSRF.
- **Reglas de Dominio**:
  - Valida pertenencia al usuario actual.
  - Elimina categoría física en BD, provocando `ON DELETE SET NULL` sobre `tasks.category_id`.
  - Emite auditoría: `CATEGORY_DELETED`.
- **Respuesta**: `302 Found` a `/categories` con flash confirmando que las tareas fueron preservadas y desvinculadas, o `200 OK` JSON.

#### 3.5 Asignar Tarea a Categoría: `POST /tasks/<int:task_id>/category`
- **Controlador**: `src/taskcontrol/blueprints/tasks.py` delegando en `TaskService.assign_task_category(user_id, task_id, category_id)`.
- **Seguridad**: `@login_required` + token CSRF.
- **Payload**: `{ "category_id": 2 | null | "", "csrf_token": "..." }`.
- **Reglas de Dominio**:
  - Si `category_id` viene vacío o `null`, se desasigna (`task.category_id = None`).
  - Si viene un entero, se verifica que la categoría exista y pertenezca al usuario autenticado (`category.user_id == user_id`). Queda denegado asignar categorías de otros usuarios (`CategoryAccessDeniedError` / HTTP 403 o 404).
  - Emite auditoría: `TASK_CATEGORY_ASSIGNED` con `previous_category_id` y `new_category_id`.
- **Respuesta**: `302 Found` o `200 OK` JSON.

#### 3.6 Extensión del Endpoint de Listado: `GET /tasks`
- **Parámetros Query Soportados**:
  - `status`: `'all'` (defecto), `'pending'`, `'in_progress'`, `'completed'`. (Compatibilidad total con Incrementos 1 y 2).
  - `sort_by`: `'created_desc'` (defecto), `'priority'`.
  - `category_id`: `'all'` (defecto), `'none'`, `<int>`.
- **Implementación en `TaskService.get_user_tasks`**:
  ```python
  def get_user_tasks(user_id: int, status: str = 'all', sort_by: str = 'created_desc', category_id: str | int = 'all'):
      query = Task.query.filter(Task.user_id == user_id, Task.is_deleted == False)

      # 1. Filtro por estado existente (sin alteraciones)
      if status != 'all':
          query = query.filter(Task.status == status)

      # 2. Filtro por categoría (nuevo)
      if str(category_id) == 'none':
          query = query.filter(Task.category_id.is_(None))
      elif str(category_id) != 'all':
          cat_id_int = int(category_id)
          # Verificar pertenencia al usuario
          query = query.filter(Task.category_id == cat_id_int)

      # 3. Ordenamiento ortogonal (nuevo)
      if sort_by == 'priority':
          priority_weight = db.case(
              {'high': 3, 'medium': 2, 'low': 1},
              value=Task.priority,
              else_=0
          )
          query = query.order_by(priority_weight.desc(), Task.created_at.desc())
      else:
          query = query.order_by(Task.created_at.desc())

      return query.all()
  ```
- **Garantía**: El filtro de estado se aplica de forma ortogonal e independiente del filtro de categoría y del ordenamiento. El usuario puede consultar tareas "en progreso" ordenadas por prioridad pertenecientes a una categoría específica sin conflicto.

---

### 4. Cálculo del Indicador de Tareas Vencidas (`is_overdue`) (Punto 4 del Requerimiento)

#### Dónde y Cómo se Calcula
- **Capa de Ejecución**: Exclusivamente en el backend dentro de la capa de modelos/servicios de Python (`src/taskcontrol/models/task.py` y `src/taskcontrol/services/task_service.py`).
- **Implementación**:
  ```python
  @property
  def is_overdue(self) -> bool:
      # Exclusión 1: Tareas eliminadas lógicamente nunca vencen
      if self.is_deleted:
          return False
      # Exclusión 2: Tareas completadas nunca vencen
      if self.status == 'completed':
          return False
      # Exclusión 3: Tareas sin fecha límite nunca vencen
      if self.due_date is None:
          return False
      # Evaluación en UTC contra el día calendario actual en el backend
      return self.due_date < datetime.now(timezone.utc).date()
  ```
- **Por qué NUNCA se persiste como columna física en la base de datos**:
  1. Si se persistiera como columna `is_overdue BOOLEAN`, el valor quedaría obsoleto cada medianoche a menos que se ejecutaran procesos periódicos (cron jobs, Celery, schedulers externos).
  2. La introducción de cron jobs o workers asíncronos violaría de forma flagrante el **Principio I (Monolito por diseño)** y añadiría complejidad innecesaria en contra del **Principio V (Simplicidad)**.
  3. Al calcularse dinámicamente como un campo derivado en memoria durante la consulta, la evaluación es $O(1)$, 100% determinista, siempre precisa y no requiere sincronización alguna.
- **Exclusión explícita de tareas completadas y eliminadas**:
  - Si `task.status == 'completed'`, `is_overdue` retorna `False` sin importar cuán antigua sea la `due_date`.
  - Si `task.is_deleted == True`, `is_overdue` retorna `False`.
  - Tareas con fecha límite para el día de hoy: `due_date == today` retorna `False` (el usuario tiene hasta el final del día actual para completarla; sólo se considera vencida a partir del día siguiente).
- **Consumo en la Capa de Presentación**:
  - En la respuesta JSON de `GET /tasks`, cada tarea serializada contiene `"is_overdue": task.is_overdue`.
  - En las plantillas Jinja2 (`tasks/index.html`), se evalúa `{% if task.is_overdue %}<span class="badge badge-overdue">Vencida</span>{% endif %}`.

---

### 5. Estrategia de Migraciones sobre Esquema Existente (Principio VI) (Punto 5 del Requerimiento)

Para incorporar los nuevos campos y la nueva tabla sin alterar los datos preexistentes de los Incrementos 1 y 2:

1. **Generación del Script de Alembic**:
   ```bash
   flask db migrate -m "add_categories_and_task_priority"
   ```
2. **Contenido Normativo de la Migración (`migrations/versions/zzzz_add_categories_and_task_priority.py`)**:
   ```python
   def upgrade():
       # 1. Crear tabla categories
       op.create_table('categories',
           sa.Column('id', sa.Integer(), nullable=False),
           sa.Column('user_id', sa.Integer(), nullable=False),
           sa.Column('name', sa.String(length=50), nullable=False),
           sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
           sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
           sa.PrimaryKeyConstraint('id'),
           sa.UniqueConstraint('user_id', 'name', name='uq_categories_user_id_name')
       )
       op.create_index('ix_categories_user_id', 'categories', ['user_id'])

       # 2. Agregar columna priority con server_default='medium'
       op.add_column('tasks', sa.Column('priority', sa.String(length=20), server_default='medium', nullable=False))

       # 3. Agregar columna category_id nullable
       op.add_column('tasks', sa.Column('category_id', sa.Integer(), nullable=True))
       op.create_foreign_key('fk_tasks_category_id_categories', 'tasks', 'categories', ['category_id'], ['id'], ondelete='SET NULL')

       # 4. Índices para optimización de consultas
       op.create_index('ix_tasks_user_id_priority', 'tasks', ['user_id', 'priority'])
       op.create_index('ix_tasks_category_id', 'tasks', ['category_id'])

   def downgrade():
       op.drop_index('ix_tasks_category_id', table_name='tasks')
       op.drop_index('ix_tasks_user_id_priority', table_name='tasks')
       op.drop_constraint('fk_tasks_category_id_categories', 'tasks', type_='foreignkey')
       op.drop_column('tasks', 'category_id')
       op.drop_column('tasks', 'priority')
       op.drop_index('ix_categories_user_id', table_name='categories')
       op.drop_table('categories')
   ```
3. **Preservación Estricta de Datos Existentes**:
   - `server_default='medium'` garantiza que el motor de base de datos asigne de forma inmediata y automática la prioridad `'medium'` a todas las filas de tareas preexistentes en la tabla `tasks` sin intervención manual ni pérdida de consistencia.
   - La columna `category_id` es nullable y se inicializa con `NULL` para todas las tareas preexistentes, dejándolas en estado "sin categoría" de forma válida y predecible.
   - La migración es reproducible y se ejecuta desde la raíz mediante `flask db upgrade`.

---

### 6. Pruebas Automatizadas Bloqueantes (Principio IV) (Punto 6 del Requerimiento)

Conforme al Principio IV (Test-First bloqueante), ninguna línea de la capa de dominio o servicios será implementada sin contar previamente con pruebas unitarias en rojo que cubran exhaustivamente las siguientes condiciones críticas:

#### 6.1 Pruebas de Ordenamiento por Prioridad (`tests/unit/test_task_service.py`)
1. **`test_tasks_sorted_by_priority_descending`**:
   - *Escenario*: Se crean tareas con prioridades `'low'`, `'high'`, `'medium'`.
   - *Aserción*: Al invocar `get_user_tasks(user_id, sort_by='priority')`, las tareas se retornan en el orden estricto `high` $\rightarrow$ `medium` $\rightarrow$ `low`.
2. **`test_tasks_priority_tiebreak_by_created_at_desc`**:
   - *Escenario*: Se crean tres tareas con idéntica prioridad `'high'` en marcas temporales consecutivas $t_1, t_2, t_3$.
   - *Aserción*: Al ordenar por prioridad, el desempate secundario coloca primero la más reciente ($t_3 \rightarrow t_2 \rightarrow t_1$).
3. **`test_priority_sorting_combined_with_status_filter`**:
   - *Escenario*: Múltiples tareas en diferentes estados y prioridades.
   - *Aserción*: Filtrar por `status='in_progress'` y `sort_by='priority'` devuelve exclusivamente las tareas en progreso ordenadas por prioridad.
4. **`test_default_priority_is_medium_on_creation`**:
   - *Aserción*: Toda tarea creada sin especificar prioridad adquiere `'medium'`.
5. **`test_invalid_priority_raises_domain_error`**:
   - *Aserción*: Intentar asignar una prioridad distinta a `{'high', 'medium', 'low'}` lanza `InvalidPriorityError`.

#### 6.2 Pruebas de Desvinculación de Categorías sin Eliminación en Cascada (`tests/unit/test_category_service.py`)
6. **`test_delete_category_unlinks_tasks_setting_category_id_to_null`**:
   - *Escenario*: Se crea una categoría y se le asocian 3 tareas activas.
   - *Acción*: Se invoca `CategoryService.delete_category(user_id, category_id)`.
   - *Aserción Bloqueante*:
     - La categoría deja de existir en la base de datos.
     - **Las 3 tareas siguen existiendo íntegras** (`Task.query.filter_by(user_id=user_id).count() == 3`).
     - Ninguna tarea tiene `is_deleted == True`.
     - Las 3 tareas tienen `category_id is None`.
7. **`test_category_name_unique_per_user_case_insensitive`**:
   - *Aserción*: Intentar crear una categoría con nombre duplicado (e.g., "Proyectos" y "proyectos") para el mismo usuario lanza `DuplicateCategoryNameError`.
8. **`test_cannot_assign_category_from_another_user`**:
   - *Aserción*: Intentar asignar una tarea a una categoría perteneciente a otro usuario es rechazado con excepción de seguridad de dominio.

#### 6.3 Pruebas de Cálculo de Vencimiento (`tests/unit/test_task_service.py`)
9. **`test_completed_task_with_past_due_date_is_never_overdue`**:
   - *Escenario*: Tarea con `due_date = ayer` y `status = 'completed'`.
   - *Aserción Bloqueante*: `task.is_overdue` es deterministamente `False`.
10. **`test_soft_deleted_task_with_past_due_date_is_never_overdue`**:
    - *Escenario*: Tarea eliminada lógicamente (`is_deleted = True`) con `due_date = ayer`.
    - *Aserción Bloqueante*: `task.is_overdue` es deterministamente `False`.
11. **`test_pending_or_in_progress_task_with_past_due_date_is_overdue`**:
    - *Escenario*: Tarea activa (`pending` o `in_progress`) con `due_date = ayer`.
    - *Aserción Bloqueante*: `task.is_overdue` es deterministamente `True`.
12. **`test_task_with_due_date_today_is_not_overdue`**:
    - *Escenario*: Tarea con `due_date = hoy`.
    - *Aserción*: `task.is_overdue` es `False`.
13. **`test_task_without_due_date_is_not_overdue`**:
    - *Escenario*: Tarea con `due_date = None`.
    - *Aserción*: `task.is_overdue` es `False`.

---

## Complexity Tracking

| Solución Adoptada | Justificación frente al Principio V (Simplicidad) | Alternativas Más Complejas Rechazadas |
|---|---|---|
| **Prioridad como columna `String(20)` con ponderación SQL `case()`** | Simple, directa y legible. Resuelve los 3 niveles requeridos (`high`, `medium`, `low`) con ordenamiento óptimo en una sola consulta SQL, sin introducir tablas relacionales adicionales ni joins innecesarios. | 1. Tabla relacional auxiliar `priorities` (introduce joins costosos y mantenimiento de catálogos para solo 3 constantes estáticas).<br>2. Campo entero libre (1 a 100) que introduce complejidad conceptual y visual innecesaria. |
| **Desvinculación relacional con `ON DELETE SET NULL` nativo** | Máxima simplicidad e integridad. Delega en el motor de base de datos relacional la responsabilidad de poner en nulo las claves foráneas en una única operación atómica, sin requerir bucles manuales de actualización en Python. | 1. Interceptores o listeners `before_delete` de SQLAlchemy que recorren y actualizan tarea por tarea (propenso a fallos, bloqueos y menor rendimiento).<br>2. Borrado lógico de categorías con banderas booleanas (`is_deleted`), innecesario dado que las categorías no requieren auditoría de reapertura. |
| **Cálculo de `is_overdue` como `@property` en memoria** | Costo $O(1)$, exactitud absoluta en UTC y cero mantenimiento. Elimina por completo la necesidad de almacenar un estado redundante que caduca a diario. | 1. Columna booleana persistida `is_overdue` mantenida mediante Celery Beat o cron jobs nocturnos (violación directa del Principio I al exigir procesos desacoplados fuera del monolito).<br>2. Triggers de base de datos dependientes del reloj del sistema del motor SQL (rompe la portabilidad entre SQLite y PostgreSQL). |
| **Filtro composicional directo en `TaskService`** | Permite combinar `status`, `category_id` y `sort_by` mediante métodos estándar de SQLAlchemy (`filter`, `order_by`) de forma transparente y legible. | 1. Adopción de GraphQL o bibliotecas pesadas de query builders dinámicos.<br>2. Creación de endpoints especializados separados para cada combinación posible de filtros (`/tasks/by-category`, `/tasks/by-priority`), lo que duplicaría controladores y vistas. |
