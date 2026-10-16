"""Persistence abstractions for the backend."""

from typing import Dict, Any

from botocore.exceptions import ClientError


class RepositoryError(RuntimeError):
    """Raised when persistence fails."""


class DuplicateRecordError(RepositoryError):
    """Raised when a record with the same identifier already exists."""


class ExpressionsOfInterestRepository:
    """DynamoDB repository for expressions of interest."""

    def __init__(self, table):
        self.table = table

    def save(self, record: Dict[str, Any]) -> None:
        try:
            self.table.put_item(
                Item=record,
                ConditionExpression="attribute_not_exists(id)",
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code == "ConditionalCheckFailedException":
                raise DuplicateRecordError(
                    "The expression-of-interest identifier already exists."
                ) from exc
            raise RepositoryError("Unable to save the record.") from exc

