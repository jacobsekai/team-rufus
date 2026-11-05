"""Shared pytest fixtures."""

import pytest

from backend import create_app
from backend.repositories import DuplicateRecordError, NotFoundError


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


class InMemoryForumRepository:
    """Test double with the same behaviour as ``ForumRepository``: counts
    change together with votes and comments, one report per person per item,
    and windowed rate limits."""

    def __init__(self):
        self.posts = {}
        self.comments = {}  # post_id -> {comment_id: comment}
        self.votes = {}  # (user_id, "post#<id>") -> 1 | -1
        self.reports = {}
        self.rates = {}
        self.example_added = False

    def create_post(self, post):
        self.posts[post["id"]] = dict(post)

    def get_post(self, post_id):
        post = self.posts.get(post_id)
        return dict(post) if post else None

    def query_posts(self, after_id=None, limit=50):
        ids = sorted(self.posts, reverse=True)
        if after_id:
            ids = [i for i in ids if i < after_id]
        return [dict(self.posts[i]) for i in ids[:limit]], len(ids) > limit

    def delete_post(self, post_id):
        self.posts.pop(post_id, None)
        self.comments.pop(post_id, None)

    def create_comment(self, comment):
        post = self.posts.get(comment["post_id"])
        if post is None:
            raise NotFoundError("The item no longer exists.")
        self.comments.setdefault(comment["post_id"], {})[comment["id"]] = dict(comment)
        post["comment_count"] = post.get("comment_count", 0) + 1

    def get_comment(self, post_id, comment_id):
        comment = self.comments.get(post_id, {}).get(comment_id)
        return dict(comment) if comment else None

    def list_comments(self, post_id):
        comments = self.comments.get(post_id, {})
        return [dict(comments[i]) for i in sorted(comments)]

    def delete_comment(self, post_id, comment_id):
        if self.comments.get(post_id, {}).pop(comment_id, None) is None:
            raise NotFoundError("The item no longer exists.")
        self.posts[post_id]["comment_count"] -= 1

    def get_votes(self, user_id, targets):
        return {t: self.votes[(user_id, t)] for t in targets if (user_id, t) in self.votes}

    def _target(self, target_key):
        if target_key["pk"] == "POSTS":
            return self.posts.get(target_key["sk"].split("#", 1)[1])
        post_id = target_key["pk"].split("#", 1)[1]
        return self.comments.get(post_id, {}).get(target_key["sk"].split("#", 1)[1])

    def set_vote(self, user_id, target, target_key, old, new):
        item = self._target(target_key)
        if item is None:
            raise NotFoundError("The item no longer exists.")
        item["likes"] = item.get("likes", 0) + (new == 1) - (old == 1)
        item["dislikes"] = item.get("dislikes", 0) + (new == -1) - (old == -1)
        if new:
            self.votes[(user_id, target)] = new
        else:
            self.votes.pop((user_id, target), None)
        return {"likes": item["likes"], "dislikes": item["dislikes"]}

    def create_report(self, report):
        key = (report["type"], report["target_id"], report["reporter_id"])
        if key in self.reports:
            raise DuplicateRecordError("You have already reported this.")
        self.reports[key] = dict(report)

    def take_rate_token(self, user_id, kind, limit, window_seconds, now):
        start, count = self.rates.get((user_id, kind), (None, 0))
        if start is None or start <= now - window_seconds:
            self.rates[(user_id, kind)] = (now, 1)
            return True
        if count >= limit:
            return False
        self.rates[(user_id, kind)] = (start, count + 1)
        return True

    def create_example_once(self, post, comments):
        if self.example_added:
            return False
        self.example_added = True
        self.create_post({**post, "comment_count": 0})
        for comment in comments:
            self.create_comment(comment)
        return True


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
def forum_repository():
    return InMemoryForumRepository()


@pytest.fixture
def make_app(repository, users_repository, sessions_repository, forum_repository):
    """Build an app wired to the in-memory test doubles.

    Keyword arguments replace individual dependencies, for example
    ``make_app(content_store=None)``. ``forum_example=True`` adds the
    example forum post, as in production.
    """

    def _make_app(forum_example=False, **overrides):
        dependencies = {
            "repository": repository,
            "users_repository": users_repository,
            "sessions_repository": sessions_repository,
            "forum_repository": forum_repository,
            "content_store": FakeContentStore(),
            "content_catalogue": TEST_CATALOGUE,
        }
        dependencies.update(overrides)
        config = {"TESTING": True, "FORUM_EXAMPLE": forum_example}
        return create_app(config, **dependencies)

    return _make_app


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()
