# Research & Technical Decisions: Primer Incremento TaskControl

**Feature**: `001-core-task-auth` (Gestión básica de tareas con autenticación)  
**Date**: 2026-10-06  
**Status**: Completed  

---

## 1. Arquitectura Monolítica y Estructura en Capas

### Contexto y Requisitos
El **Principio I** de la constitución exige un monolito estricto (un solo repositorio, un solo proceso, una sola base de datos relacional). El **Principio II** exige una separación estricta en 4 capas sin saltos: Modelos $\rightarrow$ Servicios (Dominio) $\rightarrow$ Blueprints (HTTP) $\rightarrow$ Presentación (Jinja2 + JS).

### Decisión
Estructurar el código bajo un paquete central `src/taskcontrol/` utilizando el patrón **Application Factory** (`create_app`) de Flask:
- `models/`: Clases SQLAlchemy puras que representan el esquema de base de datos.
- `services/`: Módulos con la lógica de negocio pura (validación de reglas de tarea, transiciones de estado, hashing, orquestación de transacciones). No importan `request`, `g`, ni `Response`.
- `blueprints/`: Controladores HTTP divididos por contexto funcional (`auth.py` y `tasks.py`). Extraen parámetros de la petición HTTP, validan sesión y delegan inmediatamente en la capa de servicios.
- `templates/` y `static/`: Renderizado del lado del servidor con Jinja2 y JavaScript vanilla mínimo para apoyo visual.

### Alternativas Consideradas
- *Estructura plana (todo en app.py)*: Rechazada por violar el Principio II y dificultar las pruebas unitarias aisladas de la lógica de negocio.
- *Arquitectura hexagonal / Clean Architecture con interfaces abstractas y repositorios genéricos*: Rechazada por sobreingeniería prematura violando el Principio V (*Simplicidad sobre generalidad prematura*). SQLAlchemy ya actúa como Data Mapper / Unit of Work.

---

## 2. Gestión de Seguridad y Hashing de Contraseñas (HU-12)

### Contexto y Requisitos
El requerimiento funcional FR-003 y el Principio VII exigen que ninguna contraseña se almacene en texto plano y que se apliquen algoritmos de derivación robustos. Además, la clarificación formalizada exige una longitud mínima de 8 caracteres con al menos una letra y un número.

### Decisión
Utilizar `werkzeug.security` con `generate_password_hash(method='scrypt')` y `check_password_hash()`.
- Algoritmo: `scrypt` (estándar nativo recomendado en Python 3.11+ y Werkzeug moderno, resistente a ataques por hardware acelerado).
- Validación en `AuthService`: Expresión regular previa al hash para verificar `len >= 8` y presencia de `[a-zA-Z]` y `[0-9]`.
- Normalización de correo: `email.strip().lower()` antes de cualquier consulta o almacenamiento para garantizar unicidad insensible a mayúsculas.

### Alternativas Consideradas
- *bcrypt con paquete C externo*: Requiere compiladores C en Windows y configuraciones adicionales de dependencias; `werkzeug.security` con `scrypt` proporciona la misma solidez criptográfica sin dependencias nativas problemáticas.
- *Validación en frontend únicamente*: Prohibida explícitamente por el Principio VII.

---

## 3. Autenticación y Manejo de Sesión (HU-13)

### Contexto y Requisitos
El Principio VII y la clarificación de sesión exigen verificación de sesión activa en el backend en cada endpoint que modifique o consulte datos privados, utilizando una sesión de navegador estándar (no persistente) que se destruya al cerrar el navegador o cerrar sesión.

### Decisión
- **Mecanismo de sesión**: Sesiones firmadas criptográficamente del lado del cliente utilizando la cookie de sesión nativa de Flask protegida con `SECRET_KEY`.
- **Configuración de cookies**:
  - `SESSION_COOKIE_HTTPONLY = True`: Impide el acceso a la cookie desde scripts del cliente (mitiga XSS).
  - `SESSION_COOKIE_SAMESITE = 'Lax'`: Mitigación complementaria de primer nivel contra ataques de CSRF (defensa en profundidad).
  - `SESSION_PERMANENT = False`: La cookie expira al cerrar la sesión del navegador.
