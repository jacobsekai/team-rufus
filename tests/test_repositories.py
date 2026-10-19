"""Check the exact DynamoDB requests the repositories make."""

from decimal import Decimal

from botocore.exceptions import ClientError
import pytest

from backend.repositories import RepositoryError, SessionsRepository, UsersRepository


class StubTable:
    """Records every call and returns a canned response."""

    def __init__(self, response=None, error_code=None):
        self.response = response or {}
        self.error_code = error_code
        self.calls = []

    def _record(self, name, kwargs):
        self.calls.append((name, kwargs))
        if self.error_code:
            raise ClientError({"Error": {"Code": self.error_code, "Message": "stub"}}, name)
        return self.response

    def put_item(self, **kwargs):
        return self._record("put_item", kwargs)

    def get_item(self, **kwargs):
        return self._record("get_item", kwargs)

    def delete_item(self, **kwargs):
        return self._record("delete_item", kwargs)

    def update_item(self, **kwargs):
        return self._record("update_item", kwargs)


def test_get_user_uses_consistent_read():
    table = StubTable(response={"Item": {"email": "a@example.com"}})

    assert UsersRepository(table).get_user("a@example.com") == {"email": "a@example.com"}
    assert table.calls == [
        ("get_item", {"Key": {"email": "a@example.com"}, "ConsistentRead": True})
    ]


def test_get_missing_user_returns_none():
    assert UsersRepository(StubTable(response={})).get_user("a@example.com") is None


def test_record_failed_login_is_an_atomic_increment():
    table = StubTable(response={"Attributes": {"failed_login_count": Decimal(3)}})

    assert UsersRepository(table).record_failed_login("a@example.com") == 3
    name, kwargs = table.calls[0]
    assert name == "update_item"
    assert kwargs["UpdateExpression"] == "ADD failed_login_count :one"
    assert kwargs["ConditionExpression"] == "attribute_exists(email)"


def test_lock_and_clear_failed_logins():
    table = StubTable()
    repository = UsersRepository(table)

    repository.lock_user("a@example.com", 1234)
    repository.clear_failed_logins("a@example.com")

    assert table.calls[0][1]["ExpressionAttributeValues"] == {":until": 1234, ":zero": 0}
    assert table.calls[1][1]["UpdateExpression"] == (
        "SET failed_login_count = :zero REMOVE locked_until"
    )


def test_delete_user():
    table = StubTable()
    UsersRepository(table).delete_user("a@example.com")

    assert table.calls == [("delete_item", {"Key": {"email": "a@example.com"}})]


def test_session_repository_calls():
    table = StubTable(response={"Item": {"token_hash": "abc"}})
    repository = SessionsRepository(table)

    repository.create_session({"token_hash": "abc"})
    assert repository.get_session("abc") == {"token_hash": "abc"}
    repository.delete_session("abc")

    assert [name for name, _ in table.calls] == ["put_item", "get_item", "delete_item"]
    assert table.calls[0][1]["ConditionExpression"] == "attribute_not_exists(token_hash)"


@pytest.mark.parametrize(
    "call",
    [
        lambda r: r.get_user("a@example.com"),
        lambda r: r.delete_user("a@example.com"),
        lambda r: r.record_failed_login("a@example.com"),
    ],
)
def test_aws_errors_become_repository_errors(call):
    repository = UsersRepository(StubTable(error_code="InternalServerError"))

    with pytest.raises(RepositoryError):
        call(repository)
