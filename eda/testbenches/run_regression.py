#!/usr/bin/env python3
"""P1 regression runner: compile smtj_sot.va, run ngspice, compare to golden.

Steps:
  1. ensure golden_psw.csv exists (else run gen_golden.py).
  2. compile  eda/models/smtj_sot.va  ->  smtj_sot.osdi   (OpenVAF / OpenVAF-Reloaded).
  3. run      regression_psw.spice in ngspice (-b), producing ngspice_psw.csv.
  4. compare  V(psw) vs golden, assert max|err| small and R^2 >= 0.99.

If openvaf/ngspice are not installed this prints install guidance (see
eda/SETUP_opensource.md) and exits 0 — the artifacts are ready to run later.

Run:  python eda/testbenches/run_regression.py
"""
from __future__ import annotations
import csv
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent / "models" / "smtj_sot.va"
GOLDEN = HERE / "golden_psw.csv"
NETLIST = HERE / "regression_psw.spice"
OSDI = HERE / "smtj_sot.osdi"
NG_OUT = HERE / "ngspice_psw.csv"

OPENVAF_CANDIDATES = ["openvaf", "openvaf-reloaded", "openvaf_reloaded"]
NGSPICE_CANDIDATES = ["ngspice", "ngspice_con"]


def find(cands):
    for c in cands:
        p = shutil.which(c)
        if p:
            return p
    return None


def load_csv(path, cols):
    """Load whitespace/comma CSV; return dict of column index -> np.array."""
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line[0] in "*#":
                continue
            parts = [p for p in line.replace(",", " ").split() if p]
            try:
                rows.append([float(p) for p in parts])
            except ValueError:
                continue  # header
    arr = np.array(rows)
    return {c: arr[:, c] for c in cols} if arr.size else {}


def r2(y, yhat):
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def main():
    if not GOLDEN.exists():
        print("golden missing; generating ...")
        subprocess.run([sys.executable, str(HERE / "gen_golden.py")], check=True)

    openvaf = find(OPENVAF_CANDIDATES)
    ngspice = find(NGSPICE_CANDIDATES)
    if not openvaf or not ngspice:
        print("=" * 64)
        print("Open-source EDA not found:")
        print(f"  OpenVAF : {openvaf or 'NOT FOUND'}")
        print(f"  ngspice : {ngspice or 'NOT FOUND'}")
        print("Install per eda/SETUP_opensource.md, then re-run this script.")
        print("Artifacts are ready: smtj_sot.va, regression_psw.spice, golden_psw.csv")
        print("=" * 64)
        return 0

    # 2. compile Verilog-A -> OSDI
    print(f"[1/3] compiling {MODEL.name} with {openvaf}")
    subprocess.run([openvaf, str(MODEL), "-o", str(OSDI)], check=True, cwd=HERE)

    # 3. run ngspice (batch)
    print(f"[2/3] running ngspice on {NETLIST.name}")
    subprocess.run([ngspice, "-b", str(NETLIST)], check=True, cwd=HERE)

    # 4. compare
    print("[3/3] comparing to golden")
    g = load_csv(GOLDEN, [0, 1])          # V, psw
    n = load_csv(NG_OUT, [0, 1])          # V, psw   (wrdata: col0=sweep, col1=v(psw))
    if not g or not n:
        print("FAIL: could not parse outputs")
        return 1
    psw_golden = np.interp(n[0], g[0], g[1])
    err = np.abs(n[1] - psw_golden)
    rsq = r2(psw_golden, n[1])
    print(f"  max|err| = {err.max():.2e}   R^2(ngspice vs golden) = {rsq:.5f}")
    ok = err.max() < 1e-3 and rsq >= 0.99
    print("  RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
