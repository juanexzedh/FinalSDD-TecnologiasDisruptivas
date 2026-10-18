# TaskControl — Incrementos 001 y 002

Implementación generada con Claude (chat), NO con `/speckit-implement`. Ver DECLARACION_IMPLEMENTACION.md.

## Levantar (PowerShell, desde la raíz, con el venv activo)
    copy .env.example .env          # y pon un valor en SECRET_KEY
    pip install -r requirements.txt
    flask db upgrade
    flask run                       # http://127.0.0.1:5000
    pytest -v

Generar clave: python -c "import secrets; print(secrets.token_hex(32))"
El enlace de "Recuperar contraseña" aparece en la consola donde corre `flask run` (ConsoleEmailSender).

## Historias cubiertas
HU-01 a 09, HU-12, HU-13 y HU-14 (incrementos 001, 002 y 003): 12 de 16.
NO implementadas: HU-10, 11 (004) y HU-15, 16 (005); tienen spec, clarify y plan.
Pruebas: 151 (pytest -v).