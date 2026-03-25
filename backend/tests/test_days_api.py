from app.models import DaySummary


def test_get_days_returns_summaries_in_desc_order(client, sqlite_session):
    sqlite_session.add_all(
        [
            DaySummary(
                day="2026-03-16",
                first_segment_at="2026-03-16T00:05:00+08:00",
                last_segment_at="2026-03-16T23:55:00+08:00",
                total_segment_count=10,
                total_recorded_sec=3600.0,
                total_gap_sec=120.0,
                has_warning=False,
                updated_at="2026-03-24T00:00:00+08:00",
            ),
            DaySummary(
                day="2026-03-17",
                first_segment_at="2026-03-17T00:00:00+08:00",
                last_segment_at="2026-03-17T23:59:59+08:00",
                total_segment_count=12,
                total_recorded_sec=7200.0,
                total_gap_sec=40.0,
                has_warning=True,
                updated_at="2026-03-24T00:00:00+08:00",
            ),
        ]
    )
    sqlite_session.commit()

    response = client.get("/api/days")

    assert response.status_code == 200
    assert response.json() == [
        {
            "day": "2026-03-17",
            "segmentCount": 12,
            "recordedSeconds": 7200.0,
            "gapSeconds": 40.0,
            "hasWarning": True,
            "firstSegmentAt": "2026-03-17T00:00:00+08:00",
            "lastSegmentAt": "2026-03-17T23:59:59+08:00",
        },
        {
            "day": "2026-03-16",
            "segmentCount": 10,
            "recordedSeconds": 3600.0,
            "gapSeconds": 120.0,
            "hasWarning": False,
            "firstSegmentAt": "2026-03-16T00:05:00+08:00",
            "lastSegmentAt": "2026-03-16T23:55:00+08:00",
        },
    ]
