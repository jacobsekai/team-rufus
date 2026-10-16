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
  aws.py                      AWS/DynamoDB client construction
  config.py                   Environment-based configuration
  repositories.py             DynamoDB persistence layer
  routes.py                   HTTP endpoints and request validation
  requirements.txt            Runtime dependencies
  requirements-dev.txt        Runtime plus test dependencies
tests/
  conftest.py                 Test fixtures and in-memory repository
  test_api.py                 Expression-of-interest API tests
  test_users.py               User signup API and repository tests
  test_lambda.py              API Gateway/Lambda event tests
infra/
  dynamodb-table.yaml         Development table definitions
deploy/
  template.yaml               CloudFront, S3, API Gateway, Lambda (AWS SAM)
  deploy.sh                   Build and deploy to AWS
  teardown.sh                 Delete the AWS deployment
docs/
  dynamodb-design.md          Table and data design
  deployment.md               AWS hosting design and security decisions
  development-log.md          Iterative development record
  test-log.md                 Iterative test record
```

## Local setup

Create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
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

The tests use an in-memory repository and do not contact AWS.

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

Submit an expression of interest:

```bash
curl -X POST http://127.0.0.1:5000/api/expressions-of-interest \
  -H 'Content-Type: application/json' \
  -d '{
    "full_name": "Example Student",
    "email": "example.student@example.com",
    "school": "Example School",
    "interests": ["Digital", "Engineering"],
    "consent": true
  }'
```

The API returns only the generated record ID and status after a successful
submission. It does not provide an unauthenticated read endpoint for
expression-of-interest records.

Create a user account:

```bash
curl -X POST http://127.0.0.1:5000/api/users \
  -H 'Content-Type: application/json' \
  -d '{
    "full_name": "Example Student",
    "email": "example.student@example.com",
    "password": "correct horse battery"
  }'
```

| Field | Rules |
|---|---|
| `full_name` | Required, 1–100 characters |
| `email` | Required, valid email; stored lower-case |
| `password` | Required, 12–128 characters |

| Status | Meaning |
|---|---|
| `201` | Account created; returns `id`, `email`, `full_name`, `status` |
| `400` | Validation failed; `details` lists each problem |
| `409` | An account with this email already exists |
| `415` | Request was not JSON |
| `503` | The account could not be saved |

The password is hashed before storage and is never returned.

## DynamoDB tables

The application expects two tables by default. Both are defined in
`infra/dynamodb-table.yaml`.

| Table | Setting | Partition key |
|---|---|---|
| `t-level-expressions-of-interest-dev` | `DYNAMODB_TABLE_NAME` | `id` |
| `t-level-users-dev` | `USERS_TABLE_NAME` | `email` |

Both tables use:

- On-demand billing for the prototype.
- Server-side encryption.
- Point-in-time recovery.

No AWS resource is created by this local scaffold. Deploy the tables only after
the team has confirmed the AWS account, region, permissions, and data-handling
approval.

Use synthetic data while developing and demonstrating the prototype. Do not
store real student or customer information until the team has agreed the
retention, access-control, and privacy requirements.

## Deploy to AWS

The prototype can be hosted on CloudFront so others can open it in a browser.
See `docs/deployment.md` for the architecture and security decisions.

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

