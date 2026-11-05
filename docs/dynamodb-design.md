# DynamoDB design

| Table | Partition key | Holds |
|---|---|---|
| `t-level-expressions-of-interest-dev` | `id` | Expressions of interest |
| `t-level-users-dev` | `email` | User accounts |
| `t-level-sessions-dev` | `token_hash` | Sign-in sessions |
| `t-level-forum-dev` | `pk` + sort key `sk` | Forum posts, comments, votes, reports, rate limits |

The first three tables are read and written by partition key only. The forum
table also uses `Query` on one partition (posts, or one post's comments), so
no secondary indexes or scans are needed. Multi-item writes are changing an
email address and the forum transactions (see below).

## Expressions of interest table

Development table name:

```text
t-level-expressions-of-interest-dev
```

The name is configurable through `DYNAMODB_TABLE_NAME`.

## Key design

| Attribute | Type | Purpose |
|---|---|---|
| `id` | String | UUID partition key |

Submissions can only be written through the API. Reading them back would need
an authenticated staff role, which is out of scope for the prototype.

## Item shape

| Attribute | Type | Purpose |
|---|---|---|
| `id` | String | Unique record identifier |
| `full_name` | String | User-provided name |
| `email` | String | Normalised email address |
| `customer_type` | String | `student`, `school`, `parent_carer`, or `other` |
| `school` | String | Optional school or organisation |
| `interests` | List[String] | Placement areas: `Digital`, `Business`, `Media`, `Finance`, `Engineering` |
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
| `terms_accepted_at` | String | UTC time the user accepted the Terms of use and Privacy notice |
| `saved` | Map | Saved items: `"subject:digital"` → UTC time saved (max 50) |
| `failed_login_count` | Number | Wrong passwords in a row (absent until the first failure) |
| `locked_until` | Number | Epoch seconds; sign-in refused until then (absent when not locked) |
| `session_version` | Number | Increased on every password change; ends older sessions (absent until the first change) |
| `created_at` | String | UTC creation timestamp |
| `updated_at` | String | UTC update timestamp |

The plain-text password is never stored, logged, or returned by the API.
`failed_login_count` is increased with an atomic `ADD` update, so two wrong
passwords submitted at the same moment are both counted.

### Changing the email address

Because the email is the partition key, `UsersRepository.change_email` moves
the account with one `TransactWriteItems` call: a `Put` of the whole item under
the new email (condition `attribute_not_exists(email)`) and a `Delete` of the
old one. Either both happen or neither does, and DynamoDB still guarantees the
new email is not already registered (HTTP 409 if it is). The `id`,
`created_at`, saved items and password hash move with it. Transactions need no
extra IAM permission; they use the Lambda's existing `PutItem` and `DeleteItem`.

## Sessions table

Development table name:

```text
t-level-sessions-dev
```

The name is configurable through `SESSIONS_TABLE_NAME`.

### Key design

| Attribute | Type | Purpose |
|---|---|---|
| `token_hash` | String | SHA-256 hash of the session token (partition key) |

The browser keeps a random 256-bit token in the `rufus_session` cookie. Only
its hash is stored, so someone who could read the table still could not sign
in as anyone. Sessions are stored on the server rather than in a signed cookie
so that signing out and deleting an account take effect immediately.

### Item shape

| Attribute | Type | Purpose |
|---|---|---|
| `token_hash` | String | Partition key |
| `email` | String | Which user the session belongs to |
| `user_id` | String | The user's `id`; the session is refused if it does not match |
| `session_version` | Number | The user's `session_version` when the session started; refused if it no longer matches |
| `created_at` | String | UTC creation timestamp |
| `expires_at` | Number | Epoch seconds; DynamoDB time-to-live deletes the item after this (12 hours, or 30 days with Remember me) |

TTL deletion can take up to a few days, so the application also rejects any
session whose `expires_at` has passed.

Sessions cannot be listed per user without a scan or an index, so instead of
deleting a user's other sessions the application makes them stop matching:

- **Password change:** the user's `session_version` goes up by one and the
  current session is updated to match, so only that browser stays signed in.
- **Email change, account deletion:** other sessions still point at the old
  email. If someone later registers that email, the `user_id` check stops the
  old sessions opening the new account.

Sessions created before `user_id` was added are refused, which signs everyone
out once when this change is deployed.

## Forum table

Development table name `t-level-forum-dev`, configurable through
`FORUM_TABLE_NAME`. One table holds every forum item; the partition key `pk`
and sort key `sk` say what each item is:

| Item | `pk` | `sk` | Other attributes |
|---|---|---|---|
| Post | `POSTS` | `POST#<post_id>` | `id`, `title`, `body`, `author_id`, `author_name`, `created_at`, `likes`, `dislikes`, `comment_count` |
| Comment | `POST#<post_id>` | `COMMENT#<comment_id>` | `id`, `post_id`, `body`, `author_id`, `author_name`, `created_at`, `likes`, `dislikes` |
| Vote | `VOTES#<user_id>` | `post#<id>` or `comment#<id>` | `value`: `1` like, `-1` dislike |
| Report | `REPORTS` | `<type>#<id>#<reporter_id>` | `type`, `target_id`, `reason`, `reporter_id`, `created_at` |
| Rate limit | `RATE#<user_id>` | `post`, `comment`, `vote` or `report` | `count`, `window_start`, `expires_at` (TTL) |
| Example marker | `META` | `EXAMPLE_POST` | `post_id` |

IDs start with the creation time in microseconds, so sort-key order is time
order: newest posts are a `Query` on `POSTS` read backwards, a post's comments
a `Query` on `POST#<id>` read forwards.

- **Counts stay right.** Adding or deleting a comment changes the post's
  `comment_count`, and every like or dislike changes the target's counts, in
  the same `TransactWriteItems` call as the comment or vote. The vote write is
  conditional on the vote the API last read, so two requests at the same
  moment can't count twice (the API retries once).
- **One vote and one report per person per item**: the key includes the user.
- **Reading likes**: one `BatchGetItem` (with `ConsistentRead`) for the
  viewer's votes on the posts or comments on screen.
- **Rate limits** are counted with conditional updates per user and action;
  finished windows expire with TTL on `expires_at`.
- **Example post**: added the first time the forum is listed, with a marker
  item written first, so it isn't added again after someone deletes it.
- **Deleting a post** deletes its comments too (`BatchWriteItem`). Votes on it
  stay in voters' partitions; nothing reads them once the post is gone.
- **Deleting an account** doesn't delete forum posts (they show the first
  name only). Removing them on account deletion is future work.

