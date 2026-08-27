#!/usr/bin/env bash
# =============================================================================
# 08_backup.sh — PostgreSQL backup: take a dump now, and install a daily
# cron job (03:00 UTC) to repeat it automatically.
#
# Usage (as root, from APP_DIR):
#   sudo bash deploy/08_backup.sh              # backup now + install cron
#   sudo bash deploy/08_backup.sh --no-cron    # backup now only
#
# Backups are gzipped pg_dumps written to $BACKUP_DIR (default: APP_DIR/backups),
# named web_mail_YYYYmmdd_HHMMSS.sql.gz, pruned after $BACKUP_RETENTION_DAYS days.
# If BACKUP_S3_BUCKET is set in .env, each dump is additionally copied to S3
# using the AWS CLI installed by 01_server_setup.sh.
# =============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/web_mail}"
cd "$APP_DIR"

if [[ -f .env ]]; then
    set -a; source .env; set +a
fi

BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
DB_USER="${DB_USER:-web_mail_user}"
DB_NAME="${DB_NAME:-web_mail_db}"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/web_mail_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "==> Dumping database '$DB_NAME' to $BACKUP_FILE..."
docker compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

if [[ ! -s "$BACKUP_FILE" ]]; then
    echo "ERROR: backup file is empty — pg_dump failed." >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi
echo "   Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"

if [[ -n "${BACKUP_S3_BUCKET:-}" ]]; then
    echo "==> Uploading to s3://$BACKUP_S3_BUCKET/..."
    aws s3 cp "$BACKUP_FILE" "s3://$BACKUP_S3_BUCKET/$(basename "$BACKUP_FILE")" --only-show-errors
fi

echo "==> Pruning backups older than $BACKUP_RETENTION_DAYS days..."
find "$BACKUP_DIR" -name 'web_mail_*.sql.gz' -mtime "+${BACKUP_RETENTION_DAYS}" -print -delete

if [[ "${1:-}" != "--no-cron" ]]; then
    CRON_FILE="/etc/cron.d/web-mail-backup"
    if [[ ! -f "$CRON_FILE" ]]; then
        echo "==> Installing daily backup cron job (03:00 UTC)..."
        cat > "$CRON_FILE" << CRONEOF
# Daily WebMail database backup at 03:00 UTC
0 3 * * * root APP_DIR=$APP_DIR bash $APP_DIR/deploy/08_backup.sh --no-cron >> $BACKUP_DIR/backup.log 2>&1
CRONEOF
        chmod 644 "$CRON_FILE"
    else
        echo "==> Cron job already installed at $CRON_FILE — skipping."
    fi
fi

echo ""
echo "====================================================="
echo " Backup complete : $BACKUP_FILE"
echo " Retention       : $BACKUP_RETENTION_DAYS days"
echo " S3 bucket       : ${BACKUP_S3_BUCKET:-none configured}"
echo " Daily cron      : /etc/cron.d/web-mail-backup"
echo ""
echo " Test a restore with:"
echo "   sudo bash deploy/09_restore_backup.sh $BACKUP_FILE"
echo "====================================================="
