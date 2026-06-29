#!/usr/bin/env python3
"""Input-referred OFFSET (vs V_T=23.4 mV) of a clocked sense amp, Monte-Carlo over
per-transistor Vth mismatch -- now a NETLIST FACTORY so alternative comparator
topologies are compared in the SAME flow as our StrongARM (revision-plan Phase 3).

Each design is one self-contained netlist under `comparators/<design>.spice` that
provides the gate offset-injection sources `Vo*` + the transistor core, against the
shared interface nodes (vdd vss clk vinp vinn -> outp outn). A `* META ...` header
line declares: n_off (number of Vo offset sources), wl (comma list of each offset
device's W*L in um^2, may reference `win`), meas_t (decision sample time), and
win_default. The harness wraps the core with a shared preamble + a vind sweep, runs
ngspice once per MC sample, and finds the vind where the decision (vop-von) flips =
the input-referred offset. Headline: sigma_offset / V_T (a ratio -- transfers across
nodes; absolute mV is 130nm/1.8V sky130-class).

MUST RUN IN WSL (native ngspice + sky130):
  wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd <repo>; \
      python3 eda/hero/run_offset_mc.py [--design strongarm] [N] [scale]'

Caveat: AVT is a sky130-class assumption (not the PDK mismatch model).
"""
from __future__ import annotations
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CMP = HERE / "comparators"
LIB = "/opt/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
RUN = HERE / "_sa_mc.spice"
VT = 0.023414
AVT_N = 5.0e-3                              # sky130-class NMOS Pelgrom AVT [V*um] (ASSUMPTION)

PREAMBLE = """* {design} offset MC sample (sky130, netlist factory)
.lib {lib} tt
Vdd vdd 0 1.8
Vss vss 0 0
Vclk clk 0 PULSE(0 1.8 1n 50p 50p 2n 10n)
Vinp vinp 0 0.9
Vinn vinn 0 0.9
"""
CONTROL = """.control
  let vd = -0.04
  dowhile vd <= 0.0401
    alter @vinp[dc] = 0.9 + vd/2
    alter @vinn[dc] = 0.9 - vd/2
    tran 5p 4n
    meas tran vop find v(outp) at={meas_t}
    meas tran von find v(outn) at={meas_t}
    echo PT $&vd $&vop $&von
    let vd = vd + 0.002
  end
  quit
.endc
.end
"""


def load_design(design):
    """Return (core_text, meta dict) for comparators/<design>.spice."""
    text = (CMP / f"{design}.spice").read_text()
    meta = {"n_off": 0, "meas_t": "2.9n", "win_default": 4.0, "wl": []}
    m = re.search(r"^\*\s*META\s+(.*)$", text, re.MULTILINE)
    if not m:
        raise ValueError(f"{design}.spice: missing '* META ...' header")
    for tok in m.group(1).split():
        k, _, v = tok.partition("=")
        if k == "n_off":
            meta["n_off"] = int(v)
        elif k == "meas_t":
            meta["meas_t"] = v
        elif k == "win_default":
            meta["win_default"] = float(v)
        elif k == "wl":
            meta["wl"] = v.split(",")          # exprs in `win`, eval'd later
        elif k == "desc":
            meta["desc"] = v.replace("-", " ")
    return text, meta


def sigma_list(meta, win):
    """Per-offset-source Pelgrom sigma_Vth = AVT_N / sqrt(W*L)."""
    wl = [eval(e, {"__builtins__": {}}, {"win": win}) for e in meta["wl"]]   # noqa: S307 (trusted files)
    return [AVT_N / math.sqrt(a) for a in wl]


def offset_of(core, meta, os, win, design):
    """Sweep vind in ngspice; return vind where (vop-von) crosses 0 [V], or nan."""
    body = core.format(win=win, **{f"os{i}": os[i] for i in range(len(os))})
    RUN.write_text(PREAMBLE.format(design=design, lib=LIB) + body
                   + CONTROL.format(meas_t=meta["meas_t"]))
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
    idx = np.where(np.diff(np.sign(d)) != 0)[0]
    if not len(idx):
        return float("nan")
    i = idx[0]
    return float(vd[i] - d[i] * (vd[i + 1] - vd[i]) / (d[i + 1] - d[i]))


def main():
    args = [a for a in sys.argv[1:]]
    design = "strongarm"
    if args and args[0] == "--design":
        design = args[1]; args = args[2:]
    N = int(args[0]) if args else 24
    scale = float(args[1]) if len(args) > 1 else 1.0
    core, meta = load_design(design)
    win = meta["win_default"] * scale
    sig = sigma_list(meta, win)
    rng = np.random.default_rng(20260627)
    offs = []
    for k in range(N):
        o = offset_of(core, meta, [rng.normal(0, s) for s in sig], win, design)
        if np.isfinite(o):
            offs.append(o)
        print(f"  [{design}] sample {k+1}/{N}: offset = {o*1e3:+.2f} mV", flush=True)
    offs = np.array(offs)
    if not len(offs):
        print(f"\n[{design}] NO finite offsets -- the design did not produce a clean "
              f"decision flip across the vind sweep (check the netlist/topology).")
        sys.exit(2)
    sigma, mean = float(np.std(offs)), float(np.mean(offs))
    print(f"\n{design} offset (sky130, scale={scale}x, Win={win}um, N={len(offs)}):")
    print(f"  mean={mean*1e3:+.2f} mV  sigma={sigma*1e3:.2f} mV  V_T={VT*1e3:.2f} mV")
    print(f"  sigma_offset/V_T = {sigma/VT:.2f}   3sigma/V_T = {3*sigma/VT:.2f}")
    summ = dict(design=design, desc=meta.get("desc", design), N=len(offs), scale=scale,
                Win_um=win, AVT_N_mV_um=AVT_N * 1e3, sigma_Vth_mV=[s * 1e3 for s in sig],
                offset_mean_mV=mean * 1e3, offset_sigma_mV=sigma * 1e3, VT_mV=VT * 1e3,
                sigma_offset_over_VT=sigma / VT, three_sigma_over_VT=3 * sigma / VT,
                note=("AVT is a sky130-class assumption (not PDK mismatch model); 130nm/1.8V "
                      "-> ratio sigma_offset/V_T transfers, not absolute mV. Same-flow "
                      "reproduction comparison: all designs share this harness."))
    if design == "strongarm" and scale == 1.0:
        fn = "offset_mc_summary.json"          # back-compat name for the baseline
    else:
        fn = f"offset_mc_{design}{'' if scale == 1.0 else f'_s{scale:g}'}.json"
    (HERE / fn).write_text(json.dumps(summ, indent=2))
    print(f"  -> {fn}")


if __name__ == "__main__":
    main()
