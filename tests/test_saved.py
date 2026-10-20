"""Saved subjects and guides tests."""

import pytest

from backend.saved import MAX_SAVED_ITEMS


PASSWORD = "correct horse battery 9!"
EMAIL = "member@example.com"


@pytest.fixture
def signed_in(client):
    response = client.post(
        "/api/users",
        json={"full_name": "Example Member", "email": EMAIL, "password": PASSWORD,
              "accept_terms": True},
    )
    assert response.status_code == 201


def _save(client, item_type, item_id):
    return client.post("/api/users/me/saved", json={"type": item_type, "id": item_id})


def test_subjects_list(client):
    response = client.get("/api/subjects")

    assert response.status_code == 200
    assert response.get_json() == {"subjects": [
        {"id": "digital", "name": "Digital"},
        {"id": "business", "name": "Business"},
        {"id": "media", "name": "Media"},
        {"id": "finance", "name": "Finance"},
        {"id": "engineering", "name": "Engineering"},
    ]}


@pytest.mark.parametrize("method, path", [
    ("get", "/api/users/me/saved"),
    ("post", "/api/users/me/saved"),
    ("post", "/api/users/me/saved/remove"),
])
def test_saved_items_need_sign_in(client, method, path):
    response = getattr(client, method)(path, json={"type": "subject", "id": "digital"})

    assert response.status_code == 401


def test_new_account_has_no_saved_items(client, signed_in):
    assert client.get("/api/users/me/saved").get_json() == {"items": []}


def test_save_and_list_items(client, signed_in, users_repository):
    first = _save(client, "subject", "digital")
    second = _save(client, "guide", "parents-guide")

    assert first.status_code == 201
    assert second.status_code == 201
    items = client.get("/api/users/me/saved").get_json()["items"]
    assert [(i["type"], i["id"]) for i in items] == [("guide", "parents-guide"), ("subject", "digital")]
    assert all(i["saved_at"].endswith("Z") for i in items)
    assert set(users_repository.users[EMAIL]["saved"]) == {"subject:digital", "guide:parents-guide"}


def test_saving_twice_is_harmless(client, signed_in):
    _save(client, "subject", "digital")
    again = _save(client, "subject", "digital")

    assert again.status_code == 200
    assert again.get_json()["status"] == "already_saved"
    assert len(again.get_json()["items"]) == 1


def test_remove_item(client, signed_in):
    _save(client, "subject", "digital")
    _save(client, "subject", "media")

    response = client.post("/api/users/me/saved/remove", json={"type": "subject", "id": "digital"})

    assert response.status_code == 200
    assert response.get_json()["status"] == "removed"
    assert [i["id"] for i in client.get("/api/users/me/saved").get_json()["items"]] == ["media"]


def test_removing_something_not_saved_is_harmless(client, signed_in):
    response = client.post("/api/users/me/saved/remove", json={"type": "guide", "id": "never-saved"})

    assert response.status_code == 200
    assert response.get_json()["status"] == "not_saved"


@pytest.mark.parametrize("payload, detail", [
    ({"type": "subject", "id": "cooking"}, "id must be one of: digital, business, media, finance, engineering."),
    ({"type": "subject", "id": "Digital"}, "id must be one of: digital, business, media, finance, engineering."),
    ({"type": "course", "id": "digital"}, "type must be one of: subject, guide."),
    ({"type": "guide", "id": "Has Spaces"}, "id must be 1 to 64 lowercase letters, numbers or dashes."),
    ({"type": "guide", "id": "x" * 65}, "id must be 1 to 64 lowercase letters, numbers or dashes."),
    ({"type": "guide", "id": "ok", "note": "x"}, "Unknown fields: note."),
])
def test_save_validation(client, signed_in, payload, detail):
    response = client.post("/api/users/me/saved", json=payload)

    assert response.status_code == 400
    assert detail in response.get_json()["details"]


def test_saved_items_limit(client, signed_in):
    for i in range(MAX_SAVED_ITEMS):
        assert _save(client, "guide", f"guide-{i}").status_code == 201

    response = _save(client, "guide", "one-too-many")

    assert response.status_code == 400
    assert response.get_json() == {"error": f"You can save up to {MAX_SAVED_ITEMS} items."}


def test_saved_items_are_private_to_each_user(client, signed_in):
    _save(client, "subject", "digital")
    client.post("/api/logout")
    client.post("/api/users", json={"full_name": "Someone Else", "email": "other@example.com",
                                    "password": PASSWORD, "accept_terms": True})

    assert client.get("/api/users/me/saved").get_json() == {"items": []}


def test_my_account_does_not_expose_saved_map_or_terms(client, signed_in):
    _save(client, "subject", "digital")

    body = client.get("/api/users/me").get_json()

    assert set(body) == {"id", "email", "full_name", "created_at"}
