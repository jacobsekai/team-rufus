"""Forum: posts, comments, likes and dislikes, and reports.

Anyone can read. Writing (posting, commenting, voting, reporting) needs a
signed-in account. Authors can delete their own posts and comments. Only
the author's first name is shown, never their email. Full API reference:
docs/api.md; storage: docs/dynamodb-design.md.
"""

import json
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from flask import Blueprint, current_app, g, jsonify, request

from .accounts import current_user, login_required
from .helpers import error_response, json_body_or_error, unknown_fields_error, utc_timestamp
from .repositories import (
    ConflictError,
    DuplicateRecordError,
    ForumRepository,
    NotFoundError,
    RepositoryError,
)


forum = Blueprint("forum", __name__)

REPORT_REASONS = ("spam", "bullying", "personal_info", "other")
TITLE_LENGTH = (5, 120)
BODY_LENGTH = (10, 5000)
COMMENT_LENGTH = (1, 2000)
PAGE_SIZE = 20

# "Most liked" reads posts this many at a time and sorts at most
# MAX_TOP_POSTS. Plenty for a prototype; a larger forum would keep a score
# index instead.
SCAN_PAGE = 50
MAX_TOP_POSTS = 500

# (actions, seconds): stops one account flooding the forum.
RATE_LIMITS = {
    "post": (5, 600),
    "comment": (20, 600),
    "vote": (120, 60),
    "report": (20, 600),
}

# "<16-digit microseconds>-<12 hex>"; comments add ".<same shape>".
_ID = r"\d{16}-[0-9a-f]{12}"
POST_ID = re.compile(rf"^{_ID}$")
COMMENT_ID = re.compile(rf"^({_ID})\.{_ID}$")

EXAMPLE_FILE = Path(__file__).with_name("forum_example.json")


def _repository() -> ForumRepository:
    return current_app.extensions["forum_repository"]


def _new_id() -> str:
    return f"{time.time_ns() // 1000:016d}-{uuid4().hex[:12]}"


def _first_name(user: Dict[str, Any]) -> str:
    parts = (user.get("full_name") or "").split()
    return parts[0][:40] if parts else "Member"


def _viewer_id() -> Optional[str]:
    """The signed-in user's ID, or None. Reading never fails on the session."""

    try:
        user = current_user()
    except RepositoryError:
        current_app.logger.exception("Failed to check the session.")
        return None
    return user["id"] if user else None


def _unavailable(message: str):
    current_app.logger.exception(message)
    return error_response("The forum is having a problem. Please try again in a few minutes.", 503)


def _rate_limited(kind: str):
    limit, window = RATE_LIMITS[kind]
    allowed = _repository().take_rate_token(
        g.current_user["id"], kind, limit, window, int(time.time())
    )
    if allowed:
        return None
    response = error_response("You're doing that too often. Please wait a few minutes.", 429)
    response[0].headers["Retry-After"] = str(window)
    return response


# ---------- Shapes returned by the API ----------
def _public_post(post: Dict[str, Any], votes: Dict[str, int], viewer: Optional[str]):
    return {
        "id": post["id"],
        "title": post["title"],
        "body": post["body"],
        "author_name": post["author_name"],
        "created_at": post["created_at"],
        "likes": post.get("likes", 0),
        "dislikes": post.get("dislikes", 0),
        "comment_count": post.get("comment_count", 0),
        "my_vote": votes.get(f"post#{post['id']}", 0),
        "is_mine": viewer is not None and post["author_id"] == viewer,
    }


def _public_comment(comment: Dict[str, Any], votes: Dict[str, int], viewer: Optional[str]):
    return {
        "id": comment["id"],
        "body": comment["body"],
        "author_name": comment["author_name"],
        "created_at": comment["created_at"],
        "likes": comment.get("likes", 0),
        "dislikes": comment.get("dislikes", 0),
        "my_vote": votes.get(f"comment#{comment['id']}", 0),
        "is_mine": viewer is not None and comment["author_id"] == viewer,
    }


