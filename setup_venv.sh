#!/bin/bash
# Create the analysis venv on the shared /ngnu filesystem (run once, on the UI).
# Worker nodes run the same OS (AlmaLinux9), so they can use this venv directly.
#   ./setup_venv.sh [VENV_PATH]
set -euo pipefail
VENV=${1:-/ngnu/home/sungbino/venvs/nuisflat}
PY=${PYTHON:-/usr/bin/python3}     # system python, present on UI and WNs

echo "python: $($PY --version)  ->  venv: $VENV"
$PY -m venv "$VENV"
source "$VENV/bin/activate"
pip install --upgrade pip
pip install -r "$(dirname "$0")/requirements.txt"
python -c "import uproot, awkward, pyarrow, pandas; print('OK uproot', uproot.__version__, 'awkward', awkward.__version__)"
