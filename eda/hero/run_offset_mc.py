#!/usr/bin/env python3
"""Hero (A1) core result: StrongARM sense-amp input-referred OFFSET vs V_T=23.4mV.

Monte-Carlo over per-transistor Vth mismatch (Pelgrom sigma_Vth=AVT/sqrt(W*L)),
injected as gate-series offset sources on the input pair + latch NMOS. Per MC sample
we sweep the input differential `vind` INSIDE one ngspice run (lib parsed once/sample,
~20x fewer parses than per-bisection-step) and find the `vind` where the comparator
decision flips -- that is the input-referred offset. Headline: sigma_offset / V_T.

MUST RUN IN WSL (native ngspice + sky130):
  wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd <repo>; python3 eda/hero/run_offset_mc.py [N]'

Caveats: AVT is a sky130-class assumption (not the PDK mismatch model); 130nm/1.8V,
so the RATIO sigma_offset/V_T transfers, not absolute mV.
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LIB = "/opt/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
RUN = HERE / "_sa_mc.spice"
VT = 0.023414
AVT_N = 5.0e-3                              # sky130-class NMOS Pelgrom AVT [V*um] (ASSUMPTION)
SIG = [AVT_N / np.sqrt(4 * 0.15)] * 2 + [AVT_N / np.sqrt(2 * 0.15)] * 2   # in-pair, latch

HEAD = """* StrongARM offset MC sample (sky130)
.lib {lib} tt
Vdd vdd 0 1.8
Vss vss 0 0
Vclk clk 0 PULSE(0 1.8 1n 50p 50p 2n 10n)
Vinp vinp 0 0.9
Vinn vinn 0 0.9
Vo1 g1 vinp DC {os0:.6f}
Vo2 g2 vinn DC {os1:.6f}
Vo3 g3 outp DC {os2:.6f}
Vo4 g4 outn DC {os3:.6f}
XMtail ntail clk   vss   vss sky130_fd_pr__nfet_01v8 W=4 L=0.15
XM1    da    g1    ntail vss sky130_fd_pr__nfet_01v8 W={win} L=0.15
XM2    db    g2    ntail vss sky130_fd_pr__nfet_01v8 W={win} L=0.15
XM3    outn  g3    da    vss sky130_fd_pr__nfet_01v8 W=2 L=0.15
XM4    outp  g4    db    vss sky130_fd_pr__nfet_01v8 W=2 L=0.15
XM5    outn  outp  vdd   vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XM6    outp  outn  vdd   vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp1   outp  clk   vdd   vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp2   outn  clk   vdd   vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp3   da    clk   vdd   vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp4   db    clk   vdd   vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
.control
  let vd = -0.04
  dowhile vd <= 0.0401
    alter @vinp[dc] = 0.9 + vd/2
    alter @vinn[dc] = 0.9 - vd/2
    tran 5p 4n
    meas tran vop find v(outp) at=2.9n
    meas tran von find v(outn) at=2.9n
    echo PT $&vd $&vop $&von
    let vd = vd + 0.002
  end
  quit
.endc
.end
"""


def offset_of(os, win):
    """Sweep vind in ngspice; return the vind where (vop-von) crosses 0 [V], or nan."""
    RUN.write_text(HEAD.format(lib=LIB, win=win, os0=os[0], os1=os[1], os2=os[2], os3=os[3]))
    out = subprocess.run(["ngspice", "-b", RUN.name], cwd=HERE,
                         capture_output=True, text=True).stdout
    pts = []
    for m in re.finditer(r"PT\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", out):
        vd, vop, von = float(m.group(1)), float(m.group(2)), float(m.group(3))
        pts.append((vd, vop - von))
    if len(pts) < 3:
        return float("nan")
    pts.sort()
    vd = np.array([p[0] for p in pts]); d = np.array([p[1] for p in pts])
    sign = np.sign(d)
    idx = np.where(np.diff(sign) != 0)[0]
    if not len(idx):
        return float("nan")
    i = idx[0]                              # linear-interp the zero crossing of vop-von
    return float(vd[i] - d[i] * (vd[i + 1] - vd[i]) / (d[i + 1] - d[i]))


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    scale = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0   # input-pair area scale
    win = 4.0 * scale                       # input-pair width [um]; latch fixed at W=2
    sig = [AVT_N / np.sqrt(win * 0.15)] * 2 + [AVT_N / np.sqrt(2 * 0.15)] * 2
    rng = np.random.default_rng(20260627)
    offs = []
    for k in range(N):
        o = offset_of([rng.normal(0, s) for s in sig], win)
        if np.isfinite(o):
            offs.append(o)
        print(f"  sample {k+1}/{N}: offset = {o*1e3:+.2f} mV", flush=True)
    offs = np.array(offs)
    sigma, mean = float(np.std(offs)), float(np.mean(offs))
    print(f"\nStrongARM offset (sky130, scale={scale}x, Win={win}um, N={len(offs)}):")
    print(f"  mean={mean*1e3:+.2f} mV  sigma={sigma*1e3:.2f} mV  V_T={VT*1e3:.2f} mV")
    print(f"  sigma_offset/V_T = {sigma/VT:.2f}   3sigma/V_T = {3*sigma/VT:.2f}")
    summ = dict(N=len(offs), scale=scale, Win_um=win, AVT_N_mV_um=AVT_N * 1e3,
                sigma_Vth_mV=[s * 1e3 for s in sig],
                offset_mean_mV=mean * 1e3, offset_sigma_mV=sigma * 1e3, VT_mV=VT * 1e3,
                sigma_offset_over_VT=sigma / VT, three_sigma_over_VT=3 * sigma / VT,
                note=("AVT is a sky130-class assumption (not PDK mismatch model); 130nm/1.8V "
                      "-> ratio sigma_offset/V_T transfers, not absolute mV. Area sweep: "
                      "sigma ~ 1/sqrt(area) (Pelgrom) gives the SA area to meet an offset budget."))
    fn = "offset_mc_summary.json" if scale == 1.0 else f"offset_mc_s{scale:g}.json"
    (HERE / fn).write_text(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
