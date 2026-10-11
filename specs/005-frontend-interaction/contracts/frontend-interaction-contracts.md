# Contratos HTTP: Interactividad Frontend y Reordenamiento Persistente (HU-15, HU-16)

**Feature**: `005-frontend-interaction`  
**Date**: 2026-10-08  
**Principios Constitucionales**: III (Contrato explícito previo a la implementación) y VII (Seguridad por defecto)  

---

## 0. Política Global de Seguridad y Protección CSRF

En cumplimiento del Principio VII, **todas las peticiones asíncronas mutantes (`fetch`)** ejecutadas desde JavaScript exigen:
- **Autenticación activa**: Sesión verificada en el backend vía `@login_required`.
- **Encabezado `X-CSRFToken`**: Inyectado obligatoriamente en cada llamada `fetch`, extrayéndolo de `<meta name="csrf-token" content="{{ csrf_token() }}">` en `base.html`.
- **Formato**: `Content-Type: application/json`.
- **Fallo CSRF**: Retorna código HTTP `400 Bad Request` (`CSRF_ERROR`).

---

## 1. Completar Tarea de Forma Asíncrona (`HU-15`)

### 1.1 `POST /tasks/<int:task_id>/status` (Reutilización del Endpoint Existente)
- **Descripción**: Actualiza el estado de una tarea a `'completed'` mediante una llamada asíncrona sin recargar la página. Si la petición falla, el cliente JavaScript revierte el cambio visual optimista y presenta una alerta de error.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Encabezados HTTP Requeridos**:
  - `Content-Type: application/json`
  - `X-CSRFToken: <token_csrf>`
- **Payload de Entrada (JSON)**:
  ```json
  {
    "status": "completed"
  }
  ```
- **Validaciones en Backend**:
  - Tarea debe existir y pertenecer al usuario (o estar asignada a él).
  - Tarea no debe estar eliminada lógicamente (`is_deleted == False`).
  - La transición debe ser válida según la máquina de estados.
- **Respuestas**:
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Estado de la tarea actualizado exitosamente",
      "data": {
        "id": 15,
        "status": "completed",
        "previous_status": "in_progress",
        "is_overdue": false
      }
    }
    ```
  - `400 Bad Request` (Transición inválida o CSRF):
    ```json
    {
      "status": "error",
      "code": "INVALID_STATE_TRANSITION",
      "message": "Transición de estado no permitida."
    }
    ```
  - `401 Unauthorized`: Sesión expirada o no iniciada.
  - `404 Not Found`: Tarea inexistente o ajena.

---

## 2. Persistencia del Reordenamiento tras Arrastrar y Soltar (`HU-16`)

### 2.1 `POST /tasks/reorder`
- **Descripción**: Recibe la lista ordenada de identificadores de tareas tras una acción de arrastrar y soltar (*drag and drop*) en el cliente, y actualiza de forma atómica el campo `position` de cada una en la base de datos relacional.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida (`X-CSRFToken`).
- **Payload de Entrada (JSON)**:
  ```json
  {
    "task_ids": [15, 12, 8, 3]
  }
  ```
- **Validaciones en Backend (Principio VII)**:
  - `task_ids`: Lista no vacía de números enteros.
  - **Aislamiento e Integridad por Usuario**: El servicio verifica que **el 100% de las tareas** referenciadas en `task_ids` pertenezcan al usuario autenticado (`user_id == current_user.id`) y no estén eliminadas.
  - Si se detecta un identificador inexistente o perteneciente a otro usuario, la petición es rechazada de inmediato con `403 Forbidden` (`TASK_ACCESS_DENIED`) y se aborta la transacción sin alterar ninguna posición.
- **Comportamiento en Base de Datos**:
  - Se asigna `position = 0` al primer elemento de la lista, `position = 1` al segundo, y así sucesivamente.
  - La actualización se confirma de forma atómica (`db.session.commit()`).
- **Respuestas**:
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Orden de tareas guardado exitosamente",
      "data": {
        "reordered_count": 4
      }
    }
    ```
  - `400 Bad Request` (Payload malformado o lista vacía):
    ```json
    {
      "status": "error",
      "code": "INVALID_PAYLOAD",
      "message": "Se requiere una lista válida de identificadores de tareas."
    }
    ```
  - `403 Forbidden` (Intento de reordenar tareas de otro usuario):
    ```json
    {
      "status": "error",
      "code": "TASK_ACCESS_DENIED",
      "message": "Una o más tareas no pertenecen al usuario autenticado."
    }
    ```

---

## 3. Extensión del Criterio de Ordenamiento en `GET /tasks`

### 3.1 Consulta de Listado Predeterminado
- Cuando el usuario consulta `/tasks` sin seleccionar un ordenamiento explícito por prioridad (`sort_by=priority`), el backend aplica como criterio principal la posición manual guardada:
  ```sql
  ORDER BY tasks.position ASC, tasks.created_at DESC
  ```
- Esto garantiza que al recargar la página (F5) o ingresar desde otra sesión, las tareas se presenten exactamente en el orden posicional establecido por el usuario mediante drag-and-drop.