def _votes(viewer: Optional[str], targets: List[str]) -> Dict[str, int]:
    if viewer is None or not targets:
        return {}
    return _repository().get_votes(viewer, targets)


# ---------- Validation ----------
def _text(payload: Dict[str, Any], field: str, limits: Tuple[int, int], errors: List[str]) -> str:
    value = payload.get(field)
    low, high = limits
    if not isinstance(value, str) or not low <= len(value.strip()) <= high:
        errors.append(f"{field} must be between {low} and {high} characters.")
        return ""
    return value.strip()


def _payload(allowed) -> Tuple[Optional[Dict[str, Any]], List[str], Optional[tuple]]:
    payload, error = json_body_or_error()
    if error:
        return None, [], error
    if not isinstance(payload, dict):
        return None, ["The request body must be a JSON object."], None
    unknown = unknown_fields_error(payload, allowed)
    return payload, [unknown] if unknown else [], None


def _not_found(what: str = "Post"):
    return error_response(f"{what} not found.", 404)


# ---------- Example post ----------
def _ensure_example() -> None:
    """Add the example post once per database (checked once per process)."""

    if not current_app.config["FORUM_EXAMPLE"] or current_app.extensions.get("forum_example_checked"):
        return
    try:
        example = json.loads(EXAMPLE_FILE.read_text(encoding="utf-8"))
        now = utc_timestamp()
        post = {
            **example["post"],
            "id": _new_id(),
            "author_id": "team-rufus",
            "created_at": now,
            "likes": 0,
            "dislikes": 0,
        }
        comments = [
            {
                **comment,
                "id": f"{post['id']}.{_new_id()}",
                "post_id": post["id"],
                "author_id": "team-rufus",
                "created_at": now,
                "likes": 0,
                "dislikes": 0,
            }
            for comment in example.get("comments", [])
        ]
        _repository().create_example_once(post, comments)
        current_app.extensions["forum_example_checked"] = True
    except (RepositoryError, OSError, ValueError, KeyError):
        # The forum still works; the example is tried again next time.
        current_app.logger.exception("Failed to add the example forum post.")


# ---------- Posts ----------
def _newest(cursor: Optional[str]):
    """One page of newest posts. Returns (posts, next cursor or None)."""

    # One extra post shows whether there is another page.
    posts, _ = _repository().query_posts(after_id=cursor, limit=PAGE_SIZE + 1)
    if len(posts) > PAGE_SIZE:
        return posts[:PAGE_SIZE], posts[PAGE_SIZE - 1]["id"]
    return posts, None


def _top(cursor: Optional[str]):
    """One page of the most liked posts. The cursor is an offset."""

    offset = int(cursor or 0)
    posts: List[Dict[str, Any]] = []
    after = None
    while len(posts) < MAX_TOP_POSTS:
        page, has_more = _repository().query_posts(after_id=after, limit=SCAN_PAGE)
        posts.extend(page)
        if not has_more or not page:
            break
        after = page[-1]["id"]
    # Most liked first; newest first when the score is the same.
    posts.sort(key=lambda p: (p.get("likes", 0) - p.get("dislikes", 0), p["id"]), reverse=True)
    page = posts[offset:offset + PAGE_SIZE]
    more = offset + PAGE_SIZE < len(posts)
    return page, str(offset + PAGE_SIZE) if more else None


@forum.get("/api/forum/posts")
def list_posts():
    """List posts, newest or most liked first."""

    sort = request.args.get("sort", "new")
    cursor = request.args.get("cursor") or None
    errors = []
    if sort not in ("new", "top"):
        errors.append("sort must be new or top.")
    elif cursor is not None and not (
        POST_ID.fullmatch(cursor) if sort == "new" else cursor.isdigit() and len(cursor) <= 6
    ):
        errors.append("cursor is not valid.")
    if errors:
        return error_response("Validation failed.", 400, errors)

    _ensure_example()
    try:
        posts, next_cursor = (_top if sort == "top" else _newest)(cursor)
        viewer = _viewer_id()
        votes = _votes(viewer, [f"post#{p['id']}" for p in posts])
    except RepositoryError:
        return _unavailable("Failed to list forum posts.")
    return jsonify({
        "posts": [_public_post(p, votes, viewer) for p in posts],
        "next_cursor": next_cursor,
    }), 200


