"""Run the backend locally with ``python -m backend``."""

from . import create_app


def main() -> None:
    app = create_app()
    app.run(
        host=app.config["FLASK_HOST"],
        port=app.config["FLASK_PORT"],
        debug=app.config["FLASK_DEBUG"],
    )


if __name__ == "__main__":
    main()

