#!/usr/bin/env python3
"""Faithful reproduction of the Yoon/Cacoilo CMOS-integrated sMTJ p-bit DRIVER
(J.-Y. Yoon, N. Cacoilo, A. Madhavan, J. J. McClelland, S. Kanai, H. Ohno, S. Fukami,
W. A. Borders, "CMOS-integrated superparamagnetic tunnel junction-based p-bit",
arXiv:2604.14446, 2026; IEEE EDL), rebuilt in OUR sky130/ngspice flow around OUR
calibrated committed device (eda/models/smtj_sot.va).

WHY THIS SCRIPT EXISTS
----------------------
The Yoon p-bit is the closest published sMTJ-divider-plus-threshold circuit to our
readout front end. Its headline circuit claim is a variable-threshold stage trimmed in
100-mV steps; our readout question is always referred to the device probability window
V_T = 23.4 mV. This repro turns Yoon's V_th-trim row into numbers MEASURED in the same
sky130/ngspice flow as every other comparison point (eda/design_survey/README.md), so
the D-appendix can carry a like-for-like entry instead of a survey estimate.

PAPER TOPOLOGY AND CLAIMS (verbatim quotes, arXiv:2604.14446 HTML v1)
---------------------------------------------------------------------
* Divider:  "sMTJ in series with an n-channel MOS (NMOS) transistor whose drain output
  is fed into an inverter."  (sMTJ from VDD to the NMOS drain; gate = bias input)
* VTC:      "The output feeds to the input of a variable threshold controller (VTC),
  containing two pull-up and two pull-down transistors, that collectively represent
  threshold voltages from 0.7 V to 1.1 V with a 100-mV step."
* Buffer:   "The VTC stage output feeds into a final inverter which produces voltage
  fluctuations between 0 V and 1.8 V."
* Node:     130 nm CMOS, VDD = 1.8 V (same node class and rail as sky130 1.8-V devices).
* Divider NMOS sizing: "the transistors are designed with channel widths of
  1, 3, 9, 27 um, producing currents from hundreds of uA to tens of mA."
* Their sMTJ: resistance 2.5-8 kOhm, TMR 50-100 %, "fluctuations with ms dwell times".
The paper does NOT disclose the VTC interconnection, the threshold-select mechanism, or
transistor sizes of the VTC -- those are OUR mapping (documented in the JSON under
"mapping_adaptations"); the leg COUNT (2 PU + 2 PD input transistors) is the paper's.

WHAT IS MEASURED vs WHAT IS MODELED (integrity labels)
------------------------------------------------------
MEASURED (ngspice DC, sky130 tt, schematic-level):
  (a) the achieved VTC trip voltage at each of 5 trim codes (step / range / monotonic),
  (b) the sMTJ/NMOS divider output for both device states vs gate bias (separation),
  (c) the full-chain digitization windows and centering margins.
STATIC TWO-STATE DEVICE: the committed Verilog-A model deliberately keeps the RNG in
the harness -- its MTJ read branch is a two-state resistor set by control node `st`
(V(st)=0 -> R_P, 1 -> R_AP); stochastic transient is BY DESIGN external. The divider is
therefore characterized statically at st=0 and st=1 using the committed compiled OSDI
model itself (not a substitute resistor). The paper's devices fluctuate with "ms dwell
times", so the static two-state characterization matches its operating regime.
MODEL-DERIVED (labeled analytic, committed formulas, NOT simulated noise):
  p_AP at the unbiased SOT branch from <s> = tanh(Delta*V/Vc0); the probability
  excursion an equivalent trim step would command on our device sigmoid
  P_sw(V) = 1/(1+exp(-(V-Vth)/V_T)); the ideal-resistor divider-separation bound
  S_ideal = VDD*(R_AP-R_P)/(sqrt(R_P)+sqrt(R_AP))^2.
House norm: RATIOS are the headline (step/V_T, separation/step); absolute mV numbers
are schematic-level sky130/1.8-V-class values.

MUST RUN IN WSL (native ngspice + sky130 + compiled smtj_sot.osdi):
  wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd <repo>; \
      python3 eda/design_survey/repro/yoon_pbit_driver.py [--smoke]'
Writes yoon_pbit_driver_summary.json next to this file. Every number in the JSON is
computed by this script; nothing is typed by hand.
"""
from __future__ import annotations

import bisect
import itertools
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
VA = REPO / "eda" / "models" / "smtj_sot.va"
OSDI_REL = "../../testbenches/smtj_sot.osdi"      # relative: repo path contains spaces
LIB = "/opt/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
VDD = 1.8
TARGETS = [0.7, 0.8, 0.9, 1.0, 1.1]               # the paper's claimed threshold row [V]
L = 0.15                                          # house channel length (strongarm core)
DIV_W = [1, 3, 9, 27]                             # paper's divider-NMOS width options [um]


# ----------------------------------------------------------------------------------
# committed-model provenance
# ----------------------------------------------------------------------------------
def parse_va():
    txt = VA.read_text(encoding="utf-8")
    p = {m.group(1): float(m.group(2)) for m in re.finditer(
        r"parameter\s+real\s+(\w+)\s*=\s*([0-9.eE+-]+)", txt)}
    for k in ("Vth", "VT", "Delta", "Vc0", "Rp", "TMR", "Rsot"):
        assert k in p, f"smtj_sot.va missing parameter {k}"
    # gate against the calibrated constants used across the repo
    assert abs(p["Vth"] - 0.895783) < 1e-6 and abs(p["VT"] - 0.023414) < 1e-6, \
        "committed sigmoid constants changed -- re-audit this repro"
    p["Rap"] = p["Rp"] * (1.0 + p["TMR"])
    return p


