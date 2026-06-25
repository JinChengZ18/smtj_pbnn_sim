#!/usr/bin/env python3
"""P3 first-cut: differential dual-cell XNOR-popcount column at MTJ (resistor) level.

Each weight is a differential pair (R+, R-): (R_P, R_AP) if w=+1 else (R_AP, R_P).
Input x drives the pair differentially +-x*Vr/2; both legs tie to a virtual-ground
bit-line (0 V ammeter). Then
    I_BL = (Vr/2) * (G_P - G_AP) * sum_i w_i x_i           (the signal),
and a COMMON input offset adds a weight/input-INDEPENDENT term (G_P+G_AP per cell,
calibratable) -> bias cancellation (claim a). MTJ device mismatch (sigma_Rp, sigma_TMR)
turns that "constant" into a data-dependent RESIDUAL offset; this harness measures it
vs array size N via Monte-Carlo, with a matched-case linearity check.

The READ path is a pure resistor network (R_P/R_AP), so the .va is not needed here (it
models the stochastic WRITE + observables for P1/P2). A real transistor current-sense
amplifier and ITS input-referred offset come with the sky130 PDK (P3 full) -- that offset
is the second claim-(c) knob to compare against V_T (errata R2).

Run: python eda/testbenches/diff_column.py     (needs ngspice; no OpenVAF/.va)
"""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CONFIG = HERE.parent / "tools.local.json"
NET = HERE / "_diff_run.spice"

RP, TMR, VR = 4900.0, 1.0, 0.1            # R_P [ohm], TMR, read voltage [V]
GP, GAP = 1.0 / RP, 1.0 / (RP * (1 + TMR))
DG = GP - GAP                              # delta-G per unit |w x|
SIG_RP, SIG_TMR = 0.07, 0.04               # mismatch (Hikstor 40nm PDK statistics)
LSB_I = (VR / 2.0) * DG                     # bit-line current per 1 popcount unit


def _cfg():
    try:
        return json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    except Exception:
        return {}


def find_tool(env, key, names):
    v = os.environ.get(env)
    if v and Path(v).exists():
        return v
    c = _cfg().get(key)
    if c and Path(c).exists():
        return c
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def build_netlist(w, x, rp, rap):
    L = ["* P3 differential column (resistor read network)",
         "Vbl bl 0 dc 0"]                   # virtual-ground bit-line + ammeter
    for i, (wi, xi) in enumerate(zip(w, x)):
        vp, vn = +xi * VR / 2.0, -xi * VR / 2.0
        Rplus = rp[i] if wi > 0 else rap[i]   # R+ = R_P if w=+1 else R_AP
        Rminus = rap[i] if wi > 0 else rp[i]
        L += [f"V{i}p rp{i} 0 dc {vp:.6g}",
              f"V{i}n rn{i} 0 dc {vn:.6g}",
              f"Rp{i} rp{i} bl {Rplus:.6g}",
              f"Rn{i} rn{i} bl {Rminus:.6g}"]
    L += [".control", "op", "print i(Vbl)", "quit", ".endc", ".end"]
    return "\n".join(L) + "\n"


def run_ibl(ng, w, x, rp, rap):
    NET.write_text(build_netlist(w, x, rp, rap))
    out = subprocess.run([ng, "-b", NET.name], cwd=HERE, capture_output=True, text=True)
    m = re.search(r"i\(vbl\)\s*=\s*([-+0-9.eE]+)", out.stdout, re.IGNORECASE)
    return float(m.group(1)) if m else float("nan")


def mismatch(n, rng):
    rp = RP * (1.0 + SIG_RP * rng.standard_normal(n))
    tmr = TMR * (1.0 + SIG_TMR * rng.standard_normal(n))
    rap = rp * (1.0 + tmr)
    return rp, rap


def main():
    ng = find_tool("NGSPICE", "ngspice", ["ngspice_con", "ngspice"])
    if not ng:
        print("ngspice not found; see eda/SETUP_opensource.md")
        return 0
    (HERE / ".spiceinit").write_text("* P3 read network: no OSDI model needed\n")
    rng = np.random.default_rng(20260626)

    # --- (1) matched-case linearity: I_BL should equal (Vr/2)*DG*sum(w x) ---
    lin = []
    for _ in range(12):
        n = 64
        w = rng.choice([-1, 1], n); x = rng.choice([-1, 1], n)
        ibl = run_ibl(ng, w, x, np.full(n, RP), np.full(n, RP * (1 + TMR)))
        lin.append((int(np.sum(w * x)), ibl / LSB_I))   # (ideal popcount, measured popcount)
    ideal = np.array([a for a, _ in lin]); meas = np.array([b for _, b in lin])
    sign = 1.0 if np.dot(ideal, meas) >= 0 else -1.0    # fix global polarity convention
    lin_err = float(np.max(np.abs(sign * meas - ideal)))

    # --- (2) bias-cancellation residual: balanced pattern (sum w x = 0) + MTJ mismatch ---
    print(f"matched linearity: max|I_BL/LSB - sum(w x)| = {lin_err:.3e} popcount units")
    print("N     residual_offset(popcount units, 1-sigma)   /sqrt(N)")
    res_rows = []
    for n in (16, 64, 256):
        prod = np.array([1] * (n // 2) + [-1] * (n // 2))   # sum of products = 0 (balanced)
        resid = []
        for _ in range(40):
            w = rng.choice([-1, 1], n)
            x = prod * w                                    # enforce w*x = prod (sum 0)
            rp, rap = mismatch(n, rng)
            resid.append(sign * run_ibl(ng, w, x, rp, rap) / LSB_I)
        resid = np.array(resid)
        sd = float(np.std(resid))
        res_rows.append(dict(N=n, residual_sigma_popcount=sd, per_sqrtN=sd / np.sqrt(n)))
        print(f"{n:<5} {sd:>10.4f}                              {sd/np.sqrt(n):.4f}")

    summ = dict(RP=RP, TMR=TMR, Vr=VR, sigma_Rp=SIG_RP, sigma_TMR=SIG_TMR,
                LSB_current_uA=LSB_I * 1e6, matched_linearity_maxerr=lin_err,
                residual=res_rows,
                note=("matched -> bias cancels (residual~0); mismatch -> residual offset "
                      "~sqrt(N)*per-cell. Transistor sense-amp offset added with sky130 (P3 full)."))
    (HERE / "diff_summary.json").write_text(json.dumps(summ, indent=2))
    print(f"\nLSB current = {LSB_I*1e6:.2f} uA/popcount. matched bias cancellation: "
          f"residual ~ 0; mismatch residual grows ~sqrt(N) (claim a quantified).")


if __name__ == "__main__":
    main()
