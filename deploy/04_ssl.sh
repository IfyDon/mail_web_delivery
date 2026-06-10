#!/usr/bin/env bash
# =============================================================================
# 04_ssl.sh — Get a Let's Encrypt SSL certificate and activate HTTPS in nginx
#
# Prerequisites:
#   - Domain DNS A record already points to this server's public IP
#   - nginx container is running (HTTP must be reachable on port 80)
#   - deploy/03_deploy.sh has been run
#
# Usage:
#   sudo bash deploy/04_ssl.sh  yourdomain.com  admin@yourdomain.com
# =============================================================================
set -euo pipefail

DOMAIN="${1:?Usage: $0 DOMAIN EMAIL}"
EMAIL="${2:?Usage: $0 DOMAIN EMAIL}"
APP_DIR="${APP_DIR:-/opt/web_mail}"

cd "$APP_DIR"

# ── Step 1: Install certbot ──────────────────────────────────────────────────
echo "==> [1/5] Installing certbot..."
apt-get install -y -qq certbot

# ── Step 2: Verify DNS resolves to this server ────────────────────────────────
echo "==> [2/5] Checking DNS for $DOMAIN..."
SERVER_IP=$(curl -4 -s https://ifconfig.me)
DNS_IP=$(dig +short "$DOMAIN" A | tail -1)

if [[ "$DNS_IP" != "$SERVER_IP" ]]; then
    echo "WARNING: $DOMAIN resolves to $DNS_IP but this server is $SERVER_IP"
    echo "Certbot will fail if DNS is not pointing here. Continue? [y/N]"
    read -r confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
fi

# ── Step 3: Obtain certificate via webroot ─────────────────────────────────────
# nginx serves /.well-known/acme-challenge/ from /var/www/certbot (already configured)
echo "==> [3/5] Obtaining certificate for $DOMAIN..."
certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    --domain "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive \
    --keep-until-expiring

# ── Step 4: Install nginx.ssl.conf with HTTPS enabled ─────────────────────────
echo "==> [4/5] Activating HTTPS in nginx.conf..."
cp deploy/nginx.ssl.conf nginx/nginx.conf
# Replace the YOUR_DOMAIN placeholder with the actual domain (3 occurrences)
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" nginx/nginx.conf

# Reload nginx inside the container
docker compose exec nginx nginx -s reload
echo "   nginx reloaded with HTTPS configuration."

# ── Step 5: Update .env with https:// URLs ────────────────────────────────────
echo "==> [5/5] Updating BASE_URL and TRACKING_BASE_URL in .env..."
sed -i "s|^BASE_URL=.*|BASE_URL=https://$DOMAIN|" .env
sed -i "s|^TRACKING_BASE_URL=.*|TRACKING_BASE_URL=https://$DOMAIN|" .env
sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN|" .env
sed -i "s|^CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=https://$DOMAIN|" .env
sed -i "s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=https://$DOMAIN|" .env
sed -i "s|^FRONTEND_BASE_URL=.*|FRONTEND_BASE_URL=https://$DOMAIN|" .env

# Restart web service so it picks up the new env vars
docker compose up -d --no-deps web worker beat

# ── Step 6: Set up automatic renewal ──────────────────────────────────────────
echo "==> Setting up automatic certificate renewal..."
cat > /etc/cron.d/certbot-renewal << CRONEOF
# Renew Let's Encrypt certs at 02:30 UTC on 1st and 15th of each month
30 2 1,15 * * root certbot renew --quiet \
    --deploy-hook "docker compose -f $APP_DIR/docker-compose.yml exec -T nginx nginx -s reload"
CRONEOF
chmod 644 /etc/cron.d/certbot-renewal

echo ""
echo "====================================================="
echo " HTTPS is now active for https://$DOMAIN"
echo ""
echo " Certificate auto-renews via cron (1st + 15th monthly)"
echo " Verify: curl -I https://$DOMAIN/health/"
echo ""
echo " Next: run  bash deploy/05_aws_ses.sh $DOMAIN"
echo "====================================================="
