#!/usr/bin/env python3
"""Generate the golden reference for the smtj_sot.va regression (P1).

Self-contained (numpy only). Mirrors the calibrated compact model in
``src/smtj_pbnn_sim/device/arrhenius.py`` and ``device/telegraph.py`` so the
Verilog-A model's observables (V(psw), V(sinf), V(tau)) can be checked against
the SAME numbers the system-level simulator uses, and against the measured
46-point data shipped in ``data/smtj_psw_curves/measured_0p75ns.csv``.

Outputs (next to this script):
  golden_psw.csv      dense V sweep: V, psw, sinf, tau_ns   (the ngspice target)
  golden_summary.json R^2 of the sigmoid vs measured A/P->AP, and the 0.78 pJ check

Run:  python eda/testbenches/gen_golden.py
This needs no EDA tools; it produces the target the (later) ngspice run must match.
"""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path

import numpy as np

# ---- calibrated parameters (must match eda/models/smtj_sot.va defaults; errata N1) ----
VTH = 0.895783      # sigmoid center [V]
VT = 0.023414       # slope param 1/beta_s [V]   (beta_s = 42.71 V^-1)
DELTA = 4.91        # thermal stability factor
VC0 = 0.857         # zero-thermal critical voltage [V]
TAU0 = 1.0e-9       # attempt time [s]
RSOT = 776.0        # SOT channel resistance [ohm]
TW = 0.75e-9        # write pulse width [s]
VWR_NOM = 0.90      # nominal write voltage [V] for the energy check

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MEASURED = REPO / "data" / "smtj_psw_curves" / "measured_0p75ns.csv"


def psw_sigmoid(V):
    return 1.0 / (1.0 + np.exp(-(V - VTH) / VT))


def sinf(V):
    return np.tanh(DELTA * V / VC0)


def tau_ns(V):
    rup = (1.0 / TAU0) * np.exp(-DELTA * (1.0 - V / VC0))
    rdn = (1.0 / TAU0) * np.exp(-DELTA * (1.0 + V / VC0))
    return 1.0e9 / (rup + rdn)


def load_measured(device="A", direction="P->AP"):
    V, P = [], []
    if not MEASURED.exists():
        return np.array([]), np.array([])
    with open(MEASURED, newline="") as f:
        for row in csv.DictReader(f):
            if row["device_id"] == device and row["direction"] == direction:
                V.append(float(row["V"]))
                P.append(float(row["P_sw"]))
    order = np.argsort(V)
    return np.array(V)[order], np.array(P)[order]


def r2(y, yhat):
    y, yhat = np.asarray(y), np.asarray(yhat)
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def main():
    # dense sweep = the ngspice DC-sweep target
    Vsw = np.round(np.arange(0.80, 0.9701, 0.002), 4)
    rows = [(float(v), float(psw_sigmoid(v)), float(sinf(v)), float(tau_ns(v))) for v in Vsw]
    with open(HERE / "golden_psw.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["V", "psw", "sinf", "tau_ns"])
        w.writerows(rows)

    # validate the sigmoid against the measured 46-point data (Device A, P->AP)
    Vm, Pm = load_measured("A", "P->AP")
    rsq = r2(Pm, psw_sigmoid(Vm)) if Vm.size else None
    rmse = float(np.sqrt(np.mean((Pm - psw_sigmoid(Vm)) ** 2))) if Vm.size else None

    # physical write-energy check (Ohmic): E = V^2/R * t_w
    e_write = VWR_NOM ** 2 / RSOT * TW

    summary = {
        "params": {"Vth": VTH, "VT": VT, "beta_s": 1.0 / VT, "Delta": DELTA,
                   "Vc0": VC0, "tau0": TAU0, "Rsot": RSOT},
        "sigmoid_vs_measured_A_PtoAP": {
            "n_points": int(Vm.size), "R2": rsq, "RMSE": rmse,
            "pass_R2_ge_0p99": (rsq is not None and rsq >= 0.99),
        },
        "tau_zero_bias_ns": float(tau_ns(0.0)),     # ~ tau0*exp(Delta)/2 ~ 68 ns
        "sinf_at_0p1V": float(sinf(0.1)),
        "write_energy_pJ": e_write * 1e12,
        "write_energy_pass_0p78pJ": abs(e_write * 1e12 - 0.78) < 0.02,
        "sweep_rows": len(rows),
    }
    with open(HERE / "golden_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"golden_psw.csv: {len(rows)} rows  (V 0.80..0.97, observables psw/sinf/tau_ns)")
    if rsq is not None:
        print(f"sigmoid vs measured A/P->AP: n={Vm.size}  R^2={rsq:.4f}  RMSE={rmse:.4f}  "
              f"-> {'PASS' if summary['sigmoid_vs_measured_A_PtoAP']['pass_R2_ge_0p99'] else 'CHECK'}")
    else:
        print("measured CSV not found; sweep target still written")
    print(f"tau(0V) = {tau_ns(0.0):.1f} ns   write energy(0.9V,776ohm,0.75ns) = "
          f"{e_write*1e12:.3f} pJ -> {'PASS' if summary['write_energy_pass_0p78pJ'] else 'CHECK'}")


if __name__ == "__main__":
    main()
