#!/usr/bin/env python3
"""P6 interface (first-cut): inject EDA-extracted PPA numbers into smtj_pbnn_sim and
re-run the MNIST PPA -- the one-way bridge ("new interface").

Reads eda/extraction/peripheral_energy.yaml and recomputes per-MAC + MNIST-MLP energy
with the extracted values, comparing against the 28 nm-placeholder defaults. smtj_pbnn_sim
is NOT modified; values are injected one-way (the sim never imports eda/).

The READ energy (sky130 StrongARM SA, 48 fJ) and the channel+driver WRITE energy are now
EDA-grounded; the read value is folded into the simulator default (ppa/tech_params), so the sim
is independently credible. This script audits the legacy-placeholder -> grounded shift (errata
R1) against an explicit 28 nm baseline; DAC/counter remain sky130-pending.

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
    tp = tech_params.default_28nm()                    # current default: sky130-grounded read
    tp_legacy = tech_params.TechParams(e_smtj_read=5.0e-15)  # historical 28 nm read placeholder
    pm_def = energy.per_mac_energy(tp_legacy)          # legacy 28 nm placeholders + Ohmic write
    e_write_ext = ext.get("e_smtj_write", tp.e_smtj_write)
    e_read = ext.get("e_smtj_read", tp.e_smtj_read)
    e_dac = ext.get("e_dac_step", tp.e_dac_step)
    e_cnt = ext.get("e_count_inc", tp.e_count_inc)
    pm_ext = per_mac(e_dac, e_write_ext, e_read, e_cnt)

    print(f"per-MAC energy:  default {pm_def*1e15:6.1f} fJ  ->  extracted {pm_ext*1e15:6.1f} fJ "
          f"({100*(pm_ext-pm_def)/pm_def:+.1f}%)")
    print(f"  write : {tp.e_smtj_write*1e12:.3f} pJ (Ohmic)  ->  {e_write_ext*1e12:.3f} pJ "
          f"(P2 +driver)   write fraction {100*e_write_ext/pm_ext:.1f}%")
    print(f"  read  : {tp_legacy.e_smtj_read*1e15:.1f} fJ (legacy 28nm)  ->  {e_read*1e15:.1f} fJ "
          f"(sky130 StrongARM SA, now sim default)   read fraction {100*e_read/pm_ext:.1f}%")
    print(f"  DAC/counter: still 28nm placeholders ({(e_dac+e_cnt)*1e15:.1f} fJ, "
          f"{100*(e_dac+e_cnt)/pm_ext:.1f}% of per-MAC) -- await sky130 DAC")
    rows = []
    for T in (4, 8):
        Ed, Ee = mnist_energy(pm_def, T), mnist_energy(pm_ext, T)
        print(f"  MNIST PPA T={T}: default {Ed*1e6:.3f} uJ -> extracted {Ee*1e6:.3f} uJ "
              f"({100*(Ee-Ed)/Ed:+.1f}%)")
        rows.append(dict(T=T, default_uJ=Ed * 1e6, extracted_uJ=Ee * 1e6))

    summ = dict(per_mac_default_fJ=pm_def * 1e15, per_mac_extracted_fJ=pm_ext * 1e15,
                e_write_extracted_pJ=e_write_ext * 1e12,
                write_fraction_pct=100 * e_write_ext / pm_ext,
                e_read_extracted_fJ=e_read * 1e15, read_fraction_pct=100 * e_read / pm_ext,
                extracted_fields=["e_smtj_write", "e_smtj_read"],
                pending_sky130=["e_dac_step", "e_count_inc"],
                mnist=rows)
    (HERE / "interface_summary.json").write_text(json.dumps(summ, indent=2))
    print("\nNOTE: write (channel+driver) and read (sky130 StrongARM SA) are now EDA-grounded; the "
          "read\nupdate moves the write fraction 98.7%->93.8% (read 0.6%->5.6%). DAC/counter remain "
          "28nm\nplaceholders; a column-shared multi-bit ADC (if added downstream) would raise the "
          "peripheral\nfraction further.")


if __name__ == "__main__":
    main()