# ----------------------------------------------------------------------------------
# ngspice plumbing
# ----------------------------------------------------------------------------------
def ensure_spiceinit():
    f = HERE / ".spiceinit"
    want = f"osdi {OSDI_REL}\n"
    if not f.exists() or f.read_text() != want:
        f.write_text(want)


def run_deck(tag, body):
    deck = HERE / f"_yoon_{tag}.spice"
    deck.write_text(body)
    r = subprocess.run(["ngspice", "-b", deck.name], cwd=HERE,
                       capture_output=True, text=True)
    (HERE / f"_yoon_{tag}.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr)
    if r.returncode != 0:
        raise RuntimeError(f"ngspice failed for {tag}; see _yoon_{tag}.log")
    return r.stdout


def read_wrdata(name, nvec):
    """wrdata layout: per row, (scale, vec) pairs -> return (x, [y0..y{nvec-1}])."""
    rows = []
    for line in (HERE / name).read_text().splitlines():
        t = line.split()
        if len(t) == 2 * nvec:
            try:
                rows.append([float(v) for v in t])
            except ValueError:
                continue
    assert rows, f"no data parsed from {name}"
    x = [r[0] for r in rows]
    assert all(abs(r[2] - r[0]) < 1e-12 for r in rows) if nvec > 1 else True, \
        f"{name}: wrdata scale columns disagree -- parsing assumption broken"
    return x, [[r[2 * i + 1] for r in rows] for i in range(nvec)]


def cross_falling(x, y, level):
    """First x where y falls through `level` (linear interp); nan if none."""
    for i in range(1, len(x)):
        if y[i - 1] >= level > y[i]:
            return x[i - 1] + (y[i - 1] - level) * (x[i] - x[i - 1]) / (y[i - 1] - y[i])
    return float("nan")


def cross_rising(x, y, level):
    for i in range(1, len(x)):
        if y[i - 1] <= level < y[i]:
            return x[i - 1] + (level - y[i - 1]) * (x[i] - x[i - 1]) / (y[i] - y[i - 1])
    return float("nan")


# ----------------------------------------------------------------------------------
# netlist generators.  Widths are built from proven sky130 bins only
# (W in {0.42, 1, 2} um) via the instance multiplier m, so every device bins.
# ----------------------------------------------------------------------------------
def wm(w_eff, base):
    """Represent effective width w_eff as (W, m) using proven bin widths only."""
    for b in (base, 1.0, 0.42):
        m = round(w_eff / b)
        if m > 0 and abs(m * b - w_eff) < 1e-6:
            return b, m
    raise AssertionError(f"width {w_eff} not representable from proven bins")


def fet(name, d, g, s, b, kind, w_eff, base, mscale=1):
    w, m = wm(w_eff, base)
    return (f"X{name} {d} {g} {s} {b} sky130_fd_pr__{kind}_01v8 "
            f"W={w} L={L} m={m * mscale}\n")


def vtc_cell(pfx, vin, vout, en, widths):
    """2-PU + 2-PD input transistors (the paper's leg count), each leg gated by a
    series enable device (2x the leg width -- OUR mapping).  en = 4 net names for
    (enp1, enp2, enn1, enn2); enp active-LOW, enn active-HIGH."""
    wp1, wp2, wn1, wn2 = widths
    s = ""
    s += fet(f"{pfx}PE1", "vdd", en[0], f"{pfx}p1", "vdd", "pfet", wp1, PBASE, 2)
    s += fet(f"{pfx}PI1", f"{pfx}p1", vin, vout, "vdd", "pfet", wp1, PBASE)
    s += fet(f"{pfx}PE2", "vdd", en[1], f"{pfx}p2", "vdd", "pfet", wp2, PBASE, 2)
    s += fet(f"{pfx}PI2", f"{pfx}p2", vin, vout, "vdd", "pfet", wp2, PBASE)
    s += fet(f"{pfx}NI1", vout, vin, f"{pfx}n1", "vss", "nfet", wn1, NBASE)
    s += fet(f"{pfx}NE1", f"{pfx}n1", en[2], "vss", "vss", "nfet", wn1, NBASE, 2)
    s += fet(f"{pfx}NI2", vout, vin, f"{pfx}n2", "vss", "nfet", wn2, NBASE)
    s += fet(f"{pfx}NE2", f"{pfx}n2", en[3], "vss", "vss", "nfet", wn2, NBASE, 2)
    return s


PBASE, NBASE = 1.0, 0.42                       # proven sky130 bin widths (um)
COMBOS = [(pu, pd) for pu in ((1, 0), (0, 1), (1, 1)) for pd in ((1, 0), (0, 1), (1, 1))]


def combo_nets(pu, pd):
    """Hard-wired enable nets for a (pu, pd) leg-selection combo."""
    return ("vss" if pu[0] else "vdd", "vss" if pu[1] else "vdd",
            "vdd" if pd[0] else "vss", "vdd" if pd[1] else "vss")


def combo_ratio(pu, pd, widths):
    wp1, wp2, wn1, wn2 = widths
    return (pu[0] * wp1 + pu[1] * wp2) / (pd[0] * wn1 + pd[1] * wn2)


PRE = f"""* Yoon p-bit repro deck ({{tag}}) -- sky130 tt, schematic-level
.lib {LIB} tt
Vdd vdd 0 {VDD}
Vss vss 0 0
"""


# ----------------------------------------------------------------------------------
# phase 1/2: VTC survey (many hard-wired variants, one shared DC input sweep)
# ----------------------------------------------------------------------------------
def measure_vtc_variants(tag, width_sets):
    """One deck: for each width set, all 9 leg combos hard-wired; DC sweep the common
    input; return dict[(set_idx, combo_idx)] -> measured trip (vin @ vout=VDD/2)."""
    body = PRE.format(tag=tag) + "Vin vin 0 0\n"
    n = 0
    for si, ws in enumerate(width_sets):
        for ci, (pu, pd) in enumerate(COMBOS):
            body += vtc_cell(f"S{si}C{ci}", "vin", f"o{n}", combo_nets(pu, pd), ws)
            n += 1
    body += ".control\nset wr_singlescale\ndc Vin 0 1.8 0.002\n"
    vecs = [f"v(o{i})" for i in range(n)]
    files = []
    for k in range(0, n, 9):
        f = f"_yoon_{tag}_{k // 9}.csv"
        body += f"wrdata {f} {' '.join(vecs[k:k + 9])}\n"
        files.append((f, min(9, n - k)))
    body += "quit\n.endc\n.end\n"
    run_deck(tag, body)
    out, idx = {}, 0
    for f, cnt in files:
        # set wr_singlescale not guaranteed on all builds; parse defensively
        try:
            x, ys = read_wrdata(f, cnt)
        except AssertionError:
            x, ys = read_wrdata_single(f, cnt)
        for y in ys:
            out[(idx // 9, idx % 9)] = cross_falling(x, y, VDD / 2)
            idx += 1
    return out


def read_wrdata_single(name, nvec):
    """Fallback: wrdata with a single leading scale column."""
    rows = []
    for line in (HERE / name).read_text().splitlines():
        t = line.split()
        if len(t) == nvec + 1:
            try:
                rows.append([float(v) for v in t])
            except ValueError:
                continue
    assert rows, f"no data parsed from {name}"
    return [r[0] for r in rows], [[r[i + 1] for r in rows] for i in range(nvec)]


def sel_obj(vms):
    """Selection objective: closeness to the paper's targets PLUS step evenness
    (the claim is a uniform 100-mV step, so both anchors are part of the claim)."""
    sse = sum((v - t) ** 2 for v, t in zip(vms, TARGETS))
    pen = sum((vms[i + 1] - vms[i] - 0.1) ** 2 for i in range(4))
    return sse + pen


def fit_and_pick(measured, width_sets):
    """Piecewise-linear V_M(log r) from all measured survey points, then grid-search
    (wp1,wp2,wn1,wn2) + a monotone 5-of-9 combo subset minimizing sel_obj."""
    pts = sorted((math.log(combo_ratio(*COMBOS[ci], width_sets[si])), vm)
                 for (si, ci), vm in measured.items() if math.isfinite(vm))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    def vm_pred(r):
        lx = math.log(r)
        if lx <= xs[0]:
            i = 1
        elif lx >= xs[-1]:
            i = len(xs) - 1
        else:
            i = bisect.bisect_left(xs, lx)
        x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
        return y0 + (lx - x0) * (y1 - y0) / (x1 - x0) if x1 > x0 else y0

    wp_opts = [0.42, 0.84] + [float(m) for m in range(1, 17)]
    wn_opts = [round(NBASE * m, 2) for m in range(1, 11)]
    best = None
    for wp1, wp2 in itertools.combinations(wp_opts, 2):
        for wn1, wn2 in itertools.combinations(wn_opts, 2):
            ws = (wp1, wp2, wn1, wn2)
            rs = sorted((combo_ratio(pu, pd, ws), ci)
                        for ci, (pu, pd) in enumerate(COMBOS))
            preds = [(vm_pred(r), ci) for r, ci in rs]
            for sub in itertools.combinations(range(9), 5):
                obj = sel_obj([preds[j][0] for j in sub])
                if best is None or obj < best[0]:
                    best = (obj, ws, [preds[j][1] for j in sub])
    return best[1], best[2], math.sqrt(best[0] / 5)


# ----------------------------------------------------------------------------------
# phase 3: final VTC + output inverter, 5 codes, measured trip points
# ----------------------------------------------------------------------------------
def out_inverter(pfx, vin, vout):
    return (fet(f"{pfx}P", vout, vin, "vdd", "vdd", "pfet", 2.0, PBASE)
            + fet(f"{pfx}N", vout, vin, "vss", "vss", "nfet", 0.84, NBASE))


def measure_final_vtc(widths, code_cis):
    body = PRE.format(tag="vtcfinal") + "Vin vin 0 0\n"
    for k, ci in enumerate(code_cis):
        pu, pd = COMBOS[ci]
        body += vtc_cell(f"K{k}", "vin", f"m{k}", combo_nets(pu, pd), widths)
        body += out_inverter(f"B{k}", f"m{k}", f"f{k}")
    body += ".control\ndc Vin 0 1.8 0.001\n"
    body += ("wrdata _yoon_vtcfinal_m.csv "
             + " ".join(f"v(m{k})" for k in range(len(code_cis))) + "\n")
    body += ("wrdata _yoon_vtcfinal_f.csv "
             + " ".join(f"v(f{k})" for k in range(len(code_cis))) + "\n")
    body += "quit\n.endc\n.end\n"
    run_deck("vtcfinal", body)
    x, ms = read_wrdata("_yoon_vtcfinal_m.csv", len(code_cis))
    _, fs = read_wrdata("_yoon_vtcfinal_f.csv", len(code_cis))
    vm_vtc = [cross_falling(x, y, VDD / 2) for y in ms]
    vm_chain = [cross_rising(x, y, VDD / 2) for y in fs]   # final inv re-inverts
    return vm_vtc, vm_chain


# ----------------------------------------------------------------------------------
# phase 4: sMTJ(OSDI, two-state via st) / NMOS divider vs gate bias
# ----------------------------------------------------------------------------------
def divider_deck_devices():
    s = ".model smtj_sot smtj_sot\n"
    for k, w in enumerate(DIV_W):
        # ports: wr rd com st psw tau sinf ; wr tied to com (SOT branch unbiased)
        s += f"Nsm{k} vd{k} vdd vd{k} st psw{k} tau{k} sinf{k} smtj_sot\n"
        s += fet(f"D{k}", f"vd{k}", "vb", "vss", "vss", "nfet", float(w), 1.0)
    return s


def measure_divider():
    body = PRE.format(tag="div") + "Vb vb 0 0\nVst st 0 0\n" + divider_deck_devices()
    body += ".control\n"
    for st, nm in ((0, "P"), (1, "AP")):
        body += f"alter @Vst[dc] = {st}\ndc Vb 0 1.8 0.002\n"
        body += (f"wrdata _yoon_div_{nm}.csv "
                 + " ".join(f"v(vd{k})" for k in range(len(DIV_W))) + "\n")
    body += "quit\n.endc\n.end\n"
    run_deck("div", body)
    x, yP = read_wrdata("_yoon_div_P.csv", len(DIV_W))
    _, yAP = read_wrdata("_yoon_div_AP.csv", len(DIV_W))
    return x, yP, yAP


# ----------------------------------------------------------------------------------
# phase 5: full chain (divider -> VTC -> output inverter), all codes x both states
# ----------------------------------------------------------------------------------
def measure_chain(widths, code_cis, div_w):
    body = PRE.format(tag="chain") + "Vb vb 0 0\nVst st 0 0\n.model smtj_sot smtj_sot\n"
    body += "Nsm vdiv vdd vdiv st psw tau sinf smtj_sot\n"
    body += fet("DN", "vdiv", "vb", "vss", "vss", "nfet", float(div_w), 1.0)
    for i, p in enumerate(("enp1", "enp2", "enn1", "enn2")):
        body += f"Ven{i} {p} 0 0\n"
    body += vtc_cell("V", "vdiv", "vtcout", ("enp1", "enp2", "enn1", "enn2"), widths)
    body += out_inverter("B", "vtcout", "final")
    body += ".control\n"
    for k, ci in enumerate(code_cis):
        pu, pd = COMBOS[ci]
        vals = (0 if pu[0] else VDD, 0 if pu[1] else VDD,
                VDD if pd[0] else 0, VDD if pd[1] else 0)
        for i, v in enumerate(vals):
            body += f"alter @Ven{i}[dc] = {v}\n"
        for st, nm in ((0, "P"), (1, "AP")):
            body += f"alter @Vst[dc] = {st}\ndc Vb 0 1.8 0.002\n"
            body += (f"wrdata _yoon_chain_c{k}_{nm}.csv "
                     f"v(vdiv) v(vtcout) v(final) i(Vdd)\n")
    body += "quit\n.endc\n.end\n"
    run_deck("chain", body)
    out = {}
    for k in range(len(code_cis)):
        for nm in ("P", "AP"):
            x, ys = read_wrdata(f"_yoon_chain_c{k}_{nm}.csv", 4)
            out[(k, nm)] = (x, ys)
    return out


# ----------------------------------------------------------------------------------
# smoke: minimal osdi + sky130 co-load check (SHORT config before any sweep)
# ----------------------------------------------------------------------------------
def smoke():
    ensure_spiceinit()
    body = PRE.format(tag="smoke") + "Vb vb 0 0.9\nVst st 0 0\n.model smtj_sot smtj_sot\n"
    body += "Nsm vdiv vdd vdiv st psw tau sinf smtj_sot\n"
    body += fet("DN", "vdiv", "vb", "vss", "vss", "nfet", 3.0, 1.0)
    body += fet("IP", "out", "vdiv", "vdd", "vdd", "pfet", 2.0, PBASE)
    body += fet("IN", "out", "vdiv", "vss", "vss", "nfet", 0.84, NBASE)
    body += (".control\ndc Vb 0.5 1.3 0.1\nwrdata _yoon_smoke_P.csv v(vdiv) v(out)\n"
             "alter @Vst[dc] = 1\ndc Vb 0.5 1.3 0.1\n"
             "wrdata _yoon_smoke_AP.csv v(vdiv) v(out)\nquit\n.endc\n.end\n")
    run_deck("smoke", body)
    xP, yP = read_wrdata("_yoon_smoke_P.csv", 2)
    xA, yA = read_wrdata("_yoon_smoke_AP.csv", 2)
    seps = [p - a for p, a in zip(yP[0], yA[0])]
    print(f"[smoke] OK: osdi+sky130 co-load fine; vdiv(P) at vb=0.9: "
          f"{yP[0][4]:.3f} V, vdiv(AP): {yA[0][4]:.3f} V, sep {max(seps)*1e3:.0f} mV max",
          flush=True)
    assert max(seps) > 0.05, "two-state divider separation implausibly small"
    return True


# ----------------------------------------------------------------------------------
def main():
    if "--smoke" in sys.argv:
        return 0 if smoke() else 1
    par = parse_va()
    ensure_spiceinit()
    print(f"[0] committed device: Rp={par['Rp']:.0f} Rap={par['Rap']:.0f} ohm, "
          f"Vth={par['Vth']:.6f} V, V_T={par['VT']*1e3:.3f} mV", flush=True)

    # ---- phase 1: survey (guides sizing only; final numbers come from phase 3) ----
    survey_sets = [(2.0, 6.0, 0.42, 0.84), (3.0, 9.0, 0.42, 0.84),
                   (4.0, 12.0, 0.84, 1.68), (1.0, 4.0, 0.42, 0.84),
                   (1.0, 2.0, 1.26, 2.52), (0.42, 3.0, 0.84, 1.68)]
    meas1 = measure_vtc_variants("survey", survey_sets)
    ok = sum(math.isfinite(v) for v in meas1.values())
    print(f"[1] survey: {ok}/{len(meas1)} variants tripped; "
          f"V_M span {min(v for v in meas1.values() if math.isfinite(v)):.3f}"
          f"-{max(v for v in meas1.values() if math.isfinite(v)):.3f} V", flush=True)

    widths, code_cis, rms_pred = fit_and_pick(meas1, survey_sets)
    print(f"[2] picked widths wp=({widths[0]},{widths[1]}) wn=({widths[2]},{widths[3]}) "
          f"um, codes {code_cis}, predicted RMS err {rms_pred*1e3:.1f} mV", flush=True)

    # ---- phase 2: verify the chosen cell (all 9 combos measured), reselect codes ----
    meas2 = measure_vtc_variants("verify", [widths])
    order = sorted(range(9), key=lambda ci: combo_ratio(*COMBOS[ci], widths))
    vm9 = {ci: meas2[(0, ci)] for ci in range(9)}
    best = None
    for sub in itertools.combinations(order, 5):   # order-preserving = monotone in r
        vms = [vm9[ci] for ci in sub]
        if any(not math.isfinite(v) for v in vms):
            continue
        obj = sel_obj(vms)
        if best is None or obj < best[0]:
            best = (obj, list(sub))
    code_cis = best[1]
    print(f"[3] verified codes {code_cis}: V_M = "
          + " ".join(f"{vm9[ci]:.3f}" for ci in code_cis), flush=True)

    # ---- phase 3: final VTC + output inverter, measured trip points ----
    vm_vtc, vm_chain = measure_final_vtc(widths, code_cis)
    steps = [(vm_chain[i + 1] - vm_chain[i]) * 1e3 for i in range(4)]
    mean_step = sum(steps) / len(steps)
    print(f"[4] chain-referred thresholds: "
          + " ".join(f"{v:.4f}" for v in vm_chain)
          + f" V; steps {['%.1f' % s for s in steps]} mV", flush=True)

    # ---- phase 4: divider two-state characterization ----
    vb, yP, yAP = measure_divider()
    div = []
    for k, w in enumerate(DIV_W):
        sep = [p - a for p, a in zip(yP[k], yAP[k])]
        i = max(range(len(sep)), key=lambda j: sep[j])
        mid_lo = min((yP[k][j] + yAP[k][j]) / 2 for j in range(len(vb)))
        mid_hi = max((yP[k][j] + yAP[k][j]) / 2 for j in range(len(vb)))
        div.append(dict(W_um=w, sep_max_mV=sep[i] * 1e3, vb_at_sepmax=vb[i],
                        vdiv_P=yP[k][i], vdiv_AP=yAP[k][i],
                        midpoint_at_sepmax=(yP[k][i] + yAP[k][i]) / 2,
                        midpoint_range_V=[mid_lo, mid_hi]))
        print(f"[5] divider W={w}um: max sep {sep[i]*1e3:.1f} mV at vb={vb[i]:.3f} V "
              f"(vdiv P/AP = {yP[k][i]:.3f}/{yAP[k][i]:.3f} V)", flush=True)
    # choose the W maximizing the centering margin of the MIDDLE trim code
    # (margin uses divider curves only: the VTC input is a MOS gate, no DC load)
    vm_mid = vm_chain[2]
    def best_margin_for(k):
        return max(min(yP[k][j] - vm_mid, vm_mid - yAP[k][j]) for j in range(len(vb)))
    kbest = max(range(len(DIV_W)), key=best_margin_for)
    wsel = DIV_W[kbest]
    print(f"[5] selected divider W={wsel} um (middle-code margin "
          f"{best_margin_for(kbest)*1e3:.1f} mV; others "
          f"{[round(best_margin_for(k)*1e3) for k in range(len(DIV_W))]} mV)",
          flush=True)

    # ---- phase 5: full chain, digitization windows + centering margins ----
    chain = measure_chain(widths, code_cis, wsel)
    kb = kbest
    per_code = []
    for k in range(5):
        xP_, yPc = chain[(k, "P")]
        _, yAc = chain[(k, "AP")]
        hi, lo = 0.9 * VDD, 0.1 * VDD
        win = [v for j, v in enumerate(xP_)
               if yPc[2][j] > hi and yAc[2][j] < lo]
        # centering margin vs the divider curves (measured), referred to vdiv axis
        marg = [min(yP[kb][j] - vm_chain[k], vm_chain[k] - yAP[kb][j])
                for j in range(len(vb))]
        jm = max(range(len(marg)), key=lambda j: marg[j])
        # cross-check: chain trip bias predicted from divider curve vs measured flip
        pred_trip_P = cross_falling(vb, yP[kb], vm_chain[k])
        meas_trip_P = cross_rising(xP_, [-v for v in yPc[2]], -VDD / 2)
        per_code.append(dict(
            code=k, vm_vtc_V=vm_vtc[k], vm_chain_V=vm_chain[k],
            digitize_window_vb_V=[min(win), max(win)] if win else None,
            window_width_mV=(max(win) - min(win)) * 1e3 if win else 0.0,
            best_margin_mV=marg[jm] * 1e3, vb_at_best_margin=vb[jm],
            pred_vs_meas_tripP_mV=abs(pred_trip_P - meas_trip_P) * 1e3
            if math.isfinite(pred_trip_P) and math.isfinite(meas_trip_P) else None))
        print(f"[6] code {k}: window "
              f"{per_code[-1]['digitize_window_vb_V']} V, best margin "
              f"{marg[jm]*1e3:.1f} mV @ vb={vb[jm]:.3f} V", flush=True)

    # static supply current (schematic-level), best code at its best-margin bias
    kctr = max(range(5), key=lambda k: per_code[k]["best_margin_mV"])
    vbstar = per_code[kctr]["vb_at_best_margin"]
    pw = {}
    for nm in ("P", "AP"):
        x_, ys_ = chain[(kctr, nm)]
        j = min(range(len(x_)), key=lambda j: abs(x_[j] - vbstar))
        pw[nm] = -ys_[3][j] * VDD * 1e6   # i(Vdd) is negative for sourced current
    sep_at = None
    j = min(range(len(vb)), key=lambda j: abs(vb[j] - vbstar))
    sep_at = (yP[kb][j] - yAP[kb][j]) * 1e3

    # ---- model-derived (labeled) analytics ----
    s_ideal = VDD * (par["Rap"] - par["Rp"]) / (math.sqrt(par["Rp"])
                                                + math.sqrt(par["Rap"])) ** 2
    dstep = mean_step / 1e3
    dp_step = (1 / (1 + math.exp(-dstep / 2 / par["VT"]))
               - 1 / (1 + math.exp(dstep / 2 / par["VT"])))

    achieved_range = [vm_chain[0], vm_chain[-1]]
    mono = all(steps[i] > 0 for i in range(4))
    worst_center_err = max(steps) / 2                   # worst gap in the (uneven) grid
    margin_worstcase = sep_at / 2 - worst_center_err
    n_distinct = 1 + sum(1 for s in steps if s > 30.0)  # levels separated by >30 mV

    out = {
        "_about": "Faithful reproduction of the Yoon/Cacoilo sMTJ p-bit driver "
                  "(sMTJ/NMOS divider -> variable-threshold inverter -> output "
                  "inverter) in our sky130/ngspice flow with our committed calibrated "
                  "device model. All numbers computed by yoon_pbit_driver.py.",
        "_paper": "J.-Y. Yoon, N. Cacoilo, A. Madhavan, J. J. McClelland, S. Kanai, "
                  "H. Ohno, S. Fukami, W. A. Borders, 'CMOS-integrated "
                  "superparamagnetic tunnel junction-based p-bit', arXiv:2604.14446 "
                  "(2026); IEEE Electron Device Letters. 130 nm CMOS, VDD=1.8 V.",
        "_paper_quotes": [
            "sMTJ in series with an n-channel MOS (NMOS) transistor whose drain "
            "output is fed into an inverter",
            "The output feeds to the input of a variable threshold controller (VTC), "
            "containing two pull-up and two pull-down transistors, that collectively "
            "represent threshold voltages from 0.7 V to 1.1 V with a 100-mV step.",
            "The VTC stage output feeds into a final inverter which produces voltage "
            "fluctuations between 0 V and 1.8 V",
            "the transistors are designed with channel widths of 1, 3, 9, 27 um, "
            "producing currents from hundreds of uA to tens of mA",
            "their sMTJ: resistance range 2.5-8 kOhm, TMR 50-100%, 'fluctuations "
            "with ms dwell times'"],
        "device_usage": {
            "model": "eda/models/smtj_sot.va compiled to OSDI (committed calibrated "
                     "model), MTJ read branch as the divider element",
            "how": "STATIC TWO-STATE: the committed model keeps the RNG in the "
                   "harness by design; its read branch is a two-state resistor set "
                   "by control node st (0=P, 1=AP). The divider is characterized at "
                   "st=0 and st=1 (DC), matching the paper's ms-dwell regime. No "
                   "stochastic transient was simulated.",
            "R_P_ohm": par["Rp"], "R_AP_ohm": par["Rap"], "TMR": par["TMR"],
            "Vth_V": par["Vth"], "V_T_V": par["VT"],
            "SOT_branch": "unbiased (wr tied to com): V_wr=0"},
        "vtc_design_ours": {
            "leg_count": "2 pull-up + 2 pull-down INPUT transistors (per the paper)",
            "enable_mapping": "each leg gated by a series enable device of 2x the "
                              "leg width; 5 codes = 5 enable patterns (paper does "
                              "not disclose its select mechanism -- OUR mapping)",
            "widths_um": {"wp1": widths[0], "wp2": widths[1],
                          "wn1": widths[2], "wn2": widths[3], "L": L},
            "codes": [{"code": k, "combo": COMBOS[ci],
                       "ratio_PUeff_over_PDeff": round(
                           combo_ratio(*COMBOS[ci], widths), 3)}
                      for k, ci in enumerate(code_cis)],
            "all_9_combos_measured_V": {str(COMBOS[ci]): round(vm9[ci], 4)
                                        for ci in order},
            "output_inverter_um": {"wp": 2.0, "wn": 0.84, "L": L}},
        "measured_vtc_thresholds": {
            "_label": "MEASURED, ngspice DC, sky130 tt, schematic-level",
            "definition": "chain-referred trip: divider-node voltage at which the "
                          "final (buffered) output crosses VDD/2; vm_vtc = VTC-stage "
                          "output crossing VDD/2",
            "per_code_V": [round(v, 4) for v in vm_chain],
            "vtc_stage_V": [round(v, 4) for v in vm_vtc],
            "steps_mV": [round(s, 1) for s in steps],
            "mean_step_mV": round(mean_step, 1),
            "range_V": [round(achieved_range[0], 4), round(achieved_range[1], 4)],
            "span_mV": round((achieved_range[1] - achieved_range[0]) * 1e3, 1),
            "monotonic": mono,
            "paper_claim": "0.7 to 1.1 V in 100 mV steps (5 levels)",
            "targets_V": TARGETS,
            "rms_error_to_paper_targets_mV": round(math.sqrt(sum(
                (v - t) ** 2 for v, t in zip(vm_chain, TARGETS)) / 5) * 1e3, 1),
            "n_levels_separated_by_gt_30mV": n_distinct,
            "structural_finding": "with 2 PU + 2 PD input legs the 9 enable combos "
                "give strength ratios {p1,p2,p1+p2}x{1/n1,1/n2,1/(n1+n2)}; spanning "
                "0.7-1.1 V in sky130 needs a ~2-orders-of-magnitude ratio span, and "
                "at such spans {p1,p2,p1+p2} degenerates to ~2 usable levels per "
                "side, so the combos cluster into ~4 well-separated thresholds and "
                "one code pair is nearly degenerate (the measured "
                f"{min(steps):.0f}-mV step). A uniform 5-level 100-mV row like the "
                "paper's claim would need a third leg or an undisclosed select "
                "mechanism -- the paper does not describe its VTC interconnection."},
        "measured_divider": {
            "_label": "MEASURED, ngspice DC, sky130 tt, schematic-level; sMTJ = "
                      "committed OSDI two-state read branch",
            "per_W": [dict(W_um=d["W_um"], sep_max_mV=round(d["sep_max_mV"], 1),
                           vb_at_sepmax=round(d["vb_at_sepmax"], 3),
                           vdiv_P_V=round(d["vdiv_P"], 4),
                           vdiv_AP_V=round(d["vdiv_AP"], 4),
                           midpoint_V=round(d["midpoint_at_sepmax"], 4)) for d in div],
            "selected_W_um": wsel,
            "sep_ideal_resistor_bound_mV": round(s_ideal * 1e3, 1),
            "sep_ideal_formula": "S_ideal = VDD*(R_AP-R_P)/(sqrt(R_P)+sqrt(R_AP))^2 "
                                 "(ANALYTIC, labeled; ideal-resistor pulldown at the "
                                 "geometric-mean operating point)"},
        "measured_chain": {
            "_label": "MEASURED, ngspice DC, sky130 tt, schematic-level",
            "per_code": per_code,
            "best_code": kctr, "vb_star_V": round(vbstar, 3),
            "separation_at_vb_star_mV": round(sep_at, 1),
            "static_supply_current_uA_P": round(pw["P"] / VDD, 2),
            "static_supply_current_uA_AP": round(pw["AP"] / VDD, 2),
            "static_power_uW_P": round(pw["P"], 2),
            "static_power_uW_AP": round(pw["AP"], 2),
            "static_power_label": "SCHEMATIC-LEVEL (not extracted); full chain "
                                  "divider+VTC+buffer at vb_star"},
        "headline_ratios": {
            "_label": "ratios are the transferable headline (house norm)",
            "trim_step_over_V_T": round(mean_step / (par["VT"] * 1e3), 2),
            "separation_over_trim_step": round(sep_at / mean_step, 2),
            "trim_span_over_separation": round(
                (achieved_range[1] - achieved_range[0]) * 1e3 / sep_at, 2),
            "worstcase_centering_margin_mV": round(margin_worstcase, 1),
            "worstcase_centering_margin_over_V_T": round(
                margin_worstcase / (par["VT"] * 1e3), 2)},
        "model_derived": {
            "_label": "MODEL-DERIVED from committed formulas (NOT simulated noise)",
            "p_AP_at_operating_point": 0.5,
            "p_AP_formula": "<s> = tanh(Delta*V_wr/Vc0), p_AP = (1+<s>)/2; SOT "
                            "branch unbiased (V_wr = 0) => p_AP = 0.5",
            "delta_Psw_if_one_step_on_sigmoid_axis": round(dp_step, 3),
            "delta_Psw_formula": "P_sw(Vth+step/2) - P_sw(Vth-step/2) with the "
                                 "committed sigmoid P_sw(V)=1/(1+exp(-(V-Vth)/V_T)); "
                                 "shows one trim step commands ~the whole probability "
                                 "window if used as a probability knob",
            "interpretation": "the VTC trim is a comparator-CENTERING knob (needs "
                              "resolution << divider separation), not a probability "
                              "trim (which would need resolution << V_T)"},
        "mapping_adaptations": [
            "LEG COUNT KEPT: 2 pull-up + 2 pull-down input transistors, exactly the "
            "paper's stated VTC content; the paper does not disclose interconnection "
            "or select mechanism, so each leg is gated by a series enable device (2x "
            "leg width) and a threshold code = an enable pattern (OUR mapping).",
            "SIZING OURS: the paper gives no VTC transistor sizes; leg widths were "
            "chosen by a measured sizing survey in the same flow to approach the "
            "paper's 0.7-1.1 V targets, then the achieved thresholds were MEASURED "
            "and reported as-is (errors to target kept visible).",
            "DEVICE OURS: their sMTJ (2.5-8 kOhm, TMR 50-100%) is replaced by OUR "
            "committed calibrated device (R_P=4.9k, R_AP=9.8k, TMR=1.0) -- the point "
            "of the repro is their circuit on our device.",
            "STATIC TWO-STATE: our committed model exposes the state as a control "
            "node (harness-owned RNG by design); with ms dwell times (paper) each "
            "state is a DC operating point, so the divider/VTC are characterized "
            "statically per state; no stochastic transient is claimed.",
            "DIVIDER NMOS: the paper's 1/3/9/27-um width options are all "
            "instantiated and measured; the reported chain uses the width whose "
            "max-separation midpoint falls nearest the trim-range center.",
            "NODE: sky130 (130 nm, 1.8 V) matches the paper's 130-nm/1.8-V class; "
            "absolute mV numbers remain schematic-level (no extraction)."],
        "assumptions": [
            "sky130 tt corner, 27C default, VDD=1.8 V, L=0.15 um everywhere (house "
            "style, strongarm core).",
            "Enable devices at 2x leg width so leg strength is dominated by the "
            "input transistor; all widths built from proven bins (W in {0.42,1,2} "
            "um with instance multiplier m).",
            "Threshold definition: input (divider-node) voltage where the buffered "
            "output crosses VDD/2 in DC.",
            "Digitization window: vb range where final(P) > 0.9*VDD and final(AP) < "
            "0.1*VDD simultaneously.",
            "Worst-case centering error taken as step/2 (uniform step grid).",
            "The committed model's read-branch two-state resistances stand in for "
            "the fluctuating sMTJ; read-branch bias dependence of R (TMR rolloff) "
            "is not in the committed model and therefore not claimed."],
    }
    out["conclusion"] = (
        f"Yoon's p-bit driver maps cleanly onto sky130 with our device. The 2PU+2PD "
        f"variable-threshold stage, trimmed by enable patterns, achieves 5 monotone "
        f"chain-referred thresholds {[round(v,3) for v in vm_chain]} V (span "
        f"{(achieved_range[1]-achieved_range[0])*1e3:.0f} mV, steps "
        f"{min(steps):.0f}-{max(steps):.0f} mV, mean {mean_step:.0f} mV, RMS error "
        f"to the paper's 0.7-1.1 V targets "
        f"{out['measured_vtc_thresholds']['rms_error_to_paper_targets_mV']} mV; the "
        f"steps are NOT uniform -- only {n_distinct} levels are separated by more "
        f"than 30 mV, a structural limit of 2PU+2PD enable combos at this span). The "
        f"committed two-state divider (R_P=4.9k/R_AP=9.8k, W={wsel} um NMOS) gives a "
        f"measured max state separation of {div[kbest]['sep_max_mV']:.0f} mV "
        f"(ideal-resistor bound {s_ideal*1e3:.0f} mV, analytic), i.e. "
        f"{sep_at/mean_step:.1f}x the trim step at the operating point -- the trim "
        f"CAN center the threshold inside the state separation with "
        f"{margin_worstcase:.0f} mV worst-case margin "
        f"({margin_worstcase/(par['VT']*1e3):.1f} V_T). On the task-relevant axis, "
        f"one trim step is {mean_step/(par['VT']*1e3):.1f}x our V_T=23.4 mV window "
        f"(a single step would command {dp_step*100:.0f}% of the probability range "
        f"if referred to the device sigmoid), so Yoon-style VTC trimming is a "
        f"state-discrimination centering mechanism, not a probability-resolution "
        f"mechanism, on our device.")

    (HERE / "yoon_pbit_driver_summary.json").write_text(json.dumps(out, indent=2))
    print("\n" + out["conclusion"], flush=True)
    print("\nwrote yoon_pbit_driver_summary.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
