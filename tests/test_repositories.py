"""Check the exact DynamoDB requests the repositories make."""

from decimal import Decimal

from botocore.exceptions import ClientError
import pytest

from backend.repositories import (
    DuplicateRecordError,
    RepositoryError,
    SessionsRepository,
    UsersRepository,
)


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


def test_set_saved_items_replaces_the_map():
    table = StubTable()
    UsersRepository(table).set_saved_items("a@example.com", {"subject:digital": "t"}, "now")

    name, kwargs = table.calls[0]
    assert name == "update_item"
    assert kwargs["UpdateExpression"] == "SET saved = :saved, updated_at = :updated_at"
    assert kwargs["ExpressionAttributeValues"] == {":saved": {"subject:digital": "t"}, ":updated_at": "now"}
    assert kwargs["ConditionExpression"] == "attribute_exists(email)"


class StubTransactionClient:
    def __init__(self, cancellation_codes=None):
        self.cancellation_codes = cancellation_codes
        self.calls = []

    def transact_write_items(self, **kwargs):
        self.calls.append(kwargs)
        if self.cancellation_codes:
            raise ClientError(
                {
                    "Error": {"Code": "TransactionCanceledException", "Message": "stub"},
                    "CancellationReasons": [{"Code": code} for code in self.cancellation_codes],
                },
                "TransactWriteItems",
            )
        return {}


def _transaction_table(client):
    table = StubTable()
    table.name = "users"
    table.meta = type("Meta", (), {"client": client})()
    return table


def test_change_email_moves_the_item_in_one_transaction():
    client = StubTransactionClient()
    user = {"email": "old@example.com", "id": "u1", "full_name": "Old", "saved": {}}

    new_user = UsersRepository(_transaction_table(client)).change_email(
        user, "new@example.com", "New", "now"
    )

    assert new_user == {"email": "new@example.com", "id": "u1", "full_name": "New", "saved": {}, "updated_at": "now"}
    assert client.calls == [
        {
            "TransactItems": [
                {"Put": {"TableName": "users", "Item": new_user, "ConditionExpression": "attribute_not_exists(email)"}},
                {"Delete": {"TableName": "users", "Key": {"email": "old@example.com"}, "ConditionExpression": "attribute_exists(email)"}},
            ]
        }
    ]


def test_change_email_to_a_registered_email_is_a_duplicate():
    client = StubTransactionClient(cancellation_codes=["ConditionalCheckFailed", "None"])

    with pytest.raises(DuplicateRecordError):
        UsersRepository(_transaction_table(client)).change_email(
            {"email": "old@example.com"}, "taken@example.com", "Name", "now"
        )


@pytest.mark.parametrize("codes", [["None", "ConditionalCheckFailed"], ["ThrottlingError", "None"]])
def test_other_transaction_failures_are_repository_errors(codes):
    client = StubTransactionClient(cancellation_codes=codes)

    with pytest.raises(RepositoryError) as raised:
        UsersRepository(_transaction_table(client)).change_email(
            {"email": "old@example.com"}, "new@example.com", "Name", "now"
        )
    assert not isinstance(raised.value, DuplicateRecordError)


def test_update_full_name():
    table = StubTable()
    UsersRepository(table).update_full_name("a@example.com", "New Name", "now")

    name, kwargs = table.calls[0]
    assert name == "update_item"
    assert kwargs["UpdateExpression"] == "SET full_name = :full_name, updated_at = :updated_at"
    assert kwargs["ConditionExpression"] == "attribute_exists(email)"


def test_change_password_increments_the_session_version():
    table = StubTable(response={"Attributes": {"session_version": Decimal(2)}})

    assert UsersRepository(table).change_password("a@example.com", "hash", "now") == 2
    name, kwargs = table.calls[0]
    assert kwargs["UpdateExpression"] == (
        "SET password_hash = :hash, updated_at = :updated_at ADD session_version :one"
    )
    assert kwargs["ConditionExpression"] == "attribute_exists(email)"
    assert kwargs["ReturnValues"] == "UPDATED_NEW"


def test_session_updates_never_recreate_a_deleted_session():
    table = StubTable()
    repository = SessionsRepository(table)

    repository.set_email("abc", "new@example.com")
    repository.set_session_version("abc", 3)

    assert [kwargs["UpdateExpression"] for _, kwargs in table.calls] == [
        "SET email = :value",
        "SET session_version = :value",
    ]
    assert all(kwargs["ConditionExpression"] == "attribute_exists(token_hash)" for _, kwargs in table.calls)
    assert all(kwargs["Key"] == {"token_hash": "abc"} for _, kwargs in table.calls)
