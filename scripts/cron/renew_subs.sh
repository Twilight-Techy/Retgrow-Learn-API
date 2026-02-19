#!/bin/bash

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
CRON_SECRET="${CRON_SECRET:-secret}"

echo "Triggering renewal at $API_URL/cron/renew-subscriptions..."

curl -X POST "$API_URL/cron/renew-subscriptions" \
  -H "X-Cron-Secret: $CRON_SECRET" \
  -H "Content-Type: application/json"

echo "\nDone."
