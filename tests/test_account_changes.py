"""Changing account details and password, and the session rules behind them."""

import pytest

from backend.repositories import RepositoryError


PASSWORD = "correct horse battery 9!"
NEW_PASSWORD = "a brand new password 7?"
EMAIL = "member@example.com"
NEW_EMAIL = "renamed@example.com"
NAME = "Example Member"


def _sign_up(client, email=EMAIL, password=PASSWORD, full_name=NAME):
    response = client.post(
        "/api/users",
        json={"full_name": full_name, "email": email, "password": password, "accept_terms": True},
    )
    assert response.status_code == 201
    return response.get_json()


def _login(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/login", json={"email": email, "password": password})


def _update(client, **overrides):
    body = {"full_name": NAME, "email": EMAIL, "current_password": PASSWORD}
    body.update(overrides)
    return client.post("/api/users/me/update", json=body)


def _change_password(client, current=PASSWORD, new=NEW_PASSWORD):
    return client.post(
        "/api/users/me/password", json={"current_password": current, "new_password": new}
    )


@pytest.fixture
def member(client):
    """A signed-up member; ``client`` stays signed in."""

    return _sign_up(client)


# ---- Edit details ---------------------------------------------------------

def test_change_name_only(client, member, users_repository):
    response = _update(client, full_name="  New Name  ")

    assert response.status_code == 200
    assert response.get_json() == {
        "id": member["id"],
        "email": EMAIL,
        "full_name": "New Name",
        "created_at": member["created_at"],
    }
    assert client.get("/api/users/me").get_json()["full_name"] == "New Name"
    assert users_repository.users[EMAIL]["updated_at"] >= member["created_at"]


def test_change_email_moves_the_account(client, member, users_repository):
    client.post("/api/users/me/saved", json={"type": "subject", "id": "digital"})

    response = _update(client, email="  Renamed@Example.COM ")

    assert response.status_code == 200
    assert response.get_json()["email"] == NEW_EMAIL
    assert response.get_json()["id"] == member["id"]
    assert EMAIL not in users_repository.users
    # This browser stays signed in and keeps its saved items.
    assert client.get("/api/users/me").get_json()["email"] == NEW_EMAIL
    assert [item["id"] for item in client.get("/api/users/me/saved").get_json()["items"]] == ["digital"]

    client.post("/api/logout")
    assert _login(client).status_code == 401
    assert _login(client, email=NEW_EMAIL).status_code == 200


def test_change_email_ends_other_sessions(app, client, member):
    other = app.test_client()
    _login(other)

    assert _update(client, email=NEW_EMAIL).status_code == 200
    assert other.get("/api/users/me").status_code == 401


def test_change_email_to_a_registered_email_is_refused(app, client, member, users_repository):
    _sign_up(app.test_client(), email="taken@example.com")

    response = _update(client, email="taken@example.com", full_name="Changed")

    assert response.status_code == 409
    assert response.get_json()["error"] == "An account with this email already exists."
    assert users_repository.users[EMAIL]["full_name"] == NAME
    assert users_repository.users["taken@example.com"]["id"] != member["id"]


def test_update_with_wrong_password_changes_nothing(client, member, users_repository):
    response = _update(client, full_name="Changed", email=NEW_EMAIL, current_password="wrong password 1!")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Password is incorrect."
    assert users_repository.users[EMAIL]["full_name"] == NAME
    assert NEW_EMAIL not in users_repository.users


@pytest.mark.parametrize(
    "body",
    [
        {"full_name": NAME, "email": EMAIL},
        {"full_name": "", "email": EMAIL, "current_password": PASSWORD},
        {"full_name": "x" * 101, "email": EMAIL, "current_password": PASSWORD},
        {"full_name": NAME, "email": "not-an-email", "current_password": PASSWORD},
        {"email": EMAIL, "current_password": PASSWORD},
        {"full_name": NAME, "email": EMAIL, "current_password": PASSWORD, "id": "someone-else"},
        {"full_name": NAME, "email": EMAIL, "current_password": PASSWORD, "password_hash": "x"},
        ["not", "an", "object"],
    ],
)
def test_update_validation(client, member, users_repository, body):
    response = client.post("/api/users/me/update", json=body)

    assert response.status_code == 400
    assert response.get_json()["error"] == "Validation failed."
    assert users_repository.users[EMAIL]["full_name"] == NAME


# ---- Change password ------------------------------------------------------

def test_change_password(client, member):
    response = _change_password(client)

    assert response.status_code == 200
    assert response.get_json() == {"status": "updated"}
    # This browser stays signed in.
    assert client.get("/api/users/me").status_code == 200

    client.post("/api/logout")
    assert _login(client).status_code == 401
    assert _login(client, password=NEW_PASSWORD).status_code == 200


def test_change_password_ends_other_sessions(app, client, member):
    other = app.test_client()
    _login(other)

    assert _change_password(client).status_code == 200
    assert other.get("/api/users/me").status_code == 401
    # Signing in again with the new password works on the other device.
    assert _login(other, password=NEW_PASSWORD).status_code == 200
    assert other.get("/api/users/me").status_code == 200


def test_change_password_twice(client, member):
    assert _change_password(client).status_code == 200
    assert _change_password(client, current=NEW_PASSWORD, new="third password here 3#").status_code == 200
    assert client.get("/api/users/me").status_code == 200


def test_change_password_with_wrong_current_password(client, member, users_repository):
    before = users_repository.users[EMAIL]["password_hash"]

    response = _change_password(client, current="wrong password 1!")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Password is incorrect."
    assert users_repository.users[EMAIL]["password_hash"] == before


def test_change_password_to_the_same_password(client, member):
    response = _change_password(client, new=PASSWORD)

    assert response.status_code == 400
    assert response.get_json()["error"] == "Your new password must be different from your current one."


@pytest.mark.parametrize(
    "new_password",
    ["short 1!", "no numbers here at all!", "no symbols here 123", "x1!" * 43, None],
)
def test_change_password_applies_the_sign_up_rule(client, member, new_password):
    response = client.post(
        "/api/users/me/password",
        json={"current_password": PASSWORD, "new_password": new_password},
    )

    assert response.status_code == 400
    assert response.get_json()["details"] == [
        "new_password must be 12 to 128 characters and include a number and a symbol."
    ]


def test_change_password_rejects_unknown_fields(client, member):
    response = client.post(
        "/api/users/me/password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD, "email": NEW_EMAIL},
    )

    assert response.status_code == 400


# ---- Shared rules -----------------------------------------------------------

@pytest.mark.parametrize("path", ["/api/users/me/update", "/api/users/me/password"])
def test_signed_out_users_are_refused(client, path):
    assert client.post(path, json={}).status_code == 401


def test_session_does_not_follow_a_released_email(app, client, member):
    """A session left on another device must not open the account of whoever
    registers the old email next."""

    other = app.test_client()
    _login(other)
    assert _update(client, email=NEW_EMAIL).status_code == 200

    _sign_up(app.test_client(), email=EMAIL, full_name="Someone Else")

    assert other.get("/api/users/me").status_code == 401


def test_session_does_not_follow_a_deleted_account(app, client, member):
    other = app.test_client()
    _login(other)
    client.post("/api/users/me/delete", json={"password": PASSWORD})

    _sign_up(app.test_client(), full_name="Someone Else")

    assert other.get("/api/users/me").status_code == 401


def test_sessions_without_a_user_id_are_refused(client, member, sessions_repository):
    for session in sessions_repository.sessions.values():
        del session["user_id"]

    assert client.get("/api/users/me").status_code == 401


def test_database_failures_return_503(client, member, users_repository):
    def fail(*args, **kwargs):
        raise RepositoryError("The database request failed.")

    users_repository.update_full_name = fail
    users_repository.change_email = fail
    users_repository.change_password = fail

    assert _update(client, full_name="Changed").status_code == 503
    assert _update(client, email=NEW_EMAIL).status_code == 503
    assert _change_password(client).status_code == 503


def test_session_update_failure_still_saves_the_change(client, member, sessions_repository, users_repository):
    def fail(*args, **kwargs):
        raise RepositoryError("The database request failed.")

    sessions_repository.set_email = fail

    assert _update(client, email=NEW_EMAIL).status_code == 200
    assert NEW_EMAIL in users_repository.users
    # The session still points at the old email, so this browser must sign in again.
    assert client.get("/api/users/me").status_code == 401
