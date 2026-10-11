from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    session,
    url_for,
)

from ..services import recovery_service
from ..services.errors import InvalidTokenError, ValidationError
from .common import json_error, payload, wants_json

recovery_bp = Blueprint("recovery", __name__)

NEUTRAL_MSG = "Si el correo electrónico se encuentra registrado, recibirás instrucciones para restablecer tu contraseña en breve."


@recovery_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    from flask import request

    if session.get("user_id"):
        return redirect(url_for("tasks.list_tasks"))
    if request.method == "GET":
        return render_template("auth/forgot_password.html")
    d = payload()
    try:
        recovery_service.request_password_reset(
            d.get("email"),
            current_app.extensions["email_sender"],
            lambda t: url_for("recovery.reset_password", token=t, _external=True),
        )
    except ValidationError as e:
        if wants_json():
            return json_error("VALIDATION_ERROR", str(e), 400, e.errors)
        for msgs in e.errors.values():
            for m in msgs:
                flash(m, "error")
        return render_template("auth/forgot_password.html", email=d.get("email", "")), 400
    # Respuesta ciega: idéntica exista o no el correo, y con o sin throttling
    if wants_json():
        return jsonify({"status": "success", "message": NEUTRAL_MSG}), 200
    flash(NEUTRAL_MSG, "success")
    return redirect(url_for("auth.login"))


@recovery_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    from flask import request

    def invalid():
        if wants_json():
            return json_error("INVALID_OR_EXPIRED_TOKEN", "Enlace inválido o expirado.", 400)
        flash("El enlace es inválido o ha expirado. Solicita uno nuevo.", "error")
        return redirect(url_for("recovery.forgot_password"))

    if request.method == "GET":
        if not recovery_service.is_token_valid(token):
            return invalid()
        return render_template("auth/reset_password.html", token=token)
    d = payload()
    try:
        recovery_service.reset_password(token, d.get("new_password"), d.get("confirm_password"))
    except InvalidTokenError:
        return invalid()
    except ValidationError as e:
        if wants_json():
            return json_error("VALIDATION_ERROR", str(e), 400, e.errors)
        for msgs in e.errors.values():
            for m in msgs:
                flash(m, "error")
        return render_template("auth/reset_password.html", token=token), 400
    if wants_json():
        return jsonify({"status": "success", "code": "PASSWORD_UPDATED", "message": "Contraseña actualizada."}), 200
    flash("Contraseña actualizada. Inicia sesión con la nueva.", "success")
    return redirect(url_for("auth.login"))
