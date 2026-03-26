def test_list_cameras_returns_sorted_configured_channels(
    authenticated_client, settings_override
):
    response = authenticated_client.get("/api/cameras")

    assert response.status_code == 200
    assert response.json() == [
        {"cameraNo": 1, "label": "通道 1"},
        {"cameraNo": 3, "label": "通道 3"},
    ]


def test_list_cameras_requires_authentication(client):
    response = client.get("/api/cameras")

    assert response.status_code == 401
