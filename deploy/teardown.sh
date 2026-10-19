#!/usr/bin/env bash
# Delete everything created by deploy.sh, including both DynamoDB tables and
# all data in them. Run this after the presentation.
set -euo pipefail

STACK_NAME="${STACK_NAME:-team-rufus-dev}"
DEPLOY_REGION="${DEPLOY_REGION:-us-west-2}"

cd "$(dirname "$0")/.."
# shellcheck source=deploy/aws-login.sh
source deploy/aws-login.sh

aws_sign_in
confirm_account "Delete '$STACK_NAME'"
read -r -p "Permanently delete stack '$STACK_NAME' and ALL its data in $DEPLOY_REGION? Type the stack name to confirm: " answer
if [[ "$answer" != "$STACK_NAME" ]]; then
    echo "Cancelled."
    exit 1
fi

output() {
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$DEPLOY_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
        --output text
}

# CloudFormation cannot delete a bucket that still contains files.
for output_key in FrontendBucketName ContentBucketName; do
    bucket="$(output "$output_key")"
    if [[ -n "$bucket" && "$bucket" != "None" ]]; then
        aws s3 rm "s3://$bucket" --recursive --region "$DEPLOY_REGION"
    fi
done
sam delete --stack-name "$STACK_NAME" --region "$DEPLOY_REGION" --no-prompts
