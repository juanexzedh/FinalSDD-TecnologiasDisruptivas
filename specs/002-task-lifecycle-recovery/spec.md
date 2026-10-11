# Feature Specification: Cierre de Gestión Básica de Tareas y Recuperación de Acceso

**Feature Branch**: `002-task-lifecycle-recovery`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Especifica el segundo incremento funcional de TaskControl: cierre de la gestión básica de tareas y recuperación de acceso. Este incremento cubre HU-05, HU-06 y HU-14 del backlog, y asume que el Incremento 1 (registro, login/logout, creación, listado, cambio de estado y edición de tareas) ya está implementado y en producción. Alcance funcional: 1. Eliminación de tareas (HU-05): un usuario elimina una tarea propia. La eliminación es lógica (soft delete), nunca física — la tarea deja de aparecer en el listado por defecto pero su registro y su historial de auditoría se preservan. No se permite eliminar una tarea que ya fue eliminada. 2. Reapertura de tareas (HU-06): un usuario reabre una tarea que había sido marcada como completada por error, devolviéndola a un estado activo. La reapertura queda registrada en el log de auditoría como un evento distinto de la creación original y distinto de un cambio de estado ordinario — debe poder distinguirse en el historial que esa tarea fue reabierta, no solo 'cambiada de estado'. 3. Recuperación de contraseña (HU-14): un usuario que olvidó su contraseña puede solicitar restablecerla mediante su correo registrado, sin que esto revele si ese correo existe o no en el sistema (para no filtrar qué correos están registrados). El mecanismo de restablecimiento debe invalidar la posibilidad de reutilizarse después de usado una vez o tras expirar. Fuera de alcance explícito de este incremento: prioridad y categorías de tareas (HU-07, HU-08), indicación de tareas vencidas (HU-09), asignación y notificaciones (HU-10, HU-11), interacción sin recarga de página y drag-and-drop (HU-15, HU-16). Esta especificación debe ser consistente con la constitución del proyecto: soft delete preserva el log de auditoría (Principio VI), toda transición de estado queda registrada (Principio VIII), y el mecanismo de recuperación de contraseña no introduce almacenamiento de secretos en texto plano ni en el repositorio (Principio VII)."

---

## Clarifications

### Session 2026-10-11

- Q: ¿La eliminación lógica de una tarea debe ser irreversible y definitiva para el usuario final, o debe contemplarse una funcionalidad de papelera y restauración? → A: Definitiva e irreversible para el usuario (la tarea no se puede restaurar ni vuelve a mostrarse en ninguna vista; el soft delete es exclusivamente para integridad referencial y auditoría).
- Q: ¿A qué estado del ciclo de vida debe retornar una tarea completada cuando se solicita su reapertura? → A: Siempre al estado "pending" (Pendiente): la acción transiciona la tarea completada exclusivamente a pendiente de forma determinista; el usuario puede pasarla a "en progreso" posteriormente mediante el flujo ordinario.
- Q: ¿Al completarse el restablecimiento exitoso de la contraseña se deben revocar e invalidar todas las sesiones activas previas del usuario en el sistema? → A: Revocar todas las sesiones activas: al actualizar exitosamente la contraseña, se invalidan de forma inmediata y global todas las sesiones previas del usuario en cualquier navegador o dispositivo, exigiendo iniciar sesión con la nueva credencial.
- Q: ¿Cuál debe ser el tiempo de expiración del enlace de restablecimiento y qué debe ocurrir con los enlaces previos si el usuario genera varias solicitudes sucesivas? → A: 15 minutos de vigencia e invalidación de solicitudes previas: el enlace expira a los 15 minutos; cada nueva solicitud de recuperación invalida de inmediato cualquier token previo no utilizado para esa cuenta (solo el enlace más reciente es utilizable).
- Q: ¿Se debe limitar la cantidad de solicitudes de recuperación de contraseña permitidas por correo electrónico para prevenir abusos y ataques de denegación de servicio? → A: Límite con estrangulamiento silencioso (máximo 3 solicitudes por correo cada 15 minutos): si se supera el umbral, el backend no emite más tokens pero retorna la misma confirmación neutra de éxito, preservando la confidencialidad absoluta (Principio VII).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Eliminación Lógica de Tareas Propias (Priority: P1)

Como usuario autenticado, quiero eliminar tareas mías que ya no son relevantes para mantener mi listado ordenado y libre de elementos obsoletos, con la seguridad de que el sistema preserva la integridad de los datos y el historial de auditoría sin borrarlos físicamente.

