# Tasks: Organización y Priorización de Tareas (Incremento 3)

**Branch**: `003-task-organization-priority` | **Date**: 2026-10-17 | **Spec**: [spec.md](specs/003-task-organization-priority/spec.md) | **Plan**: [plan.md](specs/003-task-organization-priority/plan.md)

**Scope**: HU-07 (Prioridad), HU-08 (Categorías), HU-09 (Vencimiento). Quedan estrictamente excluidas: HU-10, HU-11, HU-15 y HU-16.

---

## Phase 1: Setup (Infraestructura Compartida y Herramientas Base)

**Purpose**: Preparación de fixtures de testing y constantes de dominio base sin dependencias externas.

- [ ] T001 Configurar fixtures compartidas de categorías, prioridades y fechas de prueba en tests/conftest.py para soporte de base de datos en memoria y simulación de sesiones de usuario autenticado
- [ ] T002 [P] Definir constantes canónicas de prioridad (`ALLOWED_PRIORITIES = ('high', 'medium', 'low')`) y mapeo de ponderaciones de ordenamiento en src/taskcontrol/models/task.py
- [ ] T003 [P] Definir excepciones de dominio específicas `InvalidPriorityError(ValidationError)`, `DuplicateCategoryNameError(ValidationError)`, `CategoryLimitExceededError(ValidationError)` y `CategoryAccessDeniedError(NotFoundError)` en src/taskcontrol/services/errors.py

---

## Phase 2: Foundational (Esquema de Base de Datos y Migración Incremental)

**Purpose**: Modificaciones estructurales de persistencia y modelos que bloquean la implementación de las historias de usuario.

> ⚠️ **CRÍTICO**: Ninguna historia de usuario puede implementarse hasta completar esta fase.

- [ ] T004 Crear modelo de entidad `Category` en src/taskcontrol/models/category.py con `id` (Integer PK), `user_id` (Integer FK `users.id` con `ondelete='CASCADE'`), `name` (`String(50)`, nullable=False), `created_at` (`DateTime(timezone=True)` not null) y restricción única compuesta `uq_categories_user_id_name`
- [ ] T005 [P] Extender modelo `Task` en src/taskcontrol/models/task.py agregando columna `priority = db.Column(db.String(20), default='medium', server_default='medium', nullable=False)`, columna `category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)` e índices `ix_tasks_user_id_priority` e `ix_tasks_category_id`
- [ ] T006 Registrar y exportar `Category` en src/taskcontrol/models/__init__.py incluyéndolo en `__all__`
- [ ] T007 [P] Extender helper de auditoría para categorías `record_category_event(actor_id, action, category_id, details=None)` delegando en `record_event(actor_id, action, 'Category', category_id, details)` en src/taskcontrol/services/audit_service.py
- [ ] T008 Crear script de migración incremental versionado en migrations/versions/c3d4e5f6a7b8_add_categories_and_task_priority.py con `server_default='medium'` para `tasks.priority` y clave foránea `category_id` nullable con política declarativa `ON DELETE SET NULL`, garantizando cero pérdida o alteración de datos existentes de los Incrementos 1 y 2 (Principio VI)
- [ ] T009 Aplicar y verificar la migración incremental en la base de datos local ejecutando `flask db upgrade` en migrations/

**Checkpoint**: Base de datos, modelos relacionales y excepciones de dominio listos. La implementación de historias de usuario puede comenzar.

---

## Phase 3: User Story 1 - Asignación, Modificación y Ordenamiento por Prioridad (HU-07) (Priority: P1) 🎯 MVP

**Goal**: Permitir al usuario asignar un nivel de prioridad (`high`, `medium`, `low`) a sus tareas (con valor por defecto `medium`), actualizar rápidamente la prioridad de tareas activas mediante endpoint dedicado registrando auditoría inmutable `TASK_UPDATED` con metadatos `old_priority` y `new_priority`, y ordenar el listado por urgencia descendente (`high` -> `medium` -> `low`) con desempate por fecha de creación descendente.

