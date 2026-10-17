import json
import pytest

from taskcontrol.services.errors import ValidationError


def test_create_category_success(app, user):
    from taskcontrol.models import AuditLog
    from taskcontrol.services import category_service as cs

    c = cs.create_category(user.id, "  Trabajo  ")
    assert c.name == "Trabajo"
    assert c.user_id == user.id
    log = AuditLog.query.filter_by(action="CATEGORY_CREATED", entity_id=c.id).first()
    assert log is not None
    assert log.entity_type == "Category"
    assert log.actor_id == user.id


def test_category_name_unique_per_user_case_insensitive(app, user, other_user):
    from taskcontrol.services import category_service as cs
    from taskcontrol.services.errors import DuplicateCategoryNameError

    cs.create_category(user.id, "Trabajo")
    with pytest.raises((DuplicateCategoryNameError, ValidationError)):
        cs.create_category(user.id, "trabajo")
    with pytest.raises((DuplicateCategoryNameError, ValidationError)):
        cs.create_category(user.id, "  TRABAJO  ")

    # Mismo nombre permitido para otro usuario
    c2 = cs.create_category(other_user.id, "Trabajo")
    assert c2.name == "Trabajo"
    assert c2.user_id == other_user.id


def test_cannot_create_more_than_50_categories_per_user(app, user):
    from taskcontrol.services import category_service as cs
    from taskcontrol.services.errors import CategoryLimitExceededError

    for i in range(50):
        cs.create_category(user.id, f"Cat {i}")
    with pytest.raises((CategoryLimitExceededError, ValidationError)):
        cs.create_category(user.id, "Cat 51")


def test_get_user_categories_isolation(app, user, other_user):
    from taskcontrol.services import category_service as cs
    from taskcontrol.services import task_service as ts

    c1 = cs.create_category(user.id, "Cat A")
    c2 = cs.create_category(user.id, "Cat B")
    cs.create_category(other_user.id, "Other Cat")

    ts.create_task(user.id, "T1", None, None, category_id=c1.id)
    ts.create_task(user.id, "T2", None, None, category_id=c1.id)

    cats = cs.get_user_categories(user.id)
    assert len(cats) == 2
    names = [c["name"] if isinstance(c, dict) else c.name for c in cats]
    assert "Cat A" in names and "Cat B" in names and "Other Cat" not in names


def test_rename_category_preserves_task_links_and_records_audit(app, user):
    from taskcontrol.models import AuditLog, Task
    from taskcontrol.services import category_service as cs
    from taskcontrol.services import task_service as ts

    c = cs.create_category(user.id, "Antiguo")
    t1 = ts.create_task(user.id, "T1", None, None, category_id=c.id)

    updated = cs.update_category(user.id, c.id, "Nuevo")
    assert updated.name == "Nuevo"

    db_task = Task.query.get(t1.id)
    assert db_task.category_id == c.id

    log = AuditLog.query.filter_by(action="CATEGORY_UPDATED", entity_id=c.id).first()
    assert log is not None
    d = json.loads(log.details)
    assert d.get("old_name") == "Antiguo" and d.get("new_name") == "Nuevo"


def test_delete_category_unlinks_tasks_setting_category_id_to_null(app, user):
    from taskcontrol.models import AuditLog, Category, Task
    from taskcontrol.services import category_service as cs
    from taskcontrol.services import task_service as ts

    c = cs.create_category(user.id, "Por borrar")
    t1 = ts.create_task(user.id, "T1", None, None, category_id=c.id)
    t2 = ts.create_task(user.id, "T2", None, None, category_id=c.id)
    t3 = ts.create_task(user.id, "T3", None, None, category_id=c.id)

    cs.delete_category(user.id, c.id)

    assert Category.query.get(c.id) is None
    assert Task.query.filter_by(user_id=user.id).count() == 3
    tasks = Task.query.filter_by(user_id=user.id).all()
    for t in tasks:
        assert t.is_deleted is False
        assert t.category_id is None

    log = AuditLog.query.filter_by(action="CATEGORY_DELETED", entity_id=c.id).first()
    assert log is not None


def test_category_name_validation(app, user):
    from taskcontrol.services import category_service as cs

    with pytest.raises(ValidationError):
        cs.create_category(user.id, "")
    with pytest.raises(ValidationError):
        cs.create_category(user.id, "   ")
    with pytest.raises(ValidationError):
        cs.create_category(user.id, "x" * 51)