**Why this priority**: Cierra el ciclo de vida básico de una tarea personal junto con el Incremento 1 (crear, listar, cambiar estado, editar). Es indispensable para la higiene operativa del usuario y el cumplimiento del Principio VI (soft delete mandatorio para preservar la integridad referencial y auditoría). Cubre HU-05.

**Independent Test**: Puede probarse de forma aislada creando una tarea, ejecutando su eliminación lógica, verificando que desaparece del listado por defecto de tareas del usuario, confirmando que la fila permanece en la base de datos con su marca de borrado, y validando que se genera un evento de auditoría `TASK_DELETED` preservando todo su historial previo.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado con una tarea activa en su listado, **When** solicita eliminar dicha tarea, **Then** el sistema marca la tarea como eliminada lógicamente (soft delete), la remueve del listado estándar de tareas, preserva el registro en la base de datos y genera una entrada en el log de auditoría con la acción `TASK_DELETED`, el identificador de la tarea, el autor y la marca temporal (Principio VIII).
2. **Given** una tarea que ya ha sido eliminada lógicamente, **When** el usuario intenta enviar una solicitud para eliminarla nuevamente, **Then** el sistema rechaza la operación informando que la tarea ya se encuentra eliminada o no está disponible.
3. **Given** una tarea que ha sido eliminada lógicamente, **When** el usuario intenta editarla o modificar su estado, **Then** el sistema deniega terminantemente la acción conservando los datos inalterados.
4. **Given** un usuario autenticado, **When** intenta eliminar una tarea que pertenece a otro usuario, **Then** el sistema deniega el acceso sin modificar la tarea y sin filtrar información sobre la existencia de dicho recurso.

---

### User Story 2 - Reapertura Controlada de Tareas Completadas (Priority: P1)

Como usuario autenticado, quiero reabrir una tarea que fue marcada como completada por error o que requiere trabajo adicional, devolviéndola al estado activo "pendiente", de modo que en el historial y la auditoría se distinga explícitamente que fue un acto de reapertura y no un cambio ordinario de estado ni una tarea nueva.

**Why this priority**: Resuelve la restricción establecida en el Incremento 1 (donde las tareas completadas quedaban bloqueadas ante transiciones ordinarias). Proporciona el flujo formal y trazable para reactivar trabajo terminado según HU-06 y el Principio VIII de observabilidad.

**Independent Test**: Puede probarse de forma independiente tomando una tarea en estado "completada", solicitando su reapertura formal, verificando que su estado cambia a "pendiente", comprobando que aparece como activa en el listado filtrado, y constatando en el log de auditoría la presencia del evento específico `TASK_REOPENED`.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado con una tarea propia en estado "completada", **When** solicita reabrir la tarea, **Then** el sistema actualiza su estado a "pendiente" y genera un evento de auditoría específico e inmutable `TASK_REOPENED`, claramente diferenciado de la creación original (`TASK_CREATED`) y de una transición ordinaria (`TASK_STATUS_CHANGED`).
2. **Given** una tarea propia en estado "pendiente" o "en progreso", **When** el usuario intenta invocar la acción de reapertura, **Then** el sistema rechaza la solicitud indicando que la reapertura solo aplica a tareas en estado completado.
3. **Given** una tarea propia completada que posteriormente fue eliminada lógicamente, **When** el usuario intenta reabrirla, **Then** el sistema rechaza la acción impidiendo mutaciones sobre tareas eliminadas.
4. **Given** un usuario autenticado, **When** intenta reabrir una tarea completada perteneciente a otro usuario, **Then** el sistema deniega la operación sin aplicar cambios.

---

### User Story 3 - Recuperación Segura de Acceso y Contraseña (Priority: P2)

Como usuario registrado que ha olvidado su contraseña, quiero solicitar el restablecimiento de acceso mediante mi correo registrado sin que el sistema revele públicamente si mi cuenta existe, y utilizar un enlace con token temporal de un solo uso para establecer una nueva contraseña segura, garantizando la confidencialidad y la protección de mi cuenta.

**Why this priority**: Proporciona el mecanismo indispensable de recuperación de cuenta (HU-14) exigido para la autonomía del usuario, aplicando los criterios estrictos del Principio VII (cero divulgación de correos/enumeración de usuarios, tokens de un solo uso con expiración y contraseñas hasheadas de forma robusta).

