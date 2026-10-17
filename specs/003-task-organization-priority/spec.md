# Feature Specification: Organización y Priorización de Tareas

**Feature Branch**: `003-task-organization-priority`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Especifica el tercer incremento funcional de TaskControl: organización y priorización de tareas. Este incremento cubre HU-07, HU-08 y HU-09 del backlog, y asume que los Incrementos 1 y 2 ya están implementados. Alcance funcional: 1. Prioridad de tareas (HU-07): toda tarea tiene una prioridad (alta, media, baja) con un valor por defecto definido explícitamente. El listado de tareas (ya existente desde HU-02) se puede ordenar por prioridad, además de los filtros por estado ya existentes. Un usuario puede cambiar la prioridad de una tarea propia en cualquier momento. 2. Categorías o proyectos (HU-08): un usuario puede crear categorías para agrupar tareas relacionadas. Una tarea pertenece a máximo una categoría (o a ninguna). Eliminar una categoría no elimina las tareas que pertenecían a ella — quedan sin categoría, nunca se eliminan en cascada. 3. Indicación de tareas vencidas (HU-09): el sistema calcula si una tarea está vencida (fecha límite superada y no completada) y lo expone en el listado. Este cálculo se hace exclusivamente en el backend, nunca en JavaScript, para evitar inconsistencias por zona horaria del cliente. Una tarea eliminada o completada nunca se marca como vencida aunque su fecha límite haya pasado. Fuera de alcance explícito de este incremento: asignación y notificaciones (HU-10, HU-11), interacción sin recarga de página y drag-and-drop (HU-15, HU-16). Esta especificación debe ser consistente con la constitución del proyecto: separación de capas al introducir el nuevo concepto de categoría como entidad propia (Principio II), y cálculo de vencimiento resuelto en el backend como parte del contrato de datos que recibe el frontend (Principio III)."

---

## Clarifications

### Session 2026-10-17

- Q: ¿Cuál debe ser el valor por defecto para la prioridad de una tarea nueva y cómo debe registrarse su modificación en el log de auditoría? → A: Prioridad por defecto "media" (`medium`) y cambio registrado en auditoría bajo `TASK_UPDATED` con metadatos de estado previo y posterior (`old_priority` y `new_priority`).
- Q: ¿Puede un usuario renombrar una categoría existente y qué impacto tiene dicha operación sobre las tareas asignadas y el log de auditoría? → A: Sí, se permite renombrar la categoría; las tareas mantienen su vinculación (por `category_id`) y se registra `CATEGORY_UPDATED` en auditoría con `old_name` y `new_name`.
- Q: ¿Debe el nombre de una categoría ser estrictamente único por usuario sin distinguir mayúsculas/minúsculas y existe un límite en la cantidad total de categorías que puede crear cada usuario? → A: Unicidad estricta insensible a mayúsculas/minúsculas (`case-insensitive`) por usuario tras aplicar normalización/trim, con un límite máximo de 50 categorías por cuenta.
- Q: ¿Qué zona horaria debe definir la fecha actual de referencia en el backend para calcular las tareas vencidas y cómo se evalúa una tarea cuya fecha límite corresponde al día de hoy? → A: Referencia en UTC (`due_date < today_utc`); la fecha de hoy NO cuenta como vencida (el usuario tiene toda la jornada y vence a las 00:00:00 UTC del día siguiente).
- Q: ¿Cómo deben estructurarse los parámetros HTTP para filtrar tareas por categoría (incluyendo la opción "sin categoría") y cómo interactúan combinados con los filtros de estado y el ordenamiento por prioridad? → A: Parámetros acumulativos (`AND`): `status` (`all`, `pending`, `in_progress`, `completed`), `category` (soporta ID numérico de la categoría, valor especial `'uncategorized'` para tareas sin categoría, o `'all'` por defecto) y `sort` (`priority` o `created_at`), resolviendo combinaciones en una sola consulta relacional filtrada.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Asignación, Modificación y Ordenamiento por Prioridad (Priority: P1)

