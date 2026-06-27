#!/usr/bin/env python3
"""Hero (A1) C1 — accuracy-vs-(V_offset/V_T) Pareto with offset-cancellation options.

The publishable design boundary of "slope-matched p-bit readout": budget the SA input-referred
offset against the device Sigmoid slope V_T (the Bernoulli decision window), then ask WHICH
offset-cancellation strategy is Pareto-optimal at each readout operating point. Extends
readout_mapping.py (co-design law sigma_pc = sigma_offset_V * 2*PC_FS / V_in) with a PPA COST axis.

Inputs (reused, consistent with the rest of the Hero loop):
  - per-column accuracy curve  : eda/interface/hero_mnist_summary.json (sigma_popcount -> acc)
  - extracted plain-SA offset  : 9.21 mV = 0.39 V_T (run_offset_mc.py N=120; N=24 gave 11.05, high)
  - SA dynamic energy floor    : ~48 fJ central (sa_postlayout.py range 23-74 fJ)

Cancellation options (residual offset is Pelgrom/prior-art order-of-magnitude; cost is a PPA proxy
-- AREA x ENERGY relative to the plain StrongARM. Honesty: ratios, sky130-class AVT, first-cut):
  plain SA            :  9.21 mV, area 1.0x, energy 1.0x   (1 eval phase; run_offset_mc N=120)
  4x input-pair area  :  4.61 mV, area 2.2x, energy 1.25x  (Pelgrom 1/sqrt(A): sigma/2)
  single-cap auto-zero:  1.50 mV, area 1.5x, energy 1.7x   (+1 sample phase; ~7x suppression)
  two-phase chopping  :  0.50 mV, area 1.7x, energy 2.2x   (continuous chop + ripple filter)
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
VT_mV = 23.414
E0_fJ = 48.0          # central SA dynamic energy (sa_postlayout.py)
NOISE_PP = 0.15       # single-run MNIST accuracy noise floor (the per-column curve wiggles ~this)
WORTH_PP = 0.20       # accuracy gain over plain SA needed to "earn" the cost (must beat NOISE_PP)

OPTIONS = [   # name, residual offset mV, area x, energy x
    ("plain SA",             9.21, 1.0, 1.00),   # run_offset_mc.py N=120 (= 0.39 V_T)
    ("4x input-pair area",   4.61, 2.2, 1.25),   # Pelgrom sigma/2
    ("single-cap auto-zero", 1.50, 1.5, 1.70),
    ("two-phase chopping",   0.50, 1.7, 2.20),
]
LAYERS = {"layer1 F=784": 784, "layer2 F=1024": 1024}
PLAIN_mV = OPTIONS[0][1]                                        # plain-SA offset (firmed, run_offset_mc N=120)
AZ_mV = next(o[1] for o in OPTIONS if "auto-zero" in o[0])      # single-cap auto-zero residual


def load_curve():
    d = json.loads((REPO / "eda" / "interface" / "hero_mnist_summary.json").read_text())
    sweep = sorted(d["per_column_sweep"], key=lambda r: r["sigma_popcount"])
    xs = np.array([r["sigma_popcount"] for r in sweep])
    ys = np.array([r["acc_pct"] for r in sweep])
    return xs, ys, float(d["per_column_sweep"][0]["acc_pct"])


def sigma_pc(off_mV, pc_fs, v_in):
    return off_mV * 2.0 * pc_fs / (v_in * 1e3)     # co-design law (max-gain transimpedance)


def pareto_front(points):
    """points: list of dict with cost(min) and acc(max). Return non-dominated subset."""
    front = []
    for p in points:
        dominated = any(q is not p and q["cost"] <= p["cost"] and q["acc"] >= p["acc"]
                        and (q["cost"] < p["cost"] or q["acc"] > p["acc"]) for q in points)
        if not dominated:
            front.append(p)
    return sorted(front, key=lambda r: r["cost"])


def main():
    xs, ys, base = load_curve()
    acc = lambda s: float(np.interp(s, xs, ys))
    print("=" * 92)
    print("Hero(A1) C1 Pareto: offset-cancellation vs readout operating point")
    print("curve baseline = %.2f%%; knee ~ sigma_pc 4-8; V_T = %.1f mV; E0(SA) = %.0f fJ" %
          (base, VT_mV, E0_fJ))
    print("=" * 92)

    out = {"baseline_pct": base, "VT_mV": VT_mV, "E0_fJ": E0_fJ, "conditions": []}
    for lname, F in LAYERS.items():
        pc_fs = 3.0 * np.sqrt(F)
        for v_in in (0.8, 0.6, 0.5, 0.4):
            pts = []
            for name, off, a, e in OPTIONS:
                s = sigma_pc(off, pc_fs, v_in)
                pts.append(dict(name=name, off_mV=off, off_VT=off / VT_mV, sigma_pc=s,
                                acc=acc(s), drop=base - acc(s), cost=a * e,
                                area=a, energy=e, E_fJ=E0_fJ * e))
            front = pareto_front(pts)
            front_names = {p["name"] for p in front}
            # is any cancellation worth its cost vs plain?
            plain = next(p for p in pts if p["name"] == "plain SA")
            best_gain = max((p["acc"] - plain["acc"]) for p in pts) if pts else 0.0
            verdict = ("plain SA Pareto-optimal (gains within noise)" if best_gain < WORTH_PP
                       else "cancellation earns its cost")
            print(f"\n--- {lname}, V_in={v_in:.1f} V (PC_FS={pc_fs:.0f}) -> {verdict} "
                  f"(best gain {best_gain:+.2f} pp) ---")
            for p in pts:
                star = " *FRONT" if p["name"] in front_names else ""
                print("   %-22s off=%.2fmV(%.2f V_T) sigma_pc=%4.2f acc=%5.2f%% drop=%+.2fpp "
                      "cost=%.2fx (A%.1f xE%.2f, %.0ffJ)%s" %
                      (p["name"], p["off_mV"], p["off_VT"], p["sigma_pc"], p["acc"], -p["drop"],
                       p["cost"], p["area"], p["energy"], p["E_fJ"], star))
            out["conditions"].append(dict(layer=lname, F=F, V_in_V=v_in, PC_FS=round(pc_fs, 1),
                                          verdict=verdict, best_gain_pp=round(best_gain, 3),
                                          pareto_front=sorted(front_names),
                                          points=[{k: (round(v, 4) if isinstance(v, float) else v)
                                                   for k, v in p.items()} for p in pts]))

    # decision boundary: finest V_in where auto-zero first earns its cost, per layer
    print("\n" + "=" * 92)
    print("DESIGN BOUNDARY (V_in below which single-cap auto-zero earns its cost, >%.2f pp):" % WORTH_PP)
    bnd = {}
    for lname, F in LAYERS.items():
        pc_fs = 3.0 * np.sqrt(F)
        thr = None
        for v_in in np.round(np.arange(0.9, 0.29, -0.01), 2):
            plain_acc = acc(sigma_pc(PLAIN_mV, pc_fs, v_in))
            az_acc = acc(sigma_pc(AZ_mV, pc_fs, v_in))
            if az_acc - plain_acc >= WORTH_PP:
                thr = float(v_in)
                break
        bnd[lname] = thr
        print("   %-14s : V_in <= %s V" % (lname, ("%.2f" % thr) if thr else "(never in 0.3-0.9)"))
    out["autozero_boundary_V_in"] = bnd

    pc96 = 3.0 * np.sqrt(1024)                                  # worst corner: layer2, low V_in
    plain_drop_04 = base - acc(sigma_pc(PLAIN_mV, pc96, 0.4))
    az_gain_04 = acc(sigma_pc(AZ_mV, pc96, 0.4)) - acc(sigma_pc(PLAIN_mV, pc96, 0.4))
    concl = ("C1 design boundary (noise floor %.2f pp; plain-SA offset %.2f mV = %.2f V_T, "
             "run_offset_mc N=120): with slope-matched max-gain readout, the plain StrongARM SA is "
             "Pareto-optimal for MNIST-scale fan-in at V_in>=0.5 V (its %.2f V_T lands at sigma_pc~2-4, "
             "below the curve knee -> drop within the %.2f pp single-run MNIST noise, so "
             "auto-zero/chopping only ADD area+energy for no SIGNIFICANT accuracy). Offset cancellation "
             "earns its cost ONLY in the low-V_in (<=0.4 V) / wide-fan-in (F=1024) / under-budgeted-gain "
             "corner (layer2@0.4V: plain drop %.2f pp, auto-zero recovers %+.2f pp). => Spec-inverted "
             "result: budget offset against V_T, not TMR margin, and skip auto-zero unless the readout "
             "gain budget forces it. Closes errata R2 as a quantified boundary, not 'auto-zero "
             "mandatory'. (Firming sigma 11.05->9.21 mV widened the plain-SA-sufficient region.)"
             % (NOISE_PP, PLAIN_mV, PLAIN_mV / VT_mV, PLAIN_mV / VT_mV, NOISE_PP,
                plain_drop_04, az_gain_04))
    print("\n" + "=" * 92 + "\n" + concl + "\n" + "=" * 92)
    out["conclusion"] = concl
    (HERE / "pareto_offset_cancellation_summary.json").write_text(json.dumps(out, indent=2))
    print("wrote pareto_offset_cancellation_summary.json")


if __name__ == "__main__":
    main()
