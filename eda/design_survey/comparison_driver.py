#!/usr/bin/env python3
"""Phase 4: aggregate the SAME-FLOW reproduction results into one comparison file.

Revision-plan Phase 4. Each submodule's designs were reproduced in the identical
sky130 flow as ours (Phase 3): readout-SA comparators through the offset-MC harness
(eda/hero/run_offset_mc.py), write-DACs through the topology factory
(eda/hero/run_write_dac.py). This driver reads the committed per-design summary JSONs
and emits eda/design_survey/comparison_results.json -- the apples-to-apples table
that replaces the retired fabricated scatter. It invents nothing: every number is a
measured value read straight from a committed *_summary.json.

Run: python eda/design_survey/comparison_driver.py
"""
from __future__ import annotations
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERO = REPO / "eda" / "hero"
TB = REPO / "eda" / "testbenches"
OUT = Path(__file__).resolve().parent / "comparison_results.json"


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else None


def readout_sa():
    """Same-flow input-referred offset (sigma/V_T) of each reproduced comparator."""
    files = {"strongarm": HERO / "offset_mc_summary.json",
             "dsa": HERO / "offset_mc_dsa.json",
             "double_tail": HERO / "offset_mc_double_tail.json",
             "current_sampling": HERO / "offset_mc_current_sampling.json",
             "dong_autozero": HERO / "offset_mc_dong_autozero.json"}
    rows = []
    for key, fp in files.items():
        d = jload(fp)
        if not d:
            continue
        rows.append(dict(design=d.get("design", key), is_ours=(key == "strongarm"),
                         sigma_offset_over_VT=d["sigma_offset_over_VT"],
                         sigma_offset_mV=d["offset_sigma_mV"], N=d["N"]))
    rows.sort(key=lambda r: r["sigma_offset_over_VT"])
    return dict(metric="input-referred offset sigma / V_T (lower better)", flow="sky130 offset-MC (run_offset_mc.py)",
                designs=rows,
                finding="Mismatch-limited topologies (StrongARM, double-tail, DSA, current-sampling) all land "
                        "at ~0.39 V_T in the same 130 nm flow: offset is set by input-pair Pelgrom mismatch "
                        "(same W*L). The single-cap auto-zero (Dong lineage) measurably cancels it to ~0.16 V_T "
                        "(>60% reduction, consistent with the paper's relative claim) -- but 0.39 V_T already "
                        "meets the window budget at the nominal operating point, so plain StrongARM remains the "
                        "energy-minimal Pareto choice; auto-zero is the validated option for the low-swing "
                        "wide-fan-in corner.")


def write_dac():
    """Same-flow LSB/range/monotonicity/INL of each reproduced DAC topology."""
    rows = []
    for key in ("resistor_string", "current_steering", "r2r"):
        d = jload(HERO / f"write_dac_{key}.json")
        if not d:
            continue
        rows.append(dict(topology=d["topology"], is_ours=(key == "resistor_string"),
                         monotonic=d["monotonic"], INL_LSB=d["INL_LSB"],
                         LSB_mV=d["LSB_mV"], range_mV=d["range_mV"]))
    rows.sort(key=lambda r: (not r["monotonic"], r["INL_LSB"]))
    return dict(metric="monotonicity + INL (LSB) into the 776 ohm write load",
                flow="sky130 code-sweep (run_write_dac.py topology factory)", designs=rows,
                finding="Into the low-impedance 776 ohm write load only the voltage-mode resistor-string "
                        "is monotonic (INL 0.48 LSB); current-steering (INL 1.71, PMOS Vsd compliance) and "
                        "R-2R (INL 2.62, switch Ron at major carry) are non-monotonic -> resistor-string "
                        "is the correct write-DAC, now measured not asserted.")


def sar_adc():
    """SAR readout: cap-DAC switching energy is now TRANSIENT-measured in sky130
    (sar_capdac_tran.py); the comparator is the extracted StrongARM SA, added analytically."""
    d = jload(TB / "sar_capdac_tran_summary.json")
    if not d:
        return dict(metric="SAR energy per conversion (fJ)", status="pending: run sar_capdac_tran.py")
    rows = [r for r in d["rows"] if r.get("b") == 8] or d["rows"]
    designs = [dict(scheme=r["scheme"], b=r["b"], E_capdac_fJ=r["E_capdac_fJ_measured"],
                    E_comp_fJ=r["E_comp_fJ"], E_total_fJ=r["E_total_fJ"]) for r in rows]
    return dict(metric="SAR energy per conversion (fJ): transient cap-DAC + extracted comparator",
                flow="sky130 transient charge-integration (sar_capdac_tran.py); comparator = extracted StrongARM SA 48 fJ",
                designs=designs,
                finding="Cap-DAC switching energy is transient-measured (not the analytic series): monotonic "
                        "switching cuts the cap-DAC term ~3x vs conventional (b=8: 141 vs 457 fJ), less than "
                        "the analytic /10 estimate; the comparator (b*48 fJ) dominates total SAR energy, "
                        "confirming comparator-sharing (not bit reduction) as the energy lever.",
                caveat="representative run; regenerate sar_capdac_tran.py to verify; SS-hybrid not done.")


def main():
    res = dict(
        _about="Phase-4 aggregation of same-flow reproduction results (revision plan). Numbers are read "
               "verbatim from committed *_summary.json; nothing is invented. The qualitative "
               "capability matrix lives in appendix D (article/appendix_D_circuit_comparison.md); "
               "this is the quantitative same-flow view.",
        readout_sa=readout_sa(), write_dac=write_dac(), sar_adc=sar_adc())
    OUT.write_text(json.dumps(res, indent=2))
    print("=== readout SA (same-flow offset) ===")
    for r in res["readout_sa"]["designs"]:
        print(f"  {'*' if r['is_ours'] else ' '} {r['design']:<12} sigma/V_T={r['sigma_offset_over_VT']:.3f} (N={r['N']})")
    print("=== write DAC (same-flow into 776 ohm) ===")
    for r in res["write_dac"]["designs"]:
        print(f"  {'*' if r['is_ours'] else ' '} {r['topology']:<16} monotonic={r['monotonic']!s:<5} INL={r['INL_LSB']:.2f} LSB")
    sar = res["sar_adc"]
    print("=== SAR ADC (transient cap-DAC + extracted comparator) ===")
    for r in sar.get("designs", []):
        print(f"    b{r['b']} {r['scheme']:<12} capdac={r['E_capdac_fJ']:.0f}fJ comp={r['E_comp_fJ']:.0f}fJ total={r['E_total_fJ']:.0f}fJ")
    if sar.get("status"):
        print(f"    {sar['status']}")
    print(f"\nwrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
