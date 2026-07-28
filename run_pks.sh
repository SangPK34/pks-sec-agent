#!/usr/bin/env bash
# Launch the pks (CTF-optimized CAI fork) using the existing cai venv.
# Runs the code in THIS folder (pks/src) without touching the original cai install.
set -euo pipefail
PKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="${CAI_VENV_PY:-/home/sangpk05/cai/venv_linux/bin/python3}"
export PYTHONPATH="$PKS_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
export PKS_LICENSE_OFF="${PKS_LICENSE_OFF:-1}"
export CAI_COST_DISPLAYED="true"
export PKS_COST_DISPLAYED="true"
# load pks/.env if present
[ -f "$PKS_DIR/.env" ] && set -a && . "$PKS_DIR/.env" && set +a
cd "$PKS_DIR"
exec "$VENV_PY" -c "import sys; from pks.cli import main; sys.exit(main())" "$@"
