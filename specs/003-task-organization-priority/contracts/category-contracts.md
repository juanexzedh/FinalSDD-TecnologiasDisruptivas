# Contratos HTTP: Gestión de Categorías (HU-08)

**Feature**: `003-task-organization-priority`  
**Date**: 2026-10-07  
**Principio Constitucional**: III (Contrato explícito previo a la implementación) y VII (Seguridad por defecto)  

---

## 0. Política Global de Seguridad y Protección CSRF (Principio VII)

En estricto cumplimiento del Principio VII (Seguridad por defecto), **todas las peticiones mutantes con método POST** (`/categories`, `/categories/<int:category_id>/delete`) exigen:
- **Autenticación activa**: Verificación mediante decorador `@login_required`. Peticiones no autenticadas devuelven redirección (302) a `/login` o `401 Unauthorized` en JSON.
- **Validación CSRF**:
  - En formularios HTML (`application/x-www-form-urlencoded`): campo oculto `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
  - En peticiones asíncronas vía `fetch` / JSON: encabezado HTTP `X-CSRFToken` o campo `"csrf_token"` en el payload.
- **Respuesta ante fallo de CSRF (`400 Bad Request`)**:
  ```json
  {
    "status": "error",
    "code": "CSRF_ERROR",
    "message": "Token CSRF ausente o inválido."
  }
  ```

---

## 1. Listado de Categorías del Usuario (`HU-08`)

### 1.1 `GET /categories`
- **Descripción**: Retorna la colección de categorías pertenecientes exclusivamente al usuario autenticado, junto con el conteo de tareas activas asociadas.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Parámetros de Consulta**: Ninguno.
- **Respuestas**:
  - `200 OK` (Navegador): Renderiza la vista `categories/index.html` con la lista de categorías del usuario y el formulario para crear nuevas.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "data": {
        "categories": [
          {
            "id": 1,
            "name": "Trabajo",
            "task_count": 5,
            "created_at": "2026-10-07T10:00:00Z"
          },
          {
            "id": 2,
            "name": "Personal",
            "task_count": 2,
            "created_at": "2026-10-07T11:15:00Z"
          }
        ],
        "total": 2
      }
    }
    ```
  - `401 Unauthorized`:
    ```json
    {
      "status": "error",
      "code": "UNAUTHORIZED",
      "message": "Se requiere autenticación activa para consultar categorías."
    }
    ```

---

## 2. Creación de Categorías (`HU-08`)

### 2.1 `POST /categories`
- **Descripción**: Registra una nueva categoría asociada al usuario autenticado y genera un evento de auditoría (`CATEGORY_CREATED`).
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida.
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "name": "Finanzas",
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
- **Validaciones en Backend**:
  - `csrf_token`: Obligatorio y válido contra la sesión activa.
  - `name`: Obligatorio, cadena no vacía tras aplicar `.strip()`, longitud entre 1 y 50 caracteres.
  - **Unicidad por usuario**: No debe existir otra categoría activa para el mismo `user_id` con el mismo nombre (comparación insensible a mayúsculas/minúsculas).
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/categories` con mensaje flash `"Categoría 'Finanzas' creada exitosamente."`.
  - `201 Created` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Categoría creada exitosamente",
      "data": {
        "id": 3,
        "name": "Finanzas",
        "created_at": "2026-10-07T12:00:00Z"
      }
    }
    ```
  - `400 Bad Request` (Nombre inválido):
    ```json
    {
      "status": "error",
      "code": "INVALID_CATEGORY_NAME",
      "message": "El nombre de la categoría es obligatorio y debe contener entre 1 y 50 caracteres."
    }
    ```
  - `409 Conflict` (Nombre duplicado para este usuario):
    ```json
    {
      "status": "error",
      "code": "CATEGORY_ALREADY_EXISTS",
      "message": "Ya posee una categoría con el nombre especificado."
    }
    ```

---

## 3. Eliminación Segura de Categoría (`HU-08`)

### 3.1 `POST /categories/<int:category_id>/delete`
- **Descripción**: Elimina la categoría especificada. **Regla innegociable de negocio**: Esta acción **NUNCA** elimina en cascada las tareas asociadas. A nivel relacional (`ON DELETE SET NULL`), todas las tareas que pertenecían a esta categoría son automáticamente desvinculadas, quedando con `category_id = null`.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida.
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
- **Validaciones en Backend**:
  - `csrf_token`: Obligatorio y válido.
  - La categoría debe existir y pertenecer al usuario autenticado (`category.user_id == current_user.id`). Si pertenece a otro usuario, responde `404 Not Found` (aislamiento estricto, sin revelar existencia).
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/categories` con mensaje flash `"Categoría eliminada exitosamente. Las tareas asociadas fueron desvinculadas y preservadas intactas."`.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Categoría eliminada exitosamente. Tareas desvinculadas.",
      "data": {
        "deleted_category_id": 1,
        "unlinked_tasks_count": 5
      }
    }
    ```
  - `404 Not Found`:
    ```json
    {
      "status": "error",
      "code": "CATEGORY_NOT_FOUND",
      "message": "La categoría solicitada no existe o no tiene permisos para acceder a ella."
    }
    ```

---

## 4. Asignación de Tarea a Categoría (`HU-08`)

### 4.1 `POST /tasks/<int:task_id>/category`
- **Descripción**: Asigna una tarea a una categoría del usuario o la desvincula de cualquier categoría (`category_id = null`). Emite el evento de auditoría `TASK_CATEGORY_ASSIGNED`.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida.
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "category_id": 2,
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
  *(Para desvincular, se envía `"category_id": null` o valor vacío `""`).*
- **Validaciones en Backend**:
  - `csrf_token`: Obligatorio y válido.
  - La tarea debe pertenecer al usuario autenticado y no estar eliminada (`is_deleted == False`).
  - Si `category_id` se proporciona (no nulo): la categoría DEBE existir y pertenecer al mismo usuario autenticado. Queda terminantemente prohibido asociar categorías de otros usuarios (HTTP 403/404).
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/tasks` con mensaje flash `"Categoría de la tarea actualizada exitosamente."`.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Categoría de la tarea actualizada exitosamente",
      "data": {
        "task_id": 10,
        "category_id": 2,
        "category_name": "Personal"
      }
    }
    ```
  - `400 Bad Request` / `404 Not Found` (Categoría ajena o inexistente):
    ```json
    {
      "status": "error",
      "code": "INVALID_CATEGORY",
      "message": "La categoría indicada no existe o no le pertenece."
    }
    ```
