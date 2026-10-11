<!--
Sync Impact Report:
- Version change: Initial Scaffold -> v1.0.0
- List of modified principles:
  - Defined Principle I: Monolito por diseño
  - Defined Principle II: Separación de responsabilidades dentro del monolito
  - Defined Principle III: Contrato explícito entre backend y JavaScript
  - Defined Principle IV: Test-first para toda la lógica de negocio (bloqueante)
  - Defined Principle V: Simplicidad sobre generalidad prematura
  - Defined Principle VI: Integridad de datos y migraciones versionadas
  - Defined Principle VII: Seguridad por defecto
  - Defined Principle VIII: Observabilidad mínima viable
- Added sections:
  - Restricciones Técnicas y del Stack Tecnológico
  - Flujo de Desarrollo, Calidad y Trazabilidad con el Backlog
  - Governance (Gobernanza, cumplimiento y versionado semántico)
- Removed sections: N/A (reemplazo del andamiaje base inicial)
- Follow-up TODOs: Ninguno (todos los tokens y directrices han sido formalizados)
-->

# TaskControl Constitution

## Core Principles

### I. Monolito por Diseño
El sistema TaskControl se concibe y construye como un monolito estricto: un único repositorio de código fuente, un único proceso de aplicación desplegable y una única base de datos relacional compartida.
- Queda expresamente prohibida la introducción de microservicios, funciones desacopladas o sistemas de mensajería asíncrona distribuida (colas como Celery, RabbitMQ o Redis Streams) durante el desarrollo base del roadmap.
- Cualquier propuesta de desacoplamiento arquitectónico requerirá una enmienda constitucional respaldada por evidencia empírica verificable que demuestre que el proceso monolítico no puede satisfacer un requisito técnico o de rendimiento específico.

### II. Separación de Responsabilidades dentro del Monolito
El monolito DEBE estructurarse internamente mediante capas de responsabilidad nítidas y dependencias estrictamente unidireccionales:
1. **Capa de Modelos y Datos**: Modelos de persistencia (SQLAlchemy) y mapeo relacional.
2. **Capa de Dominio / Lógica de Negocio (Servicios)**: Reglas de negocio puras, transiciones de estado, auditoría y orquestación, independientes de cualquier contexto HTTP.
3. **Capa de Rutas y Controladores HTTP**: Blueprints de Flask encargados exclusivamente de recibir solicitudes HTTP, deserializar parámetros, delegar en la capa de servicios y devolver respuestas HTTP estructuradas.
4. **Capa de Presentación**: Plantillas Jinja2 para renderizado inicial del servidor y JavaScript en el cliente para interactividad dinámica.

*Regla de acceso*: Ninguna capa accederá a otra saltándose la inmediatamente inferior. Queda prohibido que las rutas de Flask o las plantillas Jinja2 ejecuten consultas ORM directas o manipulen la base de datos sin pasar por la capa de servicios; la capa de servicios nunca debe manipular objetos de petición o respuesta HTTP (`request`/`Response`).

### III. Contrato Explícito entre Backend y JavaScript
Toda comunicación cliente-servidor para interactividad dinámica en el cliente JavaScript DEBE realizarse a través de endpoints HTTP con un contrato rigurosamente definido y documentado con anterioridad a su implementación:
- Cada contrato DEBE especificar: ruta URL, método HTTP, parámetros/cuerpo de solicitud, esquema de respuesta JSON exitosa (códigos 2xx) y catálogo de respuestas ante errores previsibles (códigos 4xx y 5xx).
- La interfaz de JavaScript consumirá exclusivamente estos contratos, manejando de forma determinista las respuestas de error y evitando suposiciones sobre el estado interno del servidor.

