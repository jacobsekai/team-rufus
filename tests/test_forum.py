"""Forum tests: posts, comments, likes and dislikes, reports, limits."""

import importlib

import pytest

from backend.forum import PAGE_SIZE, RATE_LIMITS

# "backend.forum" on the package is the blueprint; this is the module.
forum_module = importlib.import_module("backend.forum")


PASSWORD = "correct horse battery 9!"
POST = {"title": "Is the placement paid?",
        "body": "Does anyone know if T Level placements are paid?"}


def _sign_up(client, name="Sam Example", email="sam@example.com"):
    response = client.post("/api/users", json={
        "full_name": name, "email": email, "password": PASSWORD, "accept_terms": True,
    })
    assert response.status_code == 201
    return client


@pytest.fixture
def sam(app):
    return _sign_up(app.test_client())


@pytest.fixture
def priya(app):
    return _sign_up(app.test_client(), "Priya Example", "priya@example.com")


def _post(client, **changes):
    return client.post("/api/forum/posts", json={**POST, **changes})


def _new_post(client, **changes):
    response = _post(client, **changes)
    assert response.status_code == 201
    return response.get_json()


def _comment(client, post_id, body="Thanks, that helps!"):
    return client.post(f"/api/forum/posts/{post_id}/comments", json={"body": body})


def _thread(client, post_id):
    response = client.get(f"/api/forum/posts/{post_id}")
    assert response.status_code == 200
    return response.get_json()


# ---------- Reading and posting ----------
def test_empty_forum(client):
    assert client.get("/api/forum/posts").get_json() == {"posts": [], "next_cursor": None}


def test_create_post_shows_first_name_only(sam):
    post = _new_post(sam)

    assert post["title"] == POST["title"]
    assert post["author_name"] == "Sam"
    assert post["is_mine"] is True
    assert (post["likes"], post["dislikes"], post["comment_count"], post["my_vote"]) == (0, 0, 0, 0)
    assert "author_id" not in post and "email" not in str(post)


def test_anyone_can_read_but_only_the_author_owns_it(app, sam, priya):
    post = _new_post(sam)

    as_visitor = app.test_client().get("/api/forum/posts").get_json()["posts"][0]
    as_priya = priya.get("/api/forum/posts").get_json()["posts"][0]

    assert as_visitor["id"] == post["id"] and as_visitor["is_mine"] is False
    assert as_priya["is_mine"] is False


def test_text_is_trimmed(sam):
    post = _new_post(sam, title="   Spaces around   ", body="  Ten or more letters  ")

    assert (post["title"], post["body"]) == ("Spaces around", "Ten or more letters")


@pytest.mark.parametrize("changes, message", [
    ({"title": "Hey"}, "title must be between 5 and 120 characters."),
    ({"title": "x" * 121}, "title must be between 5 and 120 characters."),
    ({"body": "too short"}, "body must be between 10 and 5000 characters."),
    ({"body": "x" * 5001}, "body must be between 10 and 5000 characters."),
    ({"topic": "placements"}, "Unknown fields: topic."),
    ({"author_name": "Admin"}, "Unknown fields: author_name."),
])
def test_post_validation(sam, changes, message):
    response = _post(sam, **changes)

    assert response.status_code == 400
    assert message in response.get_json()["details"]


def test_writing_needs_sign_in(client, sam):
    post_id = _new_post(sam)["id"]
    comment_id = _comment(sam, post_id).get_json()["id"]

    for path, body in [
        ("/api/forum/posts", POST),
        (f"/api/forum/posts/{post_id}/comments", {"body": "Hello"}),
        (f"/api/forum/posts/{post_id}/vote", {"value": 1}),
        (f"/api/forum/comments/{comment_id}/vote", {"value": 1}),
        (f"/api/forum/posts/{post_id}/delete", {}),
        (f"/api/forum/comments/{comment_id}/delete", {}),
        ("/api/forum/reports", {"type": "post", "id": post_id, "reason": "spam"}),
    ]:
        assert client.post(path, json=body).status_code == 401, path


# ---------- Listing ----------
def test_newest_first_and_paging(sam, forum_repository, monkeypatch):
    monkeypatch.setitem(RATE_LIMITS, "post", (100, 600))
    ids = [_new_post(sam, title=f"Question number {i}")["id"] for i in range(PAGE_SIZE + 3)]

    first = sam.get("/api/forum/posts").get_json()
    second = sam.get(f"/api/forum/posts?cursor={first['next_cursor']}").get_json()

    assert [p["id"] for p in first["posts"]] == ids[::-1][:PAGE_SIZE]
    assert [p["id"] for p in second["posts"]] == ids[::-1][PAGE_SIZE:]
    assert second["next_cursor"] is None


