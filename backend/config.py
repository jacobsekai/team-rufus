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
    aws_endpoint_url: Optional[str]
    host: str
    port: int
    debug: bool
    max_content_length: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            aws_region=os.getenv("AWS_REGION", "eu-west-2"),
            aws_profile=os.getenv("AWS_PROFILE") or None,
            dynamodb_table_name=os.getenv(
                "DYNAMODB_TABLE_NAME",
                "t-level-expressions-of-interest-dev",
            ),
            aws_endpoint_url=os.getenv("AWS_ENDPOINT_URL") or None,
            host=os.getenv("FLASK_HOST", "127.0.0.1"),
            port=int(os.getenv("FLASK_PORT", "5000")),
            debug=_as_bool(os.getenv("FLASK_DEBUG"), default=False),
            max_content_length=int(
                os.getenv("MAX_CONTENT_LENGTH", str(16 * 1024))
            ),
        )