**Independent Test**: Puede probarse de forma independiente solicitando la recuperación para un correo registrado, verificando que se muestra un mensaje ciego indistinguible, consumiendo el token generado dentro del tiempo límite para cambiar la contraseña por una conforme a la política, comprobando que se puede iniciar sesión con la nueva credencial, y confirmando que un segundo intento de usar el mismo token es rechazado.

**Acceptance Scenarios**:

1. **Given** una persona en la pantalla de solicitud de recuperación de contraseña, **When** introduce una dirección de correo electrónico válida asociada a una cuenta registrada existente, **Then** el sistema genera un token de recuperación criptográficamente seguro con vigencia limitada (15 minutos), despacha las instrucciones de restablecimiento y muestra un mensaje de confirmación neutro e indistinguible ("Si el correo está registrado en el sistema, recibirás instrucciones para restablecer tu contraseña").
2. **Given** una persona en la pantalla de solicitud de recuperación de contraseña, **When** introduce una dirección de correo electrónico que NO está registrada en el sistema, **Then** el sistema muestra exactamente el mismo mensaje neutro de confirmación y con un tiempo de respuesta equivalente, impidiendo la enumeración de usuarios o deducción de cuentas registradas (Principio VII).
3. **Given** un usuario con un token de recuperación válido y no expirado, **When** accede a la pantalla de restablecimiento e ingresa una nueva contraseña que cumple la política de seguridad (mínimo 8 caracteres, al menos una letra y un número), **Then** el sistema actualiza la contraseña aplicando hash seguro (`scrypt`), invalida inmediatamente el token para prevenir reutilizaciones, revoca de forma inmediata y global todas las sesiones activas previas del usuario en cualquier dispositivo o navegador, registra el evento de auditoría `PASSWORD_RESET_COMPLETED` y le exige iniciar sesión con sus nuevas credenciales.
4. **Given** una persona que intenta utilizar un token de recuperación que ya fue utilizado previamente, que fue superado por una solicitud posterior o cuyo tiempo de vigencia ha expirado (más de 15 minutos), **When** envía el formulario con una nueva contraseña, **Then** el sistema rechaza la solicitud, no modifica ninguna credencial e informa que el enlace de recuperación es inválido o ha expirado.
5. **Given** un usuario en el formulario de restablecimiento con token válido, **When** ingresa una contraseña que no cumple los criterios de complejidad (menos de 8 caracteres o sin letra y número), **Then** el sistema rechaza el cambio y solicita una contraseña válida, manteniendo el token activo hasta su expiración o uso exitoso.
6. **Given** una persona que solicita restablecimiento de contraseña reiteradamente para un mismo correo electrónico (más de 3 veces en una ventana de 15 minutos), **When** envía solicitudes adicionales, **Then** el sistema aplica estrangulamiento silencioso (silent throttling), no emite nuevos tokens ni despacha correos, y retorna la misma confirmación neutra para prevenir ataques de denegación de servicio y saturación de correo sin revelar la existencia de la cuenta (Principio VII).

---

### Edge Cases

