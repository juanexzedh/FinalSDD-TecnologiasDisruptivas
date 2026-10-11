# Quickstart & Guía de Validación: TaskControl (Incremento 5)

**Feature**: `005-frontend-interaction`  
**Date**: 2026-10-08  
**Stack**: Python 3.11+, Flask 3.x, SQLAlchemy, Flask-Migrate, Flask-WTF (`CSRFProtect`), JavaScript Vanilla (ECMAScript nativo), pytest  

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

Ejecutar desde la raíz del proyecto para aplicar la migración incremental `add_task_position`:

```bash
flask db upgrade
```

> **Garantía de Integridad**: Todas las tareas existentes de los Incrementos 1 a 4 adquieren automáticamente `position = 0` (`server_default='0'`). Como el criterio secundario de ordenamiento es `created_at DESC`, las tareas existentes conservan intacto su orden cronológico habitual hasta que el usuario decida reordenarlas manualmente.

---

## 3. Ejecución de la Aplicación

Iniciar el servidor web monolítico:

```bash
flask run
# Acceder a http://127.0.0.1:5000 en el navegador
```

---

## 4. Pruebas Automatizadas Bloqueantes (Principio IV)

Ejecutar la suite de pruebas automatizadas del backend para el nuevo servicio de reordenamiento y contratos de estado:

```bash
# 1. Pruebas unitarias de dominio para el servicio de reordenamiento e integridad de propiedad
pytest tests/unit/test_task_service.py -k "reorder" -v

# 2. Pruebas de integración HTTP para los endpoints de reordenamiento y cambio de estado JSON
pytest tests/integration/test_task_routes.py -k "status or reorder" -v

# 3. Cobertura global
pytest --cov=src/taskcontrol tests/
```

> **Nota sobre Pruebas de Frontend (JavaScript)**: Conforme a la constitución del proyecto y el principio de simplicidad (Principio V), el repositorio no incluye runners de testing de navegador headless (como Playwright o Jest) para no introducir cadenas de dependencias de Node.js en un monolito de Python. Las pruebas de reversión visual y drag-and-drop en el cliente se validan mediante los escenarios manuales reproducibles descritos a continuación.

---

## 5. Escenarios de Validación End-to-End

### Escenario A: Completar Tarea sin Recargar y Reversión ante Fallo (HU-15)
1. **Completar con éxito**:
   - Iniciar sesión y acceder a `/tasks`.
   - Ubicar una tarea en estado "pendiente".
   - Hacer clic en la casilla o botón de completar.
   - **Resultado esperado**: La tarea cambia visualmente al estado completada (estilo tachado/badge verde) de manera inmediata y fluida, **sin recargar la página completa**. El badge de tarea vencida (si existía) desaparece.
2. **Validar persistencia**:
   - Presionar F5 en el navegador.
   - **Resultado esperado**: La tarea continúa figurando en estado completada.
3. **Simular fallo y validar Rollback Visual**:
   - Abrir las herramientas de desarrollo del navegador (F12) $\rightarrow$ pestaña *Network* y marcar el modo *Offline* (o apagar momentáneamente la conexión).
   - En `/tasks`, hacer clic en completar otra tarea pendiente.
   - **Resultado esperado**:
     - La interfaz aplica el cambio visual por un instante.
     - Al detectar el fallo de red, **revierte de inmediato el cambio visual** (la casilla se desmarca, se retira el estilo tachado).
     - Se despliega una alerta o toast prominente de error indicando que no se pudo guardar el cambio.
     - La pantalla **nunca** queda mostrando un estado que el servidor no confirmó.

### Escenario B: Reordenamiento mediante Arrastrar y Soltar (HU-16)
1. **Reordenar tarjetas**:
   - En `/tasks`, tomar con el ratón la tarjeta inferior del listado y arrastrarla hacia la primera posición.
   - Soltar la tarjeta en la nueva posición.
   - **Resultado esperado**: Las tarjetas se reacomodan fluidamente en el listado.
2. **Validar persistencia tras recarga**:
   - Presionar F5 en el navegador (o cerrar la sesión y volver a ingresar).
   - **Resultado esperado**: Las tareas se presentan exactamente en el nuevo orden personalizado guardado.
3. **Simular fallo de persistencia de orden**:
   - En modo *Offline*, arrastrar una tarjeta a otra posición y soltarla.
   - **Resultado esperado**: Al fallar la petición `fetch` hacia `/tasks/reorder`, las tarjetas vuelven automáticamente a sus posiciones originales en la pantalla (rollback del DOM) y se alerta al usuario.

### Escenario C: Aislamiento Concurrente entre Usuarios
1. Iniciar sesión con "Usuario A" en una ventana de incógnito y con "Usuario B" en una ventana normal.
2. Ambos usuarios reordenan sus respectivas tareas.
3. **Resultado esperado**: Cada usuario conserva su propio orden sin afectar en lo absoluto el orden ni las tareas del otro usuario.
