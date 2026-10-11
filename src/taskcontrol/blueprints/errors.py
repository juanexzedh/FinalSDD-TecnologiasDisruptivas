from flask import render_template
from flask_wtf.csrf import CSRFError

from .common import json_error, wants_json


def register_error_handlers(app):
    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        if wants_json():
            return json_error("CSRF_ERROR", "Token CSRF ausente o inválido.", 400)
        return render_template("error.html", message="Token CSRF ausente o inválido."), 400

    @app.errorhandler(404)
    def not_found(_e):
        if wants_json():
            return json_error("NOT_FOUND", "Recurso no encontrado.", 404)
        return render_template("error.html", message="Recurso no encontrado."), 404
