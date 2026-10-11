# Feature Specification: Mejoras de Interacción Frontend mediante JavaScript (Actualización Asíncrona y Drag and Drop)

**Feature Branch**: `005-frontend-interaction`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Especifica el quinto y último incremento funcional de TaskControl: mejoras de interacción en el frontend mediante JavaScript. Este incremento cubre HU-15 y HU-16 del backlog, y asume que todos los incrementos anteriores (1 a 4) ya están implementados y expuestos como endpoints HTTP con contrato definido. Alcance funcional: 1. Completar tareas sin recargar la página (HU-15): desde el listado de tareas, un usuario marca una tarea como completada mediante una interacción de JavaScript que llama al endpoint de cambio de estado ya existente (del Incremento 1), sin recargar la página completa. Si la petición al backend falla, la interfaz revierte el cambio visual mostrado y presenta un mensaje de error al usuario — nunca debe quedar la interfaz mostrando un estado que el backend no confirmó. 2. Reordenar tareas arrastrándolas (HU-16): un usuario reordena visualmente sus tareas en el listado mediante arrastrar y soltar (drag and drop). El nuevo orden se persiste en el backend inmediatamente después de soltar el elemento, de forma que si el usuario recarga la página el orden se mantiene. Como este es el incremento final de JavaScript, no introduce ningún endpoint nuevo de backend — reutiliza exclusivamente los contratos ya definidos en incrementos anteriores (cambio de estado) y requiere, como único elemento nuevo de backend, un campo de orden persistente por tarea para HU-16. Esta especificación debe ser consistente con la constitución del proyecto: no se introduce ningún framework SPA (React, Vue, Angular) salvo justificación explícita, manteniéndose en JavaScript vanilla o una librería ligera de interactividad (restricción técnica del stack), y toda llamada al backend sigue el contrato de endpoints ya documentado (Principio III)."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Completar Tareas sin Recarga de Página con Reversión Visual ante Fallo (Priority: P1)

Como usuario autenticado en mi listado de tareas, quiero marcar una tarea como completada directamente con un solo clic sin experimentar una recarga completa de la página, para tener una experiencia de uso ágil y fluida, con la seguridad de que si la comunicación con el servidor falla, la interfaz revertirá inmediatamente el cambio visual y me notificará el error, impidiendo que la pantalla muestre un estado falso no confirmado por el backend.

**Why this priority**: Es el núcleo de la interactividad ágil en el listado de tareas (HU-15). Elimina los parpadeos y esperas de la recarga completa del navegador, aplicando el patrón de interfaz optimista con reversión determinista ante errores (Principio III).

**Independent Test**: Puede probarse de forma aislada ingresando al listado de tareas con una tarea activa ("pendiente" o "en progreso"), haciendo clic en el control de completar, observando cómo la tarea pasa visualmente al estado completada (estilo tachado/badge verde) de forma inmediata mientras la petición `fetch` asíncrona se envía en segundo plano; y simulando un fallo (cortando la red o provocando un error 400 en el backend) para comprobar que la interfaz desmarca el control, restaura el estilo visual previo exacto y presenta un banner o mensaje de alerta visible explicando el fallo.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado visualizando una tarea en estado "pendiente" en el listado `/tasks`, **When** hace clic en la casilla o botón "Completar", **Then** el JavaScript del cliente aplica inmediatamente la transición visual de completada, despacha una petición asíncrona `POST` al endpoint existente `/tasks/<id>/status` adjuntando el encabezado `X-CSRFToken` y el payload `{ "status": "completed" }`, y al recibir la confirmación exitosa (`200 OK`) del servidor consolida el estado visual sin recargar la página.
2. **Given** un usuario que marca una tarea como completada desde la interfaz, **When** la petición HTTP al backend falla (por error de red, expiración de sesión, rechazo de CSRF o error interno del servidor), **Then** la interfaz revierte inmediatamente la tarea a su estado visual anterior ("pendiente"), restaura la casilla sin marcar y despliega un mensaje de error prominente y comprensible indicando que no fue posible guardar el cambio en el servidor.
3. **Given** un usuario intentando completar una tarea que ya fue completada o modificada concurrentemente, **When** el backend devuelve un código de error de negocio (`400 Bad Request`), **Then** la interfaz ejecuta el rollback visual inmediato, deshace la acción optimista y presenta el motivo exacto devuelto por el servidor.
4. **Given** una tarea marcada como completada de forma asíncrona exitosa, **When** el usuario recarga manualmente la página con F5, **Then** la tarea aparece confirmada en el estado "completada" reflejando la persistencia real del servidor.