- **Eliminación consecutiva o concurrente**: Si se envían múltiples solicitudes simultáneas para eliminar la misma tarea, la primera marca la eliminación lógica y las subsiguientes son rechazadas limpiamente como operación no permitida o recurso no encontrado, evitando duplicación en auditoría.
- **Manipulación de identificadores en eliminación o reapertura**: Intentos de alterar identificadores en peticiones para borrar o reabrir tareas ajenas son interceptados y rechazados estrictamente sin filtrar información sobre la propiedad o existencia de la tarea.
- **Solicitud reiterada de restablecimiento para una misma cuenta**: Si un usuario solicita recuperación de contraseña múltiples veces (hasta el límite de 3 solicitudes en 15 minutos), cada nueva solicitud genera un nuevo token con 15 minutos de vigencia e invalida de inmediato cualquier token previo no consumido emitido para esa cuenta (solo el último enlace es utilizable). Si se supera el límite de 3 solicitudes en 15 minutos, las peticiones adicionales son ignoradas silenciosamente (sin generar tokens ni despachar correos) devolviendo la respuesta neutra idéntica.
- **Vencimiento exacto del token de recuperación**: Peticiones enviadas en el límite temporal o con segundos de retraso son evaluadas de forma estricta contra la marca de tiempo de expiración del backend, rechazando cualquier token vencido.
- **Token manipulado o corrupto**: Cualquier intento de acceder o enviar el formulario con un token truncado, alterado o inexistente devuelve un rechazo inmediato por token inválido sin exponer trazas internas de error.
- **Intento de reapertura sobre tareas no completadas**: Si un usuario intenta enviar una solicitud forzada de reapertura sobre una tarea pendiente o en progreso, el sistema rechaza la operación validando el estado previo de negocio.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a un usuario autenticado eliminar lógicamente (soft delete) cualquier tarea de su propiedad (HU-05).
- **FR-002**: El sistema NUNCA DEBE eliminar físicamente de la base de datos relacional el registro de una tarea eliminada ni sus registros de auditoría vinculados, garantizando la preservación íntegra del historial según el Principio VI.
- **FR-003**: Las tareas marcadas como eliminadas lógicamente DEBEN ser excluidas de forma predeterminada del listado principal y de las consultas regulares de tareas del usuario.
- **FR-004**: El sistema DEBE rechazar cualquier intento de eliminar una tarea que ya haya sido eliminada lógicamente con anterioridad, siendo la eliminación lógica definitiva e irreversible para el usuario final (sin opción de papelera de reciclaje ni restauración en este incremento).
- **FR-005**: El sistema DEBE bloquear cualquier intento de editar o cambiar el estado de una tarea que se encuentre en condición de eliminación lógica.
- **FR-006**: Toda eliminación lógica de una tarea DEBE generar un registro inmediato e inmutable en el log de auditoría con la acción `TASK_DELETED`, asociando el identificador del usuario responsable, la tarea y la marca temporal en UTC (Principio VIII).
- **FR-007**: El sistema DEBE permitir a un usuario autenticado reabrir una tarea propia que se encuentre en estado "completada", transicionándola de regreso exclusivamente al estado activo "pendiente" (HU-06).
- **FR-008**: La reapertura de una tarea DEBE registrarse en el log de auditoría como un evento específico `TASK_REOPENED`, distinguible de la creación inicial (`TASK_CREATED`) y de las transiciones ordinarias de estado (`TASK_STATUS_CHANGED`), capturando el estado previo ("completada") y el nuevo estado ("pendiente") (Principio VIII).
- **FR-009**: El sistema DEBE rechazar la acción de reapertura si la tarea indicada no se encuentra en estado "completada" o si ha sido eliminada lógicamente.
- **FR-010**: El sistema DEBE permitir a cualquier persona solicitar el restablecimiento de su contraseña mediante el suministro de una dirección de correo electrónico (HU-14).
- **FR-011**: La respuesta del sistema a la solicitud de recuperación DEBE ser completamente neutra y ciega (blind response), mostrando un mensaje idéntico tanto si el correo existe como si no existe en la base de datos, con tiempos de respuesta consistentes para evitar ataques de enumeración de usuarios (Principio VII).
- **FR-012**: Para solicitudes con correos registrados existentes, el sistema DEBE generar un token de recuperación unívoco, criptográficamente seguro y con un tiempo de vigencia de exactamente 15 minutos desde su emisión. Cada nueva solicitud de recuperación invalida de inmediato cualquier token previo no consumido emitido para dicha cuenta (solo el enlace más reciente es utilizable).
- **FR-013**: Ningún token de recuperación en texto plano ni secreto DEBE almacenarse en la base de datos ni versionarse en el repositorio (Principio VII); en la persistencia solo se almacena su hash criptográfico.
- **FR-014**: El uso exitoso de un token de recuperación para actualizar la contraseña DEBE invalidar de manera inmediata e irreversible dicho token, impidiendo cualquier reutilización posterior (single-use).
- **FR-015**: El sistema DEBE validar que la nueva contraseña proporcionada en el restablecimiento cumpla la política de seguridad estipulada (mínimo 8 caracteres, al menos una letra y al menos un número) y almacenarla cifrada con algoritmo de derivación robusto (`scrypt`).
- **FR-016**: La finalización exitosa del restablecimiento de contraseña DEBE registrar un evento de auditoría `PASSWORD_RESET_COMPLETED` asociado al usuario sin almacenar contraseñas ni tokens en el log.
- **FR-017**: El sistema DEBE revocar e invalidar de forma global e inmediata todas las sesiones activas previas del usuario en cualquier navegador o dispositivo tras un restablecimiento de contraseña exitoso, forzando un nuevo inicio de sesión (Principio VII).
- **FR-018**: El sistema DEBE aplicar estrangulamiento silencioso (silent throttling) con un límite de hasta 3 solicitudes de recuperación de contraseña por correo electrónico en una ventana móvil de 15 minutos; las solicitudes excedentes DEBEN devolver la respuesta neutra idéntica sin generar nuevos tokens ni despachar correos (Principio VII).
- **FR-019**: **Fuera de alcance explícito**: Quedan expresamente excluidos de este incremento: asignación de prioridad (HU-07), agrupación en categorías/proyectos (HU-08), indicación visual de tareas vencidas (HU-09), asignación a otros usuarios (HU-10), notificaciones internas (HU-11), interactividad asíncrona sin recarga (HU-15) y reordenamiento drag-and-drop (HU-16).

