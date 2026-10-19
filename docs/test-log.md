# Iterative test log

Record representative tests rather than every individual test execution.

| Date | Component | Test type | Test data/condition | Expected result | Actual result | Status |
|---|---|---|---|---|---|---|
| 2026-10-16 | Health endpoint | Functional | `GET /health` | HTTP 200 and non-sensitive status | HTTP 200 and `{"status":"ok"}` | Pass |
| 2026-10-16 | Expression-of-interest API | Validation | Unknown JSON field | HTTP 400; record is not stored | Covered by automated test | Pass |
| 2026-10-16 | Expression-of-interest API | Validation | `consent: false` | HTTP 400; record is not stored | Covered by automated test | Pass |
| 2026-10-16 | Expression-of-interest API | Functional | Valid JSON submission | HTTP 201 and generated ID | Covered by automated test | Pass |
| 2026-10-16 | User signup API | Functional | Valid signup | HTTP 201; ID returned; no password in response | Covered by automated test | Pass |
| 2026-10-16 | User signup API | Security | Inspect stored record | Password stored only as a PBKDF2 hash that verifies against the original | Covered by automated test | Pass |
| 2026-10-16 | User signup API | Validation | Same email twice, different letter case | Second request HTTP 409; one record stored | Covered by automated test | Pass |
| 2026-10-16 | User signup API | Validation | Password under 12, over 128, or not a string | HTTP 400; nothing stored | Covered by automated test | Pass |
| 2026-10-16 | User signup API | Security | Invalid request containing a password | Password not echoed in the error response | Covered by automated test | Pass |
| 2026-10-16 | User signup API | Validation | Bad email, blank name, unknown field (`is_admin`) | HTTP 400 with specific error; nothing stored | Covered by automated test | Pass |
| 2026-10-16 | User signup API | Error handling | Storage failure | HTTP 503 with generic message | Covered by automated test | Pass |
| 2026-10-16 | Users repository | Unit | Stubbed DynamoDB table | Writes with `attribute_not_exists(email)`; maps conditional failure to duplicate error | Covered by automated test | Pass |
| 2026-10-16 | Lambda integration | Integration | API Gateway HTTP API v2 event for `POST /api/users` | HTTP 201; user stored | Covered by automated test | Pass |
| 2026-10-16 | Lambda integration | Integration | API Gateway HTTP API v2 event for `GET /health` | HTTP 200 and `{"status":"ok"}` | Covered by automated test | Pass |
| 2026-10-16 | Deployment template | Static analysis | `sam validate --lint` on `deploy/template.yaml` and `infra/dynamodb-table.yaml` | Valid template, no lint errors | Valid SAM Template | Pass |
| 2026-10-16 | Lambda package | Build | Build with Python 3.12 for `manylinux2014_aarch64`; import `backend.lambda_handler` | Python 3.12 wheels selected; handler imports | boto3 1.43, ARM `.so` files; handler imported | Pass |
| 2026-10-16 | Deploy sign-in | Manual (stubbed `aws`/`ada`) | No credentials; enter account and role; answer `yes` | Ada called with Conduit provider, account, role, profile; account shown; deploy continues | As expected | Pass |
| 2026-10-16 | Deploy sign-in | Manual (stubbed `aws`/`ada`) | Already signed in; answer `no` | Account shown; script exits without changes | Cancelled, exit code 1 | Pass |
| 2026-10-16 | Live deployment (CloudFront) | Smoke | `GET /` and `GET /health` | Test panel served; HTTP 200 `{"status":"ok"}` | As expected | Pass |
| 2026-10-16 | Live deployment (CloudFront) | Functional | Synthetic signup, then same email again | HTTP 201, then HTTP 409 | As expected | Pass |
| 2026-10-16 | Live deployment (CloudFront) | Validation | Password `short` | HTTP 400 with password error | As expected | Pass |
| 2026-10-16 | Live deployment (CloudFront) | Functional | Synthetic expression of interest | HTTP 201 with ID | As expected | Pass |
| 2026-10-16 | Live deployment (DynamoDB) | Security | Read stored synthetic user item | Only `pbkdf2:sha256:600000` hash stored, no plain password | As expected | Pass |
| 2026-10-16 | Live deployment (security) | Security | HTTP request; direct S3 object URL; response headers | 301 to HTTPS; S3 returns 403; HSTS, nosniff, X-Frame-Options present | As expected | Pass |
| 2026-10-19 | Sign-in | Functional | Correct email (any letter case) and password | HTTP 200; cookie set with HttpOnly, Secure, SameSite=Strict | Covered by automated test | Pass |
| 2026-10-19 | Sign-in | Security | Wrong password vs unknown email | Identical HTTP 401 message; no cookie | Covered by automated test | Pass |
| 2026-10-19 | Sign-in | Security | 5 wrong passwords then the correct one | HTTP 429 with Retry-After ≤ 900 s | Covered by automated test | Pass |
| 2026-10-19 | Sign-in | Boundary | Lock time in the past; success after one failure | Sign-in allowed; failure count reset to 0 | Covered by automated test | Pass |
| 2026-10-19 | Sign-in | Validation | Missing email/password, empty password, unknown field, non-object, non-JSON | HTTP 400 / 415 | Covered by automated test | Pass |
| 2026-10-19 | Sessions | Security | Inspect sessions table after sign-in | Only SHA-256 of token stored, never the token | Covered by automated test | Pass |
| 2026-10-19 | Sessions | Security | Made-up token; expired session; session of deleted user | HTTP 401; bad cookie cleared; expired session deleted | Covered by automated test | Pass |
| 2026-10-19 | Sign-out | Functional | Sign out, then GET /api/users/me | Session deleted; HTTP 401 | Covered by automated test | Pass |
| 2026-10-19 | My account | Security | GET /api/users/me signed in / signed out | Only id, email, full_name, created_at / HTTP 401 | Covered by automated test | Pass |
| 2026-10-19 | Delete account | Security | Wrong password; not signed in; correct password | HTTP 403 / 401 / 200 then user and session removed and sign-in fails | Covered by automated test | Pass |
| 2026-10-19 | Downloads | Functional | List content signed out and signed in | All items listed; `signed_in` flag correct | Covered by automated test | Pass |
| 2026-10-19 | Downloads | Security | Members-only item signed out, signed in, after sign-out | HTTP 401 / 302 to signed link / 401 | Covered by automated test | Pass |
| 2026-10-19 | Downloads | Validation | Unknown ID; no bucket configured | HTTP 404 / 503 | Covered by automated test | Pass |
| 2026-10-19 | Content catalogue | Validation | Duplicate ID, bad ID, `../` path, non-boolean flag, extra field, blank title | Start-up refused with a clear error | Covered by automated test | Pass |
| 2026-10-19 | Expression of interest | Validation | Each customer type; missing/unknown/wrong-case type | HTTP 201 / HTTP 400 | Covered by automated test | Pass |
| 2026-10-19 | Expression of interest | Validation | Interests ` digital `, `FINANCE`, `Digital`; `Cooking`; non-list | Stored as `Digital`, `Finance` / HTTP 400 | Covered by automated test | Pass |
| 2026-10-19 | Repositories | Unit | Stubbed DynamoDB table | Consistent reads, atomic `ADD` for failures, AWS errors mapped to RepositoryError | Covered by automated test | Pass |
| 2026-10-19 | Lambda integration | Integration | Sign up via API Gateway v2 event, reuse returned cookie on GET /api/users/me | HTTP 200 with the user's email | Covered by automated test | Pass |
| 2026-10-19 | Test quality | Mutation | Temporarily removed members-only check, weakened SameSite, disabled lockout | Each change made at least one test fail | Covered by automated test | Pass |
| 2026-10-19 | CloudFrontSigner files | Static check | Compare templates with CloudFrontSignerConstructs 6.x | Byte-identical: 403 page 375 chars, handler 11,867 chars | Match | Pass |
| 2026-10-19 | CloudFrontSigner files | Unit | Render with dummy Bindle and secret ARN | No placeholders left; v2 authorize endpoint; handler parses | As expected | Pass |
| 2026-10-19 | Signing key | Unit | Generate key pair locally | PKCS#8 private key, SPKI public key, file mode 600 | As expected | Pass |
| 2026-10-19 | Deployment template | Static analysis | `sam validate --lint` | Valid; every behavior except `/js/cfs-handler.js` has the trusted key group | Valid SAM Template | Pass |
| 2026-10-19 | Delete account | Regression | Wrong password; API status codes | HTTP 400 (not 403, which CloudFront reserves for Midway) | Covered by automated test | Pass |
| 2026-10-19 | Live deployment (Midway) | Security | Distribution config after deploy | Default, `/api/*`, `/health` restricted to the CloudFrontSigner key group; only `/js/cfs-handler.js` open; 403 → `/error/403.html` | As expected | Pass |
| 2026-10-19 | Live deployment (Midway) | Security | Unauthenticated GET `/`, `/index.html`, `/health`, `/api/users/me`, `/api/content`, a download, a missing path, `/error/403.html`; POST `/api/users` | HTTP 403 with the CloudFrontSigner redirect page; no app content or data | As expected | Pass |
| 2026-10-19 | Live deployment (Midway) | Security | Forged CloudFront-* cookies | HTTP 403 | As expected | Pass |
| 2026-10-19 | Live deployment (Midway) | Security | Direct call to the Lambda function URL; old API Gateway URL | HTTP 403 (IAM); old URL no longer resolves | As expected | Pass |
| 2026-10-19 | Live deployment (Midway) | Functional | GET `/js/cfs-handler.js` | HTTP 200 with v2 authorize endpoint | As expected | Pass |
