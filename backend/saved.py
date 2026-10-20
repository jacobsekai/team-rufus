"""Saved subjects and guides for signed-in users.

Saved items live on the user's own record as a map from "type:id" to the
time it was saved, so loading the list needs no extra table or query.
"""

import re
from typing import Any, Dict, List, Tuple

from flask import Blueprint, current_app, g, jsonify

from .accounts import login_required
from .helpers import error_response, json_body_or_error, unknown_fields_error, utc_timestamp
from .repositories import RepositoryError
from .routes import SUBJECT_IDS


saved = Blueprint("saved", __name__)

SAVED_ITEM_FIELDS = {"type", "id"}
SAVED_ITEM_TYPES = ("subject", "guide")
MAX_SAVED_ITEMS = 50

# Guides are frontend pages, so the backend checks the ID's shape only.
_GUIDE_ID_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")


def _items(user: Dict[str, Any]) -> Dict[str, str]:
    return dict(user.get("saved") or {})


def _as_list(saved_map: Dict[str, str]) -> List[Dict[str, str]]:
    items = []
    for key, saved_at in saved_map.items():
        item_type, item_id = key.split(":", 1)
        items.append({"type": item_type, "id": item_id, "saved_at": saved_at})
    # Newest first.
    return sorted(items, key=lambda item: item["saved_at"], reverse=True)


def _validate_item(payload: Any) -> Tuple[str, List[str]]:
    if not isinstance(payload, dict):
        return "", ["The request body must be a JSON object."]

    errors: List[str] = []
    unknown = unknown_fields_error(payload, SAVED_ITEM_FIELDS)
    if unknown:
        errors.append(unknown)

    item_type = payload.get("type")
    item_id = payload.get("id")
    if item_type not in SAVED_ITEM_TYPES:
        errors.append("type must be one of: " + ", ".join(SAVED_ITEM_TYPES) + ".")
    elif item_type == "subject" and item_id not in SUBJECT_IDS:
        errors.append("id must be one of: " + ", ".join(SUBJECT_IDS) + ".")
    elif item_type == "guide" and (
        not isinstance(item_id, str) or not _GUIDE_ID_PATTERN.fullmatch(item_id)
    ):
        errors.append("id must be 1 to 64 lowercase letters, numbers or dashes.")

    if errors:
        return "", errors
    return f"{item_type}:{item_id}", []


def _save(user: Dict[str, Any], saved_map: Dict[str, str]) -> None:
    current_app.extensions["users_repository"].set_saved_items(
        user["email"], saved_map, utc_timestamp()
    )


@saved.get("/api/users/me/saved")
@login_required
def list_saved_items():
    """List the signed-in user's saved subjects and guides."""

    return jsonify({"items": _as_list(_items(g.current_user))}), 200


@saved.post("/api/users/me/saved")
@login_required
def save_item():
    """Save a subject or guide. Saving something twice is harmless."""

    payload, error = json_body_or_error()
    if error:
        return error
    key, errors = _validate_item(payload)
    if errors:
        return error_response("Validation failed.", 400, errors)

    saved_map = _items(g.current_user)
    if key in saved_map:
        return jsonify({"items": _as_list(saved_map), "status": "already_saved"}), 200
    if len(saved_map) >= MAX_SAVED_ITEMS:
        return error_response(f"You can save up to {MAX_SAVED_ITEMS} items.", 400)

    saved_map[key] = utc_timestamp()
    try:
        _save(g.current_user, saved_map)
    except RepositoryError:
        current_app.logger.exception("Failed to save an item.")
        return error_response("The item could not be saved.", 503)
    return jsonify({"items": _as_list(saved_map), "status": "saved"}), 201


# POST rather than DELETE: CloudFront's signed requests to the Lambda function
# URL reject DELETE requests that have a body.
@saved.post("/api/users/me/saved/remove")
@login_required
def remove_item():
    """Remove a saved subject or guide. Removing something unsaved is harmless."""

    payload, error = json_body_or_error()
    if error:
        return error
    key, errors = _validate_item(payload)
    if errors:
        return error_response("Validation failed.", 400, errors)

    saved_map = _items(g.current_user)
    if key not in saved_map:
        return jsonify({"items": _as_list(saved_map), "status": "not_saved"}), 200

    del saved_map[key]
    try:
        _save(g.current_user, saved_map)
    except RepositoryError:
        current_app.logger.exception("Failed to remove a saved item.")
        return error_response("The item could not be removed.", 503)
    return jsonify({"items": _as_list(saved_map), "status": "removed"}), 200
