import json
import logging
from datetime import date

import pytest

from taskcontrol.models import AuditLog
from taskcontrol.services import task_service as ts
from taskcontrol.services.errors import (
    InvalidTransitionError,
    NotFoundError,
    ValidationError,
)


def test_create_task_defaults_and_audit(app, user):
    t = ts.create_task(user.id, "Estudiar", "texto", "2020-01-01")
    assert t.status == "pending"
    assert t.due_date == date(2020, 1, 1)  # fechas pasadas permitidas
    log = AuditLog.query.filter_by(entity_id=t.id).one()
    assert (log.action, log.actor_id, log.entity_type) == ("TASK_CREATED", user.id, "Task")
    assert log.timestamp is not None


@pytest.mark.parametrize("title", ["", "   ", None, "x" * 201])
def test_create_task_rejects_bad_title(app, user, title):
    with pytest.raises(ValidationError):
        ts.create_task(user.id, title, None, None)
    assert AuditLog.query.count() == 0


def test_create_task_rejects_long_description_and_bad_date(app, user):
    with pytest.raises(ValidationError):
        ts.create_task(user.id, "ok", "x" * 2001, None)
    with pytest.raises(ValidationError):
        ts.create_task(user.id, "ok", None, "31-12-2026")
    with pytest.raises(ValidationError):
        ts.create_task(user.id, "ok", None, "2026-02-30")


def test_description_stored_as_plain_text_not_escaped(app, user):
    t = ts.create_task(user.id, "ok", "<script>x</script>\nlinea2", None)
    assert t.description == "<script>x</script>\nlinea2"


def test_list_only_own_tasks_ordered_desc_and_filtered(app, user, other_user):
    a = ts.create_task(user.id, "A", None, None)
    b = ts.create_task(user.id, "B", None, None)
    ts.create_task(other_user.id, "Ajena", None, None)
    ts.change_task_status(user.id, a.id, "in_progress")
    assert [t.title for t in ts.get_user_tasks(user.id)] == ["B", "A"]
    assert [t.title for t in ts.get_user_tasks(user.id, "in_progress")] == ["A"]
    assert [t.title for t in ts.get_user_tasks(user.id, "pending")] == ["B"]
    with pytest.raises(ValidationError):
        ts.get_user_tasks(user.id, "inventado")


@pytest.mark.parametrize(
    "start,end",
    [
        ("pending", "in_progress"),
        ("pending", "completed"),
        ("in_progress", "pending"),
        ("in_progress", "completed"),
    ],
)
def test_valid_transitions_are_audited(app, user, start, end):
    t = ts.create_task(user.id, "T", None, None)
    if start != "pending":
        ts.change_task_status(user.id, t.id, start)
    ts.change_task_status(user.id, t.id, end)
    log = AuditLog.query.filter_by(action="TASK_STATUS_CHANGED").order_by(AuditLog.id.desc()).first()
    d = json.loads(log.details)
    assert d["new_status"] == end and d["old_status"] == start


@pytest.mark.parametrize("target", ["pending", "in_progress", "completed"])
def test_completed_is_locked(app, user, target):
    t = ts.create_task(user.id, "T", None, None)
    ts.change_task_status(user.id, t.id, "completed")
    before = AuditLog.query.count()
    with pytest.raises(InvalidTransitionError):
        ts.change_task_status(user.id, t.id, target)
    assert AuditLog.query.count() == before  # lo rechazado no se audita


def test_same_state_and_unknown_state_rejected(app, user):
    t = ts.create_task(user.id, "T", None, None)
    with pytest.raises(InvalidTransitionError):
        ts.change_task_status(user.id, t.id, "pending")
    with pytest.raises(ValidationError):
        ts.change_task_status(user.id, t.id, "borrada")


def test_update_keeps_status_and_audits(app, user):
    t = ts.create_task(user.id, "T", None, None)
    ts.change_task_status(user.id, t.id, "in_progress")
    t2 = ts.update_task(user.id, t.id, "Nuevo", "d", "2030-05-05")
    assert (t2.title, t2.status) == ("Nuevo", "in_progress")
    assert AuditLog.query.filter_by(action="TASK_UPDATED").count() == 1


def test_update_validates_like_create(app, user):
    t = ts.create_task(user.id, "T", None, None)
    with pytest.raises(ValidationError):
        ts.update_task(user.id, t.id, "  ", None, None)