Prototype limits: all posts share the `POSTS` partition (fine for thousands
of posts), and "Most liked" sorts up to 500 posts in the API. A larger forum
would add a secondary index on score.

## Security decisions

- The Flask service defaults to `127.0.0.1`.
- The only read endpoint for personal data is `GET /api/users/me`, which
  returns the signed-in user's own profile and nothing else.
- Sign-in uses the same error message for an unknown email and a wrong
  password, and checks a dummy hash for unknown emails so response times do
  not reveal which emails are registered.
- After 5 wrong passwords in a row, the account is locked for 15 minutes.
  This slows down password guessing. Someone could deliberately lock another
  user out for 15 minutes; this is accepted for the prototype.
- The session cookie is `HttpOnly` (JavaScript cannot read it), `Secure`
  (HTTPS only), and `SameSite=Strict` (not sent with requests started by other
  websites, which prevents cross-site request forgery).
- Deleting an account, changing the name or email, and changing the password
  all require the current password again, so a session left open on a shared
  computer cannot be used to take the account over.
- Deleting an account removes the user item and the current session. Any
  other sessions stop working at once because their user no longer exists.
  Expressions of interest are separate submissions and are not deleted.
- Forum posts show only the author's first name; the user ID is stored but
  never returned. Authors can delete their own posts and comments; others get
  `404`. Posting, commenting, voting and reporting are rate limited per account.
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

