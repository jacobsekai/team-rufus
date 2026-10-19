"""Downloadable content.

The catalogue (``content_catalogue.json``) lists each file and whether an
account is needed to download it. Files are kept in a private S3 bucket and
handed out as short-lived pre-signed links, so a link cannot be shared for
long and members-only files are never publicly readable.
"""

import json
from pathlib import Path
import posixpath
import re
from typing import Any, Dict, List

from flask import Blueprint, current_app, jsonify, redirect

from .accounts import current_user
from .helpers import error_response
from .repositories import RepositoryError


content = Blueprint("content", __name__)

DEFAULT_CATALOGUE_PATH = Path(__file__).with_name("content_catalogue.json")

# Pre-signed download links stop working after this many seconds.
DOWNLOAD_LINK_SECONDS = 300

_ITEM_ID_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")
_FILE_PATTERN = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")


def load_catalogue(path: Path = DEFAULT_CATALOGUE_PATH) -> List[Dict[str, Any]]:
    """Load and validate the content catalogue.

    Raises ``ValueError`` with a clear message if the file is malformed, so a
    bad edit fails at start-up instead of when someone clicks a download.
    """

    with open(path, encoding="utf-8") as handle:
        items = json.load(handle)

    if not isinstance(items, list):
        raise ValueError("The content catalogue must be a JSON list.")

    seen_ids = set()
    for index, item in enumerate(items):
        where = f"Content catalogue item {index}"
        if not isinstance(item, dict):
            raise ValueError(f"{where} must be an object.")
        if set(item) != {"id", "title", "description", "file", "requires_login"}:
            raise ValueError(
                f"{where} must have exactly: id, title, description, file, "
                "requires_login."
            )
        if not isinstance(item["id"], str) or not _ITEM_ID_PATTERN.fullmatch(item["id"]):
            raise ValueError(f"{where} has an invalid id.")
        if item["id"] in seen_ids:
            raise ValueError(f"{where} repeats the id {item['id']!r}.")
        seen_ids.add(item["id"])
        if not isinstance(item["title"], str) or not item["title"].strip():
            raise ValueError(f"{where} needs a title.")
        if not isinstance(item["description"], str):
            raise ValueError(f"{where} needs a description.")
        if (
            not isinstance(item["file"], str)
            or not _FILE_PATTERN.fullmatch(item["file"])
            or ".." in item["file"].split("/")
        ):
            raise ValueError(f"{where} has an invalid file path.")
        if not isinstance(item["requires_login"], bool):
            raise ValueError(f"{where} requires_login must be true or false.")

    return items


class S3ContentStore:
    """Creates pre-signed download links for files in the content bucket."""

    def __init__(self, s3_client, bucket_name: str):
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def download_url(self, key: str) -> str:
        filename = posixpath.basename(key)
        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=DOWNLOAD_LINK_SECONDS,
        )


def _catalogue() -> List[Dict[str, Any]]:
    return current_app.extensions["content_catalogue"]


def _public_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item["id"],
        "title": item["title"],
        "description": item["description"],
        "requires_login": item["requires_login"],
        "download_url": f"/api/content/{item['id']}/download",
    }


@content.get("/api/content")
def list_content():
    """List all downloadable content and whether the visitor is signed in."""

    try:
        signed_in = current_user() is not None
    except RepositoryError:
        current_app.logger.exception("Failed to check the session.")
        signed_in = False

    return jsonify(
        {
            "signed_in": signed_in,
            "items": [_public_item(item) for item in _catalogue()],
        }
    ), 200


@content.get("/api/content/<item_id>/download")
def download_content(item_id: str):
    """Redirect to a short-lived download link for one catalogue item."""

    item = next((i for i in _catalogue() if i["id"] == item_id), None)
    if item is None:
        return error_response("Content not found.", 404)

    if item["requires_login"]:
        try:
            if current_user() is None:
                return error_response(
                    "You need to sign in to download this content.", 401
                )
        except RepositoryError:
            current_app.logger.exception("Failed to check the session.")
            return error_response("Unable to check your session.", 503)

    store = current_app.extensions["content_store"]
    if store is None:
        return error_response("Downloads are not configured.", 503)

    try:
        url = store.download_url(item["file"])
    except Exception:
        current_app.logger.exception("Failed to create a download link.")
        return error_response("The download is not available right now.", 503)

    response = redirect(url, code=302)
    # The link expires, so browsers and CloudFront must not reuse it.
    response.headers["Cache-Control"] = "no-store"
    return response
