def test_register_login_logout_flow(client):
    r = client.post("/register", json={"email": "z@example.com", "password": "clave1234"})
    assert r.status_code == 201
    r = client.post("/login", json={"email": "z@example.com", "password": "clave1234"})
    assert r.status_code == 200
    assert client.get("/tasks", headers={"Accept": "application/json"}).status_code == 200
    assert client.post("/logout", json={}).status_code == 200
    assert client.get("/tasks", headers={"Accept": "application/json"}).status_code == 401


def test_register_errors(client, user):
    assert client.post("/register", json={"email": "mala", "password": "clave1234"}).status_code == 400
    assert client.post("/register", json={"email": "q@example.com", "password": "debil"}).status_code == 400
    assert client.post("/register", json={"email": "ana@example.com", "password": "clave1234"}).status_code == 409


def test_login_wrong_credentials_is_401_and_generic(client, user):
    a = client.post("/login", json={"email": "ana@example.com", "password": "malaclave1"})
    b = client.post("/login", json={"email": "nadie@example.com", "password": "clave1234"})
    assert a.status_code == b.status_code == 401
    assert a.get_json()["message"] == b.get_json()["message"]


def test_html_pages_render(client):
    for path in ("/login", "/register"):
        r = client.get(path)
        assert r.status_code == 200 and b"csrf" in r.data.lower()


def test_html_unauthenticated_redirects_to_login(client):
    r = client.get("/tasks")
    assert r.status_code == 302 and "/login" in r.headers["Location"]
