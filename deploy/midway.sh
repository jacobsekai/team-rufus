# Midway authentication via CloudFrontSigner (CFS). Source this file from
# deploy.sh or teardown.sh; do not run it directly.
#
# CFS signs CloudFront cookies for Midway-authenticated users who are allowed
# by a Bindle. It needs, in this account:
#   - a KMS key whose alias starts with CFSEncryptionKey
#   - an RSA key pair: the public key in CloudFront (used by the key group in
#     deploy/template.yaml) and the private key in a Secrets Manager secret
#     whose name starts with CFSSigningKey, encrypted with that KMS key
# This mirrors what the official CloudFrontSignerConstructs CDK package does.
# See https://w.amazon.com/bin/view/CloudFrontSigner/Onboarding/
#
# The private key only ever exists in a temporary directory (deleted on exit)
# and in Secrets Manager. It is never written into this repository.
#
# Requires: STACK_NAME, DEPLOY_REGION.

CFS_SERVICE_PRINCIPAL="cloudfrontsigner.aws.internal"
CFS_AUTHORIZE_ENDPOINT="https://cloudfrontsigner.ninjas.security.a2z.com/v2/authorize"

cfs_names() {
    CFS_KMS_ALIAS="alias/CFSEncryptionKey-$STACK_NAME"
    CFS_SECRET_NAME="CFSSigningKey-$STACK_NAME"
}

# Ask for the Bindle that controls who may open the site.
cfs_require_bindle() {
    if [[ -z "${CFS_BINDLE_ID:-}" ]]; then
        read -r -p "Bindle ID that controls access (amzn1.bindle.resource...): " CFS_BINDLE_ID
    fi
    if [[ ! "$CFS_BINDLE_ID" =~ ^amzn1\.bindle\.resource\.[a-z0-9]+$ ]]; then
        echo "That is not a Bindle ID (expected amzn1.bindle.resource...)." >&2
        exit 1
    fi
}

_cfs_ensure_kms_key() {
    if aws kms describe-key --key-id "$CFS_KMS_ALIAS" --region "$DEPLOY_REGION" >/dev/null 2>&1; then
        return
    fi

    local account_id policy key_id
    account_id="$(aws sts get-caller-identity --query Account --output text)"
    policy="$(cat <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AccountAdministration",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::$account_id:root"},
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "Allow CloudFrontSigner prod accounts to use key",
      "Effect": "Allow",
      "Principal": {"Service": "$CFS_SERVICE_PRINCIPAL"},
      "Action": ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:DescribeKey"],
      "Resource": "*"
    }
  ]
}
POLICY
)"

    echo "Creating KMS key $CFS_KMS_ALIAS..."
    key_id="$(aws kms create-key \
        --region "$DEPLOY_REGION" \
        --description "Encrypts the CloudFrontSigner signing key for $STACK_NAME" \
        --policy "$policy" \
        --tags TagKey=Project,TagValue=T-Level-Team-Project TagKey=Environment,TagValue=Development \
        --query KeyMetadata.KeyId --output text)"
    aws kms create-alias --region "$DEPLOY_REGION" --alias-name "$CFS_KMS_ALIAS" --target-key-id "$key_id"
}

# Prints the public key ID stored in the secret, or nothing.
_cfs_secret_public_key_id() {
    aws secretsmanager get-secret-value \
        --region "$DEPLOY_REGION" \
        --secret-id "$CFS_SECRET_NAME" \
        --query SecretString --output text 2>/dev/null \
        | python3 -c 'import json, sys; print(json.load(sys.stdin).get("PUBLIC_KEY_ID", ""))' 2>/dev/null \
        || true
}

# Generate a key pair, register the public key with CloudFront, and store
# {PUBLIC_KEY_ID, PRIVATE_KEY} in the secret (creating it if needed).
_cfs_create_key_pair() {
    local work public_key_id stamp
    work="$(mktemp -d)"
    chmod 700 "$work"
    # shellcheck disable=SC2064
    trap "rm -rf '$work'" RETURN

    echo "Generating a new CloudFrontSigner key pair..."
    (umask 077 && openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$work/private.pem" 2>/dev/null)
    openssl pkey -in "$work/private.pem" -pubout -out "$work/public.pem"

    stamp="$(date -u +%Y%m%d%H%M%S)"
    python3 - "$work/public.pem" "$STACK_NAME-$stamp" "$work/public-key-config.json" <<'PY'
import json, sys
public_pem, name, out = sys.argv[1:4]
with open(public_pem, encoding="utf-8") as handle:
    config = {"CallerReference": name, "Name": "CFSSigningKey-" + name, "EncodedKey": handle.read()}
with open(out, "w", encoding="utf-8") as handle:
    json.dump(config, handle)
PY
    public_key_id="$(aws cloudfront create-public-key \
        --public-key-config "file://$work/public-key-config.json" \
        --query PublicKey.Id --output text)"

    python3 - "$work/private.pem" "$public_key_id" "$work/secret.json" <<'PY'
import json, os, sys
private_pem, public_key_id, out = sys.argv[1], sys.argv[2], sys.argv[3]
with open(private_pem, encoding="utf-8") as handle:
    secret = {"PUBLIC_KEY_ID": public_key_id, "PRIVATE_KEY": handle.read()}
fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    json.dump(secret, handle)
PY

    if aws secretsmanager describe-secret --region "$DEPLOY_REGION" --secret-id "$CFS_SECRET_NAME" >/dev/null 2>&1; then
        aws secretsmanager put-secret-value \
            --region "$DEPLOY_REGION" \
            --secret-id "$CFS_SECRET_NAME" \
            --secret-string "file://$work/secret.json" >/dev/null
    else
        aws secretsmanager create-secret \
            --region "$DEPLOY_REGION" \
            --name "$CFS_SECRET_NAME" \
            --description "CloudFrontSigner signing key for $STACK_NAME" \
            --kms-key-id "$CFS_KMS_ALIAS" \
            --secret-string "file://$work/secret.json" \
            --tags Key=Project,Value=T-Level-Team-Project Key=Environment,Value=Development >/dev/null
    fi
}

