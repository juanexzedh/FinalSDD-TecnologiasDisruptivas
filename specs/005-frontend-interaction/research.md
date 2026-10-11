# Research & Technical Decisions: Incremento 5 TaskControl

**Feature**: `005-frontend-interaction` (Mejoras de interacción frontend mediante JavaScript: actualización asíncrona y drag-and-drop)  
**Date**: 2026-10-08  
**Status**: Completed  

---

## 1. Estrategia de JavaScript para Interacción sin Recarga (HU-15)

### Contexto y Requisitos
El requerimiento HU-15 exige que los usuarios puedan marcar tareas como completadas desde el listado sin recargar la página. Si la petición falla, la interfaz debe revertir inmediatamente el estado visual (Optimistic UI con Rollback) y notificar el error, impidiendo discrepancias con el backend.

### Decisión
1. **API Nativa `fetch`**:
   - Se utiliza `fetch` estándar de JavaScript en `static/js/main.js` consumiendo el endpoint ya existente `POST /tasks/<id>/status` (definido en el Incremento 1).
   - Inyección de CSRF: Extrae el token sincronizador de `<meta name="csrf-token" content="{{ csrf_token() }}">` y lo envía en el encabezado `X-CSRFToken` y `Content-Type: application/json`.
   - Payload: `{ "status": "completed" }`.
2. **Patrón Optimista con Reversión Visual Determinista**:
   ```javascript
   async function toggleTaskComplete(taskId, checkboxElement) {
       const taskCard = checkboxElement.closest('.task-card');
       const previousChecked = !checkboxElement.checked; // Estado original antes del clic
       
       // 1. Cambio visual optimista inmediato (< 10 ms)
       taskCard.classList.toggle('task-completed', checkboxElement.checked);
       checkboxElement.disabled = true; // Prevenir clics duplicados concurrentes

       try {
           const response = await fetch(`/tasks/${taskId}/status`, {
               method: 'POST',
               headers: {
                   'Content-Type': 'application/json',
                   'X-CSRFToken': getCsrfToken()
               },
               body: JSON.stringify({ status: 'completed' })
           });

           if (!response.ok) {
               const errData = await response.json().catch(() => ({}));
               throw new Error(errData.message || 'Error al actualizar el estado de la tarea.');
           }

           // 2. Éxito confirmado: consolidar UI y actualizar badges
           checkboxElement.disabled = false;
           updateOverdueBadge(taskCard, false); // Tarea completada nunca está vencida
       } catch (error) {
           // 3. Rollback visual determinista ante cualquier fallo
           checkboxElement.checked = previousChecked;
           taskCard.classList.toggle('task-completed', previousChecked);
           checkboxElement.disabled = false;
           showToast(error.message, 'error');
       }
   }
   ```
3. **Justificación frente a Frameworks Adicionales (Principio V y Restricción Técnica 4)**:
   - Se rechaza formalmente la introducción de frameworks SPA (React, Vue, Angular) o micro-frameworks (Alpine.js, HTMX). La manipulación requerida es directa sobre nodos existentes del DOM renderizados por Jinja2 y toma menos de 40 líneas de código nativo. Añadir un framework violaría el Principio V (Simplicidad) y la Restricción Técnica 4 del stack sin brindar valor arquitectónico adicional.

---

## 2. Técnica y Librería para Drag-and-Drop (HU-16)

### Contexto y Requisitos
HU-16 exige reordenar visualmente tareas en el listado arrastrándolas y soltándolas, persistiendo el orden de forma inmediata en el backend.

### Decisión
1. **Técnica Elegida**:
   - Se implementa mediante **la API nativa HTML5 Drag and Drop** (`draggable="true"`, eventos `dragstart`, `dragover`, `drop`, `dragend`) o alternativamente mediante la micro-librería utilitaria sin dependencias **`SortableJS`** (~10 KB minificado) alojada localmente en `static/js/sortable.min.js`.
2. **Justificación Constitucional**:
   - `SortableJS` no es un framework SPA. No gestiona enrutamiento, no posee Virtual DOM, no altera el flujo de renderizado en servidor de Jinja2 y no exige cadenas de herramientas Node.js/Webpack. Es un componente imperativo liviano de interfaz que complementa directamente a Jinja2 y JavaScript vanilla.
3. **Flujo de Persistencia tras el Drop**:
   - Al soltarse una tarjeta (`drop` / evento `onEnd`):
     1. JavaScript recopila en orden los identificadores de tarea visibles en el DOM: `const taskIds = Array.from(list.children).map(el => parseInt(el.dataset.taskId));`
     2. Envía `fetch('/tasks/reorder', { method: 'POST', body: JSON.stringify({ task_ids: taskIds }), headers: ... })`.
     3. Si la llamada falla, JavaScript revierte la posición de los nodos en el DOM al orden previo (rollback del DOM) y muestra un mensaje de alerta.

---

## 3. Modelo de Datos y Contrato de Persistencia de Orden

### Decisión
1. **Único Cambio de Backend**:
   - Columna `position` en la tabla `tasks`: `Integer`, `nullable=False`, `default=0`, `server_default='0'`.
   - Índice compuesto: `ix_tasks_user_id_position` sobre `(user_id, position)` para optimizar el listado predeterminado.
2. **Endpoint de Reordenamiento**:
   - `POST /tasks/reorder` dentro del blueprint `tasks.py`.
   - Payload: `{ "task_ids": [15, 12, 8, 3], "csrf_token": "..." }`.
   - Se procesa en `TaskService.reorder_tasks(user_id, task_ids)` validando que todas las tareas pertenezcan al usuario autenticado.

---

## 4. Prevención de Inconsistencias entre Usuarios Concurrentes (Principio VII)

### Decisión
1. **Aislamiento por Usuario**:
   - El orden es estrictamente local por usuario (`Task.user_id == current_user.id`), no una secuencia global.
   - Dos usuarios reordenando sus tareas operan sobre filas disjuntas de la base de datos relacional.
2. **Validación de Propiedad Estricta**:
   - `TaskService.reorder_tasks` valida que cada ID en `task_ids` pertenezca al usuario en sesión (`user_id`). Si se incluye un ID ajeno, la transacción se revierte con excepción `TaskAccessDeniedError` (HTTP 403), impidiendo manipulación cruzada (Principio VII).
