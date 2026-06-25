#!/usr/bin/env python3
"""P6 interface (first-cut): inject EDA-extracted PPA numbers into smtj_pbnn_sim and
re-run the MNIST PPA -- the one-way bridge ("new interface").

Reads eda/extraction/peripheral_energy.yaml and recomputes per-MAC + MNIST-MLP energy
with the extracted values, comparing against the 28 nm-placeholder defaults. smtj_pbnn_sim
is NOT modified; values are injected one-way (the sim never imports eda/).

Currently only the WRITE energy is EDA-extracted (P2 first-cut, channel+driver). read/DAC/
counter remain placeholders pending sky130 (P4). Once P4 lands the ADC/sense numbers in the
same YAML, this script reports the big peripheral-fraction shift (errata R1) with no code change.

Run: python eda/interface/load_tech_params.py
"""
from __future__ import annotations
import json
from pathlib import Path

from smtj_pbnn_sim.ppa import tech_params, energy

HERE = Path(__file__).resolve().parent
EXTRACT = HERE.parent / "extraction" / "peripheral_energy.yaml"
MNIST = [(784, 1024), (1024, 1024), (1024, 10)]   # (in, out) per PBNN-MLP layer


def load_extract():
    """Tiny key: float parser (avoids a hard PyYAML dependency)."""
    d = {}
    for line in EXTRACT.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.split("#")[0].strip()
        try:
            d[k.strip()] = float(v)
        except ValueError:
            pass
    return d


def per_mac(e_dac, e_write, e_read, e_count):
    return e_dac + e_write + e_read + e_count


def mnist_energy(pm, T):
    return pm * sum(r * c for r, c in MNIST) * T


def main():
    ext = load_extract()
    tp = tech_params.default_28nm()
    pm_def = energy.per_mac_energy(tp)                 # placeholders + Ohmic write
    e_write_ext = ext.get("e_smtj_write", tp.e_smtj_write)
    e_read = ext.get("e_smtj_read", tp.e_smtj_read)
    e_dac = ext.get("e_dac_step", tp.e_dac_step)
    e_cnt = ext.get("e_count_inc", tp.e_count_inc)
    pm_ext = per_mac(e_dac, e_write_ext, e_read, e_cnt)

    print(f"per-MAC energy:  default {pm_def*1e15:6.1f} fJ  ->  extracted {pm_ext*1e15:6.1f} fJ "
          f"({100*(pm_ext-pm_def)/pm_def:+.1f}%)")
    print(f"  write : {tp.e_smtj_write*1e12:.3f} pJ (Ohmic)  ->  {e_write_ext*1e12:.3f} pJ "
          f"(P2 +driver)   write fraction {100*e_write_ext/pm_ext:.1f}%")
    print(f"  read/DAC/counter: still 28nm placeholders ({(e_read+e_dac+e_cnt)*1e15:.1f} fJ, "
          f"{100*(e_read+e_dac+e_cnt)/pm_ext:.1f}% of per-MAC) -- await sky130 (P4)")
    rows = []
    for T in (4, 8):
        Ed, Ee = mnist_energy(pm_def, T), mnist_energy(pm_ext, T)
        print(f"  MNIST PPA T={T}: default {Ed*1e6:.3f} uJ -> extracted {Ee*1e6:.3f} uJ "
              f"({100*(Ee-Ed)/Ed:+.1f}%)")
        rows.append(dict(T=T, default_uJ=Ed * 1e6, extracted_uJ=Ee * 1e6))

    summ = dict(per_mac_default_fJ=pm_def * 1e15, per_mac_extracted_fJ=pm_ext * 1e15,
                e_write_extracted_pJ=e_write_ext * 1e12,
                write_fraction_pct=100 * e_write_ext / pm_ext,
                extracted_fields=["e_smtj_write"],
                pending_sky130=["e_smtj_read", "e_dac_step", "e_count_inc (P4/R1)"],
                mnist=rows)
    (HERE / "interface_summary.json").write_text(json.dumps(summ, indent=2))
    print("\nNOTE: only the write energy is EDA-extracted (P2). Once P4 lands the sky130 "
          "ADC/sense\nnumbers in peripheral_energy.yaml, this same script reports the "
          "peripheral-fraction shift (R1).")


if __name__ == "__main__":
    main()
