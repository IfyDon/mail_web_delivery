#!/usr/bin/env bash
# =============================================================================
# 06_stripe.sh — Register your live Stripe webhook endpoint
#
# What this script does:
#   1. Logs you into the Stripe CLI with your live secret key
#   2. Creates a webhook endpoint at https://YOUR_DOMAIN/api/v1/webhooks/stripe/
#      subscribed to the exact events your app handles
#   3. Prints the webhook signing secret (STRIPE_WEBHOOK_SECRET) to add to .env
#
# Prerequisites:
#   - stripe CLI installed (done by 01_server_setup.sh)
#   - HTTPS is live (run 04_ssl.sh first — Stripe requires HTTPS)
#   - You have your live Stripe secret key (sk_live_...)
#     from https://dashboard.stripe.com/apikeys
#
# Usage:
#   bash deploy/06_stripe.sh  yourdomain.com  sk_live_YOUR_KEY
# =============================================================================
set -euo pipefail

DOMAIN="${1:?Usage: $0 DOMAIN STRIPE_SECRET_KEY}"
STRIPE_SECRET_KEY="${2:?Usage: $0 DOMAIN STRIPE_SECRET_KEY}"
APP_DIR="${APP_DIR:-/opt/web_mail}"

WEBHOOK_URL="https://$DOMAIN/api/v1/webhooks/stripe/"

# ── Events your app handles (from api/v1/views/stripe_webhook.py) ─────────────
EVENTS=(
    "checkout.session.completed"
    "customer.subscription.updated"
    "customer.subscription.deleted"
    "invoice.paid"
    "invoice.payment_failed"
)
EVENTS_CSV=$(IFS=','; echo "${EVENTS[*]}")

echo "==> [1/3] Authenticating with Stripe CLI..."
stripe login --api-key "$STRIPE_SECRET_KEY"

echo ""
echo "==> [2/3] Creating webhook endpoint..."
echo "   URL   : $WEBHOOK_URL"
echo "   Events: $EVENTS_CSV"
echo ""

WEBHOOK_OUTPUT=$(stripe webhooks create \
    --url "$WEBHOOK_URL" \
    --events "$EVENTS_CSV" \
    --api-key "$STRIPE_SECRET_KEY" \
    --output json 2>&1)

WEBHOOK_SECRET=$(echo "$WEBHOOK_OUTPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('secret', data.get('signing_secret', '')))
" 2>/dev/null || echo "")

WEBHOOK_ID=$(echo "$WEBHOOK_OUTPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('id',''))
" 2>/dev/null || echo "")

if [[ -z "$WEBHOOK_SECRET" ]]; then
    echo "WARNING: Could not automatically extract signing secret."
    echo "Run:  stripe webhooks describe $WEBHOOK_ID --api-key $STRIPE_SECRET_KEY"
    echo "and copy the 'signing_secret' value to STRIPE_WEBHOOK_SECRET in .env"
else
    echo "==> [3/3] Updating .env with webhook secret..."
    if [[ -f "$APP_DIR/.env" ]]; then
        sed -i "s|^STRIPE_WEBHOOK_SECRET=.*|STRIPE_WEBHOOK_SECRET=$WEBHOOK_SECRET|" "$APP_DIR/.env"
        echo "   STRIPE_WEBHOOK_SECRET updated in .env"
    fi
fi

# ── Verify Stripe can reach the endpoint ─────────────────────────────────────
echo ""
echo "==> Testing Stripe can reach $WEBHOOK_URL ..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -H "Stripe-Signature: invalid" \
    -d '{}')

# A 400 means nginx reached Django and Django rejected the invalid signature —
# which is exactly what we want (proves the route is live).
if [[ "$HTTP_STATUS" == "400" || "$HTTP_STATUS" == "401" ]]; then
    echo "   ✓ Endpoint is reachable (returned $HTTP_STATUS — expected for invalid sig)"
else
    echo "   WARNING: Got HTTP $HTTP_STATUS — verify the endpoint is accessible"
fi

echo ""
echo "====================================================="
echo " Stripe webhook configured."
echo " Webhook ID: $WEBHOOK_ID"
echo " Endpoint  : $WEBHOOK_URL"
echo ""
if [[ -n "$WEBHOOK_SECRET" ]]; then
    echo " STRIPE_WEBHOOK_SECRET has been saved to .env"
    echo ""
    echo " ⚠ Restart the app to apply the new secret:"
    echo "   cd $APP_DIR && docker compose up -d --no-deps web"
fi
echo ""
echo " Subscribed events:"
for e in "${EVENTS[@]}"; do echo "   - $e"; done
echo ""
echo " Dashboard: https://dashboard.stripe.com/webhooks"
echo "====================================================="