_cfs_allow_signer_to_read_secret() {
    local policy
    policy="$(cat <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "$CFS_SERVICE_PRINCIPAL"},
      "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
      "Resource": "*"
    }
  ]
}
POLICY
)"
    aws secretsmanager put-resource-policy \
        --region "$DEPLOY_REGION" \
        --secret-id "$CFS_SECRET_NAME" \
        --resource-policy "$policy" >/dev/null
}

# Make sure the KMS key, CloudFront public key, and secret exist and match.
# Sets CFS_PUBLIC_KEY_ID and CFS_SECRET_ARN.
cfs_ensure_signing_key() {
    cfs_names
    _cfs_ensure_kms_key

    CFS_PUBLIC_KEY_ID="$(_cfs_secret_public_key_id)"
    if [[ -z "$CFS_PUBLIC_KEY_ID" ]] \
        || ! aws cloudfront get-public-key --id "$CFS_PUBLIC_KEY_ID" >/dev/null 2>&1; then
        _cfs_create_key_pair
        CFS_PUBLIC_KEY_ID="$(_cfs_secret_public_key_id)"
    fi

    _cfs_allow_signer_to_read_secret
    CFS_SECRET_ARN="$(aws secretsmanager describe-secret \
        --region "$DEPLOY_REGION" --secret-id "$CFS_SECRET_NAME" \
        --query ARN --output text)"
    echo "CloudFrontSigner public key: $CFS_PUBLIC_KEY_ID"
}

# Write error/403.html and js/cfs-handler.js into a directory, filled in
# exactly as CloudFrontSignerConstructs does (CFS checks the 403 page's hash).
cfs_render_files() {
    local target="$1"
    mkdir -p "$target/error" "$target/js"
    python3 - "$CFS_BINDLE_ID" "$CFS_SECRET_ARN" "$CFS_AUTHORIZE_ENDPOINT" "$target" <<'PY'
import sys
from pathlib import Path

bindle_id, secret_arn, endpoint, target = sys.argv[1:5]
templates = Path("deploy/cfs")

html = (templates / "403.html.template").read_text(encoding="utf-8")
html = html.replace("INSERT-BINDLE-ID-HERE", bindle_id, 1)
html = html.replace("INSERT-SECRET-ARN-HERE", secret_arn, 1)
(Path(target) / "error" / "403.html").write_text(html, encoding="utf-8")

js = (templates / "cfs-handler.js.template").read_text(encoding="utf-8")
js = js.replace("INSERT-SERVICE-ENDPOINT-HERE", endpoint)
js = js.replace("INSERT-COOKIE-PARTITIONED-HERE", "", 1)
js = js.replace("INSERT-COOKIE-SAMESITE-HERE", "Lax", 1)
js = js.replace("INSERT-SKIP-DOUBLE-DECODE-HERE", "false")
(Path(target) / "js" / "cfs-handler.js").write_text(js, encoding="utf-8")
PY
}

# Remove the signing key resources. Call after the stack (and its key group)
# has been deleted.
cfs_delete_signing_key() {
    cfs_names
    local public_key_id etag key_id
    public_key_id="$(_cfs_secret_public_key_id)"
    if [[ -n "$public_key_id" ]]; then
        etag="$(aws cloudfront get-public-key --id "$public_key_id" --query ETag --output text 2>/dev/null || true)"
        if [[ -n "$etag" ]]; then
            aws cloudfront delete-public-key --id "$public_key_id" --if-match "$etag"
        fi
    fi
    aws secretsmanager delete-secret --region "$DEPLOY_REGION" \
        --secret-id "$CFS_SECRET_NAME" --force-delete-without-recovery >/dev/null 2>&1 || true
    key_id="$(aws kms describe-key --region "$DEPLOY_REGION" --key-id "$CFS_KMS_ALIAS" \
        --query KeyMetadata.KeyId --output text 2>/dev/null || true)"
    if [[ -n "$key_id" ]]; then
        aws kms delete-alias --region "$DEPLOY_REGION" --alias-name "$CFS_KMS_ALIAS"
        aws kms schedule-key-deletion --region "$DEPLOY_REGION" --key-id "$key_id" \
            --pending-window-in-days 7 >/dev/null
    fi
}
