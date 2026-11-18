#!/bin/bash
# Set up the python environment for nuisflat_ana_ngnu.  Usage (from anywhere):
#     source setup.sh
# Creates <repo>/.venv/venv_nuisflat_ana39 with the system python3.9 on first use,
# installs/updates requirements.txt when something is missing, and activates it.
# Put the repo on /ngnu so the worker nodes (AlmaLinux9, same python) see the venv.

# ---- must be sourced, not executed
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "Please source this script:  source ${BASH_SOURCE[0]}" >&2
    exit 1
fi

export NUISFLAT_ANA_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

######################################################
#### setup virtual python env if it is not already set
######################################################
PYTHON=${PYTHON:-/usr/bin/python3}          # AlmaLinux9 system python (3.9), same on WNs
PYTHON_VERSION=3.9
VENV_NAME=venv_nuisflat_ana39
ENV_DIR=${NUISFLAT_ANA_DIR}/.venv
VENV_DIR=${ENV_DIR}/${VENV_NAME}
LOGDIR=${ENV_DIR}/logs
mkdir -p "${LOGDIR}"

PY_FOUND=$("${PYTHON}" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)
if [[ "${PY_FOUND}" != "${PYTHON_VERSION}" ]]; then
    echo "WARNING: ${PYTHON} is python ${PY_FOUND:-<not found>}, expected ${PYTHON_VERSION}" >&2
fi
if [[ "${VENV_DIR}" != /ngnu/* ]]; then
    echo "WARNING: ${VENV_DIR} is not on /ngnu; HTCondor worker nodes may not see it" >&2
fi

# Check if virtual environment already exists
if [ -f "${VENV_DIR}/bin/activate" ]; then
    echo "Virtual environment '${VENV_NAME}' already exists. Activating it."
else
    echo "Creating virtual environment '${VENV_NAME}' with ${PYTHON} (python ${PY_FOUND})"
    "${PYTHON}" -m venv "${VENV_DIR}" || { echo "ERROR: venv creation failed" >&2; return 1; }
    echo "Virtual environment '${VENV_NAME}' created."
fi

# Activate the virtual environment
source "${VENV_DIR}/bin/activate"

# check requirements are installed
if pip freeze -r "${NUISFLAT_ANA_DIR}/requirements.txt" 2>&1 | grep -q "not installed"; then
    echo "Updating virtual env installation (log: ${LOGDIR}/init_pip.log)"
    PIPLOG=${LOGDIR}/init_pip.log
    date >> "${PIPLOG}"
    pip install --no-cache-dir --upgrade pip 2>&1 | tee -a "${PIPLOG}"
    pip install --no-cache-dir -r "${NUISFLAT_ANA_DIR}/requirements.txt" 2>&1 | tee -a "${PIPLOG}"
fi

python -c "import uproot, awkward, pyarrow, pandas; print('OK  python', __import__('sys').version.split()[0], ' uproot', uproot.__version__, ' awkward', awkward.__version__)" \
    || { echo "ERROR: package import failed, see ${LOGDIR}/init_pip.log" >&2; return 1; }

# used by submit.sh / submit.sub
export VENV=${VENV_DIR}

echo "Virtual environment '${VENV_NAME}' set up successfully (VENV=${VENV})."
echo "To leave it: deactivate.   To come back: source ${NUISFLAT_ANA_DIR}/setup.sh"
######################################################
