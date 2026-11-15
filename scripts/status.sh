#!/usr/bin/env bash
# Show what version runs in each environment and whether it answers.
set -uo pipefail
. "$(dirname "$0")/lib.sh"
STATE_DIR="${STATE_DIR:-${HOME:-/tmp}/.shop-deploy}"

printf '%-9s %-12s %-10s %s\n' ENV VERSION HEALTH URL
for e in dev test staging prod; do
  url="$(base_url "$e")"
  version="-"; [ -f "$STATE_DIR/$e.current" ] && version="$(cat "$STATE_DIR/$e.current")"
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$url/api/health" || true)"
  [ "$code" = "200" ] && health="up" || health="down"
  printf '%-9s %-12s %-10s %s\n' "$e" "$version" "$health" "$url"
done
