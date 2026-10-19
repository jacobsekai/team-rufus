"""Health and expression-of-interest API tests."""

import pytest


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
            "customer_type": "student",
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
    assert saved["customer_type"] == "student"
    assert saved["interests"] == ["Digital", "Engineering"]
    assert saved["consent"] is True
    assert saved["created_at"].endswith("Z")


def test_rejects_unknown_fields(client, repository):
    response = client.post(
        "/api/expressions-of-interest",
        json={
            "full_name": "Example Student",
            "email": "student@example.com",
            "customer_type": "student",
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
            "customer_type": "student",
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



VALID_INTEREST = {
    "full_name": "Example Parent",
    "email": "parent@example.com",
    "customer_type": "parent_carer",
    "consent": True,
}


@pytest.mark.parametrize("customer_type", ["student", "school", "parent_carer", "other"])
def test_accepts_each_customer_type(client, repository, customer_type):
    response = client.post(
        "/api/expressions-of-interest",
        json={**VALID_INTEREST, "customer_type": customer_type},
    )

    assert response.status_code == 201
    assert repository.records[0]["customer_type"] == customer_type


@pytest.mark.parametrize("customer_type", [None, "", "teacher", "Student", 1])
def test_rejects_invalid_customer_type(client, repository, customer_type):
    payload = {**VALID_INTEREST, "customer_type": customer_type}
    if customer_type is None:
        del payload["customer_type"]

    response = client.post("/api/expressions-of-interest", json=payload)

    assert response.status_code == 400
    assert (
        "customer_type must be one of: student, school, parent_carer, other."
        in response.get_json()["details"]
    )
    assert repository.records == []


def test_interests_are_normalised_and_deduplicated(client, repository):
    response = client.post(
        "/api/expressions-of-interest",
        json={**VALID_INTEREST, "interests": [" digital ", "FINANCE", "Digital"]},
    )

    assert response.status_code == 201
    assert repository.records[0]["interests"] == ["Digital", "Finance"]


@pytest.mark.parametrize(
    "interests",
    [["Digital", "Cooking"], "Digital", [1], [""]],
)
def test_rejects_interests_outside_placement_areas(client, repository, interests):
    response = client.post(
        "/api/expressions-of-interest",
        json={**VALID_INTEREST, "interests": interests},
    )

    assert response.status_code == 400
    assert repository.records == []


def test_missing_interests_defaults_to_empty_list(client, repository):
    response = client.post("/api/expressions-of-interest", json=VALID_INTEREST)

    assert response.status_code == 201
    assert repository.records[0]["interests"] == []
