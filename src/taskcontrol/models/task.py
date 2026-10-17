from datetime import datetime, timezone

from ..extensions import db

TASK_STATUSES = ("pending", "in_progress", "completed")
ALLOWED_PRIORITIES = ("high", "medium", "low")
PRIORITY_WEIGHTS = {"high": 3, "medium": 2, "low": 1}


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

    # Prioridad (HU-07) y Categorías (HU-08)
    priority = db.Column(db.String(20), nullable=False, default="medium", server_default="medium")
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    category = db.relationship("Category", backref=db.backref("tasks", lazy="dynamic", passive_deletes=True))

    __table_args__ = (
        db.Index("ix_tasks_user_id_is_deleted", "user_id", "is_deleted"),
        db.Index("ix_tasks_user_id_priority", "user_id", "priority"),
        db.Index("ix_tasks_category_id", "category_id"),
    )

    owner = db.relationship("User", back_populates="tasks")

    @property
    def is_overdue(self) -> bool:
        if self.is_deleted or self.status == "completed" or self.due_date is None:
            return False
        return self.due_date < datetime.now(timezone.utc).date()

