from datetime import date

from ..extensions import db
from ..models import ALLOWED_PRIORITIES, PRIORITY_WEIGHTS, TASK_STATUSES, Category, Task
from . import audit_service
from .errors import (
    CategoryAccessDeniedError,
    InvalidPriorityError,
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


def _clean_fields(title, description, due_date, priority="medium", category_id=None):
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

    if priority is None or priority == "":
        priority = "medium"
    if priority not in ALLOWED_PRIORITIES:
        raise InvalidPriorityError(
            "Valor de prioridad inválido. Los valores admitidos son: high, medium, low."
        )

    parsed_category_id = None
    if category_id not in (None, ""):
        try:
            parsed_category_id = int(category_id)
        except (ValueError, TypeError):
            errors["category_id"] = ["Identificador de categoría inválido."]

    if errors:
        raise ValidationError(errors)
    return title, description, parsed, priority, parsed_category_id


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


def create_task(user_id, title, description, due_date, priority="medium", category_id=None):
    title, description, parsed, priority, cat_id = _clean_fields(
        title, description, due_date, priority, category_id
    )
    if cat_id is not None:
        cat = Category.query.filter_by(id=cat_id, user_id=user_id).first()
        if not cat:
            raise CategoryAccessDeniedError("La categoría indicada no existe o no le pertenece.")

    task = Task(
        user_id=user_id,
        title=title,
        description=description,
        due_date=parsed,
        status="pending",
        priority=priority,
        category_id=cat_id,
    )
    db.session.add(task)
    db.session.flush()
    audit_service.record_task_event(user_id, "TASK_CREATED", task.id, {"title": title})
    db.session.commit()
    return task


def get_user_tasks(user_id, status_filter="all", category="all", sort="created_at", **kwargs):
    category_param = kwargs.get("category_id", category)
    sort_param = kwargs.get("sort_by", sort)
    status_param = kwargs.get("status", status_filter) or "all"

    if status_param != "all" and status_param not in TASK_STATUSES:
        raise ValidationError({"status": ["Filtro de estado inválido."]})

    q = Task.query.filter_by(user_id=user_id, is_deleted=False)
    if status_param != "all":
        q = q.filter_by(status=status_param)

    # Filtro por categoría acumulativo (AND)
    if str(category_param).lower() in ("uncategorized", "none"):
        q = q.filter(Task.category_id.is_(None))
    elif str(category_param) != "all" and category_param is not None:
        try:
            cat_id_int = int(category_param)
            q = q.filter(Task.category_id == cat_id_int)
        except (ValueError, TypeError):
            pass

    # Ordenamiento ortogonal
    if sort_param == "priority":
        priority_weight = db.case(
            PRIORITY_WEIGHTS,
            value=Task.priority,
            else_=0,
        )
        q = q.order_by(priority_weight.desc(), Task.created_at.desc(), Task.id.desc())
    else:
        q = q.order_by(Task.created_at.desc(), Task.id.desc())

    return q.all()


def update_task(user_id, task_id, title, description, due_date, priority=None, category_id="KEEP"):
    task = _active_task(user_id, task_id)
    p_to_check = task.priority if priority is None else priority
    c_to_check = task.category_id if category_id == "KEEP" else category_id
    title, description, parsed, new_priority, new_cat_id = _clean_fields(
        title, description, due_date, p_to_check, c_to_check
    )
    if category_id != "KEEP" and new_cat_id is not None:
        cat = Category.query.filter_by(id=new_cat_id, user_id=user_id).first()
        if not cat:
            raise CategoryAccessDeniedError("La categoría indicada no existe o no le pertenece.")

    old_priority = task.priority
    old_category_id = task.category_id

    changed = [
        f
        for f, old, new in (
            ("title", task.title, title),
            ("description", task.description, description),
            ("due_date", task.due_date, parsed),
        )
        if old != new
    ]
    if priority is not None and old_priority != new_priority:
        changed.append("priority")
    if category_id != "KEEP" and old_category_id != new_cat_id:
        changed.append("category_id")

    task.title, task.description, task.due_date = title, description, parsed
    if priority is not None:
        task.priority = new_priority
    if category_id != "KEEP":
        task.category_id = new_cat_id

    audit_details = {"changed_fields": changed}
    if priority is not None and old_priority != new_priority:
        audit_details["old_priority"] = old_priority
        audit_details["new_priority"] = new_priority

    audit_service.record_task_event(user_id, "TASK_UPDATED", task.id, audit_details)
    db.session.commit()
    return task


def set_task_priority(user_id, task_id, priority):
    task = _active_task(user_id, task_id)
    if priority not in ALLOWED_PRIORITIES:
        raise InvalidPriorityError(
            "Valor de prioridad inválido. Los valores admitidos son: high, medium, low."
        )
    old_priority = task.priority
    task.priority = priority
    audit_service.record_task_event(
        user_id, "TASK_UPDATED", task.id, {"old_priority": old_priority, "new_priority": priority}
    )
    db.session.commit()
    return task


def assign_task_category(user_id, task_id, category_id):
    task = _active_task(user_id, task_id)
    new_cat_id = None
    if category_id not in (None, ""):
        try:
            cid = int(category_id)
        except (ValueError, TypeError):
            raise ValidationError({"category_id": ["Identificador de categoría inválido."]})
        cat = Category.query.filter_by(id=cid, user_id=user_id).first()
        if not cat:
            raise CategoryAccessDeniedError("La categoría indicada no existe o no le pertenece.")
        new_cat_id = cat.id

    prev_cat_id = task.category_id
    task.category_id = new_cat_id
    audit_service.record_task_event(
        user_id,
        "TASK_CATEGORY_ASSIGNED",
        task.id,
        {"previous_category_id": prev_cat_id, "new_category_id": new_cat_id},
    )
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

