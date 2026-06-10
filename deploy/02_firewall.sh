#!/usr/bin/env bash
# =============================================================================
# 02_firewall.sh — Configure UFW firewall for production
#
# Allows:  SSH (22), HTTP (80), HTTPS (443)
# Blocks:  Direct Gunicorn (8000), Celery Flower (5555), PostgreSQL (5432),
#          Redis (6379) from public internet.
#
# Run as root: sudo bash 02_firewall.sh
# =============================================================================
set -euo pipefail

SSH_PORT="${SSH_PORT:-22}"

echo "==> Installing UFW..."
apt-get install -y -qq ufw

echo "==> Configuring default policies..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw default deny routed

echo "==> Allowing SSH on port $SSH_PORT..."
ufw allow "$SSH_PORT/tcp" comment 'SSH'

echo "==> Allowing HTTP and HTTPS (nginx)..."
ufw allow 80/tcp  comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

echo "==> Blocking direct access to internal services from public internet..."
# These ports are bound to 127.0.0.1 or the Docker internal network,
# but we block them at the host firewall as a defence-in-depth measure.
ufw deny 8000/tcp comment 'Block direct Gunicorn — use nginx on 443'
ufw deny 5555/tcp comment 'Block direct Flower — tunnel via SSH if needed'
ufw deny 5432/tcp comment 'Block direct PostgreSQL'
ufw deny 6379/tcp comment 'Block direct Redis'

echo "==> Enabling UFW..."
ufw --force enable
ufw status verbose

echo ""
echo "====================================================="
echo " Firewall configured."
echo ""
echo " To access Flower securely, use an SSH tunnel:"
echo "   ssh -L 5555:127.0.0.1:5555 user@YOUR_SERVER_IP"
echo " Then open http://localhost:5555 in your browser."
echo "====================================================="
