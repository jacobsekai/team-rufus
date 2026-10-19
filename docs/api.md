# API reference

All endpoints accept and return JSON. Request bodies must be sent with
`Content-Type: application/json`, otherwise the API returns `415`.

Errors always look like this; `details` is only present for validation errors:

```json
{"error": "Validation failed.", "details": ["email must be a valid email address."]}
```

On the deployed site the frontend and API share one address, so call the API
with relative paths, for example `fetch("/api/login", ...)`. The browser sends
the session cookie automatically; no token handling is needed in JavaScript.

| Method | Path | Sign-in | Purpose |
|---|---|---|---|
| `GET` | `/health` | No | Liveness check |
| `POST` | `/api/expressions-of-interest` | No | Register interest in T Level placements |
| `POST` | `/api/users` | No | Create an account (also signs in) |
| `POST` | `/api/login` | No | Sign in |
| `POST` | `/api/logout` | No | Sign out |
| `GET` | `/api/users/me` | Yes | View my account |
| `DELETE` | `/api/users/me` | Yes | Delete my account |
| `GET` | `/api/content` | No | List downloadable content |
| `GET` | `/api/content/<id>/download` | Depends on item | Download a file |

## `GET /health`

`200` `{"status": "ok"}`

## `POST /api/expressions-of-interest`

```json
{
  "full_name": "Example Student",
  "email": "example.student@example.com",
  "customer_type": "student",
  "school": "Example School",
  "interests": ["Digital", "Engineering"],
  "consent": true
}
```

| Field | Rules |
|---|---|
| `full_name` | Required, 1–100 characters |
| `email` | Required, valid email; stored lower-case |
| `customer_type` | Required: `student`, `school`, `parent_carer`, or `other` |
| `school` | Optional, up to 200 characters |
| `interests` | Optional list of `Digital`, `Business`, `Media`, `Finance`, `Engineering` (any letter case; duplicates removed) |
| `consent` | Required, must be `true` |

| Status | Meaning |
|---|---|
| `201` | `{"id": "...", "status": "received"}` |
| `400` | Validation failed |
| `503` | Could not be saved |

There is deliberately no endpoint for reading submissions back.

## `POST /api/users`

```json
{"full_name": "Example Student", "email": "example.student@example.com", "password": "correct horse battery"}
```

| Field | Rules |
|---|---|
| `full_name` | Required, 1–100 characters |
| `email` | Required, valid email; stored lower-case |
| `password` | Required, 12–128 characters |

| Status | Meaning |
|---|---|
| `201` | Account created and signed in; returns `id`, `email`, `full_name`, `created_at`, `status` |
| `400` | Validation failed |
| `409` | An account with this email already exists |
| `503` | The account could not be saved |

## `POST /api/login`

```json
{"email": "example.student@example.com", "password": "correct horse battery"}
```

| Status | Meaning |
|---|---|
| `200` | Signed in; returns the profile and sets the session cookie |
| `400` | Missing email or password |
| `401` | `Email or password is incorrect.` (same message whether or not the email exists) |
| `429` | Locked after 5 wrong passwords in a row; `Retry-After` header gives seconds to wait (up to 15 minutes) |
| `503` | Temporary problem |

## `POST /api/logout`

No body needed. Always `200` `{"status": "signed_out"}` and clears the cookie.

## `GET /api/users/me`

| Status | Meaning |
|---|---|
| `200` | `{"id", "email", "full_name", "created_at"}` |
| `401` | `You need to sign in.` |

## `DELETE /api/users/me`

Confirms the password before deleting.

```json
{"password": "correct horse battery"}
```

| Status | Meaning |
|---|---|
| `200` | `{"status": "deleted"}`; account deleted and signed out |
| `400` | Password missing |
| `401` | Not signed in |
| `403` | Password is incorrect |

## `GET /api/content`

```json
{
  "signed_in": false,
  "items": [
    {
      "id": "placement-preparation-checklist",
      "title": "Placement preparation checklist (placeholder)",
      "description": "...",
      "requires_login": true,
      "download_url": "/api/content/placement-preparation-checklist/download"
    }
  ]
}
```

Use `signed_in` and `requires_login` to decide whether to show a download link
or a "sign in to download" prompt.

## `GET /api/content/<id>/download`

Use as a normal link (`<a href="...">`). The browser follows the redirect and
downloads the file.

| Status | Meaning |
|---|---|
| `302` | Redirect to a download link that expires after 5 minutes |
| `401` | This item needs sign-in |
| `404` | No item with that ID |
| `503` | Downloads unavailable |
