"""Downloadable content tests."""

import json

import pytest

from backend.content import S3ContentStore, load_catalogue


PASSWORD = "correct horse battery"


def _sign_up(client):
    client.post(
        "/api/users",
        json={"full_name": "Example Member", "email": "member@example.com", "password": PASSWORD},
    )


def test_list_content_when_signed_out(client):
    response = client.get("/api/content")

    assert response.status_code == 200
    body = response.get_json()
    assert body["signed_in"] is False
    assert [item["id"] for item in body["items"]] == ["public-guide", "members-guide"]
    assert body["items"][1] == {
        "id": "members-guide",
        "title": "Members guide",
        "description": "Sign-in needed.",
        "requires_login": True,
        "download_url": "/api/content/members-guide/download",
    }


def test_list_content_when_signed_in(client):
    _sign_up(client)

    assert client.get("/api/content").get_json()["signed_in"] is True


def test_public_download_redirects_to_signed_link(client):
    response = client.get("/api/content/public-guide/download")

    assert response.status_code == 302
    assert response.headers["Location"] == (
        "https://downloads.example.com/guides/public-guide.txt?signature=test"
    )
    assert response.headers["Cache-Control"] == "no-store"


def test_members_download_requires_sign_in(client):
    response = client.get("/api/content/members-guide/download")

    assert response.status_code == 401
    assert "Location" not in response.headers


def test_members_download_when_signed_in(client):
    _sign_up(client)
    response = client.get("/api/content/members-guide/download")

    assert response.status_code == 302
    assert "members/members-guide.txt" in response.headers["Location"]


def test_members_download_after_logout_is_refused(client):
    _sign_up(client)
    client.post("/api/logout")

    assert client.get("/api/content/members-guide/download").status_code == 401


def test_unknown_content_is_404(client):
    assert client.get("/api/content/does-not-exist/download").status_code == 404


def test_downloads_unavailable_without_bucket(make_app):
    client = make_app(content_store=None).test_client()

    assert client.get("/api/content/public-guide/download").status_code == 503


def test_real_catalogue_is_valid():
    items = load_catalogue()

    assert items
    assert any(item["requires_login"] for item in items)
    assert any(not item["requires_login"] for item in items)


VALID_ITEM = {
    "id": "a-guide",
    "title": "A guide",
    "description": "About something.",
    "file": "guides/a-guide.pdf",
    "requires_login": False,
}


@pytest.mark.parametrize(
    "items, message",
    [
        ({"id": "x"}, "must be a JSON list"),
        ([VALID_ITEM, VALID_ITEM], "repeats the id"),
        ([{**VALID_ITEM, "id": "Has Spaces"}], "invalid id"),
        ([{**VALID_ITEM, "file": "../secrets.txt"}], "invalid file path"),
        ([{**VALID_ITEM, "requires_login": "yes"}], "requires_login"),
        ([{**VALID_ITEM, "extra": 1}], "must have exactly"),
        ([{**VALID_ITEM, "title": " "}], "needs a title"),
    ],
)
def test_catalogue_validation(tmp_path, items, message):
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps(items))

    with pytest.raises(ValueError, match=message):
        load_catalogue(path)


def test_s3_content_store_creates_short_lived_attachment_link():
    class RecordingS3Client:
        def generate_presigned_url(self, operation, Params, ExpiresIn):
            self.call = (operation, Params, ExpiresIn)
            return "https://signed.example.com"

    s3 = RecordingS3Client()
    url = S3ContentStore(s3, "content-bucket").download_url("members/guide.pdf")

    assert url == "https://signed.example.com"
    assert s3.call == (
        "get_object",
        {
            "Bucket": "content-bucket",
            "Key": "members/guide.pdf",
            "ResponseContentDisposition": 'attachment; filename="guide.pdf"',
        },
        300,
    )
