from functools import wraps

from flask import redirect, request, session, url_for

from ..services import auth_service
from .common import json_error, wants_json


def login_required(view):
    """Verificación de sesión en el backend (Principio VII). Además compara la versión de
    sesión: si el usuario restableció su contraseña, las sesiones anteriores dejan de valer."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        uid = session.get("user_id")
        if uid:
            user = auth_service.get_user(uid)
            if user is None or session.get("session_version") != user.session_version:
                session.clear()
                uid = None
        if not uid:
            if wants_json():
                return json_error("UNAUTHORIZED", "Se requiere autenticación activa.", 401)
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped
