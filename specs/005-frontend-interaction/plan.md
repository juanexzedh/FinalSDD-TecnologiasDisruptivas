# Implementation Plan: Mejoras de Interacción Frontend mediante JavaScript (Incremento 5)

**Branch**: `005-frontend-interaction` | **Date**: 2026-10-08 | **Spec**: [spec.md](file:///C:/Users/Kreilt/Downloads/SDD-Tecnologias-Disruptivas-main/specs/005-frontend-interaction/spec.md)

**Input**: Especificación funcional desde `specs/005-frontend-interaction/spec.md` (cubre HU-15 y HU-16 del backlog, construyendo sobre los endpoints y modelos ya definidos en los Incrementos 1 a 4).

---

## Summary

Implementar el quinto y último incremento funcional de TaskControl (Mejoras de Interacción Frontend mediante JavaScript) optimizando la experiencia de usuario sin recargar la página y permitiendo reordenamiento visual de tareas, en estricto cumplimiento de la constitución del proyecto y sus restricciones tecnológicas:
1. **Completar tareas sin recarga de página (HU-15)**: Implementación en JavaScript vanilla utilizando `fetch` asíncrono contra el endpoint ya existente `POST /tasks/<id>/status` (Incremento 1) con cabecera `X-CSRFToken`. Se aplica el patrón de interfaz optimista con **reversión visual obligatoria (Rollback)** ante cualquier error de red o de servidor, garantizando que la pantalla jamás exhiba un estado no confirmado por el backend.
2. **Reordenamiento persistente mediante Arrastrar y Soltar (HU-16)**: Implementación de Drag and Drop en el cliente mediante la API nativa HTML5 Drag and Drop (o micro-librería utilitaria imperativa sin dependencias como SortableJS) en `static/js/main.js`. Al soltar el elemento, se despacha una llamada asíncrona hacia el backend que persiste la nueva secuencia de posiciones.
3. **Único cambio de backend**: Adición de una columna numérica `position` en el modelo `Task` (`Integer`, no nulo, indexado) y un endpoint de actualización de posiciones `POST /tasks/reorder` dentro del blueprint `tasks.py`.
4. **Aislamiento y concurrencia por usuario (Principio VII)**: El orden es estrictamente local por usuario (`user_id`). Dos usuarios reordenando simultáneamente operan sobre conjuntos de filas disjuntos sin bloqueos ni inconsistencias. La validación en el backend verifica que el 100% de las tareas pertenezcan al usuario autenticado antes de alterar cualquier posición.
5. **Migración e integridad de datos (Principio VI)**: Script de migración en Flask-Migrate con `server_default='0'`, garantizando que todas las tareas existentes de los Incrementos 1 a 4 adquieran `position = 0` y conserven su orden cronológico habitual (`created_at DESC`) sin alteración alguna.
6. **Estrategia de pruebas (Principio IV)**: Pruebas unitarias de servicio en Python que certifican la actualización correcta de posiciones y el rechazo ante tareas ajenas, y escenarios de validación manual sistemáticos para la reversión visual de JavaScript sin requerir herramientas externas de Node.js.

---

## Technical Context

**Language/Version**: Python 3.11+ (Backend) y JavaScript Vanilla (ECMAScript estándar para Frontend)  
**Primary Dependencies**: Flask 3.x, Flask-SQLAlchemy 3.x, Flask-Migrate (Alembic), Flask-WTF 1.2+ (`CSRFProtect`), python-dotenv 1.0+, Werkzeug 3.x, Jinja2  
**Storage**: Base de datos relacional vía SQLAlchemy ORM (SQLite local para desarrollo/pruebas; PostgreSQL para producción)  
**Testing**: `pytest`, `pytest-cov` (ejecución de pruebas backend con SQLite en memoria)  
**Target Platform**: Servidor web monolítico ejecutable localmente en Windows y Linux  
**Project Type**: Aplicación web monolítica con renderizado en servidor Jinja2 y JavaScript vanilla auxiliar  
**Performance Goals**: Tiempo de respuesta visual optimista < 50 ms en el cliente; persistencia de reordenamiento < 100 ms en backend  
**Constraints**:
- Cumplimiento estricto de los 8 principios constitucionales.
- Monolito por diseño: un único repositorio, un único proceso y una única base de datos (Principio I).
- Restricción Técnica 4 del Stack: **Prohibido el uso de frameworks SPA pesados (React, Vue, Angular)**. Toda la interactividad se programa en JavaScript vanilla o micro-librería utilitaria sin dependencias.
- Contratos de endpoints rigurosamente tipados con protección CSRF (`X-CSRFToken`) en todas las peticiones asíncronas `fetch` (Principio III y VII).
- TDD obligatorio y bloqueante para la lógica de reordenamiento en backend (Principio IV).
- Simplicidad y YAGNI (Principio V): cero empaquetadores complejos (webpack/vite), cero librerías pesadas de gestión de estado.
- Integridad de esquema mediante migraciones versionadas (Principio VI).
- Seguridad por defecto: validación obligatoria de propiedad de todas las tareas en el reordenamiento (Principio VII).  
**Scale/Scope**: Incremento final focalizado exclusivamente en HU-15 y HU-16. Cierra la totalidad de las 16 historias de usuario del backlog.

---

## Constitution Check

*GATE: Evaluación técnica previa y posterior al diseño contra la constitución de TaskControl.*

| Principio | Estado | Justificación y Cumplimiento en el Plan |
|---|---|---|
| **I. Monolito por diseño** | **PASS** | La aplicación permanece como un único proceso monolítico. Toda la interactividad cliente reside en `static/js/main.js` consumiendo endpoints HTTP expuestos por la misma aplicación Flask sobre la base de datos relacional compartida. |
| **II. Separación en capas** | **PASS** | Estricta separación: Modelo `Task` con columna `position`; servicio `TaskService.reorder_tasks` con lógica de asignación de índices; blueprint `tasks.py` deserializando y respondiendo JSON; plantillas Jinja2 renderizando atributos de orden; y JavaScript vanilla gestionando eventos del DOM. |
| **III. Contrato explícito backend-JS** | **PASS** | Documentado en `contracts/frontend-interaction-contracts.md`. Todas las llamadas `fetch` consumen contratos formales (`POST /tasks/<id>/status` y `POST /tasks/reorder`) con JSON, tokens CSRF y catálogo determinista de respuestas 2xx/4xx. |
| **IV. Test-first en lógica de negocio** | **PASS** | TDD bloqueante a nivel de backend en `tests/unit/test_task_service.py` para el reordenamiento posicional y control de acceso. Las pruebas de reversión visual en frontend se validan con escenarios manuales documentados y reproducibles en `quickstart.md`. |
| **V. Simplicidad sobre generalidad prematura** | **PASS** | Filosofía YAGNI: (1) JavaScript vanilla nativo sin React/Vue/Angular ni bundles compilados; (2) Reordenamiento basado en un simple campo entero secuencial `position` en `tasks`; (3) Persistencia de orden en un único endpoint atómico. |
| **VI. Integridad de datos y migraciones** | **PASS** | Script versionado de Alembic que añade `position` con `server_default='0'`. Todas las tareas creadas en incrementos previos preservan su orden cronológico habitual por desempate con `created_at DESC`. |
| **VII. Seguridad por defecto** | **PASS** | Inyección obligatoria de `X-CSRFToken` en toda llamada `fetch`. Validación estricta en el backend que comprueba que todas las tareas a reordenar pertenezcan al usuario autenticado, impidiendo manipulación de datos ajenos (prevención de IDOR). |
| **VIII. Observabilidad mínima viable** | **PASS** | El cambio de estado asíncrono emite su correspondiente evento de auditoría en `audit_logs` con actor y timestamp. |

---

## Project Structure

### Documentation (este incremento)

```text
specs/005-frontend-interaction/
├── spec.md                              # Especificación funcional validada (HU-15, HU-16)
├── plan.md                              # Este plan técnico de implementación
├── research.md                          # Decisiones técnicas y justificaciones de arquitectura
├── data-model.md                        # Modelo relacional consolidado con campo position
├── quickstart.md                        # Guía de inicialización y validación extremo a extremo
├── checklists/
│   └── requirements.md                  # Checklist de verificación de calidad de requerimientos
└── contracts/                           # Contratos HTTP explícitos (Principio III)
    └── frontend-interaction-contracts.md# Contratos de cambio de estado asíncrono y reordenamiento
```

### Source Code (Repositorio Monolítico)

```text
src/
└── taskcontrol/
    ├── __init__.py                      # Application Factory
    ├── config.py                        # Configuración por entornos
    ├── extensions.py                    # SQLAlchemy, Flask-Migrate, CSRFProtect
    │
    ├── models/                          # Capa 1: Persistencia relacional
    │   ├── __init__.py
    │   ├── user.py
    │   ├── task.py                      # EXTENDIDO: Columna position con índice compuesto
    │   ├── category.py
    │   ├── notification.py
    │   ├── password_reset_token.py
    │   └── audit_log.py
    │
    ├── services/                        # Capa 2: Lógica de dominio (TDD bloqueante)
    │   ├── __init__.py
    │   ├── auth_service.py
    │   ├── task_service.py              # EXTENDIDO: reorder_tasks(user_id, task_ids), orden por position
    │   ├── notification_service.py
    │   ├── category_service.py
    │   ├── recovery_service.py
    │   ├── email_service.py
    │   └── audit_service.py
    │
    ├── blueprints/                      # Capa 3: Controladores HTTP y protección CSRF
    │   ├── __init__.py
    │   ├── auth.py
    │   ├── tasks.py                     # EXTENDIDO: POST /tasks/reorder y soporte JSON en status
    │   ├── notifications.py
    │   ├── categories.py
    │   └── decorators.py
    │
    ├── templates/                       # Capa 4A: Presentación Jinja2
    │   ├── base.html                    # Layout maestro (meta csrf-token, contenedor de toasts/alertas)
    │   └── tasks/
    │       └── index.html               # ACTUALIZADO: data-task-id, controles interactivos y draggable="true"
    │
    └── static/                          # Capa 4B: JavaScript Vanilla y Estilos
        ├── css/styles.css               # Estilos para arrastre (dropzone, dragging) y toasts
        └── js/
            └── main.js                  # ACTUALIZADO: toggleTaskComplete() y lógica de Drag and Drop

migrations/                              # Scripts versionados de Alembic / Flask-Migrate
├── versions/
│   ├── xxxx_initial_schema.py           # Incremento 1
│   ├── yyyy_add_soft_delete_and_reset.py# Incremento 2
│   ├── zzzz_add_categories_and_task_priority.py # Incremento 3
│   ├── aaaa_add_task_assignee_and_notifications.py # Incremento 4
│   └── bbbb_add_task_position.py        # NUEVO: columna position en tasks con índice compuesto

tests/
├── conftest.py
├── unit/                                # Pruebas unitarias de dominio (TDD bloqueante)
│   ├── test_task_service.py             # EXTENDIDO: Pruebas de reorder_tasks y aislamiento por usuario
│   ├── test_notification_service.py
│   ├── test_category_service.py
│   ├── test_auth_service.py
│   └── test_audit_service.py
└── integration/                         # Pruebas de integración HTTP y contratos
    └── test_task_routes.py              # EXTENDIDO: Pruebas de POST /tasks/reorder y POST /status JSON
```

**Structure Decision**: Se mantiene inalterada la estructura monolítica en `src/taskcontrol/`.

---

## Estrategia de Implementación Detallada por Capas

### 1. Estrategia de JavaScript para Interacción sin Recarga (HU-15) (Punto 1 del Requerimiento)

#### Consumo de Endpoint Existente y Reversión ante Error
- Se utiliza la función nativa `fetch()` del navegador en `src/taskcontrol/static/js/main.js` apuntando al endpoint ya existente `POST /tasks/<id>/status` (definido en el Incremento 1).
- **Extracción de Token CSRF**: Se lee el token desde la etiqueta `<meta name="csrf-token" content="{{ csrf_token() }}">` y se envía en el encabezado `X-CSRFToken` y `Content-Type: application/json`.
- **Flujo de Ejecución y Rollback Visual**:
  ```javascript
  function initAsyncComplete() {
      document.querySelectorAll('.task-complete-btn, .task-complete-checkbox').forEach(btn => {
          btn.addEventListener('change', async (event) => {
              const taskCard = btn.closest('.task-card');
              const taskId = taskCard.dataset.taskId;
              const wasChecked = !btn.checked; // Estado previo original

              // 1. Cambio visual optimista inmediato
              taskCard.classList.toggle('task-completed', btn.checked);
              btn.disabled = true; // Prevenir clics duplicados

              try {
                  const response = await fetch(`/tasks/${taskId}/status`, {
                      method: 'POST',
                      headers: {
                          'Content-Type': 'application/json',
                          'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                      },
                      body: JSON.stringify({ status: 'completed' })
                  });

                  if (!response.ok) {
                      const err = await response.json().catch(() => ({}));
                      throw new Error(err.message || 'Error al actualizar el estado de la tarea en el servidor.');
                  }

                  // 2. Éxito confirmado: habilitar control y ocultar badge de vencida
                  btn.disabled = false;
                  const overdueBadge = taskCard.querySelector('.badge-overdue');
                  if (overdueBadge) overdueBadge.style.display = 'none';

              } catch (error) {
                  // 3. Rollback visual determinista
                  btn.checked = wasChecked;
                  taskCard.classList.toggle('task-completed', wasChecked);
                  btn.disabled = false;
                  showNotificationToast(error.message, 'error');
              }
          });
      });
  }
  ```
- **Justificación de No Introducir Frameworks (Restricción Técnica 4 del Stack y Principio V)**:
  - La actualización visual se reduce a conmutar una clase CSS (`classList.toggle`) y actualizar un atributo booleano. Implementar React, Vue, Angular o incluso Alpine.js añadiría kilobytes innecesarios, compiladores, dependencias externas y complejidad de mantenimiento sin ningún beneficio real, violando el Principio V (Simplicidad) y la prohibición explícita de la constitución contra frameworks SPA pesados.

---

### 2. Técnica y Librería para Drag-and-Drop (HU-16) (Punto 2 del Requerimiento)

#### Elección Técnica
- Se implementa mediante **la API nativa HTML5 Drag and Drop** (`draggable="true"` con eventos `dragstart`, `dragover`, `drop`, `dragend`) o, para máxima consistencia y soporte táctil, la micro-librería utilitaria sin dependencias **`SortableJS`** (~10 KB minificado) alojada de forma estática en `static/js/sortable.min.js`.

#### Justificación frente a la Constitución:
- `SortableJS` es una biblioteca utilitaria de funcionalidad acotada (micro-librería de manipulación imperativa del DOM existente), **no un framework SPA**.
- No implementa Virtual DOM, no toma control del enrutamiento ni de la renderización de plantillas, no exige Node.js, npm, Webpack ni Babel, y se integra de forma transparente como un archivo estático auxiliar en Jinja2.
- Cumple 100% con la restricción del stack: *"Plantillas Jinja2 para renderizado en servidor complementadas con JavaScript vanilla (estándar) para interactividad y peticiones asíncronas vía fetch. No se permite el uso de frameworks SPA pesados..."*.

---

### 3. Único Cambio de Backend y Contrato de Endpoint (Punto 3 del Requerimiento)

#### 3.1 Cambio en el Modelo `Task` (`src/taskcontrol/models/task.py`)
Se incorpora la columna `position`:
```python
position = db.Column(db.Integer, default=0, server_default='0', nullable=False)

__table_args__ = (
    # Índices existentes...
    db.Index('ix_tasks_user_id_position', 'user_id', 'position'),
)
```

#### 3.2 Contrato del Endpoint de Reordenamiento: `POST /tasks/reorder`
- **Ruta**: `/tasks/reorder`
- **Método**: `POST`
- **Autenticación**: Requerida (`@login_required`).
- **Protección CSRF**: Requerida vía encabezado `X-CSRFToken`.
- **Payload de Entrada (JSON)**:
  ```json
  {
    "task_ids": [15, 12, 8, 3]
  }
  ```
- **Lógica de Servicio en `TaskService.reorder_tasks(user_id, task_ids)`**:
  ```python
  def reorder_tasks(user_id: int, task_ids: list[int]) -> int:
      if not task_ids:
          raise InvalidPayloadError("La lista de tareas no puede estar vacía.")

      # Validar que todas las tareas existan, no estén eliminadas y pertenezcan al usuario
      tasks = Task.query.filter(
          Task.id.in_(task_ids),
          Task.user_id == user_id,
          Task.is_deleted == False
      ).all()

      if len(tasks) != len(task_ids):
          raise TaskAccessDeniedError("Una o más tareas no pertenecen al usuario o han sido eliminadas.")

      task_map = {task.id: task for task in tasks}

      # Actualizar posiciones secuenciales atómicamente
      for index, task_id in enumerate(task_ids):
          task_map[task_id].position = index

      db.session.commit()
      return len(task_ids)
  ```
- **Payload de Salida**:
  - `200 OK`:
    ```json
    {
      "status": "success",
      "message": "Orden de tareas guardado exitosamente",
      "data": {
        "reordered_count": 4
      }
    }
    ```
  - `400 Bad Request` (`INVALID_PAYLOAD`): Si `task_ids` no es una lista válida.
  - `403 Forbidden` (`TASK_ACCESS_DENIED`): Si se intenta alterar el orden de una tarea que no pertenece al usuario autenticado.

#### 3.3 Extensión del Listado Predeterminado en `GET /tasks`
En `TaskService.get_user_tasks`:
```python
if sort_by == 'priority':
    query = query.order_by(priority_weight.desc(), Task.created_at.desc())
else:
    # Orden manual personalizado con desempate por fecha
    query = query.order_by(Task.position.asc(), Task.created_at.desc())
```

---

### 4. Prevención de Inconsistencias entre Usuarios Concurrentes (Principio VII) (Punto 4 del Requerimiento)

- **Aislamiento por Usuario**:
  - El campo `position` no es un orden global de la base de datos; tiene alcance estrictamente acotado por usuario (`user_id`).
  - Cada usuario tiene su propia secuencia $0, 1, 2, \dots$ asociada a sus tareas.
- **Validación de Propiedad en Servidor**:
  - `TaskService.reorder_tasks` ejecuta `Task.query.filter(Task.id.in_(task_ids), Task.user_id == user_id)`.
  - Si un usuario malintencionado intenta inyectar el ID de una tarea ajena en el payload `task_ids`, la cantidad de tareas devueltas no coincide con la longitud de `task_ids`, provocando la inmediata denegación con excepción `TaskAccessDeniedError` (HTTP 403) y cancelando cualquier mutación.
- **Concurrencia Segura**:
  - Como cada usuario muta exclusivamente filas con su propio `user_id`, las operaciones de dos usuarios en paralelo tocan filas disjuntas, eliminando cualquier riesgo de condiciones de carrera o bloqueos cruzados entre usuarios.

---

### 5. Migración de Esquema para el Campo `position` (Principio VI) (Punto 5 del Requerimiento)

Script de migración de Alembic: `migrations/versions/bbbb_add_task_position.py`:

```python
def upgrade():
    op.add_column('tasks', sa.Column('position', sa.Integer(), server_default='0', nullable=False))
    op.create_index('ix_tasks_user_id_position', 'tasks', ['user_id', 'position'])

def downgrade():
    op.drop_index('ix_tasks_user_id_position', table_name='tasks')
    op.drop_column('tasks', 'position')
```

- **Preservación de Tareas Existentes**:
  - Al especificar `server_default='0'`, el motor de base de datos asigna automáticamente `position = 0` a todas las tareas creadas en los Incrementos 1 a 4.
  - Dado que la consulta de listado define como criterio secundario `Task.created_at.desc()`, todas las tareas existentes conservan de forma idéntica su orden cronológico habitual hasta que el usuario decida arrastrarlas manualmente.

---

### 6. Pruebas Automatizadas Bloqueantes y Estrategia de Testing (Principio IV) (Punto 6 del Requerimiento)

#### 6.1 Pruebas Bloqueantes a Nivel de Servicio / Backend (`tests/unit/test_task_service.py`)
1. **`test_reorder_tasks_updates_positions_sequentially`**:
   - Se crean tres tareas [T1, T2, T3]. Se invoca `reorder_tasks(user_id, [T3.id, T1.id, T2.id])`.
   - Se verifica que `T3.position == 0`, `T1.position == 1` y `T2.position == 2`.
   - Se consulta `get_user_tasks(user_id)` y se valida que el orden devuelto es exactamente [T3, T1, T2].
2. **`test_reorder_tasks_rejects_foreign_tasks_with_security_error`**:
   - Usuario 1 intenta reordenar incluyendo una tarea de Usuario 2.
   - La prueba verifica que se lanza `TaskAccessDeniedError`, no se altera ninguna posición y se ejecuta `rollback()`.
3. **`test_reorder_tasks_empty_list_rejected`**:
   - Pasar lista vacía arroja `InvalidPayloadError`.
4. **`test_default_position_is_zero_and_tiebreaks_by_created_at_desc`**:
   - Tareas con `position = 0` se ordenan por `created_at DESC`.

#### 6.2 Estrategia de Pruebas de JavaScript (Frontend)
- **Declaración Explícita**: Dado que TaskControl es un monolito estricto en Python/Flask/Jinja2 sin herramientas de Node.js instaladas en el repositorio (para no violar el Principio V agregando dependencias como Jest, Playwright o Selenium), las pruebas de comportamiento en el cliente se certifican mediante **escenarios de validación manual sistemáticos y reproducibles** documentados en `quickstart.md`:
  - Validación de reversión visual (Rollback): simular desconexión (DevTools Offline) al hacer clic en completar y verificar que la casilla se desmarca y aparece la alerta de error.
  - Validación de persistencia de Drag and Drop: arrastrar tarjeta, soltar, recargar con F5 y verificar que la posición persiste.

---

## Complexity Tracking

| Solución Adoptada | Justificación frente al Principio V (Simplicidad) | Alternativas Más Complejas Rechazadas |
|---|---|---|
| **JavaScript Vanilla y `fetch` con Rollback** | Cero dependencias añadidas. Resuelve la reactividad optimista y el manejo de errores en 40 líneas de código nativo, manteniendo el stack liviano. | 1. Introducir React, Vue o Angular (viola la Restricción 4 y exige Node.js/Webpack).<br>2. Librerías de estado global (Redux, Zustand). |
| **API HTML5 Drag and Drop / SortableJS** | Manipulación imperativa y directa sobre el DOM de Jinja2 en ~10 KB sin dependencias externas. | 1. Frameworks de drag and drop pesados vinculados a ecosistemas React/Vue.<br>2. Re-renderizado completo de la página mediante iframe o polling. |
| **Columna secuencial `position` en `tasks`** | Modelo simple de ordenamiento por enteros secuenciales. Fácil de migrar, indexar y consultar. | 1. Lista doblemente enlazada relacional (`previous_task_id`, `next_task_id`) que introduce complejidad extrema en inserciones y bloqueos.<br>2. Algoritmos de ordenamiento fraccionario (Fractional Indexing) que requieren librerías matemáticas y manejo de precisión flotante. |