Como usuario autenticado, quiero asignar un nivel de prioridad (alta, media, baja) a mis tareas y poder ordenar mi listado por prioridad, para enfocar mi atención primero en los compromisos más urgentes e importantes.

**Why this priority**: Es la base de la priorización del trabajo personal (HU-07). Permite al usuario clasificar tareas en el momento de creación o modificarlas dinámicamente según cambien las circunstancias operativas.

**Independent Test**: Puede probarse de forma aislada creando tareas sin especificar prioridad (deben recibir la prioridad por defecto "media"), creando tareas con prioridad explícita ("alta", "baja"), cambiando la prioridad de una tarea existente, y solicitando el listado ordenado por prioridad verificando que las tareas con prioridad alta preceden a las medias y bajas.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado creando una nueva tarea sin seleccionar prioridad explícita, **When** guarda la tarea, **Then** el sistema le asigna automáticamente la prioridad por defecto "media" (`medium`).
2. **Given** un usuario autenticado creando o editando una tarea, **When** selecciona una prioridad válida ("alta" / `high`, "media" / `medium`, "baja" / `low`), **Then** el sistema persiste la tarea con dicha prioridad y actualiza el log de auditoría si se trata de una modificación.
3. **Given** un usuario autenticado con múltiples tareas en diferentes prioridades, **When** accede a su listado de tareas y selecciona ordenar por prioridad, **Then** las tareas activas se presentan agrupadas/ordenadas en sentido descendente de urgencia (alta $\rightarrow$ media $\rightarrow$ baja), manteniendo el orden por fecha de creación descendente como criterio secundario de desempate.
4. **Given** un usuario autenticado consultando su listado con un filtro de estado activo (e.g., solo "en progreso"), **When** aplica el ordenamiento por prioridad, **Then** el sistema muestra únicamente las tareas que cumplen el filtro de estado ordenadas por prioridad.
5. **Given** un usuario autenticado, **When** intenta asignar un valor de prioridad no reconocido o inválido, **Then** el sistema rechaza la operación con un error de validación claro conservando los datos previos.

---

### User Story 2 - Agrupación en Categorías y Desvinculación Segura (Priority: P1)

Como usuario autenticado, quiero crear categorías o proyectos personales para agrupar tareas relacionadas y poder clasificar mis tareas dentro de una categoría, con la garantía de que si decido eliminar una categoría, mis tareas no se borrarán en cascada sino que quedarán simplemente sin categoría asignada.

**Why this priority**: Proporciona la estructura organizativa de proyectos (HU-08). La regla de negocio de no eliminación en cascada es crítica para la integridad y tranquilidad del usuario: borrar una etiqueta organizativa jamás debe destruir el trabajo subyacente.

**Independent Test**: Puede probarse creando una categoría "Finanzas", asignando dos tareas a ella, verificando que aparecen filtradas bajo esa categoría, eliminando la categoría "Finanzas", y constatando que las dos tareas continúan existiendo en el listado general con su categoría en estado "sin categoría" (`None`).

**Acceptance Scenarios**:

1. **Given** un usuario autenticado en la sección de categorías, **When** ingresa un nombre válido no vacío para una nueva categoría, **Then** el sistema registra la categoría vinculada exclusivamente a su cuenta de usuario.
2. **Given** un usuario autenticado intentando crear una categoría con un nombre que ya posee entre sus categorías activas, **When** envía la solicitud, **Then** el sistema rechaza la creación por duplicidad para evitar confusiones en su espacio de trabajo.
3. **Given** un usuario autenticado creando o editando una tarea propia, **When** selecciona una de sus categorías existentes (o ninguna), **Then** el sistema vincula la tarea a dicha categoría (máximo una por tarea) o la deja sin categoría.
4. **Given** un usuario con una categoría que contiene tareas asociadas, **When** solicita eliminar dicha categoría, **Then** el sistema elimina la categoría, desvincula automáticamente todas las tareas que le pertenecían (estableciendo su categoría en nula/sin categoría) y NO elimina ninguna tarea ni física ni lógicamente.
5. **Given** un usuario autenticado en el listado de tareas, **When** aplica simultáneamente un filtro por categoría (e.g., `category=5` o `category=uncategorized`), un filtro por estado (e.g., `status=in_progress`) y ordenamiento por prioridad (`sort=priority`), **Then** el listado muestra exclusivamente las tareas activas que satisfacen todos los criterios aplicados de forma acumulativa (`AND`), ordenadas en sentido descendente de prioridad.
6. **Given** un usuario autenticado, **When** intenta asignar a una tarea suya una categoría perteneciente a otro usuario, **Then** el sistema deniega la operación con error de autorización impidiendo cruces de información.
7. **Given** un usuario autenticado con una categoría que tiene tareas asignadas, **When** renombra la categoría a un nombre válido no duplicado, **Then** el sistema actualiza el nombre, preserva intacta la asociación de todas sus tareas existentes y registra el evento `CATEGORY_UPDATED` en el log de auditoría con los nombres previo y posterior.
8. **Given** un usuario autenticado que ha alcanzado el límite máximo de 50 categorías, **When** intenta crear una categoría adicional, **Then** el sistema rechaza la solicitud impidiendo la creación y notificando que se superó el límite permitido por cuenta.

---

### User Story 3 - Detección y Marcado en Backend de Tareas Vencidas (Priority: P2)

Como usuario autenticado, quiero ver claramente qué tareas están vencidas para atender inmediatamente el trabajo retrasado, con la seguridad de que el cálculo se realiza de manera determinista y confiable en el servidor, sin depender de la fecha, reloj ni zona horaria del navegador del cliente.

**Why this priority**: Aporta valor directo de alerta y priorización temporal (HU-09). Resolver el cálculo exclusivamente en el servidor previene discrepancias de zona horaria o manipulación del reloj del dispositivo cliente, cumpliendo el Principio III (contrato backend-cliente estricto).

**Independent Test**: Puede probarse creando una tarea con fecha límite de ayer en estado "pendiente" (debe marcarse como vencida: `is_overdue = true`), una tarea con fecha de ayer pero en estado "completada" (no debe marcarse como vencida: `is_overdue = false`), y una tarea eliminada con fecha pasada (tampoco debe marcarse como vencida).

**Acceptance Scenarios**:

1. **Given** una tarea activa cuyo estado es "pendiente" o "en progreso", **When** su fecha límite (`due_date`) es anterior a la fecha actual del sistema evaluada en el backend en UTC, **Then** el backend expone en el contrato de datos el indicador `is_overdue = true` y la interfaz lo presenta con una advertencia visual destacada.
2. **Given** una tarea con fecha límite en el pasado cuyo estado es "completada", **When** se consulta en el listado, **Then** el backend expone deterministamente `is_overdue = false` (un compromiso ya finalizado no se considera vencido).
3. **Given** una tarea que no tiene fecha límite asignada (`due_date = null`), **When** se consulta en el listado, **Then** el backend expone `is_overdue = false`.
4. **Given** una tarea eliminada lógicamente (soft deleted), **When** se evalúa en el sistema, **Then** nunca se computa como vencida.
5. **Given** un usuario visualizando su listado en cualquier zona horaria o dispositivo, **When** se renderiza la lista de tareas, **Then** el estado de vencimiento refleja idénticamente la evaluación calculada por el backend.

---

### Edge Cases

