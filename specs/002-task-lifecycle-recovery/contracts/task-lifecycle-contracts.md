# Contratos HTTP: Cierre de Ciclo de Vida de Tareas (HU-05, HU-06)

**Feature**: `002-task-lifecycle-recovery`  
**Date**: 2026-10-07  
**Principio Constitucional**: III (Contrato explícito previo a la implementación) y VII (Seguridad por defecto)  

---

## 0. Política de Seguridad y CSRF

En cumplimiento del Principio VII, todos los endpoints mutantes con método POST descritos en este documento exigen:
- **Autenticación activa**: Requieren `@login_required`. Si no hay sesión, devuelven redirección (302) a `/login` o `401 Unauthorized`.
- **Protección CSRF**: En formularios HTML se requiere el campo `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`. En peticiones asíncronas vía `fetch` o clientes API se requiere el encabezado `X-CSRFToken` o el campo `"csrf_token"` en el cuerpo.
- **Fallo de CSRF**: Responde `400 Bad Request` con payload:
  ```json
  {
    "status": "error",
    "code": "CSRF_ERROR",
    "message": "Token CSRF ausente o inválido."
  }
  ```

---

## 1. Eliminación Lógica de Tareas (`HU-05`)

### 1.1 `POST /tasks/<int:task_id>/delete`
- **Descripción**: Marca lógicamente una tarea como eliminada (`is_deleted=True`, `deleted_at=utcnow`) preservando su fila en base de datos y su historial de auditoría. La tarea deja de aparecer en el listado por defecto.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida.
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
  *(En peticiones fetch/JSON puede enviarse únicamente el encabezado `X-CSRFToken` sin cuerpo).*
- **Validaciones en Backend**:
  - `csrf_token`: Obligatorio y válido contra la sesión activa.
  - La tarea debe pertenecer al usuario autenticado.
  - La tarea NO debe encontrarse previamente eliminada (`task.is_deleted == False`).
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/tasks` con mensaje flash `"Tarea eliminada exitosamente."`.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Tarea eliminada exitosamente",
      "data": {
        "id": 10,
        "is_deleted": true,
        "deleted_at": "2026-10-07T18:30:00Z"
      }
    }
    ```
  - `400 Bad Request` (Tarea ya eliminada):
    ```json
    {
      "status": "error",
      "code": "TASK_ALREADY_DELETED",
      "message": "La tarea ya ha sido eliminada previamente."
    }
    ```
  - `401 Unauthorized`: Sin sesión activa en el backend.
  - `403 Forbidden` / `404 Not Found`: Si la tarea no existe o pertenece a otro usuario (cero fuga de información).

---

## 2. Reapertura de Tareas Completadas (`HU-06`)

### 2.1 `POST /tasks/<int:task_id>/reopen`
- **Descripción**: Reabre una tarea que fue completada por error, transicionándola al estado activo `'pending'` y generando el evento de auditoría específico `TASK_REOPENED`.
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
  - La tarea debe pertenecer al usuario autenticado.
  - La tarea NO debe estar eliminada lógicamente (`is_deleted == False`).
  - La tarea debe encontrarse actualmente en estado `'completed'`.
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/tasks` con mensaje flash `"Tarea reabierta exitosamente."`.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Tarea reabierta exitosamente",
      "data": {
        "id": 10,
        "previous_status": "completed",
        "new_status": "pending"
      }
    }
    ```
  - `400 Bad Request` (Estado inválido para reapertura):
    ```json
    {
      "status": "error",
      "code": "INVALID_STATE_TRANSITION",
      "message": "Solo las tareas en estado completado pueden ser reabiertas."
    }
    ```
  - `400 Bad Request` (Tarea eliminada):
    ```json
    {
      "status": "error",
      "code": "TASK_ALREADY_DELETED",
      "message": "No se puede reabrir una tarea que ha sido eliminada."
    }
    ```
  - `401 Unauthorized`: Sin sesión activa.
  - `403 Forbidden` / `404 Not Found`: Tarea inexistente o perteneciente a otro usuario.
