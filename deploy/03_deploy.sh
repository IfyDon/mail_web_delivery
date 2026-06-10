#!/usr/bin/env bash
# =============================================================================
# 03_deploy.sh — First-time deployment (and subsequent redeploys)
#
# Prerequisites:
#   - 01_server_setup.sh has been run
#   - Project code is in APP_DIR
#   - .env file is present in APP_DIR (copy from deploy/.env.production)
#
# Usage (from APP_DIR):
#   bash deploy/03_deploy.sh
#
# On subsequent deploys (code updates), re-run the same script.
# =============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/web_mail}"
cd "$APP_DIR"

# ── Validate .env exists and has critical vars set ─────────────────────────
if [[ ! -f .env ]]; then
    echo "ERROR: .env not found in $APP_DIR"
    echo "Copy deploy/.env.production to .env and fill in all values."
    exit 1
fi

# Source .env to validate a few key variables
set -a; source .env; set +a

: "${SECRET_KEY:?ERROR: SECRET_KEY is not set in .env}"
: "${DB_PASSWORD:?ERROR: DB_PASSWORD is not set in .env}"
: "${ALLOWED_HOSTS:?ERROR: ALLOWED_HOSTS is not set in .env}"

if [[ "$SECRET_KEY" == *"change-me"* ]]; then
    echo "ERROR: SECRET_KEY still has the placeholder value. Generate one:"
    echo "  python3 -c \"import secrets; print(secrets.token_hex(50))\""
    exit 1
fi

echo "==> [1/6] Pulling latest Docker images and rebuilding..."
docker compose pull --quiet
docker compose build --quiet

echo "==> [2/6] Stopping old containers (if any)..."
docker compose down --remove-orphans --timeout 30 || true

echo "==> [3/6] Starting database and Redis (needed for migrations)..."
docker compose up -d db redis
echo "   Waiting for database to be healthy..."
until docker compose exec -T db pg_isready -U web_mail_user -q; do
    sleep 2
done

echo "==> [4/6] Running database migrations..."
docker compose run --rm web python manage.py migrate --noinput

echo "==> [5/6] Creating superuser (first deploy only — skip if exists)..."
docker compose run --rm web python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        username='admin',
        email='${SUPERUSER_EMAIL:-admin@example.com}',
        password='${SUPERUSER_PASSWORD:-CHANGE_ME_NOW}'
    )
    print('Superuser created.')
else:
    print('Superuser already exists — skipped.')
" 2>/dev/null || true

echo "==> [6/6] Starting all services..."
docker compose up -d
docker compose ps

echo ""
echo "====================================================="
echo " Deployment complete."
echo ""
echo " Services:"
echo "   Web app  : http://$(hostname -I | awk '{print $1}'):80"
echo "   Health   : curl http://localhost/health/"
echo "   Readiness: curl http://localhost/readiness/"
echo "   API docs : https://YOUR_DOMAIN/api/docs/"
echo "   Admin    : https://YOUR_DOMAIN/admin/"
echo ""
echo " Next steps:"
echo "   1. Run  sudo bash deploy/02_firewall.sh  (if not done)"
echo "   2. Point your domain DNS A record to this server IP"
echo "   3. Run  sudo bash deploy/04_ssl.sh YOUR_DOMAIN EMAIL"
echo "   4. Run       bash deploy/05_aws_ses.sh"
echo "   5. Run       bash deploy/06_stripe.sh"
echo "   6. Run       bash deploy/07_verify.sh"
echo "====================================================="
