# Feature Specification: Gestión Básica de Tareas con Autenticación de Usuarios

**Feature Branch**: `001-core-task-auth`

**Created**: 2026-10-06

**Status**: Draft

**Input**: User description: "Especifica el primer incremento funcional de TaskControl: gestión básica de tareas con autenticación de usuarios. Este incremento cubre HU-01 a HU-04 y HU-12–HU-13 del backlog del proyecto. Alcance funcional: 1. Registro de usuario (HU-12). 2. Inicio y cierre de sesión (HU-13). 3. Creación de tareas (HU-01). 4. Listado de tareas (HU-02). 5. Cambio de estado (HU-03). 6. Edición de tareas (HU-04)."

## Clarifications

### Session 2026-10-06

- Q: ¿Cuál debe ser el orden predeterminado en el que se muestran las tareas en el listado cuando el usuario no aplica ningún criterio de ordenamiento adicional? (HU-02) → A: Por fecha de creación descendente (las tareas más recientes aparecen primero).
- Q: ¿Se debe permitir registrar o editar fechas límite con fechas pasadas al crear o actualizar una tarea? (HU-01, HU-04) → A: Permitir fechas pasadas (la fecha límite solo debe ser una fecha de calendario válida, sin restricción respecto a la fecha actual).
- Q: ¿Qué requisitos de complejidad debe validar el sistema para las contraseñas durante el registro de usuarios? (HU-12) → A: Longitud mínima de 8 caracteres requiriendo al menos una letra y un número.
- Q: ¿El campo de descripción de las tareas debe admitir únicamente texto sin formato (texto plano) o debe soportar formato enriquecido como Markdown o HTML? (HU-01, HU-04) → A: Solo texto plano (los caracteres especiales se escapan como texto literal, preservando únicamente saltos de línea).
- Q: ¿Cuál debe ser la política de persistencia y expiración de la sesión autenticada del usuario en el sistema? (HU-13) → A: Sesión de navegador estándar (activa mientras el navegador esté abierto; se destruye al cerrar el navegador o cerrar sesión explícitamente).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registro, Acceso y Protección de Cuenta (Priority: P1)

Como usuario nuevo o recurrente, quiero registrar una cuenta protegida, iniciar sesión de forma segura y cerrarla cuando termine, para que mis tareas personales estén aisladas y resguardadas de accesos no autorizados.

**Why this priority**: Es la base del sistema y condición indispensable para la titularidad de los datos. Sin autenticación y control de sesión, no es posible atribuir tareas a un propietario ni garantizar la privacidad ni auditar acciones. Cubre HU-12 y HU-13.

**Independent Test**: Puede probarse de forma independiente registrando una cuenta con correo y contraseña, cerrando sesión, intentando acceder a la zona privada (debe impedirse), y volviendo a iniciar sesión con las credenciales registradas.

**Acceptance Scenarios**:

1. **Given** un visitante en la pantalla de registro, **When** ingresa un correo electrónico con formato válido no registrado previamente y una contraseña válida (mínimo 8 caracteres, con al menos una letra y un número), **Then** el sistema crea la cuenta, almacena la credencial de forma segura y cifra la contraseña, permitiendo el ingreso al sistema.
2. **Given** un visitante en la pantalla de registro, **When** ingresa un correo que ya pertenece a una cuenta existente, con formato no válido o una contraseña no conforme (menos de 8 caracteres o sin combinación de letra y número), **Then** el sistema rechaza el registro, muestra un mensaje descriptivo y no crea la cuenta.
3. **Given** un usuario registrado, **When** introduce su correo y contraseña correctos, **Then** el sistema inicia una sesión activa y le concede acceso a su panel personal de tareas.
4. **Given** un usuario registrado, **When** introduce credenciales incorrectas, **Then** el sistema deniega el acceso y muestra un mensaje de error sin revelar detalles internos ni existencia previa del correo.
5. **Given** un usuario con sesión activa, **When** solicita cerrar sesión o finaliza la sesión cerrando el navegador, **Then** el sistema da por terminada la sesión activa y cualquier intento subsiguiente de consultar o manipular tareas requiere un nuevo inicio de sesión.
6. **Given** una persona no autenticada, **When** intenta consultar directamente las pantallas o acciones de gestión de tareas, **Then** el sistema intercepta la petición y exige iniciar sesión.

