"""User accounts: sign up, sign in, sign out, and "my account".

Sessions are server-side. The browser holds a random token in an HttpOnly
cookie; DynamoDB stores only a SHA-256 hash of it, so signing out or deleting
an account ends the session immediately.
"""

from datetime import timedelta
from functools import lru_cache, wraps
import hashlib
import secrets
from typing import Any, Dict, List, Optional
from uuid import uuid4

from flask import Blueprint, current_app, g, jsonify, make_response, request
from werkzeug.security import check_password_hash, generate_password_hash

from .helpers import (
    error_response,
    json_body_or_error,
    normalize_email,
    unknown_fields_error,
    utc_now,
    utc_timestamp,
    validate_email,
    validate_full_name,
)
from .repositories import DuplicateRecordError, RepositoryError


accounts = Blueprint("accounts", __name__)

SIGNUP_FIELDS = {"full_name", "email", "password"}
LOGIN_FIELDS = {"email", "password"}
DELETE_ACCOUNT_FIELDS = {"password"}

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128

# PBKDF2 is used instead of Werkzeug's default scrypt because scrypt is not
# available in every Python build (for example the macOS system Python).
# 600,000 iterations follows the OWASP Password Storage Cheat Sheet.
PASSWORD_HASH_METHOD = "pbkdf2:sha256:600000"

SESSION_COOKIE_NAME = "rufus_session"

# After this many wrong passwords in a row the account is locked for
# LOCKOUT_SECONDS, which slows down password guessing.
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60

INVALID_LOGIN_MESSAGE = "Email or password is incorrect."
SIGN_IN_REQUIRED_MESSAGE = "You need to sign in."


def hash_password(password: str) -> str:
    return generate_password_hash(password, method=PASSWORD_HASH_METHOD)


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    # Checked when the email is unknown so the response takes as long as a
    # real password check and does not reveal which emails are registered.
    return hash_password(secrets.token_urlsafe(16))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _users():
    return current_app.extensions["users_repository"]


def _sessions():
    return current_app.extensions["sessions_repository"]


def _public_profile(user: Dict[str, Any]) -> Dict[str, Any]:
    """Fields that are safe to return to the signed-in user."""

    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "created_at": user["created_at"],
    }


def _set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=current_app.config["SESSION_HOURS"] * 3600,
        secure=current_app.config["SESSION_COOKIE_SECURE"],
        httponly=True,
        samesite="Strict",
        path="/",
    )


def _clear_session_cookie(response) -> None:
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        secure=current_app.config["SESSION_COOKIE_SECURE"],
        httponly=True,
        samesite="Strict",
        path="/",
    )


def _start_session(response, email: str) -> None:
    token = secrets.token_urlsafe(32)
    now = utc_now()
    expires = now + timedelta(hours=current_app.config["SESSION_HOURS"])
    _sessions().create_session(
        {
            "token_hash": _token_hash(token),
            "email": email,
            "created_at": utc_timestamp(),
            # Epoch seconds, as required by DynamoDB time-to-live.
            "expires_at": int(expires.timestamp()),
        }
    )
    _set_session_cookie(response, token)


def current_user() -> Optional[Dict[str, Any]]:
    """Return the signed-in user, or ``None``.

    The result is cached on ``flask.g`` for the rest of the request.
    """

    if "current_user" in g:
        return g.current_user

    g.current_user = None
    g.session_token_hash = None

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    token_hash = _token_hash(token)
    session = _sessions().get_session(token_hash)
    if session is None:
        return None

    if int(session["expires_at"]) <= utc_now().timestamp():
        _sessions().delete_session(token_hash)
        return None

    user = _users().get_user(session["email"])
    if user is None:
        return None

    g.current_user = user
    g.session_token_hash = token_hash
    return user


def _sign_in_required_response():
    response = make_response(error_response(SIGN_IN_REQUIRED_MESSAGE, 401))
    if request.cookies.get(SESSION_COOKIE_NAME):
        _clear_session_cookie(response)
    return response


