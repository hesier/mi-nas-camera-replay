def test_days_api_includes_cors_header_for_frontend_origin(client):
    response = client.get(
        "/api/days",
        headers={"Origin": "http://127.0.0.1:4173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:4173"


def test_cors_preflight_allows_frontend_origin(client):
    response = client.options(
        "/api/days",
        headers={
            "Origin": "http://127.0.0.1:4173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:4173"
