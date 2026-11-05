"""Persistence abstractions for the backend."""

from typing import Any, Dict, List, Optional

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

    def update_full_name(self, email: str, full_name: str, updated_at: str) -> None:
        _call(
            self.table.update_item,
            Key={"email": email},
            UpdateExpression="SET full_name = :full_name, updated_at = :updated_at",
            ConditionExpression="attribute_exists(email)",
            ExpressionAttributeValues={":full_name": full_name, ":updated_at": updated_at},
        )

    def change_email(
        self, user: Dict[str, Any], new_email: str, full_name: str, updated_at: str
    ) -> Dict[str, Any]:
        """Move the account to a new email address and return the new item.

        The email is the partition key, so the item is copied to the new key
        and the old one deleted in a single transaction: either both happen
        or neither does, and the new email cannot already be registered.
        """

        new_user = {
            **user,
            "email": new_email,
            "full_name": full_name,
            "updated_at": updated_at,
        }
        try:
            # The resource's client converts Python values to DynamoDB types.
            self.table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": new_user,
                            "ConditionExpression": "attribute_not_exists(email)",
                        }
                    },
                    {
                        "Delete": {
                            "TableName": self.table.name,
                            "Key": {"email": user["email"]},
                            "ConditionExpression": "attribute_exists(email)",
                        }
                    },
                ]
            )
        except ClientError as exc:
            # One reason per item, in order; the first is the Put.
            reasons = exc.response.get("CancellationReasons") or []
            if reasons and reasons[0].get("Code") == "ConditionalCheckFailed":
                raise DuplicateRecordError(
                    "An account with this email already exists."
                ) from exc
            raise RepositoryError("The database request failed.") from exc
        return new_user

    def change_password(self, email: str, password_hash: str, updated_at: str) -> int:
        """Store a new password hash and return the new session version.

        Increasing ``session_version`` ends every session started before the
        change (see ``accounts.current_user``).
        """

        response = _call(
            self.table.update_item,
            Key={"email": email},
            UpdateExpression=(
                "SET password_hash = :hash, updated_at = :updated_at "
                "ADD session_version :one"
            ),
            ConditionExpression="attribute_exists(email)",
            ExpressionAttributeValues={
                ":hash": password_hash,
                ":updated_at": updated_at,
                ":one": 1,
            },
            ReturnValues="UPDATED_NEW",
        )
        return int(response["Attributes"]["session_version"])

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

    def set_email(self, token_hash: str, email: str) -> None:
        self._set(token_hash, "email", email)

    def set_session_version(self, token_hash: str, session_version: int) -> None:
        self._set(token_hash, "session_version", session_version)

    def _set(self, token_hash: str, attribute: str, value: Any) -> None:
        # The condition stops an update from re-creating a deleted session.
        _call(
            self.table.update_item,
            Key={"token_hash": token_hash},
            UpdateExpression=f"SET {attribute} = :value",
            ConditionExpression="attribute_exists(token_hash)",
            ExpressionAttributeValues={":value": value},
        )


class NotFoundError(RepositoryError):
    """Raised when the item an operation depends on does not exist."""


class ConflictError(RepositoryError):
    """Raised when a concurrent change made a conditional write fail."""


def _number(value) -> int:
    """DynamoDB returns numbers as ``Decimal``; the API returns integers."""

    return int(value or 0)


