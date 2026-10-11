from datetime import datetime, timezone

from ..extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    # Se incrementa al restablecer la contraseña: invalida todas las sesiones previas (clarify 002 Q3)
    session_version = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    tasks = db.relationship("Task", back_populates="owner", lazy="dynamic")
