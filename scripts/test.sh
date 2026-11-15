#!/usr/bin/env bash
# Unit tests run inside the Docker build (the 'test' stage). A failing test fails the build.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
docker build --target test -t shop-api-test:latest "$ROOT/api"
echo "unit tests passed"
