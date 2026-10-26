"""Shared pytest fixtures."""

import pytest

from backend import create_app
from backend.repositories import DuplicateRecordError


class InMemoryExpressionsOfInterestRepository:
    """Small test double with the same method used by the real repository."""

    def __init__(self):
        self.records = []

    def save(self, record):
        self.records.append(record)


class InMemoryUsersRepository:
    """Test double that enforces unique emails like the DynamoDB condition."""

    def __init__(self):
        self.users = {}

    def create_user(self, user):
        if user["email"] in self.users:
            raise DuplicateRecordError("An account with this email already exists.")
        self.users[user["email"]] = dict(user)

    def get_user(self, email):
        user = self.users.get(email)
        return dict(user) if user else None

    def delete_user(self, email):
        self.users.pop(email, None)

    def update_full_name(self, email, full_name, updated_at):
        self.users[email]["full_name"] = full_name
        self.users[email]["updated_at"] = updated_at

    def change_email(self, user, new_email, full_name, updated_at):
        if new_email in self.users:
            raise DuplicateRecordError("An account with this email already exists.")
        new_user = {**self.users.pop(user["email"]), "email": new_email,
                    "full_name": full_name, "updated_at": updated_at}
        self.users[new_email] = new_user
        return dict(new_user)

    def change_password(self, email, password_hash, updated_at):
        user = self.users[email]
        user["password_hash"] = password_hash
        user["updated_at"] = updated_at
        user["session_version"] = user.get("session_version", 0) + 1
        return user["session_version"]

    def record_failed_login(self, email):
        user = self.users[email]
        user["failed_login_count"] = user.get("failed_login_count", 0) + 1
        return user["failed_login_count"]

    def lock_user(self, email, locked_until):
        self.users[email]["locked_until"] = locked_until
        self.users[email]["failed_login_count"] = 0

    def set_saved_items(self, email, saved, updated_at):
        self.users[email]["saved"] = dict(saved)
        self.users[email]["updated_at"] = updated_at

    def clear_failed_logins(self, email):
        self.users[email]["failed_login_count"] = 0
        self.users[email].pop("locked_until", None)


class InMemorySessionsRepository:
    def __init__(self):
        self.sessions = {}

    def create_session(self, session):
        self.sessions[session["token_hash"]] = dict(session)

    def get_session(self, token_hash):
        session = self.sessions.get(token_hash)
        return dict(session) if session else None

    def delete_session(self, token_hash):
        self.sessions.pop(token_hash, None)

    def set_email(self, token_hash, email):
        self.sessions[token_hash]["email"] = email

    def set_session_version(self, token_hash, session_version):
        self.sessions[token_hash]["session_version"] = session_version


class FakeContentStore:
    """Returns a predictable URL instead of a real pre-signed S3 link."""

    def download_url(self, key):
        return f"https://downloads.example.com/{key}?signature=test"


TEST_CATALOGUE = [
    {
        "id": "public-guide",
        "title": "Public guide",
        "description": "Anyone can download this.",
        "file": "guides/public-guide.txt",
        "requires_login": False,
    },
    {
        "id": "members-guide",
        "title": "Members guide",
        "description": "Sign-in needed.",
        "file": "members/members-guide.txt",
        "requires_login": True,
    },
]


@pytest.fixture
def repository():
    return InMemoryExpressionsOfInterestRepository()


@pytest.fixture
def users_repository():
    return InMemoryUsersRepository()


@pytest.fixture
def sessions_repository():
    return InMemorySessionsRepository()


@pytest.fixture
def make_app(repository, users_repository, sessions_repository):
    """Build an app wired to the in-memory test doubles.

    Keyword arguments replace individual dependencies, for example
    ``make_app(content_store=None)``.
    """

    def _make_app(**overrides):
        dependencies = {
            "repository": repository,
            "users_repository": users_repository,
            "sessions_repository": sessions_repository,
            "content_store": FakeContentStore(),
            "content_catalogue": TEST_CATALOGUE,
        }
        dependencies.update(overrides)
        return create_app({"TESTING": True}, **dependencies)

    return _make_app


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()
