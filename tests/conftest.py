import pytest

from taskcontrol import create_app
from taskcontrol.extensions import db


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user(app):
    from taskcontrol.services.auth_service import register_user

    return register_user("ana@example.com", "clave1234")


@pytest.fixture()
def other_user(app):
    from taskcontrol.services.auth_service import register_user

    return register_user("beto@example.com", "clave1234")


@pytest.fixture()
def auth_client(client, user):
    client.post("/login", json={"email": "ana@example.com", "password": "clave1234"})
    return client


@pytest.fixture()
def csrf_client():
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


class FakeSender:
    """Sustituto de ConsoleEmailSender para pruebas unitarias del servicio."""

    def __init__(self):
        self.sent = []

    def send_password_reset(self, to, link):
        self.sent.append((to, link))


@pytest.fixture()
def sender():
    return FakeSender()