**Independent Test**: Crear tareas sin especificar prioridad y verificar que asumen `'medium'`; crear tareas con prioridades variadas y comprobar que `GET /tasks?sort=priority` (o alias `sort_by=priority`) las lista en orden estricto `high` -> `medium` -> `low` desempatando por `created_at DESC`; invocar `POST /tasks/<id>/priority` con token CSRF y constatar en `audit_logs` la inserción de `TASK_UPDATED` con `old_priority` y `new_priority`; y confirmar que intentar mutar una tarea eliminada lógicamente (`is_deleted=True`) o ajena es bloqueado por el backend.

### Tests for User Story 1 (TDD - Escribir primero y verificar que fallen en rojo 🔴)

> **NOTA**: Ejecutar `.\venv\Scripts\python -m pytest tests/unit/test_task_service.py tests/integration/test_task_routes.py` y constatar el fallo inicial en rojo antes de implementar.

- [ ] T010 [P] [US1] Escribir pruebas unitarias en rojo en tests/unit/test_task_service.py para prioridad y ordenamiento: verificar `test_default_priority_is_medium_on_creation` (bloqueante), `test_invalid_priority_raises_domain_error` (bloqueante), `test_tasks_sorted_by_priority_descending` (`high` -> `medium` -> `low`) (bloqueante), y `test_tasks_priority_tiebreak_by_created_at_desc` (bloqueante)
- [ ] T011 [P] [US1] Escribir pruebas unitarias en rojo en tests/unit/test_task_service.py para actualización de prioridad, auditoría y aislamiento de eliminadas: verificar `test_set_task_priority_success` registrando `TASK_UPDATED` con metadatos `old_priority` y `new_priority`, `test_cannot_set_priority_on_deleted_task` (`TaskDeletedError`), y `test_cannot_set_priority_on_other_user_task` (`NotFoundError`)
- [ ] T012 [P] [US1] Escribir pruebas de integración HTTP en rojo en tests/integration/test_task_routes.py para endpoints de prioridad: verificar `POST /tasks/<id>/priority` con autenticación obligatoria `@login_required`, token CSRF requerido, soporte JSON 200 y HTML 302 con flash a `/tasks`, validación de prioridad permitida (HTTP 400 ante valor no canónico), y verificación de `GET /tasks?sort=priority` ordenando correctamente

### Implementation for User Story 1

- [ ] T013 [US1] Modificar funciones `_clean_fields`, `create_task` y `update_task` en src/taskcontrol/services/task_service.py para recibir y sanitizar `priority` (fijando por defecto `'medium'` si se omite; rechazando valores distintos a `ALLOWED_PRIORITIES` con `ValidationError`), y auditar `TASK_UPDATED` capturando `old_priority` y `new_priority` cuando la prioridad se modifique
- [ ] T014 [US1] Implementar método `set_task_priority(user_id, task_id, priority)` en src/taskcontrol/services/task_service.py: validar tarea activa propia vía `_active_task(user_id, task_id)` (bloqueando tareas eliminadas con `TaskDeletedError`), validar que `priority in ALLOWED_PRIORITIES`, actualizar `task.priority`, registrar evento inmutable de auditoría `TASK_UPDATED` con `{"old_priority": old_priority, "new_priority": priority}` vía `audit_service.record_task_event` y confirmar con commit
- [ ] T015 [US1] Extender método `get_user_tasks` en src/taskcontrol/services/task_service.py para soportar parámetro `sort` (y alias retrocompatible `sort_by`): si el valor es `'priority'`, aplicar ordenamiento con `db.case({'high': 3, 'medium': 2, 'low': 1}, value=Task.priority, else_=0).desc()` y desempate secundario por `Task.created_at.desc(), Task.id.desc()`
- [ ] T016 [US1] Implementar controlador `POST /tasks/<int:task_id>/priority` en src/taskcontrol/blueprints/tasks.py con decorador `@login_required` y validación obligatoria de token CSRF (`csrf_token` o `X-CSRFToken`), delegando en `task_service.set_task_priority` y retornando JSON 200 o redirección 302 con flash a `/tasks`
- [ ] T017 [US1] Actualizar controladores `list_tasks`, `create_task` y `update_task` en src/taskcontrol/blueprints/tasks.py para soportar el parámetro query `sort` / `sort_by`, procesar `priority` en formularios y payloads, e incluir `"priority": t.priority` en la serialización `_task_dict`
- [ ] T018 [US1] Actualizar vistas de creación y edición en src/taskcontrol/templates/tasks/new.html y src/taskcontrol/templates/tasks/edit.html agregando selector desplegable de prioridad (`Alta`, `Media`, `Baja`) con valor por defecto "Media" y campo CSRF
- [ ] T019 [US1] Actualizar vista de listado src/taskcontrol/templates/tasks/index.html y estilos en src/taskcontrol/static/css/styles.css agregando selector de ordenamiento por urgencia/fecha, badges visuales coloreados por nivel de prioridad (Alta: badge rojo/urgente, Media: badge azul, Baja: badge verde) y formulario rápido de actualización de prioridad con token CSRF

