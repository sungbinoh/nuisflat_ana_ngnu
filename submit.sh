#!/bin/bash
# One-stop submit for any user, from any directory:
#   ./submit.sh                                        # shared samples -> <repo>/output
#   ./submit.sh -i <flat/tree/dir> -o <output/dir> -v <venv/dir>
#   ./submit.sh -t AR25_20i -f numu           # one tune, one flavor
#   ./submit.sh -t AR25_20i,AR25_20j -f numu,numubar
#   ./submit.sh -f numu -n 5 -m 6GB           # split numu groups into jobs of <=5 files
#   ./submit.sh -l                            # list available tune/flavor groups, no submit
# Relative paths are taken w.r.t. your current directory.
set -euo pipefail
REPO=$(cd "$(dirname "$0")" && pwd)
INDIR=""; TUNE=""; FLAVOR=""; LIST=0; NPER=0; MEMORY=4GB; DISK=4GB; OUTDIR="$REPO/output"; VENV="${VENV:-$REPO/.venv/venv_nuisflat_ana39}"
while getopts "i:o:v:t:f:n:m:d:lh" opt; do
  case $opt in
    i) INDIR=$(realpath -m "$OPTARG") ;;
    o) OUTDIR=$(realpath -m "$OPTARG") ;;
    v) VENV=$(realpath -m "$OPTARG") ;;
    t) TUNE=$OPTARG ;;
    f) FLAVOR=$OPTARG ;;
    n) NPER=$OPTARG ;;
    m) MEMORY=$OPTARG ;;
    d) DISK=$OPTARG ;;
    l) LIST=1 ;;
    *) echo "usage: $0 [-i input_dir] [-o output_dir] [-v venv_dir] [-t tunes] [-f flavors]"
       echo "          [-n files_per_job] [-m request_memory] [-d request_disk] [-l]"; exit 1 ;;
  esac
done
cd "$REPO"

if [ "$VENV" = "$REPO/.venv/venv_nuisflat_ana39" ]; then
  set +u; source "$REPO/setup.sh" >/dev/null || exit 1; set -u   # creates it on first use
else
  [ -f "$VENV/bin/activate" ] || { echo "ERROR: no venv at $VENV" >&2; exit 1; }
  set +u; source "$VENV/bin/activate"; set -u
fi
if [ $LIST -eq 1 ]; then
  python make_joblist.py ${INDIR:+--indir "$INDIR"} --list
  exit 0
fi
python make_joblist.py ${INDIR:+--indir "$INDIR"} ${TUNE:+--tune "$TUNE"} ${FLAVOR:+--flavor "$FLAVOR"} \
    --files-per-job "$NPER"
mkdir -p "$OUTDIR" job_log
echo "venv   -> $VENV"
echo "output -> $OUTDIR   (request_memory=$MEMORY, request_disk=$DISK)"
condor_submit OUTDIR="$OUTDIR" VENV="$VENV" MEMORY="$MEMORY" DISK="$DISK" submit.sub
