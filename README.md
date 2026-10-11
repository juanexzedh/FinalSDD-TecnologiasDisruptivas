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
HU-01, 02, 03, 04, 12, 13 (incremento 001) y HU-05, 06, 14 (incremento 002).
NO implementadas: HU-07, 08, 09 (003), HU-10, 11 (004), HU-15, 16 (005).