### IV. Test-First para Toda la Lógica de Negocio (Bloqueante)
Toda lógica de negocio en la capa de dominio DEBE desarrollarse bajo la disciplina de Test-Driven Development (TDD):
- Operaciones críticas como creación de tareas, transiciones de estado válidas e inválidas, eliminación lógica (soft delete), reaperturas, asignación a usuarios y validaciones de datos DEBEN especificarse primero mediante pruebas automatizadas que fallen inicialmente (Red).
- Únicamente tras confirmar el fallo de la prueba se implementará el código mínimo necesario para superarla (Green), procediendo luego a la refactorización (Refactor).
- Este principio es **bloqueante**: ningún commit o Pull Request que agregue o modifique reglas en la capa de dominio será aceptado sin sus correspondientes pruebas automatizadas aprobadas.

### V. Simplicidad sobre Generalidad Prematura
El diseño del sistema priorizará en todo momento la simplicidad y el enfoque directo sobre cualquier abstracción o generalización anticipada:
- No se introducirán capas de abstracción no requeridas, sistemas de plugins, motores de reglas dinámicos ni patrones de diseño complejos sin un requisito explícito e inmediato derivado del backlog.
- Cada elemento de código debe resolver una necesidad funcional actual (filosofía YAGNI), evitando código preparatorio para escenarios futuros no especificados.

### VI. Integridad de Datos y Migraciones Versionadas
La persistencia y el esquema de la base de datos relacional son activos críticos que demandan máxima integridad:
- Cualquier alteración estructural al esquema de la base de datos (tablas, campos, índices, claves foráneas) DEBE realizarse exclusivamente mediante scripts de migración reproducibles y versionados en el repositorio utilizando Flask-Migrate (Alembic).
- Queda terminantemente prohibida cualquier modificación manual directa sobre bases de datos de desarrollo, pruebas o producción.
- La eliminación de entidades clave como tareas DEBE gestionarse de forma lógica (soft delete) para garantizar la integridad referencial y la continuidad del log de auditoría.

### VII. Seguridad por Defecto
La seguridad debe ser intrínseca al desarrollo y verificarse activamente en cada punto de interacción:
- **Validación del lado del servidor**: Toda entrada de usuario DEBE validarse y sanitizarse exhaustivamente en el backend antes de ser procesada o persistida, independientemente de que existan validaciones en el cliente JavaScript.
- **Autenticación y autorización continua**: Cada endpoint que consulte o modifique datos DEBE verificar la identidad del usuario y sus permisos de acceso sobre el recurso solicitado en el backend, no dependiendo únicamente de elementos visuales ocultos en la interfaz.
- **Protección de credenciales y secretos**: Las contraseñas de usuario se almacenarán siempre aplicando algoritmos de hash criptográficamente seguros (bcrypt / Argon2). Ningún secreto, token o clave de entorno (`SECRET_KEY`) debe ser versionado en el repositorio de control de versiones.

### VIII. Observabilidad Mínima Viable
Toda mutación de estado que ocurra dentro del dominio de tareas DEBE registrarse de forma consistente e inmediata en un log estructurado desde el primer incremento funcional:
- Cada evento registrado DEBE contener mínimamente: marca de tiempo en formato ISO 8601 (`timestamp`), identificador del usuario responsable (`actor`), acción ejecutada (`action`, e.g., `TASK_CREATED`, `STATE_TRANSITION`, `TASK_SOFT_DELETED`), entidad afectada (`entity`) y metadatos relevantes del cambio (estado previo y posterior).
- Los registros de observabilidad deben ser accesibles para auditoría operativa y soporte de diagnósticos de error.

## Restricciones Técnicas y del Stack Tecnológico

1. **Lenguaje y Entorno**: Python versión 3.11 o superior.
2. **Framework Web**: Flask como único framework web permitido para el backend. Queda prohibida la introducción de alternativas como FastAPI, Django o Tornado sin una enmienda constitucional previa.
3. **ORM y Persistencia**: SQLAlchemy (vía Flask-SQLAlchemy) como ORM oficial sobre una base de datos relacional (SQLite para entornos de desarrollo/pruebas locales y PostgreSQL para entornos de despliegue).
4. **Capa Cliente (Frontend)**: Plantillas Jinja2 para renderizado en servidor complementadas con JavaScript vanilla (estándar) para interactividad y peticiones asíncronas vía `fetch`. No se permite el uso de frameworks SPA pesados (como React, Angular o Vue) por defecto, manteniendo la pila liviana y monolítica.
5. **Ejecución Unificada**: El entorno de desarrollo y la aplicación deben ser capaces de inicializarse y ejecutarse localmente con un único comando documentado, permitiendo una puesta en marcha ágil y reproducible.

