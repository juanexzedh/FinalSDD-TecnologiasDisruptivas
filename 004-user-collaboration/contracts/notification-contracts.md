# Contratos HTTP: Notificaciones Internas (HU-11)

**Feature**: `004-user-collaboration`  
**Date**: 2026-10-08  
**Principios Constitucionales**: III (Contrato explícito previo a la implementación) y VII (Seguridad por defecto)  

---

## 0. Política Global de Seguridad y Protección CSRF

En cumplimiento del Principio VII, **todas las peticiones mutantes con método POST** (`/notifications/<id>/read`, `/notifications/read-all`, `/notifications/<id>/delete`) exigen:
- **Autenticación activa**: Sesión obligatoria vía `@login_required`.
- **Protección CSRF**: Campo `csrf_token` en formularios HTML o cabecera `X-CSRFToken` en peticiones fetch/JSON.
- **Aislamiento por usuario**: Un usuario solo puede visualizar, marcar o eliminar sus propias notificaciones (`notification.user_id == current_user.id`).

---

## 1. Listado de Notificaciones del Usuario (`HU-11`)

### 1.1 `GET /notifications`
- **Descripción**: Consulta el historial cronológico de notificaciones internas del usuario autenticado (más recientes primero) junto con el total de notificaciones no leídas (`unread_count`).
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Parámetros de Consulta**:
  - `status` (opcional, string): `'all'` (defecto), `'unread'`, `'read'`.
- **Tipos de Notificaciones Soportadas**:
  - **Asignación**: `title: "Nueva tarea asignada"`, mensaje: `"El usuario <creador> te ha asignado la tarea '<título>'."`
  - **Desasignación/Reasignación**: `title: "Asignación de tarea retirada"`, mensaje: `"El usuario <creador> ha retirado tu asignación de la tarea '<título>'."` o `"El usuario <creador> ha reasignado la tarea '<título>' a otro colaborador."`
- **Comportamiento con Tareas Eliminadas**:
  - Si la tarea fue eliminada lógicamente (`is_deleted=True`) o `task_id` es `null`, la notificación permanece intacta en el historial. La interfaz exhibe un indicador `"Tarea no disponible"`; cualquier intento de navegar a la tarea redirige con flash `"La tarea referenciada ha sido eliminada y ya no se encuentra disponible."`
- **Respuestas**:
  - `200 OK` (Navegador): Renderiza la plantilla `notifications/index.html` con la lista de notificaciones, enlaces a las tareas y botones de acción.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "data": {
        "notifications": [
          {
            "id": 101,
            "task_id": 15,
            "title": "Nueva tarea asignada",
            "message": "El usuario lider@empresa.com te ha asignado la tarea 'Auditoría de seguridad del monolito'.",
            "is_read": false,
            "read_at": null,
            "task_available": true,
            "created_at": "2026-10-08T09:00:00Z"
          },
          {
            "id": 88,
            "task_id": 12,
            "title": "Asignación de tarea retirada",
            "message": "El usuario lider@empresa.com ha retirado tu asignación de la tarea 'Revisión de documentación'.",
            "is_read": true,
            "read_at": "2026-10-07T14:20:00Z",
            "task_available": false,
            "created_at": "2026-10-07T14:00:00Z"
          }
        ],
        "unread_count": 1,
        "total": 2
      }
    }
    ```
  - `401 Unauthorized`: Si no hay sesión activa.

---

## 2. Marcar Notificación como Leída (`HU-11`)

### 2.1 `POST /notifications/<int:notification_id>/read`
- **Descripción**: Actualiza el estado de la notificación a leída (`is_read=True`, `read_at=utcnow`). **Regla innegociable**: La notificación **persiste** en el historial del usuario y NO se elimina.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida.
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
- **Validaciones en Backend**:
  - La notificación debe pertenecer al usuario autenticado. Si pertenece a otro usuario o no existe, responde `404 Not Found` (aislamiento estricto).
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/notifications` o a la tarea referenciada.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Notificación marcada como leída",
      "data": {
        "id": 101,
        "is_read": true,
        "read_at": "2026-10-08T09:30:00Z"
      }
    }
    ```

---

## 3. Marcar Todas las Notificaciones como Leídas (`HU-11`)

### 3.1 `POST /notifications/read-all`
- **Descripción**: Actualiza en lote todas las notificaciones pendientes del usuario actual marcándolas como leídas.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida.
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/notifications` con mensaje flash `"Todas las notificaciones fueron marcadas como leídas."`.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Todas las notificaciones fueron marcadas como leídas",
      "data": {
        "marked_count": 3
      }
    }
    ```

---

## 4. Eliminación Voluntaria de Notificación (`HU-11`)

### 4.1 `POST /notifications/<int:notification_id>/delete`
- **Descripción**: Permite al usuario eliminar voluntariamente una notificación de su bandeja histórica.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida.
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/notifications`.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Notificación eliminada exitosamente",
      "data": {
        "deleted_id": 101
      }
    }
    ```
