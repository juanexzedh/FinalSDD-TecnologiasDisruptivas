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

from ..services import task_service
from ..services.errors import (
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


def _uid():
    return session["user_id"]


def _task_dict(t):
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "status": t.status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def _validation_response(e, template, status=400, **ctx):
    if wants_json():
        return json_error("VALIDATION_ERROR", str(e), 400, e.errors)
    for msgs in e.errors.values():
        for m in msgs:
            flash(m, "error")
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
    try:
        tasks = task_service.get_user_tasks(_uid(), flt)
    except ValidationError as e:
        return _validation_response(e, "tasks/index.html", tasks=[], current_filter="all", labels=STATUS_LABELS)
    if wants_json():
        return jsonify(
            {"status": "success", "data": {"tasks": [_task_dict(t) for t in tasks], "filter": flt, "total": len(tasks)}}
        )
    return render_template("tasks/index.html", tasks=tasks, current_filter=flt, labels=STATUS_LABELS)


@tasks_bp.get("/tasks/new")
@login_required
def new_task_form():
    return render_template("tasks/new.html", form={})


@tasks_bp.post("/tasks")
@login_required
def create_task():
    d = payload()
    try:
        t = task_service.create_task(_uid(), d.get("title"), d.get("description"), d.get("due_date"))
    except ValidationError as e:
        return _validation_response(e, "tasks/new.html", form=d)
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
    if wants_json():
        return jsonify({"status": "success", "data": _task_dict(t)})
    return render_template("tasks/edit.html", task=t, form=_task_dict(t))


@tasks_bp.post("/tasks/<int:task_id>/edit")
@login_required
def edit_task(task_id):
    d = payload()
    try:
        t = task_service.update_task(_uid(), task_id, d.get("title"), d.get("description"), d.get("due_date"))
    except NotFoundError:
        return _not_found()
    except TaskDeletedError as e:
        return _deleted(e)
    except ValidationError as e:
        task = None
        try:
            task = task_service.get_task(_uid(), task_id)
        except NotFoundError:
            pass
        return _validation_response(e, "tasks/edit.html", task=task, form=d)
    if wants_json():
        return jsonify({"status": "success", "message": "Tarea actualizada exitosamente", "data": _task_dict(t)})
    flash("Tarea actualizada exitosamente.", "success")
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
