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

### Deployed site: two rules for `fetch`

1. **Midway first.** The whole site sits behind Midway. A visitor signs in to
   Midway when they open any page; after that, `fetch` calls to `/api/...`
   from the same site work normally. If the Midway cookies expire, API calls
   get an HTML `403` page instead of JSON, and reloading the page signs the
   visitor in again.
2. **Hash request bodies.** Requests with a body (`POST` with JSON)
   must send the body's SHA-256 hash in an `x-amz-content-sha256` header,
   because CloudFront signs requests to the Lambda backend. Use this helper:

   ```js
   async function apiFetch(method, path, body) {
     const options = { method, headers: {} };
     if (body !== undefined) {
       const text = JSON.stringify(body);
       const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
       options.headers["Content-Type"] = "application/json";
       options.headers["x-amz-content-sha256"] = [...new Uint8Array(digest)]
         .map((b) => b.toString(16).padStart(2, "0")).join("");
       options.body = text;
     }
     return fetch(path, options);
   }
   ```

The API never returns `403` itself; CloudFront reserves that code for the
Midway sign-in page. The API also has no `DELETE` endpoints: CloudFront's
signed requests to the Lambda backend reject `DELETE` requests with a body, so
deleting an account is a `POST`.

| Method | Path | Sign-in | Purpose |
|---|---|---|---|
| `GET` | `/health` | No | Liveness check |
| `POST` | `/api/expressions-of-interest` | No | Register interest in T Level placements |
| `POST` | `/api/users` | No | Create an account (also signs in) |
| `POST` | `/api/login` | No | Sign in |
| `POST` | `/api/logout` | No | Sign out |
| `GET` | `/api/users/me` | Yes | View my account |
| `GET` | `/api/users/me/saved` | Yes | List my saved subjects and guides |
| `POST` | `/api/users/me/saved` | Yes | Save a subject or guide |
| `POST` | `/api/users/me/saved/remove` | Yes | Remove a saved item |
| `GET` | `/api/subjects` | No | List the placement subject areas |
| `POST` | `/api/users/me/delete` | Yes | Delete my account |
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
{"full_name": "Example Student", "email": "example.student@example.com", "password": "correct horse battery 9!", "accept_terms": true}
```

| Field | Rules |
|---|---|
| `full_name` | Required, 1–100 characters |
| `email` | Required, valid email; stored lower-case |
| `password` | Required, 12–128 characters, with at least one number and one symbol (spaces don't count as symbols) |
| `accept_terms` | Required, must be `true` (the Terms of use / Privacy notice checkbox). The time is stored as evidence. |

The new session is not remembered: it ends when the browser closes.

| Status | Meaning |
|---|---|
| `201` | Account created and signed in; returns `id`, `email`, `full_name`, `created_at`, `status` |
| `400` | Validation failed |
| `409` | An account with this email already exists |
| `503` | The account could not be saved |

## `POST /api/login`

```json
{"email": "example.student@example.com", "password": "correct horse battery 9!", "remember_me": false}
```

`remember_me` is optional (default `false`). Unticked, the cookie ends when the browser closes and the session expires after 12 hours. Ticked, the session lasts 30 days.

| Status | Meaning |
|---|---|
| `200` | Signed in; returns the profile and sets the session cookie |
| `400` | Missing email or password, or `remember_me` not true/false |
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

## `POST /api/users/me/delete`

Confirms the password before deleting.

```json
{"password": "correct horse battery"}
```

| Status | Meaning |
|---|---|
| `200` | `{"status": "deleted"}`; account deleted and signed out |
| `400` | Password missing |
| `401` | Not signed in |
| `400` | `Password is incorrect.` |

## `GET /api/subjects`

The single list of placement subject areas. Use its `id` values for
`interests` (expression of interest, any letter case) and for saved subjects.

```json
{"subjects": [{"id": "digital", "name": "Digital"}, {"id": "business", "name": "Business"},
              {"id": "media", "name": "Media"}, {"id": "finance", "name": "Finance"},
              {"id": "engineering", "name": "Engineering"}]}
```

## Saved subjects and guides

All three need sign-in (`401` otherwise) and return the full list, newest first:

```json
{"items": [{"type": "guide", "id": "parents-guide", "saved_at": "2026-10-20T09:00:00Z"}], "status": "saved"}
```

| Request | Body | Result |
|---|---|---|
| `GET /api/users/me/saved` | none | `200` with `items` |
| `POST /api/users/me/saved` | `{"type": "subject", "id": "digital"}` | `201` `saved`, or `200` `already_saved` |
| `POST /api/users/me/saved/remove` | `{"type": "guide", "id": "parents-guide"}` | `200` `removed`, or `200` `not_saved` |

- `type` is `subject` or `guide`.
- Subject IDs must come from `GET /api/subjects`.
- Guide IDs are the frontend's page slugs: 1 to 64 lowercase letters, numbers or dashes.
- Up to 50 saved items per account (`400` beyond that).

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
