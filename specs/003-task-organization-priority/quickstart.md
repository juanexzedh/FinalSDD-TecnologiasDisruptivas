# Quickstart & Guía de Validación: TaskControl (Incremento 3)

**Feature**: `003-task-organization-priority`  
**Date**: 2026-10-07  
**Stack**: Python 3.11+, Flask 3.x, SQLAlchemy, Flask-Migrate, Flask-WTF (`CSRFProtect`), python-dotenv, pytest  

---

## 1. Prerrequisitos y Configuración Local

1. Asegurar dependencias del proyecto instaladas:
   ```bash
   pip install -r requirements.txt
   ```
2. Verificar el archivo `.env` en la raíz del proyecto:
   ```env
   FLASK_APP=src/taskcontrol:create_app
   FLASK_ENV=development
   FLASK_DEBUG=1
   SECRET_KEY=TU_CLAVE_ALEATORIA_GENERADA
   DATABASE_URL=sqlite:///taskcontrol.db
   ```

---

## 2. Aplicación de Migraciones de Base de Datos (Principio VI)

Ejecutar desde la raíz del proyecto para aplicar la migración incremental `add_categories_and_task_priority`:

```bash
flask db upgrade
```

> **Garantía de Integridad**: Todas las tareas preexistentes de los Incrementos 1 y 2 adquieren automáticamente `priority = 'medium'` (`server_default='medium'`) y `category_id = NULL`, preservando intactos todos los registros históricos y logs de auditoría.

---

## 3. Ejecución de la Aplicación

Iniciar el servidor web monolítico desde la raíz:

```bash
flask run
# Acceder a http://127.0.0.1:5000 en el navegador
```

---

## 4. Ejecución de Pruebas Automatizadas Bloqueantes (Principio IV)

Ejecutar las pruebas unitarias y de integración que salvaguardan las reglas de negocio del Incremento 3:

```bash
# 1. Pruebas unitarias de dominio (ordenamiento por prioridad, eliminación segura de categorías, cálculo de vencimiento)
pytest tests/unit/test_task_service.py tests/unit/test_category_service.py -v

# 2. Pruebas de integración de rutas, contratos HTTP y protección CSRF
pytest tests/integration/test_task_routes.py tests/integration/test_category_routes.py -v

# 3. Cobertura global de pruebas
pytest --cov=src/taskcontrol tests/
```

---

## 5. Escenarios de Validación Manual / End-to-End

### Escenario A: Prioridad de Tareas y Ordenamiento (HU-07)
1. **Crear tarea sin especificar prioridad**: Verificar que en la lista aparece con prioridad "Media" (`medium`).
2. **Crear tareas con prioridades variadas**: Registrar una tarea "Alta", una "Media" y una "Baja".
3. **Cambiar prioridad**: Modificar una tarea existente de "Media" a "Alta" mediante `POST /tasks/<id>/priority` o en el formulario de edición.
4. **Ordenar por prioridad**: En el listado, seleccionar orden "Por Prioridad". Comprobar que las tareas se ordenan estrictamente:
   - Primero todas las de prioridad **Alta** (`high`).
   - Luego las de prioridad **Media** (`medium`).
   - Finalmente las de prioridad **Baja** (`low`).
   - Dentro de cada grupo de prioridad, las más recientes aparecen primero (`created_at DESC`).
5. **Combinar con filtro de estado**: Filtrar por "En Progreso" y ordenar por prioridad. Comprobar que se muestran únicamente tareas en progreso, ordenadas de mayor a menor urgencia.

### Escenario B: Categorías y Desvinculación Segura sin Borrado en Cascada (HU-08)
1. **Crear categoría**: Ingresar a `/categories`, crear la categoría "Proyectos Web".
2. **Intentar duplicado**: Intentar crear nuevamente "proyectos web" (con minúsculas/mayúsculas); verificar que el sistema rechaza el duplicado con mensaje amigable.
3. **Asignar tareas**: Crear o editar dos tareas asignándoles la categoría "Proyectos Web".
4. **Filtrar por categoría**: En el listado de tareas, filtrar por "Proyectos Web"; verificar que solo se muestran las dos tareas asignadas.
5. **Eliminar categoría**: En `/categories`, presionar "Eliminar" en "Proyectos Web".
6. **Verificar desvinculación segura**: Volver al listado de tareas general. **Comprobar que las dos tareas continúan existiendo y activas**, pero ahora figuran como "Sin categoría" (`category_id = null`). ¡Ninguna tarea fue eliminada!

### Escenario C: Indicación de Tareas Vencidas Calculada en Backend (HU-09)
1. **Crear tarea vencida**: Registrar una tarea en estado "Pendiente" con fecha límite de ayer.
   - Verificar en la interfaz que aparece el badge de advertencia "Vencida" (`is_overdue = true`).
2. **Completar tarea vencida**: Cambiar el estado de la tarea a "Completada".
   - Verificar de inmediato que el indicador de vencida desaparece (`is_overdue = false`).
3. **Tarea para hoy**: Registrar una tarea con fecha límite de hoy.
   - Verificar que no aparece como vencida (`is_overdue = false`) durante todo el transcurso del día.
4. **Tarea eliminada**: Eliminar lógicamente una tarea con fecha pasada.
   - Verificar que en el backend nunca se evalúa como vencida.
