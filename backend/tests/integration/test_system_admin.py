import app.core.security as security_module


def test_system_admin_endpoints_require_staff(client, alice_headers):
    # Provision Alice's user row first (lazy on first authenticated call).
    client.get("/api/v1/notifications", headers=alice_headers)

    forbidden = client.get("/api/v1/admin/system/overview", headers=alice_headers)
    assert forbidden.status_code == 403


def test_system_admin_overview_and_endpoints_work_for_staff(client, db_session, alice_headers, bob_headers, monkeypatch):
    # is_staff is re-synced from STAFF_EMAILS on every request (see
    # core/security.py), so granting it for a test means patching that
    # config rather than flipping the DB row directly.
    monkeypatch.setattr(security_module.settings, "staff_emails", "alice@example.com")
    client.get("/api/v1/notifications", headers=alice_headers)

    league = client.post("/api/v1/leagues", json={"name": "Staff League"}, headers=alice_headers).json()
    client.post("/api/v1/leagues/join", json={"invite_code": league["invite_code"]}, headers=bob_headers)
    client.post(f"/api/v1/leagues/{league['id']}/gameweeks/generate-next", headers=alice_headers)

    overview = client.get("/api/v1/admin/system/overview", headers=alice_headers)
    assert overview.status_code == 200
    body = overview.json()
    assert body["leagues_count"] >= 1
    assert body["matches_count"] >= 1
    assert body["open_gameweeks_count"] >= 1
    assert body["odds_provider"] == "mock"

    odds_health = client.get("/api/v1/admin/system/odds-health", headers=alice_headers)
    assert odds_health.status_code == 200
    assert any(row["matches_open"] > 0 for row in odds_health.json())

    model_versions = client.get("/api/v1/admin/system/model-versions", headers=alice_headers)
    assert model_versions.status_code == 200
    assert model_versions.json() == []  # nothing trained in this test DB

    failed_jobs = client.get("/api/v1/admin/system/failed-jobs", headers=alice_headers)
    assert failed_jobs.status_code == 200
    assert failed_jobs.json() == []
