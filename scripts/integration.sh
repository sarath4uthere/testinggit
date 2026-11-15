#!/usr/bin/env bash
# Functional test through the real stack (web -> api -> database).
# It CREATES data, so run it on dev/test/staging, never on prod.
# usage: scripts/integration.sh http://localhost:8090
set -euo pipefail

BASE="${1:?usage: integration.sh <base-url>}"
BODY="$(mktemp)"
trap 'rm -f "$BODY"' EXIT

# send METHOD PATH [JSON]  -> prints HTTP status, body is left in $BODY
send() {
  if [ $# -ge 3 ]; then
    curl -s -o "$BODY" -w '%{http_code}' --max-time 10 -X "$1" \
      -H 'Content-Type: application/json' -d "$3" "$BASE$2"
  else
    curl -s -o "$BODY" -w '%{http_code}' --max-time 10 -X "$1" "$BASE$2"
  fi
}
number_after() { grep -o "\"$1\": *[0-9]*" "$BODY" | head -1 | tr -dc '0-9'; }
expect() { # description actual expected
  if [ "$2" = "$3" ]; then echo "ok    $1"; else echo "FAIL  $1 (expected $3, got $2)"; exit 1; fi
}

expect "create product"        "$(send POST /api/products '{"name":"Integration Widget","price":12.50,"stock":10}')" 201
PRODUCT_ID="$(number_after id)"
[ -n "$PRODUCT_ID" ] || { echo "FAIL  could not read product id"; exit 1; }

expect "order 2 units"         "$(send POST /api/orders "{\"product_id\":$PRODUCT_ID,\"quantity\":2}")" 201
expect "read product back"     "$(send GET "/api/products/$PRODUCT_ID")" 200
expect "stock dropped to 8"    "$(number_after stock)" 8
expect "oversell is refused"   "$(send POST /api/orders "{\"product_id\":$PRODUCT_ID,\"quantity\":999}")" 409
expect "unknown product 404"   "$(send POST /api/orders '{"product_id":999999,"quantity":1}')" 404
expect "bad payload is 400"    "$(send POST /api/orders '{"product_id":"x","quantity":1}')" 400
expect "orders list works"     "$(send GET /api/orders)" 200

echo "integration test: all checks passed"
