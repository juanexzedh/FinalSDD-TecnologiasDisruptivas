# Implementation Plan: Cierre de Gestión Básica de Tareas y Recuperación de Acceso

**Branch**: `002-task-lifecycle-recovery` | **Date**: 2026-10-07 | **Spec**: [spec.md](file:///C:/Users/Kreilt/Downloads/SDD-Tecnologias-Disruptivas-main/specs/002-task-lifecycle-recovery/spec.md)

**Input**: Especificación funcional desde `specs/002-task-lifecycle-recovery/spec.md` (cubre HU-05, HU-06 y HU-14 del backlog, asumiendo el Incremento 1 implementado y operativo).

---

## Summary

Implementar el segundo incremento funcional de TaskControl completando el ciclo de vida del dominio de tareas y agregando recuperación segura de acceso, manteniendo la arquitectura monolítica en 4 capas y el cumplimiento estricto de la constitución:
1. **Eliminación lógica de tareas (HU-05)**: Extensión del modelo `Task` con banderas de borrado lógico (`is_deleted`, `deleted_at`) que preservan los registros en persistencia e historial (Principio VI), excluyéndolas por defecto del listado regular (HU-02) e impidiendo mutaciones subsiguientes sobre tareas eliminadas. La eliminación es definitiva e irreversible para el usuario final (sin papelera de reciclaje ni opción de restaurar en este incremento).
2. **Reapertura controlada de tareas (HU-06)**: Habilitación de la transición determinista `completed -> pending` en la máquina de estados mediante un servicio y endpoint específico `reopen_task`, auditada bajo el evento unívoco `TASK_REOPENED` para distinguirla formalmente de la creación original y de cambios ordinarios de estado (Principio VIII).
3. **Recuperación segura de contraseñas (HU-14)**: Flujo de autoservicio con respuesta ciega (blind response) para prevenir enumeración de correos (Principio VII), generación de tokens criptográficos de un solo uso con ventana estricta de 15 minutos, almacenamiento exclusivo del hash SHA-256 de los tokens en BD, invalidación automática de tokens previos no utilizados al solicitar uno nuevo (solo el enlace más reciente es utilizable), estrangulamiento silencioso (*silent throttling* a un máximo de 3 solicitudes por correo cada 15 minutos) contra ataques de saturación de correo, e invalidación inmediata tras su consumo.
4. **Revocación global de sesiones activas (Principio VII)**: Al completar exitosamente el restablecimiento de contraseña, el sistema invalida de forma inmediata y global todas las sesiones previas del usuario en todos los dispositivos y navegadores mediante control de versión de sesión (`session_version`), forzando un nuevo inicio de sesión.
5. **Despacho local de correos**: Emulación mediante `ConsoleEmailSender` que emite los enlaces de restablecimiento directamente en consola/log estructurado, garantizando autonomía total para desarrollo y evaluación académica sin dependencias externas (Principio V).
6. **Migraciones e Integridad**: Script incremental con Flask-Migrate con valores por defecto que preservan intactos los datos del Incremento 1 (Principio VI).
7. **Desarrollo Test-First (TDD)**: Suite de pruebas unitarias bloqueantes para la lógica de dominio en `tests/unit/` antes de implementar el código de servicio (Principio IV).

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flask 3.x, Flask-SQLAlchemy 3.x, Flask-Migrate (Alembic), Flask-WTF 1.2+ (`CSRFProtect`), python-dotenv 1.0+, Werkzeug 3.x, Jinja2  
**Storage**: Base de datos relacional gestionada vía SQLAlchemy ORM (SQLite local para desarrollo/pruebas; compatible con PostgreSQL)  
**Testing**: `pytest`, `pytest-cov` (ejecución de pruebas unitarias con SQLite en memoria `:memory:`)  
**Target Platform**: Servidor web monolítico ejecutable localmente en Windows y Linux  
**Project Type**: Aplicación web monolítica con renderizado en servidor Jinja2 y JavaScript vanilla auxiliar  
**Performance Goals**: Tiempo de respuesta menor a 100 ms para operaciones de tareas y solicitud de recuperación  
**Constraints**:
- Cumplimiento innegociable de los 8 principios de la constitución del proyecto.
- Cero eliminación física de tareas; soft delete mandatorio para preservar log de auditoría (Principio VI).
- Toda transición de estado y reapertura debe registrarse en `audit_logs` con acción explícita (Principio VIII).
- Protección CSRF mandatoria en todos los nuevos endpoints POST (Principio VII).
- Cero secretos o tokens en texto plano en el repositorio o en la base de datos; hash SHA-256 para tokens de reset y `scrypt` para contraseñas (Principio VII).
- Respuestas ciegas e indistinguibles en recuperación de contraseña para evitar filtración de usuarios registrados (Principio VII).
- TDD bloqueante para toda regla de negocio nueva (Principio IV).
- Despacho de correo emulado en consola para desarrollo sin servicios externos pesados (Principio V e I).
- Arranque y migraciones estandarizados desde la raíz (`flask db upgrade`, `flask run`) gobernados por `FLASK_APP` (Restricción 5).  
**Scale/Scope**: Limitado estrictamente a HU-05, HU-06 y HU-14. Quedan fuera de alcance HU-07 a HU-11 y HU-15 a HU-16.

---

## Constitution Check

*GATE: Evaluación técnica previa y posterior al diseño contra la constitución de TaskControl.*

| Principio | Estado | Justificación y Cumplimiento en el Plan |
|---|---|---|
| **I. Monolito por diseño** | **PASS** | El sistema continúa ejecutándose en un único proceso desplegable con una única base de datos relacional. El despacho de correo en desarrollo se integra dentro del mismo proceso monolítico vía logging de consola (`ConsoleEmailSender`), sin requerir colas de mensajería asíncronas (Celery, RabbitMQ) ni servicios externos. |
| **II. Separación en capas** | **PASS** | Estricta adherencia a las 4 capas: Modelos (`Task`, `PasswordResetToken`), Servicios (`TaskService`, `AuthService`, `RecoveryService`, `EmailService`), Blueprints (`tasks.py`, `auth.py`) y Presentación (Jinja2/JS). La lógica de expiración de tokens, filtrado de tareas eliminadas y transiciones de reapertura reside exclusivamente en la capa de servicios. |
| **III. Contrato explícito backend-JS** | **PASS** | Todos los nuevos endpoints (`/tasks/<id>/delete`, `/tasks/<id>/reopen`, `/forgot-password`, `/reset-password/<token>`) cuentan con contratos exhaustivos en [contracts/task-lifecycle-contracts.md](file:///C:/Users/Kreilt/Downloads/SDD-Tecnologias-Disruptivas-main/specs/002-task-lifecycle-recovery/contracts/task-lifecycle-contracts.md) y [contracts/recovery-contracts.md](file:///C:/Users/Kreilt/Downloads/SDD-Tecnologias-Disruptivas-main/specs/002-task-lifecycle-recovery/contracts/recovery-contracts.md), especificando métodos, payloads, tokens CSRF y catálogo de códigos 2xx/4xx. |
| **IV. Test-first en lógica de negocio** | **PASS** | TDD mandatorio y bloqueante: las pruebas unitarias que validan que una tarea eliminada no aparece en el listado, que no se puede eliminar dos veces, que la reapertura emite `TASK_REOPENED`, y que tokens expirados o usados son rechazados deben implementarse en rojo (Red) antes de codificar los servicios. |
| **V. Simplicidad sobre generalidad prematura** | **PASS** | Filosofía YAGNI: (1) Soft delete implementado con dos columnas nativas (`is_deleted`, `deleted_at`) y filtrado explícito en consultas, sin plugins complejos de ORM. (2) Entrega de correos en desarrollo emulada con logger de consola, evitando la sobreingeniería de configurar servidores SMTP o APIs externas de terceros. (3) Tokens de reset hasheados con SHA-256 nativo sin sistemas de bóvedas externas. |
| **VI. Integridad de datos y migraciones** | **PASS** | La eliminación de tareas es estrictamente lógica (soft delete), protegiendo la integridad referencial y preservando el historial completo de auditoría. Los cambios en el esquema se aplican mediante un script de migración versionado en Flask-Migrate con `server_default='0'`, garantizando que las tareas existentes del Incremento 1 no se alteren ni se pierdan. |
| **VII. Seguridad por defecto** | **PASS** | (1) Mitigación de enumeración de cuentas mediante respuesta ciega (blind response) con mensaje y tiempo de respuesta idénticos. (2) Tokens efímeros (15 min) de alta entropía almacenados exclusivamente mediante hash SHA-256 en BD. (3) Invalidación irreversible tras uso único e invalidación automática de tokens previos por nueva solicitud (solo el último enlace es utilizable). (4) Estrangulamiento silencioso (silent throttling, máx. 3 solicitudes por correo cada 15 min) contra ataques de saturación. (5) Revocación inmediata y global de todas las sesiones activas del usuario en todos los navegadores/dispositivos tras el cambio de clave. (6) Validación estricta de complejidad de contraseñas y hashing con `scrypt`. (7) Protección CSRF obligatoria en todos los métodos POST. |
| **VIII. Observabilidad mínima viable** | **PASS** | Ampliación del catálogo de auditoría en `audit_logs`: eventos inmutables `TASK_DELETED`, `TASK_REOPENED` (con metadatos de estado previo y posterior) y `PASSWORD_RESET_COMPLETED`, emitidos de forma consistente a nivel de servicio y reflejados en el log estructurado JSON. |

---

## Project Structure

### Documentation (este incremento)

```text
specs/002-task-lifecycle-recovery/
├── spec.md                              # Especificación funcional validada y aprobada
├── plan.md                              # Este plan técnico de implementación
├── research.md                          # Decisiones técnicas y justificaciones del Principio V
├── data-model.md                        # Modelo relacional ampliado y máquina de estados
├── quickstart.md                        # Guía de inicialización y escenarios de validación extremo a extremo
├── checklists/
│   └── requirements.md                  # Checklist de calidad de requerimientos
└── contracts/                           # Contratos HTTP explícitos (Principio III)
    ├── task-lifecycle-contracts.md      # Contratos para POST /tasks/<id>/delete y /reopen (HU-05, HU-06)
    └── recovery-contracts.md            # Contratos para /forgot-password y /reset-password (HU-14)
```

### Source Code (Repositorio Monolítico)

```text
src/
└── taskcontrol/
    ├── __init__.py                      # Application Factory (registro de modelos, blueprints y CSRF)
    ├── config.py                        # Configuración por entornos (DevelopmentConfig con ConsoleEmailSender)
    ├── extensions.py                    # Instancias de SQLAlchemy, Flask-Migrate y CSRFProtect
    │
    ├── models/                          # Capa 1: Persistencia relacional
    │   ├── __init__.py
    │   ├── user.py                      # Modelo User EXTENDIDO con session_version para revocación global de sesiones
    │   ├── task.py                      # Modelo Task EXTENDIDO con is_deleted, deleted_at e índice compuesto
    │   ├── password_reset_token.py      # Modelo NUEVO PasswordResetToken (user_id, token_hash, expires_at, used_at)
    │   └── audit_log.py                 # Modelo AuditLog (soporta TASK_DELETED, TASK_REOPENED, PASSWORD_RESET_COMPLETED)
    │
    ├── services/                        # Capa 2: Lógica de negocio y dominio (TDD bloqueante)
    │   ├── __init__.py
    │   ├── auth_service.py              # Registro, autenticación y hash scrypt
    │   ├── task_service.py              # EXTENDIDO con delete_task() irreversible, reopen_task() a pending y filtro is_deleted=False
    │   ├── recovery_service.py          # NUEVO: generación de tokens (15 min), silent throttling, invalidación previa, revocación de sesión y reseteo
    │   ├── email_service.py             # NUEVO: abstracción EmailSender y ConsoleEmailSender para entorno local
    │   └── audit_service.py             # Registro centralizado de auditoría y emisión de logs JSON
    │
    ├── blueprints/                      # Capa 3: Controladores HTTP y protección CSRF
    │   ├── __init__.py
    │   ├── auth.py                      # EXTENDIDO con rutas /forgot-password y /reset-password/<token>, asignando session_version en login
    │   ├── tasks.py                     # EXTENDIDO con rutas POST /tasks/<id>/delete y POST /tasks/<id>/reopen
    │   └── decorators.py                # Decorador @login_required validando sesión activa y coincidencia de session_version
    │
    ├── templates/                       # Capa 4A: Presentación Jinja2 con CSRF
    │   ├── base.html                    # Layout base con navbar y meta csrf-token
    │   ├── auth/
    │   │   ├── login.html
    │   │   ├── register.html
    │   │   ├── forgot_password.html     # NUEVO: Formulario de solicitud de recuperación
    │   │   └── reset_password.html      # NUEVO: Formulario de ingreso de nueva contraseña
    │   └── tasks/
    │       ├── index.html               # ACTUALIZADO: Botones de eliminación y reapertura con formularios POST/CSRF
    │       ├── new.html
    │       └── edit.html
    │
    └── static/                          # Capa 4B: Recursos estáticos
        ├── css/styles.css
        └── js/main.js                   # JavaScript vanilla auxiliar para confirmación y envío con X-CSRFToken

migrations/                              # Scripts versionados de Alembic
├── versions/
│   ├── xxxx_initial_schema.py           # Migración del Incremento 1 (users, tasks, audit_logs)
│   └── yyyy_add_soft_delete_and_reset.py# Migración NUEVA (is_deleted, deleted_at, session_version en users, password_reset_tokens)

tests/
├── conftest.py                          # Fixtures compartidas actualizadas
├── unit/                                # Pruebas unitarias de dominio (TDD bloqueante)
│   ├── test_auth_service.py
│   ├── test_task_service.py             # Pruebas de soft delete irreversible, exclusión en listado y reapertura a pending
│   ├── test_recovery_service.py         # NUEVO: Pruebas de tokens, blind response, silent throttling, revocación de sesión, expiración y reuso
│   └── test_audit_service.py            # Pruebas de eventos TASK_DELETED, TASK_REOPENED, PASSWORD_RESET_COMPLETED
└── integration/                         # Pruebas de integración HTTP y contratos
    ├── test_auth_routes.py              # Pruebas de rutas de forgot-password, reset-password y expiración de sesiones
    └── test_task_routes.py              # Pruebas de endpoints /delete y /reopen con CSRF
```

---

## Estrategia de Implementación por Capas

### 1. Capa de Modelos y Datos (`models/`)
- **`User` (`src/taskcontrol/models/user.py`)**:
  - Incorporar columna de control de versión de sesión:
    ```python
    session_version = db.Column(db.Integer, default=1, server_default='1', nullable=False)
    ```
  - Permite la revocación global e inmediata de todas las sesiones activas en cualquier navegador/dispositivo tras actualizar la contraseña (Principio VII).
- **`Task` (`src/taskcontrol/models/task.py`)**:
  - Incorporar columnas de borrado lógico (definitivo e irreversible para el usuario final):
    ```python
    is_deleted = db.Column(db.Boolean, default=False, server_default='0', nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ```
  - Definir índice compuesto:
    ```python
    __table_args__ = (
        db.Index('ix_tasks_user_id_is_deleted', 'user_id', 'is_deleted'),
    )
    ```
- **`PasswordResetToken` (`src/taskcontrol/models/password_reset_token.py`)**:
  - Definición de tabla `password_reset_tokens`:
    ```python
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    ```

### 2. Capa de Servicios (`services/`) — TDD Bloqueante
- **`TaskService`**:
  - `get_user_tasks(user_id, status_filter='all')`: Modifica la consulta para aplicar incondicionalmente `Task.is_deleted == False`. Excluye tareas eliminadas de cualquier listado o filtro por estado sin romper clientes existentes.
  - `delete_task(user_id, task_id)`:
    1. Obtiene la tarea verificando `user_id`. Si no existe, lanza `TaskNotFoundError`.
    2. Si `task.is_deleted == True`, lanza `TaskAlreadyDeletedError`.
    3. Fija `task.is_deleted = True` y `task.deleted_at = datetime.now(timezone.utc)` (acción irreversible para el usuario final; sin opción de restauración).
    4. Invoca `AuditService.record_task_event(actor_id=user_id, action='TASK_DELETED', task_id=task.id)`.
  - `reopen_task(user_id, task_id)`:
    1. Obtiene la tarea verificando `user_id`. Si no existe, lanza `TaskNotFoundError`.
    2. Si `task.is_deleted == True`, lanza `TaskAlreadyDeletedError`.
    3. Si `task.status != 'completed'`, lanza `InvalidStateTransitionError` ("Solo tareas completadas pueden reabrirse").
    4. Actualiza `task.status = 'pending'` de forma determinista y unívoca (siempre retorna a estado "pendiente").
    5. Invoca `AuditService.record_task_event(actor_id=user_id, action='TASK_REOPENED', task_id=task.id, details={'previous_status': 'completed', 'new_status': 'pending'})`.
  - `update_task` y `change_task_status`: Aseguran que `task.is_deleted == False`; si está eliminada, rechazan la mutación.
- **`RecoveryService`**:
  - `request_password_reset(email)`:
    1. Normaliza correo (`email.strip().lower()`).
    2. Busca usuario. Si no existe, ejecuta operación dummy de tiempo equivalente y retorna sin error (blind response indistinguible).
    3. Si existe:
       a. **Silent Throttling**: Cuenta tokens emitidos para ese `user_id` en los últimos 15 minutos (`created_at >= utcnow() - timedelta(minutes=15)`). Si son $\ge 3$, retorna de inmediato sin generar nuevo token ni enviar correo (respuesta neutra idéntica contra abusos).
       b. **Invalidación de tokens previos**: Si está dentro del límite ($< 3$), invalida de inmediato cualquier token pendiente previo no usado de ese usuario (`used_at IS NULL, expires_at > utcnow()`), marcándolos como expirados (`expires_at = utcnow()`), garantizando que solo el enlace más reciente sea utilizable.
       c. **Generación del nuevo token**: Genera `raw_token = secrets.token_urlsafe(32)`, calcula `token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()`, guarda en `PasswordResetToken` con `expires_at = utcnow() + timedelta(minutes=15)`.
       d. Delega en `EmailService.send_password_reset_email(email, reset_url)`.
  - `verify_reset_token(raw_token)`:
    1. Calcula SHA-256 de `raw_token`.
    2. Busca en BD. Valida que exista, que `used_at IS NULL` y que `expires_at > utcnow()`.
    3. Si falla, lanza `InvalidTokenError`.
    4. Si es válido, retorna la entidad `PasswordResetToken` con su usuario asociado.
  - `reset_password(raw_token, new_password)`:
    1. Valida el token con `verify_reset_token`.
    2. Valida complejidad de contraseña ($\ge 8$ caracteres, letra y número).
    3. Genera hash `scrypt` y actualiza `user.password_hash`.
    4. **Revocación Global de Sesiones**: Incrementa `user.session_version += 1`, invalidando inmediatamente todas las sesiones previas del usuario en cualquier navegador/dispositivo.
    5. Marca `token.used_at = datetime.now(timezone.utc)`.
    6. Invoca `AuditService.record_user_event(actor_id=user.id, action='PASSWORD_RESET_COMPLETED', user_id=user.id)`.
- **`EmailService`**:
  - `ConsoleEmailSender`: En entornos de desarrollo/pruebas emite el mensaje formateado vía `logging.getLogger('taskcontrol.email')` conteniendo el enlace `http://127.0.0.1:5000/reset-password/<token>`. Cero configuración externa requerida.

### 3. Capa de Blueprints y Seguridad (`blueprints/`)
- **`tasks.py`**:
  - `POST /tasks/<int:task_id>/delete`: Requiere `@login_required` y token CSRF. Delega en `TaskService.delete_task`. Redirige a `/tasks` con flash.
  - `POST /tasks/<int:task_id>/reopen`: Requiere `@login_required` y token CSRF. Delega en `TaskService.reopen_task`. Redirige a `/tasks` con flash.
- **`auth.py`**:
  - `GET /forgot-password`: Muestra formulario de recuperación con `csrf_token()`.
  - `POST /forgot-password`: Requiere token CSRF. Delega en `RecoveryService.request_password_reset`. Redirige a `/login` con mensaje flash ciego/neutro.
  - `GET /reset-password/<token>`: Valida token. Si es inválido/expirado, redirige a `/forgot-password` con flash de error. Si es válido, muestra formulario de cambio de clave.
  - `POST /reset-password/<token>`: Requiere token CSRF. Delega en `RecoveryService.reset_password`. Si tiene éxito, redirige a `/login` con mensaje de éxito (forzando nuevo login con credencial actualizada). Si hay error de validación o expiración, muestra error correspondiente.
  - En `login()`: tras autenticar credenciales, persiste en sesión `session["user_id"] = user.id` y `session["session_version"] = user.session_version`.
- **`decorators.py` (`@login_required`)**:
  - Verifica sesión activa: comprueba `user_id` y valida que `session.get("session_version") == user.session_version`. Si la versión difiere o no existe, ejecuta `session.clear()` y redirige a login (o 401 JSON), asegurando la revocación global efectiva.

### 4. Capa de Presentación (`templates/` y `static/`)
- Formularios con inclusión obligatoria de `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- Vistas `auth/forgot_password.html` y `auth/reset_password.html` diseñadas con interfaz limpia y mensajes de retroalimentación semánticos.
- En `tasks/index.html`:
  - Botón "Eliminar" en cada tarjeta/fila de tarea activa que envía formulario POST a `/tasks/<id>/delete` con confirmación previa.
  - Botón "Reabrir Tarea" visible exclusivamente en tareas con estado `completed`, enviando POST a `/tasks/<id>/reopen`.

---

## Migraciones y Mantenimiento de Esquema (Principio VI)

1. **Generación del Script de Migración**:
   ```bash
   flask db migrate -m "add_soft_delete_and_password_reset"
   ```
2. **Operaciones del Script de Alembic**:
   - `op.add_column('users', sa.Column('session_version', sa.Integer(), server_default='1', nullable=False))`
   - `op.add_column('tasks', sa.Column('is_deleted', sa.Boolean(), server_default='0', nullable=False))`
   - `op.add_column('tasks', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))`
   - `op.create_index('ix_tasks_user_id_is_deleted', 'tasks', ['user_id', 'is_deleted'])`
   - `op.create_table('password_reset_tokens', ...)`
   - `op.create_index('ix_password_reset_tokens_token_hash', 'password_reset_tokens', ['token_hash'], unique=True)`
3. **Preservación de Datos Existentes**:
   - Gracias al `server_default='0'` en tareas y `server_default='1'` en usuarios, cualquier registro previo del Incremento 1 preserva su integridad y funcionamiento sin requerir intervención manual ni migraciones de datos intermedias.

---

## Pruebas Automatizadas Bloqueantes (Principio IV)

La fase de implementación comenzará obligatoriamente escribiendo las siguientes pruebas unitarias en rojo:

1. `test_soft_delete_task_success`: `delete_task()` establece `is_deleted=True` y marca `deleted_at`.
2. `test_soft_deleted_task_excluded_from_listing`: `get_user_tasks()` no retorna tareas con `is_deleted=True`.
3. `test_cannot_delete_already_deleted_task`: Re-eliminar lanza excepción de dominio y no duplica auditoría.
4. `test_cannot_edit_or_change_status_of_deleted_task`: Tareas eliminadas no admiten actualización de atributos ni cambios de estado.
5. `test_soft_delete_is_permanent_for_user`: Confirma que la eliminación es definitiva e irreversible para el usuario (cero soporte de restauración o papelera).
6. `test_reopen_completed_task_success`: `reopen_task()` sobre tarea `completed` la transiciona de forma unívoca a `pending` y registra `TASK_REOPENED`.
7. `test_cannot_reopen_pending_or_in_progress_task`: `reopen_task()` sobre tareas no completadas es rechazado.
8. `test_cannot_reopen_deleted_task`: `reopen_task()` sobre tareas eliminadas es bloqueado.
9. `test_request_reset_unregistered_email_silent`: Correos inexistentes no lanzan error ni generan tokens.
10. `test_request_reset_registered_email_creates_token`: Se genera token con hash SHA-256 y expiración en 15 minutos.
11. `test_request_reset_invalidates_prior_unused_tokens`: Una nueva solicitud válida invalida de inmediato cualquier token pendiente previo para esa cuenta.
12. `test_request_reset_silent_throttling_limit`: A partir de la 4ta solicitud en 15 minutos para un correo, se aplica silent throttling (no crea token adicional ni envía correo, retornando éxito neutro).
13. `test_reset_password_with_valid_token`: Se actualiza la contraseña con `scrypt`, se marca `used_at` y se incrementa `session_version`.
14. `test_reset_password_revokes_all_active_sessions`: Al restablecer la contraseña, las sesiones activas previas quedan invalidadas en `@login_required` por discrepancia de `session_version`.
15. `test_reset_password_with_expired_token_fails`: Token vencido (>15 min) es rechazado.
16. `test_reset_password_with_used_token_fails`: Token previamente usado es rechazado.

---

## Complexity Tracking

| Solución Adoptada | Justificación frente al Principio V (Simplicidad) | Alternativas Más Complejas Rechazadas |
|---|---|---|
| **Soft Delete mediante columnas nativas (`is_deleted`, `deleted_at`)** | Simple, transparente y sin dependencias. Añadir dos campos filtrados en `TaskService` no introduce abstracciones complejas ni altera el comportamiento ORM estándar de SQLAlchemy. | 1. Plugins o interceptores globales de ORM (`before_compile` events de SQLAlchemy) que ocultan el comportamiento y dificultan consultas de auditoría.<br>2. Tablas separadas de histórico/eliminadas (`deleted_tasks`) que rompen claves foráneas y complican las migraciones. |
| **Revocación de sesiones mediante `session_version` en `User`** | Incrementar un entero `session_version` en la base de datos al cambiar la clave y verificarlo en `@login_required` garantiza revocación global inmediata en todos los navegadores/dispositivos sin requerir servidores de caché externos. | 1. Infraestructura de sesiones distribuidas (Redis / Memcached) que introduce dependencias y viola el monolito estricto (Principio I).<br>2. Tablas pesadas de seguimiento de tokens de sesión y listas negras complejas. |
| **Control de tasa por silent throttling en base de datos** | Contar registros en `password_reset_tokens` emitidos en los últimos 15 min en `RecoveryService` ofrece protección efectiva contra abusos sin añadir librerías adicionales. | 1. Integración de extensiones de rate limiting como `Flask-Limiter` que requieren almacenamiento en memoria compartida o Redis.<br>2. Mecanismos con CAPTCHA que degradan la experiencia de usuario y añaden servicios de terceros. |
| **Envío de correos emulado en consola (`ConsoleEmailSender`)** | Máxima simplicidad y autonomía para un proyecto académico monolítico. Permite ejecutar y validar el 100% de los flujos de recuperación de forma inmediata sin costos, sin cuentas de terceros y sin riesgo de filtrar credenciales SMTP en archivos locales. | 1. Integración con servicios externos (SendGrid, Mailgun, AWS SES) que añaden dependencias de red, costos y complejidad.<br>2. Configuración obligatoria de servidor SMTP real en `.env`, riesgosa para la seguridad y propensa a fallos de cortafuegos o spam. |
| **Almacenamiento de tokens mediante hash SHA-256** | Los tokens aleatorios generados con `secrets.token_urlsafe(32)` cuentan con 256 bits de entropía nativa. Calcular su SHA-256 nativo es instantáneo y seguro para contrastar en base de datos sin requerir librerías externas. | 1. Algoritmos lentos de derivación como Argon2/scrypt para tokens (innecesarios dado que el token aleatorio no es una contraseña humana adivinable por fuerza bruta).<br>2. Cifrado simétrico reversible (AES) con gestión compleja de claves secretas. |
| **Métodos y endpoints específicos para `reopen_task` y `delete_task`** | Definir rutas explícitas (`/tasks/<id>/reopen`, `/tasks/<id>/delete`) y métodos de servicio dedicados mantiene el código claro, predecible y fuertemente tipado en cuanto a intencionalidad de negocio y eventos de auditoría. | 1. Sobrecargar `change_task_status` con banderas booleanas condicionales (`is_reopening=True`) o estados mágicos (`status='deleted'`), lo que degrada la legibilidad y vulnera la máquina de estados. |