---

### User Story 2 - Creación y Listado de Tareas Personales (Priority: P1)

Como usuario autenticado, quiero registrar nuevas tareas con su información básica y ver mi lista de tareas pendientes organizada con filtros, para planificar y hacer seguimiento claro de mis compromisos.

**Why this priority**: Constituye el valor principal de la aplicación. Permitir la captura y visualización de tareas completa el Producto Mínimo Viable (MVP) junto con la autenticación. Cubre HU-01 y HU-02.

**Independent Test**: Puede probarse de forma independiente creando dos tareas con distintos estados iniciales y atributos, verificando que aparecen en la lista personal, comprobando que los filtros por estado funcionan adecuadamente y asegurando que un segundo usuario nunca ve las tareas del primero.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado en la vista de creación de tareas, **When** ingresa un título no vacío y opcionalmente una descripción y fecha límite válida, **Then** el sistema registra la tarea en estado "pendiente", vinculada exclusivamente a dicho usuario, y crea una entrada en el registro de auditoría con el autor y la marca de tiempo.
2. **Given** un usuario autenticado, **When** intenta crear una tarea con el título vacío o con solo espacios en blanco, **Then** el sistema rechaza la creación y solicita un título válido.
3. **Given** un usuario autenticado con múltiples tareas creadas, **When** accede a su listado de tareas sin aplicar ordenamiento adicional, **Then** observa sus tareas ordenadas por fecha de creación descendente (las más recientes primero) con título, estado actual y fecha límite, sin visualizar ninguna tarea perteneciente a otros usuarios del sistema.
4. **Given** un usuario autenticado con tareas en diferentes estados, **When** selecciona un filtro por estado ("pendiente", "en progreso", "completada" o "todas"), **Then** el listado se actualiza mostrando únicamente las tareas que coinciden con dicho filtro.

---

### User Story 3 - Transición de Estados del Ciclo de Vida (Priority: P2)

Como usuario autenticado, quiero actualizar el estado de mis tareas conforme avanzo en mi trabajo (pendiente, en progreso, completada), para reflejar fielmente el progreso de mis compromisos.

**Why this priority**: Permite que las tareas evolucionen a lo largo del tiempo. Depende de la existencia de tareas creadas (User Story 2) y sienta las bases del ciclo de vida del trabajo. Cubre HU-03.

**Independent Test**: Puede probarse tomando una tarea en estado "pendiente", transicionándola a "en progreso" y luego a "completada", validando que las transiciones no autorizadas son bloqueadas y que cada cambio queda registrado en la auditoría con su autor y marca de tiempo.

**Acceptance Scenarios**:

1. **Given** una tarea en estado "pendiente" de un usuario autenticado, **When** el usuario cambia el estado a "en progreso" o "completada", **Then** el sistema actualiza el estado y genera un registro de auditoría con la acción, el actor, la tarea y los estados anterior y posterior.
2. **Given** una tarea en estado "en progreso" de un usuario autenticado, **When** el usuario cambia el estado a "completada" o vuelve a "pendiente", **Then** el sistema registra la transición exitosamente y actualiza la auditoría.
3. **Given** una tarea en estado "completada", **When** el usuario intenta cambiar su estado a "pendiente" o "en progreso", **Then** el sistema bloquea la acción indicando que una tarea completada no admite cambio directo de estado en este incremento y requiere un proceso explícito de reapertura.
4. **Given** un usuario autenticado, **When** intenta cambiar el estado de una tarea perteneciente a otro usuario, **Then** el sistema rechaza terminantemente la solicitud y no modifica la tarea.

---

### User Story 4 - Edición y Mantenimiento de Tareas Existentes (Priority: P2)

Como usuario autenticado, quiero modificar el título, la descripción o la fecha límite de mis tareas registradas, para rectificar errores o actualizar información sin perder el historial.