def login_required(view):
    """Allow the view only for signed-in users; otherwise return HTTP 401."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            user = current_user()
        except RepositoryError:
            current_app.logger.exception("Failed to check the session.")
            return error_response("Unable to check your session.", 503)
        if user is None:
            return _sign_in_required_response()
        return view(*args, **kwargs)

    return wrapped


def _validate_password_length(password: Any, errors: List[str]) -> None:
    if (
        not isinstance(password, str)
        or not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH
    ):
        errors.append(
            f"password must be between {PASSWORD_MIN_LENGTH} and "
            f"{PASSWORD_MAX_LENGTH} characters."
        )


def _validate_signup(payload: Any) -> tuple[Dict[str, Any], List[str]]:
    if not isinstance(payload, dict):
        return {}, ["The request body must be a JSON object."]

    errors: List[str] = []
    unknown = unknown_fields_error(payload, SIGNUP_FIELDS)
    if unknown:
        errors.append(unknown)

    full_name = payload.get("full_name")
    validate_full_name(full_name, errors)

    email = payload.get("email")
    validate_email(email, errors)

    # Passwords are not stripped: spaces are valid password characters.
    password = payload.get("password")
    _validate_password_length(password, errors)

    if errors:
        return {}, errors

    return {
        "full_name": full_name.strip(),
        "email": normalize_email(email),
        "password": password,
    }, []


def _validate_login(payload: Any) -> tuple[Dict[str, Any], List[str]]:
    if not isinstance(payload, dict):
        return {}, ["The request body must be a JSON object."]

    errors: List[str] = []
    unknown = unknown_fields_error(payload, LOGIN_FIELDS)
    if unknown:
        errors.append(unknown)

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip():
        errors.append("email is required.")

    password = payload.get("password")
    if (
        not isinstance(password, str)
        or not 1 <= len(password) <= PASSWORD_MAX_LENGTH
    ):
        errors.append("password is required.")

    if errors:
        return {}, errors
    return {"email": normalize_email(email), "password": password}, []


@accounts.post("/api/users")
def create_user():
    """Register a new user account and sign them in.

    The password is hashed before storage and is never returned or logged.
    """

    payload, error = json_body_or_error()
    if error:
        return error

    signup, errors = _validate_signup(payload)
    if errors:
        return error_response("Validation failed.", 400, errors)

    timestamp = utc_timestamp()
    user = {
        "email": signup["email"],
        "id": str(uuid4()),
        "full_name": signup["full_name"],
        "password_hash": hash_password(signup["password"]),
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    response = make_response(
        jsonify({**_public_profile(user), "status": "created"}), 201
    )
    try:
        _users().create_user(user)
    except DuplicateRecordError:
        return error_response("An account with this email already exists.", 409)
    except RepositoryError:
        current_app.logger.exception("Failed to persist user account.")
        return error_response("The account could not be created.", 503)

    try:
        _start_session(response, user["email"])
    except RepositoryError:
        # The account exists, so still report success; the user can sign in.
        current_app.logger.exception("Failed to start a session after signup.")

    return response


@accounts.post("/api/login")
def login():
    """Check an email and password and start a session."""

    payload, error = json_body_or_error()
    if error:
        return error

    credentials, errors = _validate_login(payload)
    if errors:
        return error_response("Validation failed.", 400, errors)

    try:
        user = _users().get_user(credentials["email"])

        if user is None:
            check_password_hash(_dummy_password_hash(), credentials["password"])
            return error_response(INVALID_LOGIN_MESSAGE, 401)

        locked_until = int(user.get("locked_until", 0))
        now = int(utc_now().timestamp())
        if locked_until > now:
            response = make_response(
                error_response(
                    "Too many failed sign-in attempts. Try again later.", 429
                )
            )
            response.headers["Retry-After"] = str(locked_until - now)
            return response

        if not check_password_hash(user["password_hash"], credentials["password"]):
            failures = _users().record_failed_login(user["email"])
            if failures >= MAX_FAILED_LOGINS:
                _users().lock_user(user["email"], now + LOCKOUT_SECONDS)
            return error_response(INVALID_LOGIN_MESSAGE, 401)

        if user.get("failed_login_count") or user.get("locked_until"):
            _users().clear_failed_logins(user["email"])

        response = make_response(
            jsonify({**_public_profile(user), "status": "signed_in"}), 200
        )
        _start_session(response, user["email"])
    except RepositoryError:
        current_app.logger.exception("Failed to sign the user in.")
        return error_response("Unable to sign in right now.", 503)

    return response


@accounts.post("/api/logout")
def logout():
    """End the current session. Safe to call when not signed in."""

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        try:
            _sessions().delete_session(_token_hash(token))
        except RepositoryError:
            current_app.logger.exception("Failed to delete the session.")
            return error_response("Unable to sign out right now.", 503)

    response = make_response(jsonify({"status": "signed_out"}), 200)
    _clear_session_cookie(response)
    return response


@accounts.get("/api/users/me")
@login_required
def get_my_account():
    """Return the signed-in user's own details (UK GDPR right of access)."""

    return jsonify(_public_profile(g.current_user)), 200


@accounts.delete("/api/users/me")
@login_required
def delete_my_account():
    """Delete the signed-in user's account (UK GDPR right to erasure).

    The password must be confirmed so a session left open on a shared computer
    cannot be used to delete someone's account.
    """

    payload, error = json_body_or_error()
    if error:
        return error

    errors: List[str] = []
    if not isinstance(payload, dict):
        errors.append("The request body must be a JSON object.")
    else:
        unknown = unknown_fields_error(payload, DELETE_ACCOUNT_FIELDS)
        if unknown:
            errors.append(unknown)
        if not isinstance(payload.get("password"), str):
            errors.append("password is required.")
    if errors:
        return error_response("Validation failed.", 400, errors)

    user = g.current_user
    if not check_password_hash(user["password_hash"], payload["password"]):
        # Not 403: CloudFront replaces every 403 with the Midway sign-in page.
        return error_response("Password is incorrect.", 400)

    try:
        _users().delete_user(user["email"])
    except RepositoryError:
        current_app.logger.exception("Failed to delete the account.")
        return error_response("The account could not be deleted.", 503)

    try:
        _sessions().delete_session(g.session_token_hash)
    except RepositoryError:
        # Harmless: a session whose user no longer exists is never accepted.
        current_app.logger.exception("Failed to delete the session.")

    response = make_response(jsonify({"status": "deleted"}), 200)
    _clear_session_cookie(response)
    return response
