import re

from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User
from .errors import AuthenticationError, DuplicateEmailError, ValidationError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email):
    return (email or "").strip().lower()


def validate_password(password):
    pwd = password or ""
    if len(pwd) < 8 or not re.search(r"[A-Za-z]", pwd) or not re.search(r"\d", pwd):
        raise ValidationError(
            {"password": ["La contraseña debe tener mínimo 8 caracteres, con al menos una letra y un número."]}
        )


def register_user(email, password):
    email = normalize_email(email)
    if not _EMAIL_RE.match(email) or len(email) > 255:
        raise ValidationError({"email": ["Formato de correo inválido."]})
    validate_password(password)
    if User.query.filter_by(email=email).first():
        raise DuplicateEmailError("El correo ya está registrado.")
    user = User(email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise DuplicateEmailError("El correo ya está registrado.")
    return user


def authenticate_user(email, password):
    user = User.query.filter_by(email=normalize_email(email)).first()
    if user is None or not check_password_hash(user.password_hash, password or ""):
        raise AuthenticationError("Credenciales inválidas.")
    return user


def get_user(user_id):
    return db.session.get(User, user_id)