def test_other_users_task_is_not_found(app, user, other_user):
    t = ts.create_task(user.id, "T", None, None)
    with pytest.raises(NotFoundError):
        ts.update_task(other_user.id, t.id, "hack", None, None)
    with pytest.raises(NotFoundError):
        ts.change_task_status(other_user.id, t.id, "completed")
    with pytest.raises(NotFoundError):
        ts.get_task(other_user.id, 9999)


def test_audit_emits_structured_log(app, user, caplog):
    with caplog.at_level(logging.INFO, logger="taskcontrol.audit"):
        t = ts.create_task(user.id, "T", None, None)
    rec = json.loads(caplog.records[-1].getMessage())
    assert {"actor_id", "action", "entity_type", "entity_id", "timestamp"} <= set(rec)
    assert rec["entity_id"] == t.id


# --- Incremento 3: US1 - Prioridad (HU-07) ---


def test_default_priority_is_medium_on_creation(app, user):
    t = ts.create_task(user.id, "Sin prioridad", None, None)
    assert t.priority == "medium"


def test_invalid_priority_raises_domain_error(app, user):
    with pytest.raises(ValidationError):
        ts.create_task(user.id, "T", None, None, priority="invalid")
    t = ts.create_task(user.id, "T", None, None)
    with pytest.raises(ValidationError):
        ts.set_task_priority(user.id, t.id, "urgente")


def test_tasks_sorted_by_priority_descending(app, user):
    low = ts.create_task(user.id, "Low", None, None, priority="low")
    high = ts.create_task(user.id, "High", None, None, priority="high")
    med = ts.create_task(user.id, "Med", None, None, priority="medium")

    tasks_sort = ts.get_user_tasks(user.id, sort="priority")
    assert [t.title for t in tasks_sort] == ["High", "Med", "Low"]

    tasks_sort_alias = ts.get_user_tasks(user.id, sort_by="priority")
    assert [t.title for t in tasks_sort_alias] == ["High", "Med", "Low"]


def test_tasks_priority_tiebreak_by_created_at_desc(app, user):
    h1 = ts.create_task(user.id, "H1", None, None, priority="high")
    h2 = ts.create_task(user.id, "H2", None, None, priority="high")
    h3 = ts.create_task(user.id, "H3", None, None, priority="high")

    tasks = ts.get_user_tasks(user.id, sort="priority")
    assert [t.title for t in tasks] == ["H3", "H2", "H1"]


