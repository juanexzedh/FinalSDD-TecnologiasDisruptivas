# Research & Technical Decisions: Incremento 4 TaskControl

**Feature**: `004-user-collaboration` (Colaboración entre usuarios: asignación y notificaciones internas)  
**Date**: 2026-10-08  
**Status**: Completed  

---

## 1. Modelado de Propietario vs. Asignatario en la Entidad `Task` (HU-10)

### Contexto y Requisitos
El requerimiento HU-10 exige permitir que un usuario delegue una tarea propia a otro usuario registrado en la plataforma. Es necesario definir si el modelo de persistencia `Task` mantiene un campo separado para el asignatario o si se reinterpreta el campo `user_id` preexistente.

### Decisión
1. **Dos Columnas Separadas en `tasks`**:
   - `user_id` (conceptual: `creator_id`): Preserva su significado inalterado como la clave foránea obligatoria hacia `users.id` (`nullable=False`), identificando al autor original y propietario de la tarea.
   - `assignee_id`: Nueva columna opcional (`nullable=True`), clave foránea hacia `users.id` con cláusula `ON DELETE SET NULL`.
2. **Relaciones ORM**:
   ```python
   creator = db.relationship('User', foreign_keys=[user_id], backref=db.backref('created_tasks', lazy='dynamic'))
   assignee = db.relationship('User', foreign_keys=[assignee_id], backref=db.backref('assigned_tasks', lazy='dynamic'))
   ```
3. **Índice de Optimización**:
   - `ix_tasks_assignee_id` sobre `(assignee_id)` y `ix_tasks_assignee_id_is_deleted` sobre `(assignee_id, is_deleted)`.

### Rationale
- **Preservación de Auditoría y Propiedad**: Si se reescribiera `user_id`, se destruiría la información sobre quién creó la tarea, impidiendo saber a quién pertenecía si el asignatario renuncia a la tarea o si la cuenta del asignatario se elimina.
- **Seguridad y Control de Acceso (Principio VII)**: El creador conserva derechos de administración sobre su tarea (edición profunda, reasignación, eliminación lógica), mientras que el asignatario recibe permisos operativos (cambio de estado, reapertura).
- **Compatibilidad hacia atrás (Principio VI)**: Mantener `user_id` asegura que todas las consultas y datos de los Incrementos 1, 2 y 3 sigan funcionando exactamente igual.

### Alternativas Consideradas y Rechazadas
- **Reinterpretar `user_id` cambiando su valor al usuario asignado**: Violación grave de integridad histórica; impide que el creador mantenga control de sus tareas delegadas.
- **Tabla relacional intermedia muchos-a-muchos (`task_assignees`)**: Rechazada por YAGNI (Principio V). El requerimiento especifica que una tarea se asigna a máximo un usuario a la vez.

---

## 2. Entidad `Notification` y Flujo Atómico de Notificaciones (HU-11)

### Contexto y Requisitos
El requerimiento HU-11 exige que cuando un usuario recibe una tarea asignada, se le genere una notificación interna en la aplicación. La notificación debe poder consultarse, marcarse como leída y persistir en el historial del usuario.

### Decisión
1. **Entidad de Persistencia `Notification`**:
   - `id`: Entero, PK autoincremental.
   - `user_id`: Entero, FK a `users.id` con `ON DELETE CASCADE`. Destinatario de la alerta.
   - `task_id`: Entero, FK a `tasks.id` con `ON DELETE CASCADE`. Tarea referenciada.
   - `title`: `String(150)`, resumen de la notificación.
   - `message`: `String(500)`, detalle legible indicando quién asignó la tarea.
   - `is_read`: `Boolean`, por defecto `False`, `server_default='0'`.
   - `read_at`: `DateTime(timezone=True)`, fecha/hora en la que fue leída.
   - `created_at`: `DateTime(timezone=True)`, fecha/hora de emisión en UTC.
2. **Índices de Optimización**:
   - `ix_notifications_user_id_is_read` sobre `(user_id, is_read)` para que la consulta del contador del navbar (`unread_count`) se resuelva en $O(1)$ (< 5 ms).
