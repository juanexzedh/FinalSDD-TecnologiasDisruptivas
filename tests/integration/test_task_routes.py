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


# --- Incremento 3: US1 - Prioridad (HU-07) ---


def test_priority_endpoints_require_session(client):
    assert client.post("/tasks/1/priority", json={"priority": "high"}, headers=JSON).status_code == 401


def test_set_task_priority_route_json(auth_client):
    auth_client.post("/tasks", json={"title": "Tarea P"}, headers=JSON)
    r = auth_client.post("/tasks/1/priority", json={"priority": "high"}, headers=JSON)
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["priority"] == "high"
    assert data["previous_priority"] == "medium"


def test_set_task_priority_route_html(auth_client):
    auth_client.post("/tasks", json={"title": "Tarea HTML"}, headers=JSON)
    r = auth_client.post("/tasks/1/priority", data={"priority": "low"})
    assert r.status_code == 302
    assert "/tasks" in r.headers["Location"]


def test_set_task_priority_invalid_value(auth_client):
    auth_client.post("/tasks", json={"title": "Tarea P"}, headers=JSON)
    r = auth_client.post("/tasks/1/priority", json={"priority": "invalid"}, headers=JSON)
    assert r.status_code == 400


def test_task_priority_sorting_routes(auth_client):
    auth_client.post("/tasks", json={"title": "Baja", "priority": "low"}, headers=JSON)
    auth_client.post("/tasks", json={"title": "Alta", "priority": "high"}, headers=JSON)
    auth_client.post("/tasks", json={"title": "Media", "priority": "medium"}, headers=JSON)

    r = auth_client.get("/tasks?sort=priority", headers=JSON)
    assert r.status_code == 200
    titles = [t["title"] for t in r.get_json()["data"]["tasks"]]
    assert titles == ["Alta", "Media", "Baja"]

    r_alias = auth_client.get("/tasks?sort_by=priority", headers=JSON)
    assert r_alias.status_code == 200
    assert [t["title"] for t in r_alias.get_json()["data"]["tasks"]] == ["Alta", "Media", "Baja"]


# --- Incremento 3: US2 - Categorías en tareas (HU-08) ---


def test_task_category_endpoints_require_session(client):
    assert client.post("/tasks/1/category", json={"category_id": 1}, headers=JSON).status_code == 401


def test_assign_task_category_route(auth_client):
    r_cat = auth_client.post("/categories", json={"name": "Trabajo"}, headers=JSON)
    cat_id = r_cat.get_json()["data"]["id"]

    auth_client.post("/tasks", json={"title": "Tarea Cat"}, headers=JSON)
    r_assign = auth_client.post("/tasks/1/category", json={"category_id": cat_id}, headers=JSON)
    assert r_assign.status_code == 200
    assert r_assign.get_json()["data"]["category_id"] == cat_id

    # Desasignar
    r_unassign = auth_client.post("/tasks/1/category", json={"category_id": None}, headers=JSON)
    assert r_unassign.status_code == 200
    assert r_unassign.get_json()["data"]["category_id"] is None


def test_cannot_assign_other_user_category_route(client, user, other_user):
    # beto crea cat
    client.post("/login", json={"email": "beto@example.com", "password": "clave1234"})
    r_cat = client.post("/categories", json={"name": "Beto Cat"}, headers=JSON)
    beto_cat_id = r_cat.get_json()["data"]["id"]
    client.post("/logout", json={})

    # ana intenta asignarla a su tarea
    client.post("/login", json={"email": "ana@example.com", "password": "clave1234"})
    client.post("/tasks", json={"title": "Ana Task"}, headers=JSON)
    r = client.post("/tasks/1/category", json={"category_id": beto_cat_id}, headers=JSON)
    assert r.status_code in (400, 403, 404)


def test_filter_by_category_routes(auth_client):
    r_c1 = auth_client.post("/categories", json={"name": "C1"}, headers=JSON)
    c1_id = r_c1.get_json()["data"]["id"]

    r_c2 = auth_client.post("/categories", json={"name": "C2"}, headers=JSON)
    c2_id = r_c2.get_json()["data"]["id"]

    auth_client.post("/tasks", json={"title": "T_C1", "category_id": c1_id, "priority": "high"}, headers=JSON)
    auth_client.post("/tasks", json={"title": "T_C2", "category_id": c2_id, "priority": "low"}, headers=JSON)
    auth_client.post("/tasks", json={"title": "T_None"}, headers=JSON)

    # Filtrar c1
    r1 = auth_client.get(f"/tasks?category={c1_id}", headers=JSON)
    assert [t["title"] for t in r1.get_json()["data"]["tasks"]] == ["T_C1"]

    # Filtrar sin categoria
    r_none = auth_client.get("/tasks?category=uncategorized", headers=JSON)
    assert [t["title"] for t in r_none.get_json()["data"]["tasks"]] == ["T_None"]

    # Combinado
    r_comb = auth_client.get(f"/tasks?status=pending&category={c1_id}&sort=priority", headers=JSON)
    assert [t["title"] for t in r_comb.get_json()["data"]["tasks"]] == ["T_C1"]


# --- Incremento 3: US3 - Vencimiento en rutas (HU-09) ---


def test_task_overdue_in_routes(auth_client):
    from datetime import datetime, timedelta, timezone

    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    today = datetime.now(timezone.utc).date().isoformat()

    auth_client.post("/tasks", json={"title": "Vencida", "due_date": yesterday}, headers=JSON)
    auth_client.post("/tasks", json={"title": "Hoy", "due_date": today}, headers=JSON)

    # JSON expone is_overdue
    r = auth_client.get("/tasks", headers=JSON)
    assert r.status_code == 200
    tasks = r.get_json()["data"]["tasks"]
    overdue_task = [t for t in tasks if t["title"] == "Vencida"][0]
    today_task = [t for t in tasks if t["title"] == "Hoy"][0]
    assert overdue_task["is_overdue"] is True
    assert today_task["is_overdue"] is False

    # HTML expone badge
    html = auth_client.get("/tasks").data.decode()
    assert "Vencida" in html
    assert "badge-overdue" in html

