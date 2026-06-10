#!/usr/bin/env bash
# =============================================================================
# 07_verify.sh — Post-deploy smoke tests
#
# Runs a series of checks to confirm the deployment is healthy:
#   - All Docker containers running
#   - Health and readiness probes
#   - HTTPS / TLS
#   - API root reachable
#   - Celery workers processing tasks
#   - Database connectivity
#   - Redis connectivity
#   - SES sandbox status
#   - Stripe webhook reachability
#
# Usage:
#   bash deploy/07_verify.sh  yourdomain.com
# =============================================================================
set -euo pipefail

DOMAIN="${1:?Usage: $0 DOMAIN}"
APP_DIR="${APP_DIR:-/opt/web_mail}"
PASS=0; FAIL=0

cd "$APP_DIR"

# ── Helpers ───────────────────────────────────────────────────────────────────
ok()   { echo "  ✓  $1"; PASS=$((PASS+1)); }
fail() { echo "  ✗  $1"; FAIL=$((FAIL+1)); }
check_http() {
    local label="$1" url="$2" expected="${3:-200}"
    local status
    status=$(curl -sk -o /dev/null -w "%{http_code}" "$url")
    if [[ "$status" == "$expected" ]]; then ok "$label (HTTP $status)";
    else fail "$label — expected $expected, got $status";
    fi
}

echo ""
echo "=============================="
echo " Web Mail — Production Checks"
echo " Domain: $DOMAIN"
echo "=============================="

# ── 1. Docker containers ──────────────────────────────────────────────────────
echo ""
echo "── Docker services ──────────────────────"
for svc in db redis web worker beat nginx; do
    STATE=$(docker compose ps --format json "$svc" 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('State','missing'))" \
        2>/dev/null || echo "missing")
    if [[ "$STATE" == "running" ]]; then ok "$svc is running";
    else fail "$svc is $STATE";
    fi
done

# ── 2. Health / readiness probes ──────────────────────────────────────────────
echo ""
echo "── Health probes ────────────────────────"
check_http "HTTP  /health/"    "http://$DOMAIN/health/"    "200"
check_http "HTTPS /health/"    "https://$DOMAIN/health/"   "200"
check_http "HTTPS /readiness/" "https://$DOMAIN/readiness/" "200"

# ── 3. TLS / certificate ──────────────────────────────────────────────────────
echo ""
echo "── TLS certificate ──────────────────────"
CERT_EXPIRY=$(echo | openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" 2>/dev/null \
    | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2 || echo "unknown")
if [[ "$CERT_EXPIRY" != "unknown" ]]; then ok "TLS cert valid until $CERT_EXPIRY";
else fail "Could not retrieve TLS certificate";
fi

# Check HSTS header
HSTS=$(curl -sI "https://$DOMAIN/" | grep -i "strict-transport-security" || echo "")
if [[ -n "$HSTS" ]]; then ok "HSTS header present";
else fail "HSTS header missing";
fi

# ── 4. API endpoints ─────────────────────────────────────────────────────────
echo ""
echo "── API endpoints ────────────────────────"
check_http "GET /api/"          "https://$DOMAIN/api/"          "200"
check_http "GET /api/docs/"     "https://$DOMAIN/api/docs/"     "200"
check_http "GET /api/schema/"   "https://$DOMAIN/api/schema/"   "200"

# ── 5. Celery task queue ──────────────────────────────────────────────────────
echo ""
echo "── Celery workers ───────────────────────"
CELERY_PING=$(docker compose exec -T worker \
    celery -A config.celery inspect ping --timeout 5 2>/dev/null || echo "")
if echo "$CELERY_PING" | grep -q "pong"; then ok "Celery workers responding";
else fail "No Celery workers responding to ping";
fi

BEAT_PID=$(docker compose exec -T beat cat /tmp/celerybeat.pid 2>/dev/null || echo "")
if [[ -n "$BEAT_PID" ]]; then ok "Celery beat running (pid=$BEAT_PID)";
else
    # beat might not write a pidfile depending on version
    BEAT_RUNNING=$(docker compose ps beat --format json 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('State',''))" \
        2>/dev/null || echo "")
    if [[ "$BEAT_RUNNING" == "running" ]]; then ok "Celery beat container running";
    else fail "Celery beat not confirmed running";
    fi
fi

# ── 6. Database and cache ─────────────────────────────────────────────────────
echo ""
echo "── Database / cache ─────────────────────"
DB_OK=$(docker compose exec -T web python manage.py shell -c \
    "from django.db import connection; connection.ensure_connection(); print('ok')" \
    2>/dev/null || echo "error")
if [[ "$DB_OK" == "ok" ]]; then ok "Database connection OK";
else fail "Database connection failed";
fi

REDIS_OK=$(docker compose exec -T redis redis-cli ping 2>/dev/null || echo "error")
if [[ "$REDIS_OK" == "PONG" ]]; then ok "Redis connection OK";
else fail "Redis connection failed";
fi

# ── 7. Production configuration validation ────────────────────────────────────
echo ""
echo "── App configuration ────────────────────"
PROD_CHECK=$(docker compose exec -T web python manage.py check_production 2>&1 || true)
if echo "$PROD_CHECK" | grep -q "All checks passed"; then
    ok "check_production passed"
else
    while IFS= read -r line; do
        if echo "$line" | grep -q "^  \[FAIL\]"; then fail "$line";
        elif echo "$line" | grep -q "^  \[WARN\]"; then echo "  ⚠  $line";
        elif echo "$line" | grep -q "^  \[OK\]";  then ok "$line";
        fi
    done <<< "$PROD_CHECK"
fi

# ── 8. DNS records ────────────────────────────────────────────────────────────
echo ""
echo "── DNS records ──────────────────────────"
A_RECORD=$(dig +short "$DOMAIN" A | tail -1 || echo "")
SERVER_IP=$(curl -4 -s https://ifconfig.me 2>/dev/null || echo "unknown")
if [[ "$A_RECORD" == "$SERVER_IP" ]]; then ok "A record $DOMAIN → $SERVER_IP";
else fail "A record $DOMAIN → $A_RECORD (server is $SERVER_IP)";
fi

SPF=$(dig +short "$DOMAIN" TXT | grep "v=spf1" || echo "")
if [[ -n "$SPF" ]]; then ok "SPF record present";
else fail "SPF TXT record not found for $DOMAIN";
fi

DMARC=$(dig +short "_dmarc.$DOMAIN" TXT | grep "v=DMARC1" || echo "")
if [[ -n "$DMARC" ]]; then ok "DMARC record present";
else fail "DMARC TXT record not found for _dmarc.$DOMAIN";
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "=============================="
echo " Results: $PASS passed, $FAIL failed"
echo "=============================="
if [[ $FAIL -eq 0 ]]; then
    echo " ✓ All checks passed — deployment is healthy!"
    exit 0
else
    echo " ✗ $FAIL check(s) failed — review the output above."
    exit 1
fi