@forum.post("/api/forum/posts")
@login_required
def create_post():
    """Start a discussion."""

    payload, errors, error = _payload({"title", "body"})
    if error:
        return error
    if payload is not None:
        title = _text(payload, "title", TITLE_LENGTH, errors)
        body = _text(payload, "body", BODY_LENGTH, errors)
    if errors:
        return error_response("Validation failed.", 400, errors)

    try:
        limited = _rate_limited("post")
        if limited:
            return limited
        user = g.current_user
        post = {
            "id": _new_id(),
            "title": title,
            "body": body,
            "author_id": user["id"],
            "author_name": _first_name(user),
            "created_at": utc_timestamp(),
            "likes": 0,
            "dislikes": 0,
            "comment_count": 0,
        }
        _repository().create_post(post)
    except RepositoryError:
        return _unavailable("Failed to create a forum post.")
    return jsonify(_public_post(post, {}, user["id"])), 201


@forum.get("/api/forum/posts/<post_id>")
def get_post(post_id):
    """One post with all its comments, oldest comment first."""

    if not POST_ID.fullmatch(post_id):
        return _not_found()
    try:
        post = _repository().get_post(post_id)
        if post is None:
            return _not_found()
        comments = _repository().list_comments(post_id)
        viewer = _viewer_id()
        votes = _votes(viewer, [f"post#{post_id}"] + [f"comment#{c['id']}" for c in comments])
    except RepositoryError:
        return _unavailable("Failed to load a forum post.")
    return jsonify({
        "post": _public_post(post, votes, viewer),
        "comments": [_public_comment(c, votes, viewer) for c in comments],
    }), 200


# POST rather than DELETE: CloudFront's signed requests to the Lambda function
# URL reject DELETE requests that have a body.
@forum.post("/api/forum/posts/<post_id>/delete")
@login_required
def delete_post(post_id):
    """Delete your own post (and its comments)."""

    if not POST_ID.fullmatch(post_id):
        return _not_found()
    try:
        post = _repository().get_post(post_id)
        if post is None:
            return _not_found()
        if post["author_id"] != g.current_user["id"]:
            # 404, not 403: CloudFront reserves 403 for the Midway sign-in page.
            return _not_found()
        _repository().delete_post(post_id)
    except RepositoryError:
        return _unavailable("Failed to delete a forum post.")
    return jsonify({"status": "deleted"}), 200


# ---------- Comments ----------
@forum.post("/api/forum/posts/<post_id>/comments")
@login_required
def create_comment(post_id):
    """Comment on a post."""

    if not POST_ID.fullmatch(post_id):
        return _not_found()
    payload, errors, error = _payload({"body"})
    if error:
        return error
    if payload is not None:
        body = _text(payload, "body", COMMENT_LENGTH, errors)
    if errors:
        return error_response("Validation failed.", 400, errors)

    try:
        limited = _rate_limited("comment")
        if limited:
            return limited
        user = g.current_user
        comment = {
            "id": f"{post_id}.{_new_id()}",
            "post_id": post_id,
            "body": body,
            "author_id": user["id"],
            "author_name": _first_name(user),
            "created_at": utc_timestamp(),
            "likes": 0,
            "dislikes": 0,
        }
        _repository().create_comment(comment)
    except NotFoundError:
        return _not_found()
    except RepositoryError:
        return _unavailable("Failed to add a forum comment.")
    return jsonify(_public_comment(comment, {}, user["id"])), 201


