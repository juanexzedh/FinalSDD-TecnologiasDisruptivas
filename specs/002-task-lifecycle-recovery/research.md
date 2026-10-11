# Research & Technical Decisions: Incremento 2 TaskControl

**Feature**: `002-task-lifecycle-recovery` (Cierre de gestión básica de tareas y recuperación de acceso)  
**Date**: 2026-10-07  
**Status**: Completed  

---

## 1. Estrategia de Soft Delete en SQLAlchemy y Preservación de Auditoría (HU-05)

### Contexto y Requisitos
El Principio VI y el requerimiento funcional FR-001/FR-002 exigen que la eliminación de tareas sea puramente lógica (soft delete) para garantizar la integridad referencial y la continuidad del log de auditoría. Además, una tarea eliminada no debe aparecer en el listado por defecto (HU-02) ni permitir posteriores mutaciones (edición, cambio de estado, reapertura o re-eliminación).

### Decisión
1. **Extensión del Modelo `Task`**:
   - Agregar columnas:
     - `is_deleted`: `Boolean`, por defecto `False`, no nulo (`nullable=False`, `server_default='0'`).
     - `deleted_at`: `DateTime(timezone=True)`, nulo por defecto (`nullable=True`), poblado con la marca temporal UTC en el momento de la eliminación.
   - Agregar índice compuesto `ix_tasks_user_id_is_deleted` sobre `(user_id, is_deleted)` para optimizar las consultas de filtrado por usuario sin penalizar el rendimiento.
2. **Encapsulamiento en la Capa de Servicios (`TaskService`)**:
   - `get_user_tasks(user_id, status_filter='all')`: Añade explícitamente el filtro `Task.is_deleted == False` a la consulta base de SQLAlchemy. Todas las vistas y endpoints existentes continúan funcionando de forma transparente excluyendo las tareas eliminadas.
   - `delete_task(user_id, task_id)`:
     - Consulta la tarea por `id` y `user_id`.
     - Si no existe: lanza `TaskNotFoundError` (HTTP 404).
     - Si `task.is_deleted` ya es `True`: lanza `TaskAlreadyDeletedError` (HTTP 400), impidiendo re-eliminaciones.
     - Marca `task.is_deleted = True` y `task.deleted_at = datetime.now(timezone.utc)`.
     - Registra el evento en `AuditService.record_task_event(actor_id=user_id, action='TASK_DELETED', task_id=task.id)`.
   - `update_task` y `change_task_status`: Verifican que `task.is_deleted == False`. Si la tarea está eliminada, rechazan la operación lanzando `TaskAlreadyDeletedError` o `TaskNotFoundError`.

### Justificación frente al Principio V (Simplicidad)
- *Alternativas rechazadas*:
  - **Extensiones complejas de Soft Delete (SQLAlchemy ORM events con interceptores globales `before_compile` o plugins como `sqlalchemy-easy-softdelete`)**: Introducen magia implícita, dificultan la depuración y generan problemas cuando consultas administrativas o de auditoría necesitan inspeccionar tareas eliminadas.
  - **Mover filas a una tabla separada `deleted_tasks`**: Rompe claves foráneas, fragmenta el esquema y complica innecesariamente las migraciones.
- *Solución elegida*: Dos columnas nativas (`is_deleted`, `deleted_at`) filtradas de manera explícita en `TaskService`. Código directo, legible y 100% predecible sin abstracciones ocultas.

---

## 2. Máquina de Estados, Transición de Reapertura y Auditoría Distinguible (HU-06)

### Contexto y Requisitos
En el Incremento 1, la máquina de estados prohibía explícitamente cualquier transición desde `completed` hacia otro estado (rechazada con 400). El requerimiento HU-06 y el Principio VIII exigen permitir reabrir tareas completadas por error devolviéndolas a un estado activo, pero con la condición estricta de que el evento quede registrado en auditoría como `TASK_REOPENED`, diferenciado de una creación (`TASK_CREATED`) y de un cambio ordinario de estado (`TASK_STATUS_CHANGED`).

