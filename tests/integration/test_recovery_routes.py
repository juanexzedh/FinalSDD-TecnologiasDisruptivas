import re

JSON = {"Accept": "application/json"}


def _sent(app):
    return app.extensions["email_sender"].sent


def test_forgot_password_page_renders(client):
    r = client.get("/forgot-password")
    assert r.status_code == 200 and b"csrf" in r.data.lower()


def test_blind_response_identical_for_registered_and_unregistered(client, user):
    a = client.post("/forgot-password", json={"email": "ana@example.com"})
    b = client.post("/forgot-password", json={"email": "nadie@example.com"})
    assert a.status_code == b.status_code == 200
    assert a.get_json() == b.get_json()


def test_blind_response_html_redirects_to_login(client, user):
    for email in ("ana@example.com", "nadie@example.com"):
        r = client.post("/forgot-password", data={"email": email})
        assert r.status_code == 302 and r.headers["Location"].endswith("/login")


def test_malformed_email_is_validation_error(client):
    r = client.post("/forgot-password", json={"email": "no-es-correo"})
    assert r.status_code == 400 and r.get_json()["code"] == "VALIDATION_ERROR"


def test_full_reset_flow(app, client, user):
    client.post("/forgot-password", json={"email": "ana@example.com"})
    token = _sent(app)[-1][1].rsplit("/", 1)[1]
    assert client.get(f"/reset-password/{token}").status_code == 200
    r = client.post(f"/reset-password/{token}", json={"new_password": "NuevaClave99", "confirm_password": "NuevaClave99"})
    assert r.status_code == 200 and r.get_json()["code"] == "PASSWORD_UPDATED"
    assert client.post("/login", json={"email": "ana@example.com", "password": "NuevaClave99"}).status_code == 200
    assert client.post("/login", json={"email": "ana@example.com", "password": "clave1234"}).status_code == 401


def test_invalid_token_post_and_get(client):
    r = client.post("/reset-password/falso", json={"new_password": "NuevaClave99", "confirm_password": "NuevaClave99"})
    assert r.status_code == 400 and r.get_json()["code"] == "INVALID_OR_EXPIRED_TOKEN"
    g = client.get("/reset-password/falso")
    assert g.status_code == 302 and g.headers["Location"].endswith("/forgot-password")


def test_weak_password_rejected_by_route(app, client, user):
    client.post("/forgot-password", json={"email": "ana@example.com"})
    token = _sent(app)[-1][1].rsplit("/", 1)[1]
    r = client.post(f"/reset-password/{token}", json={"new_password": "debil", "confirm_password": "debil"})
    assert r.status_code == 400 and r.get_json()["code"] == "VALIDATION_ERROR"


def test_reset_revokes_sessions_in_other_browsers(app, auth_client, user):
    assert auth_client.get("/tasks", headers=JSON).status_code == 200
    other = app.test_client()
    other.post("/forgot-password", json={"email": "ana@example.com"})
    token = _sent(app)[-1][1].rsplit("/", 1)[1]
    other.post(f"/reset-password/{token}", json={"new_password": "NuevaClave99", "confirm_password": "NuevaClave99"})
    assert auth_client.get("/tasks", headers=JSON).status_code == 401


def test_route_level_throttling_is_silent(app, client, user):
    bodies = [client.post("/forgot-password", json={"email": "ana@example.com"}).get_json() for _ in range(5)]
    assert all(b == bodies[0] for b in bodies)
    assert len(_sent(app)) == 3


def test_forgot_password_redirects_when_already_logged_in(auth_client):
    r = auth_client.get("/forgot-password")
    assert r.status_code == 302 and r.headers["Location"].endswith("/tasks")


def test_csrf_enforced_on_recovery_posts(csrf_client):
    for path in ("/forgot-password", "/reset-password/abc"):
        r = csrf_client.post(path, json={})
        assert r.status_code == 400 and r.get_json()["code"] == "CSRF_ERROR"
