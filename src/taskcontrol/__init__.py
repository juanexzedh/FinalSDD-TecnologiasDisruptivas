import logging
import os
from pathlib import Path

from flask import Flask, redirect, url_for

from .config import CONFIGS
from .extensions import csrf, db, migrate


def create_app(config_name=None):
    config_name = config_name or os.environ.get("APP_ENV", "development")
    root = Path(__file__).resolve().parents[2]  # raíz del proyecto
    app = Flask(__name__, instance_path=str(root / "instance"))
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.from_object(CONFIGS[config_name])

    if app.config["REQUIRE_SECRET_KEY"]:
        key = CONFIGS[config_name].secret_key()
        if not key:
            raise RuntimeError(
                "Falta SECRET_KEY. Copia .env.example a .env y define un valor."
            )
        app.config["SECRET_KEY"] = key

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from . import models  # noqa: F401  (registra tablas para Alembic)
    from .blueprints.auth import auth_bp
    from .blueprints.errors import register_error_handlers
    from .blueprints.recovery import recovery_bp
    from .services.email_sender import ConsoleEmailSender
    from .blueprints.tasks import tasks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(recovery_bp)
    app.extensions["email_sender"] = ConsoleEmailSender()
    register_error_handlers(app)

    for name in ("taskcontrol.audit", "taskcontrol.email"):
        lg = logging.getLogger(name)
        if not lg.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter("%(message)s"))
            lg.addHandler(h)
            lg.setLevel(logging.INFO)

    @app.get("/")
    def index():
        return redirect(url_for("tasks.list_tasks"))

    return app
