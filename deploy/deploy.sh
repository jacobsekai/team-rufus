#!/usr/bin/env bash
# Build the Lambda package, deploy the stack, and upload the frontend.
#
# Usage (from the repository root):
#   deploy/deploy.sh
#
# If you are not signed in, the script signs you in through Conduit (via Ada)
# and shows the target account before changing anything. See aws-login.sh for
# optional settings. Override defaults with STACK_NAME=... DEPLOY_REGION=...
#
# The site is protected by Midway (CloudFrontSigner). Set CFS_BINDLE_ID to the
# Bindle that controls who may open it, or you will be asked for it. Set
# DISTRIBUTION_ENABLED=false to deploy with the site switched off.
set -euo pipefail

STACK_NAME="${STACK_NAME:-team-rufus-dev}"
DEPLOY_REGION="${DEPLOY_REGION:-us-west-2}"
PACKAGE_DIR=".aws-sam/lambda-package"

cd "$(dirname "$0")/.."
# shellcheck source=deploy/aws-login.sh
source deploy/aws-login.sh

aws_sign_in
confirm_account "Deploy '$STACK_NAME'"

# shellcheck source=deploy/midway.sh
source deploy/midway.sh
cfs_require_bindle
cfs_ensure_signing_key
DISTRIBUTION_ENABLED="${DISTRIBUTION_ENABLED:-true}"

# Dependencies must be resolved by the same Python version Lambda runs (3.12).
find_python312() {
    for candidate in "${PYTHON:-}" python3.12; do
        if [[ -n "$candidate" ]] && "$candidate" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))' 2>/dev/null; then
            echo "$candidate"
            return
        fi
    done
    if command -v mise >/dev/null && mise where python@3.12 >/dev/null 2>&1; then
        echo "$(mise where python@3.12)/bin/python3.12"
        return
    fi
    echo "Python 3.12 is required to build the Lambda package. Install it or set PYTHON=/path/to/python3.12." >&2
    exit 1
}
PYTHON312="$(find_python312)"

echo "Building Lambda package..."
rm -rf "$PACKAGE_DIR"
# Install Linux ARM wheels that match the Lambda runtime, not this computer.
"$PYTHON312" -m pip install \
    --quiet \
    --requirement backend/requirements.txt \
    --target "$PACKAGE_DIR" \
    --platform manylinux2014_aarch64 \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all:
rsync -a --exclude __pycache__ backend "$PACKAGE_DIR/"

echo "Deploying infrastructure..."
sam deploy \
    --template-file deploy/template.yaml \
    --stack-name "$STACK_NAME" \
    --region "$DEPLOY_REGION" \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
    --resolve-s3 \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset \
    --parameter-overrides \
        "CfsPublicKeyId=$CFS_PUBLIC_KEY_ID" \
        "DistributionEnabled=$DISTRIBUTION_ENABLED"

output() {
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$DEPLOY_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
        --output text
}

BUCKET="$(output FrontendBucketName)"
CONTENT_BUCKET="$(output ContentBucketName)"
DISTRIBUTION_ID="$(output DistributionId)"
SITE_URL="$(output SiteUrl)"

echo "Uploading downloadable content..."
aws s3 sync content/ "s3://$CONTENT_BUCKET" --delete --exclude README.md --region "$DEPLOY_REGION"

echo "Uploading frontend and Midway sign-in files..."
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
cp -R frontend/. "$STAGING/"
cfs_render_files "$STAGING"
aws s3 sync "$STAGING/" "s3://$BUCKET" --delete --region "$DEPLOY_REGION" \
    --exclude "error/403.html" --exclude "js/cfs-handler.js"
# Never cached, so browsers do not loop on a stale redirect page.
for file in error/403.html js/cfs-handler.js; do
    aws s3 cp "$STAGING/$file" "s3://$BUCKET/$file" --region "$DEPLOY_REGION" \
        --cache-control "no-store"
done
aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*" \
    --query "Invalidation.Id" \
    --output text

echo
echo "Deployed: $SITE_URL (Midway sign-in required)"
echo
echo "First deployment only:"
echo "  1. Open https://cloudfrontsigner.ninjas.security.a2z.com/ > Onboard > enter ${SITE_URL#https://}"
echo "  2. In Bindles ($CFS_BINDLE_ID) add 'CloudFront Domain Permissions'"
echo "     for the people or groups who should have access."