- **Tarea con fecha límite para el día de hoy**: Una tarea con fecha límite igual a la fecha actual del servidor evaluada en UTC no se considera vencida; permanece activa durante toda la jornada y pasa a considerarse vencida únicamente a partir de las 00:00:00 UTC del día siguiente.
- **Categoría eliminada mientras se edita una tarea**: Si un usuario tiene un formulario abierto con una categoría seleccionada y la categoría es eliminada concurrentemente, al guardar la tarea el sistema detecta que la categoría ya no existe y rechaza la asignación o asigna la tarea sin categoría con un mensaje claro.
- **Nombres de categorías con espacios, colisiones de mayúsculas y unicidad**: Nombres de categoría compuestos únicamente de espacios son rechazados. Espacios en los extremos son recortados mediante trim. Comparaciones de unicidad se evalúan en minúsculas (`case-insensitive`), impidiendo que un usuario cree "Trabajo" y "trabajo".
- **Límite máximo de categorías alcanzado**: Intentos de crear más de 50 categorías por usuario son rechazados limpiamente por el backend con error 400.
- **Cambio de estado de tarea vencida a completada**: En el momento exacto en que una tarea vencida transiciona a `completed`, el indicador `is_overdue` calculado pasa a `false` inmediatamente.
- **Combinación simultánea de filtros y ordenamiento**: El listado soporta combinaciones acumulativas ortogonales de parámetros (`status`, `category` y `sort`). Si se envía un `category` inexistente o perteneciente a otro usuario, el sistema responde con una lista vacía o rechazo 404/400 sin filtrar información de otros usuarios.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Toda tarea en el sistema DEBE poseer un atributo de prioridad con uno de los tres valores admitidos: `'high'` (alta), `'medium'` (media) o `'low'` (baja) (HU-07).
- **FR-002**: Si al crear una tarea no se suministra una prioridad explícita, el sistema DEBE asignarle de forma predeterminada la prioridad `'medium'` (media).
- **FR-003**: El sistema DEBE permitir a un usuario autenticado modificar la prioridad de cualquiera de sus tareas activas en cualquier momento, tanto al editar la tarea como a través de una acción de actualización de prioridad; dicha modificación DEBE registrarse en el log de auditoría bajo el evento `TASK_UPDATED` capturando los metadatos de estado previo y posterior (`old_priority` y `new_priority`) (Principio VIII).
- **FR-004**: El listado de tareas DEBE permitir ordenar los resultados por nivel de prioridad en orden descendente de urgencia (`high` $\rightarrow$ `medium` $\rightarrow$ `low`), manteniendo el ordenamiento por fecha de creación descendente como criterio secundario.
- **FR-005**: El ordenamiento por prioridad DEBE ser combinable con los filtros por estado existentes (`all`, `pending`, `in_progress`, `completed`).
- **FR-006**: El sistema DEBE permitir a un usuario autenticado crear, listar, renombrar (editar) y eliminar categorías o proyectos personales para organizar su trabajo; al renombrar una categoría, las tareas vinculadas conservan intacta su relación referencial y se registra el evento de auditoría `CATEGORY_UPDATED` con el nombre previo y posterior (`old_name` y `new_name`) (HU-08, Principio VIII).
- **FR-007**: El nombre de una categoría es obligatorio, no puede estar vacío, tiene una longitud máxima de 50 caracteres, DEBE ser único por usuario insensible a mayúsculas/minúsculas (`case-insensitive` tras aplicar trim/normalización) y el sistema DEBE aplicar un límite de hasta 50 categorías creadas por cuenta.
- **FR-008**: Una tarea DEBE pertenecer a como máximo una categoría a la vez, o no pertenecer a ninguna (categoría opcional).
- **FR-009**: La eliminación de una categoría NUNCA DEBE eliminar las tareas que pertenecían a ella; el sistema DEBE desvincularlas de forma segura (`ON DELETE SET NULL`), dejándolas en estado "sin categoría" y preservando intactos sus atributos y auditoría.
- **FR-010**: El listado de tareas DEBE permitir filtrar las tareas del usuario por categoría asignada recibiendo el parámetro `category` (con soporte para el identificador numérico de categoría, el valor especial `'uncategorized'` para tareas sin categoría, o `'all'` por defecto) y este filtro DEBE ser acumulativo y combinable mediante conjunción lógica (`AND`) con el filtro por `status` y el criterio de ordenamiento `sort` (`priority` o `created_at`).
- **FR-011**: El sistema DEBE calcular en el backend si una tarea se encuentra vencida (`is_overdue`), contrastando la fecha límite contra la fecha actual del servidor en UTC (`due_date < datetime.now(timezone.utc).date()`); la fecha del día en curso NO se considera vencida (vence formalmente al inicio del día calendario siguiente en UTC) y la tarea NO debe encontrarse en estado completada ni eliminada (HU-09).
- **FR-012**: El cálculo de `is_overdue` DEBE realizarse exclusivamente en la capa de servicios del backend y transmitirse como un atributo calculado en el contrato de respuesta hacia las plantillas Jinja2 y el cliente JavaScript, quedando estrictamente prohibido realizar este cálculo de negocio en el cliente para evitar inconsistencias de reloj o zona horaria (Principio III).
- **FR-013**: Una tarea en estado "completada" (`status = 'completed'`) o eliminada lógicamente (`is_deleted = true`) NUNCA DEBE marcarse como vencida (`is_overdue = false`), aun cuando su fecha límite pertenezca al pasado.
- **FR-014**: El concepto de Categoría DEBE estructurarse conforme a la separación estricta de responsabilidades (Principio II): modelo de persistencia `Category`, capa de dominio `CategoryService` y controlador `categories.py` en blueprints.
- **FR-015**: **Límites de alcance explícitos**: Quedan expresamente fuera de este incremento: asignación de tareas a otros usuarios (HU-10), notificaciones internas (HU-11), interactividad asíncrona sin recarga de página (HU-15) y reordenamiento manual mediante drag-and-drop (HU-16).

