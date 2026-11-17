#!/bin/bash
# One-stop submit for any user, from any directory:
#   ./submit.sh                                        # shared samples -> <repo>/output
#   ./submit.sh -i <flat/tree/dir> -o <output/dir> -v <venv/dir>
# Relative paths are taken w.r.t. your current directory.
set -euo pipefail
REPO=$(cd "$(dirname "$0")" && pwd)
INDIR=""; OUTDIR="$REPO/output"; VENV="${VENV:-$REPO/.venv}"
while getopts "i:o:v:h" opt; do
  case $opt in
    i) INDIR=$(realpath -m "$OPTARG") ;;
    o) OUTDIR=$(realpath -m "$OPTARG") ;;
    v) VENV=$(realpath -m "$OPTARG") ;;
    *) echo "usage: $0 [-i input_dir] [-o output_dir] [-v venv_dir]"; exit 1 ;;
  esac
done
cd "$REPO"

[ -f "$VENV/bin/activate" ] || { echo "no venv at $VENV -> creating it (one-time)"; ./setup_venv.sh "$VENV"; }
source "$VENV/bin/activate"
python make_joblist.py ${INDIR:+--indir "$INDIR"}
mkdir -p "$OUTDIR" job_log
echo "venv   -> $VENV"
echo "output -> $OUTDIR"
condor_submit OUTDIR="$OUTDIR" VENV="$VENV" submit.sub