---

### User Story 2 - Reordenamiento Persistente de Tareas mediante Arrastrar y Soltar (Priority: P1)

Como usuario autenticado, quiero reordenar visualmente las tareas de mi listado arrastrándolas y soltándolas (drag and drop) en la posición deseada, para organizar mi flujo de trabajo según mis preferencias subjetivas del momento, con la garantía de que este nuevo orden se guarda de inmediato en el servidor y se mantiene intacto si refresco la página o accedo desde otra sesión.

**Why this priority**: Aporta valor directo de personalización y organización visual del trabajo (HU-16). Permite priorizaciones situacionales directas que trascienden el ordenamiento cronológico o por categoría.

**Independent Test**: Puede probarse creando tres tareas ("Tarea 1", "Tarea 2", "Tarea 3"), arrastrando la "Tarea 3" a la primera posición del listado, verificando que al soltarla se dispara la petición asíncrona que persiste la nueva posición en el backend, y recargando la página completa (F5) comprobando que las tareas se presentan en el nuevo orden persistido ("Tarea 3", "Tarea 1", "Tarea 2").

**Acceptance Scenarios**:

1. **Given** un usuario autenticado observando su listado de tareas en `/tasks`, **When** hace clic sostenido sobre una tarjeta de tarea y la arrastra hacia una nueva posición entre otras tareas, **Then** la interfaz ofrece retroalimentación visual clara durante el arrastre (indicador de zona de soltado / dropzone).
2. **Given** un usuario que suelta la tarea en su nueva posición deseada, **When** se produce el evento de soltado (*drop*), **Then** el JavaScript del cliente calcula los nuevos índices de orden y despacha inmediatamente la petición asíncrona hacia el backend reutilizando los contratos existentes, persistiendo el campo de orden (`position` / `sort_order`) sin recargar la página.
3. **Given** un reordenamiento completado exitosamente, **When** el usuario recarga la página o cierra y reabre su navegador, **Then** las tareas se renderizan exactamente en el orden personalizado guardado.
4. **Given** un usuario que arrastra y suelta una tarea, **When** la petición de persistencia del nuevo orden falla en el backend (por error de red o de servidor), **Then** la interfaz revierte las tarjetas a sus posiciones visuales originales previas al arrastre (rollback del DOM) y presenta una notificación alertando que el nuevo orden no pudo guardarse.
5. **Given** un usuario en un dispositivo con teclado o lector de pantalla (accesibilidad), **When** interactúa con las tareas, **Then** la interfaz proporciona controles alternativos accesibles (botones de mover arriba/abajo) para alterar el orden sin depender exclusivamente del cursor del ratón.

---

### User Story 3 - Integridad de Contratos y Ausencia de Frameworks SPA Pesados (Priority: P2)

Como mantenedor del sistema y usuario de la aplicación, quiero que toda la interactividad del frontend esté construida exclusivamente con JavaScript vanilla liviano y la API estándar HTML5 Drag and Drop, consumiendo estrictamente los contratos de endpoints ya existentes y validados con CSRF, para mantener una arquitectura monolítica ágil, rápida de cargar, libre del peso y la complejidad de frameworks SPA (React, Vue, Angular) y totalmente alineada con la constitución del proyecto.

**Why this priority**: Garantiza la sustentabilidad y el cumplimiento del Principio I (monolito por diseño), Principio III (contratos explícitos) y la Restricción Técnica 4 del stack tecnológico.

**Independent Test**: Puede probarse inspeccionando los recursos cargados en el navegador: confirmar que no se descarga ningún bundle de React, Vue, Angular ni bibliotecas pesadas de gestión de estado, que el archivo `main.js` contiene código JavaScript estándar con `addEventListener`, `fetch` y `dragstart`/`dragover`/`drop`, y que todas las llamadas HTTP mutantes incluyen el encabezado `X-CSRFToken` validado exitosamente en el backend.

**Acceptance Scenarios**:

