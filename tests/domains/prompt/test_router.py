def test_create_and_list_prompt_template(client):
    create_response = client.post(
        "/api/v1/prompts",
        json={"name": "default", "template_text": "hello {name}", "is_active": True},
        headers={"X-Internal-Api-Key": "test-key"},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "default"
    assert created["is_active"] is True

    list_response = client.get("/api/v1/prompts", headers={"X-Internal-Api-Key": "test-key"})

    assert list_response.status_code == 200
    assert any(p["id"] == created["id"] for p in list_response.json())


def test_update_and_delete_prompt_template(client):
    created = client.post(
        "/api/v1/prompts",
        json={"name": "to-update", "template_text": "v1", "is_active": True},
        headers={"X-Internal-Api-Key": "test-key"},
    ).json()

    update_response = client.patch(
        f"/api/v1/prompts/{created['id']}",
        json={"template_text": "v2"},
        headers={"X-Internal-Api-Key": "test-key"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["template_text"] == "v2"

    delete_response = client.delete(
        f"/api/v1/prompts/{created['id']}", headers={"X-Internal-Api-Key": "test-key"}
    )
    assert delete_response.status_code == 204

    list_response = client.get("/api/v1/prompts", headers={"X-Internal-Api-Key": "test-key"})
    assert all(p["id"] != created["id"] for p in list_response.json())


def test_prompt_endpoints_reject_wrong_internal_api_key(client):
    response = client.post(
        "/api/v1/prompts",
        json={"name": "x", "template_text": "y", "is_active": True},
        headers={"X-Internal-Api-Key": "wrong-key"},
    )

    assert response.status_code == 401
