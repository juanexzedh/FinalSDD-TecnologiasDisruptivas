# Quickstart & Guía de Validación: TaskControl (Incremento 2)

**Feature**: `002-task-lifecycle-recovery`  
**Date**: 2026-10-07  
**Stack**: Python 3.11+, Flask 3.x, SQLAlchemy, Flask-Migrate, Flask-WTF (`CSRFProtect`), python-dotenv, pytest  

---

## 1. Prerrequisitos y Configuración Local

1. Asegurar que las dependencias del proyecto están instaladas:
   ```bash
   pip install -r requirements.txt
   ```
2. Verificar que el archivo local `.env` existe y contiene una `SECRET_KEY` válida generada:
   ```env
   FLASK_APP=src/taskcontrol:create_app
   FLASK_ENV=development
   FLASK_DEBUG=1
   SECRET_KEY=TU_CLAVE_ALEATORIA_GENERADA
   DATABASE_URL=sqlite:///taskcontrol.db
   ```

---

## 2. Aplicación de Migraciones de Base de Datos (Principio VI)

Ejecutar desde la raíz del proyecto para actualizar el esquema existente del Incremento 1 (agregando `is_deleted`, `deleted_at` e índices a `tasks`, y creando la tabla `password_reset_tokens`):

```bash
flask db upgrade
```
*(Todas las tareas previamente creadas conservan automáticamente `is_deleted=False` sin pérdida de datos).*

---

## 3. Ejecución de la Aplicación

Iniciar el servidor de desarrollo monolítico desde la raíz del proyecto:

```bash
flask run
# Servidor disponible en http://127.0.0.1:5000
```

---

## 4. Ejecución de Pruebas Automatizadas Bloqueantes (Principio IV)

Ejecutar las pruebas unitarias y de integración que verifican las reglas de dominio obligatorias:

```bash
# 1. Pruebas unitarias de dominio (soft delete, reapertura y tokens de reset)
pytest tests/unit/ -v

# 2. Pruebas de integración de rutas y contratos (eliminación, reapertura, flujos HTTP de recuperación)
pytest tests/integration/ -v

# 3. Cobertura global
pytest --cov=src/taskcontrol tests/
```

---

## 5. Escenarios de Validación Extremo a Extremo (Manual / Navegador)

### Escenario 1: Eliminación Lógica de Tareas (HU-05)
1. Iniciar sesión con un usuario y crear una tarea con título `"Tarea para eliminar"`.
2. En el listado `/tasks`, hacer clic en el botón "Eliminar" (o enviar POST a `/tasks/<id>/delete` con CSRF).
3. **Resultado esperado**:
   - Redirección a `/tasks` con mensaje flash informativo `"Tarea eliminada exitosamente."`.
   - La tarea ya no aparece en el listado visible de tareas del usuario.
   - En la base de datos, la fila permanece con `is_deleted = 1` y `deleted_at` poblado (soft delete).
   - En la tabla `audit_logs`, se registró el evento con `action = 'TASK_DELETED'`.
4. Intentar enviar una segunda solicitud de eliminación para la misma tarea:
   - **Resultado esperado**: Rechazo inmediato con código `400 Bad Request` indicando que la tarea ya está eliminada.

### Escenario 2: Reapertura de Tarea Completada (HU-06)
1. Crear una tarea `"Tarea a completar"`, cambiar su estado a `"en progreso"` y luego a `"completada"`.
2. Intentar cambiar su estado a `"pendiente"` mediante el selector ordinario de estado:
   - **Resultado esperado**: Bloqueado con error (la máquina de estados rechaza transición ordinaria desde completada).
3. En la tarjeta de la tarea completada, hacer clic en "Reabrir Tarea" (envía POST a `/tasks/<id>/reopen` con token CSRF).
4. **Resultado esperado**:
   - Redirección a `/tasks` con mensaje `"Tarea reabierta exitosamente."`.
   - La tarea vuelve a mostrarse en estado `"pendiente"`.
   - En `audit_logs`, se registra un evento con `action = 'TASK_REOPENED'` y detalles `{"previous_status": "completed", "new_status": "pending"}`, claramente distinguible de `TASK_CREATED` y `TASK_STATUS_CHANGED`.

### Escenario 3: Recuperación de Contraseña con Respuesta Ciega (Blind Response) (HU-14)
1. Cerrar sesión y navegar a `http://127.0.0.1:5000/forgot-password`.
2. Introducir un correo inexistente `noexiste@ejemplo.com` y enviar el formulario.
   - **Resultado esperado**: Redirección a `/login` con mensaje `"Si el correo electrónico se encuentra registrado en el sistema, recibirás instrucciones para restablecer tu contraseña en breve."` (cero filtración sobre existencia de la cuenta).
3. Enviar nuevamente la solicitud con el correo registrado de un usuario `usuario@ejemplo.com`.
   - **Resultado esperado**: El navegador muestra **exactamente el mismo mensaje neutro**.
   - En la consola donde se ejecuta `flask run`, el servicio `ConsoleEmailSender` imprime:
     ```text
     [EMAIL SIMULADO] Para: usuario@ejemplo.com
     Asunto: Restablecimiento de contraseña - TaskControl
     Enlace: http://127.0.0.1:5000/reset-password/<token_generado>
     ```

### Escenario 4: Restablecimiento de Contraseña e Invalidación de Token (HU-14)
1. Copiar el enlace impreso en consola y acceder en el navegador (`http://127.0.0.1:5000/reset-password/<token_generado>`).
2. Se muestra la pantalla de cambio de contraseña.
3. Ingresar nueva contraseña `NuevaClaveSegura2026` y confirmarla.
4. **Resultado esperado**:
   - Redirección a `/login` con confirmación de cambio exitoso.
   - En `audit_logs`, se registra `PASSWORD_RESET_COMPLETED`.
   - En `password_reset_tokens`, el registro tiene `used_at` poblado con la hora actual.
   - En `users`, `session_version` se incrementó en 1. Cualquier sesión activa previa en otro navegador/dispositivo queda inmediatamente revocada al intentar interactuar con el sistema.
   - Iniciar sesión con `usuario@ejemplo.com` y `NuevaClaveSegura2026` funciona correctamente; la contraseña anterior ya no es válida.
5. Intentar acceder nuevamente al mismo enlace de restablecimiento ya consumido:
   - **Resultado esperado**: Redirección inmediata a `/forgot-password` con mensaje de error informando que el enlace es inválido o ha expirado.

### Escenario 5: Silent Throttling y Solicitudes Múltiples (HU-14)
1. Enviar una solicitud de recuperación a `/forgot-password` para `usuario@ejemplo.com`.
2. Enviar inmediatamente una segunda solicitud para el mismo correo:
   - **Resultado esperado**: Ambas responden con el mensaje neutro. El primer token generado queda invalidado en BD y solo el segundo enlace impreso en consola es válido.
3. Enviar 2 solicitudes más en menos de 15 minutos (totalizando 4 solicitudes para la misma cuenta):
   - **Resultado esperado**: La 4ta solicitud devuelve el mensaje neutro idéntico ("Si el correo electrónico se encuentra registrado..."), pero en el backend no se genera ningún nuevo registro en `password_reset_tokens` ni se despacha correo a consola (silent throttling activo protegiendo al usuario).
