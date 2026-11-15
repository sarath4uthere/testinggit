#!/usr/bin/env bash
# Vulnerability scan with Trivy (runs as a container, needs the Docker socket).
# SCAN_STRICT=true makes HIGH/CRITICAL findings fail the build; default only reports them.
set -euo pipefail

TAG="${TAG:?TAG is required}"
REGISTRY="${REGISTRY:-shop}"
EXIT_CODE=0
[ "${SCAN_STRICT:-false}" = "true" ] && EXIT_CODE=1

for image in "$REGISTRY/shop-api:$TAG" "$REGISTRY/shop-web:$TAG"; do
  echo "=== scanning $image ==="
  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v trivy-cache:/root/.cache \
    aquasec/trivy:0.57.1 image \
      --severity HIGH,CRITICAL --exit-code "$EXIT_CODE" --no-progress "$image"
done