- **Protección de rutas en backend**: Un decorador reutilizable `@login_required` en la capa de blueprints que verifica `session.get('user_id')`. Si no existe sesión activa, redirige inmediatamente a `/login` con un mensaje flash o responde 401 Unauthorized.
- **Aislamiento de recursos**: Los endpoints de tareas siempre pasan el `current_user_id` obtenido de la sesión al `TaskService`, asegurando que ninguna consulta ni mutación opere fuera del ámbito del usuario autenticado.

---

## 4. Auditoría Estructurada Centralizada (Principio VIII)

### Contexto y Requisitos
El Principio VIII exige que toda mutación sobre tareas (creación, cambio de estado, edición) genere un registro de auditoría estructurado con `actor`, `action`, `entity`, `timestamp` y detalles desde el primer incremento. No debe duplicarse esta lógica en cada ruta.

### Decisión
Centralizar la auditoría en la capa de servicios mediante un módulo dedicado `audit_service.py`:
1. **Persistencia**: Se persiste una fila en la tabla relacional `audit_logs` con `actor_id`, `action`, `entity_type='Task'`, `entity_id`, `details` (JSON o dict serializado) y `timestamp` (UTC).
2. **Logging en aplicación**: Simultáneamente, se emite un registro estructurado a través de `logging.getLogger('taskcontrol.audit')` formateado como JSON para trazabilidad en consola y archivos de log.
3. **Punto de integración**: `TaskService` invoca `AuditService.record_event()` dentro de la misma transacción atómica de base de datos antes del `commit`. Las rutas HTTP nunca invocan auditoría directamente.

### Alternativas Consideradas
- *Hooks / signals de SQLAlchemy (`after_insert`, `after_update`)*: Añaden complejidad oculta y dificultan identificar el `actor` de negocio cuando se opera fuera del ciclo de petición HTTP o en tests de servicio.
- *Llamadas manuales en cada función de Blueprint*: Rechazadas por violar el principio DRY y permitir que una ruta olvide auditar una acción.

---

## 5. Estrategia de Migraciones de Base de Datos (Principio VI)

### Contexto y Requisitos
El Principio VI prohíbe modificaciones manuales directas a la base de datos y exige migraciones versionadas y reproducibles mediante Flask-Migrate / Alembic.

### Decisión
- Configurar `Flask-Migrate` vinculado a la instancia única de `SQLAlchemy`.
- Directorio de migraciones en la raíz del repositorio: `migrations/`.
- Flujo de inicialización y ejecución:
  1. `flask db init`: Genera el entorno de Alembic (se ejecuta una única vez al configurar el repositorio).
  2. `flask db migrate -m "initial_schema_users_tasks_audit"`: Detecta los modelos `User`, `Task` y `AuditLog` y genera el script versionado.
  3. `flask db upgrade`: Aplica los cambios sobre el motor de base de datos relacional (SQLite local `taskcontrol.db`) ejecutable directamente desde la raíz del proyecto.

---

## 6. Estrategia de Pruebas y TDD (Principio IV)

### Contexto y Requisitos
El Principio IV impone Test-First (TDD) bloqueante para la lógica de negocio y transiciones de estado.

### Decisión
Estructurar las pruebas con `pytest` en dos niveles estrictamente delimitados:
1. **Pruebas de Unidad / Dominio (`tests/unit/`)**:
   - Validan `AuthService`, `TaskService` y `AuditService`.
   - Se ejecutan contra una base de datos SQLite en memoria (`sqlite:///:memory:`).
   - Prueban: validación de contraseñas, unicidad de correos, transiciones permitidas e inválidas de tareas, bloqueo de reapertura de tareas completadas, y registro de auditoría.
   - **Regla bloqueante**: Estas pruebas deben escribirse en rojo (Red) antes de escribir la lógica del servicio correspondiente.
