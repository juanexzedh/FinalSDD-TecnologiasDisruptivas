import pytest

JSON = {"Accept": "application/json"}


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/categories"),
        ("post", "/categories"),
        ("post", "/categories/1/edit"),
        ("post", "/categories/1/delete"),
    ],
)
def test_category_endpoints_require_session(client, method, path):
    r = (
        getattr(client, method)(path, json={}, headers=JSON)
        if method == "post"
        else client.get(path, headers=JSON)
    )
    assert r.status_code == 401


def test_crud_category_json(auth_client):
    # 1. Crear
    r = auth_client.post("/categories", json={"name": "Proyectos"}, headers=JSON)
    assert r.status_code == 201
    cat_id = r.get_json()["data"]["id"]
    assert r.get_json()["data"]["name"] == "Proyectos"

    # 2. Rechazar duplicado
    r_dup = auth_client.post("/categories", json={"name": "proyectos"}, headers=JSON)
    assert r_dup.status_code in (400, 409)

    # 3. Listar
    r_list = auth_client.get("/categories", headers=JSON)
    assert r_list.status_code == 200
    data = r_list.get_json()["data"]
    assert data["total"] == 1
    assert data["categories"][0]["name"] == "Proyectos"

    # 4. Renombrar
    r_edit = auth_client.post(
        f"/categories/{cat_id}/edit", json={"name": "Proyectos Nuevos"}, headers=JSON
    )
    assert r_edit.status_code == 200
    assert r_edit.get_json()["data"]["name"] == "Proyectos Nuevos"

    # 5. Eliminar
    r_del = auth_client.post(f"/categories/{cat_id}/delete", headers=JSON)
    assert r_del.status_code == 200

    # 6. Listar de nuevo vacío
    r_after = auth_client.get("/categories", headers=JSON)
    assert r_after.get_json()["data"]["total"] == 0


def test_category_html_flow(auth_client):
    # GET vista
    r = auth_client.get("/categories")
    assert r.status_code == 200
    assert b"Categor" in r.data

    # POST crear
    r_create = auth_client.post("/categories", data={"name": "Personal"})
    assert r_create.status_code == 302
    assert "/categories" in r_create.headers["Location"]

    # POST renombrar
    r_edit = auth_client.post("/categories/1/edit", data={"name": "Personal 2"})
    assert r_edit.status_code == 302
    assert "/categories" in r_edit.headers["Location"]

    # POST eliminar
    r_del = auth_client.post("/categories/1/delete", data={})
    assert r_del.status_code == 302
    assert "/categories" in r_del.headers["Location"]


def test_delete_category_unlinks_tasks_in_routes(auth_client):
    r_cat = auth_client.post("/categories", json={"name": "Urgente"}, headers=JSON)
    cat_id = r_cat.get_json()["data"]["id"]

    r_task = auth_client.post(
        "/tasks", json={"title": "Tarea en categoria", "category_id": cat_id}, headers=JSON
    )
    task_id = r_task.get_json()["data"]["id"]

    # Verificar que tiene categoría
    r_tasks = auth_client.get("/tasks", headers=JSON)
    t = [x for x in r_tasks.get_json()["data"]["tasks"] if x["id"] == task_id][0]
    assert t["category"] is not None and t["category"]["id"] == cat_id

    # Eliminar categoría
    r_del = auth_client.post(f"/categories/{cat_id}/delete", headers=JSON)
    assert r_del.status_code == 200

    # Verificar que la tarea sigue activa y con category null
    r_tasks_after = auth_client.get("/tasks", headers=JSON)
    t_after = [x for x in r_tasks_after.get_json()["data"]["tasks"] if x["id"] == task_id][0]
    assert t_after["category"] is None


def test_other_user_category_isolation_routes(client, user, other_user):
    # beto crea una categoria
    client.post("/login", json={"email": "beto@example.com", "password": "clave1234"})
    r_cat = client.post("/categories", json={"name": "Secreta Beto"}, headers=JSON)
    cat_id = r_cat.get_json()["data"]["id"]
    client.post("/logout", json={})

    # ana intenta editar o borrar
    client.post("/login", json={"email": "ana@example.com", "password": "clave1234"})
    assert (
        client.post(f"/categories/{cat_id}/edit", json={"name": "Hack"}, headers=JSON).status_code
        == 404
    )
    assert client.post(f"/categories/{cat_id}/delete", headers=JSON).status_code == 404
