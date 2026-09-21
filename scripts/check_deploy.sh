#!/usr/bin/env bash
# Usage: ./scripts/check_deploy.sh https://your-backend.onrender.com/health
if [ -z "$1" ]; then
  echo "Usage: $0 <HEALTH_URL>"
  exit 2
fi
HEALTH_URL=$1
for i in 1 2 3 4 5; do
  status=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL || true)
  echo "Attempt $i: HTTP $status"
  if [ "$status" = "200" ]; then
    echo "Healthy"
    exit 0
  fi
  sleep 5
done
echo "Health check failed"
exit 1