---

### Key Entities *(include if feature involves data)*

- **Prioridad (`Priority`)**: Enumeración del dominio con valores canónicos ordenados: `high` (3), `medium` (2), `low` (1).
- **Categoría (`Category`)**: Entidad de persistencia que representa un proyecto o agrupación temática del usuario. Atributos: `id`, `user_id` (FK a `users.id`), `name` (cadena 1-50 caracteres), `created_at`.
- **Tarea (`Task`) (Extendida)**: Incorpora `priority` (String con valor por defecto `'medium'`) y `category_id` (FK a `categories.id` nullable con política `SET NULL`). Expone la propiedad calculada `is_overdue` en sus contratos de salida.
- **Registro de Auditoría (`AuditLog`)**: Registra cambios en prioridad bajo el evento `TASK_UPDATED` con detalles `{"old_priority": ..., "new_priority": ...}` y eventos de ciclo de vida de categorías (`CATEGORY_CREATED`, `CATEGORY_UPDATED`, `CATEGORY_DELETED`).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las tareas creadas sin prioridad explícita reciben automáticamente la prioridad predeterminada "media" (`medium`).
- **SC-002**: El 100% de las tareas desvinculadas tras eliminar su categoría asociada permanecen íntegras en el sistema con `category_id = null`, registrando una tasa de 0% de pérdidas de tareas por borrado de categorías.
- **SC-003**: Discrepancia del 0% en la indicación de tareas vencidas entre diferentes clientes o navegadores, al ser un valor computado deterministamente en el backend.
- **SC-004**: El listado de tareas permite alternar el ordenamiento entre fecha de creación descendente y prioridad descendente en un tiempo de respuesta de backend inferior a 100 ms.
- **SC-005**: 100% de cumplimiento en el aislamiento por usuario: ningún usuario puede ver, asignar o filtrar categorías de otros usuarios.

---

## Assumptions

- Los Incrementos 1 (`001-core-task-auth`) y 2 (`002-task-lifecycle-recovery`) se encuentran plenamente construidos y en producción.
- La escala de prioridades se limita a 3 niveles estándar: "alta" (`high`), "media" (`medium`) y "baja" (`low`). No se requieren niveles intermedios ni ponderaciones numéricas complejas en este incremento.
- El valor por defecto de prioridad es "media" (`medium`).
- El cálculo de vencimiento en el backend se efectúa contrastando la fecha de calendario `due_date` contra la fecha actual del servidor (`date.today()` / UTC actual). Una tarea vence al inicio del día posterior a su `due_date`.
- Una categoría pertenece exclusivamente a un usuario; no hay categorías compartidas entre usuarios en este incremento (la colaboración corresponde a HU-10 en incrementos posteriores).
- Todas las operaciones HTTP mutantes para categorías y actualización de prioridades utilizan el método POST protegido con tokens CSRF conforme a la constitución.
