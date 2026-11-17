#!/bin/bash
# One-stop submit for any user, from any directory:
#   ./submit.sh                                        # shared samples -> <repo>/output
#   ./submit.sh -i <flat/tree/dir> -o <output/dir> -v <venv/dir>
#   ./submit.sh -t AR25_20i -f numu           # one tune, one flavor
#   ./submit.sh -t AR25_20i,AR25_20j -f numu,numubar
#   ./submit.sh -l                            # list available tune/flavor groups, no submit
# Relative paths are taken w.r.t. your current directory.
set -euo pipefail
REPO=$(cd "$(dirname "$0")" && pwd)
INDIR=""; TUNE=""; FLAVOR=""; LIST=0; OUTDIR="$REPO/output"; VENV="${VENV:-$REPO/.venv}"
while getopts "i:o:v:t:f:lh" opt; do
  case $opt in
    i) INDIR=$(realpath -m "$OPTARG") ;;
    o) OUTDIR=$(realpath -m "$OPTARG") ;;
    v) VENV=$(realpath -m "$OPTARG") ;;
    t) TUNE=$OPTARG ;;
    f) FLAVOR=$OPTARG ;;
    l) LIST=1 ;;
    *) echo "usage: $0 [-i input_dir] [-o output_dir] [-v venv_dir] [-t tunes] [-f flavors] [-l]"; exit 1 ;;
  esac
done
cd "$REPO"

[ -f "$VENV/bin/activate" ] || { echo "no venv at $VENV -> creating it (one-time)"; ./setup_venv.sh "$VENV"; }
source "$VENV/bin/activate"
if [ $LIST -eq 1 ]; then
  python make_joblist.py ${INDIR:+--indir "$INDIR"} --list
  exit 0
fi
python make_joblist.py ${INDIR:+--indir "$INDIR"} ${TUNE:+--tune "$TUNE"} ${FLAVOR:+--flavor "$FLAVOR"}
mkdir -p "$OUTDIR" job_log
echo "venv   -> $VENV"
echo "output -> $OUTDIR"
condor_submit OUTDIR="$OUTDIR" VENV="$VENV" submit.sub
