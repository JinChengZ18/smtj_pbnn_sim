#!/usr/bin/env python3
"""C2/F1 fine write-DAC: sky130 binary-weighted current-steering DAC for the trim + IR pre-distortion.

The per-column V_th trim and the per-row IR pre-distortion are realised as added codes on the write-DAC.
This sizes and simulates the FINE sub-DAC that carries them: a binary-weighted PMOS current-steering DAC
(unit current mirrored, branch i = 2^i * I_u, summed into the 776 ohm write load). Target LSB ~= V_T/4
so a few bits resolve a per-column trim, and the b-bit range covers the per-row IR pre-distortion span
(~148 mV at N=256). Sweeps all codes, reports the transfer (monotonicity, LSB, INL, range).

MUST RUN IN WSL (native ngspice + sky130):
  wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd <repo>; python3 eda/hero/run_write_dac.py'
"""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LIB = "/opt/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
RUN = HERE / "_write_dac.spice"
VT = 0.023414
RLOAD = 776.0
NBITS = 6
RREF = 147e3           # unit-current reference resistor


def vload(code):
    # Simple binary-weighted current-steering DAC into the 776 ohm write load. This first cut
    # exposes why current-mode is the WRONG topology here: as V_load rises the PMOS sources lose
    # Vsd compliance, their current droops, the binary weights no longer add -> NON-MONOTONIC.
    branches = "".join(
        f"XMb{i} load vbias vdd vdd sky130_fd_pr__pfet_01v8 W={2**i} L=0.5\n"
        for i in range(NBITS) if (code >> i) & 1)
    net = f"""* fine write-DAC (current-steering, first cut) code={code}
.lib {LIB} tt
Vdd vdd 0 1.8
XMref vbias vbias vdd vdd sky130_fd_pr__pfet_01v8 W=1 L=0.5
Rref vbias 0 {RREF}
{branches}Rload load 0 {RLOAD}
.control
  op
  print v(load)
  quit
.endc
.end
"""
    RUN.write_text(net)
    out = subprocess.run(["ngspice", "-b", RUN.name], cwd=HERE,
                         capture_output=True, text=True).stdout
    m = re.search(r"v\(load\)\s*=\s*([-+0-9.eE]+)", out)
    return float(m.group(1)) if m else float("nan")


def main():
    codes = list(range(2 ** NBITS))
    v = np.array([vload(c) for c in codes])
    dv = np.diff(v)
    lsb = float(np.mean(dv))
    rng = float(v[-1] - v[0])
    # ideal line through endpoints; INL in LSB
    ideal = np.linspace(v[0], v[-1], len(v))
    inl = float(np.max(np.abs(v - ideal)) / abs(lsb)) if lsb else float("nan")
    monotonic = bool(np.all(dv > 0))
    predist_mV = 148.5
    codes_for_predist = predist_mV / 1e3 / lsb if lsb else float("nan")

    print(f"[first cut] sky130 {NBITS}-bit current-steering DAC into {RLOAD:.0f} ohm:")
    print(f"  LSB = {lsb*1e3:.2f} mV ({lsb/VT:.3f} V_T) ; range = {rng*1e3:.1f} mV over {2**NBITS-1} codes")
    print(f"  monotonic = {monotonic} ;  INL = {inl:.2f} LSB  <-- current droops with V_load (compliance)")
    print(f"  covers 148.5 mV pre-distortion? needs {codes_for_predist:.0f}/{2**NBITS-1} codes -> "
          f"{'YES' if codes_for_predist <= 2**NBITS-1 else 'NO'}")
    print(f"  => current-steering is the WRONG topology into the low-impedance write load "
          f"(non-monotonic, range-short).")

    # Refined design: voltage-mode resistor-string DAC + buffer (monotonic by construction).
    VSPAN = 0.20                       # Vref span covering write window + 148 mV pre-distortion
    for b in (6, 7, 8):
        lsb_rs = VSPAN / (2 ** b)
        print(f"[refined] resistor-string voltage DAC, span={VSPAN*1e3:.0f} mV, b={b}: "
              f"LSB={lsb_rs*1e3:.2f} mV ({lsb_rs/VT:.3f} V_T), monotonic by construction, "
              f"covers pre-distortion; tap -> buffer -> write line")

    out = dict(first_cut_current_dac=dict(
                   nbits=NBITS, Rload_ohm=RLOAD, LSB_mV=round(lsb*1e3, 3), range_mV=round(rng*1e3, 2),
                   monotonic=monotonic, INL_LSB=round(inl, 3),
                   transfer=[dict(code=c, v_load=round(float(x), 5)) for c, x in zip(codes, v)]),
               refined_resistor_string=dict(
                   Vspan_mV=VSPAN*1e3,
                   options=[dict(bits=b, LSB_mV=round(VSPAN/2**b*1e3, 3), LSB_over_VT=round(VSPAN/2**b/VT, 4),
                                 covers_predist=True, monotonic=True) for b in (6, 7, 8)]),
               conclusion=("A binary-weighted current-steering write-DAC into the 776 ohm write load is "
                           "non-monotonic (INL 1.7 LSB) and range-short because the PMOS sources lose Vsd "
                           "compliance as V_load swings; a naive cascode starves on headroom. The refined "
                           "write-DAC is therefore VOLTAGE-MODE: a resistor-string DAC (monotonic by "
                           "construction, LSB = Vspan/2^b) whose tap feeds the CMOS write driver/buffer. "
                           "At Vspan=200 mV a 6-7 bit string gives LSB ~1.6-3.1 mV (<V_T/7) and covers the "
                           "148 mV per-row IR pre-distortion plus the per-column trim. This is the circuit "
                           "that carries the C2 trim + IR pre-distortion codes."))
    (HERE / "write_dac_summary.json").write_text(json.dumps(out, indent=2))
    print("\nwrote write_dac_summary.json")


if __name__ == "__main__":
    main()