### Decisión
1. **Transición Habilitada en la Máquina de Estados**:
   - Se formaliza la transición específica: `completed` $\rightarrow$ `pending`.
   - Estado activo de destino: Se fija deterministamente en `pending`.
2. **Separación de Responsabilidades en Endpoints y Servicios**:
   - `change_task_status(user_id, task_id, new_status)`: **Mantiene bloqueada** la transición desde `completed`. Si un usuario intenta enviar un POST ordinario a `/tasks/<id>/status` con una tarea completada, se sigue rechazando con `400 Bad Request`.
   - Se crea el método de dominio dedicado `reopen_task(user_id, task_id)` en `TaskService`:
     - Valida que la tarea pertenezca al `user_id`.
     - Valida que `task.is_deleted == False`.
     - Valida que `task.status == 'completed'`. Si no está completada (e.g. está en `pending` o `in_progress`), rechaza la reapertura con `InvalidStateTransitionError` (HTTP 400).
     - Actualiza `task.status = 'pending'`.
     - Invoca `AuditService.record_task_event(actor_id=user_id, action='TASK_REOPENED', task_id=task.id, details={'previous_status': 'completed', 'new_status': 'pending'})`.
   - Se crea el endpoint HTTP dedicado: `POST /tasks/<int:task_id>/reopen` protegido con CSRF.

### Justificación frente al Principio V (Simplicidad)
- Separar la acción `reopen_task` en un método y endpoint dedicados evita sobrecargar la lógica de `change_task_status` con banderas booleanas condicionales (`is_reopening=True`) y asegura a nivel de diseño que ningún cliente pueda generar una reapertura sin registrar la acción auditada `TASK_REOPENED`.

---

## 3. Modelo de Datos y Seguridad para Recuperación de Contraseña (HU-14)

### Contexto y Requisitos
El Principio VII (Seguridad por defecto) impone tres restricciones críticas:
1. Ningún secreto ni token debe almacenarse en texto plano en la base de datos ni en el repositorio.
2. La solicitud de recuperación no debe revelar si un correo electrónico existe o no en el sistema (prevención de enumeración de usuarios).
3. Los tokens deben ser de un solo uso y contar con expiración estricta.

### Decisión
1. **Generación Criptográfica y Almacenamiento de Tokens**:
   - Generación: Se utiliza `secrets.token_urlsafe(32)` de la biblioteca estándar de Python, produciendo una cadena aleatoria criptográficamente segura de alta entropía.
   - Almacenamiento: **Nunca se persiste el token en texto plano**. Se calcula su resumen hash `SHA-256` mediante `hashlib.sha256(raw_token.encode('utf-8')).hexdigest()` y se persiste en la columna `token_hash`.
   - El token en texto plano (`raw_token`) solo se emite al usuario en la URL del enlace de recuperación (`/reset-password/<raw_token>`).
2. **Modelo de Persistencia `PasswordResetToken`**:
   - Columnas:
     - `id`: Entero, clave primaria.
     - `user_id`: Entero, clave foránea a `users.id` con eliminación en cascada o restricción íntegra.
     - `token_hash`: `String(64)`, indexado y único.
     - `expires_at`: `DateTime(timezone=True)`, calculado como `utcnow() + timedelta(minutes=15)`.
     - `used_at`: `DateTime(timezone=True)`, nulo inicialmente; poblado con `utcnow()` al consumirse.
     - `created_at`: `DateTime(timezone=True)`.
3. **Estrategia de Expiración e Invalidación**:
   - **Vida útil**: 15 minutos desde la emisión.
   - **Uso único**: Un token es válido si y solo si `used_at IS NULL` y `expires_at > utcnow()`. Al completarse el cambio de contraseña, se marca `token.used_at = utcnow()`.
   - **Invalidación acumulativa**: Si un usuario solicita recuperación nuevamente, cualquier token anterior no usado emitido para dicho usuario se marca como invalidado (`expires_at = utcnow()`), garantizando que solo el enlace más reciente sea utilizable.
   - **Estrangulamiento silencioso (*silent throttling*)**: Si se reciben más de 3 solicitudes para el mismo correo en una ventana móvil de 15 minutos, el backend no emite nuevos tokens ni despacha correos adicionales, retornando la misma confirmación neutra para prevenir saturación de buzón y ataques de denegación de servicio sin revelar información sobre la existencia de cuentas.
