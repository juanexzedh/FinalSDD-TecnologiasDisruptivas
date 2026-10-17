# Contratos HTTP: Colaboración y Asignación de Tareas (HU-10)

**Feature**: `004-user-collaboration`  
**Date**: 2026-10-08  
**Principios Constitucionales**: III (Contrato explícito previo a la implementación) y VII (Seguridad por defecto)  

---

## 0. Política Global de Seguridad y Protección CSRF (Principio VII)

En estricto cumplimiento del Principio VII, **todas las peticiones mutantes con método POST** (`/tasks/<id>/assign`, etc.) exigen:
- **Autenticación activa**: Verificación mediante decorador `@login_required`.
- **Protección CSRF**: Campo `csrf_token` en formularios HTML o cabecera `X-CSRFToken` en peticiones fetch/JSON.
- **Fallo CSRF**: Retorna `400 Bad Request` con `"code": "CSRF_ERROR"`.

---

## 1. Asignación y Reasignación de Tareas (`HU-10`)

### 1.1 `POST /tasks/<int:task_id>/assign`
- **Descripción**: Asigna una tarea a otro usuario registrado mediante su correo electrónico exacto, la reasigna a otro usuario, o remueve la asignación (`assignee_email = ""` o `null`). Si la asignación es hacia un usuario distinto al actor, crea atómicamente una notificación interna para el nuevo asignatario. En reasignación o desasignación, emite adicionalmente una notificación de desasignación al usuario previo, registrando el evento correspondiente en `audit_logs` (`TASK_ASSIGNED` o `TASK_UNASSIGNED`).
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida.
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "assignee_email": "colaborador@empresa.com",
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
  *(En el formulario HTML se presenta un campo de texto simple `<input type="email" name="assignee_email">` sin autocompletado ni selectores para evitar la enumeración o fuga de correos de usuarios registrados conforme al Principio VII).*
- **Validaciones en Backend (Principio VII)**:
  - `csrf_token`: Obligatorio y válido contra la sesión activa.
  - La tarea debe existir y estar activa (`is_deleted == False`).
  - **Autorización (`FR-018`)**: El usuario en sesión DEBE ser exclusivamente el creador original de la tarea (`task.user_id == current_user.id`). Los asignatarios no tienen permitido reasignar ni desasignar tareas (HTTP `403 Forbidden`).
  - **Existencia del usuario destinatario**: Si `assignee_email` no está vacío, se busca en la tabla `users` tras aplicar `.strip().lower()`. Si no existe, se rechaza de inmediato con `400 Bad Request` (`USER_NOT_FOUND`). Queda terminantemente prohibido asignar a correos no registrados.
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/tasks` con mensaje flash `"Tarea asignada exitosamente a colaborador@empresa.com."` (o `"Asignación de la tarea removida exitosamente."`).
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Tarea asignada exitosamente",
      "data": {
        "task_id": 15,
        "assignee_id": 4,
        "assignee_email": "colaborador@empresa.com",
        "notifications_generated": {
          "new_assignee_notified": true,
          "previous_assignee_notified": false
        }
      }
    }
    ```
  - `400 Bad Request` (Usuario inexistente):
    ```json
    {
      "status": "error",
      "code": "USER_NOT_FOUND",
      "message": "El correo especificado no pertenece a ningún usuario registrado en el sistema."
    }
    ```
  - `403 Forbidden`: Si el usuario actual no es el creador de la tarea.
  - `404 Not Found`: Si la tarea no existe o está eliminada.

---

## 2. Listado Extendido de Tareas con Filtro de Procedencia (`HU-02`, `HU-10`)

### 2.1 `GET /tasks` (Ampliación)
- **Descripción**: Retorna las tareas del usuario autenticado, permitiendo filtrar por procedencia (`scope`) además de los filtros preexistentes de estado (`status`), categoría (`category_id`) y ordenamiento por prioridad (`sort_by`).
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Parámetros de Consulta (Query String)**:
  - `scope` (opcional, string):
    - `'all'` (defecto): Incluye tareas donde el usuario es el creador O el asignatario.
    - `'created'`: Incluye exclusivamente tareas creadas por el usuario actual (`creator_id == current_user.id`).
    - `'assigned'`: Incluye exclusivamente tareas asignadas al usuario actual por otros miembros (`assignee_id == current_user.id AND creator_id != current_user.id`).
  - `status` (opcional, string): `'all'`, `'pending'`, `'in_progress'`, `'completed'`.
  - `category_id` (opcional): `'all'`, `'none'`, `<int>`.
  - `sort_by` (opcional): `'created_desc'`, `'priority'`.
- **Estructura de Respuesta**:
  - Cada elemento del listado expone claramente quién es el creador y quién es el asignatario, permitiendo renderizar insignias visuales ("badge"):
    - `"is_assigned_to_me": true | false`
    - `"is_created_by_me": true | false`
    - `"creator_email": "autor@empresa.com"`
    - `"assignee_email": "colaborador@empresa.com" | null`
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "data": {
        "tasks": [
          {
            "id": 15,
            "title": "Auditoría de seguridad del monolito",
            "description": "Revisar decorators y CSRF",
            "due_date": "2026-10-18",
            "status": "in_progress",
            "priority": "high",
            "is_overdue": false,
            "creator_id": 1,
            "creator_email": "lider@empresa.com",
            "assignee_id": 2,
            "assignee_email": "auditor@empresa.com",
            "is_created_by_me": false,
            "is_assigned_to_me": true,
            "created_at": "2026-10-08T09:00:00Z"
          }
        ],
        "filters": {
          "scope": "all",
          "status": "all",
          "category_id": "all",
          "sort_by": "created_desc"
        },
        "total": 1
      }
    }
    ```

---

## 3. Matriz de Autorización de Endpoints para Tareas Delegadas (`FR-018`)

Conforme a la clarificación de requerimientos, la autorización sobre tareas delegadas se rige por la siguiente política estricta en la capa de servicios:

| Endpoint | Método | Autorizado para Creador (`user_id == current_user.id`) | Autorizado para Asignatario (`assignee_id == current_user.id`) | Código de Error ante no autorizados |
|---|---|---|---|---|
| `/tasks` | `GET` | **SÍ** (ve sus creadas) | **SÍ** (ve sus asignadas) | N/A (filtrado por scope) |
| `/tasks/<id>/status` | `POST` | **SÍ** | **SÍ** | `403 Forbidden` (`TaskAccessDeniedError`) |
| `/tasks/<id>/edit` | `POST` | **SÍ** | **NO** | `403 Forbidden` (`TaskAccessDeniedError`) |
| `/tasks/<id>/priority`| `POST` | **SÍ** | **NO** | `403 Forbidden` (`TaskAccessDeniedError`) |
| `/tasks/<id>/category`| `POST` | **SÍ** | **NO** | `403 Forbidden` (`TaskAccessDeniedError`) |
| `/tasks/<id>/assign`  | `POST` | **SÍ** | **NO** | `403 Forbidden` (`TaskAccessDeniedError`) |
| `/tasks/<id>/delete`  | `POST` | **SÍ** | **NO** | `403 Forbidden` (`TaskAccessDeniedError`) |

