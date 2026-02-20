#!/bin/bash
# Deploy ForgeBaselines to EC2
# Usage: bash scripts/deploy.sh
set -e

EC2_USER="ubuntu"
EC2_HOST="18.118.86.95"
EC2_KEY="$HOME/.ssh/forgebaselines.pem"
APP_DIR="/home/ubuntu/forgebaselines"

echo "=== Deploying ForgeBaselines to $EC2_HOST ==="

# Copy .env to server (never commit .env to git)
echo "Copying .env..."
scp -i "$EC2_KEY" -o StrictHostKeyChecking=no .env "$EC2_USER@$EC2_HOST:$APP_DIR/.env"

# Pull latest code and restart services
echo "Pulling latest code and restarting services..."
ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" << 'ENDSSH'
  set -e
  cd /home/ubuntu/forgebaselines
  git pull origin main
  docker compose -f docker-compose.prod.yml up --build -d
  docker compose -f docker-compose.prod.yml ps
ENDSSH

echo ""
echo "=== Deploy complete ==="
echo "App:  http://18.118.86.95"
echo "API:  http://18.118.86.95/api/health"
echo ""
echo "MLflow (SSH tunnel):"
echo "  ssh -i ~/.ssh/forgebaselines.pem -L 5001:localhost:5000 ubuntu@18.118.86.95"
echo "  then open http://localhost:5001"
