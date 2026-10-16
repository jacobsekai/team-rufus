"""Shared pytest fixtures."""

import pytest

from backend import create_app


class InMemoryExpressionsOfInterestRepository:
    """Small test double with the same method used by the real repository."""

    def __init__(self):
        self.records = []

    def save(self, record):
        self.records.append(record)


@pytest.fixture
def repository():
    return InMemoryExpressionsOfInterestRepository()


@pytest.fixture
def client(repository):
    app = create_app({"TESTING": True}, repository=repository)
    return app.test_client()

