# Feature Specification: Colaboración entre Usuarios (Asignación y Notificaciones Internas)

**Feature Branch**: `004-user-collaboration`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Especifica el cuarto incremento funcional de TaskControl: colaboración entre usuarios. Este incremento cubre HU-10 y HU-11 del backlog, y asume que los Incrementos 1 a 3 ya están implementados. Alcance funcional: 1. Asignación de tareas (HU-10): un usuario puede asignar una tarea propia a otro usuario existente del sistema (nunca a un correo que no esté registrado). El usuario asignado ve esa tarea en su propio listado de tareas, de la misma forma que ve las suyas propias — define si el listado distingue visualmente entre "mis tareas creadas" y "tareas asignadas a mí", o si se presentan sin distinción. El cambio de asignación queda registrado en el log de auditoría. 2. Notificación interna de asignación (HU-11): cuando a un usuario se le asigna una tarea, recibe una notificación dentro de la aplicación (no por correo ni push externo) que puede consultar sin tener que revisar manualmente el listado completo de tareas. Define cómo se marca una notificación como leída y si persiste tras leerse o se descarta. Fuera de alcance explícito de este incremento: interacción sin recarga de página y drag-and-drop (HU-15, HU-16), que se especifican en el incremento final. Esta especificación debe ser consistente con la constitución del proyecto: toda reasignación queda auditada con actor y timestamp (Principio VIII), y la verificación de que solo se puede asignar a usuarios existentes se valida en el backend, no solo en un selector del frontend (Principio VII)."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Delegación y Asignación de Tareas entre Usuarios Registrados (Priority: P1)

Como creador o responsable de una tarea, quiero asignar una tarea propia a otro usuario registrado en el sistema mediante su correo electrónico, para delegar formalmente la responsabilidad de su ejecución garantizando que la asignación solo se concrete si el destinatario realmente existe en la plataforma.

**Why this priority**: Es el núcleo funcional de la colaboración en equipo (HU-10). Permite distribuir la carga de trabajo entre miembros registrados y sienta las bases de propiedad compartida y visibilidad mutua sobre las tareas.

**Independent Test**: Puede probarse de forma aislada registrando dos usuarios ("Usuario A" y "Usuario B"), creando una tarea con Usuario A, asignándola al correo de Usuario B, verificando que la asignación se guarda correctamente con evento en el log de auditoría, e intentando asignar una tarea a un correo inexistente ("nadie@correo.com") comprobando que el backend rechaza la operación con error explícito de validación sin alterar la tarea.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado ("Usuario A") que es propietario de una tarea activa, **When** accede a la acción de asignación e ingresa el correo de otro usuario existente ("Usuario B"), **Then** el sistema asigna la tarea a Usuario B, persiste el cambio y registra un evento de auditoría `TASK_ASSIGNED` que incluye el identificador de Usuario A como autor, Usuario B como asignatario y la marca temporal en UTC.
2. **Given** un usuario autenticado intentando asignar una tarea, **When** suministra un correo electrónico que no corresponde a ningún usuario registrado en la base de datos, **Then** el backend rechaza la solicitud con código de error de validación, no modifica la tarea y notifica al usuario que el destinatario no existe en el sistema.
3. **Given** una tarea previamente asignada a "Usuario B", **When** su creador ("Usuario A") decide remover la asignación dejándola sin asignar, **Then** el sistema desvincula el asignatario (`assignee = null`), preserva la tarea y registra el evento de auditoría `TASK_UNASSIGNED`.
4. **Given** un usuario autenticado ("Usuario A") creando una nueva tarea, **When** especifica un usuario asignatario válido desde el formulario de creación, **Then** la tarea se crea vinculando a Usuario A como creador (`creator_id`) y a Usuario B como asignatario (`assignee_id`).
5. **Given** un usuario que no es ni creador ni asignatario actual de una tarea, **When** intenta forzar una asignación sobre ella, **Then** el sistema deniega el acceso con error de autorización protegiendo la integridad del recurso.

---

### User Story 2 - Visualización y Distinción en el Listado de Tareas Asignadas (Priority: P1)

Como usuario que ha recibido tareas asignadas por otros miembros del equipo, quiero ver esas tareas en mi listado de trabajo con una clara distinción visual respecto a mis tareas creadas por mí mismo, y poder filtrar entre "Mis tareas creadas" y "Tareas asignadas a mí", para organizar eficientemente mis responsabilidades personales frente a las delegadas.

**Why this priority**: Complemento directo e indispensable de HU-10. Sin visibilidad clara en el listado del asignatario, la delegación es inútil. La distinción visual previene confusiones sobre el origen de cada tarea.