1. **Given** la carga de cualquier página del sistema, **When** se inspeccionan las dependencias del cliente, **Then** el tamaño total del JavaScript es inferior a 50 KB y no incluye bibliotecas SPA externas.
2. **Given** cualquier petición asíncrona (`fetch`) enviada por JavaScript para completar o reordenar tareas, **When** se envía al servidor, **Then** incluye obligatoriamente el token CSRF sincronizado en el encabezado `X-CSRFToken` o en el cuerpo de la petición.
3. **Given** una petición asíncrona que carece de token CSRF o contiene un token inválido, **When** llega al servidor, **Then** el backend responde deterministamente `400 Bad Request` (`CSRF_ERROR`) y el cliente maneja el error sin colapsar.

---

## Edge Cases

- **Pérdida momentánea de conexión de red durante el clic en completar**: El usuario hace clic en completar, la interfaz muestra el cambio optimista, la petición `fetch` falla por timeout o desconexión; inmediatamente la interfaz captura el fallo en el bloque `.catch()`, desmarca la tarea, elimina el estilo tachado y muestra una alerta: *"No se pudo actualizar la tarea por problemas de conexión. Intente nuevamente."*
- **Reordenamiento durante filtros activos (e.g. filtro por estado "en progreso")**: Cuando el usuario reordena tareas dentro de un subconjunto filtrado, el JavaScript actualiza las posiciones relativas correspondientes a los elementos visibles, preservando la coherencia global del orden en la base de datos.
- **Doble clic rápido accidental sobre el botón de completar**: El JavaScript deshabilita temporalmente el control de interacción (debounce / bandera `isProcessing`) mientras la petición HTTP está en curso para prevenir condiciones de carrera y peticiones duplicadas innecesarias.
- **Arrastre cancelado por el usuario (soltar fuera de una zona válida o presionar Escape)**: Si el usuario suelta el elemento fuera de la lista de tareas o cancela la acción, el DOM regresa intacto a su estado original sin emitir ninguna llamada HTTP al backend.
- **Tarea que ya no existe al momento de completar o reordenar**: Si otro proceso o sesión eliminó la tarea mientras el usuario tenía la página abierta, el backend responde `404 Not Found` y la interfaz elimina la tarjeta del listado o revierte la acción notificando que la tarea ya no está disponible.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a un usuario autenticado marcar una tarea como completada directamente desde el listado `/tasks` sin recargar la página completa del navegador (HU-15).
- **FR-002**: La interacción de completar tarea DEBE ejecutarse mediante una petición HTTP asíncrona (`fetch`) en JavaScript hacia el endpoint de cambio de estado ya existente (`POST /tasks/<id>/status`), reutilizando el contrato definido en el Incremento 1 (Principio III).
- **FR-003**: La interfaz de usuario DEBE aplicar una actualización visual optimista al marcar la tarea como completada, reflejando inmediatamente el cambio al usuario mientras la petición se procesa en segundo plano.
- **FR-004**: Si la petición asíncrona de cambio de estado falla (error HTTP 4xx, 5xx o fallo de red), la interfaz DEBE revertir de manera obligatoria y determinista el estado visual al previo (rollback visual) y presentar un mensaje de error visible y claro al usuario, garantizando que la pantalla jamás muestre un estado no confirmado por el backend.
- **FR-005**: El sistema DEBE permitir al usuario reordenar visualmente sus tareas en el listado arrastrándolas y soltándolas (Drag and Drop) (HU-16).
- **FR-006**: El nuevo orden de las tareas DEBE persistirse de forma asíncrona en el backend inmediatamente después de soltarse el elemento, de modo que al recargar la página (F5) o iniciar una nueva sesión, las tareas se presenten en el orden exacto establecido por el usuario.
- **FR-007**: Si la persistencia del nuevo orden falla en el backend, la interfaz DEBE revertir las tarjetas de las tareas a su orden visual anterior (rollback del DOM) y alertar al usuario del fallo.
- **FR-008**: Para soportar el ordenamiento persistente de HU-16, el modelo `Task` en el backend DEBE incorporar como único elemento nuevo un campo numérico de orden (`position` o `sort_order`, entero, no nulo, indexado) con valor por defecto coherente.
- **FR-009**: La persistencia del orden de las tareas DEBE reutilizar los contratos de endpoints ya existentes (mediante actualización de atributos de tareas en el backend), sin introducir nuevos recursos o endpoints ajenos a la arquitectura monolítica.
- **FR-010**: Toda la interactividad del frontend DEBE implementarse estrictamente en **JavaScript vanilla** estándar haciendo uso de la API nativa HTML5 Drag and Drop (`draggable`, `dragstart`, `dragover`, `drop`) y la API nativa `fetch`, quedando terminantemente prohibida la introducción de frameworks SPA pesados (React, Vue, Angular) conforme a la Restricción Técnica 4 de la constitución.
- **FR-011**: Todas las llamadas asíncronas mutantes (`POST`) ejecutadas por JavaScript DEBEN extraer el token CSRF del elemento `<meta name="csrf-token">` del layout maestro e inyectarlo en el encabezado HTTP `X-CSRFToken`, cumpliendo estrictamente con la protección global CSRF (Principio VII).
- **FR-012**: Las tareas que se reordenen manualmente DEBEN ser presentadas en el listado respetando el campo `position` de forma predeterminada cuando el usuario no tenga seleccionado un ordenamiento explícito por prioridad o fecha.
- **FR-013**: El cálculo en memoria de tareas vencidas (`is_overdue`) y las etiquetas de prioridad y procedencia definidas en los Incrementos 1 a 4 DEBEN actualizarse de forma consistente y reactiva en el cliente cuando una tarea transiciona a completada (ocultando el badge de vencida inmediatamente al completarse).

