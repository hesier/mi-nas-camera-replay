from types import SimpleNamespace


def test_rebuild_index_returns_day_scope_payload(client, monkeypatch):
    captured = {}

    def fake_run_index_job(session, root=None, target_day=None):
        captured["root"] = root
        captured["target_day"] = target_day
        return SimpleNamespace(id=12)

    monkeypatch.setattr("app.api.index_jobs.run_index_job", fake_run_index_job)

    response = client.post("/api/index/rebuild", params={"day": "2026-03-20"})

    assert response.status_code == 200
    assert response.json() == {
        "accepted": True,
        "jobId": 12,
        "scope": "day",
        "day": "2026-03-20",
    }
    assert captured == {"root": None, "target_day": "2026-03-20"}


def test_rebuild_index_returns_all_scope_payload(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.index_jobs.run_index_job",
        lambda session, root=None, target_day=None: SimpleNamespace(id=23),
    )

    response = client.post("/api/index/rebuild")

    assert response.status_code == 200
    assert response.json() == {
        "accepted": True,
        "jobId": 23,
        "scope": "all",
        "day": None,
    }