def test_exactly_one_page_has_no_next_cursor(sam, monkeypatch):
    monkeypatch.setitem(RATE_LIMITS, "post", (100, 600))
    for i in range(PAGE_SIZE):
        _new_post(sam, title=f"Question number {i}")

    response = sam.get("/api/forum/posts").get_json()

    assert len(response["posts"]) == PAGE_SIZE
    assert response["next_cursor"] is None


def test_most_liked_reads_every_page(sam, priya, monkeypatch):
    monkeypatch.setitem(RATE_LIMITS, "post", (100, 600))
    monkeypatch.setattr(forum_module, "SCAN_PAGE", 5)
    liked = _new_post(sam, title="The oldest post")["id"]
    for i in range(12):
        _new_post(sam, title=f"Newer question {i}")
    priya.post(f"/api/forum/posts/{liked}/vote", json={"value": 1})

    assert sam.get("/api/forum/posts?sort=top").get_json()["posts"][0]["id"] == liked


def test_most_liked_first(sam, priya):
    low = _new_post(sam, title="Few likes here")["id"]
    high = _new_post(sam, title="Lots of likes here")["id"]
    disliked = _new_post(sam, title="People disagree here")["id"]
    for client, post_id, value in [(sam, high, 1), (priya, high, 1), (priya, low, 1),
                                   (priya, disliked, -1)]:
        assert client.post(f"/api/forum/posts/{post_id}/vote", json={"value": value}).status_code == 200

    top = sam.get("/api/forum/posts?sort=top").get_json()["posts"]

    assert [p["id"] for p in top] == [high, low, disliked]


@pytest.mark.parametrize("query", ["sort=hot", "cursor=abc", "sort=top&cursor=x"])
def test_list_validation(client, query):
    assert client.get(f"/api/forum/posts?{query}").status_code == 400


# ---------- One post and comments ----------
def test_comments_in_order_with_count(sam, priya):
    post_id = _new_post(sam)["id"]
    _comment(priya, post_id, "First comment")
    _comment(sam, post_id, "Second comment")

    thread = _thread(priya, post_id)

    assert [c["body"] for c in thread["comments"]] == ["First comment", "Second comment"]
    assert [c["author_name"] for c in thread["comments"]] == ["Priya", "Sam"]
    assert [c["is_mine"] for c in thread["comments"]] == [True, False]
    assert thread["post"]["comment_count"] == 2


def test_comment_validation_and_missing_post(sam):
    post_id = _new_post(sam)["id"]

    assert _comment(sam, post_id, "   ").status_code == 400
    assert _comment(sam, post_id, "x" * 2001).status_code == 400
    assert _comment(sam, "1730000000000000-aaaaaaaaaaaa").status_code == 404


def test_unknown_or_malformed_post_is_json_404(client):
    for path in ["/api/forum/posts/1730000000000000-aaaaaaaaaaaa", "/api/forum/posts/not-an-id"]:
        response = client.get(path)
        assert response.status_code == 404
        assert response.get_json() == {"error": "Post not found."}


# ---------- Likes and dislikes ----------
def test_like_switch_to_dislike_and_clear(sam, priya):
    post_id = _new_post(sam)["id"]
    path = f"/api/forum/posts/{post_id}/vote"

    liked = priya.post(path, json={"value": 1}).get_json()
    again = priya.post(path, json={"value": 1}).get_json()
    switched = priya.post(path, json={"value": -1}).get_json()
    cleared = priya.post(path, json={"value": 0}).get_json()

    assert liked == {"likes": 1, "dislikes": 0, "my_vote": 1}
    assert again == liked  # liking twice counts once
    assert switched == {"likes": 0, "dislikes": 1, "my_vote": -1}
    assert cleared == {"likes": 0, "dislikes": 0, "my_vote": 0}


def test_votes_are_per_person_and_shown_back(sam, priya):
    post_id = _new_post(sam)["id"]
    sam.post(f"/api/forum/posts/{post_id}/vote", json={"value": 1})
    priya.post(f"/api/forum/posts/{post_id}/vote", json={"value": -1})

    assert _thread(sam, post_id)["post"]["my_vote"] == 1
    assert _thread(priya, post_id)["post"]["my_vote"] == -1
    assert (_thread(sam, post_id)["post"]["likes"], _thread(sam, post_id)["post"]["dislikes"]) == (1, 1)


