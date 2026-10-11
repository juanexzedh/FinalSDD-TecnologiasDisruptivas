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
