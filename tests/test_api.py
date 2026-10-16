"""API behaviour tests."""


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_expression_of_interest(client, repository):
    response = client.post(
        "/api/expressions-of-interest",
        json={
            "full_name": "Example Student",
            "email": "Student@example.com",
            "school": "Example School",
            "interests": ["Digital", "Engineering"],
            "consent": True,
        },
    )

    assert response.status_code == 201
    result = response.get_json()
    assert result["status"] == "received"
    assert result["id"]

    assert len(repository.records) == 1
    saved = repository.records[0]
    assert saved["email"] == "student@example.com"
    assert saved["consent"] is True
    assert saved["created_at"].endswith("Z")


def test_rejects_unknown_fields(client, repository):
    response = client.post(
        "/api/expressions-of-interest",
        json={
            "full_name": "Example Student",
            "email": "student@example.com",
            "consent": True,
            "unexpected": "not accepted",
        },
    )

    assert response.status_code == 400
    assert "Unknown fields: unexpected." in response.get_json()["details"]
    assert repository.records == []


def test_requires_consent(client, repository):
    response = client.post(
        "/api/expressions-of-interest",
        json={
            "full_name": "Example Student",
            "email": "student@example.com",
            "consent": False,
        },
    )

    assert response.status_code == 400
    assert "consent must be true." in response.get_json()["details"]
    assert repository.records == []


def test_requires_json(client):
    response = client.post(
        "/api/expressions-of-interest",
        data="not-json",
    )

    assert response.status_code == 415

