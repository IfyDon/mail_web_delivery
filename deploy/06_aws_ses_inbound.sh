#!/usr/bin/env bash
# =============================================================================
# 06_aws_ses_inbound.sh — Provision AWS SES inbound mail receiving
#
# What this script does:
#   1. Creates an S3 bucket to store raw inbound MIME messages
#   2. Attaches a bucket policy allowing SES to write to it
#   3. Creates an SNS topic for inbound-mail notifications
#   4. Subscribes your live HTTPS endpoint to that SNS topic
#   5. Creates (or reuses) an SES receipt rule set with S3 + SNS actions
#      and activates it
#   6. Updates .env with the bucket name so the app can fetch stored mail
#
# This provisions ONE shared receiving pipeline for the whole platform —
# it does not touch any customer's domain DNS. Each customer who wants
# inbound mail adds an MX record on THEIR OWN domain (shown in the
# dashboard once they create an inbound route) pointing at:
#   10 inbound-smtp.<region>.amazonaws.com
#
# Prerequisites:
#   - awscli installed and configured
#   - HTTPS is live (run 04_ssl.sh first) — SNS requires HTTPS to subscribe
#   - SES inbound receiving is only available in us-east-1, us-west-2, eu-west-1
#
# Usage:
#   bash deploy/06_aws_ses_inbound.sh  yourapp.com  us-east-1
# =============================================================================
set -euo pipefail

APP_DOMAIN="${1:?Usage: $0 APP_DOMAIN AWS_REGION}"
REGION="${2:-us-east-1}"
BUCKET_NAME="${BUCKET_NAME:-${APP_DOMAIN//./-}-inbound-mail}"
SNS_TOPIC_NAME="webmail-inbound-notifications"
RULE_SET_NAME="webmail-inbound-rules"
RULE_NAME="webmail-catch-all"
S3_PREFIX="inbound/"

case "$REGION" in
  us-east-1|us-west-2|eu-west-1) ;;
  *) echo "!! SES inbound receiving is not available in $REGION (only us-east-1, us-west-2, eu-west-1)"; exit 1 ;;
esac

ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

echo "==> SES inbound receiving setup for account=$ACCOUNT_ID region=$REGION"

# ── 1. Create S3 bucket ──────────────────────────────────────────────────────
echo ""
echo "==> [1/5] Creating S3 bucket '$BUCKET_NAME'..."
_create_bucket_err=$(mktemp)
if [[ "$REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" 2>"$_create_bucket_err"
else
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION" 2>"$_create_bucket_err"
fi
_create_bucket_rc=$?
if [[ $_create_bucket_rc -ne 0 ]]; then
    if grep -q "BucketAlreadyOwnedByYou" "$_create_bucket_err"; then
        echo "   (bucket already exists — owned by this account, continuing)"
    else
        echo "   FAILED to create bucket:"
        cat "$_create_bucket_err" >&2
        rm -f "$_create_bucket_err"
        exit 1
    fi
fi
rm -f "$_create_bucket_err"

echo "==> [2/5] Attaching bucket policy allowing SES to write..."
aws s3api put-bucket-policy --bucket "$BUCKET_NAME" --policy "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [{
    \"Sid\": \"AllowSESPuts\",
    \"Effect\": \"Allow\",
    \"Principal\": { \"Service\": \"ses.amazonaws.com\" },
    \"Action\": \"s3:PutObject\",
    \"Resource\": \"arn:aws:s3:::$BUCKET_NAME/*\",
    \"Condition\": {
      \"StringEquals\": { \"aws:Referer\": \"$ACCOUNT_ID\" }
    }
  }]
}"

# ── 3. Create SNS topic + subscribe our endpoint ─────────────────────────────
echo "==> [3/5] Creating SNS topic '$SNS_TOPIC_NAME'..."
TOPIC_ARN=$(aws sns create-topic --name "$SNS_TOPIC_NAME" --region "$REGION" \
    --output text --query 'TopicArn')
echo "   Topic ARN: $TOPIC_ARN"

WEBHOOK_URL="https://$APP_DOMAIN/api/v1/webhooks/ses-inbound-email/"
echo "   Subscribing $WEBHOOK_URL..."
echo "   (SNS will POST a SubscriptionConfirmation — the app auto-confirms it)"
aws sns subscribe --topic-arn "$TOPIC_ARN" --protocol https \
    --notification-endpoint "$WEBHOOK_URL" --region "$REGION"
echo "   Waiting 5s for SNS to deliver the confirmation request..."
sleep 5
aws sns list-subscriptions-by-topic --topic-arn "$TOPIC_ARN" --region "$REGION" --output table

# ── 4. Create receipt rule set (S3 + SNS actions) and activate it ────────────
echo "==> [4/5] Creating SES receipt rule set '$RULE_SET_NAME'..."
aws ses create-receipt-rule-set --rule-set-name "$RULE_SET_NAME" --region "$REGION" 2>/dev/null \
    || echo "   (rule set already exists)"

aws ses create-receipt-rule --rule-set-name "$RULE_SET_NAME" --region "$REGION" --rule "{
  \"Name\": \"$RULE_NAME\",
  \"Enabled\": true,
  \"ScanEnabled\": true,
  \"Actions\": [
    { \"S3Action\": { \"BucketName\": \"$BUCKET_NAME\", \"ObjectKeyPrefix\": \"$S3_PREFIX\" } },
    { \"SNSAction\": { \"TopicArn\": \"$TOPIC_ARN\", \"Encoding\": \"UTF-8\" } }
  ]
}" 2>/dev/null || echo "   (rule already exists — edit it manually if you need to change actions)"

echo "==> [5/5] Activating rule set '$RULE_SET_NAME'..."
aws ses set-active-receipt-rule-set --rule-set-name "$RULE_SET_NAME" --region "$REGION"

# ── Update .env ───────────────────────────────────────────────────────────────
APP_DIR="${APP_DIR:-/opt/web_mail}"
if [[ -f "$APP_DIR/.env" ]]; then
    grep -q '^AWS_SES_INBOUND_BUCKET=' "$APP_DIR/.env" \
        && sed -i "s|^AWS_SES_INBOUND_BUCKET=.*|AWS_SES_INBOUND_BUCKET=$BUCKET_NAME|" "$APP_DIR/.env" \
        || echo "AWS_SES_INBOUND_BUCKET=$BUCKET_NAME" >> "$APP_DIR/.env"
    grep -q '^AWS_SES_INBOUND_PREFIX=' "$APP_DIR/.env" \
        && sed -i "s|^AWS_SES_INBOUND_PREFIX=.*|AWS_SES_INBOUND_PREFIX=$S3_PREFIX|" "$APP_DIR/.env" \
        || echo "AWS_SES_INBOUND_PREFIX=$S3_PREFIX" >> "$APP_DIR/.env"
    echo "   Updated AWS_SES_INBOUND_BUCKET / AWS_SES_INBOUND_PREFIX in .env"
    echo "   Restart the app to pick these up: docker compose up -d web worker"
fi

echo ""
echo "====================================================="
echo " Inbound receiving is provisioned platform-wide."
echo ""
echo " Each customer who wants inbound mail must add this MX record"
echo " on THEIR OWN domain (shown automatically in their dashboard"
echo " once they add an inbound route there):"
echo ""
echo "   Type     : MX"
echo "   Priority : 10"
echo "   Value    : inbound-smtp.$REGION.amazonaws.com"
echo ""
echo " S3 bucket : $BUCKET_NAME"
echo " SNS topic : $TOPIC_ARN"
echo " Rule set  : $RULE_SET_NAME (active)"
echo "====================================================="