**Independent Test**: Puede probarse creando la Tarea 1 con Usuario A, la Tarea 2 con Usuario B asignada a Usuario A, e ingresando con la sesión de Usuario A para verificar que ambas tareas aparecen en el listado general, que la Tarea 2 posee una insignia visual indicando "Asignada por Usuario B", y que al aplicar el filtro "Asignadas a mí" solo se visualiza la Tarea 2.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado consultando su listado de tareas (`/tasks`), **When** tiene tanto tareas creadas por él como tareas asignadas por otros usuarios, **Then** el listado consolidado muestra ambos conjuntos de tareas activas, distinguiendo cada elemento mediante una insignia ("badge") visual que indica claramente si fue "Creada por mí" o "Asignada por [correo del creador]".
2. **Given** un usuario en su listado de tareas, **When** selecciona el filtro de procedencia "Asignadas a mí", **Then** el listado muestra exclusivamente las tareas activas donde el usuario actual figura como asignatario y cuyo creador es otro usuario.
3. **Given** un usuario en su listado de tareas, **When** selecciona el filtro de procedencia "Creadas por mí", **Then** el listado muestra únicamente las tareas donde el usuario actual es el autor original (`creator_id`).
4. **Given** un usuario aplicando filtros de procedencia ("Asignadas a mí" o "Creadas por mí"), **When** combina este filtro con ordenamiento por prioridad o filtros de estado (`pending`, `completed`), **Then** el sistema responde con la intersección exacta de dichos criterios sin romper los filtros preexistentes.
5. **Given** una tarea asignada que supera su fecha límite sin completarse, **When** el usuario asignado consulta su listado, **Then** el indicador de vencida (`is_overdue = true`) se expone idénticamente que en las tareas creadas por él.

---

### User Story 3 - Notificaciones Internas de Asignación y Gestión de Lectura (Priority: P2)

Como usuario asignatario, quiero recibir una notificación dentro de la aplicación cada vez que otro miembro me asigna una tarea, y poder consultar mis notificaciones en un apartado centralizado marcándolas como leídas, para enterarme oportunamente del trabajo recibido sin necesidad de revisar manualmente todo el listado de tareas.

**Why this priority**: Satisface el requerimiento HU-11 de alertar de forma oportuna y no invasiva. Es una característica autónoma dentro del monolito que no depende de proveedores externos de correo ni de mensajería push.

**Independent Test**: Puede probarse cuando Usuario A asigna una tarea a Usuario B: comprobar que en la barra de navegación de Usuario B aparece un contador de notificaciones pendientes (1), acceder a la vista de notificaciones (`/notifications`), verificar el mensaje detallado con el título de la tarea y el autor, marcar la notificación como leída y constatar que el contador se actualiza a 0 mientras la notificación permanece guardada en el historial.

**Acceptance Scenarios**:

1. **Given** un usuario ("Usuario A") que asigna una tarea a otro usuario ("Usuario B"), **When** la asignación es procesada exitosamente en el servidor, **Then** el sistema genera automáticamente una notificación interna vinculada a Usuario B que incluye: título de la tarea, correo del usuario que asignó, fecha/hora y estado no leído (`is_read = false`).
2. **Given** un usuario que se asigna o reasigna una tarea a sí mismo, **When** se completa la operación, **Then** el sistema NO genera notificación interna para evitar alertas redundantes y ruido operativo.
3. **Given** un usuario autenticado navegando en la aplicación, **When** posee notificaciones no leídas, **Then** la barra de navegación exhibe un indicador visual prominente (contador numérico) con la cantidad de notificaciones pendientes de lectura.
4. **Given** un usuario en la vista de notificaciones (`/notifications`), **When** hace clic en "Marcar como leída" en una notificación o hace clic en el enlace para ir a la tarea referenciada, **Then** la notificación pasa al estado leído (`is_read = true`, con `read_at`), el contador del menú decrece, y **la notificación permanece en el historial** (persiste, no se destruye automáticamente).
5. **Given** un usuario con múltiples notificaciones no leídas, **When** ejecuta la acción "Marcar todas como leídas", **Then** todas sus notificaciones activas se actualizan a leídas de manera simultánea.
6. **Given** un usuario revisando su historial de notificaciones, **When** decide voluntariamente eliminar una notificación leída mediante la acción "Eliminar notificación", **Then** el sistema remueve dicha notificación de su historial de forma segura.

---

### Edge Cases

