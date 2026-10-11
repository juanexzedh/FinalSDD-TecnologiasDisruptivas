# Implementation Plan: Gestión Básica de Tareas con Autenticación de Usuarios

**Branch**: `001-core-task-auth` | **Date**: 2026-10-06 | **Spec**: [spec.md](file:///G:/INFO%2003-02-2021/DOCUMENTOS/Jehg/jehg/UNIVERSIDAD/6%20Semestre/Pagina%20Disruptivas/specs/001-core-task-auth/spec.md)

**Input**: Especificación de la funcionalidad desde `specs/001-core-task-auth/spec.md` (HU-01 a HU-04 y HU-12 a HU-13 del backlog).

---

## Summary

Implementar el primer incremento funcional de TaskControl como un monolito estricto en Python con Flask. El incremento abarca el registro seguro de usuarios con contraseñas hasheadas (`scrypt`), control de sesiones en el backend (`login_required`), protección mandatoria contra falsificación de peticiones en sitios cruzados (CSRF) para todas las mutaciones POST (`/register`, `/login`, `/logout`, `/tasks`, `/tasks/<id>/edit`, `/tasks/<id>/status` vía `Flask-WTF` `CSRFProtect`), gestión desacoplada de `SECRET_KEY` cargada estrictamente de variables de entorno utilizando `.env.example` como plantilla no confidencial (Principio VII), creación de tareas con validación en servidor, listado y filtrado por estado con orden descendente por creación, transiciones de estado controladas con bloqueo de reapertura de tareas completadas, y edición preservando el estado de la tarea. La ejecución local y el ciclo de migraciones se estandarizan sobre el CLI nativo de Flask (`flask db upgrade` y `flask run`) desde la raíz del proyecto mediante la configuración de `FLASK_APP`. Toda mutación sobre tareas genera un registro de auditoría estructurado e inmutable centralizado en la capa de servicios. La arquitectura sigue una separación estricta de 4 capas (Modelos, Servicios, Blueprints y Jinja2/JS) con desarrollo Test-First (TDD) bloqueante para la lógica de dominio.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flask 3.x, Flask-SQLAlchemy 3.x, Flask-Migrate (Alembic), Flask-WTF 1.2+ (exclusivamente `CSRFProtect`), python-dotenv 1.0+, Werkzeug 3.x, Jinja2  
**Storage**: Base de datos relacional gestionada vía SQLAlchemy ORM (SQLite local para desarrollo y pruebas; PostgreSQL compatible para producción)  
**Testing**: `pytest`, `pytest-cov` (ejecución de pruebas de servicios con SQLite en memoria)  
**Target Platform**: Servidor web monolítico ejecutable localmente en Windows y Linux  
**Project Type**: Aplicación web monolítica con renderizado en servidor y JavaScript vanilla auxiliar  
**Performance Goals**: Tiempo de respuesta de endpoints menor a 100 ms para operaciones de tareas  
**Constraints**:
- Cumplimiento innegociable de los 8 principios de la constitución del proyecto.
- Ningún microservicio ni cola de mensajería (Principio I).
- Lógica de negocio estrictamente desacoplada del contexto HTTP (Principio II).
- Contratos de endpoints respetados rigurosamente, incluyendo tokens CSRF en todas las peticiones POST (Principio III).
- TDD obligatorio y bloqueante antes de escribir código de dominio (Principio IV).
- Simplicidad y YAGNI priorizados en cada componente (Principio V).
- Migraciones versionadas con Alembic para cambios de esquema ejecutables con `flask db upgrade` desde la raíz (Principio VI).
- Seguridad por defecto (Principio VII): validación/sanitización en servidor, verificación de sesión activa (`@login_required`), protección CSRF con tokens sincronizadores en todo POST, y cero secretos en el repositorio (`SECRET_KEY` leída de entorno vía `.env` templado por `.env.example`).
- Registro de auditoría con actor, acción, entidad y marca temporal en cada mutación (Principio VIII).
- Ejecución unificada desde la raíz mediante CLI nativo (`flask db upgrade`, `flask run`) gobernado por `FLASK_APP` (Restricción Técnica 5).  
**Scale/Scope**: Primer incremento focalizado exclusivamente en 6 historias de usuario (*Must*): HU-01, HU-02, HU-03, HU-04, HU-12 y HU-13.

---

## Constitution Check

*GATE: Evaluación previa y posterior al diseño contra la constitución de TaskControl.*

| Principio | Estado | Justificación y Cumplimiento en el Plan |
|---|---|---|
| **I. Monolito por diseño** | **PASS** | Un único repositorio, un único proceso web desplegable y una única base de datos relacional. Ejecución unificada desde la raíz del proyecto mediante el CLI de Flask (`flask run`, `flask db upgrade`) gobernado por `FLASK_APP=src/taskcontrol:create_app` en `.env`. No se incluyen microservicios ni colas distribuidas. |
| **II. Separación en capas** | **PASS** | Estructura con 4 capas explícitas: `models/`, `services/`, `blueprints/` y `templates/` + `static/`. Las rutas nunca tocan el ORM directamente; los servicios no conocen `request` ni `Response`. Las validaciones de negocio residen en la capa de servicios, evitando delegarlas a librerías de formularios de presentación. |
| **III. Contrato explícito backend-JS** | **PASS** | Diseñados y documentados en [contracts/auth-contracts.md](file:///G:/INFO%2003-02-2021/DOCUMENTOS/Jehg/jehg/UNIVERSIDAD/6%20Semestre/Pagina%20Disruptivas/specs/001-core-task-auth/contracts/auth-contracts.md) y [contracts/task-contracts.md](file:///G:/INFO%2003-02-2021/DOCUMENTOS/Jehg/jehg/UNIVERSIDAD/6%20Semestre/Pagina%20Disruptivas/specs/001-core-task-auth/contracts/task-contracts.md). Especifican rutas, métodos, payloads, el requerimiento formal de tokens CSRF (`csrf_token` en formularios y `X-CSRFToken` en cabeceras HTTP) para todo POST, y el catálogo determinista de respuestas de error (incluyendo `400 CSRF_ERROR`). |
| **IV. Test-first en lógica de negocio** | **PASS** | La suite `tests/unit/` define pruebas en rojo antes de la implementación para `AuthService` y `TaskService` (transiciones válidas e inválidas, bloqueo de reaperturas, validaciones). Condición bloqueante. |
| **V. Simplicidad sobre generalidad prematura** | **PASS** | Filosofía YAGNI estricta en las tres áreas corregidas: (1) Protección CSRF utilizando exclusivamente `CSRFProtect` de `Flask-WTF` sin introducir complejas clases de formulario WTForms; (2) Gestión de secretos basada en `os.environ` y `python-dotenv` con `.env.example` sin herramientas pesadas de bóveda externa; (3) Arranque con el CLI nativo de Flask (`flask run`, `flask db upgrade`) sin scripts envoltorios propietarios. |
| **VI. Integridad de datos y migraciones** | **PASS** | Configuración de Flask-Migrate con directorio `migrations/` versionado. Esquema relacional con claves foráneas e índices. Migraciones ejecutables directamente desde la raíz con `flask db upgrade`. |
| **VII. Seguridad por defecto** | **PASS** | (1) Protección CSRF mandatoria en todos los endpoints POST (registro, login, logout, crear, editar, cambiar estado) mediante tokens sincronizadores (`CSRFProtect`), complementando `SameSite=Lax` y `HttpOnly`. (2) Ningún secreto en el repositorio: `SECRET_KEY` se lee de variables de entorno (`.env`), versionando únicamente `.env.example` con valores ficticios. (3) Hashing criptográfico con `scrypt`, sanitización contra XSS en backend y verificación de sesión con `@login_required`. |
| **VIII. Observabilidad mínima viable** | **PASS** | `AuditService` centralizado que persiste en la tabla `audit_logs` y emite log estructurado en JSON con actor, acción, entidad y timestamp para toda creación, edición o transición de tareas. |

---

## Project Structure

### Documentation (este incremento)

```text
specs/001-core-task-auth/
├── spec.md              # Especificación funcional validada y clarificada (no modificada)
├── plan.md              # Este plan de implementación técnica actualizado
├── research.md          # Investigación técnica, decisiones arquitectónicas y justificación Principio V
├── data-model.md        # Definición de entidades SQLAlchemy y máquina de estados
├── quickstart.md        # Guía de inicialización con .env.example, flask run y escenarios de prueba
├── contracts/           # Contratos formales de endpoints HTTP con especificación CSRF
│   ├── auth-contracts.md # Contratos para HU-12 y HU-13 (incluye CSRF en registro, login y logout)
│   └── task-contracts.md # Contratos para HU-01 a HU-04 (incluye CSRF en crear, editar y status)
└── checklists/
    └── requirements.md  # Checklist de calidad de requerimientos
```

### Source Code (Estructura Monolítica del Repositorio)

```text
.env.example                     # Plantilla no confidencial de variables de entorno (Principio VII)
.gitignore                       # Excluye .env y bases de datos locales, preserva !.env.example
requirements.txt                 # Dependencias fijadas (incluye Flask-WTF y python-dotenv)
run.py                           # Punto de entrada auxiliar de conveniencia (arranque estándar vía flask run)

migrations/                      # Scripts versionados de Alembic / Flask-Migrate
src/
└── taskcontrol/
    ├── __init__.py              # Application Factory (create_app registrando db, migrate, csrf)
    ├── config.py                # Configuración por entornos leyendo SECRET_KEY de os.environ
    ├── extensions.py            # Instancias de SQLAlchemy, Flask-Migrate y CSRFProtect
    │
    ├── models/                  # Capa 1: Modelos de datos relacionales (SQLAlchemy)
    │   ├── __init__.py
    │   ├── user.py              # Modelo User (id, email, password_hash, created_at)
    │   ├── task.py              # Modelo Task (id, user_id, title, description, due_date, status, timestamps)
    │   └── audit_log.py         # Modelo AuditLog (id, timestamp, actor_id, action, entity_id, details)
    │
    ├── services/                # Capa 2: Lógica de negocio y dominio puro (TDD bloqueante)
    │   ├── __init__.py
    │   ├── auth_service.py      # Registro, verificación de contraseñas y hashing
    │   ├── task_service.py      # Creación, listado filtrado, edición y máquina de transiciones
    │   └── audit_service.py     # Registro centralizado de eventos de auditoría y log estructurado
    │
    ├── blueprints/              # Capa 3: Controladores y rutas HTTP (Flask)
    │   ├── __init__.py
    │   ├── auth.py              # Rutas /register, /login, /logout (protegidas por CSRF)
    │   ├── tasks.py             # Rutas /tasks, /tasks/new, /tasks/<id>/edit, /tasks/<id>/status (CSRF)
    │   └── decorators.py        # Decorador @login_required para verificación estricta en backend
    │
    ├── templates/               # Capa 4A: Presentación en servidor (Jinja2)
    │   ├── base.html            # Layout maestro (meta csrf-token, navbar, alertas flash)
    │   ├── auth/
    │   │   ├── login.html       # Vista de login con campo oculto csrf_token()
    │   │   └── register.html    # Vista de registro con campo oculto csrf_token()
    │   └── tasks/
    │       ├── index.html       # Listado y filtrado de tareas
    │       ├── new.html         # Formulario de nueva tarea con csrf_token()
    │       └── edit.html        # Formulario de edición con csrf_token()
    │
    └── static/                  # Capa 4B: Recursos estáticos del cliente
        ├── css/
        │   └── styles.css       # Estilos visuales de la interfaz
        └── js/
            └── main.js          # JavaScript vanilla que inyecta X-CSRFToken en peticiones fetch POST

tests/
├── conftest.py                  # Fixtures compartidas (app, client, CSRF testing config, DB en memoria)
├── unit/                        # Pruebas unitarias de dominio (TDD mandatorio antes de implementar servicios)
│   ├── test_auth_service.py     # Pruebas de reglas de usuario y credenciales
│   ├── test_task_service.py     # Pruebas de reglas de tareas y máquina de estados
│   └── test_audit_service.py    # Pruebas de emisión y persistencia de eventos de auditoría
└── integration/                 # Pruebas de integración HTTP y contratos
    ├── test_auth_routes.py      # Verificación de endpoints de autenticación, sesiones y CSRF
    └── test_task_routes.py      # Verificación de endpoints de tareas, control de acceso y CSRF
```

---

## Estrategia de Implementación por Capas

### 1. Capa de Modelos (`models/`)
- Definición declarativa de `User`, `Task` y `AuditLog` utilizando `db.Model`.
- Restricciones relacionales: `user_id` en `tasks` con clave foránea; `email` único e indexado.
- Enumeración de estados en `Task`: `pending`, `in_progress`, `completed`.

### 2. Capa de Servicios (`services/`) — TDD Bloqueante
- **`AuthService`**:
  - `register_user(email, password)`: Normaliza correo, valida complejidad ($\ge 8$ caracteres, letra y número), valida unicidad, genera hash `scrypt` y persiste.
  - `authenticate_user(email, password)`: Busca por email y verifica hash con `check_password_hash`.
- **`TaskService`**:
  - `create_task(user_id, title, description, due_date)`: Valida título no vacío (1-200 caracteres), sanitiza texto plano, asigna estado inicial `pending`, persiste y delega en `AuditService`.
  - `get_user_tasks(user_id, status_filter='all')`: Consulta tareas aisladas estrictamente por `user_id`, ordenadas por `created_at DESC`.
  - `update_task(user_id, task_id, title, description, due_date)`: Verifica propiedad, valida campos, actualiza atributos preservando el estado y delega en `AuditService`.
  - `change_task_status(user_id, task_id, new_status)`: Verifica propiedad, valida transición contra la máquina de estados (bloqueando reaperturas desde `completed`), actualiza estado y delega en `AuditService`.
- **`AuditService`**:
  - `record_task_event(actor_id, action, task_id, details=None)`: Inserta fila en `audit_logs` y emite log estructurado JSON vía logger `taskcontrol.audit`.

### 3. Capa de Blueprints, Seguridad y Configuración (`blueprints/` y `config.py`)
- **Gestión de Configuración y Secretos**: `config.py` define clases de configuración (`DevelopmentConfig`, `TestingConfig`, `ProductionConfig`) leyendo `SECRET_KEY` de `os.environ.get('SECRET_KEY')`. Si en producción falta la clave, aborta el arranque. El archivo `.env.example` en la raíz guía la configuración local sin exponer secretos en el repositorio (Principio VII).
- **Protección CSRF Global**: Instancia `csrf = CSRFProtect()` en `extensions.py` inicializada en `create_app()`. Protege todos los métodos POST de la aplicación:
  - Registro (`POST /register`), Login (`POST /login`), Logout (`POST /logout`).
  - Creación de tarea (`POST /tasks`), Edición (`POST /tasks/<id>/edit`), Cambio de estado (`POST /tasks/<id>/status`).
  - Si una petición carece de token o éste es inválido, responde inmediatamente con código HTTP `400 Bad Request` (`CSRF_ERROR`).
- **Autenticación y Control de Acceso**: `decorators.py` contiene `@login_required`, verificando `session.get('user_id')` antes de ejecutar cualquier acción de tareas.
- **Descubrimiento y Arranque**: `FLASK_APP=src/taskcontrol:create_app` en `.env` permite que `flask db upgrade` y `flask run` se ejecuten inmediatamente desde la raíz del proyecto gracias a la carga automática de `python-dotenv`.

### 4. Capa de Presentación (`templates/` y `static/`)
- Plantillas Jinja2 limpias y semánticas con manejo de errores y mensajes flash.
- Inclusión del token CSRF en todo formulario HTML mediante `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- Inclusión de `<meta name="csrf-token" content="{{ csrf_token() }}">` en el encabezado de `base.html`.
- En `static/js/main.js`, cualquier petición dinámica o asíncrona mediante `fetch` (POST) extrae el token del meta tag y lo adjunta en la cabecera `X-CSRFToken`.

---

## Complexity Tracking

| Solución Adoptada | Justificación frente al Principio V (Simplicidad) | Alternativas Más Complejas Rechazadas |
|---|---|---|
| **Protección CSRF con `Flask-WTF` `CSRFProtect`** | Se utiliza **únicamente** la extensión `CSRFProtect` para validar tokens criptográficos en todos los POST, sin adoptar el framework completo WTForms. Esto evita crear clases de formulario redundantes (`FlaskForm`, `TaskForm`) y mantiene las reglas de validación en la capa de servicios de dominio (Principio II), logrando máxima seguridad con el mínimo código (2 líneas de inicialización). | 1. Implementar generador y validador artesanal de HMAC/tokens (propenso a fallos criptográficos y desincronización de sesión).<br>2. WTForms completo con clases de formulario y validadores declarativos (abstracción excesiva y duplicación de validaciones). |
| **Carga de `SECRET_KEY` desde entorno con `.env.example`** | Carga directa mediante `os.environ.get('SECRET_KEY')` apoyada por `python-dotenv`. `.env.example` sirve de plantilla con valores ficticios sin secretos en Git. Cumple al 100% el Principio VII con cero abstracción adicional (patrón 12-Factor estándar). | 1. Integración con gestores de secretos externos (Vault, AWS Secrets Manager).<br>2. Cifrado de repositorios con herramientas como git-crypt o SOPS (sobreingeniería para el primer incremento monolítico). |
| **Arranque y migraciones vía CLI de Flask (`FLASK_APP`)** | Configurar `FLASK_APP=src/taskcontrol:create_app` en `.env` aprovecha el cargador nativo de `python-dotenv` integrado en Flask. Permite que `flask db upgrade` y `flask run` funcionen desde la raíz sin intervención manual en cualquier SO. | 1. Scripts personalizados en bash/PowerShell (`start.ps1`, `start.sh`) que introducen discrepancias entre plataformas.<br>2. Gestores de procesos externos (Makefiles, Honcho, Supervisord). |
