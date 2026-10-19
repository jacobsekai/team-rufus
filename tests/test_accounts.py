"""Sign-in, sign-out, session, and "my account" tests."""

import hashlib

import pytest

from backend.accounts import (
    LOCKOUT_SECONDS,
    MAX_FAILED_LOGINS,
    SESSION_COOKIE_NAME,
)
from backend.repositories import RepositoryError


PASSWORD = "correct horse battery"
EMAIL = "member@example.com"


@pytest.fixture
def signed_up(client):
    """Create an account, then sign out so each test starts signed out."""

    response = client.post(
        "/api/users",
        json={"full_name": "Example Member", "email": EMAIL, "password": PASSWORD},
    )
    assert response.status_code == 201
    client.post("/api/logout")
    return response.get_json()


def _login(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/login", json={"email": email, "password": password})


def _session_cookie_header(response):
    return next(
        header
        for header in response.headers.getlist("Set-Cookie")
        if header.startswith(SESSION_COOKIE_NAME + "=")
    )


def test_signup_signs_the_user_in(client):
    response = client.post(
        "/api/users",
        json={"full_name": "New Member", "email": "new@example.com", "password": PASSWORD},
    )

    assert response.status_code == 201
    assert client.get("/api/users/me").get_json()["email"] == "new@example.com"


def test_login_sets_secure_session_cookie(client, signed_up):
    response = _login(client)

    assert response.status_code == 200
    assert response.get_json()["status"] == "signed_in"
    cookie = _session_cookie_header(response)
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=Strict" in cookie
    assert "Path=/" in cookie


def test_login_email_is_case_insensitive(client, signed_up):
    assert _login(client, email="  MEMBER@Example.com ").status_code == 200


def test_only_a_hash_of_the_session_token_is_stored(client, signed_up, sessions_repository):
    _login(client)
    token = client.get_cookie(SESSION_COOKIE_NAME).value

    assert token not in sessions_repository.sessions
    assert hashlib.sha256(token.encode()).hexdigest() in sessions_repository.sessions


def test_me_returns_profile_without_secrets(client, signed_up):
    _login(client)
    response = client.get("/api/users/me")

    assert response.status_code == 200
    assert response.get_json() == {
        "id": signed_up["id"],
        "email": EMAIL,
        "full_name": "Example Member",
        "created_at": response.get_json()["created_at"],
    }


def test_me_requires_sign_in(client):
    response = client.get("/api/users/me")

    assert response.status_code == 401
    assert response.get_json() == {"error": "You need to sign in."}


def test_unknown_session_token_is_rejected_and_cleared(client):
    client.set_cookie(SESSION_COOKIE_NAME, "made-up-token")
    response = client.get("/api/users/me")

    assert response.status_code == 401
    assert client.get_cookie(SESSION_COOKIE_NAME) is None


@pytest.mark.parametrize(
    "email, password",
    [(EMAIL, "wrong password here"), ("nobody@example.com", PASSWORD)],
)
def test_wrong_email_or_password_gives_the_same_answer(client, signed_up, email, password):
    response = _login(client, email=email, password=password)

    assert response.status_code == 401
    assert response.get_json() == {"error": "Email or password is incorrect."}
    assert client.get_cookie(SESSION_COOKIE_NAME) is None


@pytest.mark.parametrize(
    "payload",
    [{}, {"email": EMAIL}, {"password": PASSWORD}, {"email": EMAIL, "password": ""},
     {"email": EMAIL, "password": PASSWORD, "remember_me": True}, ["not", "an", "object"]],
)
def test_login_validation(client, payload):
    assert client.post("/api/login", json=payload).status_code == 400


def test_login_requires_json(client):
    assert client.post("/api/login", data="email=x").status_code == 415


def test_account_locks_after_repeated_failures(client, signed_up, users_repository):
    for _ in range(MAX_FAILED_LOGINS):
        assert _login(client, password="wrong password here").status_code == 401

    response = _login(client)  # correct password, but now locked

    assert response.status_code == 429
    assert 0 < int(response.headers["Retry-After"]) <= LOCKOUT_SECONDS
    assert users_repository.users[EMAIL]["locked_until"]


def test_lock_expires(client, signed_up, users_repository):
    users_repository.users[EMAIL]["locked_until"] = 1  # long in the past

    assert _login(client).status_code == 200
    assert "locked_until" not in users_repository.users[EMAIL]


def test_successful_login_resets_failure_count(client, signed_up, users_repository):
    _login(client, password="wrong password here")
    assert users_repository.users[EMAIL]["failed_login_count"] == 1

    _login(client)

    assert users_repository.users[EMAIL]["failed_login_count"] == 0


def test_logout_ends_the_session(client, signed_up, sessions_repository):
    _login(client)
    response = client.post("/api/logout")

    assert response.status_code == 200
    assert sessions_repository.sessions == {}
    assert client.get("/api/users/me").status_code == 401


def test_logout_when_not_signed_in_is_harmless(client):
    assert client.post("/api/logout").status_code == 200


def test_expired_session_is_rejected(client, signed_up, sessions_repository):
    _login(client)
    for session in sessions_repository.sessions.values():
        session["expires_at"] = 1

    assert client.get("/api/users/me").status_code == 401
    assert sessions_repository.sessions == {}


def test_session_of_deleted_user_is_rejected(client, signed_up, users_repository):
    _login(client)
    users_repository.users.clear()

    assert client.get("/api/users/me").status_code == 401


def test_delete_account_requires_correct_password(client, signed_up, users_repository):
    _login(client)
    response = client.delete("/api/users/me", json={"password": "wrong password here"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "Password is incorrect."}
    assert EMAIL in users_repository.users


def test_delete_account_requires_sign_in(client, signed_up, users_repository):
    response = client.delete("/api/users/me", json={"password": PASSWORD})

    assert response.status_code == 401
    assert EMAIL in users_repository.users


def test_delete_account_removes_user_and_session(
    client, signed_up, users_repository, sessions_repository
):
    _login(client)
    response = client.delete("/api/users/me", json={"password": PASSWORD})

    assert response.status_code == 200
    assert response.get_json() == {"status": "deleted"}
    assert EMAIL not in users_repository.users
    assert sessions_repository.sessions == {}
    assert _login(client).status_code == 401


def test_login_returns_503_when_database_fails(make_app):
    class FailingUsersRepository:
        def get_user(self, email):
            raise RepositoryError("The database request failed.")

    client = make_app(users_repository=FailingUsersRepository()).test_client()

    assert _login(client).status_code == 503


def test_api_never_returns_403(client, signed_up):
    """CloudFront turns any 403 into the Midway redirect page, so the API must
    use other status codes for its own errors."""

    _login(client)
    responses = [
        client.delete("/api/users/me", json={"password": "wrong password here"}),
        client.post("/api/login", json={"email": EMAIL, "password": "wrong"}),
        client.get("/api/content/members-guide/download"),
    ]

    assert all(response.status_code != 403 for response in responses)