## Flujo de Desarrollo, Calidad y Trazabilidad con el Backlog

El desarrollo de TaskControl está directamente gobernado por el backlog del proyecto establecido en [.specify/memory/backlog.md](file:///G:/INFO%2003-02-2021/DOCUMENTOS/Jehg/jehg/UNIVERSIDAD/6%20Semestre/Pagina%20Disruptivas/.specify/memory/backlog.md):
- **Trazabilidad de Historias (HU-XX)**: Todo incremento funcional, rama, especificación o conjunto de pruebas debe asociarse explícitamente a su identificador de historia de usuario correspondiente según las 5 épicas del proyecto:
  - *Épica 1 — Gestión de tareas (núcleo del dominio)*: HU-01 (creación), HU-02 (listado/filtro), HU-03 (cambio de estado), HU-04 (edición), HU-05 (soft delete) y HU-06 (reapertura).
  - *Épica 2 — Organización y priorización*: HU-07 (prioridad), HU-08 (categorías/proyectos) y HU-09 (indicación visual de vencimiento en backend).
  - *Épica 3 — Colaboración*: HU-10 (asignación entre usuarios) y HU-11 (notificaciones internas).
  - *Épica 4 — Cuentas y acceso*: HU-12 (registro y hashing seguro), HU-13 (sesión y control de acceso en backend) y HU-14 (recuperación de acceso).
  - *Épica 5 — Interfaz e interacción*: HU-15 (actualización asíncrona sin recarga con reversión ante error) y HU-16 (reordenamiento drag & drop persistido).
- **Enfoque del Primer Incremento**: Conforme al principio de simplicidad, el primer incremento funcional se focalizará estrictamente en el conjunto *Must*: HU-01 a HU-04 (núcleo de tareas) y HU-12 a HU-13 (cuentas y autenticación segura), sentando las bases arquitectónicas antes de abordar colaboración o interactividad avanzada.
- **Criterios de Aceptación como Barrera de Calidad**: Ninguna tarea o historia de usuario se considerará finalizada si no satisface el 100% de los criterios de aceptación estipulados en el backlog junto con sus pruebas automatizadas unitarias y de integración.

## Governance

- **Supremacía Constitucional**: Esta constitución representa la normativa máxima para el diseño y construcción de TaskControl. Prevalece sobre decisiones puntuales o preferencias de implementación que contravengan sus principios.
- **Verificación en Revisiones**: Toda revisión de código (Pull Request o Merge Request) debe verificar el cumplimiento de los 8 principios y las restricciones de stack. Cualquier violación estructural o introducción no justificada de complejidad será causal de rechazo.
- **Procedimiento de Enmienda**: Toda modificación a la presente constitución requerirá una propuesta documentada que exponga: justificación basada en evidencia técnica, análisis de impacto en la arquitectura y en el backlog, y plan de migración.
- **Versionado Semántico de la Constitución**:
  - **MAYOR (MAJOR)**: Cambios incompatibles con la arquitectura base o su gobernanza (por ejemplo, disolver el monolito hacia microservicios, sustitución de Flask por otro framework web, o eliminación de la obligatoriedad de TDD o seguridad por defecto).
  - **MENOR (MINOR)**: Adición de nuevos principios, incorporación de nuevas restricciones tecnológicas compatibles o ampliación sustancial de secciones normativas.
  - **PARCHE (PATCH)**: Correcciones ortográficas, mejoras de redacción, ajuste de referencias cruzadas o aclaraciones no semánticas.

**Version**: 1.0.0 | **Ratified**: 2026-10-06 | **Last Amended**: 2026-10-06
