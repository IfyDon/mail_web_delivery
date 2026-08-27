#!/usr/bin/env bash
# =============================================================================
# 09_restore_backup.sh — Restore a database backup created by 08_backup.sh
#
# WARNING: DESTRUCTIVE. Drops and recreates the database, replacing all
# current data with the contents of the given backup file.
#
# Usage (as root, from APP_DIR):
#   sudo bash deploy/09_restore_backup.sh /path/to/web_mail_20260101_030000.sql.gz
# =============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/web_mail}"
cd "$APP_DIR"

if [[ -f .env ]]; then
    set -a; source .env; set +a
fi

BACKUP_FILE="${1:?Usage: $0 /path/to/backup.sql.gz}"
DB_USER="${DB_USER:-web_mail_user}"
DB_NAME="${DB_NAME:-web_mail_db}"

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "ERROR: backup file not found: $BACKUP_FILE" >&2
    exit 1
fi

echo "WARNING: This will PERMANENTLY REPLACE all data in the '$DB_NAME' database"
echo "on this server with the contents of:"
echo "  $BACKUP_FILE"
echo ""
read -r -p "Type the database name to confirm ($DB_NAME): " CONFIRM
if [[ "$CONFIRM" != "$DB_NAME" ]]; then
    echo "Aborted — confirmation did not match."
    exit 1
fi

echo "==> Stopping web, worker, and beat (database stays up)..."
docker compose stop web worker beat

echo "==> Dropping and recreating '$DB_NAME'..."
docker compose exec -T db psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker compose exec -T db psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo "==> Restoring from $BACKUP_FILE..."
gunzip -c "$BACKUP_FILE" | docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME"

echo "==> Restarting all services..."
docker compose up -d

echo ""
echo "====================================================="
echo " Restore complete from: $BACKUP_FILE"
echo " Run  bash deploy/07_verify.sh YOUR_DOMAIN  to confirm health."
echo "====================================================="
