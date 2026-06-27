#!/usr/bin/env python3
"""Hero (A1) B5: readout transimpedance maps SA offset (mV) -> popcount -> accuracy.

Closes the LAST gap in the Hero loop. Three upstream numbers, three different units:
  * LSB_I = 5.10 uA / popcount      (P3 diff_column.py, ngspice-verified)
  * sigma_offset_V = 9.21 mV        (run_offset_mc.py N=120, sky130 StrongARM, = 0.39 V_T)
  * per-column accuracy curve       (hero_mnist_sweep.py: sigma_popcount -> acc)
The first is current, the second volts, the third popcounts. The current-sense
readout's transimpedance R_TI is the bridge:
    LSB_V = LSB_I * R_TI            [volts / popcount]
so the SA's input-referred offset is a popcount-domain decision-threshold error
    sigma_pc = sigma_offset_V / LSB_V.
Feed sigma_pc into the measured per-column curve -> accuracy. End to end, in one place.

CO-DESIGN LAW (the contribution, not "we added a CSA"): make R_TI as LARGE as the
column dynamic range allows -- the full-scale popcount PC_FS must not saturate the SA
differential input range V_in:
    PC_FS * LSB_V <= V_in / 2   ->   LSB_V* = V_in / (2 * PC_FS)     (max usable gain)
    => sigma_pc = sigma_offset_V * 2 * PC_FS / V_in.
Wider fan-in (larger PC_FS) or a smaller SA input range makes the SAME mV offset cost
MORE popcounts. The non-obvious payoff: at max gain the plain SA's 0.39 V_T lands at only
~2-3 popcount (curve tolerates it); but an under-budgeted readout (gain backed off for
headroom) or a small V_in pushes sigma_pc past the curve's knee (~4-8 pc) and costs
accuracy -- so the readout gain budget, not just the SA, sets the loss. Auto-zero / larger
SA area buy the headroom to relax the gain.

PC_FS is fan-in driven: popcount = sum_F (+-1)(+-1) ~ N(0, F), so PC_FS ~ 3*sqrt(F).
  layer 1 (F=784):  3*sqrt(784)  = 84
  layer 2 (F=1024): 3*sqrt(1024) = 96

Caveats (must appear in the paper): linear-transimpedance first-cut; BatchNorm reference
assumed ideal; PC_FS and V_in are design parameters (swept here); AVT is a sky130-class
assumption -> ratios (sigma/V_T, popcount) transfer, not absolute mV.

Run: python eda/hero/readout_mapping.py        (pure Python; ingests upstream JSON)
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

LSB_I_uA = 5.102                 # P3: (Vr/2)*(G_P - G_AP), ngspice-verified
VT_mV = 23.414

# SA input-referred offset variants:
#   plain  = measured (run_offset_mc.py, N=120 MC -> sigma=9.21 mV; the earlier N=24 gave 11.05 mV,
#            small-sample-high; firmed SE ~0.6 mV)
#   4x area= Pelgrom 1/sqrt(area): 4x input-pair area -> sigma/2
#   autozero = cited prior-art residual target (switched-cap auto-zero/chopper,
#            ISSCC-2018-class), << V_T -- a design TARGET, not measured here.
OFFSET_VARIANTS_mV = {
    "plain SA (1x)":       9.21,
    "4x input-pair area":  9.21 / 2.0,
    "auto-zero (target)":  1.5,
}

# fan-in -> full-scale popcount (3 sigma of the +-1 random-walk sum)
LAYERS = {"layer1 (F=784)": 784, "layer2 (F=1024)": 1024}


def load_curve():
    p = REPO / "eda" / "interface" / "hero_mnist_summary.json"
    d = json.loads(p.read_text())
    sweep = sorted(d["per_column_sweep"], key=lambda r: r["sigma_popcount"])
    xs = np.array([r["sigma_popcount"] for r in sweep])
    ys = np.array([r["acc_pct"] for r in sweep])
    base = d.get("acc_at_offset0_pct", float(ys[0]))
    return xs, ys, base


def acc_at(sigma_pc, xs, ys):
    return float(np.interp(sigma_pc, xs, ys))   # clamps outside the measured range


def main():
    xs, ys, base = load_curve()
    print(f"per-column curve loaded: sigma_pc {xs.min():.0f}..{xs.max():.0f} -> "
          f"acc {ys.max():.2f}..{ys.min():.2f}% (baseline {base:.2f}%)")
    print(f"LSB_I = {LSB_I_uA:.2f} uA/popcount (P3); V_T = {VT_mV:.1f} mV\n")

    V_in_range = [0.6, 0.4]          # StrongARM differential usable input swing [V]
    rows = []
    for lname, F in LAYERS.items():
        pc_fs = 3.0 * np.sqrt(F)
        for v_in in V_in_range:
            lsb_v_mV = v_in / (2.0 * pc_fs) * 1e3            # max-gain volts/popcount
            r_ti = (lsb_v_mV * 1e-3) / (LSB_I_uA * 1e-6)     # transimpedance [ohm]
            print(f"--- {lname}: PC_FS={pc_fs:.0f},  V_in={v_in:.1f} V  ->  "
                  f"LSB_V*={lsb_v_mV:.2f} mV/pc,  R_TI={r_ti:.0f} ohm (max gain) ---")
            for vname, off_mV in OFFSET_VARIANTS_mV.items():
                sigma_pc = off_mV / lsb_v_mV
                acc = acc_at(sigma_pc, xs, ys)
                drop = base - acc
                print(f"    {vname:<22} sigma_offset={off_mV:5.2f} mV ({off_mV/VT_mV:4.2f} V_T)"
                      f"  ->  sigma_pc={sigma_pc:4.2f}  acc={acc:5.2f}%  (drop {drop:+.2f} pp)")
                rows.append(dict(layer=lname, F=F, PC_FS=round(float(pc_fs), 1),
                                 V_in_V=v_in, LSB_V_mV_per_pc=round(lsb_v_mV, 3),
                                 R_TI_ohm=round(float(r_ti), 1), variant=vname,
                                 sigma_offset_mV=off_mV,
                                 sigma_offset_over_VT=round(off_mV / VT_mV, 3),
                                 sigma_pc=round(float(sigma_pc), 3),
                                 acc_pct=round(acc, 3),
                                 drop_pp=round(float(base - acc), 3)))
            print()

    summ = dict(LSB_I_uA_per_pc=LSB_I_uA, VT_mV=VT_mV, baseline_acc_pct=base,
                offset_variants_mV=OFFSET_VARIANTS_mV, rows=rows,
                law="sigma_pc = sigma_offset_V * 2*PC_FS / V_in  (max-gain transimpedance)",
                note=("Bridges run_offset_mc (mV) -> P3 LSB_I (uA/pc) -> hero per-column "
                      "accuracy curve. Max-gain readout keeps plain SA near baseline "
                      "(sigma_pc~3-4); small V_in / wide fan-in / under-budgeted gain push "
                      "past the curve knee; auto-zero & SA area buy headroom. First-cut: "
                      "linear transimpedance, ideal BN reference, PC_FS=3*sqrt(F)."))
    (HERE / "readout_mapping_summary.json").write_text(json.dumps(summ, indent=2))

    # headline
    plain_worst = max(r["drop_pp"] for r in rows if r["variant"].startswith("plain"))
    az_worst = max(r["drop_pp"] for r in rows if r["variant"].startswith("auto-zero"))
    print(f"HEADLINE: at dynamic-range-max transimpedance, plain SA worst-case drop "
          f"= {plain_worst:.2f} pp; auto-zero worst-case = {az_worst:.2f} pp.")
    print("Loop closed: extracted SA mV -> R_TI -> popcount -> MNIST accuracy.")
    print("wrote readout_mapping_summary.json")


if __name__ == "__main__":
    main()
