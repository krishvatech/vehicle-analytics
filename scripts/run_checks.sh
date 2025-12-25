#!/usr/bin/env bash
set -euo pipefail

API_BASE=${API_BASE:-http://localhost:8000}
USER=${USER_NAME:-admin}
PASS=${USER_PASS:-admin}

echo "== Health =="
curl -s "${API_BASE}/health" | jq .

echo "== Login =="
TOKEN=$(curl -s -X POST -d "username=${USER}&password=${PASS}" "${API_BASE}/auth/login" | jq -r .access_token)
echo "Token acquired"

auth() { curl -s -H "Authorization: Bearer ${TOKEN}" "$@"; }

echo "== List events =="
auth "${API_BASE}/events/" | jq '.[0:3]'

echo "== Export CSV =="
auth -L "${API_BASE}/events/export" --output /tmp/events.csv
echo "Saved /tmp/events.csv"

echo "== Metrics =="
curl -s "${API_BASE}/metrics/prometheus" | head -n 20
