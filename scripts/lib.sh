#!/usr/bin/env bash
# Shared helpers. Source this file; do not run it.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

env_file() { echo "$ROOT/env/$1.env"; }

web_port() {
  local file; file="$(env_file "$1")"
  [ -f "$file" ] || { echo "unknown environment: $1" >&2; return 2; }
  grep -E '^WEB_PORT=' "$file" | head -1 | cut -d= -f2
}

# Inside the Jenkins container, "localhost" is the container itself.
# Set SMOKE_HOST=host.docker.internal there so tests reach the published ports.
base_url() { echo "http://${SMOKE_HOST:-localhost}:$(web_port "$1")"; }
