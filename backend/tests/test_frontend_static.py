from pathlib import Path


def test_root_serves_built_frontend(client, monkeypatch, tmp_path):
    frontend_dist = tmp_path / "static"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<!doctype html><title>replay</title>", encoding="utf-8")
    (frontend_dist / "robots.txt").write_text("User-agent: *", encoding="utf-8")

    import app.main as app_main

    monkeypatch.setattr(app_main, "get_frontend_dist_dir", lambda: frontend_dist)
    app_main.configure_frontend(client.app)

    root_response = client.get("/")
    file_response = client.get("/robots.txt")
    spa_response = client.get("/replay")

    assert root_response.status_code == 200
    assert "replay" in root_response.text
    assert file_response.status_code == 200
    assert file_response.text == "User-agent: *"
    assert spa_response.status_code == 200
    assert "replay" in spa_response.text


def test_api_route_is_not_swallowed_by_frontend_fallback(client, monkeypatch, tmp_path):
    frontend_dist = tmp_path / "static"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<!doctype html><title>replay</title>", encoding="utf-8")

    import app.main as app_main

    monkeypatch.setattr(app_main, "get_frontend_dist_dir", lambda: frontend_dist)
    app_main.configure_frontend(client.app)

    response = client.get("/api/not-found")

    assert response.status_code == 404


def test_path_traversal_is_rejected_by_frontend_fallback(client, monkeypatch, tmp_path):
    frontend_dist = tmp_path / "static"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<!doctype html><title>replay</title>", encoding="utf-8")

    import app.main as app_main

    monkeypatch.setattr(app_main, "get_frontend_dist_dir", lambda: frontend_dist)
    app_main.configure_frontend(client.app)

    response = client.get("/%2E%2E/secret.txt")

    assert response.status_code == 404