def test_comment_votes(sam, priya):
    post_id = _new_post(sam)["id"]
    comment_id = _comment(sam, post_id).get_json()["id"]

    response = priya.post(f"/api/forum/comments/{comment_id}/vote", json={"value": -1})

    assert response.get_json() == {"likes": 0, "dislikes": 1, "my_vote": -1}
    assert _thread(priya, post_id)["comments"][0]["my_vote"] == -1


@pytest.mark.parametrize("value", [2, "1", True, None])
def test_vote_validation(sam, value):
    post_id = _new_post(sam)["id"]

    assert sam.post(f"/api/forum/posts/{post_id}/vote", json={"value": value}).status_code == 400


def test_vote_on_missing_items(sam):
    assert sam.post("/api/forum/posts/1730000000000000-aaaaaaaaaaaa/vote",
                    json={"value": 1}).status_code == 404
    assert sam.post("/api/forum/comments/1730000000000000-aaaaaaaaaaaa.1730000000000001-bbbbbbbbbbbb/vote",
                    json={"value": 1}).status_code == 404


# ---------- Deleting ----------
def test_author_deletes_post_with_its_comments(sam, priya, forum_repository):
    post_id = _new_post(sam)["id"]
    _comment(priya, post_id)

    assert priya.post(f"/api/forum/posts/{post_id}/delete", json={}).status_code == 404
    assert sam.post(f"/api/forum/posts/{post_id}/delete", json={}).get_json() == {"status": "deleted"}
    assert sam.get(f"/api/forum/posts/{post_id}").status_code == 404
    assert forum_repository.comments.get(post_id) is None


def test_author_deletes_comment_and_count_drops(sam, priya):
    post_id = _new_post(sam)["id"]
    comment_id = _comment(priya, post_id).get_json()["id"]

    assert sam.post(f"/api/forum/comments/{comment_id}/delete", json={}).status_code == 404
    assert priya.post(f"/api/forum/comments/{comment_id}/delete", json={}).status_code == 200
    assert _thread(sam, post_id)["post"]["comment_count"] == 0


# ---------- Reports ----------
def test_report_once_per_person(sam, priya, forum_repository):
    post_id = _new_post(sam)["id"]
    body = {"type": "post", "id": post_id, "reason": "bullying"}

    first = priya.post("/api/forum/reports", json=body)
    second = priya.post("/api/forum/reports", json=body)

    assert (first.status_code, first.get_json()) == (201, {"status": "received"})
    assert (second.status_code, second.get_json()) == (200, {"status": "already_reported"})
    [report] = forum_repository.reports.values()
    assert (report["type"], report["target_id"], report["reason"]) == ("post", post_id, "bullying")


def test_report_comment_and_validation(sam):
    post_id = _new_post(sam)["id"]
    comment_id = _comment(sam, post_id).get_json()["id"]

    ok = sam.post("/api/forum/reports", json={"type": "comment", "id": comment_id, "reason": "spam"})
    bad_reason = sam.post("/api/forum/reports", json={"type": "post", "id": post_id, "reason": "boring"})
    missing = sam.post("/api/forum/reports", json={
        "type": "post", "id": "1730000000000000-aaaaaaaaaaaa", "reason": "spam"})

    assert (ok.status_code, bad_reason.status_code, missing.status_code) == (201, 400, 404)


# ---------- Limits and safety ----------
def test_posting_is_rate_limited(sam, monkeypatch):
    monkeypatch.setitem(RATE_LIMITS, "post", (2, 600))

    statuses = [_post(sam, title=f"Rate limit check {i}").status_code for i in range(3)]

    assert statuses == [201, 201, 429]
    assert _post(sam).headers["Retry-After"] == "600"


def test_html_is_stored_as_plain_text(sam):
    post = _new_post(sam, title="<script>alert(1)</script>", body="<b>hello</b> there friend")

    assert post["title"] == "<script>alert(1)</script>"  # the frontend shows it as text


# ---------- Example post ----------
def test_example_post_added_once(make_app, forum_repository):
    client = make_app(forum_example=True).test_client()

    posts = client.get("/api/forum/posts").get_json()["posts"]
    client.get("/api/forum/posts")
    make_app(forum_example=True).test_client().get("/api/forum/posts")  # a new process

    assert len(forum_repository.posts) == 1
    [example] = posts
    assert example["title"] == "Welcome to the T Level forum: introduce yourself!"
    assert (example["author_name"], example["comment_count"]) == ("Team Rufus", 1)
    assert "topic" not in example
    assert example["is_mine"] is False