**Why this priority**: Aporta flexibilidad operativa para corregir equivocaciones o replanificar plazos. Cubre HU-04.

**Independent Test**: Puede probarse editando una tarea existente modificando su título, descripción y fecha límite, verificando que los cambios persisten, que las validaciones son equivalentes a las de creación y que un usuario ajeno no puede editarla.

**Acceptance Scenarios**:

1. **Given** una tarea existente de un usuario autenticado, **When** el usuario actualiza su título por un nuevo valor válido y ajusta la descripción o la fecha límite, **Then** el sistema guarda los cambios y registra la modificación en el log de auditoría.
2. **Given** una tarea existente, **When** el usuario intenta actualizarla dejando el título vacío o con solo espacios, **Then** el sistema rechaza la actualización y conserva los valores previos intactos.
3. **Given** un usuario autenticado, **When** intenta editar una tarea que pertenece a otro usuario, **Then** el sistema deniega la operación con un error de autorización y no realiza modificaciones.

---

### Edge Cases

- **Correos con variaciones tipográficas**: Intentos de registro con correos idénticos pero con mayúsculas/minúsculas o espacios circundantes deben normalizarse (minúsculas, trim) para garantizar unicidad estricta.
- **Títulos con caracteres especiales o espacios múltiples**: Títulos compuestos exclusivamente de espacios o caracteres de control no imprimibles deben ser rechazados. Títulos válidos con espacios en los extremos deben ser sanitizados.
- **Manipulación de identificadores (Acceso cruzado)**: Intentos de acceder a las operaciones de visualización, edición o cambio de estado alterando identificadores en las solicitudes para apuntar a tareas de otros usuarios deben ser rechazados sin fuga de información (deben responder como recurso no encontrado o acceso no autorizado).
- **Contraseñas no conformes**: Intentos de registro con contraseñas de menos de 8 caracteres o que carezcan de al menos una letra o al menos un número deben ser rechazados con mensajes claros de validación.
- **Inyección de etiquetas HTML o scripts en texto**: Intentos de ingresar código HTML o secuencias de scripts en título o descripción deben ser tratados estrictamente como texto plano literal, escapando caracteres especiales para neutralizar inyecciones de código (XSS).
- **Fechas límite inválidas**: Intentos de suministrar valores de fecha no válidos o formatos no parseables deben ser rechazados con mensajes claros de validación. Las fechas válidas en el pasado están permitidas para registrar compromisos históricos o trabajo atrasado.
- **Intentos de transición sobre tareas inexistentes o ajenas**: Cualquier operación sobre una tarea inexistente debe manejarse limpiamente sin provocar errores no controlados en el sistema.
- **Sesión caducada o cerrada durante una operación**: Si un usuario envía un formulario o acción de tarea tras haber cerrado el navegador, cerrado sesión o destruido la cookie de sesión, la operación no debe ejecutarse y se debe redirigir al inicio de sesión.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a visitantes no registrados crear una cuenta suministrando una dirección de correo electrónico válida y una contraseña con una longitud mínima de 8 caracteres que contenga al menos una letra y al menos un número (HU-12).
- **FR-002**: El sistema DEBE validar la unicidad de las direcciones de correo electrónico, impidiendo el registro duplicado de una misma dirección independientemente de diferencias entre mayúsculas y minúsculas (HU-12).
- **FR-003**: El sistema DEBE almacenar las contraseñas de los usuarios exclusivamente mediante algoritmos de derivación y hash criptográficamente seguros, garantizando que ninguna contraseña exista en texto plano en la capa de datos (HU-12).
- **FR-004**: El sistema DEBE autenticar usuarios existentes mediante correo y contraseña, iniciando una sesión segura de navegador estándar que identifique al usuario en solicitudes posteriores y permanezca activa mientras el navegador continúe abierto (HU-13).
- **FR-005**: El sistema DEBE permitir a usuarios autenticados cerrar su sesión activa en cualquier momento, invalidando inmediatamente la sesión en el servidor y requiriendo un nuevo inicio de sesión para accesos posteriores (HU-13).
- **FR-006**: El sistema DEBE exigir y verificar sesión de usuario activa en el servidor para toda consulta, creación o modificación de tareas, impidiendo cualquier operación no autenticada (HU-13).
- **FR-007**: El sistema DEBE permitir a usuarios autenticados crear nuevas tareas asociadas a su cuenta, requiriendo obligatoriamente un título no vacío y aceptando opcionalmente descripción y fecha límite válida (admitiendo fechas de calendario presentes, futuras o pasadas) (HU-01).
- **FR-008**: Toda tarea nueva creada DEBE inicializarse automáticamente con el estado "pendiente" (HU-01).
- **FR-009**: El sistema DEBE registrar un evento de auditoría estructurado para cada creación de tarea, conteniendo la marca temporal precisa, el usuario responsable y la acción ejecutada (HU-01).
- **FR-010**: El sistema DEBE mostrar a cada usuario autenticado el listado de sus tareas registradas ordenadas por defecto por fecha de creación descendente (las más recientes primero), con su título, estado y fecha límite, garantizando aislamiento estricto respecto a tareas de otros usuarios (HU-02).
- **FR-011**: El sistema DEBE permitir filtrar el listado de tareas por su estado actual (todas, pendiente, en progreso, completada) (HU-02).
- **FR-012**: El sistema DEBE permitir actualizar el estado de una tarea perteneciente al usuario autenticado, admitiendo exclusivamente las siguientes transiciones directas: de "pendiente" a "en progreso" o "completada", y de "en progreso" a "pendiente" o "completada" (HU-03).
- **FR-013**: El sistema DEBE impedir y rechazar cualquier transición directa desde el estado "completada" hacia cualquier otro estado en este incremento (HU-03).
- **FR-014**: Toda transición de estado de una tarea DEBE generar un registro de auditoría con la marca de tiempo, el usuario responsable, el identificador de la tarea, el estado anterior y el nuevo estado (HU-03).
- **FR-015**: El sistema DEBE permitir a los usuarios autenticados editar el título, descripción y fecha límite de sus tareas existentes, aplicando las mismas reglas de validación que en la creación (admitiendo fechas de calendario en el pasado si tienen formato válido) (HU-04).
- **FR-016**: El sistema DEBE generar un registro de auditoría con marca temporal y autor para cada edición de atributos de una tarea (HU-04).
- **FR-017**: El sistema DEBE rechazar cualquier intento de consultar, editar o transicionar tareas que pertenezcan a otros usuarios, garantizando que un usuario solo pueda operar sobre sus propios recursos (HU-02, HU-03, HU-04).
- **FR-018**: El sistema DEBE validar y sanitizar en el servidor todos los datos recibidos (correo, contraseña, título, descripción, fecha límite y filtros), tratando la descripción estrictamente como texto plano sin interpretación de HTML ni Markdown, preservando únicamente saltos de línea y neutralizando inyecciones de código.

