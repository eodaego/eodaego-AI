def test_create_and_list_schedule_config(client):
    create_response = client.post(
        "/api/v1/crawling/schedules",
        json={
            "job_id": "crawl_congestion",
            "trigger_type": "interval",
            "trigger_config": "hours=2",
            "is_active": True,
        },
        headers={"X-Internal-Api-Key": "test-key"},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["job_id"] == "crawl_congestion"

    list_response = client.get(
        "/api/v1/crawling/schedules", headers={"X-Internal-Api-Key": "test-key"}
    )
    assert list_response.status_code == 200
    assert any(s["id"] == created["id"] for s in list_response.json())


def test_update_and_delete_schedule_config(client):
    created = client.post(
        "/api/v1/crawling/schedules",
        json={
            "job_id": "crawl_catalog",
            "trigger_type": "interval",
            "trigger_config": "hours=2160",
            "is_active": True,
        },
        headers={"X-Internal-Api-Key": "test-key"},
    ).json()

    update_response = client.patch(
        f"/api/v1/crawling/schedules/{created['id']}",
        json={"is_active": False},
        headers={"X-Internal-Api-Key": "test-key"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False

    delete_response = client.delete(
        f"/api/v1/crawling/schedules/{created['id']}", headers={"X-Internal-Api-Key": "test-key"}
    )
    assert delete_response.status_code == 204
