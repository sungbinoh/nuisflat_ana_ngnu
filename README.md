# nuisflat → parquet on the NGNU HTCondor cluster

```bash
WORK=/ngnu/home/sungbino/generators/res_studies/parquet_jobs
mkdir -p $WORK /ngnu/home/sungbino/generators/res_studies/parquet && cd $WORK
# copy process_flat.py make_joblist.py run_job.sh submit.sub here
chmod +x run_job.sh

# 1) group files by (tune, flavor) -> jobs.txt + filelists/
python3 make_joblist.py --indir /ngnu/home/sungbino/generators/res_studies/genie_comparisons
cat jobs.txt                       # check tune/flavor parsing before submitting

# 2) (optional) smoke test one group on the UI with a few files
source /cvmfs/sft.cern.ch/lcg/views/LCG_107/x86_64-el9-gcc11-opt/setup.sh
read T F TAG FL < jobs.txt
python3 process_flat.py --tune $T --flavor $F --out test.parquet $(head -2 $FL)

# 3) submit
mkdir -p job_log
condor_submit submit.sub
condor_q                           # held? -> condor_q -better-analyze <id>
```

Output: one `<tune>_<flavor>.parquet` per job in `OUTDIR` (set in submit.sub).

Load all together:
```python
import pandas as pd, glob
df = pd.concat(map(pd.read_parquet, glob.glob(".../parquet/*.parquet")), ignore_index=True)
```

Notes
- `xsec_weight = fScaleFactor * Weight / n_files` — fScaleFactor is per file, so it must
  be divided by the number of files merged into a channel. Use this for xsec histograms.
- Selection is unchanged from the notebook: events with >=1 muon only (the
  "1mu1p" requirement is not actually applied — n_protons_50MeV is stored so you can cut later).
- `Mode` (NUISANCE interaction mode; numu CC RES = 11, 12, 13) is kept if present.
- If a job runs out of memory, lower `--step` (default "200 MB") or raise Request_memory.
