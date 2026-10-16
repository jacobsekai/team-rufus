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
