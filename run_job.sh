#!/bin/bash
# Condor executable: run_job.sh <tune> <flavor> <tag> <filelist>
# Runs on the WN inside $_CONDOR_SCRATCH_DIR; writes <tag>.parquet there,
# Condor transfers it back (see transfer_output_remaps in submit.sub).
TUNE=$1; FLAV=$2; TAG=$3; FLIST=$4

# venv on shared /ngnu, created once with setup_venv.sh (override via VENV in submit.sub)
VENV=${VENV:-/ngnu/home/sungbino/venvs/nuisflat}
if [ ! -f "$VENV/bin/activate" ]; then
    echo "ERROR: venv not found at $VENV (run setup_venv.sh on the UI first)" >&2
    exit 2
fi
source "$VENV/bin/activate"

cd "$_CONDOR_SCRATCH_DIR"
echo "host=$(hostname)  tune=$TUNE  flavor=$FLAV  scratch=$PWD  python=$(which python)"
python -c "import uproot, awkward; print('uproot', uproot.__version__, 'awkward', awkward.__version__)"

# input .flat.root files are read directly from /ngnu (shared filesystem)
mapfile -t FILES < "$FLIST"
python process_flat.py --tune "$TUNE" --flavor "$FLAV" --out "${TAG}.parquet" "${FILES[@]}"
exit $?
