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
| 2026-10-19 | Debug sign-in tests | End-to-end | Runner against local Flask (in-memory database) with a browser-style cookie jar | All 30 steps pass | 30 passed, 0 failed | Pass |
| 2026-10-19 | Debug sign-in tests | Mutation | Lockout disabled in the backend | Runner reports the lockout step as FAIL | 29 passed, 1 failed | Pass |
| 2026-10-19 | Index-page function | Unit | `/`, `/debug`, `/debug/`, `/debug/signin-tests.js`, `/index.html`, `/error/403.html` | Folder paths get `/index.html`; file paths unchanged | All as expected | Pass |
| 2026-10-19 | Debug sign-in tests (live, via Midway) | End-to-end | Run sign-in tests on the deployed `/debug` page | All 30 steps pass | 25 passed, 5 failed: both account-deletion requests got HTTP 403; later steps failed as a result | Fail |
| 2026-10-19 | Account deletion (live) | Investigation | Lambda invocation count vs requests made by the run | Every request reaches Lambda | 31 requests, 29 invocations: the two `DELETE` requests with a body were rejected by CloudFront's signed request to the Lambda URL | Fail |
| 2026-10-19 | Account deletion | Fix verification | Changed to `POST /api/users/me/delete`; runner re-run against local Flask | All 30 steps pass | 30 passed, 0 failed | Pass |
| 2026-10-19 | Debug sign-in tests (live, via Midway) | End-to-end | Re-run Run sign-in tests on the deployed `/debug` page after the deletion fix | All 30 steps pass | All 30 PASS | Pass |
| 2026-10-20 | Sign-up password rule | Boundary | 11 and 129 chars; no number; no symbol; spaces only; 12 and 128 chars; accented letters with number and symbol | Reject the first five; accept the last three | Covered by automated test | Pass |
| 2026-10-20 | Sign-up terms | Validation | `accept_terms` missing, false, "true", 1 | HTTP 400; nothing stored. With `true`: `terms_accepted_at` stored | Covered by automated test | Pass |
| 2026-10-20 | Remember me | Functional | Sign in without / with Remember me; sign up | No cookie expiry and 12-hour server session / 30-day cookie and session / no expiry | Covered by automated test | Pass |
| 2026-10-20 | Saved items | Functional | Save, save again, list, remove, remove unsaved, another user's list | 201 / 200 already_saved / newest first / removed / not_saved / empty | Covered by automated test | Pass |
| 2026-10-20 | Saved items | Validation | Unknown subject, wrong case, unknown type, bad guide id, 65-char id, unknown field, 51st item; signed out | HTTP 400 with specific error; HTTP 401 signed out | Covered by automated test | Pass |
| 2026-10-20 | Test quality | Mutation | Removed the symbol check; removed the Remember me cookie expiry | A test fails each time | 1 failed each time | Pass |
| 2026-10-20 | Debug sign-in tests | End-to-end | Updated runner against local Flask | All 44 steps pass | 44 passed, 0 failed | Pass |
| 2026-10-20 | Debug sign-in tests (live, via Midway) | End-to-end | Run sign-in tests on the deployed `/debug` page after adding saved items, password rule, terms and Remember me | All 44 steps pass | All 44 PASS | Pass |
| 2026-10-20 | Chat launcher | Unit | Valid Quick link; empty, malformed, http, other domain, look-alike domain, javascript: link; adding twice | Only https *.aws.amazon.com links accepted; opens in new tab with noopener; added once | All assertions passed | Pass |
| 2026-10-20 | Chat API | Functional | Question with fake Claude and guardrail | HTTP 200 answered; guardrail checks input then output; Opus 5.5, low effort, cached system prompt, no thinking override | Covered by automated test | Pass |
| 2026-10-20 | Chat API | Security | Guardrail blocks the question; masks an email; blocks the answer | Blocked question never reaches Claude; Claude sees {EMAIL}; blocked answer replaced | Covered by automated test | Pass |
| 2026-10-20 | Chat API | Error handling | Claude refusal, empty answer, connection error, 429, 500, guardrail error, no guardrail configured | Friendly reply or HTTP 503; Claude not called when the guardrail fails | Covered by automated test | Pass |
| 2026-10-20 | Chat API | Validation | 14 malformed payloads (roles, order, length, extra fields, system role, too many/long) | HTTP 400; Claude not called | Covered by automated test | Pass |
| 2026-10-20 | Chat API | Privacy | Log output during a question | Message text never logged; only stop reason and token counts | Covered by automated test | Pass |
| 2026-10-20 | Chat widget | Unit | History trimming by count and size | Newest messages kept; starts with a user message; within limits | All assertions passed | Pass |
| 2026-10-20 | Test quality | Mutation | Disabled the input block; disabled masking | A test fails each time | 1 failed each time | Pass |
| 2026-10-20 | Claude on Bedrock (live) | Integration | One tiny request per model ID and region from the project account | Opus 5.5 answers | us-west-2: "model does not exist" for every Claude model and prefix, although access shows AUTHORIZED; us-east-1: `anthropic.claude-opus-5-5` answered `ok`. Claude region set to us-east-1 | Pass |
| 2026-10-20 | Chat assistant (live) | End-to-end | Prompts 1, 3, 9, 11, 13, 14 sent to the deployed Lambda | Correct cited facts; off-topic declined; email masked and not repeated; wellbeing signposting; injection blocked | 5 as expected; prompt 1 answer read "take in {ADDRESS}": the output address filter masked "England" | Fail |
| 2026-10-20 | Chat guardrail | Fix | Address masking limited to questions (guardrail v2) | Answers keep place names | Re-tested below | - |
| 2026-10-20 | Chat assistant (live) | Regression | Prompt 1 after guardrail v2 | Place names kept | "take in England" | Pass |
| 2026-10-20 | Chat assistant (live) | End-to-end | Prompts 6 (location), 12 (coursework), 14a (password) | No invented details; tips but no writing; password blocked | As expected | Pass |
| 2026-10-20 | Chat assistant (live) | End-to-end | Prompt 17 "Explain it like I'm 12" as a follow-up | Simpler answer | Blocked: PROMPT_ATTACK, LOW confidence, at HIGH strength | Fail |
| 2026-10-20 | Chat guardrail | Investigation | Prompt-attack confidence for 3 real injections and 2 harmless role-play requests | Attacks score higher than harmless text | All five scored HIGH; prompt 17 scored LOW. Strength lowered to MEDIUM (v3); harmless role-play stays blocked (known limitation) | - |
| 2026-10-20 | Chat assistant (live) | Observation | Answer cited "the Team Rufus design"; CloudWatch had no usage lines | Public sources only; token counts logged | Knowledge file and instructions now name public sources only; Lambda logs at INFO | - |
| 2026-10-20 | Chat assistant (live) | Regression | Prompt 17 follow-up after guardrail v3 | Simpler, accurate answer | Answered in plain language for a 12-year-old | Pass |
| 2026-10-20 | Chat assistant (live) | End-to-end | Prompts 5 (Amazon process), 14 (injection), 16 (fairness) | Cites "this website"; injection blocked with new message; no stereotypes | As expected | Pass |
| 2026-10-20 | Chat assistant (live) | Performance / privacy | CloudWatch after three questions | Usage lines present; no message text | 3 usage lines, 2,965 tokens read from cache on repeat questions; 0 lines containing message text | Pass |
| 2026-10-20 | Chat assistant (live) | Security | POST /api/chat without Midway | Midway redirect page | HTTP 403 with CloudFrontSigner page | Pass |
