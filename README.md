# nuisflat → parquet on the NGNU HTCondor cluster

Converts NUISANCE flat trees (`*.flat.root`) into one parquet file per
(GENIE tune, neutrino flavor) with HTCondor.

Works from any directory, for any user: clone it wherever you like on `/ngnu`
(the worker nodes must see the clone and its venv), and the venv, job files and
outputs are all kept inside that clone unless you point them elsewhere.

Input samples (read-only) are found in this order:
1. `-i <dir>` / `--indir <dir>`
2. the `NUISFLAT_DIR` environment variable
3. the default shared samples: `/ngnu/home/sungbino/generators/res_studies/genie_comparisons`

## Quick start (any user)

```bash
cd <any/dir/on/ngnu>                   # e.g. /ngnu/home/$USER/work
git clone https://github.com/sungbinoh/nuisflat_ana_ngnu.git && cd nuisflat_ana_ngnu

./submit.sh                      # creates .venv once, makes jobs.txt, submits
condor_q                         # held? -> condor_q -better-analyze <id>
ls output/                       # <tune>_<flavor>.parquet  (inside this clone)
```

Options (relative paths are w.r.t. your current directory):
```bash
./submit.sh -o <output/dir>          # any output dir
./submit.sh -i <flat/tree/dir>       # any input dir containing *.flat.root (searched recursively)
./submit.sh -v <venv/dir>            # reuse an existing venv (must be on /ngnu)
export NUISFLAT_DIR=<flat/tree/dir>  # same as -i, persistent for your shell
```

Submit only some tunes / flavors:
```bash
./submit.sh -l                                   # list available tune/flavor groups (no submit)
./submit.sh -t AR25_20i -f numu                  # one tune, one flavor
./submit.sh -t AR25_20i,AR25_20j -f numu,numubar # comma-separated lists
./submit.sh -t 'AR25_20[ij]*' -f '*_NC'          # shell globs (quote them)
```
Split big groups into several jobs (avoids held jobs from memory/disk limits):
```bash
./submit.sh -f numu -n 5                         # numu groups -> jobs of <=5 files each
./submit.sh -f numu -n 5 -m 8GB -d 10GB          # also raise request_memory / request_disk
```
Outputs become `<tune>_<flavor>_partNNN.parquet`. `xsec_weight` still divides by the
total number of files in the group, so just concatenate all parts (glob below).
Check why jobs were held with `condor_q -hold`, then `condor_rm <cluster>` and resubmit.

Matching: exact, prefix up to `_` (`AR25_20i` → `AR25_20i_01_002`, `numu` → `numu_CC`
but not `numubar_CC`), or glob. Without `-t`/`-f` everything is submitted.

## Step by step (what submit.sh does)

```bash
./setup_venv.sh                  # 1. one-time: venv in ./.venv (uproot, awkward, pyarrow, pandas)
source .venv/bin/activate
python make_joblist.py           # 2. group inputs by (tune, flavor) -> jobs.txt + filelists/
                                 #    (add --tune/--flavor to select, --list to just look)
cat jobs.txt                     #    check tune/flavor parsing
mkdir -p output job_log
condor_submit submit.sub         # 3. submit from the repo dir (OUTDIR=./output, VENV=./.venv)
# condor_submit OUTDIR=<abs/out> VENV=<abs/venv> submit.sub   # other locations
```

Smoke test one group on the UI:
```bash
source .venv/bin/activate
read T F TAG FL < jobs.txt
python process_flat.py --tune $T --flavor $F --out test.parquet $(head -2 $FL)
```

Load results:
```python
import pandas as pd, glob
df = pd.concat(map(pd.read_parquet, glob.glob("output/*.parquet")), ignore_index=True)
```

## For whoever owns the input samples: sharing permissions

Other users need read access to the files and execute (traverse) access on every
parent directory. With `SAMPLES=<your/sample/dir>`:
```bash
d=$(dirname "$SAMPLES"); while [ "$d" != "/" ]; do chmod o+x "$d" 2>/dev/null; d=$(dirname "$d"); done
chmod -R o+rX "$SAMPLES"
```
(Use `g+` instead of `o+` to share only with your unix group.)
`make_joblist.py` stops with an error if the directory is unreadable and warns about
unreadable files.

## Notes
- The venv is built with /usr/bin/python3 on the UI; the WNs must have the same python
  (job log prints the python path). Otherwise rebuild with `PYTHON=<python on both> ./setup_venv.sh`.
- `xsec_weight = fScaleFactor * Weight / n_files` — fScaleFactor is per file, so it must
  be divided by the number of files merged into a channel. Use this for xsec histograms.
- Selection: events with >=1 muon only. `n_protons_50MeV`, `n_pions_30MeV` are stored so
  you can apply 1μ1p / 1μ1π cuts later.
- `Mode` (NUISANCE interaction mode; numu CC RES = 11, 12, 13) is kept if present.
- If a job runs out of memory, lower `--step` (default "200 MB") or raise Request_memory.
