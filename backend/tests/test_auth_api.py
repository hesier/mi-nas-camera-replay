def test_login_sets_session_cookie(client):
    response = client.post("/api/auth/login", json={"password": "secret-pass"})
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    assert "Set-Cookie" in response.headers
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=Lax" in response.headers["set-cookie"]


def test_unauthenticated_days_request_returns_401(client):
    response = client.get("/api/days", params={"camera": 1})
    assert response.status_code == 401


def test_login_rejects_wrong_password(client):
    response = client.post("/api/auth/login", json={"password": "wrong-pass"})
    assert response.status_code == 401


def test_auth_status_reflects_cookie_state(authenticated_client):
    response = authenticated_client.get("/api/auth/status")
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}


def test_logout_clears_cookie(authenticated_client):
    response = authenticated_client.post("/api/auth/logout")
    assert response.status_code == 200
    assert "Set-Cookie" in response.headers


def test_auth_status_is_false_without_cookie(client):
    response = client.get("/api/auth/status")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False}


def test_tampered_cookie_is_rejected(client):
    client.cookies.set("replay_session", "tampered")
    assert client.get("/api/days", params={"camera": 1}).status_code == 401
    assert client.get("/api/auth/status").json() == {"authenticated": False}
