#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://localhost:3000}"
BV="${BV:-2026-01}"

echo "== health (before) =="
curl -s "$BASE/v1/memory/health" | jq

echo ""
echo "== write (default sanctuary, should NOT store) =="
curl -s -X POST "$BASE/v1/memory/write" \
  -H "Content-Type: application/json" \
  -H "X-SK-Behavior-Version: $BV" \
  -d '{
    "org_id":"org_demo","space_id":"spc_demo","user_id":"usr_demo",
    "kind":"journal","facet_code":"W2",
    "tags":["healing"],"payload":{"content":"sanctuary test"}
  }' | jq

echo ""
echo "== health (should be unchanged) =="
curl -s "$BASE/v1/memory/health" | jq

echo ""
echo "== write (mode=save, should store) =="
curl -s -i -X POST "$BASE/v1/memory/write" \
  -H "Content-Type: application/json" \
  -H "X-SK-Behavior-Version: $BV" \
  -d '{
    "org_id":"org_demo","space_id":"spc_demo","user_id":"usr_demo",
    "kind":"journal","facet_code":"W2",
    "tags":["healing"],"mode":"save",
    "payload":{"content":"save test"}
  }' | sed -n '1,25p'

echo ""
echo "== health (should be +1) =="
curl -s "$BASE/v1/memory/health" | jq

echo ""
echo "== retrieve (should only include saved one) =="
curl -s -X POST "$BASE/v1/memory/retrieve" \
  -H "Content-Type: application/json" \
  -H "X-SK-Behavior-Version: $BV" \
  -d '{
    "org_id":"org_demo","space_id":"spc_demo","user_id":"usr_demo",
    "query":{"tags":["healing"]},"limit":10
  }' | jq

echo ""
echo "== SMOKE TEST COMPLETE =="
