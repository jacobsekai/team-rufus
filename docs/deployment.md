# Deployment design

The prototype is hosted on AWS so the team and assessors can use it from a
browser. It is a development deployment for synthetic data only and should be
deleted after the presentation.

## Architecture

```text
                       ┌─ /*                → S3 bucket (frontend files, private)
Browser ── CloudFront ─┤
   (HTTPS)             └─ /api/*, /health   → API Gateway HTTP API → Lambda (Flask) → DynamoDB
```

| Component | Purpose |
|---|---|
| CloudFront | One public HTTPS address for the frontend and the API |
| S3 | Stores the frontend HTML, CSS, and JavaScript |
| API Gateway (HTTP API) | Receives API requests from CloudFront and invokes Lambda |
| Lambda | Runs the unchanged Flask app via `backend/lambda_handler.py` |
| DynamoDB | The two tables defined in `infra/dynamodb-table.yaml` |

Everything is defined in `deploy/template.yaml` (AWS SAM). The tables are
included as a nested stack so each table is defined in one place only.

Because the frontend and API share the CloudFront address, the frontend calls
the API with relative paths such as `fetch("/api/users", ...)` and no CORS
configuration is needed.

## Security decisions

- **Private bucket.** S3 public access is fully blocked. Only this CloudFront
  distribution can read files, using Origin Access Control.
- **HTTPS only.** CloudFront redirects HTTP to HTTPS for pages and refuses plain
  HTTP for API calls. CloudFront connects to API Gateway over TLS 1.2.
- **No API caching.** `/api/*` uses the managed `CachingDisabled` policy so one
  user's response can never be served to another.
- **Security headers.** The managed `SecurityHeadersPolicy` adds HSTS,
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and
  `X-XSS-Protection` to every response.
- **Least-privilege Lambda.** The function may only call `dynamodb:PutItem` on
  the two project tables. It cannot read, update, or delete data.
- **Rate limiting.** API Gateway is limited to 10 requests per second (burst 20)
  so abuse cannot run up costs.
- **Logs expire.** Lambda logs are kept for 14 days.
- **Encryption at rest.** S3 and both DynamoDB tables are encrypted.

### Known limitations (acceptable for a prototype)

- The API Gateway address can also be called directly, bypassing CloudFront.
  The same validation and rate limit still apply.
- The rate limit is shared by all users rather than applied per person. AWS WAF
  would add per-IP limits but costs about $6 per month.
- There is no custom domain; the address is `https://<id>.cloudfront.net`.

## Deploying

Requirements: an AWS login for the project account, the AWS CLI, the AWS SAM
CLI, and Python 3.12.

```bash
deploy/deploy.sh
```

The script prints the AWS account it is using, builds the Lambda package,
deploys the stack `team-rufus-dev` to `eu-west-2`, uploads `frontend/`, clears
the CloudFront cache, and prints the site URL. The first deployment takes
about 5 to 10 minutes while CloudFront is created.

Run the same command again after changing backend or frontend code.

## Removing everything

```bash
deploy/teardown.sh
```

This permanently deletes the stack, the frontend bucket, and both DynamoDB
tables including all data. It asks you to type the stack name to confirm.
