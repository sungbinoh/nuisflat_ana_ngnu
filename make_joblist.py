#!/usr/bin/env python3
"""
Scan the copied tree for *.flat.root, group by (tune, flavor), and write
  jobs.txt          one line per Condor job:  tune flavor tag filelist
  filelists/*.txt   the input files of each group

Tune  : taken from the path (AR2x_20?_xx_xxx).
Flavor: taken from the filename prefix, e.g. 14_1000180400_CC_... -> numu_CC.
        Falls back to a directory name like numu / numubar / nue / nuebar.

Usage:
    python make_joblist.py                    # shared samples (DEFAULT_INDIR)
    python make_joblist.py --indir /my/flat   # or your own samples
                                              # (or set NUISFLAT_DIR)
"""
import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# Shared input samples (read-only for other users)
DEFAULT_INDIR = os.environ.get(
    "NUISFLAT_DIR", "/ngnu/home/sungbino/generators/res_studies/genie_comparisons")

PDG2NAME = {"14": "numu", "-14": "numubar", "12": "nue", "-12": "nuebar",
            "16": "nutau", "-16": "nutaubar"}
TUNE_RE = re.compile(r"(AR2\d_20[a-z]_\d{2}_\d{3})")
FILE_RE = re.compile(r"^(-?1[246])_\d+_(CC|NC)")
DIR_FLAVORS = {"numu", "numubar", "nue", "nuebar", "nutau", "nutaubar"}


def classify(path: Path):
    m = TUNE_RE.search(str(path))
    tune = m.group(1) if m else "unknown"
    m = FILE_RE.match(path.name)
    if m:
        return tune, f"{PDG2NAME[m.group(1)]}_{m.group(2)}"
    for part in reversed(path.parts[:-1]):
        if part.lower() in DIR_FLAVORS:
            return tune, part.lower()
    return tune, "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", default=DEFAULT_INDIR,
                    help=f"top dir to scan for *.flat.root (default: {DEFAULT_INDIR})")
    ap.add_argument("--jobs", default="jobs.txt")
    a = ap.parse_args()

    if not os.access(a.indir, os.R_OK | os.X_OK):
        sys.exit(f"ERROR: cannot read {a.indir} (ask the owner for read access)")
    print(f"scanning {a.indir}")

    groups = defaultdict(list)
    unreadable = []
    for f in sorted(Path(a.indir).rglob("*.flat.root")):
        if not os.access(f, os.R_OK):
            unreadable.append(f)
            continue
        groups[classify(f)].append(str(f.resolve()))
    if unreadable:
        print(f"WARNING: skipped {len(unreadable)} unreadable files, e.g. {unreadable[0]}")
    if not groups:
        sys.exit("ERROR: no readable *.flat.root files found")

    flist_dir = Path("filelists").resolve()
    flist_dir.mkdir(exist_ok=True)
    with open(a.jobs, "w") as jf:
        for (tune, flav), files in sorted(groups.items()):
            tag = f"{tune}_{flav}"
            fl = flist_dir / f"{tag}.txt"
            fl.write_text("\n".join(files) + "\n")
            jf.write(f"{tune} {flav} {tag} {fl}\n")
            print(f"{tag:40s} {len(files):5d} files")
    print(f"\n{len(groups)} jobs -> {a.jobs}")
    if any(k[1] == "unknown" or k[0] == "unknown" for k in groups):
        print("WARNING: some files could not be classified; check filelists/*unknown*")


if __name__ == "__main__":
    main()
