import pytest

JSON = {"Accept": "application/json"}


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/tasks"),
        ("post", "/tasks/1/edit"),
        ("post", "/tasks/1/status"),
        ("get", "/tasks/new"),
        ("get", "/tasks/1/edit"),
    ],
)
def test_task_endpoints_require_session_in_backend(client, method, path):
    r = getattr(client, method)(path, json={}, headers=JSON) if method == "post" else client.get(path, headers=JSON)
    assert r.status_code == 401


def test_create_list_filter(auth_client):
    r = auth_client.post("/tasks", json={"title": "Uno", "due_date": "2026-10-12"})
    assert r.status_code == 201 and r.get_json()["data"]["status"] == "pending"
    auth_client.post("/tasks", json={"title": "Dos"})
    auth_client.post("/tasks/1/status", json={"status": "in_progress"})
    data = auth_client.get("/tasks?status=in_progress", headers=JSON).get_json()["data"]
    assert [t["title"] for t in data["tasks"]] == ["Uno"]
    data = auth_client.get("/tasks", headers=JSON).get_json()["data"]
    assert [t["title"] for t in data["tasks"]] == ["Dos", "Uno"]


def test_create_validation_error_shape(auth_client):
    r = auth_client.post("/tasks", json={"title": "  "})
    assert r.status_code == 400
    body = r.get_json()
    assert body["code"] == "VALIDATION_ERROR" and "title" in body["errors"]


def test_invalid_transition_returns_400(auth_client):
    auth_client.post("/tasks", json={"title": "T"})
    assert auth_client.post("/tasks/1/status", json={"status": "completed"}).status_code == 200
    r = auth_client.post("/tasks/1/status", json={"status": "pending"})
    assert r.status_code == 400 and r.get_json()["code"] == "INVALID_STATE_TRANSITION"


def test_edit_task(auth_client):
    auth_client.post("/tasks", json={"title": "T"})
    r = auth_client.post("/tasks/1/edit", json={"title": "Nuevo", "description": "d"})
    assert r.status_code == 200 and r.get_json()["data"]["title"] == "Nuevo"
    assert auth_client.post("/tasks/1/edit", json={"title": ""}).status_code == 400


def test_user_never_sees_or_touches_other_users_tasks(client, user, other_user):
    client.post("/login", json={"email": "beto@example.com", "password": "clave1234"})
    client.post("/tasks", json={"title": "Secreta de Beto"})
    client.post("/logout", json={})
    client.post("/login", json={"email": "ana@example.com", "password": "clave1234"})
    assert client.get("/tasks", headers=JSON).get_json()["data"]["total"] == 0
    assert client.post("/tasks/1/status", json={"status": "completed"}).status_code == 404
    assert client.post("/tasks/1/edit", json={"title": "x"}).status_code == 404
    assert client.get("/tasks/1/edit", headers=JSON).status_code == 404


def test_xss_is_escaped_on_render(auth_client):
    auth_client.post("/tasks", json={"title": "<b>hola</b>", "description": "<script>alert(1)</script>"})
    html = auth_client.get("/tasks").data.decode()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_html_form_flow(auth_client):
    r = auth_client.post("/tasks", data={"title": "Desde form"})
    assert r.status_code == 302
    assert b"Desde form" in auth_client.get("/tasks").data
