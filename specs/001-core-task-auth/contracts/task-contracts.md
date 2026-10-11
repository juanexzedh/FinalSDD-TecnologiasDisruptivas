# Contratos HTTP: Gestión de Tareas (HU-01 a HU-04)

**Feature**: `001-core-task-auth`  
**Date**: 2026-10-06  
**Principio Constitucional**: III (Contrato explícito previo a la implementación) y VII (Seguridad por defecto)  

---

## 0. Política Global de Protección CSRF (Principio VII)

En estricto cumplimiento del Principio VII (Seguridad por defecto), **todas las peticiones mutantes con método POST** (`/tasks`, `/tasks/<int:task_id>/edit`, `/tasks/<int:task_id>/status`) exigen validación de token CSRF mediante `Flask-WTF` `CSRFProtect`:
- **Formularios HTML (`application/x-www-form-urlencoded`)**: Todo formulario de creación, edición o cambio de estado incluye el campo oculto `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- **Peticiones Asíncronas / JSON (`application/json`)**: Las peticiones enviadas mediante JavaScript vanilla (`fetch`) o clientes API deben incluir el encabezado HTTP `X-CSRFToken: <token>` (obtenido de `<meta name="csrf-token" content="{{ csrf_token() }}">` en `base.html`) o el campo `"csrf_token"` en el payload JSON.
- **Respuesta ante fallo de CSRF (`400 Bad Request`)**:
  ```json
  {
    "status": "error",
    "code": "CSRF_ERROR",
    "message": "Token CSRF ausente o inválido."
  }
  ```

---

## 1. Listado y Filtrado de Tareas (`HU-02`)

### 1.1 `GET /tasks`
- **Descripción**: Retorna las tareas pertenecientes al usuario autenticado, ordenadas por defecto por fecha de creación descendente (`created_at DESC`), con opción de filtrado por estado.
- **Autenticación requerida**: **SÍ** (`@login_required`). Si no está autenticado, redirige (302) a `/login` o responde 401.
- **Parámetros de Consulta (Query String)**:
  - `status` (opcional, string): Valores admitidos: `'all'`, `'pending'`, `'in_progress'`, `'completed'`. Por defecto: `'all'`.
- **Respuestas**:
  - `200 OK` (Navegador): Renderiza plantilla `tasks/index.html` con la lista de tareas del usuario actual y metadatos CSRF en el encabezado HTML para peticiones interactivas.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "data": {
        "tasks": [
          {
            "id": 10,
            "title": "Configurar entorno de desarrollo",
            "description": "Instalar dependencias y ejecutar migraciones iniciales.",
            "due_date": "2026-10-15",
            "status": "pending",
            "created_at": "2026-10-06T14:30:00Z"
          }
        ],
        "filter": "all",
        "total": 1
      }
    }
    ```
  - `401 Unauthorized`:
    ```json
    {
      "status": "error",
      "code": "UNAUTHORIZED",
      "message": "Se requiere autenticación activa para consultar tareas."
    }
    ```

---

## 2. Creación de Tareas (`HU-01`)

### 2.1 `GET /tasks/new`
- **Descripción**: Muestra la interfaz con el formulario para registrar una nueva tarea.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Respuestas**:
  - `200 OK`: Renderiza plantilla `tasks/new.html` conteniendo el campo oculto con `csrf_token()`.
  - `302 Found`: Redirección a `/login` si no está autenticado.

### 2.2 `POST /tasks`
- **Descripción**: Crea una nueva tarea en estado `'pending'` asociada al usuario autenticado y genera un evento de auditoría (`TASK_CREATED`).
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida (`csrf_token` en formulario o `X-CSRFToken` en cabecera HTTP).
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "title": "Implementar endpoints de tareas",
    "description": "Texto plano sin etiquetas HTML ni scripts.",
    "due_date": "2026-10-12",
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
- **Validaciones en Backend**:
  - `csrf_token`: Obligatorio y válido contra la sesión activa.
  - `title`: Obligatorio, cadena no vacía (trim), longitud de 1 a 200 caracteres.
  - `description`: Opcional, texto plano (hasta 2000 caracteres). Caracteres especiales son escapados para neutralizar XSS; se preservan saltos de línea.
  - `due_date`: Opcional, formato de fecha válido (`YYYY-MM-DD`). Se admiten fechas pasadas, presentes o futuras.
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/tasks` con mensaje flash `"Tarea creada exitosamente."`.
  - `201 Created` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Tarea creada exitosamente",
      "data": {
        "id": 1,
        "title": "Implementar endpoints de tareas",
        "description": "Texto plano sin etiquetas HTML ni scripts.",
        "due_date": "2026-10-12",
        "status": "pending",
        "created_at": "2026-10-06T15:00:00Z"
      }
    }
    ```
  - `400 Bad Request` (Error de validación de campos):
    ```json
    {
      "status": "error",
      "code": "VALIDATION_ERROR",
      "message": "El título es obligatorio y no puede estar vacío.",
      "errors": {
        "title": ["El título es obligatorio."]
      }
    }
    ```
  - `400 Bad Request` (Fallo de protección CSRF):
    ```json
    {
      "status": "error",
      "code": "CSRF_ERROR",
      "message": "Token CSRF ausente o inválido."
    }
    ```
  - `401 Unauthorized`: Acceso denegado por falta de sesión activa.

