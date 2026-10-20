"""AWS client construction.

Credentials are intentionally not accepted from application configuration.
Boto3 resolves them through the standard approved credential chain.
"""

import boto3
from botocore.config import Config

from .config import Settings


def get_dynamodb_resource(settings: Settings):
    """Return a DynamoDB service resource for the configured account."""

    session_kwargs = {"region_name": settings.aws_region}
    if settings.aws_profile:
        session_kwargs["profile_name"] = settings.aws_profile

    session = boto3.Session(**session_kwargs)
    resource_kwargs = {}
    if settings.aws_endpoint_url:
        resource_kwargs["endpoint_url"] = settings.aws_endpoint_url

    return session.resource("dynamodb", **resource_kwargs)



def get_s3_client(settings: Settings):
    """Return an S3 client that signs links for the configured region."""

    session_kwargs = {"region_name": settings.aws_region}
    if settings.aws_profile:
        session_kwargs["profile_name"] = settings.aws_profile

    session = boto3.Session(**session_kwargs)
    return session.client(
        "s3",
        # Regional virtual-hosted URLs work immediately for new buckets.
        endpoint_url=f"https://s3.{settings.aws_region}.amazonaws.com",
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    )


def _session(settings: Settings):
    session_kwargs = {"region_name": settings.aws_region}
    if settings.aws_profile:
        session_kwargs["profile_name"] = settings.aws_profile
    return boto3.Session(**session_kwargs)


def get_bedrock_runtime_client(settings: Settings):
    """Bedrock runtime client, used for ApplyGuardrail."""

    return _session(settings).client("bedrock-runtime")


def get_claude_client(settings: Settings):
    """Claude on Amazon Bedrock (Messages API), signed with AWS credentials."""

    # Imported here so the rest of the app starts even if the SDK is missing.
    from anthropic import AnthropicBedrockMantle

    return AnthropicBedrockMantle(aws_region=settings.chat_bedrock_region)
