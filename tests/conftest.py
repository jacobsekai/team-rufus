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
        self.users[user["email"]] = user


@pytest.fixture
def repository():
    return InMemoryExpressionsOfInterestRepository()


@pytest.fixture
def users_repository():
    return InMemoryUsersRepository()


@pytest.fixture
def client(repository, users_repository):
    app = create_app(
        {"TESTING": True},
        repository=repository,
        users_repository=users_repository,
    )
    return app.test_client()