2. **Pruebas de Integración y Rutas (`tests/integration/`)**:
   - Validan los Blueprints HTTP utilizando el `test_client` de Flask.
   - Prueban: cumplimiento del contrato HTTP (códigos de estado, redirecciones, cookies de sesión, headers, validación de token CSRF en POST), validación de formularios y rechazo de acceso no autenticado o acceso cruzado entre cuentas.

---

## 7. Protección Integral contra CSRF en Todas las Mutaciones POST (Principio VII y Principio V)

### Contexto y Requisitos
El Principio VII exige seguridad por defecto en cada punto de interacción. Si bien la directiva `SESSION_COOKIE_SAMESITE = 'Lax'` previene ataques básicos de navegación cruzada, es insuficiente por sí sola: no cubre navegadores heredados, no previene escenarios específicos de top-level POST ni solicitudes asíncronas con orígenes cruzados permitidos, y no reemplaza el estándar industrial de validación por token. Todas las operaciones mutantes del Incremento 1 (`POST /register`, `POST /login`, `POST /logout`, `POST /tasks`, `POST /tasks/<id>/edit`, `POST /tasks/<id>/status`) deben protegerse activamente contra CSRF.

### Decisión
1. Incorporar la extensión estándar `Flask-WTF` utilizando **únicamente** su componente `CSRFProtect` (`csrf = CSRFProtect()`, `csrf.init_app(app)` en `extensions.py`).
2. Proteger automáticamente todas las solicitudes HTTP `POST`:
   - En vistas Jinja2: se inyecta el token en formularios mediante `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` y en la cabecera HTML general mediante `<meta name="csrf-token" content="{{ csrf_token() }}">`.
   - En peticiones asíncronas / JavaScript vanilla: `main.js` lee la meta-etiqueta y adjunta el encabezado `X-CSRFToken` a cada llamada `fetch` con método POST.
   - Ante tokens ausentes o manipulados, `CSRFProtect` aborta la petición con código HTTP `400 Bad Request` y formato de error consistente `CSRF_ERROR`.
3. En la suite de pruebas de integración, `CSRFProtect` se configura apropiadamente (o se deshabilita temporalmente con `WTF_CSRF_ENABLED = False` solo en el entorno `TestingConfig`, manteniendo tests específicos de integración que validan el rechazo de peticiones sin token CSRF).

### Justificación frente al Principio V (Simplicidad)
- *Alternativa de desarrollo propio (Custom Token Handlers / HMAC decorators)*: Reinventar la generación criptográfica de tokens y la validación en tiempo constante introduciría código artesanal propenso a vulnerabilidades sutiles (timing attacks, sincronización de tokens con sesión).
- *Alternativa de framework pesado (WTForms con clases completas `FlaskForm`)*: Crear clases de formulario (`LoginForm`, `RegisterForm`, `TaskForm`) con validadores redundantes violaría el Principio V al agregar abstracciones complejas innecesarias, duplicando la lógica de validación que por diseño (Principio II) reside exclusivamente en la capa de servicios (`AuthService`, `TaskService`).
- *Solución elegida*: Usar exclusivamente `CSRFProtect` de `Flask-WTF`. Requiere únicamente 2 líneas de configuración en la fábrica de aplicaciones, reutiliza la `SECRET_KEY` existente, ofrece soporte nativo para formularios y encabezados `X-CSRFToken`, y no introduce clases ni abstracciones adicionales. Cumple estrictamente el Principio VII con la máxima simplicidad (Principio V).

---

## 8. Gestión de Configuración y Claves Secretas (`SECRET_KEY`) (Principio VII y Principio V)

### Contexto y Requisitos
El Principio VII establece de forma innegociable: *"Ningún secreto, token o clave de entorno (`SECRET_KEY`) debe ser versionado en el repositorio de control de versiones"*. Permitir que `SECRET_KEY` quede escrita en código fuente o en ejemplos de configuración rápida vulnera este mandato. Se requiere un mecanismo desacoplado para cargar secretos exclusivamente desde el entorno.