4. **Revocación Global de Sesiones Activas (Principio VII)**:
   - Al completarse exitosamente el cambio de contraseña (`PASSWORD_RESET_COMPLETED`), el sistema incrementa `user.session_version += 1`.
   - El decorador `@login_required` valida que `session.get('session_version') == user.session_version`. Al incrementarse la versión en base de datos, todas las cookies de sesión activas en cualquier navegador o dispositivo quedan invalidadas de forma inmediata, forzando un nuevo inicio de sesión.
5. **Prevención de Enumeración de Cuentas (Blind Response)**:
   - Al recibir `POST /forgot-password`:
     - El endpoint normaliza el correo (`email.strip().lower()`).
     - Si el correo existe: valida el límite de tasa móvil (máx. 3 / 15 min), invalida tokens previos pendientes, genera el nuevo token de 15 min y emite el enlace.
     - Si el correo NO existe: no realiza inserción en BD, pero ejecuta una operación simulada (o hash dummy) para mantener un perfil de tiempo de respuesta indistinguible.
     - En ambos casos, el servidor responde exactamente con la misma redirección (HTTP 302 a `/login` con mensaje flash `"Si el correo está registrado en el sistema, recibirás instrucciones para restablecer tu contraseña"`) o `200 OK` genérico en API/JSON. Cero fuga de información.

### Justificación frente al Principio V (Simplicidad)
- Se utiliza `hashlib.sha256` nativo de Python para el almacenamiento del hash del token. A diferencia de contraseñas de usuario (que requieren algoritmos lentos como `scrypt`), los tokens de recuperación poseen alta entropía aleatoria nativa (256 bits), por lo que SHA-256 es computacionalmente eficiente, seguro y no requiere librerías adicionales.

---

## 4. Estrategia de Envío de Correo en Entorno Académico y de Desarrollo

### Contexto y Requisitos
Se requiere definir cómo se envían las instrucciones de restablecimiento de contraseña en desarrollo local, justificando la elección para el alcance de un proyecto académico monolítico.

### Decisión
1. **Emulación en Desarrollo mediante Logging de Consola (`ConsoleEmailSender`)**:
   - En el entorno de desarrollo y pruebas (`DevelopmentConfig`, `TestingConfig`), no se acopla un servicio de mensajería externo (como SendGrid, Mailgun o AWS SES) ni se exige configurar credenciales SMTP reales en `.env`.
   - La capa de servicios (`RecoveryService`) delega el envío en un componente desacoplado `EmailSender`.
   - En desarrollo, el `ConsoleEmailSender` formatea el mensaje y emite el enlace completo de restablecimiento directamente en la salida de consola y en el archivo de log estructurado (`logging.getLogger('taskcontrol.email')`):
     ```text
     [EMAIL SIMULADO] Para: usuario@ejemplo.com
     Asunto: Restablecimiento de contraseña - TaskControl
     Enlace: http://127.0.0.1:5000/reset-password/TOKEN_ALEATORIO_GENERADO
     Válido por 15 minutos.
     ```
2. **Justificación frente a la Naturaleza del Proyecto y Principio V**:
   - **Autonomía y Reproducibilidad**: Un estudiante, docente o evaluador puede clonar el repositorio, ejecutar `flask run` y probar la recuperación de contraseña de inmediato sin necesidad de crear cuentas en proveedores de correo, abrir puertos SMTP o sortear bloqueos de spam.
   - **Seguridad**: Evita el riesgo de incluir credenciales SMTP de cuentas personales o corporativas en variables locales.
   - **Principio V (Simplicidad)**: Resolver la entrega mediante logging local satisface completamente los criterios de prueba del MVP con cero líneas de configuración externa. La arquitectura permite sustituir `EmailSender` por una implementación SMTP en producción sin tocar la lógica de negocio.

