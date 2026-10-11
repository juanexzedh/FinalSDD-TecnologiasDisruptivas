import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from taskcontrol.extensions import db
from taskcontrol.models import AuditLog, PasswordResetToken, User
from taskcontrol.services import recovery_service as rs
from taskcontrol.services.auth_service import authenticate_user
from taskcontrol.services.errors import AuthenticationError, InvalidTokenError, ValidationError


def link(t):
    return f"http://localhost/reset-password/{t}"


def raw_token(sender):
    return sender.sent[-1][1].rsplit("/", 1)[1]


def test_request_for_registered_email_stores_only_hash_and_sends_link(app, user, sender):
    rs.request_password_reset("ANA@example.com", sender, link)
    assert len(sender.sent) == 1 and sender.sent[0][0] == "ana@example.com"
    raw = raw_token(sender)
    row = PasswordResetToken.query.one()
    assert row.token_hash == hashlib.sha256(raw.encode()).hexdigest()
    assert raw not in row.token_hash and len(row.token_hash) == 64
    exp = row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
    assert timedelta(minutes=14) < exp - datetime.now(timezone.utc) <= timedelta(minutes=15)


def test_request_for_unregistered_email_is_blind(app, sender):
    assert rs.request_password_reset("nadie@example.com", sender, link) is None
    assert PasswordResetToken.query.count() == 0 and sender.sent == []


def test_new_request_invalidates_previous_unused_token(app, user, sender):
    rs.request_password_reset("ana@example.com", sender, link)
    first = raw_token(sender)
    rs.request_password_reset("ana@example.com", sender, link)
    with pytest.raises(InvalidTokenError):
        rs.reset_password(first, "NuevaClave99", "NuevaClave99")
    rs.reset_password(raw_token(sender), "NuevaClave99", "NuevaClave99")  # el último sí sirve


def test_silent_throttling_max_3_per_15_minutes(app, user, sender):
    for _ in range(5):
        assert rs.request_password_reset("ana@example.com", sender, link) is None
    assert len(sender.sent) == 3 and PasswordResetToken.query.count() == 3


def test_valid_token_changes_password_and_is_single_use(app, user, sender):
    rs.request_password_reset("ana@example.com", sender, link)
    raw = raw_token(sender)
    rs.reset_password(raw, "NuevaClave99", "NuevaClave99")
    assert authenticate_user("ana@example.com", "NuevaClave99").id == user.id
    with pytest.raises(AuthenticationError):
        authenticate_user("ana@example.com", "clave1234")
    assert PasswordResetToken.query.one().used_at is not None
    with pytest.raises(InvalidTokenError):
        rs.reset_password(raw, "OtraClave123", "OtraClave123")


def test_expired_token_is_rejected(app, user, sender):
    rs.request_password_reset("ana@example.com", sender, link)
    row = PasswordResetToken.query.one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()
    with pytest.raises(InvalidTokenError):
        rs.reset_password(raw_token(sender), "NuevaClave99", "NuevaClave99")


def test_garbage_token_is_rejected(app, user):
    with pytest.raises(InvalidTokenError):
        rs.reset_password("no-existe", "NuevaClave99", "NuevaClave99")


def test_weak_or_mismatched_password_rejected_and_token_not_consumed(app, user, sender):
    rs.request_password_reset("ana@example.com", sender, link)
    raw = raw_token(sender)
    with pytest.raises(ValidationError):
        rs.reset_password(raw, "debil", "debil")
    with pytest.raises(ValidationError):
        rs.reset_password(raw, "NuevaClave99", "Distinta1234")
    assert PasswordResetToken.query.one().used_at is None
    rs.reset_password(raw, "NuevaClave99", "NuevaClave99")


def test_reset_password_revokes_all_active_sessions(app, user, sender):
    v0 = user.session_version
    rs.request_password_reset("ana@example.com", sender, link)
    rs.reset_password(raw_token(sender), "NuevaClave99", "NuevaClave99")
    assert db.session.get(User, user.id).session_version == v0 + 1


def test_reset_is_audited(app, user, sender):
    rs.request_password_reset("ana@example.com", sender, link)
    rs.reset_password(raw_token(sender), "NuevaClave99", "NuevaClave99")
    log = AuditLog.query.filter_by(action="PASSWORD_RESET_COMPLETED").one()
    assert (log.actor_id, log.entity_type, log.entity_id) == (user.id, "User", user.id)
