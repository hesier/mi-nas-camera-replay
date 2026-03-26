def test_list_cameras_returns_sorted_configured_channels(client, settings_override):
    response = client.get("/api/cameras")

    assert response.status_code == 200
    assert response.json() == [
        {"cameraNo": 1, "label": "通道 1"},
        {"cameraNo": 3, "label": "通道 3"},
    ]