---

### Key Entities *(include if feature involves data)*

- **Tarea (`Task`)**: Entidad que representa la unidad de trabajo del usuario. Incorpora control de eliminación lógica mediante indicador de borrado (`is_deleted`) y fecha de eliminación (`deleted_at`), manteniendo su clave foránea al usuario propietario y sus estados (`pending`, `in_progress`, `completed`).
- **Token de Restablecimiento (`PasswordResetToken`)**: Entidad que modela la autorización temporal de recuperación de acceso. Contiene el identificador del usuario asociado, el hash criptográfico del token de un solo uso, la marca temporal de expiración, la marca temporal de utilización (`used_at`) y la marca temporal de creación.
- **Registro de Auditoría (`AuditLog`)**: Entidad inmutable de persistencia para trazabilidad operativa. Registra las nuevas acciones del dominio: `TASK_DELETED`, `TASK_REOPENED` y `PASSWORD_RESET_COMPLETED`, vinculando actor, entidad y metadatos del evento.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las tareas eliminadas se procesan mediante soft delete, registrando una tasa de 0% de eliminaciones físicas en la base de datos relacional y conservando íntegros todos sus registros históricos de auditoría.
- **SC-002**: El 100% de las tareas eliminadas lógicamente dejan de aparecer en el listado estándar de tareas del usuario propietario.
- **SC-003**: El 100% de los intentos de modificar, re-eliminar o reabrir una tarea eliminada lógicamente son rechazados por el sistema.
- **SC-004**: El 100% de las reaperturas de tareas completadas se registran en el log de auditoría con la acción identificable `TASK_REOPENED`, diferenciándose sin ambigüedad de `TASK_STATUS_CHANGED` y `TASK_CREATED`.
- **SC-005**: La tasa de divulgación de cuentas en la solicitud de recuperación es del 0% (el mensaje y la duración de respuesta no permiten discernir si el correo ingresado está o no registrado).
- **SC-006**: El 100% de los tokens de recuperación utilizados o con antigüedad mayor a 15 minutos son rechazados en cualquier intento posterior de restablecimiento de contraseña.
- **SC-007**: Los usuarios pueden completar el flujo de solicitud y restablecimiento de contraseña en menos de 2 minutos.

---

## Assumptions

- Se asume que el Incremento 1 (HU-01 a HU-04, HU-12 y HU-13) se encuentra completamente implementado, probado y en producción con su esquema base de usuarios, tareas, sesiones y auditoría.
- La reapertura de una tarea completada devuelve la tarea al estado activo predeterminado "pendiente" (`pending`).
- La ventana de vigencia temporal para los tokens de recuperación de contraseña es de 15 minutos; cada nueva solicitud válida invalida cualquier token anterior no utilizado para esa cuenta.
- El restablecimiento exitoso de la contraseña revoca todas las sesiones activas del usuario en todos los dispositivos/navegadores para garantizar seguridad total (Principio VII).
- Se aplica estrangulamiento silencioso (máximo 3 solicitudes de restablecimiento por correo cada 15 minutos) para mitigar saturación y abusos sin exponer información de cuentas.
- No se contempla en este incremento una funcionalidad de papelera de reciclaje ni restauración de tareas eliminadas (la eliminación lógica es irreversible para el usuario final en este incremento, preservándose únicamente por integridad de datos y auditoría).
- En entornos locales de desarrollo y pruebas, el enlace de restablecimiento con el token generado se emite en el registro estructurado de la consola/log para permitir la validación manual sin requerir un servidor SMTP externo.
- Todas las peticiones mutantes (POST) asociadas a eliminación, reapertura y recuperación de contraseñas incorporan la protección contra CSRF requerida por la constitución.