### Decisión
1. Cargar la configuración sensible mediante `os.environ.get('SECRET_KEY')` en `src/taskcontrol/config.py`, aprovechando la lectura automática de variables de entorno mediante `python-dotenv`.
2. Proveer un archivo de plantilla `.env.example` versionado en el repositorio con variables declaradas y valores ficticios explicativos, sin contener ningún secreto real.
3. Asegurar que `.env` y cualquier variante de secretos locales estén estrictamente listados en `.gitignore` (`.env`, `.env.*`, con excepción de `!.env.example`).
4. Documentar en `quickstart.md` la generación local de secretos criptográficos seguros mediante:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
5. En `ProductionConfig`, hacer obligatorio que `SECRET_KEY` esté presente; si está ausente o utiliza un valor por defecto no seguro, la aplicación aborta inmediatamente con un `ValueError` descriptivo.

### Justificación frente al Principio V (Simplicidad)
- *Alternativas complejas*: Utilizar servicios externos de gestión de secretos (HashiCorp Vault, AWS Secrets Manager) o sistemas de cifrado en Git (git-crypt, SOPS) representaría una sobreingeniería desproporcionada para el Incremento 1.
- *Solución elegida*: El patrón estándar de la industria de archivo `.env` local no versionado + `.env.example` como plantilla + `os.environ` satisface al 100% el Principio VII de no versionar secretos en el repositorio, requiriendo únicamente la librería liviana `python-dotenv` y ninguna infraestructura externa.

---

## 9. Ciclo de Vida de Arranque y Ejecución CLI con `FLASK_APP` (Restricción Técnica 5 y Principio V)

### Contexto y Requisitos
La Restricción Técnica 5 exige que el entorno y la aplicación se inicialicen y ejecuten localmente con un único comando documentado y reproducible. Si el proyecto depende exclusivamente de un script aislado `python run.py` sin declarar `FLASK_APP`, los comandos canónicos del ecosistema de Flask (`flask db upgrade` para migraciones y `flask run` para levantar el servidor de desarrollo) fallan al ejecutarse desde la raíz porque Flask no sabe cómo localizar la fábrica de aplicaciones `create_app` ubicada en `src/taskcontrol/`.

### Decisión
1. Declarar `FLASK_APP=src/taskcontrol:create_app` dentro de `.env` (y como referencia en `.env.example`).
2. Al incorporar `python-dotenv`, el CLI nativo de Flask detecta y carga automáticamente `.env` al ejecutar cualquier comando `flask` desde la raíz del proyecto.
3. Gracias a esto, los dos comandos fundamentales de puesta en marcha funcionan de forma transparente e inmediata desde el directorio raíz:
   - `flask db upgrade`: Aplica las migraciones versionadas de la base de datos relacional.
   - `flask run`: Inicia el servidor de desarrollo monolítico en `http://127.0.0.1:5000`.
4. Se mantiene un archivo `run.py` en la raíz del proyecto como punto de entrada de conveniencia alternativo (`python run.py`), pero los comandos estándar del flujo de trabajo y del ciclo de vida del framework son `flask db upgrade` y `flask run`.

### Justificación frente al Principio V (Simplicidad)
- *Alternativas complejas*: Escribir scripts envoltorios multiplataforma (`run.bat`, `run.sh`, `start.ps1`) o gestores de procesos (Honcho, Makefile, Procfile) crearía mantenimiento adicional y divergencias entre sistemas operativos (Windows vs Linux).
- *Solución elegida*: Apoyarse enteramente en el CLI nativo de Flask (`flask run`, `flask db upgrade`) y la variable canónica `FLASK_APP` en `.env`. Es el estándar de Flask, no requiere código auxiliar personalizado y ofrece una experiencia limpia y uniforme para cualquier desarrollador.