---

### Key Entities *(include if feature involves data)*

- **Tarea (`Task`) (Ampliación Final)**:
  - Se incorpora el atributo de orden persistente:
    - `position` (o `sort_order`): Entero, no nulo (`nullable=False`), valor por defecto `0` (`server_default='0'`), indexado junto con `user_id` para garantizar consultas ultra-rápidas en el listado ordenado.
  - El resto de los atributos de los Incrementos 1 a 4 (`id`, `user_id`, `assignee_id`, `category_id`, `title`, `description`, `due_date`, `status`, `priority`, `is_deleted`, `timestamps`) se preservan íntegros.
- **Respuesta de Estado (`TaskStateResponse`)**:
  - Contrato de retorno del endpoint `POST /tasks/<id>/status` consumido por JavaScript: `{ "status": "success", "data": { "id": 1, "status": "completed", "is_overdue": false } }`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% de reversión visual determinista: ante cualquier fallo de red o error del servidor (código 4xx/5xx), la interfaz revierte el estado visual mostrado a su valor previo sin discrepancias (0% de tareas mostrando estado no confirmado).
- **SC-002**: 100% de persistencia del orden arrastrado: al reordenar tareas y recargar la página (F5), las tareas se presentan exactamente en el nuevo orden definido por el usuario.
- **SC-003**: Tiempo de respuesta interactiva en el cliente menor a 50 ms para el cambio visual optimista tras el clic o soltado.
- **SC-004**: 0 dependencias añadidas de frameworks SPA (React, Vue, Angular): el 100% del código interactivo del cliente está implementado en JavaScript vanilla nativo en `static/js/main.js`.
- **SC-005**: 100% de cumplimiento en protección CSRF: todas las peticiones asíncronas mutantes generadas por JavaScript incluyen `X-CSRFToken` y son validadas exitosamente por el backend.

---

## Assumptions

- Todos los endpoints de los Incrementos 1 a 4 (`/tasks/<id>/status`, `/tasks`, `/tasks/<id>/edit`, etc.) se encuentran en funcionamiento y retornan respuestas JSON cuando la petición incluye `Accept: application/json` o `Content-Type: application/json`.
- Para el arrastre y soltado se utiliza la API nativa de HTML5 Drag and Drop (`dragstart`, `dragover`, `drop`, `dragend`), soportada en el 100% de los navegadores modernos estándar de escritorio.
- El reordenamiento manual aplica a las tareas del usuario activo dentro de su vista actual. Si el usuario activa un ordenamiento explícito (por prioridad o por fecha), ese criterio predomina temporalmente sobre el orden posicional manual.
- No se introducen nuevos endpoints de backend dedicados para este incremento final; la persistencia del orden y el cambio de estado reutilizan los controladores y contratos de tareas ya establecidos.
- Las notificaciones de error ante fallos de interactividad se presentan mediante elementos visuales contextuales y mensajes de alerta/toast integrados en la plantilla base sin interrumpir la navegación.
