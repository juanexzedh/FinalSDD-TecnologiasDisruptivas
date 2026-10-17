from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ..services import category_service, task_service
from ..services.errors import (
    CategoryAccessDeniedError,
    InvalidPriorityError,
    InvalidTransitionError,
    NotFoundError,
    TaskAlreadyDeletedError,
    TaskDeletedError,
    ValidationError,
)
from .common import json_error, payload, wants_json
from .decorators import login_required

tasks_bp = Blueprint("tasks", __name__)

STATUS_LABELS = {"pending": "Pendiente", "in_progress": "En progreso", "completed": "Completada"}
PRIORITY_LABELS = {"high": "Alta", "medium": "Media", "low": "Baja"}


def _uid():
    return session["user_id"]


def _task_dict(t):
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "status": t.status,
        "priority": t.priority,
        "category": {"id": t.category.id, "name": t.category.name} if t.category else None,
        "is_overdue": t.is_overdue,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def _validation_response(e, template, status=400, **ctx):
    if wants_json():
        return json_error("VALIDATION_ERROR", str(e), 400, getattr(e, "errors", None))
    errors = getattr(e, "errors", {})
    if isinstance(errors, dict):
        for msgs in errors.values():
            for m in msgs:
                flash(m, "error")
    else:
        flash(str(e), "error")
    return render_template(template, **ctx), status


def _not_found():
    """JSON: 404 estructurado. Navegador: redirige a /tasks con mensaje (clarify 001 Q5);
    igual para tarea inexistente o ajena, para no revelar si existe."""
    if wants_json():
        return json_error("NOT_FOUND", "Tarea no encontrada.", 404)
    flash("Tarea no encontrada.", "error")
    return redirect(url_for("tasks.list_tasks"))


def _deleted(e, already=False):
    code = "TASK_ALREADY_DELETED" if already else "TASK_DELETED"
    if wants_json():
        return json_error(code, str(e), 400)
    flash(str(e), "error")
    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.get("/tasks")
@login_required
def list_tasks():
    flt = request.args.get("status", "all")
    category = request.args.get("category", request.args.get("category_id", "all"))
    sort = request.args.get("sort", request.args.get("sort_by", "created_at"))
    try:
        tasks = task_service.get_user_tasks(_uid(), status_filter=flt, category=category, sort=sort)
    except ValidationError as e:
        return _validation_response(
            e,
            "tasks/index.html",
            tasks=[],
            current_filter="all",
            current_category="all",
            current_sort="created_at",
            labels=STATUS_LABELS,
            priorities=PRIORITY_LABELS,
        )
    if wants_json():
        return jsonify(
            {
                "status": "success",
                "data": {
                    "tasks": [_task_dict(t) for t in tasks],
                    "filters": {"status": flt, "category": category, "sort": sort},
                    "filter": flt,
                    "total": len(tasks),
                },
            }
        )
    cats = category_service.get_user_categories(_uid())
    return render_template(
        "tasks/index.html",
        tasks=tasks,
        current_filter=flt,
        current_category=category,
        current_sort=sort,
        labels=STATUS_LABELS,
        priorities=PRIORITY_LABELS,
        categories=cats,
    )


@tasks_bp.get("/tasks/new")
@login_required
def new_task_form():
    cats = category_service.get_user_categories(_uid())
    return render_template("tasks/new.html", form={}, categories=cats)


@tasks_bp.post("/tasks")
@login_required
def create_task():
    d = payload()
    priority = d.get("priority", "medium")
    category_id = d.get("category_id")
    try:
        t = task_service.create_task(
            _uid(),
            d.get("title"),
            d.get("description"),
            d.get("due_date"),
            priority=priority,
            category_id=category_id,
        )
    except ValidationError as e:
        cats = category_service.get_user_categories(_uid())
        return _validation_response(e, "tasks/new.html", form=d, categories=cats)
    except (CategoryAccessDeniedError, NotFoundError) as e:
        if wants_json():
            return json_error("INVALID_CATEGORY", str(e), 400)
        flash(str(e), "error")
        cats = category_service.get_user_categories(_uid())
        return render_template("tasks/new.html", form=d, categories=cats), 400

    if wants_json():
        return jsonify({"status": "success", "message": "Tarea creada exitosamente", "data": _task_dict(t)}), 201
    flash("Tarea creada exitosamente.", "success")
    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.get("/tasks/<int:task_id>/edit")
@login_required
def edit_task_form(task_id):
    try:
        t = task_service.get_task(_uid(), task_id)
    except NotFoundError:
        return _not_found()
    cats = category_service.get_user_categories(_uid())
    if wants_json():
        return jsonify({"status": "success", "data": _task_dict(t)})
    return render_template("tasks/edit.html", task=t, form=_task_dict(t), categories=cats)


