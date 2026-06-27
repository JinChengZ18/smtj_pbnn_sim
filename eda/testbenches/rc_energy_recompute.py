#!/usr/bin/env python3
"""Plan 2.5 (errata R6/R5): honest RC-vs-digital-ESN energy with the GROUNDED ADC readout.

The Chapter-5 headline is "sMTJ-RC ~38x more energy-efficient than a digital ESN" (experiment 16:
sMTJ-RC 270.9 nJ vs digital ESN 10204 nJ per 1000-step inference at the CANONICAL config N=100,
ensemble=96, dt=25 ns). But ppa/reservoir_energy.py bills the readout as a trained int8-MAC plus a
5 fJ sense -- it OMITS the analog->digital ADC that 2.3/2.4 showed gates RC and is comparator-bound.
This recompute adds the grounded SAR ADC (E_adc(b)=b*E_comp+2^b*E_capDAC, E_comp=48 fJ from the
EXTRACTED sky130 StrongARM SA, sa_postlayout.py) and reports the honest ratio.

Config is the Ch5 canonical one (found in experiments/16_rc_hardware_ppa.py). Honesty: ratios;
E_comp extracted, E_capDAC/E_dev order-of-magnitude; the ADC reads M of N nodes/step (per-node M=N
vs column-shared M=N/4).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from smtj_pbnn_sim.ppa import (ReservoirHW, default_28nm, smtj_rc_step_energy,        # noqa: E402
                               smtj_rc_inference_energy, digital_esn_inference_energy)

# Ch5 canonical config (experiments/16_rc_hardware_ppa.py)
N, ENS, L, DT = 100, 96, 1000, 25e-9
# grounded SAR ADC (2.4): comparator = extracted sky130 SA
E_COMP, E_CAPDAC0 = 48e-15, 1.1e-15


def e_adc(b):
    return b * E_COMP + E_CAPDAC0 * (2 ** b)


def main():
    tech = default_28nm()
    hw = ReservoirHW(n_nodes=N, ensemble=ENS, dt=DT)
    bd = smtj_rc_step_energy(hw, tech)
    e_rc = smtj_rc_inference_energy(hw, tech, L)
    e_dig = digital_esn_inference_energy(N, tech, L, memory="sram_cim", digital_mac=True)
    ratio0 = e_dig / e_rc

    print("=" * 90)
    print("Plan 2.5: honest RC-vs-ESN energy with grounded ADC readout (Ch5 config N=%d, ens=%d, L=%d)"
          % (N, ENS, L))
    print("=" * 90)
    print("baseline (reservoir_energy.py, NO ADC):")
    print("  per-step breakdown (pJ): " + ", ".join("%s=%.3f" % (k, v * 1e12) for k, v in bd.items()))
    print("  e_rc = %.1f nJ   e_dig(ESN,1pJ MAC) = %.0f nJ   -> ratio %.0fx" %
          (e_rc * 1e9, e_dig * 1e9, ratio0))
    print("-" * 90)
    print("add grounded SAR ADC (E_comp=48fJ extracted SA): readout digitizes M of N nodes/step")
    print("  M-mode        b   E_adc/conv   E_adc/infer   e_rc+ADC    honest ratio   advantage kept")
    rows = []
    for mtag, M in (("per-node M=N", N), ("col-shared M=N/4", N // 4)):
        for b in (6, 8, 10):
            e_adc_inf = M * L * e_adc(b)
            e_rc_g = e_rc + e_adc_inf
            ratio = e_dig / e_rc_g
            print("  %-14s %2d   %7.0ffJ   %8.1f nJ   %7.1f nJ   %8.1fx     %.0f%%" %
                  (mtag, b, e_adc(b) * 1e15, e_adc_inf * 1e9, e_rc_g * 1e9, ratio,
                   ratio / ratio0 * 100))
            rows.append(dict(M_mode=mtag, M=M, b=b, e_adc_conv_fJ=round(e_adc(b) * 1e15, 1),
                             e_adc_infer_nJ=round(e_adc_inf * 1e9, 2), e_rc_grounded_nJ=round(e_rc_g * 1e9, 2),
                             honest_ratio=round(ratio, 1), frac_of_baseline=round(ratio / ratio0, 3)))

    # representative honest point: column-shared 8-bit
    rep = next(r for r in rows if r["M_mode"].startswith("col") and r["b"] == 8)
    concl = ("Plan 2.5: the ~%.0fx RC-vs-digital-ESN advantage SURVIVES the grounded readout. "
             "reservoir_energy.py omitted the analog->digital ADC; adding the grounded SAR (comparator "
             "= extracted 48 fJ sky130 SA) lowers the ratio from %.0fx to ~%.0f-%.0fx depending on "
             "readout (per-node 8-bit -> %.0fx; column-shared 8-bit -> %.0fx). The advantage is robust "
             "because the digital ESN's O(N^2) matmul (%.1f uJ) dwarfs even the grounded RC readout. "
             "=> honest Ch5 claim: ~30-35x (not 38x); and reservoir_energy.py should carry a real ADC "
             "term (column-shared moderate-res, per 2.4). Closes errata R6 quantitative side / refines "
             "R5 RC end-to-end. Honesty: E_comp extracted, E_capDAC/E_dev order-of-mag; ratios."
             % (ratio0,
                ratio0,
                min(r["honest_ratio"] for r in rows),
                max(r["honest_ratio"] for r in rows),
                next(r["honest_ratio"] for r in rows if r["M_mode"].startswith("per") and r["b"] == 8),
                rep["honest_ratio"], e_dig * 1e6))
    print("\n" + "=" * 90 + "\n" + concl + "\n" + "=" * 90)
    out = dict(config=dict(N=N, ensemble=ENS, L=L, dt_ns=DT * 1e9),
               baseline=dict(e_rc_nJ=round(e_rc * 1e9, 2), e_dig_nJ=round(e_dig * 1e9, 1),
                             ratio=round(ratio0, 1),
                             step_breakdown_pJ={k: round(v * 1e12, 4) for k, v in bd.items()}),
               grounded=rows, representative=rep, conclusion=concl)
    (Path(__file__).resolve().parent / "rc_energy_recompute_summary.json").write_text(json.dumps(out, indent=2))
    print("wrote rc_energy_recompute_summary.json")


if __name__ == "__main__":
    main()