3. **Punto y Atomicidad de Creación**:
   - La notificación se crea **en la misma transacción de base de datos** dentro de `TaskService.assign_task`:
     ```python
     task.assignee_id = assignee.id
     if assignee.id != actor_id:
         notification = Notification(
             user_id=assignee.id,
             task_id=task.id,
             title="Nueva tarea asignada",
             message=f"El usuario {actor.email} te ha asignado la tarea '{task.title}'."
         )
         db.session.add(notification)
     audit_service.record_task_event(actor_id, 'TASK_ASSIGNED', task.id, ...)
     db.session.commit()
     ```
   - Si cualquier paso falla, se ejecuta `rollback()`, asegurando atomicidad absoluta (o se asigna y notifica, o nada cambia).
4. **Regla de Auto-Asignación**:
   - Si un usuario se auto-asigna una tarea (`assignee.id == actor_id`), se actualiza la asignación y se audita, pero **no** se genera notificación interna para evitar alertas triviales y molestas al propio usuario.
5. **Persistencia tras Lectura**:
   - Marcar como leída (`POST /notifications/<id>/read`) no destruye la fila. Actualiza `is_read = True` y `read_at = utcnow()`. La notificación permanece accesible en el historial hasta que el usuario decida eliminarla de forma voluntaria.

### Justificación frente al Principio V (Simplicidad) y Principio I (Monolito)
- Implementar las notificaciones como una tabla relacional regular en SQLite/PostgreSQL respeta el monolito estricto. Se evitan sistemas de pub/sub desacoplados (Redis, RabbitMQ) o WebSockets complejos, manteniendo un modelo liviano basado en peticiones HTTP y renderizado en servidor.

---

## 3. Validación Estricta en Backend del Asignatario (Principio VII)

### Contexto y Requisitos
Solo se puede asignar a usuarios existentes en el sistema. Queda prohibido aceptar correos no registrados.

### Decisión
1. **Validación Canónica en Capa de Dominio (`TaskService`)**:
   - Se recibe el correo electrónico del asignatario (`assignee_email`).
   - Se aplica normalización: `.strip().lower()`.
   - Si el valor no está vacío:
     - Se consulta `User.query.filter_by(email=clean_email).first()`.
     - Si el usuario no existe, se lanza inmediatamente `UserNotFoundError("El correo especificado no pertenece a ningún usuario registrado en el sistema.")`.
     - Si existe, se vincula `assignee_id = target_user.id`.
   - Si el valor viene vacío o `None`, se desasigna la tarea (`assignee_id = None`) emitiendo `TASK_UNASSIGNED`.
2. **Defensa en Profundidad**:
   - Aunque la interfaz proporcione autocompletado o un desplegable con usuarios registrados, el backend siempre valida contra la base de datos, imposibilitando ataques de manipulación de peticiones HTTP o envíos forzados con curl/fetch.

---

## 4. Extensión del Endpoint de Listado de Tareas (`GET /tasks`)

### Contexto y Requisitos
El usuario asignado debe ver las tareas en su propio listado, con distinción visual y capacidad de filtrado por procedencia (`scope`).

### Decisión
1. **Parámetro `scope` en Query String**:
   - `scope='all'` (por defecto): `Task.query.filter(or_(Task.user_id == current_user.id, Task.assignee_id == current_user.id))`
   - `scope='created'`: `Task.query.filter(Task.user_id == current_user.id)`
   - `scope='assigned'`: `Task.query.filter(Task.assignee_id == current_user.id, Task.user_id != current_user.id)`
2. **Composición Ortogonal**:
   - Se encadena con `filter(Task.is_deleted == False)`, y con los filtros ya implementados:
     - `status`: `'all'`, `'pending'`, `'in_progress'`, `'completed'`
     - `category_id`: `'all'`, `'none'`, `<int>`
     - `sort_by`: `'created_desc'`, `'priority'`
3. **Cálculo de `is_overdue`**:
   - La propiedad calculada `@property is_overdue` opera idénticamente para tareas asignadas y creadas, evaluando en memoria si la fecha límite pasó sin completarse.
