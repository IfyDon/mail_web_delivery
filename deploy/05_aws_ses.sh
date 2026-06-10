#!/usr/bin/env bash
# =============================================================================
# 05_aws_ses.sh — Configure AWS SES for production sending
#
# What this script does:
#   1. Verifies your sending domain in SES (issues TXT token to add to DNS)
#   2. Enables DKIM in SES (issues 3 CNAME records to add to DNS)
#   3. Creates an SNS topic for bounce/complaint notifications
#   4. Subscribes your live HTTPS endpoint to the SNS topic
#   5. Creates a SES configuration set and attaches bounce/complaint/delivery
#      event destinations pointing to the SNS topic
#   6. Prints the AWS support case template to request production access
#      (SES is sandboxed by default — only verified addresses can receive mail)
#
# Prerequisites:
#   - awscli installed and configured (aws configure, or IAM role on the server)
#   - Your domain DNS A record already points to this server
#   - HTTPS is live (run 04_ssl.sh first) — SNS requires HTTPS to subscribe
#
# Usage:
#   bash deploy/05_aws_ses.sh  yourdomain.com  us-east-1
# =============================================================================
set -euo pipefail

DOMAIN="${1:?Usage: $0 SENDING_DOMAIN AWS_REGION}"
REGION="${2:-us-east-1}"
APP_DOMAIN="${APP_DOMAIN:-$DOMAIN}"   # domain where the app is hosted (for SNS endpoint)
CONFIG_SET="webmail-events"
SNS_TOPIC_NAME="webmail-email-events"

echo "==> SES Configuration for domain=$DOMAIN region=$REGION"

# ── 1. Verify domain identity ────────────────────────────────────────────────
echo ""
echo "==> [1/6] Verifying domain identity in SES..."
VERIFY_TOKEN=$(aws ses verify-domain-identity \
    --domain "$DOMAIN" \
    --region "$REGION" \
    --output text \
    --query 'VerificationToken')

echo ""
echo "  ✦ Add this TXT record to your DNS BEFORE proceeding:"
echo "  ┌──────────────────────────────────────────────────────────────┐"
echo "  │ Type : TXT                                                   │"
echo "  │ Host : _amazonses.$DOMAIN                                    │"
echo "  │ Value: $VERIFY_TOKEN                                         │"
echo "  └──────────────────────────────────────────────────────────────┘"
echo ""
read -p "  Press ENTER after adding the DNS record (propagation may take up to 1 hour)..."

# ── 2. Enable DKIM signing ────────────────────────────────────────────────────
echo "==> [2/6] Enabling DKIM for $DOMAIN..."
DKIM_TOKENS=$(aws ses verify-domain-dkim \
    --domain "$DOMAIN" \
    --region "$REGION" \
    --output json \
    --query 'DkimTokens')

echo ""
echo "  ✦ Add these 3 CNAME records to your DNS:"
echo "  (AWS will use these to sign your outgoing mail)"
echo ""
i=1
for token in $(echo "$DKIM_TOKENS" | jq -r '.[]'); do
    echo "  CNAME $i:"
    echo "    Host : ${token}._domainkey.$DOMAIN"
    echo "    Value: ${token}.dkim.amazonses.com"
    echo ""
    i=$((i+1))
done
echo "  Press ENTER after adding the 3 CNAME records..."
read -r

# ── 3. Create configuration set ──────────────────────────────────────────────
echo "==> [3/6] Creating SES configuration set '$CONFIG_SET'..."
aws ses create-configuration-set \
    --configuration-set "{\"Name\":\"$CONFIG_SET\"}" \
    --region "$REGION" 2>/dev/null || echo "   (configuration set already exists)"

# ── 4. Create SNS topic ───────────────────────────────────────────────────────
echo "==> [4/6] Creating SNS topic '$SNS_TOPIC_NAME'..."
TOPIC_ARN=$(aws sns create-topic \
    --name "$SNS_TOPIC_NAME" \
    --region "$REGION" \
    --output text \
    --query 'TopicArn')
echo "   Topic ARN: $TOPIC_ARN"

# ── 5. Attach SNS event destination to configuration set ─────────────────────
echo "==> [5/6] Attaching SNS event destination to configuration set..."
aws ses create-configuration-set-event-destination \
    --configuration-set-name "$CONFIG_SET" \
    --event-destination "{
        \"Name\": \"sns-all-events\",
        \"Enabled\": true,
        \"MatchingEventTypes\": [\"bounce\", \"complaint\", \"delivery\"],
        \"SNSDestination\": { \"TopicARN\": \"$TOPIC_ARN\" }
    }" \
    --region "$REGION" 2>/dev/null || echo "   (event destination already exists)"

# ── 6. Subscribe HTTPS endpoint to SNS topic ─────────────────────────────────
WEBHOOK_URL="https://$APP_DOMAIN/api/v1/webhooks/ses/"
echo "==> [6/7] Subscribing $WEBHOOK_URL to SNS topic..."
echo "   (SNS will POST a SubscriptionConfirmation to that URL — your app auto-confirms it)"
aws sns subscribe \
    --topic-arn "$TOPIC_ARN" \
    --protocol https \
    --notification-endpoint "$WEBHOOK_URL" \
    --region "$REGION"

echo "   Waiting 5 s for SNS to deliver the confirmation request..."
sleep 5

# Confirm by checking subscription status
aws sns list-subscriptions-by-topic \
    --topic-arn "$TOPIC_ARN" \
    --region "$REGION" \
    --output table

# ── 7. Update .env with SES config ───────────────────────────────────────────
APP_DIR="${APP_DIR:-/opt/web_mail}"
if [[ -f "$APP_DIR/.env" ]]; then
    sed -i "s|^AWS_SES_REGION=.*|AWS_SES_REGION=$REGION|" "$APP_DIR/.env"
    echo "   Updated AWS_SES_REGION in .env"
fi

# ── Production access template ────────────────────────────────────────────────
echo ""
echo "====================================================="
echo " AWS SES is configured — but you are still in SANDBOX."
echo ""
echo " In sandbox mode you can ONLY send to verified addresses."
echo " To send to anyone, open an AWS Support case:"
echo ""
echo "   Service        : SES (Simple Email Service)"
echo "   Category       : Sending limits"
echo "   Subject        : Request production sending access"
echo "   Message template (fill in your details):"
echo ""
cat << 'TEMPLATE'
  I am building a transactional email service at [YOUR_DOMAIN].

  Use case: We send password resets, account confirmations,
  and transactional notifications to our registered users.

  We handle bounces and complaints via SNS → our /api/v1/webhooks/ses/
  endpoint, which automatically suppresses hard bounces and spam
  complaints. We maintain a suppression list and honour one-click
  unsubscribes per RFC 8058.

  Expected volume: [X] emails/day.

  Please grant production sending access.
TEMPLATE
echo ""
echo "  AWS Support: https://console.aws.amazon.com/support/home#/case/create"
echo "====================================================="
echo ""
echo " SNS Topic ARN (save this): $TOPIC_ARN"
echo "====================================================="
