from datetime import datetime, timezone

from ..extensions import db

TASK_STATUSES = ("pending", "in_progress", "completed")


def _now():
    return datetime.now(timezone.utc)


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    # Eliminación lógica (HU-05): nunca borrado físico, para conservar la auditoría
    is_deleted = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (db.Index("ix_tasks_user_id_is_deleted", "user_id", "is_deleted"),)

    owner = db.relationship("User", back_populates="tasks")
