#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://localhost:3000}"
BV="${BV:-2026-01}"

echo "== practices health =="
curl -s "$BASE/v1/practices/health" | jq

echo ""
echo "== practices generate (fire element) =="
curl -s -X POST "$BASE/v1/practices/generate" \
  -H "Content-Type: application/json" \
  -H "X-SK-Behavior-Version: $BV" \
  -d '{
    "org_id":"org_demo",
    "user_id":"usr_demo",
    "facet_code":"F1",
    "duration_available_min": 12,
    "difficulty":"easy",
    "contraindications":[]
  }' | jq

echo ""
echo "== practices generate (water element) =="
curl -s -X POST "$BASE/v1/practices/generate" \
  -H "Content-Type: application/json" \
  -H "X-SK-Behavior-Version: $BV" \
  -d '{
    "org_id":"org_demo",
    "user_id":"usr_demo",
    "facet_code":"W2",
    "duration_available_min": 15,
    "difficulty":"moderate",
    "contraindications":[]
  }' | jq

echo ""
echo "== SMOKE TEST COMPLETE =="
