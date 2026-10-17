import re

import pytest

from taskcontrol import create_app
from taskcontrol.extensions import db


@pytest.fixture()
def csrf_client():
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_post_without_token_is_rejected(csrf_client):
    r = csrf_client.post("/register", json={"email": "a@example.com", "password": "clave1234"})
    assert r.status_code == 400
    assert r.get_json()["code"] == "CSRF_ERROR"


def test_post_with_tampered_token_is_rejected(csrf_client):
    r = csrf_client.post(
        "/login", json={"email": "a@example.com", "password": "x"}, headers={"X-CSRFToken": "falso"}
    )
    assert r.status_code == 400


def test_post_with_valid_token_passes_csrf(csrf_client):
    html = csrf_client.get("/register").data.decode()
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    r = csrf_client.post(
        "/register",
        json={"email": "a@example.com", "password": "clave1234"},
        headers={"X-CSRFToken": token},
    )
    assert r.status_code == 201


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/tasks/1/priority", {"priority": "high"}),
        ("/categories", {"name": "Nueva"}),
        ("/categories/1/edit", {"name": "Editada"}),
        ("/categories/1/delete", {}),
        ("/tasks/1/category", {"category_id": 1}),
    ],
)
def test_new_post_endpoints_enforce_csrf(csrf_client, path, payload):
    r = csrf_client.post(path, json=payload)
    assert r.status_code == 400
    assert r.get_json()["code"] == "CSRF_ERROR"

