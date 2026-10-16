"""AWS client construction.

Credentials are intentionally not accepted from application configuration.
Boto3 resolves them through the standard approved credential chain.
"""

import boto3

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

