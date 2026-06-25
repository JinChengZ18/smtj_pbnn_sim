#!/usr/bin/env python3
"""P7a first-cut: validate the low-barrier telegraph node tau(V)/<s> via smtj_sot.va
observables (V(tau), V(sinf)) in ngspice, against the analytic forms, at the RC
operating barrier Delta~3.8 (lower than the PBNN write device Delta=4.91).

Confirms the two RC knobs are device-grounded:
  tau(V) = 1/(r_up + r_dn)        -> fading memory (voltage-tunable correlation time)
  <s>    = tanh(Delta*V/Vc0)      -> nonlinearity
Delta is overridden on the OSDI .model card: `.model smtj_sot smtj_sot Delta=3.8`.

Run: python eda/testbenches/telegraph_lowbarrier.py   (needs ngspice + OpenVAF)
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent / "models" / "smtj_sot.va"
CONFIG = HERE.parent / "tools.local.json"
OSDI = HERE / "smtj_sot.osdi"
NET = HERE / "_tele_run.spice"
OUT = HERE / "tele_out.csv"

DELTA, VC0, TAU0 = 3.8, 0.857, 1.0e-9


def _cfg():
    try:
        return json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    except Exception:
        return {}


def find_tool(env, key, names):
    v = os.environ.get(env)
    if v and Path(v).exists():
        return v
    c = _cfg().get(key)
    if c and Path(c).exists():
        return c
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def tau_ns(V):
    rup = np.exp(-DELTA * (1 - V / VC0)) / TAU0
    rdn = np.exp(-DELTA * (1 + V / VC0)) / TAU0
    return 1e9 / (rup + rdn)


def sinf(V):
    return np.tanh(DELTA * V / VC0)


NETLIST = f"""* P7a low-barrier telegraph tau(V)/<s> validation (first line = title)
.model smtj_sot smtj_sot Delta={DELTA}
Vcom com 0 dc 0
Vrd  rd  0 dc 0
Vst  st  0 dc 0
Vwr  wr  0 dc 0
N1 wr rd com st psw tau sinf smtj_sot
Rpsw  psw  0 1e12
Rtau  tau  0 1e12
Rsinf sinf 0 1e12
.control
  dc Vwr -0.2 0.2 0.004
  wrdata tele_out.csv v(tau) v(sinf)
  quit
.endc
.end
"""


def load(path, cols):
    rows = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line[0] in "*#":
            continue
        p = [x for x in line.replace(",", " ").split() if x]
        try:
            rows.append([float(x) for x in p])
        except ValueError:
            continue
    a = np.array(rows)
    return {c: a[:, c] for c in cols}


def main():
    ng = find_tool("NGSPICE", "ngspice", ["ngspice_con", "ngspice"])
    ov = find_tool("OPENVAF", "openvaf", ["openvaf", "openvaf-r"])
    if not ng or not ov:
        print("ngspice/openvaf not found; see eda/SETUP_opensource.md")
        return 0
    subprocess.run([ov, str(MODEL), "-o", str(OSDI)], check=True, cwd=HERE)
    (HERE / ".spiceinit").write_text("osdi smtj_sot.osdi\n")
    NET.write_text(NETLIST)
    subprocess.run([ng, "-b", NET.name], check=True, cwd=HERE,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = load(OUT, [0, 1, 3])              # wrdata: V tau V sinf
    V, tau_sim, sinf_sim = d[0], d[1], d[3]
    tau_an, sinf_an = tau_ns(V), sinf(V)
    tau_err = float(np.max(np.abs(tau_sim - tau_an) / np.maximum(tau_an, 1e-12)))
    sinf_err = float(np.max(np.abs(sinf_sim - sinf_an)))
    i0 = int(np.argmin(np.abs(V)))
    ok = tau_err < 1e-3 and sinf_err < 1e-3
    summ = dict(Delta=DELTA, tau_max_ns_sim=float(tau_sim[i0]),
                tau_max_ns_analytic=float(tau_an[i0]),
                tau_rel_err_max=tau_err, sinf_abs_err_max=sinf_err, pass_=ok)
    (HERE / "tele_summary.json").write_text(json.dumps(summ, indent=2))
    print(f"Delta={DELTA}: tau_max(0V) sim={tau_sim[i0]:.2f}ns analytic={tau_an[i0]:.2f}ns "
          f"| tau rel-err<{tau_err:.1e}, <s> abs-err<{sinf_err:.1e} -> "
          f"{'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
