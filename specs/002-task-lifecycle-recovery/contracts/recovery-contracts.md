# Contratos HTTP: Recuperación de Contraseña (HU-14)

**Feature**: `002-task-lifecycle-recovery`  
**Date**: 2026-10-07  
**Principio Constitucional**: III (Contrato explícito previo a la implementación) y VII (Seguridad por defecto)  

---

## 0. Política Global de Privacidad y Mitigación de Enumeración (Blind Response)

Para prevenir la filtración de información sobre qué correos electrónicos se encuentran registrados en el sistema (ataques de enumeración de cuentas), el endpoint `POST /forgot-password` devuelve **exactamente la misma respuesta HTTP, mensaje y tiempo de procesamiento**, tanto si el correo existe en la base de datos como si no existe.

---

## 1. Solicitud de Restablecimiento de Contraseña

### 1.1 `GET /forgot-password`
- **Descripción**: Muestra la interfaz con el formulario para solicitar la recuperación de contraseña.
- **Autenticación requerida**: No. Si existe sesión activa, redirige (302) a `/tasks`.
- **Códigos de Respuesta**:
  - `200 OK`: Renderiza plantilla `auth/forgot_password.html` conteniendo el campo oculto con `csrf_token()`.

### 1.2 `POST /forgot-password`
- **Descripción**: Procesa la solicitud de recuperación. Si el correo existe: valida el límite de tasa móvil (máximo 3 solicitudes por correo cada 15 minutos; si se supera, aplica estrangulamiento silencioso retornando la confirmación neutra sin generar token ni despachar correo); si está dentro del límite, invalida cualquier token pendiente previo emitido para esa cuenta, genera un nuevo token criptográfico de un solo uso (15 min de vigencia), persiste su hash SHA-256 y emite el enlace al despachador de correo (`ConsoleEmailSender` en desarrollo). Si el correo no existe, ejecuta una operación dummy de tiempo equivalente. En todos los casos devuelve la misma respuesta neutra.
- **Autenticación requerida**: No.
- **Protección CSRF**: Requerida (`csrf_token` en formulario o `X-CSRFToken` en cabecera HTTP).
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "email": "usuario@ejemplo.com",
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
- **Validaciones en Backend**:
  - `csrf_token`: Obligatorio y válido contra la sesión del cliente.
  - `email`: Formato de correo sintácticamente válido (normalizado a minúsculas y sin espacios en extremos).
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/login` con mensaje flash genérico:
    `"Si el correo electrónico se encuentra registrado en el sistema, recibirás instrucciones para restablecer tu contraseña en breve."`
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Si el correo electrónico se encuentra registrado en el sistema, recibirás instrucciones para restablecer tu contraseña en breve."
    }
    ```
  - `400 Bad Request` (Formato de correo inválido o campo vacío):
    ```json
    {
      "status": "error",
      "code": "VALIDATION_ERROR",
      "message": "Por favor, introduce una dirección de correo electrónico válida."
    }
    ```
  - `400 Bad Request` (Fallo de protección CSRF):
    ```json
    {
      "status": "error",
      "code": "CSRF_ERROR",
      "message": "Token CSRF ausente o inválido."
    }
    ```

---

## 2. Confirmación y Cambio de Contraseña con Token

### 2.1 `GET /reset-password/<token>`
- **Descripción**: Verifica la validez del token en la URL y muestra el formulario para ingresar la nueva contraseña.
- **Autenticación requerida**: No.
- **Validación del Token**:
  - Se calcula el `SHA-256` del `<token>` proporcionado en la ruta.
  - Se busca en `password_reset_tokens` donde `token_hash == SHA-256(token)`.
  - Debe cumplirse `used_at IS NULL` y `expires_at > utcnow()`.
- **Respuestas**:
  - `200 OK`: Renderiza plantilla `auth/reset_password.html` con el formulario de nueva contraseña y `csrf_token()`.
  - `302 Found` (Navegador ante token inválido, expirado o usado): Redirección a `/forgot-password` con mensaje flash de error: `"El enlace de restablecimiento es inválido o ha expirado. Por favor, solicita uno nuevo."`
  - `400 Bad Request` (API/JSON ante token inválido/expirado):
    ```json
    {
      "status": "error",
      "code": "INVALID_OR_EXPIRED_TOKEN",
      "message": "El enlace de restablecimiento es inválido o ha expirado."
    }
    ```

### 2.2 `POST /reset-password/<token>`
- **Descripción**: Procesa el cambio de credencial, valida la política de contraseña, actualiza el hash de usuario (`scrypt`), revoca e invalida de forma global e inmediata todas las sesiones activas previas del usuario en cualquier navegador/dispositivo incrementando `session_version`, invalida irreversiblemente el token marcando `used_at` y registra auditoría.
- **Autenticación requerida**: No.
- **Protección CSRF**: Requerida.
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "new_password": "NuevoPassword123",
    "confirm_password": "NuevoPassword123",
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
- **Validaciones en Backend**:
  - `csrf_token`: Obligatorio y válido.
  - Token: Válido, no expirado (`expires_at > utcnow()`) y no utilizado (`used_at IS NULL`).
  - `new_password` y `confirm_password` deben coincidir exactamente.
  - Complejidad: Mínimo 8 caracteres, al menos 1 letra y al menos 1 número (misma regla de HU-12).
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/login` con mensaje flash `"Contraseña actualizada exitosamente. Por favor, inicia sesión con tu nueva contraseña."`
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Contraseña actualizada exitosamente"
    }
    ```
  - `400 Bad Request` (Contraseñas no coinciden o no cumplen complejidad):
    ```json
    {
      "status": "error",
      "code": "VALIDATION_ERROR",
      "message": "La nueva contraseña debe tener al menos 8 caracteres y contener al menos una letra y un número.",
      "errors": {
        "password": ["Debe contener al menos 8 caracteres, una letra y un número."]
      }
    }
    ```
  - `400 Bad Request` (Token inválido, reutilizado o expirado):
    ```json
    {
      "status": "error",
      "code": "INVALID_OR_EXPIRED_TOKEN",
      "message": "El token de recuperación no es válido o ha expirado."
    }
    ```
  - `400 Bad Request` (Fallo de protección CSRF):
    ```json
    {
      "status": "error",
      "code": "CSRF_ERROR",
      "message": "Token CSRF ausente o inválido."
    }
    ```
