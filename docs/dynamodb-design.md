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

## Security decisions

- The Flask service defaults to `127.0.0.1`.
- No DynamoDB read endpoint is exposed without an authentication and
  authorisation design.
- AWS credentials are obtained through the standard AWS credential chain.
- No credentials are stored in source code or `.env.example`.
- The development table template enables server-side encryption and
  point-in-time recovery.
- Use synthetic data during development and demonstrations.
- Retention, access roles, and any additional encryption requirements must be
  agreed before storing real personal data.

