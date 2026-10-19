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
| DynamoDB | The three tables defined in `infra/dynamodb-table.yaml` |
| S3 (content) | Private bucket for downloadable files; reachable only via short-lived signed links |

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
- **Least-privilege Lambda.** The function may only create expressions of
  interest (`PutItem`), manage single user and session items (`PutItem`,
  `GetItem`, `UpdateItem`, `DeleteItem`), and read content files
  (`s3:GetObject`). It cannot scan or list any table, so it cannot dump data.
- **Private downloads.** The content bucket is not connected to CloudFront.
  Each download is a link signed by the Lambda function that expires after
  5 minutes; members-only links are only issued to signed-in users.
- **Rate limiting.** API Gateway is limited to 10 requests per second (burst 20)
  so abuse cannot run up costs.
- **Logs expire.** Lambda logs are kept for 14 days.
- **Encryption at rest.** Both S3 buckets and all DynamoDB tables are encrypted.

### Known limitations (acceptable for a prototype)

- The API Gateway address can also be called directly, bypassing CloudFront.
  The same validation and rate limit still apply.
- The rate limit is shared by all users rather than applied per person. AWS WAF
  would add per-IP limits but costs about $6 per month.
- There is no custom domain; the address is `https://<id>.cloudfront.net`.

## Security finding: CloudFront disabled (2026-10-19)

Amazon's Shepherd scanner raised a Sev-2.5 ticket (V2414010851, due
2026-10-24): "Lack of Approved Authentication for Publicly Accessible
CloudFront". Amazon policy requires Midway authentication on any public
CloudFront site in an Amazon AWS account, and this site was open to the
internet.

Containment: the distribution was disabled on 2026-10-19, as the ticket
recommends. The template now keeps it disabled (`DistributionEnabled`
defaults to `false`) so redeploying cannot re-expose it. Do not enable it
until Midway sign-in (CloudFrontSigner with a Bindle) protects the site.

Do not press "Request Verification Of Fix" or close the ticket; Shepherd
resolves it automatically.

## Deploying

Requirements: access to the project AWS account, the AWS CLI, the AWS SAM
CLI, and Python 3.12.

```bash
deploy/deploy.sh
```

### Signing in

The scripts use the AWS CLI's default credentials; no named profile is needed.
If there are no valid credentials:

- **With Ada installed (Conduit):** the script asks for the Conduit account ID
  or name and the role, then runs `ada credentials update --provider conduit`.
  Run `mwinit` first if your Midway session has expired. To skip the prompts,
  set `CONDUIT_ACCOUNT` and `CONDUIT_ROLE` in your shell.
- **Without Ada:** the script stops and suggests `aws login` or
  `aws configure sso`.

Before changing anything, the script shows the account ID, account alias,
identity, region, and stack name, and continues only if you type `yes`. It
warns if the account alias looks like a production account.

Account IDs and role names are entered at run time and are never stored in the
repository.

### What the script does

After sign-in, the script builds the Lambda package,
deploys the stack `team-rufus-dev` to `us-west-2`, uploads `content/` and
`frontend/`, clears
the CloudFront cache, and prints the site URL. The first deployment takes
about 5 to 10 minutes while CloudFront is created.

Run the same command again after changing backend or frontend code.

## Removing everything

```bash
deploy/teardown.sh
```

This permanently deletes the stack, both buckets, and all three DynamoDB
tables including all data. It uses the same sign-in, shows the account, and
then asks you to type the stack name to confirm.
