from flask import Blueprint, flash, jsonify, redirect, render_template, session, url_for

from ..services import category_service
from ..services.errors import (
    CategoryLimitExceededError,
    DuplicateCategoryNameError,
    NotFoundError,
    ValidationError,
)
from .common import json_error, payload, wants_json
from .decorators import login_required

categories_bp = Blueprint("categories", __name__)


def _uid():
    return session["user_id"]


@categories_bp.get("/categories")
@login_required
def list_categories():
    cats = category_service.get_user_categories(_uid())
    if wants_json():
        return jsonify(
            {
                "status": "success",
                "data": {
                    "categories": [
                        {
                            "id": c.id,
                            "name": c.name,
                            "task_count": getattr(c, "task_count", 0),
                            "created_at": c.created_at.isoformat() if c.created_at else None,
                        }
                        for c in cats
                    ],
                    "total": len(cats),
                },
            }
        )
    return render_template("categories/index.html", categories=cats)


@categories_bp.post("/categories")
@login_required
def create_category():
    d = payload()
    name = d.get("name")
    try:
        c = category_service.create_category(_uid(), name)
    except DuplicateCategoryNameError as e:
        if wants_json():
            return json_error("CATEGORY_ALREADY_EXISTS", str(e), 409)
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories"))
    except CategoryLimitExceededError as e:
        if wants_json():
            return json_error("CATEGORY_LIMIT_EXCEEDED", str(e), 400)
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories"))
    except ValidationError as e:
        if wants_json():
            return json_error("INVALID_CATEGORY_NAME", str(e), 400, e.errors)
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories"))

    if wants_json():
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Categoría creada exitosamente",
                    "data": {
                        "id": c.id,
                        "name": c.name,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                    },
                }
            ),
            201,
        )
    flash(f"Categoría '{c.name}' creada exitosamente.", "success")
    return redirect(url_for("categories.list_categories"))


@categories_bp.post("/categories/<int:category_id>/edit")
@login_required
def edit_category(category_id):
    d = payload()
    name = d.get("name")
    try:
        c = category_service.update_category(_uid(), category_id, name)
    except NotFoundError:
        if wants_json():
            return json_error(
                "CATEGORY_NOT_FOUND",
                "La categoría solicitada no existe o no tiene permisos para acceder a ella.",
                404,
            )
        flash("Categoría no encontrada.", "error")
        return redirect(url_for("categories.list_categories"))
    except DuplicateCategoryNameError as e:
        if wants_json():
            return json_error("CATEGORY_ALREADY_EXISTS", str(e), 409)
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories"))
    except ValidationError as e:
        if wants_json():
            return json_error("INVALID_CATEGORY_NAME", str(e), 400, e.errors)
        flash(str(e), "error")
        return redirect(url_for("categories.list_categories"))

    if wants_json():
        return jsonify(
            {
                "status": "success",
                "message": "Categoría renombrada exitosamente",
                "data": {"id": c.id, "name": c.name},
            }
        )
    flash("Categoría renombrada exitosamente.", "success")
    return redirect(url_for("categories.list_categories"))


@categories_bp.post("/categories/<int:category_id>/delete")
@login_required
def delete_category(category_id):
    try:
        category_service.delete_category(_uid(), category_id)
    except NotFoundError:
        if wants_json():
            return json_error(
                "CATEGORY_NOT_FOUND",
                "La categoría solicitada no existe o no tiene permisos para acceder a ella.",
                404,
            )
        flash("Categoría no encontrada.", "error")
        return redirect(url_for("categories.list_categories"))

    if wants_json():
        return jsonify(
            {
                "status": "success",
                "message": "Categoría eliminada exitosamente. Tareas desvinculadas.",
                "data": {"deleted_category_id": category_id},
            }
        )
    flash(
        "Categoría eliminada exitosamente. Las tareas asociadas fueron desvinculadas y preservadas intactas.",
        "success",
    )
    return redirect(url_for("categories.list_categories"))