**Checkpoint**: User Story 1 completa y verificada con 100% de pruebas en verde. La priorización opera de forma independiente y segura como MVP.

---

## Phase 4: User Story 2 - Organización por Categorías o Proyectos Personales (HU-08) (Priority: P2)

**Goal**: Permitir al usuario autenticado crear, listar, renombrar y eliminar categorías personales (con validación de nombre 1-50 caracteres, unicidad case-insensitive tras trim y límite máximo de 50 categorías por cuenta), asociar tareas a categorías (máximo una por tarea), filtrar tareas acumulativamente por categoría (incluyendo tareas sin categoría `'uncategorized'` o `'none'`) en combinación ortogonal con filtros de estado y orden por prioridad, y garantizar que la eliminación de una categoría jamás borre tareas sino que las desvincule de forma segura (`ON DELETE SET NULL`) a nivel relacional.

**Independent Test**: Crear categorías y verificar rechazo ante duplicados insensibles a mayúsculas ("Trabajo" vs "trabajo") y límite de 50 categorías; renombrar una categoría y constatar que las tareas asociadas conservan su vínculo y se audita `CATEGORY_UPDATED`; asociar tareas y probar filtros acumulativos `status=in_progress&category=<id>&sort=priority` y `category=uncategorized`; eliminar la categoría vía POST con CSRF y verificar que las tareas asociadas permanecen activas e intactas con `category_id=None` y log `CATEGORY_DELETED`.

### Tests for User Story 2 (TDD - Escribir primero y verificar que fallen en rojo 🔴)

> **NOTA**: Ejecutar pruebas unitarias e integración de categorías confirmando que fallen en rojo antes de codificar `CategoryService`.

- [ ] T020 [P] [US2] Escribir pruebas unitarias en rojo en tests/unit/test_category_service.py para gestión y restricciones de categorías: verificar `test_create_category_success` (trim y longitud 1-50), `test_category_name_unique_per_user_case_insensitive` (rechazo de duplicados como "Trabajo" y "trabajo") (bloqueante), `test_cannot_create_more_than_50_categories_per_user` (`CategoryLimitExceededError` / HTTP 400), `test_get_user_categories_isolation` (aislamiento por usuario), y `test_rename_category_preserves_task_links_and_records_audit` (`CATEGORY_UPDATED` con `old_name` y `new_name`)
- [ ] T021 [P] [US2] Escribir pruebas unitarias en rojo en tests/unit/test_category_service.py para desvinculación relacional segura: verificar `test_delete_category_unlinks_tasks_setting_category_id_to_null` (bloqueante) constatando que al borrar una categoría sus tareas no se borran física ni lógicamente, `is_deleted` permanece `False`, `category_id` pasa a ser `None`, y se emite auditoría inmutable `CATEGORY_DELETED`
- [ ] T022 [P] [US2] Escribir pruebas unitarias en rojo en tests/unit/test_task_service.py para asignación y filtros combinados: verificar `test_assign_task_category_success`, `test_cannot_assign_category_from_another_user` (`CategoryAccessDeniedError`), `test_cannot_assign_category_to_deleted_task` (`TaskDeletedError`), `test_filter_tasks_by_category_id`, `test_filter_tasks_uncategorized`, y `test_get_tasks_combines_status_category_id_and_sort_by` (bloqueante - conjunción `AND` ortogonal entre estado, categoría y orden por prioridad)
- [ ] T023 [P] [US2] Escribir pruebas de integración HTTP en rojo en tests/integration/test_category_routes.py para endpoints de categorías y tareas: verificar `GET /categories`, `POST /categories` (CSRF, error 400 por duplicado o límite excedido), `POST /categories/<id>/edit` (CSRF, renombrado con flash/JSON), `POST /categories/<id>/delete` (CSRF, confirmación de tareas preservadas) y `POST /tasks/<id>/category` (CSRF, asignación/desasignación)

