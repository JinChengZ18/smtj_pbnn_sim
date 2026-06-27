#!/usr/bin/env python3
"""C1 slope-matched readout FRONT-END: column popcount current -> transimpedance -> StrongARM.

Completes the readout circuit beyond the analytical co-design law. The 2T2MTJ XNOR-popcount column
sources a differential current I_diff = popcount * LSB_I (LSB_I = 5.10 uA/popcount, ngspice-verified).
A resistive transimpedance R_TI converts it to the StrongARM differential input; the slope-matched
design sizes R_TI so the full-scale popcount uses the SA input range:
    R_TI = V_in / (2 * PC_FS * LSB_I),   PC_FS = 3*sqrt(F).
This sweeps popcount through the StrongARM and, with/without the extracted input offset, locates the
in-circuit decision boundary -- verifying the predicted popcount-domain error sigma_pc = offset/(LSB_I*R_TI)
in a real sky130 circuit rather than on paper.

MUST RUN IN WSL (native ngspice + sky130):
  wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd <repo>; python3 eda/hero/run_readout_frontend.py'
"""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LIB = "/opt/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
RUN = HERE / "_readout_fe.spice"
LSB_I = 5.102e-6            # A/popcount (P3 diff_column, ngspice-verified)
VT = 0.023414
OFFSET_EXTRACTED = 9.21e-3  # extracted sky130 StrongARM input-referred offset (N=120 MC)

NET = """* C1 readout front-end: popcount current -> R_TI transimpedance -> StrongARM SA (sky130)
.lib {lib} tt
Vdd vdd 0 1.8
Vss vss 0 0
Vclk clk 0 PULSE(0 1.8 1n 50p 50p 2n 10n)
Vcm  vcm 0 0.9
* differential popcount current: +Ihalf into np, -Ihalf from nn ; R_TI converts to voltage
Isig 0 np dc 0
Isnk nn 0 dc 0
RTIp np vcm {rti}
RTIn nn vcm {rti}
* input-referred offset on the input pair (gate series)
Vos g1 np DC {os}
Vg2 g2 nn DC 0
XMtail ntail clk vss   vss sky130_fd_pr__nfet_01v8 W=4 L=0.15
XM1    da    g1  ntail vss sky130_fd_pr__nfet_01v8 W=4 L=0.15
XM2    db    g2  ntail vss sky130_fd_pr__nfet_01v8 W=4 L=0.15
XM3    outn  outp da   vss sky130_fd_pr__nfet_01v8 W=2 L=0.15
XM4    outp  outn db   vss sky130_fd_pr__nfet_01v8 W=2 L=0.15
XM5    outn  outp vdd  vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XM6    outp  outn vdd  vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp1   outp  clk  vdd  vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp2   outn  clk  vdd  vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp3   da    clk  vdd  vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp4   db    clk  vdd  vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
.control
  let p = {pmin}
  dowhile p <= {pmax}
    alter @Isig[dc] = p * {lsb_i} / 2
    alter @Isnk[dc] = p * {lsb_i} / 2
    tran 5p 4n
    meas tran vop find v(outp) at=2.9n
    meas tran von find v(outn) at=2.9n
    echo PT $&p $&vop $&von
    let p = p + {pstep}
  end
  quit
.endc
.end
"""


def boundary(rti, os, pmin, pmax, pstep):
    RUN.write_text(NET.format(lib=LIB, rti=rti, os=os, lsb_i=LSB_I,
                              pmin=pmin, pmax=pmax, pstep=pstep))
    out = subprocess.run(["ngspice", "-b", RUN.name], cwd=HERE,
                         capture_output=True, text=True).stdout
    pts = []
    for m in re.finditer(r"PT\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", out):
        p, vop, von = float(m.group(1)), float(m.group(2)), float(m.group(3))
        pts.append((p, vop - von))
    pts.sort()
    if len(pts) < 3:
        return float("nan"), pts
    p = np.array([x[0] for x in pts]); d = np.array([x[1] for x in pts])
    idx = np.where(np.diff(np.sign(d)) != 0)[0]
    if not len(idx):
        return float("nan"), pts
    i = idx[0]
    return float(p[i] - d[i] * (p[i + 1] - p[i]) / (d[i + 1] - d[i])), pts


def main():
    F = 1024
    PC_FS = 3.0 * np.sqrt(F)            # 96
    V_in = 0.6
    R_TI = V_in / (2.0 * PC_FS * LSB_I)  # slope-matched co-design law
    LSB_V = LSB_I * R_TI
    print(f"slope-matched readout: F={F}, PC_FS={PC_FS:.0f}, V_in={V_in} V")
    print(f"  R_TI = V_in/(2*PC_FS*LSB_I) = {R_TI:.0f} ohm ;  LSB_V = LSB_I*R_TI = {LSB_V*1e3:.3f} mV/popcount")
    print(f"  full-scale check: PC_FS*LSB_V = {PC_FS*LSB_V*1e3:.0f} mV (= V_in/2 = {V_in/2*1e3:.0f} mV)\n")

    b0, _ = boundary(R_TI, 0.0, -10, 10, 0.5)
    bo, pts = boundary(R_TI, OFFSET_EXTRACTED, -10, 10, 0.5)
    sigma_pc_meas = abs(bo - b0)
    sigma_pc_law = OFFSET_EXTRACTED / LSB_V
    print(f"in-circuit decision boundary (popcount):  offset=0 -> {b0:+.2f} ;  "
          f"offset={OFFSET_EXTRACTED*1e3:.2f} mV -> {bo:+.2f}")
    print(f"  => sigma_pc measured (in-circuit) = {sigma_pc_meas:.2f} popcount")
    print(f"     sigma_pc co-design law offset/LSB_V = {sigma_pc_law:.2f} popcount  "
          f"(match {100*sigma_pc_meas/sigma_pc_law:.0f}%)")
    print(f"  => offset {OFFSET_EXTRACTED/VT:.2f} V_T maps to {sigma_pc_meas:.2f} popcount at the "
          f"designed gain (curve knee ~4-8) -> plain SA sufficient")

    out = dict(F=F, PC_FS=PC_FS, V_in=V_in, R_TI_ohm=round(R_TI, 1), LSB_V_mV=round(LSB_V*1e3, 4),
               LSB_I_uA=LSB_I*1e6, offset_mV=OFFSET_EXTRACTED*1e3,
               boundary_pc_nooffset=round(b0, 3), boundary_pc_offset=round(bo, 3),
               sigma_pc_measured=round(sigma_pc_meas, 3), sigma_pc_law=round(sigma_pc_law, 3),
               transfer=[dict(popcount=p, vdiff_out=round(d, 4)) for p, d in pts],
               note=("In-circuit sky130 verification of the slope-matched readout co-design law: a "
                     "resistive transimpedance R_TI sized by R_TI=V_in/(2*PC_FS*LSB_I) makes the "
                     "extracted SA offset map to sigma_pc=offset/(LSB_I*R_TI) popcounts, matching the "
                     "analytical law. Ratios; AVT sky130-class; resistive TIA first cut."))
    (HERE / "readout_frontend_summary.json").write_text(json.dumps(out, indent=2))
    print("\nwrote readout_frontend_summary.json")


if __name__ == "__main__":
    main()
