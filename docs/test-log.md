# Iterative test log

Record representative tests rather than every individual test execution.

| Date | Component | Test type | Test data/condition | Expected result | Actual result | Status |
|---|---|---|---|---|---|---|
| 2026-10-16 | Health endpoint | Functional | `GET /health` | HTTP 200 and non-sensitive status | HTTP 200 and `{"status":"ok"}` | Pass |
| 2026-10-16 | Expression-of-interest API | Validation | Unknown JSON field | HTTP 400; record is not stored | Covered by automated test | Pass |
| 2026-10-16 | Expression-of-interest API | Validation | `consent: false` | HTTP 400; record is not stored | Covered by automated test | Pass |
| 2026-10-16 | Expression-of-interest API | Functional | Valid JSON submission | HTTP 201 and generated ID | Covered by automated test | Pass |

