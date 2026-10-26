#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v uv >/dev/null 2>&1; then
  echo 'Please install uv first, then run sh setup.sh.' >&2
  exit 1
fi
exec uv run --no-project --python 3.12 scripts/dev.py start
