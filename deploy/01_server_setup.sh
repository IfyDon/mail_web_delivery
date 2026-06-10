#!/usr/bin/env bash
# =============================================================================
# 01_server_setup.sh — Initial Ubuntu 22.04 LTS server setup
#
# Run once as root on a fresh VPS (DigitalOcean, Linode, AWS EC2, etc.)
# Usage:  sudo bash 01_server_setup.sh
# =============================================================================
set -euo pipefail

APP_USER="webmail"
APP_DIR="/opt/web_mail"

echo "==> [1/6] Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    curl \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    unzip \
    jq \
    python3-pip \
    awscli        # needed for deploy/05_aws_ses.sh

echo "==> [2/6] Installing Docker Engine..."
# Official Docker install script (https://get.docker.com)
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

echo "==> [3/6] Installing Docker Compose plugin..."
apt-get install -y -qq docker-compose-plugin
docker compose version   # smoke test

echo "==> [4/6] Installing Stripe CLI..."
curl -fsSL https://packages.stripe.dev/api/security/keypair/stripe-cli-gpg/public \
    | gpg --dearmor | tee /usr/share/keyrings/stripe.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/stripe.gpg] \
    https://packages.stripe.dev/stripe-cli-debian-local stable main" \
    > /etc/apt/sources.list.d/stripe.list
apt-get update -qq && apt-get install -y -qq stripe

echo "==> [5/6] Creating app user and directory..."
id "$APP_USER" &>/dev/null || useradd -m -s /bin/bash "$APP_USER"
usermod -aG docker "$APP_USER"
mkdir -p "$APP_DIR"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# Create certbot webroot directory (used by nginx for ACME challenge)
mkdir -p /var/www/certbot
chown -R www-data:www-data /var/www/certbot

echo "==> [6/6] Enabling automatic security updates..."
apt-get install -y -qq unattended-upgrades
dpkg-reconfigure -f noninteractive unattended-upgrades

echo ""
echo "====================================================="
echo " Server setup complete."
echo " App directory : $APP_DIR"
echo " App user      : $APP_USER"
echo ""
echo " Next steps:"
echo "   1. Copy your project to $APP_DIR (git clone or scp)"
echo "   2. Run  sudo bash 02_firewall.sh"
echo "   3. Run  sudo bash 03_deploy.sh  (as $APP_USER)"
echo "====================================================="
