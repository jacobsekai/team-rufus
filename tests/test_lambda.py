"""Check the Flask app works behind API Gateway's Lambda event format."""

import json

from apig_wsgi import make_lambda_handler

from backend import create_app


def _http_api_event(method, path, body=None):
    """Build a minimal API Gateway HTTP API (payload v2.0) event."""

    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {
            "content-type": "application/json",
            "host": "example.execute-api.eu-west-2.amazonaws.com",
            "x-forwarded-proto": "https",
            "x-forwarded-port": "443",
        },
        "requestContext": {
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "192.0.2.1",
            },
        },
        "body": json.dumps(body) if body is not None else "",
        "isBase64Encoded": False,
    }


def test_signup_through_lambda_event(repository, users_repository):
    app = create_app(
        {"TESTING": True},
        repository=repository,
        users_repository=users_repository,
    )
    handler = make_lambda_handler(app)

    response = handler(
        _http_api_event(
            "POST",
            "/api/users",
            {
                "full_name": "Example Student",
                "email": "student@example.com",
                "password": "correct horse battery",
            },
        ),
        None,
    )

    assert response["statusCode"] == 201
    assert json.loads(response["body"])["status"] == "created"
    assert "student@example.com" in users_repository.users


def test_health_through_lambda_event(repository, users_repository):
    app = create_app(
        {"TESTING": True},
        repository=repository,
        users_repository=users_repository,
    )
    handler = make_lambda_handler(app)

    response = handler(_http_api_event("GET", "/health"), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"status": "ok"}
