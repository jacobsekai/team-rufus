"""Small helpers shared by the route modules."""

from datetime import datetime, timezone
from email.utils import parseaddr
import re
from typing import Any, Iterable, List, Optional

from flask import jsonify, request


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def error_response(message: str, status: int, details=None):
    payload = {"error": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def json_body_or_error():
    """Return ``(payload, None)`` or ``(None, error_response)`` for non-JSON."""

    if not request.is_json:
        return None, error_response("Content-Type must be application/json.", 415)
    return request.get_json(silent=True), None


def unknown_fields_error(payload: dict, allowed: Iterable[str]) -> Optional[str]:
    unknown = sorted(set(payload) - set(allowed))
    if unknown:
        return "Unknown fields: " + ", ".join(unknown) + "."
    return None


def normalize_email(email: str) -> str:
    return parseaddr(email.strip())[1].lower()


def validate_email(email: Any, errors: List[str]) -> None:
    if not isinstance(email, str):
        errors.append("email is required.")
    elif not EMAIL_PATTERN.fullmatch(normalize_email(email)):
        errors.append("email must be a valid email address.")


def validate_full_name(full_name: Any, errors: List[str]) -> None:
    if not isinstance(full_name, str) or not 1 <= len(full_name.strip()) <= 100:
        errors.append("full_name must be between 1 and 100 characters.")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")
