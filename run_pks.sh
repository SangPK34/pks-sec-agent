#!/usr/bin/env bash
# Launch PKS from this checkout.
set -euo pipefail
PKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="${PKS_VENV_PY:-$PKS_DIR/.venv/bin/python3}"
export PYTHONPATH="$PKS_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
# load pks/.env if present
[ -f "$PKS_DIR/.env" ] && set -a && . "$PKS_DIR/.env" && set +a
cd "$PKS_DIR"
exec "$VENV_PY" -c "import sys; from pks.cli import main; sys.exit(main())" "$@"
