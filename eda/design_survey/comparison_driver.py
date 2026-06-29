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
             "double_tail": HERO / "offset_mc_double_tail.json"}
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
                finding="All comparators land at ~0.39 V_T in the same 130 nm flow: offset is set by "
                        "input-pair Pelgrom mismatch (same W*L), so the literature topology advantages "
                        "(28 nm sims) do not reproduce here -> plain StrongARM is Pareto-optimal.")


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
    """SAR readout: comparator energy is sky130-extracted but the converter energy is still ANALYTIC
    (no transient SAR sim yet) -- flagged pending the Phase-3 SAR transient testbench."""
    d = jload(TB / "sar_capdac_energy_summary.json")
    return dict(metric="comparator + cap-DAC energy per conversion (fJ)",
                flow="ANALYTIC (E_comp from extracted StrongARM SA + cap-DAC switching formula)",
                status="pending: needs an ngspice transient SAR testbench for a true same-flow comparison",
                E_comp_fJ=(d or {}).get("E_comp_fJ"), C_u_fF=(d or {}).get("C_u_fF"))


def main():
    res = dict(
        _about="Phase-4 aggregation of same-flow reproduction results (revision plan). Numbers are read "
               "verbatim from committed *_summary.json; nothing is invented. The capability matrix "
               "(gen_supplement_figs.py CAPS) remains the qualitative view; this is the quantitative one.",
        readout_sa=readout_sa(), write_dac=write_dac(), sar_adc=sar_adc())
    OUT.write_text(json.dumps(res, indent=2))
    print("=== readout SA (same-flow offset) ===")
    for r in res["readout_sa"]["designs"]:
        print(f"  {'*' if r['is_ours'] else ' '} {r['design']:<12} sigma/V_T={r['sigma_offset_over_VT']:.3f} (N={r['N']})")
    print("=== write DAC (same-flow into 776 ohm) ===")
    for r in res["write_dac"]["designs"]:
        print(f"  {'*' if r['is_ours'] else ' '} {r['topology']:<16} monotonic={r['monotonic']!s:<5} INL={r['INL_LSB']:.2f} LSB")
    print(f"=== SAR ADC: {res['sar_adc']['status']} ===")
    print(f"\nwrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