### Implementation for User Story 2

- [ ] T024 [US2] Implementar servicio de dominio `CategoryService` en src/taskcontrol/services/category_service.py: métodos `create_category(user_id, name)` (validando nombre no vacío tras trim, longitud 1-50 caracteres, validación de tope máx. 50 categorías por usuario y unicidad case-insensitive con `func.lower`, auditando `CATEGORY_CREATED`), `get_user_categories(user_id)` con conteo de tareas activas asociadas, `update_category(user_id, category_id, new_name)` (validando unicidad case-insensitive, preservando intactas las tareas asociadas y registrando `CATEGORY_UPDATED` con `old_name` y `new_name`), y `delete_category(user_id, category_id)` (validando pertenencia, eliminando la fila de categoría para que el motor SQL ejecute `ON DELETE SET NULL`, registrando `CATEGORY_DELETED` y confirmando commit)
- [ ] T025 [US2] Extender src/taskcontrol/services/task_service.py con método `assign_task_category(user_id, task_id, category_id)`: validar tarea activa propia vía `_active_task` (rechazando tareas con `is_deleted=True`), si `category_id` no es nulo verificar que la categoría exista y pertenezca al usuario (lanzando `CategoryAccessDeniedError` ante ID ajeno), asignar `task.category_id`, registrar auditoría `TASK_CATEGORY_ASSIGNED` con `previous_category_id` y `new_category_id`, y confirmar commit
- [ ] T026 [US2] Modificar métodos `create_task` y `update_task` en src/taskcontrol/services/task_service.py para admitir el parámetro opcional `category_id`, verificando pertenencia al usuario autenticado antes de asociar
- [ ] T027 [US2] Extender método `get_user_tasks` en src/taskcontrol/services/task_service.py para admitir filtrado por categoría: soportar parámetro `category` (y alias retrocompatible `category_id`), aplicando `Task.category_id.is_(None)` para valores `'uncategorized'` o `'none'`, y filtrando por `Task.category_id == cat_id` para ID numérico (si la categoría es inexistente o ajena, retornar consulta vacía sin exponer datos de otros usuarios), combinando mediante conjunción lógica `AND` con el filtro de `status` y el ordenamiento `sort`
- [ ] T028 [US2] Crear blueprint de controladores src/taskcontrol/blueprints/categories.py implementando rutas `GET /categories`, `POST /categories`, `POST /categories/<int:category_id>/edit` y `POST /categories/<int:category_id>/delete` con decorador `@login_required`, protección CSRF obligatoria y soporte para respuestas HTML y JSON
- [ ] T029 [US2] Registrar `categories_bp` en la Application Factory en src/taskcontrol/__init__.py
- [ ] T030 [US2] Implementar controlador `POST /tasks/<int:task_id>/category` en src/taskcontrol/blueprints/tasks.py con `@login_required` y token CSRF requerido, delegando en `task_service.assign_task_category`
- [ ] T031 [US2] Actualizar serialización `_task_dict` en src/taskcontrol/blueprints/tasks.py para incluir `"category": {"id": t.category.id, "name": t.category.name} if t.category else None`, y adaptar `list_tasks` para procesar el parámetro de consulta `category` / `category_id`
- [ ] T032 [US2] Crear vista de gestión de categorías en src/taskcontrol/templates/categories/index.html con formulario de creación con CSRF, listado de categorías con conteo de tareas, formulario de renombrado con CSRF y formulario de eliminación con CSRF y advertencia de desvinculación
- [ ] T033 [US2] Actualizar barra de navegación en src/taskcontrol/templates/base.html agregando el enlace accesible a "Categorías" (`url_for('categories.list_categories')`) visible para usuarios autenticados
- [ ] T034 [US2] Actualizar vistas src/taskcontrol/templates/tasks/new.html, src/taskcontrol/templates/tasks/edit.html y src/taskcontrol/templates/tasks/index.html incorporando selector de categoría opcional en formularios y filtro desplegable por categoría en el listado de tareas

