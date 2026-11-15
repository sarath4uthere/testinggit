#!/usr/bin/env bash
# Deploy one image tag to one environment, verify it, and roll back on failure.
#   usage: scripts/deploy.sh <dev|test|staging|prod> <tag>
#   env  : REGISTRY (default "shop"), SMOKE_HOST (default localhost), STATE_DIR
set -euo pipefail
. "$(dirname "$0")/lib.sh"

ENVIRONMENT="${1:?usage: deploy.sh <dev|test|staging|prod> <tag>}"
NEW_TAG="${2:?usage: deploy.sh <dev|test|staging|prod> <tag>}"
export REGISTRY="${REGISTRY:-shop}"

ENV_FILE="$(env_file "$ENVIRONMENT")"
[ -f "$ENV_FILE" ] || { echo "unknown environment: $ENVIRONMENT" >&2; exit 2; }

PROJECT="shop-$ENVIRONMENT"
STATE_DIR="${STATE_DIR:-${HOME:-/tmp}/.shop-deploy}"
mkdir -p "$STATE_DIR"
CURRENT_FILE="$STATE_DIR/$ENVIRONMENT.current"
PREVIOUS_FILE="$STATE_DIR/$ENVIRONMENT.previous"

CURRENT=""; [ -f "$CURRENT_FILE" ] && CURRENT="$(cat "$CURRENT_FILE")"
BASE_URL="$(base_url "$ENVIRONMENT")"

apply() { # tag
  TAG="$1" docker compose -p "$PROJECT" --env-file "$ENV_FILE" -f "$ROOT/docker-compose.yml" \
    up -d --wait --wait-timeout 180 --remove-orphans
  bash "$ROOT/scripts/smoke.sh" "$BASE_URL"
}

echo "==> deploying $NEW_TAG to $ENVIRONMENT (currently: ${CURRENT:-nothing})"
if apply "$NEW_TAG"; then
  [ -n "$CURRENT" ] && [ "$CURRENT" != "$NEW_TAG" ] && echo "$CURRENT" > "$PREVIOUS_FILE"
  echo "$NEW_TAG" > "$CURRENT_FILE"
  echo "==> $ENVIRONMENT is running $NEW_TAG at $BASE_URL"
  exit 0
fi

echo "!! deployment of $NEW_TAG failed"
if [ -n "$CURRENT" ] && [ "$CURRENT" != "$NEW_TAG" ]; then
  echo "==> rolling back to $CURRENT"
  if apply "$CURRENT"; then
    echo "==> rollback succeeded, $ENVIRONMENT is running $CURRENT again"
  else
    echo "!! rollback ALSO failed: manual intervention needed"
  fi
else
  echo "!! no previous version to roll back to"
fi
exit 1