---

## 3. Edición de Tareas (`HU-04`)

### 3.1 `GET /tasks/<int:task_id>/edit`
- **Descripción**: Muestra la interfaz con el formulario prellenado para editar una tarea existente.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Respuestas**:
  - `200 OK`: Renderiza plantilla `tasks/edit.html` con los datos de la tarea y el campo oculto con `csrf_token()`.
  - `404 Not Found` / `403 Forbidden`: Si la tarea no existe o no pertenece al usuario autenticado.

### 3.2 `POST /tasks/<int:task_id>/edit`
- **Descripción**: Actualiza los atributos de una tarea (título, descripción, fecha límite) preservando su estado actual y registrando el evento de auditoría (`TASK_UPDATED`).
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida (`csrf_token` en formulario o `X-CSRFToken` en cabecera HTTP).
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "title": "Título actualizado de la tarea",
    "description": "Nueva descripción en texto plano.",
    "due_date": "2026-10-20",
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/tasks` con mensaje flash `"Tarea actualizada exitosamente."`.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Tarea actualizada exitosamente",
      "data": {
        "id": 1,
        "title": "Título actualizado de la tarea",
        "description": "Nueva descripción en texto plano.",
        "due_date": "2026-10-20",
        "status": "pending",
        "updated_at": "2026-10-06T15:30:00Z"
      }
    }
    ```
  - `400 Bad Request` (Error de validación): Título vacío, longitud excedida o formato de fecha inválido.
  - `400 Bad Request` (Fallo de protección CSRF):
    ```json
    {
      "status": "error",
      "code": "CSRF_ERROR",
      "message": "Token CSRF ausente o inválido."
    }
    ```
  - `403 Forbidden` / `404 Not Found`: Tarea no encontrada o perteneciente a otro usuario (cero fuga de datos).

---

## 4. Transición de Estado de Tareas (`HU-03`)

### 4.1 `POST /tasks/<int:task_id>/status`
- **Descripción**: Modifica el estado del ciclo de vida de la tarea según la máquina de estados permitida y genera un evento de auditoría (`TASK_STATUS_CHANGED`).
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida (`csrf_token` en formulario o `X-CSRFToken` en cabecera HTTP).
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "status": "in_progress",
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
- **Valores admitidos para `status`**: `'pending'`, `'in_progress'`, `'completed'`.
- **Transiciones válidas**:
  - `pending` $\rightarrow$ `in_progress` | `completed`
  - `in_progress` $\rightarrow$ `pending` | `completed`
- **Transiciones rechazadas**:
  - `completed` $\rightarrow$ cualquier estado (rechazada con 400 en este incremento; requiere reapertura HU-06).
  - Estado actual $\rightarrow$ mismo estado (rechazada con 400).
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/tasks` tras actualizar el estado.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Estado de la tarea actualizado exitosamente",
      "data": {
        "id": 1,
        "old_status": "pending",
        "new_status": "in_progress"
      }
    }
    ```
  - `400 Bad Request` (Transición inválida):
    ```json
    {
      "status": "error",
      "code": "INVALID_STATE_TRANSITION",
      "message": "No se permite cambiar el estado de una tarea completada en este incremento."
    }
    ```
  - `400 Bad Request` (Fallo de protección CSRF):
    ```json
    {
      "status": "error",
      "code": "CSRF_ERROR",
      "message": "Token CSRF ausente o inválido."
    }
    ```
  - `403 Forbidden` / `404 Not Found`: Tarea no encontrada o no perteneciente al usuario autenticado.
