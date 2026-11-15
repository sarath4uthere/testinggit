#!/usr/bin/env bash
# Manual rollback: redeploy the version that ran before the current one.
#   usage: scripts/rollback.sh <env>
set -euo pipefail
. "$(dirname "$0")/lib.sh"

ENVIRONMENT="${1:?usage: rollback.sh <env>}"
STATE_DIR="${STATE_DIR:-${HOME:-/tmp}/.shop-deploy}"
PREVIOUS_FILE="$STATE_DIR/$ENVIRONMENT.previous"

[ -f "$PREVIOUS_FILE" ] || { echo "no previous version recorded for $ENVIRONMENT"; exit 1; }
PREVIOUS="$(cat "$PREVIOUS_FILE")"
echo "rolling $ENVIRONMENT back to $PREVIOUS"
exec bash "$ROOT/scripts/deploy.sh" "$ENVIRONMENT" "$PREVIOUS"
