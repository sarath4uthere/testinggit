#!/usr/bin/env bash
# Build both images once. The same images are promoted through every environment.
# usage: REGISTRY=shop scripts/build.sh <tag>
set -euo pipefail
. "$(dirname "$0")/lib.sh"

export TAG="${1:?usage: build.sh <tag>}"
export REGISTRY="${REGISTRY:-shop}"

docker compose --env-file "$(env_file dev)" -f "$ROOT/docker-compose.yml" build
echo "built: $REGISTRY/shop-api:$TAG and $REGISTRY/shop-web:$TAG"