@forum.post("/api/forum/comments/<comment_id>/delete")
@login_required
def delete_comment(comment_id):
    """Delete your own comment."""

    match = COMMENT_ID.fullmatch(comment_id)
    if not match:
        return _not_found("Comment")
    post_id = match.group(1)
    try:
        comment = _repository().get_comment(post_id, comment_id)
        if comment is None or comment["author_id"] != g.current_user["id"]:
            return _not_found("Comment")
        _repository().delete_comment(post_id, comment_id)
    except NotFoundError:
        return _not_found("Comment")
    except RepositoryError:
        return _unavailable("Failed to delete a forum comment.")
    return jsonify({"status": "deleted"}), 200


# ---------- Likes and dislikes ----------
def _vote(target_type: str, post_id: str, comment_id: Optional[str]):
    payload, errors, error = _payload({"value"})
    if error:
        return error
    if payload is not None:
        value = payload.get("value")
        # bool is a subclass of int in Python: refuse true/false explicitly.
        if isinstance(value, bool) or value not in (1, 0, -1):
            errors.append("value must be 1 (like), -1 (dislike) or 0 (remove).")
    if errors:
        return error_response("Validation failed.", 400, errors)

    what = "Post" if target_type == "post" else "Comment"
    target = f"{target_type}#{comment_id or post_id}"
    key = ForumRepository.target_key(target_type, post_id, comment_id)
    user_id = g.current_user["id"]
    try:
        limited = _rate_limited("vote")
        if limited:
            return limited
        for attempt in range(2):  # once more if someone voted at the same instant
            old = _repository().get_votes(user_id, [target]).get(target, 0)
            try:
                counts = _repository().set_vote(user_id, target, key, old, value)
                break
            except ConflictError:
                if attempt:
                    raise
    except NotFoundError:
        return _not_found(what)
    except RepositoryError:
        return _unavailable("Failed to save a forum vote.")
    return jsonify({**counts, "my_vote": value}), 200


@forum.post("/api/forum/posts/<post_id>/vote")
@login_required
def vote_post(post_id):
    """Like (1), dislike (-1) or clear (0) your vote on a post."""

    if not POST_ID.fullmatch(post_id):
        return _not_found()
    return _vote("post", post_id, None)


@forum.post("/api/forum/comments/<comment_id>/vote")
@login_required
def vote_comment(comment_id):
    """Like (1), dislike (-1) or clear (0) your vote on a comment."""

    match = COMMENT_ID.fullmatch(comment_id)
    if not match:
        return _not_found("Comment")
    return _vote("comment", match.group(1), comment_id)


# ---------- Reports ----------
@forum.post("/api/forum/reports")
@login_required
def report():
    """Report a post or comment to the team. Once per person per item."""

    payload, errors, error = _payload({"type", "id", "reason"})
    if error:
        return error
    if payload is not None:
        target_type = payload.get("type")
        target_id = payload.get("id")
        reason = payload.get("reason")
        if target_type not in ("post", "comment"):
            errors.append("type must be post or comment.")
        elif not isinstance(target_id, str) or not (
            POST_ID if target_type == "post" else COMMENT_ID
        ).fullmatch(target_id):
            errors.append("id is not a valid post or comment id.")
        if reason not in REPORT_REASONS:
            errors.append("reason must be one of: " + ", ".join(REPORT_REASONS) + ".")
    if errors:
        return error_response("Validation failed.", 400, errors)

    try:
        if target_type == "post":
            exists = _repository().get_post(target_id) is not None
        else:
            exists = _repository().get_comment(target_id.split(".")[0], target_id) is not None
        if not exists:
            return _not_found("Post" if target_type == "post" else "Comment")
        limited = _rate_limited("report")
        if limited:
            return limited
        _repository().create_report({
            "type": target_type,
            "target_id": target_id,
            "reason": reason,
            "reporter_id": g.current_user["id"],
            "created_at": utc_timestamp(),
        })
    except DuplicateRecordError:
        return jsonify({"status": "already_reported"}), 200
    except RepositoryError:
        return _unavailable("Failed to save a forum report.")
    return jsonify({"status": "received"}), 201
