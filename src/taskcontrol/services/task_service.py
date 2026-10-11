from datetime import date

from ..extensions import db
from ..models import TASK_STATUSES, Task
from . import audit_service
from .errors import (
    InvalidTransitionError,
    NotFoundError,
    TaskAlreadyDeletedError,
    TaskDeletedError,
    ValidationError,
)
from .timeutil import utcnow

# Máquina de estados del Incremento 1. "completed" queda bloqueado (reapertura = HU-06).
ALLOWED_TRANSITIONS = {
    "pending": {"in_progress", "completed"},
    "in_progress": {"pending", "completed"},
    "completed": set(),
}


def _clean_fields(title, description, due_date):
    errors = {}
    title = (title or "").strip() if isinstance(title, str) or title is None else str(title).strip()
    if not title:
        errors["title"] = ["El título es obligatorio."]
    elif len(title) > 200:
        errors["title"] = ["El título no puede superar 200 caracteres."]

    if description is not None and not isinstance(description, str):
        description = str(description)
    if description is not None:
        description = description.strip() or None
    if description and len(description) > 2000:
        errors["description"] = ["La descripción no puede superar 2000 caracteres."]

    parsed = None
    if due_date not in (None, ""):
        try:
            parsed = date.fromisoformat(str(due_date))
        except ValueError:
            errors["due_date"] = ["Fecha inválida. Use el formato AAAA-MM-DD."]
    if errors:
        raise ValidationError(errors)
    return title, description, parsed


def _owned_task(user_id, task_id):
    task = db.session.get(Task, task_id)
    if task is None or task.user_id != user_id:
        raise NotFoundError("Tarea no encontrada.")  # misma respuesta: no filtra existencia
    return task


def _active_task(user_id, task_id):
    """Tarea propia y no eliminada; si está eliminada, mutarla se rechaza (HU-04/HU-05)."""
    task = _owned_task(user_id, task_id)
    if task.is_deleted:
        raise TaskDeletedError("No se permite modificar una tarea eliminada.")
    return task


def get_task(user_id, task_id):
    task = _owned_task(user_id, task_id)
    if task.is_deleted:
        raise NotFoundError("Tarea no encontrada.")  # las eliminadas son invisibles para el usuario
    return task


def create_task(user_id, title, description, due_date):
    title, description, parsed = _clean_fields(title, description, due_date)
    task = Task(user_id=user_id, title=title, description=description, due_date=parsed, status="pending")
    db.session.add(task)
    db.session.flush()
    audit_service.record_task_event(user_id, "TASK_CREATED", task.id, {"title": title})
    db.session.commit()
    return task


def get_user_tasks(user_id, status_filter="all"):
    status_filter = status_filter or "all"
    if status_filter != "all" and status_filter not in TASK_STATUSES:
        raise ValidationError({"status": ["Filtro de estado inválido."]})
    q = Task.query.filter_by(user_id=user_id, is_deleted=False)
    if status_filter != "all":
        q = q.filter_by(status=status_filter)
    return q.order_by(Task.created_at.desc(), Task.id.desc()).all()


def update_task(user_id, task_id, title, description, due_date):
    task = _active_task(user_id, task_id)
    title, description, parsed = _clean_fields(title, description, due_date)
    changed = [
        f
        for f, old, new in (
            ("title", task.title, title),
            ("description", task.description, description),
            ("due_date", task.due_date, parsed),
        )
        if old != new
    ]
    task.title, task.description, task.due_date = title, description, parsed
    audit_service.record_task_event(user_id, "TASK_UPDATED", task.id, {"changed_fields": changed})
    db.session.commit()
    return task


def change_task_status(user_id, task_id, new_status):
    task = _active_task(user_id, task_id)
    if new_status not in TASK_STATUSES:
        raise ValidationError({"status": ["Estado inválido."]})
    old = task.status
    if old == "completed":
        raise InvalidTransitionError(
            "No se permite cambiar el estado de una tarea completada en este incremento."
        )
    if new_status == old:
        raise InvalidTransitionError("La tarea ya está en ese estado.")
    if new_status not in ALLOWED_TRANSITIONS[old]:
        raise InvalidTransitionError(f"Transición no permitida: {old} -> {new_status}.")
    task.status = new_status
    audit_service.record_task_event(
        user_id, "TASK_STATUS_CHANGED", task.id, {"old_status": old, "new_status": new_status}
    )
    db.session.commit()
    task.previous_status = old  # atributo transitorio para que la ruta lo informe en la respuesta
    return task


def delete_task(user_id, task_id):
    """HU-05: eliminación lógica e irreversible para el usuario (clarify 002 Q1)."""
    task = _owned_task(user_id, task_id)
    if task.is_deleted:
        raise TaskAlreadyDeletedError("La tarea ya fue eliminada.")
    task.is_deleted = True
    task.deleted_at = utcnow()
    audit_service.record_task_event(user_id, "TASK_DELETED", task.id, {"title": task.title})
    db.session.commit()
    return task


def reopen_task(user_id, task_id):
    """HU-06: completed -> pending, auditado como TASK_REOPENED (clarify 002 Q2)."""
    task = _active_task(user_id, task_id)
    if task.status != "completed":
        raise InvalidTransitionError("Solo se puede reabrir una tarea completada.")
    task.status = "pending"
    audit_service.record_task_event(
        user_id, "TASK_REOPENED", task.id, {"previous_status": "completed", "new_status": "pending"}
    )
    db.session.commit()
    return task
