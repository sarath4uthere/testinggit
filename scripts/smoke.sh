#!/usr/bin/env bash
# Quick "is it alive" checks. Safe to run against production (read-only).
# usage: scripts/smoke.sh http://localhost:8090
set -euo pipefail

BASE="${1:?usage: smoke.sh <base-url>}"
BODY="$(mktemp)"
trap 'rm -f "$BODY"' EXIT
failures=0
attempts="${SMOKE_ATTEMPTS:-8}"   # retries for the first check while the app finishes starting

# fetch URL, retrying a few times; prints the HTTP status
fetch() {
  local url="$1" code="000" attempt
  for attempt in $(seq 1 "$attempts"); do
    code="$(curl -s -o "$BODY" -w '%{http_code}' --max-time 5 "$url" || true)"
    [ "$code" = "200" ] && break
    sleep 2
  done
  echo "$code"
}

check() { # name url [text-the-body-must-contain]
  local name="$1" url="$2" needle="${3:-}" code
  code="$(fetch "$url")"
  if [ "$code" != "200" ]; then
    echo "FAIL  $name  (HTTP $code)  $url"; failures=$((failures + 1)); attempts=1; return
  fi
  if [ -n "$needle" ] && ! grep -q "$needle" "$BODY"; then
    echo "FAIL  $name  (missing '$needle')"; failures=$((failures + 1)); return
  fi
  echo "ok    $name"
}

check "web healthz"   "$BASE/healthz"
check "web index"     "$BASE/" "Shop Lab"
check "api health"    "$BASE/api/health" "ok"
check "api ready"     "$BASE/api/ready" "ready"
check "api version"   "$BASE/api/version" "version"
check "api products"  "$BASE/api/products" "\["

if [ "$failures" -gt 0 ]; then
  echo "smoke test: $failures check(s) failed"; exit 1
fi
echo "smoke test: all checks passed"
