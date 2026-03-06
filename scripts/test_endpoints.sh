#!/bin/bash
set -e

ENV_FILE="$(dirname "$0")/../.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env not found at $ENV_FILE"
  exit 1
fi

# Parse only simple single-line KEY=VALUE entries (skip multi-line blocks)
get_env() {
  grep -m1 "^$1=" "$ENV_FILE" | cut -d'=' -f2- | tr -d ' '
}

API_KEY=$(get_env "NEXT_PUBLIC_FIREBASE_API_KEY")
EMAIL=$(get_env "TEST_USER_EMAIL")
PASSWORD=$(get_env "TEST_USER_PASSWORD")
BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "==> Signing in as $EMAIL..."
RESPONSE=$(curl -s -X POST \
  "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"returnSecureToken\":true}")

TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('idToken',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "Failed to get token. Response:"
  echo "$RESPONSE"
  exit 1
fi

echo "Token acquired."
echo ""

echo "==> GET $BASE_URL/experiments/all"
curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/experiments/all" | python3 -m json.tool
echo ""

# If an experiment_id is passed as argument, test status + results too
if [ -n "$1" ]; then
  EXP_ID="$1"
  echo "==> GET $BASE_URL/experiments/$EXP_ID/status"
  curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/experiments/$EXP_ID/status" | python3 -m json.tool
  echo ""

  echo "==> GET $BASE_URL/experiments/$EXP_ID/results"
  curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/experiments/$EXP_ID/results" | python3 -m json.tool
  echo ""
fi