- **Asignación al propio usuario creador**: Un usuario puede asignarse una tarea a sí mismo (e.g., auto-asignación tras crearla desasignada). En este escenario la asignación se persiste normalmente y se audita, pero no se emite ninguna notificación interna al mismo actor.
- **Reasignación sucesiva de una tarea**: Si una tarea asignada a Usuario B es reasignada posteriormente a Usuario C, Usuario C recibe una nueva notificación interna de asignación informándole que Usuario A le ha delegado la tarea. La notificación previa de Usuario B en su bandeja histórica permanece inalterada como constancia de la asignación anterior.
- **Intento de asignar ingresando correos con espacios o mayúsculas**: El sistema aplica normalización (`strip` y conversión a minúsculas) antes de contrastar contra la base de datos de usuarios registrados.
- **Eliminación lógica de una tarea asignada**: Si el creador elimina lógicamente una tarea que estaba asignada a otro usuario, la tarea deja de mostrarse en el listado del asignatario. La notificación histórica asociada permanece accesible en la bandeja del asignatario, pero al intentar acceder a la tarea se le informa que el recurso ya no se encuentra disponible.
- **Usuario asignado que es eliminado de la plataforma**: Si una cuenta de usuario es eliminada, cualquier tarea que tuviera asignada pasa de forma segura a estado no asignada (`assignee = null`), garantizando que la tarea y su creador original no sufran pérdida de datos ni inconsistencias referenciales.
- **Múltiples asignaciones de la misma tarea al mismo usuario**: Si se edita una tarea manteniendo al mismo asignatario sin cambios, no se generan notificaciones duplicadas ni eventos espurios en el log de auditoría.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a los usuarios asignar una tarea a un usuario registrado en la plataforma mediante su dirección de correo electrónico o su identificador (HU-10).
- **FR-002**: Toda asignación de tarea DEBE validarse rigurosamente en la capa de servicios del backend, rechazando categóricamente cualquier intento de asignación hacia una dirección de correo que no exista previamente en el sistema (Principio VII).
- **FR-003**: El sistema DEBE permitir que una tarea esté sin asignar (`assignee = null`) o asignada a exactamente un usuario registrado a la vez.
- **FR-004**: Toda mutación en la asignación de una tarea (asignación inicial, cambio de asignatario o remoción de asignación) DEBE registrarse de forma inmutable en el registro de auditoría (`audit_logs`) con marca temporal en UTC, actor responsable, identificador de la tarea y metadatos con el asignatario anterior y nuevo (Principio VIII).
- **FR-005**: El listado de tareas del usuario (`/tasks`) DEBE incluir tanto las tareas donde el usuario es el creador original (`creator_id`) como aquellas donde figura como asignatario activo (`assignee_id`), excluyendo las tareas eliminadas lógicamente.
- **FR-006**: El listado de tareas DEBE diferenciar visualmente las tareas creadas por el usuario de las tareas asignadas por terceros mediante una insignia ("badge") informativa en cada tarjeta/fila de tarea.
- **FR-007**: El listado de tareas DEBE ofrecer un filtro de procedencia (`scope`) con las opciones: `'all'` (todas: creadas y asignadas, valor por defecto), `'created'` (solo tareas creadas por el usuario) y `'assigned'` (solo tareas asignadas al usuario por terceros).
- **FR-008**: Los filtros de procedencia DEBEN combinarse ortogonalmente con los filtros por estado (`status`), filtros por categoría (`category_id`) y ordenamiento por prioridad (`sort_by`) definidos en los Incrementos 1 a 3.
- **FR-009**: Cuando una tarea es asignada o reasignada a un usuario distinto del actor que realiza la acción, el sistema DEBE generar de forma inmediata una notificación interna en la aplicación para el usuario asignatario (HU-11).
- **FR-010**: Las notificaciones internas DEBEN persistir en la base de datos relacional y asociarse unívocamente al usuario receptor, conteniendo mensaje, enlace a la tarea, fecha de creación y estado de lectura (`is_read`).
- **FR-011**: La interfaz de usuario DEBE exhibir en la barra de navegación un contador numérico con la cantidad de notificaciones no leídas (`is_read = false`) del usuario en sesión.
- **FR-012**: El sistema DEBE proporcionar una vista dedicada de notificaciones (`/notifications`) donde el usuario pueda consultar su historial de notificaciones ordenado cronológicamente (más recientes primero).
- **FR-013**: Las notificaciones consultadas DEBEN poder marcarse como leídas de forma individual (`POST /notifications/<id>/read`) o de forma colectiva (`POST /notifications/read-all`).
- **FR-014**: Al marcarse como leída, la notificación DEBE persistir en el historial del usuario con su marca de tiempo `read_at` (no se descarta ni se borra automáticamente), permitiendo al usuario consultar sus asignaciones previas.
- **FR-015**: El sistema DEBE permitir al usuario eliminar voluntariamente notificaciones de su bandeja (`POST /notifications/<id>/delete`).
- **FR-016**: La arquitectura de colaboración y notificaciones DEBE implementarse dentro del monolito estricto (Principio I), sin recurrir a servicios externos de correo, servidores WebSocket ni agentes de mensajería asíncrona.
- **FR-017**: **Límites de alcance explícitos**: Quedan expresamente fuera de este incremento: actualización dinámica sin recarga de página (HU-15) y reordenamiento manual mediante drag-and-drop (HU-16).