**Checkpoint**: User Stories 1 y 2 completamente operativas e integradas sin cascada de borrado ni colisiones de categorías.

---

## Phase 5: User Story 3 - Identificación Visual y Filtrado de Tareas Vencidas en Backend (HU-09) (Priority: P3)

**Goal**: Identificar con precisión en el servidor tareas con fecha límite superada (`due_date < current_date_utc`) calculando la propiedad derivada en memoria `is_overdue` exclusivamente en el backend (sin columnas de base de datos persistidas ni cron jobs externos), excluyendo categóricamente tareas completadas (`status = 'completed'`) o eliminadas lógicamente (`is_deleted = True`), y considerando que una tarea con fecha de hoy no está vencida.

**Independent Test**: Crear una tarea con fecha límite de ayer y verificar que expone `is_overdue=True` y badge "Vencida" en la UI; transicionar dicha tarea a `completed` y constatar de inmediato que `is_overdue` pasa a `False`; eliminar lógicamente una tarea con fecha pasada y verificar que `is_overdue` es `False`; crear una tarea con fecha límite de hoy y comprobar que `is_overdue` es `False` evaluada en UTC; y verificar en las respuestas JSON de `GET /tasks` el atributo booleano explícito `is_overdue`.

### Tests for User Story 3 (TDD - Escribir primero y verificar que fallen en rojo 🔴)

> **NOTA**: Ejecutar pruebas unitarias e integración de vencimiento confirmando que fallen en rojo antes de implementar la propiedad derivada.

- [ ] T035 [P] [US3] Escribir pruebas unitarias en rojo en tests/unit/test_task_service.py para cálculo de vencimiento en backend: verificar `test_completed_task_with_past_due_date_is_never_overdue` (bloqueante), `test_soft_deleted_task_with_past_due_date_is_never_overdue` (bloqueante), `test_pending_or_in_progress_task_with_past_due_date_is_overdue`, `test_task_with_due_date_today_is_not_overdue_utc` (bloqueante), y `test_task_without_due_date_is_not_overdue`
- [ ] T036 [P] [US3] Escribir pruebas de integración HTTP en rojo en tests/integration/test_task_routes.py para visualización y serialización de vencimiento: verificar que la respuesta JSON de `GET /tasks` incluye `"is_overdue": true|false`, y que el renderizado HTML inyecta el badge visual de vencimiento exclusivamente en tareas activas vencidas

### Implementation for User Story 3

- [ ] T037 [US3] Implementar la propiedad derivada `@property def is_overdue(self) -> bool` en el modelo `Task` en src/taskcontrol/models/task.py: retornar `False` si `self.is_deleted == True`, `self.status == 'completed'` o `self.due_date is None`; y retornar `self.due_date < datetime.now(timezone.utc).date()` para evaluar deterministamente la superación de fecha en UTC sin considerar vencida la fecha del día actual
- [ ] T038 [US3] Incorporar `"is_overdue": t.is_overdue` en el helper de serialización `_task_dict(t)` en src/taskcontrol/blueprints/tasks.py para garantizar el contrato explícito de salida JSON hacia el cliente JavaScript
- [ ] T039 [US3] Actualizar la plantilla de listado src/taskcontrol/templates/tasks/index.html para renderizar el badge condicional `{% if task.is_overdue %}<span class="badge badge-overdue">Vencida</span>{% endif %}` junto al indicador de fecha límite
- [ ] T040 [US3] Incorporar estilos visuales para `.badge-overdue` en src/taskcontrol/static/css/styles.css con contraste accesible y alerta visual distintiva respecto a las insignias de prioridad

**Checkpoint**: Todas las historias de usuario (HU-07, HU-08, HU-09) implementadas, probadas y funcionales de forma independiente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verificaciones integrales de calidad, seguridad, regresión, pruebas bloqueantes y cumplimiento estricto del alcance.

