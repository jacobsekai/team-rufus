"""Persistence abstractions for the backend."""

from typing import Any, Dict, Optional

from botocore.exceptions import ClientError


class RepositoryError(RuntimeError):
    """Raised when persistence fails."""


class DuplicateRecordError(RepositoryError):
    """Raised when a record with the same identifier already exists."""


def _put_new_item(table, item: Dict[str, Any], key: str, duplicate_message: str):
    """Write ``item`` only if no item with the same ``key`` already exists."""

    try:
        table.put_item(
            Item=item,
            ConditionExpression=f"attribute_not_exists({key})",
        )
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code == "ConditionalCheckFailedException":
            raise DuplicateRecordError(duplicate_message) from exc
        raise RepositoryError("Unable to save the record.") from exc


def _call(operation, *args, **kwargs):
    """Run a DynamoDB call, converting AWS errors to ``RepositoryError``."""

    try:
        return operation(*args, **kwargs)
    except ClientError as exc:
        raise RepositoryError("The database request failed.") from exc


class ExpressionsOfInterestRepository:
    """DynamoDB repository for expressions of interest."""

    def __init__(self, table):
        self.table = table

    def save(self, record: Dict[str, Any]) -> None:
        _put_new_item(
            self.table,
            record,
            key="id",
            duplicate_message=(
                "The expression-of-interest identifier already exists."
            ),
        )


class UsersRepository:
    """DynamoDB repository for user accounts.

    The table is keyed on the normalised email address so DynamoDB itself
    guarantees that one email address can only register one account.
    """

    def __init__(self, table):
        self.table = table

    def create_user(self, user: Dict[str, Any]) -> None:
        _put_new_item(
            self.table,
            user,
            key="email",
            duplicate_message="An account with this email already exists.",
        )

    def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        response = _call(
            self.table.get_item, Key={"email": email}, ConsistentRead=True
        )
        return response.get("Item")

    def delete_user(self, email: str) -> None:
        _call(self.table.delete_item, Key={"email": email})

    def record_failed_login(self, email: str) -> int:
        """Atomically add one failed attempt and return the new total."""

        response = _call(
            self.table.update_item,
            Key={"email": email},
            UpdateExpression="ADD failed_login_count :one",
            ConditionExpression="attribute_exists(email)",
            ExpressionAttributeValues={":one": 1},
            ReturnValues="UPDATED_NEW",
        )
        return int(response["Attributes"]["failed_login_count"])

    def lock_user(self, email: str, locked_until: int) -> None:
        _call(
            self.table.update_item,
            Key={"email": email},
            UpdateExpression=(
                "SET locked_until = :until, failed_login_count = :zero"
            ),
            ConditionExpression="attribute_exists(email)",
            ExpressionAttributeValues={":until": locked_until, ":zero": 0},
        )

    def set_saved_items(self, email: str, saved: Dict[str, str], updated_at: str) -> None:
        """Replace the user's saved items.

        A whole-map write is simple and fine for one person editing their own
        list; two saves at the same instant from the same user could lose one.
        """

        _call(
            self.table.update_item,
            Key={"email": email},
            UpdateExpression="SET saved = :saved, updated_at = :updated_at",
            ConditionExpression="attribute_exists(email)",
            ExpressionAttributeValues={":saved": saved, ":updated_at": updated_at},
        )

    def clear_failed_logins(self, email: str) -> None:
        _call(
            self.table.update_item,
            Key={"email": email},
            UpdateExpression="SET failed_login_count = :zero REMOVE locked_until",
            ConditionExpression="attribute_exists(email)",
            ExpressionAttributeValues={":zero": 0},
        )


class SessionsRepository:
    """DynamoDB repository for login sessions.

    Items are keyed on a SHA-256 hash of the session token, so a leaked table
    does not reveal usable tokens. DynamoDB's time-to-live feature deletes
    items after ``expires_at``; the application also checks the expiry
    because TTL deletion can be delayed.
    """

    def __init__(self, table):
        self.table = table

    def create_session(self, session: Dict[str, Any]) -> None:
        _put_new_item(
            self.table,
            session,
            key="token_hash",
            duplicate_message="The session identifier already exists.",
        )

    def get_session(self, token_hash: str) -> Optional[Dict[str, Any]]:
        response = _call(
            self.table.get_item,
            Key={"token_hash": token_hash},
            ConsistentRead=True,
        )
        return response.get("Item")

    def delete_session(self, token_hash: str) -> None:
        _call(self.table.delete_item, Key={"token_hash": token_hash})