def test_set_task_priority_success(app, user):
    t = ts.create_task(user.id, "T", None, None)
    updated = ts.set_task_priority(user.id, t.id, "high")
    assert updated.priority == "high"

    log = (
        AuditLog.query.filter_by(action="TASK_UPDATED", entity_id=t.id)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert log is not None
    d = json.loads(log.details)
    assert d.get("old_priority") == "medium" and d.get("new_priority") == "high"


def test_cannot_set_priority_on_deleted_task(app, user):
    from taskcontrol.services.errors import TaskDeletedError

    t = ts.create_task(user.id, "T", None, None)
    ts.delete_task(user.id, t.id)
    with pytest.raises(TaskDeletedError):
        ts.set_task_priority(user.id, t.id, "high")


def test_cannot_set_priority_on_other_user_task(app, user, other_user):
    t = ts.create_task(user.id, "T", None, None)
    with pytest.raises(NotFoundError):
        ts.set_task_priority(other_user.id, t.id, "high")


# --- Incremento 3: US2 - Categorías (HU-08) ---


def test_assign_task_category_success(app, user):
    from taskcontrol.services.category_service import create_category

    cat = create_category(user.id, "Trabajo")
    t = ts.create_task(user.id, "T", None, None)

    updated = ts.assign_task_category(user.id, t.id, cat.id)
    assert updated.category_id == cat.id

    log = AuditLog.query.filter_by(action="TASK_CATEGORY_ASSIGNED", entity_id=t.id).first()
    assert log is not None
    d = json.loads(log.details)
    assert d.get("previous_category_id") is None and d.get("new_category_id") == cat.id

    unassigned = ts.assign_task_category(user.id, t.id, None)
    assert unassigned.category_id is None


def test_cannot_assign_category_from_another_user(app, user, other_user):
    from taskcontrol.services.category_service import create_category
    from taskcontrol.services.errors import CategoryAccessDeniedError

    cat = create_category(other_user.id, "Ajena")
    t = ts.create_task(user.id, "T", None, None)
    with pytest.raises((CategoryAccessDeniedError, NotFoundError)):
        ts.assign_task_category(user.id, t.id, cat.id)


def test_cannot_assign_category_to_deleted_task(app, user):
    from taskcontrol.services.category_service import create_category
    from taskcontrol.services.errors import TaskDeletedError

    cat = create_category(user.id, "Cat")
    t = ts.create_task(user.id, "T", None, None)
    ts.delete_task(user.id, t.id)
    with pytest.raises(TaskDeletedError):
        ts.assign_task_category(user.id, t.id, cat.id)


def test_filter_tasks_by_category_id(app, user):
    from taskcontrol.services.category_service import create_category

    c1 = create_category(user.id, "C1")
    c2 = create_category(user.id, "C2")

    t1 = ts.create_task(user.id, "T1", None, None, category_id=c1.id)
    t2 = ts.create_task(user.id, "T2", None, None, category_id=c2.id)
    t3 = ts.create_task(user.id, "T3", None, None)

    assert [t.title for t in ts.get_user_tasks(user.id, category=c1.id)] == ["T1"]
    assert [t.title for t in ts.get_user_tasks(user.id, category=c2.id)] == ["T2"]
    assert [t.title for t in ts.get_user_tasks(user.id, category_id=c1.id)] == ["T1"]


def test_filter_tasks_uncategorized(app, user):
    from taskcontrol.services.category_service import create_category

    c1 = create_category(user.id, "C1")
    t1 = ts.create_task(user.id, "T1", None, None, category_id=c1.id)
    t2 = ts.create_task(user.id, "T2", None, None)

    assert [t.title for t in ts.get_user_tasks(user.id, category="uncategorized")] == ["T2"]
    assert [t.title for t in ts.get_user_tasks(user.id, category="none")] == ["T2"]


def test_get_tasks_combines_status_category_id_and_sort_by(app, user):
    from taskcontrol.services.category_service import create_category

    c1 = create_category(user.id, "Cat1")
    c2 = create_category(user.id, "Cat2")

    t1 = ts.create_task(user.id, "T1-high-inprog", None, None, priority="high", category_id=c1.id)
    ts.change_task_status(user.id, t1.id, "in_progress")

    t2 = ts.create_task(user.id, "T2-low-inprog", None, None, priority="low", category_id=c1.id)
    ts.change_task_status(user.id, t2.id, "in_progress")

    t3 = ts.create_task(user.id, "T3-med-pending", None, None, priority="medium", category_id=c1.id)

    t4 = ts.create_task(user.id, "T4-high-inprog-c2", None, None, priority="high", category_id=c2.id)
    ts.change_task_status(user.id, t4.id, "in_progress")

    res = ts.get_user_tasks(user.id, status="in_progress", category=c1.id, sort="priority")
    assert [t.title for t in res] == ["T1-high-inprog", "T2-low-inprog"]


def test_filter_uncategorized_and_nonexistent_category_isolation(app, user, other_user):
    from taskcontrol.services.category_service import create_category

    c_other = create_category(other_user.id, "OtherCat")
    ts.create_task(other_user.id, "OtherTask", None, None, category_id=c_other.id)
    ts.create_task(user.id, "UserTask", None, None)

    assert ts.get_user_tasks(user.id, category=c_other.id) == []
    assert ts.get_user_tasks(user.id, category=99999) == []


# --- Incremento 3: US3 - Vencimiento en Backend (HU-09) ---


def test_completed_task_with_past_due_date_is_never_overdue(app, user):
    from datetime import datetime, timedelta, timezone

    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    t = ts.create_task(user.id, "T", None, yesterday.isoformat())
    ts.change_task_status(user.id, t.id, "completed")
    assert t.is_overdue is False


def test_soft_deleted_task_with_past_due_date_is_never_overdue(app, user):
    from datetime import datetime, timedelta, timezone

    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    t = ts.create_task(user.id, "T", None, yesterday.isoformat())
    ts.delete_task(user.id, t.id)
    assert t.is_overdue is False


def test_pending_or_in_progress_task_with_past_due_date_is_overdue(app, user):
    from datetime import datetime, timedelta, timezone

    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    t1 = ts.create_task(user.id, "T1", None, yesterday.isoformat())
    t2 = ts.create_task(user.id, "T2", None, yesterday.isoformat())
    ts.change_task_status(user.id, t2.id, "in_progress")

    assert t1.is_overdue is True
    assert t2.is_overdue is True


def test_task_with_due_date_today_is_not_overdue_utc(app, user):
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).date()
    t = ts.create_task(user.id, "T", None, today.isoformat())
    assert t.is_overdue is False


def test_task_without_due_date_is_not_overdue(app, user):
    t = ts.create_task(user.id, "T", None, None)
    assert t.is_overdue is False

