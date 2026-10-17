# Implementation Plan: Colaboración entre Usuarios (Incremento 4)

**Branch**: `004-user-collaboration` | **Date**: 2026-10-08 | **Spec**: [spec.md](file:///C:/Users/Kreilt/Downloads/SDD-Tecnologias-Disruptivas-main/specs/004-user-collaboration/spec.md)

**Input**: Especificación funcional desde `specs/004-user-collaboration/spec.md` (cubre HU-10 y HU-11 del backlog, asumiendo implementados los Incrementos 1 a 3).

---

## Summary

Implementar el cuarto incremento funcional de TaskControl (Colaboración entre Usuarios) consolidando la arquitectura monolítica en 4 capas y el cumplimiento riguroso de la constitución del proyecto:
1. **Asignación y delegación de tareas (HU-10)**: Extensión del modelo `Task` con un campo explícito y separado `assignee_id` (preservando `user_id` como creador y propietario legítimo), con validación obligatoria en backend de que el destinatario sea un usuario registrado activo (Principio VII), y registro inmutable en auditoría (`TASK_ASSIGNED`, `TASK_UNASSIGNED`, Principio VIII).
2. **Listado de tareas con procedencia y distinción visual (HU-10)**: Ampliación de `GET /tasks` con el parámetro de procedencia `scope` (`'all'`, `'created'`, `'assigned'`), distinguiendo visualmente con insignias claras las tareas creadas por el usuario de las tareas asignadas por terceros, sin romper los filtros preexistentes de estado, categoría y ordenamiento por prioridad.
3. **Notificaciones internas atómicas (HU-11)**: Nueva entidad `Notification` persistida en base de datos con clave foránea `task_id` nullable (`ON DELETE SET NULL`). La notificación se crea atómicamente en la misma transacción relacional del servicio de asignación: en asignación inicial o reasignación se notifica al nuevo asignatario; en reasignación o desasignación se notifica adicionalmente al asignatario previo para informarle la revocación (descartando alertas en auto-asignación).
4. **Gestión de lectura y retención histórica (HU-11)**: Endpoints dedicados para listar notificaciones (`GET /notifications`), marcar como leída individualmente (`POST /notifications/<id>/read`) o en lote (`POST /notifications/read-all`). Las notificaciones leídas **persisten** en el historial del usuario (`is_read=True`, `read_at`), no se destruyen automáticamente, y la eliminación lógica de una tarea conserva sus notificaciones históricas.
5. **Migraciones de esquema (Principio VI)**: Script incremental con Flask-Migrate que incorpora `assignee_id` nullable con política `ON DELETE SET NULL` y crea la tabla `notifications` con `task_id` nullable (`ON DELETE SET NULL`), garantizando la continuidad e integridad de todas las tareas existentes de incrementos anteriores.
6. **Pruebas automatizadas bloqueantes (Principio IV)**: Suite de pruebas en la capa de servicios que certifican la generación de notificaciones (incluyendo aviso al asignatario previo en reasignación/desasignación), el rechazo ante correos no registrados, la exclusividad del creador en operaciones de edición/reasignación/borrado (`FR-018`), y la presencia de la tarea en el listado del asignatario.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flask 3.x, Flask-SQLAlchemy 3.x, Flask-Migrate (Alembic), Flask-WTF 1.2+ (`CSRFProtect`), python-dotenv 1.0+, Werkzeug 3.x, Jinja2  
**Storage**: Base de datos relacional vía SQLAlchemy ORM (SQLite local para desarrollo y pruebas; PostgreSQL para despliegue)  
**Testing**: `pytest`, `pytest-cov` (ejecución de pruebas de servicios con SQLite en memoria `:memory:`)  
**Target Platform**: Servidor web monolítico ejecutable localmente en Windows y Linux  
**Project Type**: Aplicación web monolítica con renderizado en servidor Jinja2 y JavaScript vanilla auxiliar  
**Performance Goals**: Tiempo de respuesta menor a 100 ms para consultas del listado combinado de tareas y lectura de notificaciones  
**Constraints**:
- Cumplimiento innegociable de los 8 principios constitucionales.
- Monolito estricto: sin intermediarios de mensajería asíncrona ni brokers (Redis, RabbitMQ, Celery) ni servicios externos de correo (Principio I).
- Separación nítida en 4 capas: Modelos, Servicios, Blueprints, Presentación (Principio II).
- Contratos de endpoints rigurosamente tipados con protección CSRF en todo POST (Principio III y VII).
- TDD obligatorio y bloqueante antes de escribir lógica de negocio (Principio IV).
- Simplicidad y YAGNI priorizados (Principio V): notificaciones relacionales simples sin WebSockets ni push externo.
- Integridad relacional y migraciones reproducibles con Alembic (Principio VI): `ON DELETE SET NULL` en `assignee_id` y `ON DELETE SET NULL` en `notifications.task_id`.
- Seguridad por defecto (Principio VII): validación estricta en backend de existencia de usuarios, entrada manual de correo exacto sin autocompletar para evitar enumeración, aislamiento por sesión (`@login_required`) y matriz de permisos estricta (`FR-018`).
- Observabilidad mínima viable (Principio VIII): auditoría con actor, timestamp y metadatos en cada cambio de asignación.  
**Scale/Scope**: Limitado estrictamente a HU-10 y HU-11. Fuera de alcance: interacción dinámica sin recarga (HU-15) y drag-and-drop (HU-16).

---

## Constitution Check

*GATE: Evaluación técnica previa y posterior al diseño contra la constitución de TaskControl.*

| Principio | Estado | Justificación y Cumplimiento en el Plan |
|---|---|---|
| **I. Monolito por diseño** | **PASS** | El sistema continúa operando como un único proceso web con una única base de datos relacional. Las notificaciones se gestionan internamente como filas en la tabla `notifications` del monolito, prescindiendo de servicios de correo externos o sockets distribuidos. |
| **II. Separación en capas** | **PASS** | 4 capas estrictas: `models/notification.py` y `models/task.py` (persistencia); `services/notification_service.py` y `services/task_service.py` (dominio puro sin dependencias HTTP); `blueprints/notifications.py` y `blueprints/tasks.py` (controladores HTTP); y `templates/` + `static/` (presentación). |
| **III. Contrato explícito backend-JS** | **PASS** | Contratos detallados en `contracts/collaboration-contracts.md` y `contracts/notification-contracts.md`, con rutas, métodos, tokens CSRF y respuestas JSON deterministas con catálogo de errores 4xx/5xx. |
| **IV. Test-first en lógica de negocio** | **PASS** | TDD bloqueante: se implementan en rojo pruebas unitarias en `tests/unit/test_task_service.py` y `tests/unit/test_notification_service.py` para asignación, validación de existencia, emisión de notificación y persistencia de lectura. |
| **V. Simplicidad sobre generalidad prematura** | **PASS** | Filosofía YAGNI: (1) Asignatario como columna foránea simple en `tasks` en vez de tablas complejas de asignaciones grupales; (2) Notificaciones modeladas como tabla relacional consultada al cargar páginas (polling natural vía recarga), sin sistemas de suscripción ni WebSockets; (3) Creación de notificación atómica en el mismo servicio sin eventos desacoplados. |
| **VI. Integridad de datos y migraciones** | **PASS** | Script versionado de Flask-Migrate con `assignee_id` nullable y `ON DELETE SET NULL`. Las tareas existentes de los Incrementos 1 a 3 adquieren `assignee_id = NULL` sin pérdida ni alteración de datos. |
| **VII. Seguridad por defecto** | **PASS** | Validación canónica en el backend que verifica la existencia activa del destinatario en `users`, aislamiento estricto de notificaciones por usuario autenticado, y protección CSRF obligatoria en todos los métodos POST. |
| **VIII. Observabilidad mínima viable** | **PASS** | Registro obligatorio de eventos inmutables `TASK_ASSIGNED` y `TASK_UNASSIGNED` en `audit_logs` con actor, identificador de tarea y metadatos de los involucrados. |

---

## Project Structure

### Documentation (este incremento)

```text
specs/004-user-collaboration/
├── spec.md                              # Especificación funcional validada (HU-10, HU-11)
├── plan.md                              # Este plan técnico de implementación
├── research.md                          # Decisiones técnicas y justificaciones de arquitectura
├── data-model.md                        # Modelo relacional de Notification y extensión de Task
├── quickstart.md                        # Guía de inicialización y validación extremo a extremo
├── checklists/
│   └── requirements.md                  # Checklist de verificación de calidad de requerimientos
└── contracts/                           # Contratos HTTP explícitos (Principio III)
    ├── collaboration-contracts.md       # Contratos de asignación y listado de tareas con scope
    └── notification-contracts.md        # Contratos de consulta, lectura y borrado de notificaciones
```

### Source Code (Repositorio Monolítico)

```text
src/
└── taskcontrol/
    ├── __init__.py                      # Application Factory (registro de blueprints notifications y tasks)
    ├── config.py                        # Configuración por entornos
    ├── extensions.py                    # Instancias de SQLAlchemy, Flask-Migrate y CSRFProtect
    │
    ├── models/                          # Capa 1: Persistencia relacional
    │   ├── __init__.py
    │   ├── user.py                      # Modelo User existente (id, email, password_hash)
    │   ├── task.py                      # EXTENDIDO: Columna assignee_id, relaciones creator y assignee
    │   ├── category.py                  # Modelo Category existente (Incremento 3)
    │   ├── notification.py              # NUEVO: Modelo Notification (user_id, task_id, is_read, read_at)
    │   ├── password_reset_token.py      # Modelo PasswordResetToken existente (Incremento 2)
    │   └── audit_log.py                 # Modelo AuditLog (soporte para TASK_ASSIGNED, TASK_UNASSIGNED)
    │
    ├── services/                        # Capa 2: Lógica de negocio y dominio puro (TDD bloqueante)
    │   ├── __init__.py
    │   ├── auth_service.py              # Servicio de autenticación
    │   ├── task_service.py              # EXTENDIDO: assign_task(), get_user_tasks(scope='all|created|assigned')
    │   ├── notification_service.py      # NUEVO: NotificationService (crear, listar, marcar leída, marcar todas)
    │   ├── category_service.py          # Servicio de categorías
    │   ├── recovery_service.py          # Servicio de recuperación de claves
    │   ├── email_service.py             # Emulador de correos
    │   └── audit_service.py             # Auditoría estructurada JSON
    │
    ├── blueprints/                      # Capa 3: Controladores HTTP y protección CSRF
    │   ├── __init__.py
    │   ├── auth.py                      # Autenticación y recuperación de contraseñas
    │   ├── tasks.py                     # EXTENDIDO: POST /tasks/<id>/assign, GET /tasks con selector de scope
    │   ├── notifications.py             # NUEVO: Blueprint /notifications (GET /, POST /<id>/read, POST /read-all)
    │   ├── categories.py                # Blueprint de categorías
    │   └── decorators.py                # Decorador @login_required
    │
    ├── templates/                       # Capa 4A: Presentación Jinja2 con CSRF
    │   ├── base.html                    # ACTUALIZADO: Indicador de notificaciones (contador) en navbar
    │   ├── notifications/
    │   │   └── index.html               # NUEVO: Bandeja de notificaciones históricas y acciones de lectura
    │   └── tasks/
    │       ├── index.html               # ACTUALIZADO: Filtro de procedencia (scope) e insignias creador/asignado
    │       ├── new.html                 # ACTUALIZADO: Campo de asignación opcional de usuario
    │       └── edit.html                # ACTUALIZADO: Formulario para reasignar o desasignar tarea
    │
    └── static/                          # Capa 4B: Recursos estáticos
        ├── css/styles.css               # Estilos para badges de procedencia y badge numérico del navbar
        └── js/main.js                   # Inyección de X-CSRFToken en peticiones fetch

migrations/                              # Scripts versionados de Alembic / Flask-Migrate
├── versions/
│   ├── xxxx_initial_schema.py           # Incremento 1
│   ├── yyyy_add_soft_delete_and_reset.py# Incremento 2
│   ├── zzzz_add_categories_and_task_priority.py # Incremento 3
│   └── aaaa_add_task_assignee_and_notifications.py # NUEVO: assignee_id en tasks y tabla notifications

tests/
├── conftest.py                          # Fixtures compartidas
├── unit/                                # Pruebas unitarias de dominio (TDD bloqueante)
│   ├── test_task_service.py             # EXTENDIDO: Pruebas de asignación, scope y rechazo de usuario inexistente
│   ├── test_notification_service.py     # NUEVO: Pruebas de atomicidad, auto-asignación y persistencia de lectura
│   ├── test_category_service.py
│   ├── test_auth_service.py
│   └── test_audit_service.py
└── integration/                         # Pruebas de integración HTTP y contratos
    ├── test_collaboration_routes.py     # NUEVO: Pruebas de POST /tasks/<id>/assign y filtros con CSRF
    └── test_notification_routes.py      # NUEVO: Pruebas de GET /notifications y POST /read con CSRF
```

**Structure Decision**: Se mantiene la arquitectura monolítica en el módulo unificado `src/taskcontrol/`.

---

## Estrategia de Implementación Detallada por Capas

### 1. Extensión del Modelo `Task`: Separación entre Creador y Asignatario (Punto 1 del Requerimiento)

#### Decisión: Campos Separados
El modelo `Task` (`src/taskcontrol/models/task.py`) mantiene `user_id` como identificador del creador y agrega una nueva columna `assignee_id`:

```python
class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    
    # 1. CREADOR Y PROPIETARIO LEGÍTIMO (Obligatorio, inmutable durante asignaciones):
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 2. ASIGNATARIO / RESPONSABLE OPERATIVO (Opcional, nullable):
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)
    priority = db.Column(db.String(20), default='medium', server_default='medium', nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True, index=True)
    is_deleted = db.Column(db.Boolean, default=False, server_default='0', nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # RELACIONES ORM DIFERENCIADAS:
    creator = db.relationship('User', foreign_keys=[user_id], backref=db.backref('created_tasks', lazy='dynamic'))
    assignee = db.relationship('User', foreign_keys=[assignee_id], backref=db.backref('assigned_tasks', lazy='dynamic'))
    category = db.relationship('Category', backref=db.backref('tasks', lazy='dynamic', passive_deletes=True))

    __table_args__ = (
        db.Index('ix_tasks_user_id_is_deleted', 'user_id', 'is_deleted'),
        db.Index('ix_tasks_assignee_id_is_deleted', 'assignee_id', 'is_deleted'),
        db.Index('ix_tasks_user_id_priority', 'user_id', 'priority'),
    )
```

#### Justificación frente a Reinterpretar `user_id`:
1. **Pérdida de Gobernanza y Propiedad**: Si `user_id` se sobrescribiera con el asignatario, el creador perdería la titularidad de su tarea. No sería posible saber quién originó el trabajo ni quién tiene autoridad para editarla estructuralmente, reasignarla o borrarla.
2. **Desasignación y Borrado de Cuentas**: Si una tarea asignada queda sin responsable (`assignee_id = null`), `user_id` garantiza que la tarea nunca quede huérfana. Si la cuenta del usuario asignado se elimina, `ON DELETE SET NULL` desasigna la tarea pero el creador conserva su tarea intacta.
3. **Compatibilidad hacia Atrás (Principio VI)**: Mantener `user_id` permite que todas las migraciones, consultas existentes y registros de auditoría de los Incrementos 1, 2 y 3 permanezcan 100% válidos sin necesidad de reescribir consultas históricas.

#### Matriz de Permisos de Colaboración (`FR-018`):
En cumplimiento estricto del Principio VII (Seguridad por defecto) y de las clarificaciones acordadas:
- **Usuario Creador (`task.user_id == actor_id`)**: Control absoluto sobre la tarea. Puede verla en `/tasks` permanentemente (con badge de asignación), modificar título/descripción/fecha límite (`/tasks/<id>/edit`), cambiar prioridad (`/tasks/<id>/priority`), asignar/remover categoría (`/tasks/<id>/category`), reasignar o desasignar (`/tasks/<id>/assign`), y eliminarla lógicamente (`/tasks/<id>/delete`).
- **Usuario Asignatario (`task.assignee_id == actor_id` y `task.user_id != actor_id`)**: Permisos estrictamente acotados a la operación de la tarea. **Únicamente puede ver la tarea y cambiar su estado** (`pending`, `in_progress`, `completed` vía `/tasks/<id>/status`). Cualquier intento por parte del asignatario de editar contenido, alterar prioridad, cambiar categoría, reasignar, desasignar o eliminar la tarea es bloqueado categóricamente por la capa de servicios lanzando `TaskAccessDeniedError` (HTTP `403 Forbidden`).

---

### 2. Modelo de Datos de `Notification` (Punto 2 del Requerimiento)

La nueva entidad `Notification` (`src/taskcontrol/models/notification.py`) se modela con los atributos esenciales y preservación histórica:

```python
from datetime import datetime, timezone
from src.taskcontrol.extensions import db

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    # Usuario receptor/destinatario de la alerta:
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    # Tarea objeto de la notificación (nullable con SET NULL para preservar historial si la tarea se elimina):
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True, index=True)
    
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False, server_default='0', nullable=False)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relaciones:
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic', cascade='all, delete-orphan'))
    task = db.relationship('Task', backref=db.backref('notifications', lazy='dynamic'))

    __table_args__ = (
        db.Index('ix_notifications_user_id_is_read', 'user_id', 'is_read'),
    )
```

- **Pertenencia**: Pertenece estrictamente al destinatario (`user_id`).
- **Estado de lectura**: Inicialmente `is_read = False`. Al leerse, `is_read = True` y `read_at = utcnow()`.
- **Persistencia e Integridad ante Eliminación de Tareas**: La notificación **permanece en la base de datos tras ser leída** y también **persiste si la tarea referenciada es eliminada lógicamente** (`is_deleted=True`) o físicamente (`task_id` pasa a `NULL` mediante `ON DELETE SET NULL`). Si el usuario hace clic en una notificación cuya tarea asociada fue eliminada, el sistema informa con un mensaje descriptivo que la tarea ya no está disponible, sin eliminar la notificación de su bandeja histórica.

---

### 3. Contrato de los Nuevos Endpoints y Extensión del Listado (Punto 3 del Requerimiento)

#### 3.1 Asignar / Reasignar Tarea: `POST /tasks/<int:task_id>/assign`
- **Controlador**: `src/taskcontrol/blueprints/tasks.py` delegando en `TaskService.assign_task(actor_id, task_id, assignee_email)`.
- **Seguridad**: `@login_required` + protección CSRF.
- **Payload**: `{ "assignee_email": "colaborador@empresa.com", "csrf_token": "..." }` (o vacío/null para desasignar). En interfaz web se implementa mediante un campo de texto libre `<input type="email" name="assignee_email">` sin autocompletado ni selectores para evitar la enumeración de usuarios (Principio VII).
- **Validaciones**:
  - Tarea existe y no está eliminada (`is_deleted == False`).
  - **Autorización estricta (`FR-018`)**: El actor en sesión DEBE ser exclusivamente el creador original (`task.user_id == actor_id`). Los asignatarios no tienen permitido reasignar ni desasignar tareas (HTTP 403 `FORBIDDEN`).
  - Validación de correo en backend: si no está vacío, busca usuario en `User` (`.strip().lower()`). Si no existe, rechaza de inmediato (HTTP 400 `USER_NOT_FOUND`).
- **Respuesta**: `302 Found` (web) con flash `"Tarea asignada exitosamente a ..."` o `200 OK` JSON.

#### 3.2 Listar Notificaciones: `GET /notifications`
- **Controlador**: `src/taskcontrol/blueprints/notifications.py` delegando en `NotificationService.get_user_notifications(user_id, status_filter)`.
- **Seguridad**: `@login_required`.
- **Respuesta**:
  - Web: Renderiza `notifications/index.html` con listado ordenado por `created_at DESC` y contador no leído.
  - JSON: `200 OK` con `{ "status": "success", "data": { "notifications": [...], "unread_count": N, "total": M } }`.

#### 3.3 Marcar Notificación como Leída: `POST /notifications/<int:notification_id>/read`
- **Controlador**: `src/taskcontrol/blueprints/notifications.py` delegando en `NotificationService.mark_as_read(user_id, notification_id)`.
- **Seguridad**: `@login_required` + token CSRF.
- **Regla**: Valida propiedad. Establece `is_read=True` y `read_at=utcnow()`. Persiste en BD.
- **Respuesta**: `302 Found` o `200 OK` JSON.

#### 3.4 Marcar Todas como Leídas: `POST /notifications/read-all`
- **Controlador**: Delega en `NotificationService.mark_all_as_read(user_id)`.
- **Seguridad**: `@login_required` + token CSRF.
- **Respuesta**: `302 Found` o `200 OK` JSON.

#### 3.5 Extensión del Endpoint de Listado: `GET /tasks`
- **Nuevo Parámetro Query**: `scope`:
  - `'all'` (defecto): Muestra todas las tareas activas donde el usuario es el creador O el asignatario.
  - `'created'`: Muestra únicamente tareas creadas por el usuario actual (`creator_id == current_user.id`).
  - `'assigned'`: Muestra únicamente tareas donde el usuario es el asignatario y no el creador (`assignee_id == current_user.id AND creator_id != current_user.id`).
- **Implementación en `TaskService.get_user_tasks`**:
  ```python
  def get_user_tasks(user_id: int, status: str = 'all', sort_by: str = 'created_desc', 
                     category_id: str | int = 'all', scope: str = 'all'):
      query = Task.query.filter(Task.is_deleted == False)

      # 1. Filtro de procedencia (scope)
      if scope == 'created':
          query = query.filter(Task.user_id == user_id)
      elif scope == 'assigned':
          query = query.filter(Task.assignee_id == user_id, Task.user_id != user_id)
      else:  # 'all'
          query = query.filter(db.or_(Task.user_id == user_id, Task.assignee_id == user_id))

      # 2. Filtro por estado existente (Incremento 1)
      if status != 'all':
          query = query.filter(Task.status == status)

      # 3. Filtro por categoría existente (Incremento 3)
      if str(category_id) == 'none':
          query = query.filter(Task.category_id.is_(None))
      elif str(category_id) != 'all':
          query = query.filter(Task.category_id == int(category_id))

      # 4. Ordenamiento ortogonal (Incremento 3)
      if sort_by == 'priority':
          priority_weight = db.case({'high': 3, 'medium': 2, 'low': 1}, value=Task.priority, else_=0)
          query = query.order_by(priority_weight.desc(), Task.created_at.desc())
      else:
          query = query.order_by(Task.created_at.desc())

      return query.all()
  ```
- **Distinción Visual en Interfaz**:
  - En la plantilla `tasks/index.html`, cada tarjeta renderiza:
    - Si `task.user_id == current_user.id`: Badge `Creada por mí` (y si `task.assignee`, añade `(Asignada a: task.assignee.email)`).
    - Si `task.assignee_id == current_user.id and task.user_id != current_user.id`: Badge destacado `Asignada a mí por task.creator.email`.

---

### 4. Punto y Atomicidad de Creación de la Notificación (Punto 4 del Requerimiento)

La creación de la notificación se realiza **dentro del mismo servicio de asignación (`TaskService.assign_task`) y en la misma transacción relacional de base de datos**, notificando a ambas partes cuando corresponda:

```python
def assign_task(actor_id: int, task_id: int, assignee_email: str | None) -> Task:
    task = Task.query.filter_by(id=task_id, is_deleted=False).first()
    if not task:
        raise TaskNotFoundError("Tarea no encontrada.")
    if task.user_id != actor_id:
        raise TaskAccessDeniedError("Solo el creador original de la tarea tiene permisos para asignar o reasignar.")

    previous_assignee_id = task.assignee_id
    new_assignee = None

    if assignee_email and assignee_email.strip():
        clean_email = assignee_email.strip().lower()
        new_assignee = User.query.filter_by(email=clean_email).first()
        if not new_assignee:
            raise UserNotFoundError("El correo especificado no pertenece a ningún usuario registrado en el sistema.")
        new_assignee_id = new_assignee.id
    else:
        new_assignee_id = None

    # Si no hubo cambio en el asignatario, retorna sin mutaciones redundantes
    if previous_assignee_id == new_assignee_id:
        return task

    # 1. Actualiza la entidad Task
    task.assignee_id = new_assignee_id

    # 2. Genera notificaciones internas inmediatas (sin auto-alerta):
    actor = User.query.get(actor_id)
    
    # 2a. Notificación al nuevo asignatario (si no es auto-asignación):
    if new_assignee_id is not None and new_assignee_id != actor_id:
        notification_new = Notification(
            user_id=new_assignee_id,
            task_id=task.id,
            title="Nueva tarea asignada",
            message=f"El usuario {actor.email} te ha asignado la tarea '{task.title}'."
        )
        db.session.add(notification_new)

    # 2b. Notificación al asignatario previo (si existía, no es el actor y es distinto al nuevo asignatario):
    if previous_assignee_id is not None and previous_assignee_id != actor_id and previous_assignee_id != new_assignee_id:
        revocation_msg = (
            f"El usuario {actor.email} ha reasignado la tarea '{task.title}' a otro colaborador."
            if new_assignee_id else
            f"El usuario {actor.email} ha retirado tu asignación de la tarea '{task.title}'."
        )
        notification_prev = Notification(
            user_id=previous_assignee_id,
            task_id=task.id,
            title="Asignación de tarea retirada",
            message=revocation_msg
        )
        db.session.add(notification_prev)

    # 3. Registra auditoría inmutable
    action = 'TASK_ASSIGNED' if new_assignee_id else 'TASK_UNASSIGNED'
    audit_service.record_task_event(
        actor_id=actor_id,
        action=action,
        task_id=task.id,
        details={
            'previous_assignee_id': previous_assignee_id,
            'new_assignee_id': new_assignee_id,
            'assignee_email': new_assignee.email if new_assignee else None
        }
    )

    # 4. Transacción atómica única
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return task
```

- **Garantía de Atomicidad**: La asignación de la tarea, la inserción de la notificación en `notifications` y el registro en `audit_logs` ocurren bajo la misma unidad de trabajo (`db.session.commit()`). Si cualquiera de ellos falla, se revierte la transacción completa (`rollback()`), eliminando el riesgo de "notificaciones huérfanas" o "asignaciones no notificadas".

---

### 5. Validación en Backend de Existencia del Asignatario (Principio VII) (Punto 5 del Requerimiento)

- **Regla Estricta**: No se confía jamás en listas o selectores del cliente web.
- **Implementación**:
  1. `assignee_email` se somete a normalización estricta (`.strip().lower()`).
  2. Se realiza consulta directa a la base de datos: `User.query.filter_by(email=clean_email).first()`.
  3. Si la consulta devuelve `None`, se interrumpe inmediatamente el flujo lanzando `UserNotFoundError`.
  4. Ninguna fila es modificada ni insertada.
  5. La capa HTTP traduce la excepción en:
     - En interfaz web: Mensaje flash de error `flash("El correo especificado no pertenece a ningún usuario registrado en el sistema.", "error")` y redirección inmediata a `/tasks`.
     - En API JSON: Código HTTP `400 Bad Request` con payload determinista:
       ```json
       {
         "status": "error",
         "code": "USER_NOT_FOUND",
         "message": "El correo especificado no pertenece a ningún usuario registrado en el sistema."
       }
       ```

---

### 6. Migraciones de Esquema (Principio VI) (Punto 6 del Requerimiento)

Script de migración versionado en Flask-Migrate: `migrations/versions/aaaa_add_task_assignee_and_notifications.py`:

```python
def upgrade():
    # 1. Agregar columna assignee_id nullable a tasks
    op.add_column('tasks', sa.Column('assignee_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_tasks_assignee_id_users',
        'tasks', 'users',
        ['assignee_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_tasks_assignee_id', 'tasks', ['assignee_id'])
    op.create_index('ix_tasks_assignee_id_is_deleted', 'tasks', ['assignee_id', 'is_deleted'])

    # 2. Crear tabla notifications con task_id nullable y ON DELETE SET NULL
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('message', sa.String(length=500), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_task_id', 'notifications', ['task_id'])
    op.create_index('ix_notifications_user_id_is_read', 'notifications', ['user_id', 'is_read'])

def downgrade():
    op.drop_index('ix_notifications_user_id_is_read', table_name='notifications')
    op.drop_index('ix_notifications_task_id', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('ix_tasks_assignee_id_is_deleted', table_name='tasks')
    op.drop_index('ix_tasks_assignee_id', table_name='tasks')
    op.drop_constraint('fk_tasks_assignee_id_users', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'assignee_id')
```

- **Preservación de Datos Existentes**: Como `assignee_id` es nullable y no impone restricciones restrictivas iniciales, todas las tareas preexistentes creadas en los Incrementos 1, 2 y 3 quedan con `assignee_id = NULL`. Todas las tareas se mantienen activas y sin pérdida de datos.

---

### 7. Pruebas Automatizadas Bloqueantes (Principio IV) (Punto 7 del Requerimiento)

Conforme al Principio IV (TDD bloqueante), las siguientes pruebas se implementarán en rojo antes de codificar la lógica de negocio:

#### 7.1 Pruebas de Asignación, Permisos y Notificaciones Duales (`tests/unit/test_task_service.py`)
1. **`test_assign_task_creates_exactly_one_notification_for_assignee`**:
   - Asignar una tarea de Usuario 1 a Usuario 2 crea exactamente una fila en `notifications` donde `user_id == usuario_2.id` y `is_read == False`.
2. **`test_self_assignment_does_not_create_notification`**:
   - Usuario 1 asignándose la tarea a sí mismo actualiza `assignee_id`, pero no inserta ninguna fila en `notifications`.
3. **`test_assign_task_to_nonexistent_user_raises_error_and_does_not_mutate`**:
   - Intentar asignar a `"no_existe@empresa.com"` lanza `UserNotFoundError`. La tarea mantiene su estado previo y no se emiten notificaciones ni logs falsos.
4. **`test_unassign_task_sets_assignee_id_to_null_and_notifies_previous_assignee`**:
   - Desasignar una tarea previamente asignada a Usuario 2 desvincula el asignatario (`assignee_id = None`), registra `TASK_UNASSIGNED`, y genera una notificación de revocación/desasignación para Usuario 2.
5. **`test_reassign_task_creates_notifications_for_both_new_and_previous_assignee`**:
   - Reasignar una tarea de Usuario 2 a Usuario 3 crea una notificación de nueva asignación para Usuario 3 Y una notificación de desasignación/revocación para Usuario 2.
6. **`test_assignee_cannot_reassign_nor_unassign_task` (`FR-018`)**:
   - Un asignatario que intenta reasignar la tarea a otro usuario o desasignarla es bloqueado con `TaskAccessDeniedError` (HTTP 403 Forbidden).
7. **`test_assignee_cannot_edit_nor_delete_task` (`FR-018`)**:
   - Un asignatario que intenta editar título/descripción/fecha, cambiar prioridad, categoría o eliminar la tarea recibe `TaskAccessDeniedError`.
8. **`test_assignee_can_change_task_status` (`FR-018`)**:
   - El asignatario puede cambiar válidamente el estado de la tarea asignada (`pending` → `in_progress` → `completed`).

#### 7.2 Pruebas de Listado y Procedencia (`tests/unit/test_task_service.py`)
9. **`test_assigned_task_appears_in_assignee_tasks_list`**:
   - La tarea asignada a Usuario 2 por Usuario 1 aparece en `get_user_tasks(usuario_2.id, scope='all')`.
10. **`test_creator_continues_to_see_assigned_task`**:
    - El creador (Usuario 1) continúa viendo la tarea asignada en su listado `get_user_tasks(usuario_1.id, scope='created')` y `scope='all'`.
11. **`test_scope_filter_created_and_assigned`**:
    - Con `scope='created'`, Usuario 2 solo ve tareas que él creó.
    - Con `scope='assigned'`, Usuario 2 solo ve tareas asignadas por otros.
12. **`test_soft_deleted_assigned_task_excluded_from_assignee_list`**:
    - Si el creador elimina lógicamente una tarea asignada, esta desaparece del listado de Usuario 2.

#### 7.3 Pruebas de Notificaciones y Lectura (`tests/unit/test_notification_service.py`)
13. **`test_mark_notification_as_read_persists_in_history`**:
    - Marcar como leída fija `is_read=True` y `read_at != None`, pero la fila permanece en la base de datos (conteo total inalterado).
14. **`test_mark_all_notifications_as_read`**:
    - Actualiza simultáneamente todas las notificaciones pendientes del usuario a leídas.
15. **`test_cannot_read_another_users_notification`**:
    - Intentar marcar como leída la notificación de otro usuario es rechazado con error de acceso o 404.
16. **`test_notifications_persist_when_task_is_soft_deleted`**:
    - Eliminar lógicamente una tarea no elimina sus notificaciones históricas asociadas en la tabla `notifications`.

---

## Complexity Tracking

| Solución Adoptada | Justificación frente al Principio V (Simplicidad) | Alternativas Más Complejas Rechazadas |
|---|---|---|
| **Separación `user_id` / `assignee_id` en `tasks`** | Añade una sola columna foránea opcional a la tabla existente. Resuelve el 100% de los requisitos de colaboración sin alterar la lógica de propiedad ni requerir tablas intermedias. | 1. Reinterpretar `user_id` (destruye la auditoría del creador).<br>2. Tabla relacional `task_assignments` con historial y asignaciones múltiples (abstracción prematura innecesaria para asignación 1:1). |
| **Notificaciones como tabla relacional consultada al cargar** | Máxima simplicidad monolítica. El contador de notificaciones no leídas se consulta en la renderización del servidor con un índice `ix_notifications_user_id_is_read` en < 2 ms. | 1. Servidores WebSockets o SSE (Server-Sent Events) para tiempo real (complejidad operativa innecesaria para un monolito académico).<br>2. Servicios externos de mensajería (RabbitMQ, Redis Streams) prohibidos expresamente por el Principio I. |
| **Atomicidad en `TaskService` en la misma transacción** | Ejecutar la inserción de notificación y la asignación en la misma transacción (`db.session.commit()`) garantiza consistencia absoluta sin requerir patrones complejos como Outbox o Event Bus. | 1. Arquitectura de eventos asíncronos con Celery / colas (rompe el monolito y añade puntos de falla).<br>2. Transacciones distribuidas en dos fases (2PC). |
