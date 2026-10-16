# T Level Team Project — Backend

This repository contains the Flask backend for the Amazon T Level project.
The current backend scope is the expression-of-interest feature backed by
Amazon DynamoDB.

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
  aws.py                      AWS/DynamoDB client construction
  config.py                   Environment-based configuration
  repositories.py             DynamoDB persistence layer
  routes.py                   HTTP endpoints and request validation
  requirements.txt            Runtime dependencies
  requirements-dev.txt        Runtime plus test dependencies
tests/
  conftest.py                 Test fixtures and in-memory repository
  test_api.py                 API tests
infra/
  dynamodb-table.yaml         Development table definition
docs/
  dynamodb-design.md          Table and data design
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

## DynamoDB table

The application expects a table named
`t-level-expressions-of-interest-dev` by default. The table definition is in
`infra/dynamodb-table.yaml`.

The table uses:

- `id` as a string partition key.
- On-demand billing for the prototype.
- Server-side encryption.
- Point-in-time recovery.

No AWS resource is created by this local scaffold. Deploy the table only after
the team has confirmed the AWS account, region, permissions, and data-handling
approval.

Use synthetic data while developing and demonstrating the prototype. Do not
store real student or customer information until the team has agreed the
retention, access-control, and privacy requirements.

## Team workflow

- Keep `main` or `mainline` stable.
- Create a short-lived branch for each change.
- Open a pull request for review before merging.
- Keep commits small and describe the behaviour changed.
- Update `docs/development-log.md` and `docs/test-log.md` as the prototype
  evolves.
- Never commit `.env`, credentials, real personal data, build output, or
  generated files.

