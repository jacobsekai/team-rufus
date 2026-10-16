#!/usr/bin/env bash
# Build the Lambda package, deploy the stack, and upload the frontend.
#
# Usage (from the repository root):
#   deploy/deploy.sh
#
# If you are not signed in, the script signs you in through Conduit (via Ada)
# and shows the target account before changing anything. See aws-login.sh for
# optional settings. Override defaults with STACK_NAME=... DEPLOY_REGION=...
set -euo pipefail

STACK_NAME="${STACK_NAME:-team-rufus-dev}"
DEPLOY_REGION="${DEPLOY_REGION:-us-west-2}"
PACKAGE_DIR=".aws-sam/lambda-package"

cd "$(dirname "$0")/.."
# shellcheck source=deploy/aws-login.sh
source deploy/aws-login.sh

aws_sign_in
confirm_account "Deploy '$STACK_NAME'"

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
    --no-fail-on-empty-changeset

output() {
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$DEPLOY_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
        --output text
}

BUCKET="$(output FrontendBucketName)"
DISTRIBUTION_ID="$(output DistributionId)"
SITE_URL="$(output SiteUrl)"

echo "Uploading frontend..."
aws s3 sync frontend/ "s3://$BUCKET" --delete --region "$DEPLOY_REGION"
aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*" \
    --query "Invalidation.Id" \
    --output text

echo
echo "Deployed: $SITE_URL"
echo "Health check: $SITE_URL/health"
