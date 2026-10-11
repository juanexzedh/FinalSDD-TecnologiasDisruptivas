import pytest

JSON = {"Accept": "application/json"}


def _task(c, title="T"):
    return c.post("/tasks", json={"title": title}).get_json()["data"]["id"]


def test_delete_json_and_listing(auth_client):
    tid = _task(auth_client)
    r = auth_client.post(f"/tasks/{tid}/delete", json={})
    assert r.status_code == 200
    d = r.get_json()["data"]
    assert d["id"] == tid and d["is_deleted"] is True and d["deleted_at"]
    assert auth_client.get("/tasks", headers=JSON).get_json()["data"]["total"] == 0


def test_delete_twice_returns_400(auth_client):
    tid = _task(auth_client)
    auth_client.post(f"/tasks/{tid}/delete", json={})
    r = auth_client.post(f"/tasks/{tid}/delete", json={})
    assert r.status_code == 400 and r.get_json()["code"] == "TASK_ALREADY_DELETED"


def test_deleted_task_cannot_be_edited_or_changed(auth_client):
    tid = _task(auth_client)
    auth_client.post(f"/tasks/{tid}/delete", json={})
    for path, body in ((f"/tasks/{tid}/edit", {"title": "x"}), (f"/tasks/{tid}/status", {"status": "in_progress"}), (f"/tasks/{tid}/reopen", {})):
        r = auth_client.post(path, json=body)
        assert r.status_code == 400 and r.get_json()["code"] == "TASK_DELETED"


def test_delete_html_redirects_to_list(auth_client):
    tid = _task(auth_client, "Borrable")
    r = auth_client.post(f"/tasks/{tid}/delete", data={})
    assert r.status_code == 302 and r.headers["Location"].endswith("/tasks")
    assert b"Borrable" not in auth_client.get("/tasks").data


def test_reopen_json(auth_client):
    tid = _task(auth_client)
    auth_client.post(f"/tasks/{tid}/status", json={"status": "completed"})
    r = auth_client.post(f"/tasks/{tid}/reopen", json={})
    assert r.status_code == 200
    d = r.get_json()["data"]
    assert (d["previous_status"], d["new_status"]) == ("completed", "pending")


def test_reopen_non_completed_returns_400(auth_client):
    tid = _task(auth_client)
    r = auth_client.post(f"/tasks/{tid}/reopen", json={})
    assert r.status_code == 400 and r.get_json()["code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.parametrize("path", ["/tasks/1/delete", "/tasks/1/reopen"])
def test_new_endpoints_require_session(client, path):
    assert client.post(path, json={}, headers=JSON).status_code == 401


def test_other_users_task_gives_404_on_new_endpoints(client, user, other_user):
    client.post("/login", json={"email": "beto@example.com", "password": "clave1234"})
    tid = _task(client)
    client.post("/logout", json={})
    client.post("/login", json={"email": "ana@example.com", "password": "clave1234"})
    assert client.post(f"/tasks/{tid}/delete", json={}).status_code == 404
    assert client.post(f"/tasks/{tid}/reopen", json={}).status_code == 404


def test_browser_unknown_task_redirects_with_flash(auth_client):
    """Decisión clarify 001 Q5: redirigir a /tasks con mensaje, sin revelar existencia."""
    r = auth_client.get("/tasks/999/edit")
    assert r.status_code == 302 and r.headers["Location"].endswith("/tasks")
    assert "Tarea no encontrada" in auth_client.get("/tasks").data.decode()


def test_ui_completed_task_shows_reopen_and_no_status_buttons(auth_client):
    tid = _task(auth_client, "Hecha")
    auth_client.post(f"/tasks/{tid}/status", json={"status": "completed"})
    html = auth_client.get("/tasks").data.decode()
    assert "Completada" in html and "Reabrir" in html and "Eliminar" in html
    assert "→ En progreso" not in html and "→ Pendiente" not in html


@pytest.mark.parametrize("path", ["/tasks/1/delete", "/tasks/1/reopen"])
def test_csrf_enforced_on_new_posts(csrf_client, path):
    r = csrf_client.post(path, json={})
    assert r.status_code == 400 and r.get_json()["code"] == "CSRF_ERROR"