@tasks_bp.post("/tasks/<int:task_id>/edit")
@login_required
def edit_task(task_id):
    d = payload()
    priority = d.get("priority")
    category_id = d.get("category_id", "KEEP")
    try:
        t = task_service.update_task(
            _uid(),
            task_id,
            d.get("title"),
            d.get("description"),
            d.get("due_date"),
            priority=priority,
            category_id=category_id,
        )
    except NotFoundError:
        return _not_found()
    except TaskDeletedError as e:
        return _deleted(e)
    except CategoryAccessDeniedError as e:
        if wants_json():
            return json_error("INVALID_CATEGORY", str(e), 400)
        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks"))
    except ValidationError as e:
        task = None
        try:
            task = task_service.get_task(_uid(), task_id)
        except NotFoundError:
            pass
        cats = category_service.get_user_categories(_uid())
        return _validation_response(e, "tasks/edit.html", task=task, form=d, categories=cats)

    if wants_json():
        return jsonify({"status": "success", "message": "Tarea actualizada exitosamente", "data": _task_dict(t)})
    flash("Tarea actualizada exitosamente.", "success")
    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.post("/tasks/<int:task_id>/priority")
@login_required
def set_priority(task_id):
    d = payload()
    priority = d.get("priority")
    try:
        task = task_service.get_task(_uid(), task_id)
        old_priority = task.priority
        t = task_service.set_task_priority(_uid(), task_id, priority)
    except NotFoundError:
        return _not_found()
    except TaskDeletedError as e:
        return _deleted(e)
    except (InvalidPriorityError, ValidationError) as e:
        if wants_json():
            return json_error("INVALID_PRIORITY", str(e), 400)
        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks"))

    if wants_json():
        return jsonify(
            {
                "status": "success",
                "message": "Prioridad actualizada exitosamente",
                "data": {"id": t.id, "priority": t.priority, "previous_priority": old_priority},
            }
        )
    flash("Prioridad actualizada exitosamente.", "success")
    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.post("/tasks/<int:task_id>/category")
@login_required
def assign_category(task_id):
    d = payload()
    category_id = d.get("category_id")
    try:
        t = task_service.assign_task_category(_uid(), task_id, category_id)
    except NotFoundError:
        return _not_found()
    except TaskDeletedError as e:
        return _deleted(e)
    except CategoryAccessDeniedError as e:
        if wants_json():
            return json_error("INVALID_CATEGORY", str(e), 400)
        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks"))
    except ValidationError as e:
        if wants_json():
            return json_error("INVALID_CATEGORY", str(e), 400, getattr(e, "errors", None))
        flash(str(e), "error")
        return redirect(url_for("tasks.list_tasks"))

    if wants_json():
        return jsonify(
            {
                "status": "success",
                "message": "Categoría de la tarea actualizada exitosamente",
                "data": {
                    "task_id": t.id,
                    "category_id": t.category_id,
                    "category_name": t.category.name if t.category else None,
                },
            }
        )
    flash("Categoría de la tarea actualizada exitosamente.", "success")
    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.post("/tasks/<int:task_id>/status")
@login_required
def change_status(task_id):
    d = payload()
    new_status = d.get("status")
    try:
        t = task_service.change_task_status(_uid(), task_id, new_status)
    except NotFoundError:
        return _not_found()
    except TaskDeletedError as e:
        return _deleted(e)
    except InvalidTransitionError as e:
        if wants_json():
            return json_error("INVALID_STATE_TRANSITION", str(e), 400)
        return render_template("error.html", message=str(e)), 400  # contrato: 400
    except ValidationError as e:
        if wants_json():
            return json_error("VALIDATION_ERROR", str(e), 400, e.errors)
        return render_template("error.html", message=str(e)), 400
    if wants_json():
        return jsonify(
            {
                "status": "success",
                "message": "Estado de la tarea actualizado exitosamente",
                "data": {"id": t.id, "old_status": t.previous_status, "new_status": t.status},
            }
        )
    flash("Estado actualizado.", "success")
    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.post("/tasks/<int:task_id>/delete")
@login_required
def delete_task(task_id):
    try:
        t = task_service.delete_task(_uid(), task_id)
    except NotFoundError:
        return _not_found()
    except TaskAlreadyDeletedError as e:
        return _deleted(e, already=True)
    if wants_json():
        return jsonify(
            {
                "status": "success",
                "message": "Tarea eliminada",
                "data": {"id": t.id, "is_deleted": True, "deleted_at": t.deleted_at.isoformat()},
            }
        )
    flash("Tarea eliminada.", "success")
    return redirect(url_for("tasks.list_tasks"))


@tasks_bp.post("/tasks/<int:task_id>/reopen")
@login_required
def reopen_task(task_id):
    try:
        t = task_service.reopen_task(_uid(), task_id)
    except NotFoundError:
        return _not_found()
    except TaskDeletedError as e:
        return _deleted(e)
    except InvalidTransitionError as e:
        if wants_json():
            return json_error("INVALID_STATE_TRANSITION", str(e), 400)
        return render_template("error.html", message=str(e)), 400
    if wants_json():
        return jsonify(
            {
                "status": "success",
                "message": "Tarea reabierta",
                "data": {"id": t.id, "previous_status": "completed", "new_status": t.status},
            }
        )
    flash("Tarea reabierta.", "success")
    return redirect(url_for("tasks.list_tasks"))
