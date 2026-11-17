#!/usr/bin/env python3
"""
Convert one (tune, flavor) group of NUISANCE flat trees into a single parquet file.

Same output columns as the notebook version (leading muon, leading charged pion,
multiplicities, event scalars, model_flag/Models), but done column-wise in
awkward + chunked with uproot.iterate, so memory stays flat even for big samples.

Usage:
    python process_flat.py --tune AR25_20i_01_002 --flavor numu \
        --out /path/out.parquet file1.flat.root [file2.flat.root ...]
"""
import argparse
import os

import awkward as ak
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import uproot

TREE = "FlatTree_VARS"
BRANCHES = ["Enu_true", "Q2", "W", "Weight", "nfsp",
            "px", "py", "pz", "E", "pdg", "fScaleFactor"]
OPTIONAL = ["Mode", "PDGnu", "tgt", "cc"]   # kept if present in the tree

M_P = 0.938272
M_PI = 0.13957039

# tune-prefix -> (model_flag, label). Extend as needed.
TUNE_MAP = {
    "AR23_20i": (2, "GENIE Ar23 hA"),
    "AR25_20i": (4, "GENIE Ar25 hA"),
    "AR25_20j": (5, "GENIE Ar25 hN"),
    "AR25_20k": (7, "GENIE Ar25 20k"),
    "AR25_20l": (6, "GENIE Ar25 G4 Bert"),
    "AR25_20m": (8, "GENIE Ar25 20m"),
    "AR25_20n": (9, "GENIE Ar25 20n"),
}


def leading(arr, mask, fields=("px", "py", "pz", "E", "pdg")):
    """Highest-E particle passing mask per event (None if none)."""
    sel = arr[mask]
    idx = ak.argmax(sel.E, axis=1, keepdims=True)
    lead = ak.firsts(sel[idx])
    out = {}
    for f in fields:
        if f == "pdg":
            out[f] = ak.to_numpy(ak.fill_none(lead[f], 0)).astype(np.int32)
        else:
            out[f] = ak.to_numpy(ak.fill_none(lead[f], np.nan)).astype(np.float64)
    p = np.sqrt(out["px"]**2 + out["py"]**2 + out["pz"]**2)
    with np.errstate(invalid="ignore", divide="ignore"):
        out["cos_theta"] = out["pz"] / p
    return out


def process_chunk(ev, file_idx, n_files, tune, flavor, entry_offset):
    part = ak.zip({k: ev[k] for k in ("px", "py", "pz", "E", "pdg")})
    apdg = abs(part.pdg)

    is_mu = apdg == 13
    is_p = (part.pdg == 2212) & (part.E - M_P > 0.05)     # T_p  > 50 MeV
    is_pi = (apdg == 211) & (part.E - M_PI > 0.03)        # T_pi > 30 MeV
    is_cpi = apdg == 211                                  # leading cpi: no KE cut (as before)

    n_mu = ak.to_numpy(ak.sum(is_mu, axis=1))
    keep = n_mu > 0                                       # events with >=1 muon (as before)

    mu = leading(part, is_mu)
    cpi = leading(part, is_cpi)

    cols = {"entry": np.arange(len(n_mu), dtype=np.int64) + entry_offset,
            "file_idx": np.full(len(n_mu), file_idx, dtype=np.int32)}
    for k, v in mu.items():
        cols[f"muon_{k}"] = v
    for k, v in cpi.items():
        cols[f"cpi_{k}"] = v
    cols["n_muons"] = n_mu
    cols["n_protons_50MeV"] = ak.to_numpy(ak.sum(is_p, axis=1))
    cols["n_pions_30MeV"] = ak.to_numpy(ak.sum(is_pi, axis=1))
    for k in ["Enu_true", "Q2", "Weight", "fScaleFactor", "W"] + \
             [o for o in OPTIONAL if o in ev.fields]:
        cols[k] = ak.to_numpy(ev[k])

    # fScaleFactor is per-file (xsec / N_gen). When merging N files of the same
    # channel, the per-event xsec weight must be divided by N.
    cols["xsec_weight"] = cols["fScaleFactor"] * cols["Weight"] / n_files

    flag, label = TUNE_MAP.get(tune[:8], (-1, "Other"))
    n = int(keep.sum())
    table = {k: v[keep] for k, v in cols.items()}
    table["tune"] = np.full(n, tune, dtype=object)
    table["flavor"] = np.full(n, flavor, dtype=object)
    table["model_flag"] = np.full(n, flag, dtype=np.int32)
    table["Models"] = np.full(n, label, dtype=object)
    return pa.table(table)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", required=True)
    ap.add_argument("--flavor", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--step", default="200 MB", help="uproot chunk size")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    tmp = a.out + ".tmp"
    writer = None
    n_files = len(a.files)
    n_tot = 0
    for fi, f in enumerate(a.files):
        with uproot.open(f) as rf:
            t = rf[TREE]
            br = BRANCHES + [o for o in OPTIONAL if o in t.keys()]
            offset = 0
            step = int(a.step) if a.step.isdigit() else a.step
            for ev in t.iterate(br, step_size=step):
                tab = process_chunk(ev, fi, n_files, a.tune, a.flavor, offset)
                offset += len(ev)
                if writer is None:
                    writer = pq.ParquetWriter(tmp, tab.schema, compression="snappy")
                writer.write_table(tab)
                n_tot += tab.num_rows
        print(f"[{fi+1}/{n_files}] {f}  ({offset} events)", flush=True)
    if writer is not None:
        writer.close()
        os.replace(tmp, a.out)   # atomic: no half-written parquet on failure
    print(f"Wrote {n_tot} events -> {a.out}")


if __name__ == "__main__":
    main()
