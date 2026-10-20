"""Flask application factory for the T Level project backend."""

from flask import Flask

from .accounts import accounts
from .aws import get_dynamodb_resource, get_s3_client
from .config import Settings
from .content import S3ContentStore, content, load_catalogue
from .repositories import (
    ExpressionsOfInterestRepository,
    SessionsRepository,
    UsersRepository,
)
from .routes import api
from .saved import saved


def _settings_from_app(app: Flask) -> Settings:
    """Build runtime settings from Flask configuration."""

    return Settings(
        aws_region=app.config["AWS_REGION"],
        aws_profile=app.config.get("AWS_PROFILE"),
        dynamodb_table_name=app.config["DYNAMODB_TABLE_NAME"],
        users_table_name=app.config["USERS_TABLE_NAME"],
        sessions_table_name=app.config["SESSIONS_TABLE_NAME"],
        content_bucket_name=app.config.get("CONTENT_BUCKET_NAME"),
        session_hours=app.config["SESSION_HOURS"],
        remember_me_days=app.config["REMEMBER_ME_DAYS"],
        session_cookie_secure=app.config["SESSION_COOKIE_SECURE"],
        aws_endpoint_url=app.config.get("AWS_ENDPOINT_URL"),
        host=app.config["FLASK_HOST"],
        port=app.config["FLASK_PORT"],
        debug=app.config["FLASK_DEBUG"],
        max_content_length=app.config["MAX_CONTENT_LENGTH"],
    )


def create_app(
    test_config=None,
    repository=None,
    users_repository=None,
    sessions_repository=None,
    content_store=None,
    content_catalogue=None,
) -> Flask:
    """Create and configure the Flask application.

    The repositories, content store, and catalogue are injectable so tests can
    run without AWS. Production and local development use DynamoDB and S3 by
    default.
    """

    settings = Settings.from_env()
    app = Flask(__name__)
    app.config.from_mapping(
        AWS_REGION=settings.aws_region,
        AWS_PROFILE=settings.aws_profile,
        DYNAMODB_TABLE_NAME=settings.dynamodb_table_name,
        USERS_TABLE_NAME=settings.users_table_name,
        SESSIONS_TABLE_NAME=settings.sessions_table_name,
        CONTENT_BUCKET_NAME=settings.content_bucket_name,
        SESSION_HOURS=settings.session_hours,
        REMEMBER_ME_DAYS=settings.remember_me_days,
        SESSION_COOKIE_SECURE=settings.session_cookie_secure,
        AWS_ENDPOINT_URL=settings.aws_endpoint_url,
        FLASK_HOST=settings.host,
        FLASK_PORT=settings.port,
        FLASK_DEBUG=settings.debug,
        MAX_CONTENT_LENGTH=settings.max_content_length,
        TESTING=False,
    )

    if test_config:
        app.config.update(test_config)

    runtime_settings = _settings_from_app(app)

    if None in (repository, users_repository, sessions_repository):
        dynamodb = get_dynamodb_resource(runtime_settings)
        if repository is None:
            repository = ExpressionsOfInterestRepository(
                dynamodb.Table(runtime_settings.dynamodb_table_name)
            )
        if users_repository is None:
            users_repository = UsersRepository(
                dynamodb.Table(runtime_settings.users_table_name)
            )
        if sessions_repository is None:
            sessions_repository = SessionsRepository(
                dynamodb.Table(runtime_settings.sessions_table_name)
            )

    # Without a bucket the app still runs; downloads return HTTP 503.
    if content_store is None and runtime_settings.content_bucket_name:
        content_store = S3ContentStore(
            get_s3_client(runtime_settings),
            runtime_settings.content_bucket_name,
        )

    app.extensions["expressions_of_interest_repository"] = repository
    app.extensions["users_repository"] = users_repository
    app.extensions["sessions_repository"] = sessions_repository
    app.extensions["content_store"] = content_store
    app.extensions["content_catalogue"] = (
        content_catalogue if content_catalogue is not None else load_catalogue()
    )
    app.register_blueprint(api)
    app.register_blueprint(accounts)
    app.register_blueprint(content)
    app.register_blueprint(saved)
    return app
