"""Health check and expression-of-interest routes."""

from typing import Any, Dict, List
from uuid import uuid4

from flask import Blueprint, current_app, jsonify

from .helpers import (
    error_response,
    json_body_or_error,
    normalize_email,
    unknown_fields_error,
    utc_timestamp,
    validate_email,
    validate_full_name,
)
from .repositories import RepositoryError


api = Blueprint("api", __name__)

ALLOWED_FIELDS = {
    "full_name",
    "email",
    "customer_type",
    "school",
    "interests",
    "consent",
}

# The brief's customers: students, schools, and people around students.
CUSTOMER_TYPES = ("student", "school", "parent_carer", "other")

# Amazon Emerging Talent placement areas named in the brief.
PLACEMENT_AREAS = ("Digital", "Business", "Media", "Finance", "Engineering")
_PLACEMENT_AREAS_BY_KEY = {area.lower(): area for area in PLACEMENT_AREAS}


def _normalize_interests(interests: Any, errors: List[str]) -> List[str]:
    """Return interests as canonical placement-area names without duplicates."""

    if not isinstance(interests, list) or not all(
        isinstance(item, str) for item in interests
    ):
        errors.append("interests must be a list of placement areas.")
        return []

    normalized: List[str] = []
    unknown: List[str] = []
    for item in interests:
        area = _PLACEMENT_AREAS_BY_KEY.get(item.strip().lower())
        if area is None:
            unknown.append(item)
        elif area not in normalized:
            normalized.append(area)

    if unknown:
        errors.append(
            "interests must only contain: " + ", ".join(PLACEMENT_AREAS) + "."
        )
    return normalized


def _validate_payload(payload: Any) -> tuple[Dict[str, Any], List[str]]:
    if not isinstance(payload, dict):
        return {}, ["The request body must be a JSON object."]

    errors: List[str] = []
    unknown = unknown_fields_error(payload, ALLOWED_FIELDS)
    if unknown:
        errors.append(unknown)

    full_name = payload.get("full_name")
    validate_full_name(full_name, errors)

    email = payload.get("email")
    validate_email(email, errors)

    customer_type = payload.get("customer_type")
    if customer_type not in CUSTOMER_TYPES:
        errors.append(
            "customer_type must be one of: " + ", ".join(CUSTOMER_TYPES) + "."
        )

    school = payload.get("school", "")
    if not isinstance(school, str) or len(school.strip()) > 200:
        errors.append("school must be 200 characters or fewer.")

    interests = _normalize_interests(payload.get("interests", []), errors)

    if payload.get("consent") is not True:
        errors.append("consent must be true.")

    if errors:
        return {}, errors

    return {
        "full_name": full_name.strip(),
        "email": normalize_email(email),
        "customer_type": customer_type,
        "school": school.strip(),
        "interests": interests,
        "consent": True,
    }, []


@api.get("/health")
def health():
    """Return a non-sensitive liveness response."""

    return jsonify({"status": "ok"}), 200


@api.post("/api/expressions-of-interest")
def create_expression_of_interest():
    """Validate and store a new expression of interest."""

    payload, error = json_body_or_error()
    if error:
        return error

    normalized, errors = _validate_payload(payload)
    if errors:
        return error_response("Validation failed.", 400, errors)

    timestamp = utc_timestamp()
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
        return error_response("The submission could not be saved.", 503)

    return jsonify({"id": record["id"], "status": "received"}), 201
