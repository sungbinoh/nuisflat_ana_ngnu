#!/bin/bash
# Create the analysis venv (run once, on the UI).
# Put it on the shared /ngnu filesystem so the worker nodes (same OS, AlmaLinux9) can use it.
#   ./setup_venv.sh [VENV_PATH]        default: <repo>/.venv
set -euo pipefail
REPO=$(cd "$(dirname "$0")" && pwd)
VENV=$(realpath -m "${1:-${VENV:-$REPO/.venv}}")
PY=${PYTHON:-/usr/bin/python3}     # system python, present on UI and WNs

echo "python: $($PY --version)  ->  venv: $VENV"
$PY -m venv "$VENV"
source "$VENV/bin/activate"
pip install --upgrade pip
pip install -r "$REPO/requirements.txt"
python -c "import uproot, awkward, pyarrow, pandas; print('OK uproot', uproot.__version__, 'awkward', awkward.__version__)"