### Key Entities *(include if feature involves data)*

- **Usuario (User)**: Representa a la persona registrada en la plataforma.
  - Atributos clave: Identificador único, correo electrónico normalizado (único), credencial segura (hash de contraseña), fecha y hora de registro.
  - Relaciones: Posee cero o muchas Tareas y cero o muchos Registros de Auditoría.
- **Tarea (Task)**: Representa una unidad de trabajo individual bajo control de un usuario.
  - Atributos clave: Identificador único, identificador del usuario propietario, título (cadena obligatoria, no vacía), descripción (texto plano opcional, con saltos de línea preservados), fecha límite (fecha/hora opcional), estado ("pendiente", "en progreso", "completada"), fecha de creación, fecha de última modificación.
  - Relaciones: Pertenece a un único Usuario; genera múltiples Registros de Auditoría a lo largo de su ciclo de vida.
- **Registro de Auditoría (AuditLog)**: Representa la evidencia histórica inmutable de una mutación sobre una entidad.
  - Atributos clave: Identificador único, marca temporal (formato estándar con zona horaria), identificador del actor (usuario que ejecutó la acción), acción ejecutada (ej. `CREACION_TAREA`, `CAMBIO_ESTADO`, `EDICION_TAREA`), tipo y referencia de entidad afectada (`Tarea`, identificador), metadatos o detalle del cambio (ej. estado previo y posterior).
  - Relaciones: Vinculado al Usuario responsable y a la Tarea objeto de la modificación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los intentos de registro con correos duplicados, correos malformados o contraseñas no conformes son rechazados en el primer intento con mensajes claros.
