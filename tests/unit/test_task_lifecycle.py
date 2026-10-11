import json

import pytest

from taskcontrol.extensions import db
from taskcontrol.models import AuditLog, Task
from taskcontrol.services import task_service as ts
from taskcontrol.services.errors import (
    InvalidTransitionError,
    NotFoundError,
    TaskAlreadyDeletedError,
    TaskDeletedError,
)


# ---------------- HU-05: eliminación lógica ----------------
def test_delete_is_logical_and_audited(app, user):
    t = ts.create_task(user.id, "T", None, None)
    ts.delete_task(user.id, t.id)
    row = db.session.get(Task, t.id)
    assert row is not None  # nunca borrado físico
    assert row.is_deleted is True and row.deleted_at is not None
    assert AuditLog.query.filter_by(action="TASK_DELETED", entity_id=t.id).count() == 1


@pytest.mark.parametrize("flt", ["all", "pending", "in_progress", "completed"])
def test_deleted_task_never_listed(app, user, flt):
    a = ts.create_task(user.id, "A", None, None)
    b = ts.create_task(user.id, "B", None, None)
    ts.change_task_status(user.id, a.id, "completed")
    ts.delete_task(user.id, a.id)
    ts.delete_task(user.id, b.id)
    assert ts.get_user_tasks(user.id, flt) == []


def test_audit_history_preserved_after_delete(app, user):
    t = ts.create_task(user.id, "T", None, None)
    ts.delete_task(user.id, t.id)
    actions = [a.action for a in AuditLog.query.filter_by(entity_id=t.id).order_by(AuditLog.id)]
    assert actions == ["TASK_CREATED", "TASK_DELETED"]


def test_cannot_delete_twice(app, user):
    t = ts.create_task(user.id, "T", None, None)
    ts.delete_task(user.id, t.id)
    before = AuditLog.query.count()
    with pytest.raises(TaskAlreadyDeletedError):
        ts.delete_task(user.id, t.id)
    assert AuditLog.query.count() == before


def test_cannot_edit_change_status_or_reopen_deleted_task(app, user):
    t = ts.create_task(user.id, "T", None, None)
    ts.delete_task(user.id, t.id)
    with pytest.raises(TaskDeletedError):
        ts.update_task(user.id, t.id, "nuevo", None, None)
    with pytest.raises(TaskDeletedError):
        ts.change_task_status(user.id, t.id, "in_progress")
    with pytest.raises(TaskDeletedError):
        ts.reopen_task(user.id, t.id)


def test_deleted_task_is_hidden_from_get_task(app, user):
    t = ts.create_task(user.id, "T", None, None)
    ts.delete_task(user.id, t.id)
    with pytest.raises(NotFoundError):
        ts.get_task(user.id, t.id)


def test_other_user_cannot_delete(app, user, other_user):
    t = ts.create_task(user.id, "T", None, None)
    with pytest.raises(NotFoundError):
        ts.delete_task(other_user.id, t.id)
    assert db.session.get(Task, t.id).is_deleted is False


def test_soft_delete_is_permanent_for_user(app):
    """Decisión de clarify Q1: sin papelera ni restauración."""
    assert not hasattr(ts, "restore_task") and not hasattr(ts, "undelete_task")


# ---------------- HU-06: reapertura ----------------
def test_reopen_completed_goes_to_pending_with_distinct_event(app, user):
    t = ts.create_task(user.id, "T", None, None)
    ts.change_task_status(user.id, t.id, "completed")
    ts.reopen_task(user.id, t.id)
    assert db.session.get(Task, t.id).status == "pending"
    log = AuditLog.query.filter_by(action="TASK_REOPENED").one()
    d = json.loads(log.details)
    assert d == {"previous_status": "completed", "new_status": "pending"}
    # distinto de TASK_CREATED y de TASK_STATUS_CHANGED
    assert AuditLog.query.filter_by(action="TASK_STATUS_CHANGED").count() == 1


@pytest.mark.parametrize("state", ["pending", "in_progress"])
def test_cannot_reopen_non_completed(app, user, state):
    t = ts.create_task(user.id, "T", None, None)
    if state != "pending":
        ts.change_task_status(user.id, t.id, state)
    with pytest.raises(InvalidTransitionError):
        ts.reopen_task(user.id, t.id)
    assert AuditLog.query.filter_by(action="TASK_REOPENED").count() == 0


def test_reopened_task_can_continue_workflow(app, user):
    t = ts.create_task(user.id, "T", None, None)
    ts.change_task_status(user.id, t.id, "completed")
    ts.reopen_task(user.id, t.id)
    ts.change_task_status(user.id, t.id, "in_progress")
    assert db.session.get(Task, t.id).status == "in_progress"


def test_ordinary_status_change_still_cannot_leave_completed(app, user):
    t = ts.create_task(user.id, "T", None, None)
    ts.change_task_status(user.id, t.id, "completed")
    with pytest.raises(InvalidTransitionError):
        ts.change_task_status(user.id, t.id, "pending")


def test_other_user_cannot_reopen(app, user, other_user):
    t = ts.create_task(user.id, "T", None, None)
    ts.change_task_status(user.id, t.id, "completed")
    with pytest.raises(NotFoundError):
        ts.reopen_task(other_user.id, t.id)
