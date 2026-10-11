# Quickstart & Guía de Validación: TaskControl (Incremento 4)

**Feature**: `004-user-collaboration`  
**Date**: 2026-10-08  
**Stack**: Python 3.11+, Flask 3.x, SQLAlchemy, Flask-Migrate, Flask-WTF (`CSRFProtect`), python-dotenv, pytest  

---

## 1. Prerrequisitos y Configuración Local

1. Asegurar que las dependencias del proyecto están instaladas:
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

Ejecutar desde la raíz del proyecto para aplicar la migración incremental `add_task_assignee_and_notifications`:

```bash
flask db upgrade
```

> **Garantía de Integridad**: Todas las tareas existentes de los Incrementos 1 a 3 adquieren automáticamente `assignee_id = NULL`, preservando intactos a los creadores originales (`user_id`), prioridades, categorías y logs de auditoría.

---

## 3. Ejecución de la Aplicación Monolítica

Iniciar el servidor de desarrollo monolítico:

```bash
flask run
# Servidor disponible en http://127.0.0.1:5000
```

---

## 4. Ejecución de Pruebas Automatizadas Bloqueantes (Principio IV)

Ejecutar la suite de pruebas que salvaguarda las reglas de negocio de colaboración:

```bash
# 1. Pruebas unitarias de dominio (asignación, atomicidad de notificaciones, persistencia de lectura)
pytest tests/unit/test_task_service.py tests/unit/test_notification_service.py -v

# 2. Pruebas de integración de rutas, contratos HTTP y protección CSRF
pytest tests/integration/test_collaboration_routes.py tests/integration/test_notification_routes.py -v

# 3. Cobertura global
pytest --cov=src/taskcontrol tests/
```

---

## 5. Escenarios de Validación End-to-End

### Escenario A: Asignación a Usuario Registrado vs. Correo Inexistente (HU-10)
1. **Registrar dos usuarios**: `creador@empresa.com` y `colaborador@empresa.com`.
2. **Crear tarea**: Como `creador@empresa.com`, crear una tarea "Revisar arquitectura".
3. **Intentar asignar a correo inexistente**:
   - En la acción de asignación de la tarea, ingresar `fantasma@noexiste.com`.
   - **Resultado esperado**: El backend rechaza la operación inmediatamente con el mensaje *"El correo especificado no pertenece a ningún usuario registrado en el sistema."*. La tarea permanece sin asignar.
4. **Asignar a usuario registrado**:
   - Ingresar `colaborador@empresa.com`.
   - **Resultado esperado**: La tarea se asigna exitosamente y se registra el evento `TASK_ASSIGNED` en `audit_logs`.

### Escenario B: Distinción Visual y Filtro de Procedencia en el Listado (HU-10)
1. **Iniciar sesión como `colaborador@empresa.com`**:
   - Ir a `/tasks`.
   - **Resultado esperado**: La tarea "Revisar arquitectura" aparece visible en el listado general con un badge destacado: `Asignada por: creador@empresa.com`.
2. **Crear una tarea propia**:
   - Como `colaborador@empresa.com`, crear la tarea "Mi informe diario".
   - **Resultado esperado**: Esta tarea aparece con el badge `Creada por mí`.
3. **Probar filtro de procedencia (`scope`)**:
   - Seleccionar filtro "Asignadas a mí": Solo se muestra "Revisar arquitectura".
   - Seleccionar filtro "Creadas por mí": Solo se muestra "Mi informe diario".
   - Seleccionar filtro "Todas": Se muestran ambas tareas, ordenadas correctamente por fecha o prioridad.

### Escenario C: Notificación Interna, Lectura Persistente e Historial (HU-11)
1. **Verificar contador en navbar**:
   - En la sesión de `colaborador@empresa.com`, observar el icono de notificaciones en la barra superior.
   - **Resultado esperado**: Aparece la campana con contador `(1)`.
2. **Consultar notificaciones**:
   - Hacer clic en la campana o ingresar a `/notifications`.
   - **Resultado esperado**: Se lista la notificación con el título de la tarea, mensaje indicando que `creador@empresa.com` la asignó, y fecha de recepción.
3. **Marcar como leída**:
   - Presionar "Marcar como leída".
   - **Resultado esperado**:
     - El contador del navbar decrece a `0`.
     - La notificación cambia visualmente a estado "leída".
     - **La notificación permanece visible en el historial** (no se borra).
4. **Auto-asignación**:
   - Como `colaborador@empresa.com`, asignarse una tarea propia a sí mismo.
   - **Resultado esperado**: La tarea se auto-asigna, pero el contador de notificaciones no aumenta (cero notificaciones espurias a uno mismo).