---

## 5. Estrategia de Migraciones sobre Esquema Existente (Principio VI)

### Contexto y Requisitos
El Principio VI exige que cualquier alteración al esquema se realice mediante migraciones reproducibles y versionadas con Flask-Migrate (Alembic), garantizando que los datos existentes del Incremento 1 no se pierdan ni se corrompan.

### Decisión
1. Generar un script de migración versionado en `migrations/versions/`:
   `flask db migrate -m "add_soft_delete_and_password_reset"`
2. **Compatibilidad con Datos Existentes**:
   - `tasks.is_deleted`: Se define con valor predeterminado `server_default='0'` y `default=False`. Todas las tareas creadas en el Incremento 1 conservan automáticamente `is_deleted = False` tras la migración.
   - `tasks.deleted_at`: Columna nullable, nula para todas las tareas existentes.
   - Creación de tabla `password_reset_tokens`: Nueva tabla independiente con clave foránea hacia `users.id`.
3. **Índices de Optimización**:
   - Índice sobre `tasks (user_id, is_deleted)` para acelerar consultas filtradas de tareas activas.
   - Índice sobre `password_reset_tokens (token_hash)` para búsquedas de validación instantáneas.
4. **Flujo de Ejecución**:
   - Ejecución directa desde la raíz mediante `flask db upgrade`.

---

## 6. Pruebas Automatizadas Bloqueantes y TDD (Principio IV)

### Contexto y Requisitos
El Principio IV prohíbe admitir código de dominio sin pruebas automatizadas previas escritas bajo TDD (Red-Green-Refactor).

### Decisión
Se definen como **bloqueantes** las siguientes suites en `tests/unit/`:
1. **Pruebas de Soft Delete (`tests/unit/test_task_service.py`)**:
   - `test_soft_delete_task_marks_flag_and_timestamp`: Verifica que `delete_task` fija `is_deleted=True` y `deleted_at`.
   - `test_soft_deleted_tasks_excluded_from_listing`: Verifica que `get_user_tasks` nunca retorna tareas eliminadas.
   - `test_cannot_delete_already_deleted_task`: Verifica rechazo ante intento de re-eliminación.
   - `test_cannot_edit_deleted_task`: Verifica rechazo en `update_task` sobre tarea eliminada.
   - `test_cannot_change_status_of_deleted_task`: Verifica rechazo en `change_task_status` sobre tarea eliminada.
   - `test_soft_delete_records_audit_event`: Verifica emisión inmutable de `TASK_DELETED`.
2. **Pruebas de Reapertura (`tests/unit/test_task_service.py`)**:
   - `test_reopen_completed_task_transitions_to_pending`: Verifica cambio de `completed` a `pending`.
   - `test_reopen_task_records_distinct_audit_event`: Verifica que se emite `TASK_REOPENED` con metadatos específicos.
   - `test_cannot_reopen_pending_or_in_progress_task`: Verifica rechazo de reapertura sobre tareas no completadas.
   - `test_cannot_reopen_deleted_task`: Verifica rechazo de reapertura sobre tareas eliminadas.
3. **Pruebas de Recuperación de Acceso (`tests/unit/test_auth_service.py`)**:
   - `test_request_reset_unregistered_email_does_not_fail_nor_leak`: Verifica respuesta idéntica y cero token creado.
   - `test_request_reset_registered_email_creates_hashed_token`: Verifica creación de registro con hash SHA-256 y expiración a 15 minutos.
   - `test_reset_password_with_valid_token_updates_hash_and_invalidates`: Verifica cambio de contraseña e invalidación inmediata del token (`used_at`).
   - `test_reset_password_with_expired_token_fails`: Verifica rechazo cuando el tiempo de vigencia expiró.
   - `test_reset_password_with_already_used_token_fails`: Verifica rechazo cuando `used_at` ya está poblado.
   - `test_password_complexity_enforced_on_reset`: Verifica rechazo de contraseñas de menos de 8 caracteres o sin números.
