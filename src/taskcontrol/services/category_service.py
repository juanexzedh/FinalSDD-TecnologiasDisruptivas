from ..extensions import db
from ..models import Category, Task
from . import audit_service
from .errors import (
    CategoryLimitExceededError,
    DuplicateCategoryNameError,
    NotFoundError,
    ValidationError,
)


def create_category(user_id: int, name: str) -> Category:
    name = (name or "").strip() if isinstance(name, str) or name is None else str(name).strip()
    if not name or len(name) > 50:
        raise ValidationError(
            {"name": ["El nombre de la categoría es obligatorio y debe contener entre 1 y 50 caracteres."]}
        )

    count = Category.query.filter_by(user_id=user_id).count()
    if count >= 50:
        raise CategoryLimitExceededError(
            "Ha alcanzado el límite máximo de 50 categorías permitidas por cuenta."
        )

    existing = Category.query.filter(
        Category.user_id == user_id,
        db.func.lower(Category.name) == db.func.lower(name),
    ).first()
    if existing:
        raise DuplicateCategoryNameError("Ya posee una categoría con el nombre especificado.")

    c = Category(user_id=user_id, name=name)
    db.session.add(c)
    db.session.flush()
    audit_service.record_category_event(user_id, "CATEGORY_CREATED", c.id, {"name": name})
    db.session.commit()
    return c


def get_user_categories(user_id: int):
    cats = (
        Category.query.filter_by(user_id=user_id)
        .order_by(Category.created_at.asc(), Category.id.asc())
        .all()
    )
    for c in cats:
        c.task_count = Task.query.filter_by(category_id=c.id, is_deleted=False).count()
    return cats


def get_category(user_id: int, category_id: int) -> Category:
    c = Category.query.filter_by(id=category_id, user_id=user_id).first()
    if not c:
        raise NotFoundError("La categoría solicitada no existe o no tiene permisos para acceder a ella.")
    return c


def update_category(user_id: int, category_id: int, new_name: str) -> Category:
    c = get_category(user_id, category_id)
    new_name = (
        (new_name or "").strip()
        if isinstance(new_name, str) or new_name is None
        else str(new_name).strip()
    )
    if not new_name or len(new_name) > 50:
        raise ValidationError(
            {"name": ["El nombre de la categoría es obligatorio y debe contener entre 1 y 50 caracteres."]}
        )

    existing = Category.query.filter(
        Category.user_id == user_id,
        Category.id != category_id,
        db.func.lower(Category.name) == db.func.lower(new_name),
    ).first()
    if existing:
        raise DuplicateCategoryNameError("Ya posee una categoría con el nombre especificado.")

    old_name = c.name
    c.name = new_name
    audit_service.record_category_event(
        user_id, "CATEGORY_UPDATED", c.id, {"old_name": old_name, "new_name": new_name}
    )
    db.session.commit()
    return c


def delete_category(user_id: int, category_id: int):
    c = get_category(user_id, category_id)
    cat_name = c.name

    # Desvinculación segura de tareas: ON DELETE SET NULL nativo o garantizado en ORM
    Task.query.filter_by(category_id=category_id).update(
        {"category_id": None}, synchronize_session="fetch"
    )

    db.session.delete(c)
    audit_service.record_category_event(
        user_id, "CATEGORY_DELETED", category_id, {"category_name": cat_name}
    )
    db.session.commit()
    return True
