"""Persistence abstractions for the backend."""

from typing import Dict, Any

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
