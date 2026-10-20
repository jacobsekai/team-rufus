"""Environment-based application configuration."""

from dataclasses import dataclass
import os
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Runtime settings with safe local-development defaults."""

    aws_region: str
    aws_profile: Optional[str]
    dynamodb_table_name: str
    users_table_name: str
    sessions_table_name: str
    content_bucket_name: Optional[str]
    session_hours: int
    remember_me_days: int
    chat_model_id: str
    chat_guardrail_id: Optional[str]
    chat_guardrail_version: Optional[str]
    session_cookie_secure: bool
    aws_endpoint_url: Optional[str]
    host: str
    port: int
    debug: bool
    max_content_length: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            aws_region=os.getenv("AWS_REGION", "us-west-2"),
            aws_profile=os.getenv("AWS_PROFILE") or None,
            dynamodb_table_name=os.getenv(
                "DYNAMODB_TABLE_NAME",
                "t-level-expressions-of-interest-dev",
            ),
            users_table_name=os.getenv(
                "USERS_TABLE_NAME",
                "t-level-users-dev",
            ),
            sessions_table_name=os.getenv(
                "SESSIONS_TABLE_NAME",
                "t-level-sessions-dev",
            ),
            content_bucket_name=os.getenv("CONTENT_BUCKET_NAME") or None,
            session_hours=int(os.getenv("SESSION_HOURS", "12")),
            remember_me_days=int(os.getenv("REMEMBER_ME_DAYS", "30")),
            chat_model_id=os.getenv("CHAT_MODEL_ID", "anthropic.claude-opus-5-5"),
            # The chat assistant only runs when a Bedrock Guardrail is set.
            chat_guardrail_id=os.getenv("CHAT_GUARDRAIL_ID") or None,
            chat_guardrail_version=os.getenv("CHAT_GUARDRAIL_VERSION") or None,
            # Browsers only send Secure cookies over HTTPS. Set to 0 only when
            # testing locally over plain HTTP on a non-localhost address.
            session_cookie_secure=_as_bool(
                os.getenv("SESSION_COOKIE_SECURE"), default=True
            ),
            aws_endpoint_url=os.getenv("AWS_ENDPOINT_URL") or None,
            host=os.getenv("FLASK_HOST", "127.0.0.1"),
            port=int(os.getenv("FLASK_PORT", "5000")),
            debug=_as_bool(os.getenv("FLASK_DEBUG"), default=False),
            max_content_length=int(
                os.getenv("MAX_CONTENT_LENGTH", str(16 * 1024))
            ),
        )

