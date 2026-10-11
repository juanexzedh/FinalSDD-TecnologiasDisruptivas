# Contratos HTTP: Autenticación y Cuentas (HU-12, HU-13)

**Feature**: `001-core-task-auth`  
**Date**: 2026-10-06  
**Principio Constitucional**: III (Contrato explícito previo a la implementación) y VII (Seguridad por defecto)  

---

## 0. Política Global de Protección CSRF (Principio VII)

En cumplimiento del Principio VII (Seguridad por defecto), **todas las peticiones mutantes con método POST** (`/register`, `/login`, `/logout`) requieren obligatoriamente un token CSRF válido gestionado mediante el patrón Synchronizer Token (`Flask-WTF` `CSRFProtect`):
- **Formularios HTML (`application/x-www-form-urlencoded`)**: El formulario debe incluir el campo oculto `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- **Peticiones Asíncronas / JSON (`application/json`)**: La petición debe incluir el encabezado HTTP `X-CSRFToken: <token>` (obtenido de `<meta name="csrf-token" content="{{ csrf_token() }}">`) o el campo `"csrf_token"` en el payload JSON.
- **Respuesta ante fallo de CSRF (`400 Bad Request`)**:
  - En solicitudes API/JSON o asíncronas:
    ```json
    {
      "status": "error",
      "code": "CSRF_ERROR",
      "message": "Token CSRF ausente o inválido."
    }
    ```
  - En envíos directos de navegador: Respuesta HTTP 400 con mensaje indicando expiración o invalidez de la sesión del formulario.

---

## 1. Registro de Usuario (`HU-12`)

### 1.1 `GET /register`
- **Descripción**: Muestra la interfaz con el formulario de registro de nuevos usuarios.
- **Autenticación requerida**: No. Si ya existe sesión activa, redirige (302) a `/tasks`.
- **Códigos de Respuesta**:
  - `200 OK`: Renderiza plantilla `auth/register.html` conteniendo el campo oculto con `csrf_token()`.

### 1.2 `POST /register`
- **Descripción**: Procesa la creación de una nueva cuenta de usuario.
- **Autenticación requerida**: No.
- **Protección CSRF**: Requerida (`csrf_token` en formulario o `X-CSRFToken` en cabecera HTTP).
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "email": "usuario@ejemplo.com",
    "password": "Password123",
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
- **Validaciones en Backend**:
  - `csrf_token`: Obligatorio y válido contra la sesión actual.
  - `email`: Obligatorio, formato válido de correo, normalizado con trim y minúsculas.
  - `password`: Obligatorio, longitud mínima de 8 caracteres, al menos 1 letra y al menos 1 número.
- **Respuestas**:
  - `302 Found` (Navegador): Redirección a `/login` con mensaje flash informativo `"Cuenta creada exitosamente. Por favor, inicia sesión."`.
  - `201 Created` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Usuario registrado exitosamente",
      "data": {
        "id": 1,
        "email": "usuario@ejemplo.com"
      }
    }
    ```
  - `400 Bad Request` (Error de validación de campos):
    ```json
    {
      "status": "error",
      "code": "VALIDATION_ERROR",
      "message": "La contraseña debe tener al menos 8 caracteres y contener al menos una letra y un número.",
      "errors": {
        "password": ["Debe contener al menos 8 caracteres, una letra y un número."]
      }
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
  - `409 Conflict`:
    ```json
    {
      "status": "error",
      "code": "EMAIL_ALREADY_REGISTERED",
      "message": "El correo electrónico ya se encuentra registrado."
    }
    ```

---

## 2. Inicio y Cierre de Sesión (`HU-13`)

### 2.1 `GET /login`
- **Descripción**: Muestra la interfaz del formulario de inicio de sesión.
- **Autenticación requerida**: No. Si ya existe sesión activa, redirige (302) a `/tasks`.
- **Códigos de Respuesta**:
  - `200 OK`: Renderiza plantilla `auth/login.html` conteniendo el campo oculto con `csrf_token()`.

### 2.2 `POST /login`
- **Descripción**: Valida credenciales e inicializa la sesión de usuario activa.
- **Autenticación requerida**: No.
- **Protección CSRF**: Requerida (`csrf_token` en formulario o `X-CSRFToken` en cabecera HTTP).
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "email": "usuario@ejemplo.com",
    "password": "Password123",
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
- **Respuestas**:
  - `302 Found` (Navegador): Establece cookie de sesión firmada `session['user_id'] = user.id` y redirige a `/tasks`.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Sesión iniciada exitosamente",
      "data": {
        "id": 1,
        "email": "usuario@ejemplo.com"
      }
    }
    ```
  - `400 Bad Request` (Campos ausentes):
    ```json
    {
      "status": "error",
      "code": "MISSING_FIELDS",
      "message": "Correo y contraseña son requeridos."
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
  - `401 Unauthorized`:
    ```json
    {
      "status": "error",
      "code": "INVALID_CREDENTIALS",
      "message": "Correo o contraseña incorrectos."
    }
    ```

### 2.3 `POST /logout`
- **Descripción**: Finaliza y destruye la sesión activa en el servidor. Se realiza vía POST para proteger contra ataques CSRF de desautenticación forzada.
- **Autenticación requerida**: Sí (`@login_required`). Si no está autenticado, responde 302 a `/login`.
- **Protección CSRF**: Requerida (`csrf_token` en formulario o `X-CSRFToken` en cabecera HTTP).
- **Payload de Entrada** (`application/x-www-form-urlencoded` o `application/json`):
  ```json
  {
    "csrf_token": "IjE2...<token_csrf_valido>"
  }
  ```
  *(Nota: En peticiones JSON o fetch, puede omitirse el cuerpo si se envía la cabecera `X-CSRFToken`).*
- **Respuestas**:
  - `302 Found` (Navegador): Elimina los datos de sesión (`session.clear()`) y redirige a `/login` con mensaje flash.
  - `200 OK` (API/JSON):
    ```json
    {
      "status": "success",
      "message": "Sesión finalizada exitosamente"
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
