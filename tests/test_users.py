"""User signup API tests."""

from botocore.exceptions import ClientError
import pytest
from werkzeug.security import check_password_hash

from backend.repositories import (
    DuplicateRecordError,
    RepositoryError,
    UsersRepository,
)


VALID_SIGNUP = {
    "full_name": "Example Student",
    "email": "Example.Student@example.com",
    "password": "correct horse battery 9!",
    "accept_terms": True,
}


def test_create_user(client, users_repository):
    response = client.post("/api/users", json=VALID_SIGNUP)

    assert response.status_code == 201
    result = response.get_json()
    assert result["status"] == "created"
    assert result["id"]
    assert result["email"] == "example.student@example.com"
    assert "password" not in result
    assert "password_hash" not in result

    saved = users_repository.users["example.student@example.com"]
    assert saved["full_name"] == "Example Student"
    assert saved["created_at"].endswith("Z")
    assert "password" not in saved


def test_password_is_hashed_not_stored_in_plain_text(client, users_repository):
    client.post("/api/users", json=VALID_SIGNUP)

    saved = users_repository.users["example.student@example.com"]
    assert saved["password_hash"] != VALID_SIGNUP["password"]
    assert saved["password_hash"].startswith("pbkdf2:sha256:600000$")
    assert check_password_hash(saved["password_hash"], VALID_SIGNUP["password"])


def test_rejects_duplicate_email_case_insensitively(client, users_repository):
    first = client.post("/api/users", json=VALID_SIGNUP)
    second = client.post(
        "/api/users",
        json={**VALID_SIGNUP, "email": "EXAMPLE.STUDENT@EXAMPLE.COM"},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert len(users_repository.users) == 1


@pytest.mark.parametrize(
    "password",
    [
        "short",
        "abc1!" + "x" * 6,       # 11 characters
        "abc1!" + "x" * 124,     # 129 characters
        "no number here!",       # no number
        "no symbol here 123",    # spaces do not count as symbols
        123456789012,
        None,
    ],
)
def test_rejects_invalid_password(client, users_repository, password):
    response = client.post(
        "/api/users", json={**VALID_SIGNUP, "password": password}
    )

    assert response.status_code == 400
    assert (
        "password must be 12 to 128 characters and include a number and a symbol."
        in response.get_json()["details"]
    )
    assert users_repository.users == {}


def test_validation_errors_do_not_echo_the_password(client):
    response = client.post(
        "/api/users",
        json={**VALID_SIGNUP, "email": "not-an-email", "password": "tooshort"},
    )

    assert response.status_code == 400
    assert "tooshort" not in response.get_data(as_text=True)


@pytest.mark.parametrize(
    "payload, expected_detail",
    [
        ({**VALID_SIGNUP, "email": "not-an-email"}, "email must be a valid email address."),
        ({**VALID_SIGNUP, "full_name": "   "}, "full_name must be between 1 and 100 characters."),
        ({**VALID_SIGNUP, "is_admin": True}, "Unknown fields: is_admin."),
    ],
)
def test_rejects_invalid_signup_fields(client, users_repository, payload, expected_detail):
    response = client.post("/api/users", json=payload)

    assert response.status_code == 400
    assert expected_detail in response.get_json()["details"]
    assert users_repository.users == {}


def test_signup_requires_json(client):
    response = client.post("/api/users", data="not-json")

    assert response.status_code == 415


def test_signup_returns_503_when_storage_fails(make_app):
    class FailingUsersRepository:
        def create_user(self, user):
            raise RepositoryError("Unable to save the record.")

    app = make_app(users_repository=FailingUsersRepository())
    response = app.test_client().post("/api/users", json=VALID_SIGNUP)

    assert response.status_code == 503
    assert response.get_json() == {"error": "The account could not be created."}


class StubTable:
    """Records put_item calls and optionally raises a DynamoDB error."""

    def __init__(self, error_code=None):
        self.error_code = error_code
        self.calls = []

    def put_item(self, **kwargs):
        self.calls.append(kwargs)
        if self.error_code:
            raise ClientError(
                {"Error": {"Code": self.error_code, "Message": "stub"}},
                "PutItem",
            )


def test_users_repository_writes_with_unique_email_condition():
    table = StubTable()
    UsersRepository(table).create_user({"email": "a@example.com"})

    assert table.calls == [
        {
            "Item": {"email": "a@example.com"},
            "ConditionExpression": "attribute_not_exists(email)",
        }
    ]


@pytest.mark.parametrize(
    "error_code, expected_error",
    [
        ("ConditionalCheckFailedException", DuplicateRecordError),
        ("ProvisionedThroughputExceededException", RepositoryError),
    ],
)
def test_users_repository_maps_dynamodb_errors(error_code, expected_error):
    repository = UsersRepository(StubTable(error_code=error_code))

    with pytest.raises(RepositoryError) as raised:
        repository.create_user({"email": "a@example.com"})

    # Exact type check: DuplicateRecordError is a subclass of RepositoryError.
    assert type(raised.value) is expected_error


@pytest.mark.parametrize("password", ["abc1!" + "x" * 7, "abc1!" + "x" * 123, "pässwörd 1 é€"])
def test_accepts_password_at_the_boundaries(client, password):
    response = client.post("/api/users", json={**VALID_SIGNUP, "password": password})

    assert response.status_code == 201


@pytest.mark.parametrize("accept_terms", [None, False, "true", 1])
def test_signup_requires_accepting_the_terms(client, users_repository, accept_terms):
    payload = {**VALID_SIGNUP, "accept_terms": accept_terms}
    if accept_terms is None:
        del payload["accept_terms"]

    response = client.post("/api/users", json=payload)

    assert response.status_code == 400
    assert "accept_terms must be true." in response.get_json()["details"]
    assert users_repository.users == {}


def test_signup_records_when_terms_were_accepted(client, users_repository):
    client.post("/api/users", json=VALID_SIGNUP)

    saved = users_repository.users["example.student@example.com"]
    assert saved["terms_accepted_at"] == saved["created_at"]
    assert saved["saved"] == {}
