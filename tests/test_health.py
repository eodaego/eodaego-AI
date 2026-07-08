def test_health_check_returns_ok_when_db_reachable(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}
