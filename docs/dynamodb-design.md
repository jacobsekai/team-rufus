# DynamoDB design

## Table

Development table name:

```text
t-level-expressions-of-interest-dev
```

The name is configurable through `DYNAMODB_TABLE_NAME`.

## Key design

| Attribute | Type | Purpose |
|---|---|---|
| `id` | String | UUID partition key |

There is currently no secondary index because the first prototype operation is
submission. An authenticated administrative read model should be designed before
adding queries for personal data.

## Item shape

| Attribute | Type | Purpose |
|---|---|---|
| `id` | String | Unique record identifier |
| `full_name` | String | User-provided name |
| `email` | String | Normalised email address |
| `school` | String | Optional school or organisation |
| `interests` | List[String] | Selected programme interests |
| `consent` | Boolean | Confirmation that the user agreed to submit |
| `created_at` | String | UTC creation timestamp |
| `updated_at` | String | UTC update timestamp |

## Users table

Development table name:

```text
t-level-users-dev
```

The name is configurable through `USERS_TABLE_NAME`.

### Key design

| Attribute | Type | Purpose |
|---|---|---|
| `email` | String | Normalised (trimmed, lower-case) email partition key |

The email address is the partition key so that DynamoDB enforces one account
per email. `UsersRepository.create_user` writes with
`ConditionExpression="attribute_not_exists(email)"`; if the email is already
registered the write is rejected and the API returns HTTP 409. A random-`id`
key could not enforce this without a second lookup, which would also be open to
a race between two simultaneous signups.

A separate UUID `id` is still stored so other tables can reference a user
without copying their email address.

### Item shape

| Attribute | Type | Purpose |
|---|---|---|
| `email` | String | Normalised email address (partition key) |
| `id` | String | UUID for referencing the user elsewhere |
| `full_name` | String | User-provided name |
| `password_hash` | String | Salted PBKDF2-SHA256 hash, 600,000 iterations |
| `created_at` | String | UTC creation timestamp |
| `updated_at` | String | UTC update timestamp |

The plain-text password is never stored, logged, or returned by the API.

## Security decisions

- The Flask service defaults to `127.0.0.1`.
- No DynamoDB read endpoint is exposed without an authentication and
  authorisation design.
- AWS credentials are obtained through the standard AWS credential chain.
- No credentials are stored in source code or `.env.example`.
- The development table template enables server-side encryption and
  point-in-time recovery.
- Passwords are hashed with Werkzeug's `generate_password_hash` using
  `pbkdf2:sha256:600000` (the OWASP-recommended iteration count). PBKDF2 is
  used instead of scrypt because scrypt is missing from some Python builds,
  including the macOS system Python.
- Passwords must be 12 to 128 characters. The upper limit stops very long
  inputs being used to slow the server down with expensive hashing.
- Signup reveals whether an email is already registered (HTTP 409). This is
  accepted for the prototype; a production service would usually send a
  verification email instead.
- Use synthetic data during development and demonstrations.
- Retention, access roles, and any additional encryption requirements must be
  agreed before storing real personal data.

