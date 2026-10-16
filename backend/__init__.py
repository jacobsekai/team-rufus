"""Flask application factory for the T Level project backend."""

from flask import Flask

from .aws import get_dynamodb_resource
from .config import Settings
from .repositories import ExpressionsOfInterestRepository, UsersRepository
from .routes import api


def _settings_from_app(app: Flask) -> Settings:
    """Build runtime settings from Flask configuration."""

    return Settings(
        aws_region=app.config["AWS_REGION"],
        aws_profile=app.config.get("AWS_PROFILE"),
        dynamodb_table_name=app.config["DYNAMODB_TABLE_NAME"],
        users_table_name=app.config["USERS_TABLE_NAME"],
        aws_endpoint_url=app.config.get("AWS_ENDPOINT_URL"),
        host=app.config["FLASK_HOST"],
        port=app.config["FLASK_PORT"],
        debug=app.config["FLASK_DEBUG"],
        max_content_length=app.config["MAX_CONTENT_LENGTH"],
    )


def create_app(test_config=None, repository=None, users_repository=None) -> Flask:
    """Create and configure the Flask application.

    ``repository`` and ``users_repository`` are injectable so tests can run
    without AWS. Production and local development use the DynamoDB
    repositories by default.
    """

    settings = Settings.from_env()
    app = Flask(__name__)
    app.config.from_mapping(
        AWS_REGION=settings.aws_region,
        AWS_PROFILE=settings.aws_profile,
        DYNAMODB_TABLE_NAME=settings.dynamodb_table_name,
        USERS_TABLE_NAME=settings.users_table_name,
        AWS_ENDPOINT_URL=settings.aws_endpoint_url,
        FLASK_HOST=settings.host,
        FLASK_PORT=settings.port,
        FLASK_DEBUG=settings.debug,
        MAX_CONTENT_LENGTH=settings.max_content_length,
        TESTING=False,
    )

    if test_config:
        app.config.update(test_config)

    if repository is None or users_repository is None:
        runtime_settings = _settings_from_app(app)
        dynamodb = get_dynamodb_resource(runtime_settings)
        if repository is None:
            repository = ExpressionsOfInterestRepository(
                dynamodb.Table(runtime_settings.dynamodb_table_name)
            )
        if users_repository is None:
            users_repository = UsersRepository(
                dynamodb.Table(runtime_settings.users_table_name)
            )

    app.extensions["expressions_of_interest_repository"] = repository
    app.extensions["users_repository"] = users_repository
    app.register_blueprint(api)
    return app
