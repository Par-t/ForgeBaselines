#!/bin/bash
# Run once on a fresh Ubuntu 24.04 EC2 instance as root (sudo bash ec2-setup.sh)
set -e

echo "=== ForgeBaselines EC2 Bootstrap ==="

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
apt-get install -y ca-certificates curl gnupg git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow ubuntu user to run docker without sudo
usermod -aG docker ubuntu

# Configure 2GB swap (essential for Docker builds on small instances)
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "Swap configured: $(swapon --show)"
fi

# Clone the repo
APP_DIR="/home/ubuntu/forgebaselines"
if [ ! -d "$APP_DIR" ]; then
  git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git "$APP_DIR"
  chown -R ubuntu:ubuntu "$APP_DIR"
fi

mkdir -p "$APP_DIR/data"
chown -R ubuntu:ubuntu "$APP_DIR/data"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Log out and back in (for docker group to take effect)"
echo "  2. cd $APP_DIR"
echo "  3. Copy your .env file (scp from local machine)"
echo "  4. docker compose -f docker-compose.prod.yml up --build -d"
