import pytest

from taskcontrol.services.auth_service import authenticate_user, register_user
from taskcontrol.services.errors import (
    AuthenticationError,
    DuplicateEmailError,
    ValidationError,
)


def test_register_hashes_password_and_normalizes_email(app):
    u = register_user("  Ana@Example.COM ", "clave1234")
    assert u.email == "ana@example.com"
    assert u.password_hash != "clave1234"
    assert "clave1234" not in u.password_hash


@pytest.mark.parametrize("email", ["", "sin-arroba", "a@b", "a b@c.com"])
def test_register_rejects_invalid_email(app, email):
    with pytest.raises(ValidationError):
        register_user(email, "clave1234")


@pytest.mark.parametrize("pwd", ["", "corta1", "sololetras", "12345678"])
def test_register_rejects_weak_password(app, pwd):
    with pytest.raises(ValidationError):
        register_user("x@example.com", pwd)


def test_register_rejects_duplicate_email_case_insensitive(app, user):
    with pytest.raises(DuplicateEmailError):
        register_user("ANA@example.com", "otraClave99")


def test_authenticate_ok_and_fail(app, user):
    assert authenticate_user("ana@example.com", "clave1234").id == user.id
    with pytest.raises(AuthenticationError):
        authenticate_user("ana@example.com", "incorrecta1")
    with pytest.raises(AuthenticationError):
        authenticate_user("nadie@example.com", "clave1234")