- [ ] T041 [P] Ejecutar la suite completa de pruebas unitarias y de integración con cobertura (`.\venv\Scripts\python -m pytest tests/ -v --cov=src/taskcontrol`) verificando 100% de pruebas en verde y cero regresiones respecto a los Incrementos 1 y 2
- [ ] T042 Verificar exhaustivamente la ejecución de todas las pruebas bloqueantes estipuladas por el usuario: ordenamiento por prioridad descendente con desempate por fecha de creación; prioridad por defecto 'medium'; desvinculación segura de tareas al eliminar categoría; unicidad case-insensitive de categorías; exclusión de tareas completadas y eliminadas del estado vencido; fecha de hoy no vencida; y combinación ortogonal de `status`, `category_id` y `sort_by` en `GET /tasks`
- [ ] T043 [P] Auditar la protección CSRF en todos los formularios y endpoints mutantes POST nuevos (`POST /tasks/<id>/priority`, `POST /categories`, `POST /categories/<id>/edit`, `POST /categories/<id>/delete`, `POST /tasks/<id>/category`) en tests/integration/test_csrf.py
- [ ] T044 [P] Verificar que todos los servicios respeten rigurosamente el aislamiento de tareas eliminadas lógicamente (`is_deleted == False`), impidiendo cualquier mutación sobre tareas soft-deleted
- [ ] T045 Validar el cumplimiento estricto del alcance, confirmando que NO se hayan implementado ni incluido componentes de asignación a otros usuarios (HU-10), notificaciones internas (HU-11), interactividad asíncrona sin recarga (HU-15) ni drag-and-drop (HU-16)
- [ ] T046 Ejecutar validación manual guiada siguiendo los escenarios de specs/003-task-organization-priority/quickstart.md certificando la consistencia extremo a extremo

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias - inicia inmediatamente
- **Foundational (Phase 2)**: Depende de Phase 1 - BLOQUEA todas las historias de usuario
- **User Story 1 (Phase 3)**: Depende de Phase 2 (Foundational) - No depende de US2 ni US3 (MVP)
- **User Story 2 (Phase 4)**: Depende de Phase 2 (Foundational) - Integra con Task pero es independiente de US3
- **User Story 3 (Phase 5)**: Depende de Phase 2 (Foundational) - Requiere el modelo extendido de Task
- **Polish (Phase 6)**: Depende de la finalización de todas las historias de usuario deseadas

### Within Each User Story

1. Pruebas TDD escritas PRIMERO y verificadas en ROJO 🔴
2. Extensiones de modelo / excepciones
3. Capa de servicios y lógica de dominio respetando `is_deleted`
4. Controladores HTTP en blueprints con protección CSRF
5. Vistas y plantillas Jinja2 / estáticos
6. Verificación de pruebas en VERDE 🟢

### Parallel Opportunities

- Todas las tareas marcadas `[P]` pueden ejecutarse en paralelo al no compartir archivos ni tener dependencias incompletas.
- En Phase 1: `T002` y `T003` en paralelo tras `T001`.
- En Phase 2: `T005` y `T007` en paralelo.
- En Phase 3: Pruebas `T010`, `T011` y `T012` en paralelo.
- En Phase 4: Pruebas `T020`, `T021`, `T022` y `T023` en paralelo.
- En Phase 5: Pruebas `T035` y `T036` en paralelo.
- En Phase 6: Tareas de auditoría `T041`, `T043` y `T044` en paralelo.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRÍTICO - migración y modelos base)
3. Completar Phase 3: User Story 1 (Prioridad y ordenamiento)
4. **DETENERSE y VALIDAR**: Ejecutar pruebas de User Story 1 independientemente
5. Demostración funcional del incremento MVP

### Incremental Delivery

1. Setup + Foundational -> Base de datos y modelos listos
2. User Story 1 (HU-07) -> Tareas con prioridad alta/media/baja y orden ponderado (MVP)
3. User Story 2 (HU-08) -> Categorías, renombrado, límite de 50 y desvinculación sin borrado en cascada
4. User Story 3 (HU-09) -> Indicador en backend de vencimiento en UTC y badges visuales
5. Polish -> Cobertura total, auditoría CSRF y verificación de exclusión de HU-10, HU-11, HU-15 y HU-16
