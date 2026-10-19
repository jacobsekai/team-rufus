#!/usr/bin/env bash
# Delete everything created by deploy.sh, including both DynamoDB tables and
# all data in them. Run this after the presentation.
set -euo pipefail

STACK_NAME="${STACK_NAME:-team-rufus-dev}"
DEPLOY_REGION="${DEPLOY_REGION:-us-west-2}"

cd "$(dirname "$0")/.."
# shellcheck source=deploy/aws-login.sh
source deploy/aws-login.sh
# shellcheck source=deploy/midway.sh
source deploy/midway.sh

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

# The key group that used the CloudFrontSigner key went with the stack, so the
# key, its secret, and the KMS key (7-day deletion window) can now be removed.
cfs_delete_signing_key

echo "Deleted. Also offboard the domain at https://cloudfrontsigner.ninjas.security.a2z.com/"
