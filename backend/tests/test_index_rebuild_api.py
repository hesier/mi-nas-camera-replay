from types import SimpleNamespace


def test_rebuild_index_returns_day_scope_payload(authenticated_client, monkeypatch):
    captured = {}

    def fake_enqueue_index_job(*, root=None, target_day=None, session_factory=None):
        captured["root"] = root
        captured["target_day"] = target_day
        captured["session_factory"] = session_factory
        return SimpleNamespace(id=12)

    monkeypatch.setattr("app.api.index_jobs.enqueue_index_job", fake_enqueue_index_job)

    response = authenticated_client.post("/api/index/rebuild", params={"day": "2026-03-20"})

    assert response.status_code == 200
    assert response.json() == {
        "accepted": True,
        "jobId": 12,
        "scope": "day",
        "day": "2026-03-20",
    }
    assert captured["root"] is None
    assert captured["target_day"] == "2026-03-20"
    assert captured["session_factory"] is not None


def test_rebuild_index_returns_all_scope_payload(authenticated_client, monkeypatch):
    monkeypatch.setattr(
        "app.api.index_jobs.enqueue_index_job",
        lambda root=None, target_day=None, session_factory=None: SimpleNamespace(id=23),
    )

    response = authenticated_client.post("/api/index/rebuild")

    assert response.status_code == 200
    assert response.json() == {
        "accepted": True,
        "jobId": 23,
        "scope": "all",
        "day": None,
    }
