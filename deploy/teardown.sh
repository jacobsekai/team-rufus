#!/usr/bin/env bash
# Delete everything created by deploy.sh, including both DynamoDB tables and
# all data in them. Run this after the presentation.
set -euo pipefail

STACK_NAME="${STACK_NAME:-team-rufus-dev}"
DEPLOY_REGION="${DEPLOY_REGION:-eu-west-2}"

aws sts get-caller-identity --region "$DEPLOY_REGION" --output table
read -r -p "Permanently delete stack '$STACK_NAME' and ALL its data in $DEPLOY_REGION? Type the stack name to confirm: " answer
if [[ "$answer" != "$STACK_NAME" ]]; then
    echo "Cancelled."
    exit 1
fi

BUCKET="$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$DEPLOY_REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" \
    --output text)"

# CloudFormation cannot delete a bucket that still contains files.
aws s3 rm "s3://$BUCKET" --recursive --region "$DEPLOY_REGION"
sam delete --stack-name "$STACK_NAME" --region "$DEPLOY_REGION" --no-prompts
