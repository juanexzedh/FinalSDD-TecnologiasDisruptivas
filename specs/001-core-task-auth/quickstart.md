# Quickstart & Guía de Validación: TaskControl (Incremento 1)

**Feature**: `001-core-task-auth`  
**Date**: 2026-10-06  
**Stack**: Python 3.11+, Flask, SQLAlchemy, Flask-Migrate, pytest  

---

## 1. Prerrequisitos

- Python 3.11 o superior instalado.
- Entorno virtual de Python configurado.

---

## 2. Puesta en Marcha con un Solo Comando (Principio I & Restricciones)

### 2.1 Instalación de dependencias
```bash
python -m venv .venv
# En Windows PowerShell:
.venv\Scripts\Activate.ps1
# O en bash / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2.2 Variables de entorno desde plantilla no confidencial (`.env.example` y `.env`)
En cumplimiento del **Principio VII (Seguridad por defecto)**, ningún secreto se almacena en el repositorio. El repositorio proporciona [.env.example](file:///C:/Users/Kreilt/Downloads/SDD-Tecnologias-Disruptivas-main/.env.example) como plantilla base.

1. Copiar la plantilla `.env.example` para crear el archivo local `.env` (ignorado en `.gitignore`):
   ```bash
   # En Windows PowerShell:
   Copy-Item .env.example .env
   # O en bash:
   cp .env.example .env
   ```

2. Generar una clave criptográfica segura localmente para `SECRET_KEY`:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. Abrir `.env` y sustituir el valor placeholder de `SECRET_KEY` con la clave generada. El archivo resultante tendrá el siguiente esquema:
   ```env
   # Configuración de arranque de Flask (Principio I y Restricción 5)
   FLASK_APP=src/taskcontrol:create_app
   FLASK_ENV=development
   FLASK_DEBUG=1

   # Clave secreta para firma de cookies de sesión y tokens CSRF (Principio VII)
   SECRET_KEY=TU_CLAVE_ALEATORIA_GENERADA_AQUI

   # Persistencia relacional local
   DATABASE_URL=sqlite:///taskcontrol.db
   ```

### 2.3 Inicialización de Base de Datos y Migraciones (Principio VI)
Ejecutar desde la raíz del proyecto. Gracias a que `python-dotenv` carga automáticamente `FLASK_APP` desde `.env`, el comando localiza de inmediato la aplicación:
```bash
# Aplicar migraciones versionadas para crear las tablas users, tasks y audit_logs
flask db upgrade
```

### 2.4 Ejecución de la Aplicación
Iniciar el servidor de desarrollo monolítico directamente desde la raíz del proyecto con el CLI canónico de Flask:
```bash
flask run
# La aplicación queda disponible en http://127.0.0.1:5000
```

*(Opcionalmente, también es posible iniciar la aplicación mediante el punto de entrada de conveniencia: `python run.py`).*

---

## 3. Ejecución de Pruebas Automatizadas (TDD - Principio IV)

Para verificar el cumplimiento del principio Test-First y los contratos antes o después de la implementación:

```bash
# 1. Ejecutar pruebas unitarias de la capa de dominio (servicios y reglas bloqueantes)
pytest tests/unit/ -v

# 2. Ejecutar pruebas de integración de rutas HTTP y contratos (sesiones, control de acceso y CSRF)
pytest tests/integration/ -v

# 3. Ejecutar toda la suite con reporte de cobertura
pytest --cov=src/taskcontrol tests/
```

---

## 4. Escenarios de Validación Extremo a Extremo (Manual o Navegador)

> [!NOTE]
> **Protección CSRF activa (Principio VII)**: Todas las operaciones con método `POST` (registro, login, logout, creación, edición y cambio de estado) exigen un token CSRF válido. En la interfaz web, las plantillas Jinja2 inyectan automáticamente `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` en los formularios y la meta-etiqueta `<meta name="csrf-token">` para peticiones JavaScript vanilla `fetch`. Cualquier petición POST directa (como `curl` o script externo) que carezca de token CSRF válido será rechazada con `400 Bad Request` (`CSRF_ERROR`).

### Escenario 1: Registro de Usuario (HU-12)
1. Navegar a `http://127.0.0.1:5000/register`.
2. Intentar registrar `usuario@ejemplo.com` con contraseña `corta` (menos de 8 caracteres).
   - **Resultado esperado**: Error de validación en backend; el sistema rechaza el formulario.
3. Registrar `usuario@ejemplo.com` con `Password123` (8+ caracteres, letra y número).
   - **Resultado esperado**: Redirección a `/login` con mensaje de bienvenida; la contraseña queda hasheada con `scrypt` en la base de datos y el token CSRF del formulario es validado con éxito.

### Escenario 2: Inicio y Control de Sesión (HU-13)
1. Navegar a `http://127.0.0.1:5000/tasks` sin autenticación previa.
   - **Resultado esperado**: Redirección inmediata a `/login` (Principio VII).
2. En `/login`, ingresar `usuario@ejemplo.com` y `Password123`.
   - **Resultado esperado**: Redirección a `/tasks`, cookie de sesión HttpOnly y SameSite=Lax establecida.

### Escenario 3: Creación y Listado de Tareas (HU-01, HU-02)
1. En `/tasks`, hacer clic en "Nueva Tarea" o navegar a `/tasks/new`.
2. Registrar una tarea con título `"Mi primera tarea"`, descripción `"Detalles de prueba"` y fecha `"2026-10-20"`.
   - **Resultado esperado**: Redirección a `/tasks` (token CSRF verificado). La tarea aparece en la lista con estado `"pendiente"`. Se genera una fila en `audit_logs` con `action='TASK_CREATED'`.
3. Crear una segunda tarea con fecha pasada o sin fecha.
   - **Resultado esperado**: La tarea más reciente se ubica al principio del listado (orden descendente por fecha de creación).

### Escenario 4: Transición de Estados (HU-03)
1. En la lista de tareas, cambiar el estado de la tarea de `"pendiente"` a `"en progreso"`.
   - **Resultado esperado**: El estado se actualiza en pantalla y en la base de datos (POST con token CSRF); se crea un registro de auditoría `TASK_STATUS_CHANGED`.
2. Cambiar de `"en progreso"` a `"completada"`.
   - **Resultado esperado**: El estado se actualiza a completada; auditoría registrada.
3. Intentar volver de `"completada"` a `"pendiente"`.
   - **Resultado esperado**: La acción es bloqueada con mensaje de error (no se permite reapertura directa en este incremento).

### Escenario 5: Edición y Aislamiento de Usuario (HU-04, HU-02)
1. Editar la tarea creada modificando su título a `"Mi primera tarea (editada)"`.
   - **Resultado esperado**: Se guarda el cambio con token CSRF validado, se preserva el estado y se registra evento `TASK_UPDATED`.
2. Iniciar sesión con un segundo usuario `otro@ejemplo.com`.
   - **Resultado esperado**: Su listado de tareas está completamente vacío. Intentar acceder a `/tasks/1/edit` del primer usuario responde `404 Not Found` o `403 Forbidden` (cero fuga de información).
