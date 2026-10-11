from flask import Blueprint, flash, jsonify, redirect, render_template, session, url_for

from ..services import auth_service
from ..services.errors import AuthenticationError, DuplicateEmailError, ValidationError
from .common import json_error, payload, wants_json
from .decorators import login_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    from flask import request

    if request.method == "GET":
        return render_template("auth/register.html")
    data = payload()
    try:
        auth_service.register_user(data.get("email"), data.get("password"))
    except ValidationError as e:
        if wants_json():
            return json_error("VALIDATION_ERROR", str(e), 400, e.errors)
        for msgs in e.errors.values():
            for m in msgs:
                flash(m, "error")
        return render_template("auth/register.html", email=data.get("email", "")), 400
    except DuplicateEmailError as e:
        if wants_json():
            return json_error("EMAIL_ALREADY_REGISTERED", str(e), 409)
        flash(str(e), "error")
        return render_template("auth/register.html", email=data.get("email", "")), 409
    if wants_json():
        return jsonify({"status": "success", "message": "Usuario registrado."}), 201
    flash("Registro exitoso. Inicia sesión.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    from flask import request

    if request.method == "GET":
        return render_template("auth/login.html")
    data = payload()
    try:
        user = auth_service.authenticate_user(data.get("email"), data.get("password"))
    except AuthenticationError as e:
        if wants_json():
            return json_error("INVALID_CREDENTIALS", str(e), 401)
        flash(str(e), "error")
        return render_template("auth/login.html", email=data.get("email", "")), 401
    session.clear()  # evita fijación de sesión
    session["user_id"] = user.id
    session["session_version"] = user.session_version
    if wants_json():
        return jsonify({"status": "success", "message": "Sesión iniciada."}), 200
    return redirect(url_for("tasks.list_tasks"))


@auth_bp.post("/logout")
@login_required
def logout():
    session.clear()
    if wants_json():
        return jsonify({"status": "success", "message": "Sesión cerrada."}), 200
    return redirect(url_for("auth.login"))
