#!/usr/bin/env bash
set -euo pipefail
. "$(dirname "$0")/lib.sh"
base_url "${1:?usage: url.sh <env>}"
