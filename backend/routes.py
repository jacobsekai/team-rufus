"""HTTP routes and input validation."""

from datetime import datetime, timezone
from email.utils import parseaddr
import re
from typing import Any, Dict, List
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from werkzeug.security import generate_password_hash

from .repositories import DuplicateRecordError, RepositoryError


api = Blueprint("api", __name__)

ALLOWED_FIELDS = {
    "full_name",
    "email",
    "school",
    "interests",
    "consent",
}

SIGNUP_FIELDS = {
    "full_name",
    "email",
    "password",
}

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128

# PBKDF2 is used instead of Werkzeug's default scrypt because scrypt is not
# available in every Python build (for example the macOS system Python).
# 600,000 iterations follows the OWASP Password Storage Cheat Sheet.
PASSWORD_HASH_METHOD = "pbkdf2:sha256:600000"


def _error(message: str, status: int, details=None):
    payload = {"error": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def _normalize_email(email: str) -> str:
    return parseaddr(email.strip())[1].lower()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_payload(payload: Any) -> tuple[Dict[str, Any], List[str]]:
    if not isinstance(payload, dict):
        return {}, ["The request body must be a JSON object."]

    errors: List[str] = []
    unknown_fields = sorted(set(payload) - ALLOWED_FIELDS)
    if unknown_fields:
        errors.append(
            "Unknown fields: " + ", ".join(unknown_fields) + "."
        )

    full_name = payload.get("full_name")
    if not isinstance(full_name, str) or not 1 <= len(full_name.strip()) <= 100:
        errors.append("full_name must be between 1 and 100 characters.")

    email = payload.get("email")
    if not isinstance(email, str):
        errors.append("email is required.")
    elif not EMAIL_PATTERN.fullmatch(_normalize_email(email)):
        errors.append("email must be a valid email address.")

    school = payload.get("school", "")
    if not isinstance(school, str) or len(school.strip()) > 200:
        errors.append("school must be 200 characters or fewer.")

    interests = payload.get("interests", [])
    if (
        not isinstance(interests, list)
        or len(interests) > 10
        or any(
            not isinstance(item, str) or not 1 <= len(item.strip()) <= 100
            for item in interests
        )
    ):
        errors.append(
            "interests must be a list of up to 10 non-empty strings, "
            "each no longer than 100 characters."
        )

    if payload.get("consent") is not True:
        errors.append("consent must be true.")

    normalized = {
        "full_name": full_name.strip() if isinstance(full_name, str) else "",
        "email": _normalize_email(email) if isinstance(email, str) else "",
        "school": school.strip() if isinstance(school, str) else "",
        "interests": [
            item.strip()
            for item in interests
            if isinstance(item, str)
        ]
        if isinstance(interests, list)
        else [],
        "consent": True,
    }
    return normalized, errors


def _validate_signup(payload: Any) -> tuple[Dict[str, Any], List[str]]:
    if not isinstance(payload, dict):
        return {}, ["The request body must be a JSON object."]

    errors: List[str] = []
    unknown_fields = sorted(set(payload) - SIGNUP_FIELDS)
    if unknown_fields:
        errors.append(
            "Unknown fields: " + ", ".join(unknown_fields) + "."
        )

    full_name = payload.get("full_name")
    if not isinstance(full_name, str) or not 1 <= len(full_name.strip()) <= 100:
        errors.append("full_name must be between 1 and 100 characters.")

    email = payload.get("email")
    if not isinstance(email, str):
        errors.append("email is required.")
    elif not EMAIL_PATTERN.fullmatch(_normalize_email(email)):
        errors.append("email must be a valid email address.")

    # Passwords are not stripped: spaces are valid password characters.
    password = payload.get("password")
    if (
        not isinstance(password, str)
        or not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH
    ):
        errors.append(
            f"password must be between {PASSWORD_MIN_LENGTH} and "
            f"{PASSWORD_MAX_LENGTH} characters."
        )

    if errors:
        return {}, errors

    return {
        "full_name": full_name.strip(),
        "email": _normalize_email(email),
        "password": password,
    }, []


@api.get("/health")
def health():
    """Return a non-sensitive liveness response."""

    return jsonify({"status": "ok"}), 200


@api.post("/api/expressions-of-interest")
def create_expression_of_interest():
    """Validate and store a new expression of interest."""

    if not request.is_json:
        return _error("Content-Type must be application/json.", 415)

    payload = request.get_json(silent=True)
    normalized, errors = _validate_payload(payload)
    if errors:
        return _error("Validation failed.", 400, errors)

    timestamp = _utc_timestamp()
    record = {
        "id": str(uuid4()),
        **normalized,
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    repository = current_app.extensions["expressions_of_interest_repository"]
    try:
        repository.save(record)
    except RepositoryError:
        current_app.logger.exception(
            "Failed to persist expression-of-interest record."
        )
        return _error("The submission could not be saved.", 503)

    return jsonify({"id": record["id"], "status": "received"}), 201



@api.post("/api/users")
def create_user():
    """Register a new user account.

    The password is hashed before storage and is never returned or logged.
    """

    if not request.is_json:
        return _error("Content-Type must be application/json.", 415)

    payload = request.get_json(silent=True)
    signup, errors = _validate_signup(payload)
    if errors:
        return _error("Validation failed.", 400, errors)

    timestamp = _utc_timestamp()
    user = {
        "email": signup["email"],
        "id": str(uuid4()),
        "full_name": signup["full_name"],
        "password_hash": generate_password_hash(
            signup["password"], method=PASSWORD_HASH_METHOD
        ),
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    repository = current_app.extensions["users_repository"]
    try:
        repository.create_user(user)
    except DuplicateRecordError:
        return _error("An account with this email already exists.", 409)
    except RepositoryError:
        current_app.logger.exception("Failed to persist user account.")
        return _error("The account could not be created.", 503)

    return jsonify(
        {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "status": "created",
        }
    ), 201
