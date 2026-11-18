#!/usr/bin/env python3
"""
Scan the copied tree for *.flat.root, group by (tune, flavor), and write
  jobs.txt          one line per Condor job:
                    tune flavor tag filelist n_files_total file_offset
  filelists/*.txt   the input files of each group

Tune  : taken from the path (AR2x_20?_xx_xxx).
Flavor: taken from the filename prefix, e.g. 14_1000180400_CC_... -> numu_CC.
        Falls back to a directory name like numu / numubar / nue / nuebar.

Usage:
    python make_joblist.py                    # shared samples (DEFAULT_INDIR)
    python make_joblist.py --indir /my/flat   # or your own samples
                                              # (or set NUISFLAT_DIR)
    python make_joblist.py --list             # show available tune/flavor groups only
    python make_joblist.py --tune AR25_20i --flavor numu,numubar
        --tune / --flavor take comma-separated values; each matches exactly,
        as a prefix up to "_" (AR25_20i -> AR25_20i_01_002, numu -> numu_CC
        but not numubar_CC), or as a shell glob (AR25_20[ij]*, *_NC).
    python make_joblist.py --flavor numu --files-per-job 5
        split each group into jobs of at most 5 files -> <tag>_partNNN.parquet
        (xsec_weight still uses the total number of files in the group)
"""
import argparse
import fnmatch
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


def matches(value, patterns):
    """True if value matches any pattern (exact, '<pattern>_' prefix, or glob)."""
    if not patterns:
        return True
    return any(value == p or value.startswith(p + "_") or fnmatch.fnmatchcase(value, p)
               for p in patterns)


def split_csv(s):
    return [x.strip() for x in s.split(",") if x.strip()] if s else []


def check_file(path, tree="FlatTree_VARS"):
    """Return None if the file has a non-empty flat tree, else a reason string."""
    import uproot
    try:
        with uproot.open(path) as f:
            n = f[tree].num_entries
        return None if n > 0 else "0 entries"
    except Exception as e:
        return f"{type(e).__name__}: {str(e).splitlines()[0]}"


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
    ap.add_argument("--tune", default="", help="comma-separated tune selection")
    ap.add_argument("--flavor", default="", help="comma-separated flavor selection")
    ap.add_argument("--files-per-job", type=int, default=0,
                    help="split each group into jobs of at most N files (0 = one job per group)")
    ap.add_argument("--no-check", action="store_true",
                    help="skip opening each file to drop empty/corrupt ones (faster)")
    ap.add_argument("--list", action="store_true",
                    help="only print the available (tune, flavor) groups")
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

    if a.list:
        print(f"{'tune':20s} {'flavor':14s} {'files':>5s}")
        for (tune, flav), files in sorted(groups.items()):
            print(f"{tune:20s} {flav:14s} {len(files):5d}")
        return

    tunes, flavors = split_csv(a.tune), split_csv(a.flavor)
    groups = {k: v for k, v in groups.items()
              if matches(k[0], tunes) and matches(k[1], flavors)}
    if not groups:
        sys.exit(f"ERROR: no groups match --tune '{a.tune}' --flavor '{a.flavor}' "
                 "(see --list)")

    # drop empty/corrupt files so they neither crash jobs nor bias xsec_weight
    if not a.no_check:
        try:
            import uproot  # noqa: F401
        except ImportError:
            print("WARNING: uproot not available, cannot check files (activate the venv)")
            a.no_check = True
    if not a.no_check:
        n_all = sum(len(v) for v in groups.values())
        print(f"checking {n_all} files (use --no-check to skip) ...", flush=True)
        bad = []
        for k in list(groups):
            good = []
            for f in groups[k]:
                why = check_file(f)
                (bad.append((f, why)) if why else good.append(f))
            groups[k] = good
        groups = {k: v for k, v in groups.items() if v}
        if bad:
            Path("bad_files.txt").write_text("".join(f"{f}\t{w}\n" for f, w in bad))
            print(f"WARNING: dropped {len(bad)} empty/corrupt files -> bad_files.txt")
            for f, w in bad[:5]:
                print(f"   {f}  ({w})")
        if not groups:
            sys.exit("ERROR: no valid files left")
    if tunes or flavors:
        print(f"selection: tune={tunes or 'all'} flavor={flavors or 'all'}")

    flist_dir = Path("filelists").resolve()
    flist_dir.mkdir(exist_ok=True)
    n_jobs = 0
    with open(a.jobs, "w") as jf:
        for (tune, flav), files in sorted(groups.items()):
            base = f"{tune}_{flav}"
            n = len(files)
            size = a.files_per_job if a.files_per_job > 0 else n
            chunks = [files[i:i + size] for i in range(0, n, size)]
            for ic, chunk in enumerate(chunks):
                tag = base if len(chunks) == 1 else f"{base}_part{ic:03d}"
                fl = flist_dir / f"{tag}.txt"
                fl.write_text("\n".join(chunk) + "\n")
                jf.write(f"{tune} {flav} {tag} {fl} {n} {ic * size}\n")
                n_jobs += 1
            print(f"{base:40s} {n:5d} files -> {len(chunks):4d} job(s)")
    print(f"\n{n_jobs} jobs -> {a.jobs}")
    if any(k[1] == "unknown" or k[0] == "unknown" for k in groups):
        print("WARNING: some files could not be classified; check filelists/*unknown*")


if __name__ == "__main__":
    main()