---

### Key Entities *(include if feature involves data)*

- **Tarea (`Task`) (Extendida)**:
  - Mantiene `user_id` (ahora explicitado como el autor/creador de la tarea).
  - Incorpora `assignee_id`: Clave foránea opcional a `users.id` con política de integridad `ON DELETE SET NULL`. Indica el usuario actualmente responsable de la tarea.
  - Relaciones: Vinculada al usuario creador (`creator`) y al usuario asignatario (`assignee`).
- **Notificación Interna (`Notification`) (Nueva Entidad)**:
  - Entidad relacional que representa un aviso generado dentro de la aplicación.
  - Atributos:
    - `id`: Identificador único (entero autoincremental).
    - `user_id`: Identificador del usuario destinatario (clave foránea a `users.id` con `ON DELETE CASCADE`).
    - `task_id`: Identificador de la tarea referenciada (clave foránea a `tasks.id` con `ON DELETE CASCADE` o `SET NULL`).
    - `title`: Título o resumen descriptivo de la notificación.
    - `message`: Contenido explicativo detallando quién asignó la tarea y el nombre de la misma.
    - `is_read`: Booleano que indica si la notificación ha sido leída (por defecto `False`).
    - `read_at`: Marca temporal en UTC en la que fue marcada como leída (nullable).
    - `created_at`: Marca temporal en UTC de emisión.
- **Registro de Auditoría (`AuditLog`) (Nuevos Eventos)**:
  - `TASK_ASSIGNED`: Registra la asignación o reasignación de una tarea con actor, tarea y detalles (`previous_assignee_id`, `new_assignee_id`).
  - `TASK_UNASSIGNED`: Registra la desasignación de una tarea dejándola sin responsable asignado.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los intentos de asignar una tarea a un correo no registrado son rechazados en el servidor con mensaje de validación descriptivo antes de cualquier mutación de datos.
- **SC-002**: El 100% de las tareas asignadas aparecen visiblemente en el listado del usuario asignatario sin requerir ninguna acción adicional por parte del receptor.
- **SC-003**: 0% de pérdida de notificaciones: toda asignación entre usuarios distintos genera con éxito una notificación persistida en la bandeja interna del destinatario en la misma transacción o inmediatamente posterior.
- **SC-004**: El 100% de los eventos de cambio de asignación quedan registrados en el log estructurado de auditoría con actor, timestamp y metadatos verificables.
- **SC-005**: Las notificaciones leídas permanecen accesibles en el historial del usuario con una tasa de retención del 100% hasta que el usuario decida eliminarlas de forma explícita.
- **SC-006**: Tiempo de respuesta de consulta de la bandeja de notificaciones y del listado combinado de tareas inferior a 100 ms para usuarios con hasta 1,000 registros.

---

## Assumptions

- Los Incrementos 1 (`001-core-task-auth`), 2 (`002-task-lifecycle-recovery`) y 3 (`003-task-organization-priority`) se encuentran completamente desarrollados y operativos.
- Cada tarea tiene exactamente un creador (`user_id` / creador original) y puede tener a lo sumo un asignatario (`assignee_id`), o ninguno. No se admite asignación compartida a múltiples usuarios sobre la misma tarea en este incremento.
- El usuario creador conserva siempre los privilegios de administración, edición, cambio de estado, eliminación lógica y reasignación de su tarea.
- El usuario asignado tiene permisos para visualizar la tarea, cambiar su estado (`pending`, `in_progress`, `completed`), y reabrirla si fue completada por él.
- El selector de asignación en la interfaz web permite ingresar el correo del usuario destinatario o seleccionarlo de un listado de usuarios del sistema si el contexto lo permite, pero la validación canónica de existencia siempre se ejecuta en el backend contra la tabla `users`.
- La auto-asignación (un usuario asignándose una tarea propia) es una operación válida de flujo de trabajo, pero se omite la generación de notificaciones internas para evitar alertas innecesarias sobre acciones propias.
- Las notificaciones internas no sustituyen a ningún servicio externo; residen íntegramente en la base de datos relacional de la aplicación monolítica.
- Todas las peticiones mutantes sobre notificaciones y asignaciones utilizan el método POST protegido con tokens sincronizadores CSRF conforme a la constitución.
