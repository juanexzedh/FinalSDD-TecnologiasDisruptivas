import hashlib
import secrets
from datetime import timedelta

from werkzeug.security import generate_password_hash

from ..extensions import db
from ..models import PasswordResetToken, User
from . import audit_service
from .auth_service import normalize_email, validate_password, _EMAIL_RE
from .errors import InvalidTokenError, ValidationError
from .timeutil import as_utc, utcnow

TOKEN_TTL = timedelta(minutes=15)  # clarify 002 Q4
THROTTLE_WINDOW = timedelta(minutes=15)
THROTTLE_MAX = 3  # clarify 002 Q5


def _hash(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def request_password_reset(email, sender, link_builder):
    """Respuesta ciega: devuelve siempre None, exista o no el correo y haya o no throttling."""
    email = normalize_email(email)
    if not _EMAIL_RE.match(email):
        raise ValidationError({"email": ["Formato de correo inválido."]})
    now = utcnow()
    user = User.query.filter_by(email=email).first()
    raw = secrets.token_urlsafe(32)
    digest = _hash(raw)  # se calcula siempre para igualar el trabajo en ambos caminos
    recent = (
        PasswordResetToken.query.filter(
            PasswordResetToken.user_id == (user.id if user else -1),
            PasswordResetToken.created_at >= now - THROTTLE_WINDOW,
        ).count()
    )
    if user is None or recent >= THROTTLE_MAX:
        return None  # silent throttling / correo inexistente: sin token ni correo
    # Un token nuevo invalida los anteriores aún no utilizados
    for old in PasswordResetToken.query.filter_by(user_id=user.id, used_at=None).all():
        old.used_at = now
    db.session.add(
        PasswordResetToken(user_id=user.id, token_hash=digest, created_at=now, expires_at=now + TOKEN_TTL)
    )
    db.session.commit()
    sender.send_password_reset(user.email, link_builder(raw))
    return None


def _valid_token_row(raw):
    row = PasswordResetToken.query.filter_by(token_hash=_hash(raw or "")).first()
    if row is None or row.used_at is not None or as_utc(row.expires_at) <= utcnow():
        raise InvalidTokenError("Enlace inválido o expirado.")
    return row


def is_token_valid(raw):
    try:
        _valid_token_row(raw)
        return True
    except InvalidTokenError:
        return False


def reset_password(raw_token, new_password, confirm_password):
    row = _valid_token_row(raw_token)
    validate_password(new_password)
    if new_password != confirm_password:
        raise ValidationError({"confirm_password": ["Las contraseñas no coinciden."]})
    user = db.session.get(User, row.user_id)
    user.password_hash = generate_password_hash(new_password)
    user.session_version += 1  # revoca todas las sesiones activas (clarify 002 Q3)
    row.used_at = utcnow()
    audit_service.record_event(user.id, "PASSWORD_RESET_COMPLETED", "User", user.id)
    db.session.commit()
    return user
