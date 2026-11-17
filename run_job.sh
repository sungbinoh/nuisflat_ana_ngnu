#!/bin/bash
# Condor executable: run_job.sh <tune> <flavor> <tag> <filelist>
# Runs on the WN inside $_CONDOR_SCRATCH_DIR; writes <tag>.parquet there,
# Condor transfers it back (see transfer_output_remaps in submit.sub).
TUNE=$1; FLAV=$2; TAG=$3; FLIST=$4

# AlmaLinux9 WN: LCG view provides python3 + uproot + awkward + pyarrow + pandas
source /cvmfs/sft.cern.ch/lcg/views/LCG_107/x86_64-el9-gcc11-opt/setup.sh

cd "$_CONDOR_SCRATCH_DIR"
echo "host=$(hostname)  tune=$TUNE  flavor=$FLAV  scratch=$PWD"
python3 -c "import uproot, awkward, pyarrow; print('uproot', uproot.__version__, 'awkward', awkward.__version__)"

# input .flat.root files are read directly from /ngnu (shared filesystem)
mapfile -t FILES < "$FLIST"
python3 process_flat.py --tune "$TUNE" --flavor "$FLAV" --out "${TAG}.parquet" "${FILES[@]}"
RESULT=$?
exit $RESULT