- **SC-002**: Un usuario nuevo puede completar exitosamente su registro e iniciar sesión en menos de 60 segundos.
- **SC-003**: Cero incidentes de acceso cruzado entre cuentas: el 100% de las operaciones de consulta, modificación y transición de tareas garantizan aislamiento estricto por usuario (0% de fuga de datos o modificación cruzada).
- **SC-004**: El 100% de las creaciones, ediciones y transiciones de estado de tareas generan un evento de auditoría verificable con marca de tiempo precisa y autor identificado.
- **SC-005**: El 100% de los intentos de ejecutar transiciones no permitidas (incluyendo transiciones desde "completada") son bloqueados por el sistema manteniendo intacto el estado previo.
- **SC-006**: Los usuarios pueden listar y filtrar sus tareas por estado obteniendo resultados exactos y consistentes en el 100% de las consultas.
- **SC-007**: El 100% de las rutas y operaciones que modifican o consultan tareas exigen autenticación activa verificada en el servidor; el acceso no autenticado a datos privados es del 0%.

## Assumptions

- **Público objetivo y conectividad**: Los usuarios acceden mediante navegadores web modernos con conectividad a la red estándar.
- **Política de contraseñas**: Longitud mínima de 8 caracteres requiriendo al menos una letra y al menos un número.
- **Límites de campos**: El título de la tarea tendrá un límite de longitud razonable (hasta 200 caracteres); la descripción admite texto plano multilínea (hasta 2000 caracteres) sin formato HTML/Markdown.
- **Zonas horarias y fechas**: Las marcas de tiempo de auditoría y creación se registrarán con zona horaria coordinada (UTC). Las fechas límite de tareas son fechas de calendario seleccionadas por el usuario, admitiéndose fechas pasadas, presentes o futuras.
- **Ordenamiento por defecto**: El listado de tareas por defecto muestra todas las tareas del usuario ordenadas por fecha de creación descendente (las más recientes primero), pudiendo filtrarse por cada estado individual.
- **Persistencia de sesión**: Se utiliza una sesión de navegador estándar no permanente, la cual se mantiene activa durante la navegación y se destruye al cerrar la ventana del navegador o cerrar sesión explícitamente.
- **Límites de alcance explícitos (Fuera de este incremento)**:
  - Eliminación de tareas y borrado lógico (*soft delete*) (HU-05) queda diferido para un incremento posterior.
  - Reapertura de tareas completadas (HU-06) queda diferida para su propia especificación junto con HU-05.
  - Asignación de prioridades y categorías/proyectos (HU-07, HU-08) están fuera de alcance.
  - Indicadores automáticos de tareas vencidas (HU-09) están fuera de alcance.
  - Colaboración entre usuarios y notificaciones internas (HU-10, HU-11) están fuera de alcance.
  - Recuperación de contraseña por correo (HU-14) está fuera de alcance.
  - Interacciones asíncronas dinámicas sin recarga y drag-and-drop (HU-15, HU-16) están fuera de alcance.
- **Alineación con la Constitución**: La implementación subsiguiente (fase de planificación y tareas) cumplirá estrictamente con la constitución del proyecto en [.specify/memory/constitution.md](file:///G:/INFO%2003-02-2021/DOCUMENTOS/Jehg/jehg/UNIVERSIDAD/6%20Semestre/Pagina%20Disruptivas/.specify/memory/constitution.md):
  - Arquitectura monolítica en capas (Modelos, Servicios de dominio, Blueprints, Presentación Jinja2).
  - TDD obligatorio y bloqueante (pruebas en rojo primero para la lógica de dominio).
  - Contratos formales de endpoints documentados previo a la codificación.
  - Validación y sanitización exhaustiva en el backend.
  - Registro de auditoría estructurado para toda mutación.
