# T Level Team Project — Backend

This repository contains the Flask backend for the Amazon T Level project.
The current backend scope is the expression-of-interest feature and user
account signup, both backed by Amazon DynamoDB.

## Stack

- Python
- Flask
- Boto3
- Amazon DynamoDB
- Pytest

The front end is maintained separately using HTML, CSS, and JavaScript.

## Repository layout

```text
backend/
  __init__.py                 Flask application factory
  __main__.py                 Local entry point
  lambda_handler.py           AWS Lambda entry point
  accounts.py                 Sign up, sign in/out, sessions, my account
  content.py                  Downloadable content and download links
  content_catalogue.json      List of downloadable files
  helpers.py                  Shared validation and response helpers
  saved.py                    Saved subjects and guides
  chat.py                     Chat assistant (Claude on Bedrock + guardrail)
  chatbot/                    Assistant instructions and knowledge files
  aws.py                      AWS/DynamoDB client construction
  config.py                   Environment-based configuration
  repositories.py             DynamoDB persistence layer
  routes.py                   Health and expression-of-interest endpoints
  requirements.txt            Runtime dependencies
  requirements-dev.txt        Runtime plus test dependencies
tests/
  conftest.py                 Test fixtures and in-memory repository
  test_api.py                 Expression-of-interest API tests
  test_users.py               Signup API tests
  test_accounts.py            Sign-in, session, and my-account tests
  test_content.py             Downloads and catalogue tests
  test_repositories.py        DynamoDB request tests
  test_saved.py               Saved items and subjects tests
  test_chat.py                Chat assistant tests (fake Claude and guardrail)
  test_lambda.py              Lambda event (function URL / API Gateway v2) tests
content/                      Downloadable files (uploaded by deploy.sh)
frontend/
  index.html                  Placeholder home page (frontend team replaces)
  debug/index.html            Debug panel at /debug: try every endpoint
  debug/signin-tests.js       "Run sign-in tests": end-to-end sign-in checks
  chat/chat-widget.js         "Ask about T Levels" chat panel for every page
  accessibility.html          Text size and colour contrast settings
  scripts/display-settings.js Applies the saved settings (in <head> on every page)
  styles/display-settings.css Text sizes and the high contrast / dark themes
infra/
  dynamodb-table.yaml         Development table definitions
deploy/
  template.yaml               CloudFront, S3, Lambda function URL (AWS SAM)
  deploy.sh                   Build and deploy to AWS
  teardown.sh                 Delete the AWS deployment
  midway.sh                   Midway (CloudFrontSigner) signing key setup
  cfs/                        CloudFrontSigner 403 page and redirect script
docs/
  api.md                      API reference for the frontend
  dynamodb-design.md          Table and data design
  deployment.md               AWS hosting design and security decisions
  development-log.md          Iterative development record
  test-log.md                 Iterative test record
```

## Local setup

Python 3.12 is required (the version AWS Lambda runs; the Anthropic SDK needs
3.10 or later). Create a virtual environment and install the dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-dev.txt
```

Copy the local configuration template:

```bash
cp .env.example .env
```

Authenticate to AWS using the approved profile or role for the project.
Do not put access keys or secret keys in `.env`.

## Run tests

```bash
source .venv/bin/activate
python -m pytest
```

The tests use in-memory repositories and do not contact AWS.

## Run the backend locally

```bash
source .venv/bin/activate
python -m backend
```

The server listens on `127.0.0.1:5000` by default. It intentionally does not
bind to all network interfaces.

Health check:

```bash
curl http://127.0.0.1:5000/health
```

## API

The full request and response contract for the frontend team is in
[`docs/api.md`](docs/api.md).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/api/expressions-of-interest` | Register interest in placements |
| `POST` | `/api/users` | Create an account |
| `POST` | `/api/login` / `/api/logout` | Sign in / sign out |
| `GET` | `/api/users/me` | View my account |
| `POST` | `/api/users/me/update` | Change my name and email (password required) |
| `POST` | `/api/users/me/password` | Change my password |
| `POST` | `/api/users/me/delete` | Delete my account (password required) |
| `GET` / `POST` | `/api/users/me/saved` | List / add saved subjects and guides |
| `POST` | `/api/users/me/saved/remove` | Remove a saved item |
| `GET` | `/api/subjects` | Placement subject areas |
| `POST` | `/api/chat` | Ask the chat assistant (see `docs/chatbot/`) |
| `GET` | `/api/content` | List downloads |
| `GET` | `/api/content/<id>/download` | Download a file (some need sign-in) |

Passwords are hashed before storage and never returned. There is no endpoint
for reading other people's data.

## DynamoDB tables

The application expects three tables by default, all defined in
`infra/dynamodb-table.yaml`. See `docs/dynamodb-design.md` for the item shapes.

| Table | Setting | Partition key |
|---|---|---|
| `t-level-expressions-of-interest-dev` | `DYNAMODB_TABLE_NAME` | `id` |
| `t-level-users-dev` | `USERS_TABLE_NAME` | `email` |
| `t-level-sessions-dev` | `SESSIONS_TABLE_NAME` | `token_hash` |

All tables use:

- On-demand billing for the prototype.
- Server-side encryption.
- Point-in-time recovery.

No AWS resource is created by this local scaffold. Deploy the tables only after
the team has confirmed the AWS account, region, permissions, and data-handling
approval.

Use synthetic data while developing and demonstrating the prototype. Do not
store real student or customer information until the team has agreed the
retention, access-control, and privacy requirements.

## Chat assistant

The Task 4 AI feature is a chat panel on every page (**Ask about T Levels**).
`POST /api/chat` answers with Claude Opus 5.5 on Amazon Bedrock, behind a
Bedrock Guardrail. Design, safety rules and test prompts are in
[`docs/chatbot/`](docs/chatbot/README.md).

## Debug panel

`/debug` on the deployed site is an unstyled page for trying every backend
endpoint by hand. Its **Run sign-in tests** button signs up a new made-up
account and checks 58 steps of the sign-in journey against the live backend
(password rules, terms, sign-in, Remember me, saved items, editing details,
changing the password, wrong passwords,
lockout, sign-out, members-only download, account deletion), printing PASS or FAIL for each. The test account is deleted at the
end.

## Deploy to AWS

The prototype is hosted on CloudFront behind Midway sign-in, so Amazon staff
(the team and assessors) can open it in a browser. See `docs/deployment.md`
for the architecture, security decisions, and one-time Midway onboarding.

```bash
deploy/deploy.sh      # deploy or update; prints the site URL
deploy/teardown.sh    # delete everything, including all stored data
```

Only deploy to the agreed project AWS account, and use synthetic data only.

## Team workflow

- Keep `main` or `mainline` stable.
- Create a short-lived branch for each change.
- Open a pull request for review before merging.
- Keep commits small and describe the behaviour changed.
- Update `docs/development-log.md` and `docs/test-log.md` as the prototype
  evolves.
- Never commit `.env`, credentials, real personal data, build output, or
  generated files.

