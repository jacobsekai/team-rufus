# Shared AWS sign-in for deploy.sh and teardown.sh. Source this file; do not
# run it directly.
#
# Uses the AWS CLI's default credentials; no named profile is required. No
# account IDs, role names, or keys are stored in this repository.
#
# Optional settings:
#   CONDUIT_ACCOUNT  Conduit account ID or name (otherwise you are prompted)
#   CONDUIT_ROLE     Conduit role name (otherwise you are prompted)

_signed_in() {
    aws sts get-caller-identity --region "$DEPLOY_REGION" >/dev/null 2>&1
}

_conduit_sign_in() {
    local account="${CONDUIT_ACCOUNT:-}"
    local role="${CONDUIT_ROLE:-}"

    if [[ -z "$account" ]]; then
        read -r -p "Conduit account ID or name: " account
    fi
    if [[ -z "$role" ]]; then
        read -r -p "Conduit role name: " role
    fi
    if [[ -z "$account" || -z "$role" ]]; then
        echo "An account and a role are both required." >&2
        return 1
    fi

    echo "Requesting Conduit credentials..."
    if ! ada credentials update \
        --provider conduit \
        --account "$account" \
        --role "$role" \
        --once; then
        echo "Ada could not get credentials. If your Midway session has expired, run 'mwinit' and try again." >&2
        return 1
    fi
}

aws_sign_in() {
    if _signed_in; then
        return
    fi

    echo "Not signed in to AWS."
    if command -v ada >/dev/null; then
        _conduit_sign_in || exit 1
    else
        echo "Sign in first, for example with one of:" >&2
        echo "  aws login" >&2
        echo "  aws configure sso" >&2
        exit 1
    fi

    if ! _signed_in; then
        echo "Still not signed in. Check the account and role and try again." >&2
        exit 1
    fi
}

# Show which account will be changed and require an explicit "yes".
confirm_account() {
    local action="$1"
    local account_id arn alias

    account_id="$(aws sts get-caller-identity --region "$DEPLOY_REGION" --query Account --output text)"
    arn="$(aws sts get-caller-identity --region "$DEPLOY_REGION" --query Arn --output text)"
    alias="$(aws iam list-account-aliases --query 'AccountAliases[0]' --output text 2>/dev/null || true)"
    [[ "$alias" == "None" ]] && alias=""

    echo
    echo "Account     : $account_id ${alias:+($alias)}"
    echo "Identity    : $arn"
    echo "Region      : $DEPLOY_REGION"
    echo "Stack       : $STACK_NAME"

    if [[ "$alias" =~ [Pp][Rr][Oo]?[Dd] ]]; then
        echo
        echo "WARNING: this account alias looks like a production account." >&2
    fi

    echo
    read -r -p "$action in this account? Type 'yes' to continue: " answer
    if [[ "$answer" != "yes" ]]; then
        echo "Cancelled."
        exit 1
    fi
}
