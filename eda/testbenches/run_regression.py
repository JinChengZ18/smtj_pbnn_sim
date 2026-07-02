#!/usr/bin/env python3
"""P1 regression runner: compile smtj_sot.va, run ngspice, compare to golden.

Steps:
  1. ensure golden_psw.csv exists (else run gen_golden.py).
  2. compile  eda/models/smtj_sot.va  ->  smtj_sot.osdi   (OpenVAF / OpenVAF-Reloaded).
  3. write .spiceinit (`osdi smtj_sot.osdi`) so the model binds at parse time,
     then run regression_psw.spice in ngspice (-b) -> ngspice_psw.csv.
  4. compare V(psw) vs golden, assert max|err| < 1e-3 and R^2 >= 0.99.

Tool discovery (no PATH needed): env vars OPENVAF / NGSPICE, then
eda/tools.local.json {"openvaf": "...", "ngspice": "..."}, then PATH.
If tools are missing it prints guidance (eda/SETUP_opensource.md) and exits 0.

Run:  python eda/testbenches/run_regression.py
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent / "models" / "smtj_sot.va"
CONFIG = HERE.parent / "tools.local.json"          # gitignored, machine-specific
GOLDEN = HERE / "golden_psw.csv"
NETLIST = HERE / "regression_psw.spice"
OSDI = HERE / "smtj_sot.osdi"
NG_OUT = HERE / "ngspice_psw.csv"
SUMMARY = HERE / "regression_summary.json"          # committable run evidence (osdi/csv are gitignored)


def load_config():
    if CONFIG.exists():
        try:
            return json.loads(CONFIG.read_text())
        except Exception:
            return {}
    return {}


def find_tool(env_key, config_key, which_names):
    v = os.environ.get(env_key)
    if v and Path(v).exists():
        return v
    cfg = load_config().get(config_key)
    if cfg and Path(cfg).exists():
        return cfg
    for n in which_names:
        p = shutil.which(n)
        if p:
            return p
    return None


def load_csv(path, cols):
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
                continue
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

    openvaf = find_tool("OPENVAF", "openvaf", ["openvaf", "openvaf-r"])
    ngspice = find_tool("NGSPICE", "ngspice", ["ngspice_con", "ngspice"])
    if not openvaf or not ngspice:
        print("=" * 64)
        print("Open-source EDA not found:")
        print(f"  OpenVAF : {openvaf or 'NOT FOUND'}")
        print(f"  ngspice : {ngspice or 'NOT FOUND'}")
        print("Set env OPENVAF / NGSPICE, or create eda/tools.local.json, or add to PATH.")
        print("See eda/SETUP_opensource.md. Artifacts are ready to run later.")
        print("=" * 64)
        return 0

    print(f"[1/3] compiling {MODEL.name}\n      {openvaf}")
    subprocess.run([openvaf, str(MODEL), "-o", str(OSDI)], check=True, cwd=HERE)

    # ngspice-46 binds the OSDI model via `osdi <file>` in .spiceinit (read before parse)
    (HERE / ".spiceinit").write_text("osdi smtj_sot.osdi\n")
    print(f"[2/3] running ngspice\n      {ngspice}")
    subprocess.run([ngspice, "-b", str(NETLIST.name)], check=True, cwd=HERE)

    print("[3/3] comparing V(psw) to golden")
    g = load_csv(GOLDEN, [0, 1])          # V, psw
    n = load_csv(NG_OUT, [0, 1])          # V, psw  (wrdata col0=sweep, col1=v(psw))
    if not g or not n:
        print("FAIL: could not parse outputs")
        return 1
    psw_golden = np.interp(n[0], g[0], g[1])
    err = np.abs(n[1] - psw_golden)
    rsq = r2(psw_golden, n[1])
    print(f"  points={len(n[0])}  max|err|={err.max():.2e}  R^2(ngspice vs golden)={rsq:.6f}")
    ok = err.max() < 1e-3 and rsq >= 0.99
    print("  RESULT:", "PASS" if ok else "FAIL")

    # committable evidence the regression was actually executed (the .osdi/.csv are
    # gitignored as regenerable). NOTE: this R^2 is OSDI-vs-numpy SELF-CONSISTENCY
    # (the golden mirrors the same closed form the .va evaluates), i.e. a model-port /
    # tool-equivalence check -- NOT validation against measurement (see golden_summary.json,
    # sigmoid-vs-measured R^2=0.992) or against the LLG solver (see llg_validate.py).
    from datetime import datetime, timezone
    SUMMARY.write_text(json.dumps({
        "kind": "tool_self_consistency_regression",
        "note": "OSDI-compiled smtj_sot.va vs numpy golden (same closed form); not a physical validation.",
        "points": int(len(n[0])),
        "max_abs_err": float(err.max()),
        "r2_ngspice_vs_golden": float(rsq),
        "pass": bool(ok),
        "openvaf": str(openvaf),
        "ngspice": str(ngspice),
        "ran_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2))
    print(f"  wrote {SUMMARY.name}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
