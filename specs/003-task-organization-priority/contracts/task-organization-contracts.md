# Contratos HTTP: Priorización, Filtros y Vencimiento de Tareas (HU-07, HU-08, HU-09)

**Feature**: `003-task-organization-priority`  
**Date**: 2026-10-07  
**Principio Constitucional**: III (Contrato explícito previo a la implementación) y VII (Seguridad por defecto)  

---

## 0. Política Global de Seguridad y CSRF

En estricto cumplimiento del Principio VII, **todas las peticiones mutantes con método POST** (`/tasks`, `/tasks/<id>/edit`, `/tasks/<id>/priority`, `/tasks/<id>/category`) exigen:
- **Autenticación activa**: Sesión verificada vía `@login_required`.
- **Protección CSRF**: Campo `csrf_token` en formularios o encabezado `X-CSRFToken` en peticiones `fetch`.
- **Fallo CSRF**: Retorna `400 Bad Request` con código de error `"CSRF_ERROR"`.

---

## 1. Listado Extendido de Tareas con Ordenamiento y Filtros Combinados (`HU-02`, `HU-07`, `HU-08`, `HU-09`)

### 1.1 `GET /tasks`
- **Descripción**: Consulta las tareas activas (`is_deleted == False`) del usuario autenticado, permitiendo combinar filtros por estado, filtros por categoría y ordenamiento por urgencia/prioridad o por fecha.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Parámetros de Consulta (Query String)**:
  - `status` (opcional, string): `'all'` (defecto), `'pending'`, `'in_progress'`, `'completed'`.
  - `sort_by` (opcional, string): 
    - `'created_desc'` (defecto): Ordena por fecha de creación descendente (`created_at DESC`).
    - `'priority'`: Ordena por nivel de prioridad descendente (`high` $\rightarrow$ `medium` $\rightarrow$ `low`), utilizando `created_at DESC` como criterio de desempate secundario.
  - `category_id` (opcional, string/entero):
    - `'all'` (defecto): Incluye tareas sin importar su categoría.
    - `'none'`: Filtra exclusivamente tareas que NO tienen categoría asignada (`category_id IS NULL`).
    - `<int>` (e.g. `2`): Filtra tareas asignadas a la categoría con ID especificado (debe pertenecer al usuario).
- **Cálculo de `is_overdue` en la respuesta (Backend Only - Principio III)**:
  - Cada tarea expone el campo booleano `is_overdue`.
  - Regla de evaluación en el servidor:
    - Si `is_deleted == True` $\rightarrow$ `false`
    - Si `status == 'completed'` $\rightarrow$ `false`
    - Si `due_date is None` $\rightarrow$ `false`
    - Si `due_date < datetime.now(timezone.utc).date()` $\rightarrow$ `true`
    - De lo contrario $\rightarrow$ `false`.
- **Respuestas**:
  - `200 OK` (Navegador): Renderiza la plantilla `tasks/index.html` con las tareas filtradas y ordenadas, exponiendo badges visuales de prioridad y de advertencia de vencimiento (`is_overdue`).
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "data": {
        "tasks": [
          {
            "id": 14,
            "title": "Entrega final de arquitectura",
            "description": "Subir informe y video explicativo",
            "due_date": "2026-10-06",
            "status": "pending",
            "priority": "high",
            "category": {
              "id": 1,
              "name": "Trabajo"
            },
            "is_overdue": true,
            "created_at": "2026-10-07T08:00:00Z"
          },
          {
            "id": 12,
            "title": "Planificación semanal",
            "description": "Revisión de metas",
            "due_date": "2026-10-15",
            "status": "in_progress",
            "priority": "medium",
            "category": null,
            "is_overdue": false,
            "created_at": "2026-10-07T09:30:00Z"
          },
          {
            "id": 8,
            "title": "Comprar insumos de oficina",
            "description": "Papelería",
            "due_date": "2026-10-01",
            "status": "completed",
            "priority": "low",
            "category": null,
            "is_overdue": false,
            "created_at": "2026-10-05T12:00:00Z"
          }
        ],
        "filters": {
          "status": "all",
          "category_id": "all",
          "sort_by": "priority"
        },
        "total": 3
      }
    }
    ```
  - `400 Bad Request` (Parámetros inválidos de ordenamiento o categoría):
    ```json
    {
      "status": "error",
      "code": "INVALID_QUERY_PARAMS",
      "message": "Parámetro de ordenamiento o identificador de categoría inválido."
    }
    ```

---

## 2. Modificación Rápida de Prioridad (`HU-07`)

### 2.1 `POST /tasks/<int:task_id>/priority`
- **Descripción**: Actualiza directamente la prioridad de una tarea activa y emite el evento de auditoría `TASK_PRIORITY_CHANGED`.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida.
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "priority": "high",
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
- **Validaciones en Backend**:
  - `csrf_token`: Obligatorio y válido contra la sesión activa.
  - La tarea debe pertenecer al usuario autenticado.
  - La tarea NO debe estar eliminada lógicamente (`is_deleted == False`).
  - `priority`: Obligatorio. Debe pertenecer estrictamente al conjunto de valores permitidos: `'high'`, `'medium'`, `'low'`.
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/tasks` con mensaje flash `"Prioridad actualizada exitosamente."`.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Prioridad actualizada exitosamente",
      "data": {
        "id": 14,
        "priority": "high",
        "previous_priority": "medium"
      }
    }
    ```
  - `400 Bad Request` (Valor de prioridad no admitido):
    ```json
    {
      "status": "error",
      "code": "INVALID_PRIORITY",
      "message": "Valor de prioridad inválido. Los valores admitidos son: high, medium, low."
    }
    ```
  - `404 Not Found`: Si la tarea no existe o pertenece a otro usuario.

---

## 3. Extensión de Creación de Tareas con Prioridad y Categoría (`HU-01`, `HU-07`, `HU-08`)

### 3.1 `POST /tasks` (Ampliación)
- **Descripción**: Registra una nueva tarea con soporte opcional para prioridad (por defecto `'medium'`) y categoría opcional.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida.
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "title": "Configurar monitoreo de servicios",
    "description": "Integrar métricas básicas",
    "due_date": "2026-10-20",
    "priority": "high",
    "category_id": 1,
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
- **Validaciones en Backend**:
  - `title`: Obligatorio (1-200 caracteres).
  - `priority`: Opcional. Si se omite o viene vacío, se fija por defecto `'medium'`. Si se provee, debe ser `'high'`, `'medium'` o `'low'`.
  - `category_id`: Opcional (entero o `null`). Si se provee, debe pertenecer al usuario autenticado.
- **Respuestas**:
  - `201 Created` / `302 Found`.

---

## 4. Extensión de Edición de Tareas (`HU-04`, `HU-07`, `HU-08`)

### 4.1 `POST /tasks/<int:task_id>/edit` (Ampliación)
- **Descripción**: Permite modificar título, descripción, fecha límite, prioridad y categoría de una tarea existente preservando su estado actual.
- **Autenticación requerida**: **SÍ** (`@login_required`).
- **Protección CSRF**: Requerida.
- **Payload de Entrada**:
  ```json
  {
    "title": "Configurar monitoreo de servicios (Actualizado)",
    "description": "Texto ampliado",
    "due_date": "2026-10-25",
    "priority": "low",
    "category_id": "",
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
  *(Enviar `category_id` vacío o nulo desvincula la tarea de su categoría previa).*
- **Validaciones**:
  - Valida propiedad de la tarea y de la nueva categoría si se especifica.
  - Registra cambios en auditoría si la prioridad o categoría cambian.
