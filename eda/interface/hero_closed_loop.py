#!/usr/bin/env python3
"""Hero closed-loop infrastructure (Tier-A / C1): readout SA offset -> accuracy.

The Hero claim: a sense-amp input-referred offset is a per-column V_th shift in
disguise -- exactly the error class Exp.08 finds DOMINANT (V_th D2D sigma_rel=20%
-> 97.5%->92.8%, while V_T/C2C/back-hopping are benign). So the readout-circuit
spec is set by the device's OWN sigmoid scale V_T=23.4mV, not a TMR margin.

This script is the CLOSED-LOOP plumbing that ties the EDA-extracted SA offset to
the simulator's accuracy:
  * it wires the new `sigma_sense_offset_V` channel just added to device/variation.py
    (errata R2), so a Phase-1 MNIST run injects the extracted offset distribution;
  * it computes the device-physics side now (offset/V_T -> systematic p_sw decision
    shift), giving the offset BUDGET, and maps it onto Exp.08's measured V_th
    sensitivity as a FIRST-CUT accuracy-recovery curve.

The FINAL hero figure regenerates the accuracy curve by running the full-stack PBNN
MNIST eval with `VariationConfig(sigma_sense_offset_V=...)` swept (Phase 1, once a
checkpoint + the sky130 SA's extracted offset exist). Recipe printed below.

Run: python eda/interface/hero_closed_loop.py     (pure Python; reuses smtj_pbnn_sim)
"""
from __future__ import annotations
import json
from pathlib import Path

import sys

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))        # use the local (worktree) src
from smtj_pbnn_sim.device.variation import VariationConfig, VariationSampler  # noqa: E402

HERE = Path(__file__).resolve().parent
VTH_NOM, VT_NOM = 0.895783, 0.023414      # calibrated operating point
# Exp.08 measured V_th-D2D sensitivity anchors (docs/experiment_findings.md):
# accuracy(sigma_rel(V_th)): 0% -> 97.5%, 20% -> 92.8% (V_th shift is THE bottleneck).
EXP08 = [(0.00, 97.5), (0.20, 92.8)]


def psw(V):
    return 1.0 / (1.0 + np.exp(-(V - VTH_NOM) / VT_NOM))


def decision_shift(offset_V):
    """Systematic p_sw shift at the 50% operating point from an SA offset [V].
    The SA offset shifts the read decision by offset/V_T in sigmoid argument."""
    return psw(VTH_NOM + offset_V) - 0.5         # signed shift from p=0.5


def acc_from_vth_sigma(sigma_rel):
    """First-cut accuracy via Exp.08 V_th-D2D anchors (linear interp/extrap, monotone)."""
    xs = np.array([a for a, _ in EXP08]); ys = np.array([b for _, b in EXP08])
    return float(np.interp(sigma_rel, xs, ys, right=ys[-1] + (sigma_rel - xs[-1]) * (ys[-1] - ys[0]) / (xs[-1] - xs[0])))


def main():
    # (1) verify the new sigma_sense_offset_V channel is wired into the device layer
    cfg = VariationConfig(mode="sigmoid_direct", sigma_V_th_rel=0.0, sigma_V_T_rel=0.0,
                          sigma_sense_offset_V=0.010, seed=1)
    f = VariationSampler(cfg).sample((4096,), V_th_nom=VTH_NOM, V_T_nom=VT_NOM,
                                     R_P_nom=4900.0, TMR_nom=1.0)
    got = float(np.std(np.asarray(f.V_th) - VTH_NOM))
    print(f"[channel check] sigma_sense_offset_V=10mV -> measured V_th-shift std = "
          f"{got*1e3:.2f} mV  ({'OK' if abs(got-0.010) < 5e-4 else 'CHECK'})")

    # (2) device-physics: offset/V_T -> systematic decision shift + the offset budget
    print("\noffset[mV]  offset/V_T   |Δp_sw|   sigma_rel(V_th)_equiv   acc(first-cut)")
    rows = []
    for off_mV in (0, 5, 7, 10, 15, 20, 23.4, 30):
        off = off_mV * 1e-3
        dp = abs(decision_shift(off))
        # an SA offset = a V_th shift of `off`; expressed in Exp.08's sigma_rel(V_th) units
        sig_rel = off / VTH_NOM
        acc = acc_from_vth_sigma(sig_rel)
        print(f"  {off_mV:5.1f}     {off/VT_NOM:5.2f}      {dp:5.3f}        "
              f"{sig_rel*100:5.2f}%               {acc:5.2f}%")
        rows.append(dict(offset_mV=off_mV, offset_over_VT=off / VT_NOM,
                         dp_sw=dp, sigma_rel_vth=sig_rel, acc_firstcut=acc))

    # budget: largest offset keeping |Δp_sw| < 0.15 (i.e. <15% per-column decision bias)
    budget = max((r["offset_mV"] for r in rows if r["dp_sw"] < 0.15), default=0)
    summ = dict(VT_mV=VT_NOM * 1e3, channel_wired=abs(got - 0.010) < 5e-4,
                exp08_anchors=EXP08, offset_budget_mV_for_dp_lt_0p15=budget, rows=rows,
                note=("First-cut: device-physics decision shift is exact; accuracy via Exp.08 "
                      "V_th-D2D anchors (sense offset = per-column V_th shift). FINAL curve: run "
                      "full-stack PBNN MNIST with VariationConfig(sigma_sense_offset_V=...) swept."))
    (HERE / "hero_summary.json").write_text(json.dumps(summ, indent=2))

    print(f"\noffset budget (|Δp_sw|<0.15): SA input-referred offset <= ~{budget:.0f} mV "
          f"(~{budget/ (VT_NOM*1e3):.1f}*V_T).")
    print("Phase-1 final figure recipe:")
    print("  for off in offsets: train/load PBNN-MLP; evaluate FULL_STACK with")
    print("  VariationConfig(mode='sigmoid_direct', sigma_sense_offset_V=off); plot acc vs off/V_T.")
    print("  The extracted sky130 SA offset sigma (Hero MC) -> e_smtj_read + this curve = hero figure.")


if __name__ == "__main__":
    main()