class ForumRepository:
    """DynamoDB repository for the forum (one table, ``pk`` + ``sk`` keys).

    Item types, all in the one table (see docs/dynamodb-design.md):

    - post:    pk ``POSTS``,           sk ``POST#<post_id>``
    - comment: pk ``POST#<post_id>``,  sk ``COMMENT#<comment_id>``
    - vote:    pk ``VOTES#<user_id>``, sk ``post#<id>`` / ``comment#<id>``
    - report:  pk ``REPORTS``,         sk ``<type>#<id>#<user_id>``
    - rate:    pk ``RATE#<user_id>``,  sk ``<kind>`` (expires with TTL)
    - marker:  pk ``META``,            sk ``EXAMPLE_POST``

    Post and comment IDs start with the creation time in microseconds, so
    sort-key order is time order. Like, dislike and comment counts are kept
    on the post or comment and changed in the same transaction as the vote
    or comment, so they always match.
    """

    POSTS = "POSTS"

    def __init__(self, table):
        self.table = table

    # ---------- Keys ----------
    @staticmethod
    def _post_key(post_id: str) -> Dict[str, str]:
        return {"pk": ForumRepository.POSTS, "sk": f"POST#{post_id}"}

    @staticmethod
    def _comment_key(post_id: str, comment_id: str) -> Dict[str, str]:
        return {"pk": f"POST#{post_id}", "sk": f"COMMENT#{comment_id}"}

    @staticmethod
    def target_key(target_type: str, post_id: str, comment_id: Optional[str] = None):
        if target_type == "post":
            return ForumRepository._post_key(post_id)
        return ForumRepository._comment_key(post_id, comment_id)

    @staticmethod
    def _clean(item: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if item is None:
            return None
        clean = {k: v for k, v in item.items() if k not in ("pk", "sk")}
        for counter in ("likes", "dislikes", "comment_count"):
            if counter in clean:
                clean[counter] = _number(clean[counter])
        return clean

    def _transact(self, items, not_found_index: Optional[int] = None) -> None:
        """Run a transaction. A failed condition on the item at
        ``not_found_index`` means the parent is gone (``NotFoundError``);
        any other failed condition is a concurrent change (``ConflictError``)."""

        for entry in items:
            next(iter(entry.values()))["TableName"] = self.table.name
        try:
            # The resource's client converts Python values to DynamoDB types.
            self.table.meta.client.transact_write_items(TransactItems=items)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "TransactionCanceledException":
                raise RepositoryError("The database request failed.") from exc
            reasons = exc.response.get("CancellationReasons") or []
            failed = [i for i, r in enumerate(reasons) if r.get("Code") == "ConditionalCheckFailed"]
            if not_found_index is not None and not_found_index in failed:
                raise NotFoundError("The item no longer exists.") from exc
            if failed:
                raise ConflictError("The item was changed at the same time.") from exc
            raise RepositoryError("The database request failed.") from exc

    # ---------- Posts ----------
    def create_post(self, post: Dict[str, Any]) -> None:
        _put_new_item(
            self.table,
            {**self._post_key(post["id"]), **post},
            key="pk",
            duplicate_message="The post identifier already exists.",
        )

    def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        response = _call(self.table.get_item, Key=self._post_key(post_id), ConsistentRead=True)
        return self._clean(response.get("Item"))

    def query_posts(self, after_id: Optional[str] = None, limit: int = 50):
        """Return ``(posts, has_more)``: newest first, older than ``after_id``."""

        kwargs = {
            "KeyConditionExpression": "pk = :pk AND begins_with(sk, :prefix)",
            "ExpressionAttributeValues": {":pk": self.POSTS, ":prefix": "POST#"},
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if after_id:
            kwargs["ExclusiveStartKey"] = self._post_key(after_id)
        response = _call(self.table.query, **kwargs)
        posts = [self._clean(item) for item in response.get("Items", [])]
        return posts, "LastEvaluatedKey" in response

    def delete_post(self, post_id: str) -> None:
        """Delete the post and all its comments."""

        _call(self.table.delete_item, Key=self._post_key(post_id))
        keys = [
            self._comment_key(post_id, comment["id"])
            for comment in self.list_comments(post_id)
        ]
        try:
            with self.table.batch_writer() as batch:
                for key in keys:
                    batch.delete_item(Key=key)
        except ClientError as exc:
            raise RepositoryError("The database request failed.") from exc

    # ---------- Comments ----------
    def create_comment(self, comment: Dict[str, Any]) -> None:
        """Save the comment and add one to the post's comment count."""

        post_key = self._post_key(comment["post_id"])
        self._transact(
            [
                {"Put": {
                    "Item": {**self._comment_key(comment["post_id"], comment["id"]), **comment},
                    "ConditionExpression": "attribute_not_exists(pk)",
                }},
                {"Update": {
                    "Key": post_key,
                    "UpdateExpression": "ADD comment_count :one",
                    "ConditionExpression": "attribute_exists(pk)",
                    "ExpressionAttributeValues": {":one": 1},
                }},
            ],
            not_found_index=1,
        )

    def get_comment(self, post_id: str, comment_id: str) -> Optional[Dict[str, Any]]:
        response = _call(
            self.table.get_item, Key=self._comment_key(post_id, comment_id), ConsistentRead=True
        )
        return self._clean(response.get("Item"))

    def list_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """All comments on the post, oldest first."""

        kwargs = {
            "KeyConditionExpression": "pk = :pk AND begins_with(sk, :prefix)",
            "ExpressionAttributeValues": {":pk": f"POST#{post_id}", ":prefix": "COMMENT#"},
            "ConsistentRead": True,
        }
        comments: List[Dict[str, Any]] = []
        while True:
            response = _call(self.table.query, **kwargs)
            comments.extend(self._clean(item) for item in response.get("Items", []))
            if "LastEvaluatedKey" not in response:
                return comments
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    def delete_comment(self, post_id: str, comment_id: str) -> None:
        """Delete the comment and take one off the post's comment count."""

        self._transact(
            [
                {"Delete": {
                    "Key": self._comment_key(post_id, comment_id),
                    "ConditionExpression": "attribute_exists(pk)",
                }},
                {"Update": {
                    "Key": self._post_key(post_id),
                    "UpdateExpression": "ADD comment_count :minus_one",
                    "ConditionExpression": "attribute_exists(pk)",
                    "ExpressionAttributeValues": {":minus_one": -1},
                }},
            ],
            not_found_index=0,
        )

    # ---------- Likes and dislikes ----------
    def get_votes(self, user_id: str, targets: List[str]) -> Dict[str, int]:
        """Return ``{"post#<id>": 1 | -1}`` for the targets the user voted on."""

        votes: Dict[str, int] = {}
        unique = list(dict.fromkeys(targets))
        client = self.table.meta.client
        for start in range(0, len(unique), 100):  # BatchGetItem limit
            request = {self.table.name: {
                "Keys": [{"pk": f"VOTES#{user_id}", "sk": t} for t in unique[start:start + 100]],
                "ProjectionExpression": "sk, #v",
                # The vote is about to be changed, so read the latest value.
                "ConsistentRead": True,
                "ExpressionAttributeNames": {"#v": "value"},
            }}
            for _ in range(5):  # retry keys DynamoDB didn't get to
                response = _call(client.batch_get_item, RequestItems=request)
                for item in response.get("Responses", {}).get(self.table.name, []):
                    votes[item["sk"]] = _number(item["value"])
                request = response.get("UnprocessedKeys") or {}
                if not request:
                    break
        return votes

    def set_vote(
        self, user_id: str, target: str, target_key: Dict[str, str], old: int, new: int
    ) -> Dict[str, int]:
        """Change the user's vote from ``old`` to ``new`` (1, -1 or 0) and
        update the target's like/dislike counts in the same transaction.
        Returns the target's new counts."""

        if old != new:
            vote_key = {"pk": f"VOTES#{user_id}", "sk": target}
            if old == 0:
                condition = {"ConditionExpression": "attribute_not_exists(pk)"}
            else:
                condition = {
                    "ConditionExpression": "#v = :old",
                    "ExpressionAttributeNames": {"#v": "value"},
                    "ExpressionAttributeValues": {":old": old},
                }
            if new == 0:
                vote_change = {"Delete": {"Key": vote_key, **condition}}
            else:
                vote_change = {"Put": {"Item": {**vote_key, "value": new}, **condition}}

            likes = (1 if new == 1 else 0) - (1 if old == 1 else 0)
            dislikes = (1 if new == -1 else 0) - (1 if old == -1 else 0)
            self._transact(
                [
                    vote_change,
                    {"Update": {
                        "Key": target_key,
                        "UpdateExpression": "ADD likes :likes, dislikes :dislikes",
                        "ConditionExpression": "attribute_exists(pk)",
                        "ExpressionAttributeValues": {":likes": likes, ":dislikes": dislikes},
                    }},
                ],
                not_found_index=1,
            )
        response = _call(self.table.get_item, Key=target_key, ConsistentRead=True)
        item = response.get("Item")
        if item is None:
            raise NotFoundError("The item no longer exists.")
        return {"likes": _number(item.get("likes")), "dislikes": _number(item.get("dislikes"))}

    # ---------- Reports ----------
    def create_report(self, report: Dict[str, Any]) -> None:
        """Save a report. One report per person per item: a second one
        raises ``DuplicateRecordError``."""

        _put_new_item(
            self.table,
            {
                "pk": "REPORTS",
                "sk": f"{report['type']}#{report['target_id']}#{report['reporter_id']}",
                **report,
            },
            key="pk",
            duplicate_message="You have already reported this.",
        )

    # ---------- Rate limits ----------
    def take_rate_token(
        self, user_id: str, kind: str, limit: int, window_seconds: int, now: int
    ) -> bool:
        """Count one action in the user's current time window. Returns False
        when the limit is reached. Both steps are single conditional writes,
        so two requests at the same moment can't both slip through."""

        key = {"pk": f"RATE#{user_id}", "sk": kind}
        cutoff = now - window_seconds
        try:
            self.table.update_item(
                Key=key,
                UpdateExpression="ADD #c :one",
                ConditionExpression="window_start > :cutoff AND #c < :limit",
                ExpressionAttributeNames={"#c": "count"},
                ExpressionAttributeValues={":one": 1, ":cutoff": cutoff, ":limit": limit},
            )
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                raise RepositoryError("The database request failed.") from exc
        try:
            # No window yet, or the last one has ended: start a new one.
            self.table.update_item(
                Key=key,
                UpdateExpression="SET #c = :one, window_start = :now, expires_at = :expires",
                ConditionExpression="attribute_not_exists(pk) OR window_start <= :cutoff",
                ExpressionAttributeNames={"#c": "count"},
                ExpressionAttributeValues={
                    ":one": 1, ":now": now, ":cutoff": cutoff, ":expires": now + window_seconds,
                },
            )
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise RepositoryError("The database request failed.") from exc

    # ---------- Example post ----------
    def create_example_once(self, post: Dict[str, Any], comments: List[Dict[str, Any]]) -> bool:
        """Add the example post the first time only. A marker item records
        that it was added, so it isn't added back if someone deletes it.
        Returns True if it was added now."""

        try:
            _put_new_item(
                self.table,
                {"pk": "META", "sk": "EXAMPLE_POST", "post_id": post["id"]},
                key="pk",
                duplicate_message="The example post was already added.",
            )
        except DuplicateRecordError:
            return False
        self.create_post({**post, "comment_count": 0})
        for comment in comments:
            self.create_comment(comment)
        return True
