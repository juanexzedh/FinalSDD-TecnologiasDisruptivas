from flask import jsonify, request


def wants_json():
    """Negociación de contenido: JSON si el cliente envía JSON o pide application/json."""
    if request.is_json:
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


def payload():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form


def json_error(code, message, status, errors=None):
    body = {"status": "error", "code": code, "message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status
