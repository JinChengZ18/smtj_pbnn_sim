#!/usr/bin/env python3
"""Reproduction of PICO-RAM's comparator power-gating as a MEASURED energy ratio in our
sky130/ngspice flow (Zhiyu Chen et al., "PICO-RAM: A PVT-Insensitive Analog Compute-In-Memory
SRAM Macro with In-Situ Multi-Bit Charge Computing and 6T Thin-Cell-Compatible Layout",
IEEE JSSC 60:308, 2025; open preprint arXiv:2407.12829).

WHY THIS SCRIPT EXISTS
----------------------
PICO-RAM claims that gating the precise comparator of its local time-domain ADC with a cheap
coarse decision saves 55.8% of local-ADC energy with no accuracy loss. We reproduce the
PRIMITIVE (a coarse comparator power-gates a precise comparator's clock) at schematic level in
sky130 with OUR committed StrongARM as the precise comparator, and measure the per-decision
supply-energy ratio gated/ungated over a stated input ensemble. INTEGRITY rules: every energy
number in the JSON is integrated from an ngspice transient (i(Vsupply) INTEG); nothing is typed
by hand; analytic terms are LABELED analytic with their formulas.

PICO-RAM'S MECHANISM (verbatim quotes, arXiv:2407.12829, Section IV "Dual-Threshold
Time-Domain ADC")
-----------------------------------------------------------------------------------
  "A second low-power comparator (Cmp2) is added to power gate Cmp1 and TSPCs."
  "It has a slightly higher threshold (set by Vref) than Cmp1 to disable the main path of
   ADC most of the time."
  "Cmp2 is auto-zeroed by SAZ before conversion, allowing it to maintain a low-power profile
   with near-minimum sizing while achieving minimal offset."
  Result (their abstract/Sec. IV): "leading to a 55.8% energy reduction of the local ADCs
   without compromising accuracy."

MAPPING TO OUR PRIMITIVE (every adaptation documented; see "mapping" in the JSON)
---------------------------------------------------------------------------------
1. Their Cmp1 -> our committed StrongARM latch (exact sizing of
   eda/hero/comparators/strongarm.spice, nominal, no mismatch injection).
2. Their Cmp2 -> a near-minimum-size StrongARM (all devices W=0.42/L=0.15, the sky130 minimum
   width for the 01v8 fets) whose decision threshold is shifted by an OFFSET REFERENCE +-V_g,
   realized here as ideal series DC sources at the input-pair gates (in silicon: a reference
   ladder tap; in PICO-RAM: "set by Vref").
3. ONE-SIDED vs WINDOW: PICO-RAM needs only ONE Cmp2 because its ADC input is a monotonic
   time-domain ramp -- a single higher threshold is crossed strictly BEFORE Cmp1's threshold,
   so one coarse crossing marks "approaching ambiguity". Our primitive is a STATIC comparison
   (sign of a differential input), so the ambiguity band needs BOTH edges: we instantiate the
   SAME near-minimum Cmp2 twice, at thresholds +V_g and -V_g (the "dual threshold" of their
   ADC becomes a symmetric window). Input is ambiguous iff -V_g < vin < +V_g, i.e.
   amb = AND(NOT A, B) with A = (vin > +V_g) from Cmp2a, B = (vin > -V_g) from Cmp2b.
4. Power gating -> CLOCK gating of Cmp1 (a precharged StrongARM with clk held low draws only
   leakage, which the measurement includes). The gating is a REAL circuit in the netlist:
   amb = INV(NAND(outn_a, outp_b)); cclk1 = INV(NAND(clk_raw, amb)) with a WN=2/WP=4 driver.
   The BASELINE drives Cmp1 through a matched 2-stage buffer (INV+driver) from the same
   counted logic supply, so the local clock-driver energy is charged to BOTH modes and the
   gated overhead is only the delta (NAND vs INV stage-1 + amb logic + the two Cmp2s).
5. When amb=0 the answer is forced to A (Cmp2a's decision): vin > +V_g -> A=1 correct;
   vin < -V_g -> A=0=B correct. When amb=1, Cmp1 strobes and decides exactly as the baseline.

MEASUREMENT
-----------
One 12 ns decision window per input point: coarse strobe clk2 rises at 1 ns (held high so the
StrongARM outputs stay latched, falls at 9 ns), main strobe rises at 4 ns and falls at 7 ns
(decision sampled 2.9 ns after the strobe = the committed META meas_t of strongarm.spice),
integration 0..12 ns covers evaluation AND the following precharge recovery. Per-decision
energy per block = -VDD * INTEG(i(Vsupply)); separate supplies for Cmp1, Cmp2a, Cmp2b, logic.
Whether Cmp1 actually fired is MEASURED as MAX v(cclk1) in 3..8 ns.

ENSEMBLE (stated, and the headline depends on it)
-------------------------------------------------
vin_diff on a 60-point midpoint grid over +-10*V_T (V_T = 23.414 mV, the committed PBNN
sigmoid scale: inputs within +-V_T are the inherently near-random decisions). Reported
ensembles: uniform +-5*V_T (PRIMARY, 30 inner points), +-2*V_T and +-10*V_T (sensitivity).
Gating threshold V_g = V_T (the natural choice here: gate off exactly the decisions that are
deterministic at the PBNN scale). p_fire(analytic, uniform) = V_g/Vr, quoted next to measured.

ACCURACY
--------
Nominal (no-mismatch) gated-vs-ungated decision mismatches are counted on the same grid
(expected 0). The coarse-offset robustness is (a) an ANALYTIC LABELED term: a gating error
requires a coarse offset |delta| > V_g, P_err = 2*E[(delta-V_g)^+]/(2*Vr) for delta~N(0,s2),
E[(d-c)^+] = s*pdf(c/s) - c*Q(c/s), evaluated at s2 = Pelgrom AVT/sqrt(W*L) = 19.9 mV
(near-minimum, NO auto-zero) and s2 = 1.5 mV (the auto-zero residual target already cited in
eda/hero/readout_mapping.py) -- this is exactly why the paper auto-zeroes Cmp2; and (b) two
MEASURED spot checks with delta_b = +1.0 and +1.5 sigma injected into Cmp2b's reference.

MUST RUN IN WSL (native ngspice + sky130):
  wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd <repo> && python3 eda/design_survey/repro/picoram_gating.py [--smoke]'

Caveats: schematic-level (non-extracted) -> the RATIO is the deliverable, absolute fJ are
schematic-level; ideal input sources (no kickback loading from the 3 comparator front end);
offset references are ideal DC sources; tt corner, 27C, nominal only except the labeled spot
checks; our number is for the comparator-pair PRIMITIVE, PICO-RAM's 55.8% is for their WHOLE
local ADC (Cmp1 + TSPC counters gated, time-domain) -- comparable in spirit, not in scope.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = "/opt/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
RUN = HERE / "_picoram_gating.spice"

VDD = 1.8
VT = 0.023414                 # committed PBNN sigmoid scale [V] (eda/hero flow)
VG = VT                       # gating threshold choice: +-V_T ambiguity band
AVT_N = 5.0e-3                # sky130-class NMOS Pelgrom AVT [V*um] (same ASSUMPTION as run_offset_mc.py)
W2, L2 = 0.42, 0.15           # near-minimum Cmp2 device size [um]
SIGMA2 = AVT_N / math.sqrt(W2 * L2)   # coarse comparator input-pair sigma, no auto-zero [V]
SIGMA_AZ = 1.5e-3             # auto-zero residual TARGET [V] (cited in readout_mapping.py, not measured here)

T_END = "12n"
T_COARSE_MEAS = "3.8n"
T_MAIN_MEAS = "6.9n"          # main strobe at 4n + committed META meas_t=2.9n

PREAMBLE = """* PICO-RAM comparator power-gating repro ({mode}), sky130 schematic-level
.lib {lib} tt
Vdd1 vdd1 0 {vdd}
Vddl vddl 0 {vdd}
Vss vss 0 0
Vclk1 clk1raw 0 PULSE(0 {vdd} 4n 100p 100p 3n 100n)
Vinp vinp 0 0.9
Vinn vinn 0 0.9
* ---- Cmp1: committed StrongARM, exact sizing of eda/hero/comparators/strongarm.spice ----
XMtail1 ntail1 cclk1 vss vss sky130_fd_pr__nfet_01v8 W=4 L=0.15
XM11    da1   vinp  ntail1 vss sky130_fd_pr__nfet_01v8 W=4 L=0.15
XM12    db1   vinn  ntail1 vss sky130_fd_pr__nfet_01v8 W=4 L=0.15
XM13    outn1 outp1 da1    vss sky130_fd_pr__nfet_01v8 W=2 L=0.15
XM14    outp1 outn1 db1    vss sky130_fd_pr__nfet_01v8 W=2 L=0.15
XM15    outn1 outp1 vdd1  vdd1 sky130_fd_pr__pfet_01v8 W=2 L=0.15
XM16    outp1 outn1 vdd1  vdd1 sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp11   outp1 cclk1 vdd1  vdd1 sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp12   outn1 cclk1 vdd1  vdd1 sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp13   da1   cclk1 vdd1  vdd1 sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp14   db1   cclk1 vdd1  vdd1 sky130_fd_pr__pfet_01v8 W=2 L=0.15
"""

BASELINE_BLOCK = """* ---- baseline clock path: matched 2-stage buffer (counted on Vddl) ----
XIb1n nb  clk1raw vss  vss  sky130_fd_pr__nfet_01v8 W=1 L=0.15
XIb1p nb  clk1raw vddl vddl sky130_fd_pr__pfet_01v8 W=2 L=0.15
XIb2n cclk1 nb    vss  vss  sky130_fd_pr__nfet_01v8 W=2 L=0.15
XIb2p cclk1 nb    vddl vddl sky130_fd_pr__pfet_01v8 W=4 L=0.15
"""

CMP2 = """* ---- Cmp2{tag}: near-minimum StrongARM, threshold {thr_mV:+.3f} mV (offset reference) ----
Vo{tag}1 g{tag}1 vinp DC {os0:.6f}
Vo{tag}2 g{tag}2 vinn DC {os1:.6f}
Vdd2{tag} vdd2{tag} 0 {vdd}
XMtail2{tag} ntl2{tag} clk2 vss vss sky130_fd_pr__nfet_01v8 W={w} L={l}
XM21{tag} da2{tag}  g{tag}1  ntl2{tag} vss sky130_fd_pr__nfet_01v8 W={w} L={l}
XM22{tag} db2{tag}  g{tag}2  ntl2{tag} vss sky130_fd_pr__nfet_01v8 W={w} L={l}
XM23{tag} outn{tag} outp{tag} da2{tag} vss sky130_fd_pr__nfet_01v8 W={w} L={l}
XM24{tag} outp{tag} outn{tag} db2{tag} vss sky130_fd_pr__nfet_01v8 W={w} L={l}
XM25{tag} outn{tag} outp{tag} vdd2{tag} vdd2{tag} sky130_fd_pr__pfet_01v8 W={w} L={l}
XM26{tag} outp{tag} outn{tag} vdd2{tag} vdd2{tag} sky130_fd_pr__pfet_01v8 W={w} L={l}
XMq1{tag} outp{tag} clk2 vdd2{tag} vdd2{tag} sky130_fd_pr__pfet_01v8 W={w} L={l}
XMq2{tag} outn{tag} clk2 vdd2{tag} vdd2{tag} sky130_fd_pr__pfet_01v8 W={w} L={l}
XMq3{tag} da2{tag}  clk2 vdd2{tag} vdd2{tag} sky130_fd_pr__pfet_01v8 W={w} L={l}
XMq4{tag} db2{tag}  clk2 vdd2{tag} vdd2{tag} sky130_fd_pr__pfet_01v8 W={w} L={l}
"""

GATED_LOGIC = """* ---- coarse strobe: rises 1n, held high (outputs stay latched), falls 9n ----
Vclk2 clk2 0 PULSE(0 {vdd} 1n 100p 100p 8n 100n)
* ---- amb = AND(outn_a, outp_b) : NAND2 + INV (counted on Vddl) ----
XNa1 n1 outna nx   vss  sky130_fd_pr__nfet_01v8 W=1 L=0.15
XNa2 nx outpb vss  vss  sky130_fd_pr__nfet_01v8 W=1 L=0.15
XNa3 n1 outna vddl vddl sky130_fd_pr__pfet_01v8 W=1 L=0.15
XNa4 n1 outpb vddl vddl sky130_fd_pr__pfet_01v8 W=1 L=0.15
XIa1 amb n1 vss  vss  sky130_fd_pr__nfet_01v8 W=1 L=0.15
XIa2 amb n1 vddl vddl sky130_fd_pr__pfet_01v8 W=2 L=0.15
* ---- cclk1 = AND(clk1raw, amb) : NAND2 + driver INV ----
XNb1 n2 clk1raw ny vss sky130_fd_pr__nfet_01v8 W=1 L=0.15
XNb2 ny amb    vss vss sky130_fd_pr__nfet_01v8 W=1 L=0.15
XNb3 n2 clk1raw vddl vddl sky130_fd_pr__pfet_01v8 W=1 L=0.15
XNb4 n2 amb     vddl vddl sky130_fd_pr__pfet_01v8 W=1 L=0.15
XIb1 cclk1 n2 vss  vss  sky130_fd_pr__nfet_01v8 W=2 L=0.15
XIb2 cclk1 n2 vddl vddl sky130_fd_pr__pfet_01v8 W=4 L=0.15
* ---- dummy inverter loads on the unused Cmp2 outputs (balance the latch loading) ----
XDa1 dmy1 outpa vss  vss  sky130_fd_pr__nfet_01v8 W=1 L=0.15
XDa2 dmy1 outpa vddl vddl sky130_fd_pr__pfet_01v8 W=1 L=0.15
XDb1 dmy2 outnb vss  vss  sky130_fd_pr__nfet_01v8 W=1 L=0.15
XDb2 dmy2 outnb vddl vddl sky130_fd_pr__pfet_01v8 W=1 L=0.15
"""

CONTROL = """.control
let vd = {start}
dowhile vd <= {stop}
  alter @vinp[dc] = 0.9 + vd/2
  alter @vinn[dc] = 0.9 - vd/2
  tran 10p {t_end}
  meas tran e1q INTEG i(vdd1) from=0 to={t_end}
  meas tran elq INTEG i(vddl) from=0 to={t_end}
{gated_meas}  meas tran d1p FIND v(outp1) at={t_main}
  meas tran d1n FIND v(outn1) at={t_main}
  meas tran ck1 MAX v(cclk1) from=3n to=8n
  echo PT $&vd $&e1q $&elq {gated_echo}$&d1p $&d1n $&ck1
  let vd = vd + {step}
end
quit
.endc
.end
"""

GATED_MEAS = """  meas tran e2aq INTEG i(vdd2a) from=0 to={t_end}
  meas tran e2bq INTEG i(vdd2b) from=0 to={t_end}
  meas tran vpa FIND v(outpa) at={t_coarse}
  meas tran vna FIND v(outna) at={t_coarse}
  meas tran vpb FIND v(outpb) at={t_coarse}
  meas tran vnb FIND v(outnb) at={t_coarse}
  meas tran vam FIND v(amb) at={t_coarse}
"""
GATED_ECHO = "$&e2aq $&e2bq $&vpa $&vna $&vpb $&vnb $&vam "


def build_netlist(mode: str, start: float, stop: float, step: float,
                  delta_a: float = 0.0, delta_b: float = 0.0) -> str:
    """mode in {baseline, gated}; delta_* = coarse offset injected into the reference [V]."""
    text = PREAMBLE.format(mode=mode, lib=LIB, vdd=VDD)
    if mode == "baseline":
        text += BASELINE_BLOCK
        gated_meas, gated_echo = "", ""
    else:
        thr_a = +VG + delta_a          # Cmp2a decides A = (vind > thr_a)
        thr_b = -VG + delta_b          # Cmp2b decides B = (vind > thr_b)
        for tag, thr in (("a", thr_a), ("b", thr_b)):
            text += CMP2.format(tag=tag, thr_mV=thr * 1e3, os0=-thr / 2, os1=+thr / 2,
                                vdd=VDD, w=W2, l=L2)
        text += GATED_LOGIC.format(vdd=VDD)
        gated_meas = GATED_MEAS.format(t_end=T_END, t_coarse=T_COARSE_MEAS)
        gated_echo = GATED_ECHO
    text += CONTROL.format(start=start, stop=stop, step=step, t_end=T_END,
                           t_main=T_MAIN_MEAS, gated_meas=gated_meas, gated_echo=gated_echo)
    return text


def run_case(name: str, netlist: str) -> list[dict]:
    RUN.write_text(netlist)
    out = subprocess.run(["ngspice", "-b", RUN.name], cwd=HERE,
                         capture_output=True, text=True).stdout
    pts, bad = [], 0
    for line in out.splitlines():
        if not line.startswith("PT "):
            continue
        toks = line.split()[1:]
        try:
            v = [float(t) for t in toks]
        except ValueError:
            bad += 1
            continue
        if len(v) == 6:      # baseline: vd e1q elq d1p d1n ck1
            pts.append(dict(vd=v[0], e1=-VDD * v[1], el=-VDD * v[2],
                            d1p=v[3], d1n=v[4], ck1=v[5]))
        elif len(v) == 13:   # gated: vd e1q elq e2aq e2bq vpa vna vpb vnb vam d1p d1n ck1
            pts.append(dict(vd=v[0], e1=-VDD * v[1], el=-VDD * v[2],
                            e2a=-VDD * v[3], e2b=-VDD * v[4],
                            vpa=v[5], vna=v[6], vpb=v[7], vnb=v[8], vam=v[9],
                            d1p=v[10], d1n=v[11], ck1=v[12]))
        else:
            bad += 1
    print(f"[{name}] {len(pts)} points parsed, {bad} malformed", flush=True)
    if bad:
        print(f"[{name}] WARNING: {bad} malformed PT lines (a meas failed?)", flush=True)
    return pts


def decisions(base: list[dict], gated: list[dict]):
    """Per-point: baseline answer, gated answer, fired flag. Returns list of dicts keyed by vd."""
    rows = []
    for b, g in zip(base, gated):
        assert abs(b["vd"] - g["vd"]) < 1e-9
        ans_b = 1 if (b["d1p"] - b["d1n"]) > 0 else 0
        fired = g["ck1"] > 0.9 * VDD
        amb = g["vam"] > 0.5 * VDD
        if amb:
            ans_g = 1 if (g["d1p"] - g["d1n"]) > 0 else 0
        else:
            ans_g = 1 if (g["vpa"] - g["vna"]) > 0 else 0     # forced answer = A
        e_gated = g["e1"] + g["el"] + g["e2a"] + g["e2b"]
        e_base = b["e1"] + b["el"]
        rows.append(dict(vd=b["vd"], e_base=e_base, e_gated=e_gated, fired=fired,
                         amb=amb, ans_base=ans_b, ans_gated=ans_g,
                         err=int(ans_b != ans_g),
                         g_parts=dict(cmp1=g["e1"], cmp2a=g["e2a"], cmp2b=g["e2b"],
                                      logic=g["el"])))
    return rows


def ensemble_stats(rows: list[dict], vr: float) -> dict:
    sel = [r for r in rows if abs(r["vd"]) <= vr]
    n = len(sel)
    eb = sum(r["e_base"] for r in sel) / n
    eg = sum(r["e_gated"] for r in sel) / n
    return dict(range_mV=vr * 1e3, n_points=n,
                E_base_fJ=eb * 1e15, E_gated_fJ=eg * 1e15,
                ratio_gated_over_ungated=eg / eb, saving_pct=100 * (1 - eg / eb),
                p_fire_measured=sum(r["fired"] for r in sel) / n,
                p_fire_analytic_uniform=min(1.0, VG / vr),
                error_rate=sum(r["err"] for r in sel) / n)


def q_fn(x: float) -> float:
    return 0.5 * math.erfc(x / math.sqrt(2))


def excess_mean(sigma: float, c: float) -> float:
    """E[(delta - c)^+] for delta ~ N(0, sigma^2)."""
    return sigma * math.exp(-0.5 * (c / sigma) ** 2) / math.sqrt(2 * math.pi) - c * q_fn(c / sigma)


def p_err_analytic(sigma: float, vr: float) -> float:
    """ANALYTIC gating-error probability, uniform ensemble +-vr, thresholds +-VG,
    iid N(0,sigma^2) offset per coarse comparator: gating forces a WRONG unambiguous answer
    only where a coarse threshold crossed zero, P = 2*E[(delta-VG)^+]/(2*vr)."""
    return 2 * excess_mean(sigma, VG) / (2 * vr)


def main() -> None:
    smoke = "--smoke" in sys.argv
    if smoke:
        start, stop, step = -0.20, 0.19, 0.19          # 3 points: easy-low, ambiguous, easy-high
    else:
        n, vmax = 60, 10 * VT                          # 60 midpoints over +-10*V_T
        step = 2 * vmax / n
        start, stop = -vmax + step / 2, vmax

    base = run_case("baseline", build_netlist("baseline", start, stop, step))
    gated = run_case("gated", build_netlist("gated", start, stop, step))
    if len(base) != len(gated) or not base:
        print("FATAL: point-count mismatch or empty run; not writing a summary.")
        sys.exit(2)
    rows = decisions(base, gated)
    for r in rows:
        print(f"  vd={r['vd']*1e3:+8.3f} mV  E_base={r['e_base']*1e15:8.2f} fJ  "
              f"E_gated={r['e_gated']*1e15:8.2f} fJ  fired={int(r['fired'])}  "
              f"ans {r['ans_base']}/{r['ans_gated']}  err={r['err']}", flush=True)
    if smoke:
        print("\nSMOKE ONLY -- no JSON written.")
        return

    ens = {f"uniform_pm{k}VT": ensemble_stats(rows, k * VT) for k in (2, 5, 10)}
    primary = ens["uniform_pm5VT"]

    # measured mismatch spot checks: delta_b injected into Cmp2b's offset reference
    spots = []
    for mult in (1.0, 1.5):
        db = mult * SIGMA2
        g2 = run_case(f"gated_db{mult:g}sig",
                      build_netlist("gated", start, stop, step, delta_b=db))
        if len(g2) == len(base):
            r2 = decisions(base, g2)
            s = ensemble_stats(r2, 5 * VT)
            spots.append(dict(delta_b_mV=db * 1e3, delta_b_sigma=mult,
                              coarse_threshold_b_mV=(-VG + db) * 1e3,
                              error_rate_pm5VT=s["error_rate"],
                              p_fire_pm5VT=s["p_fire_measured"],
                              ratio_pm5VT=s["ratio_gated_over_ungated"]))
        else:
            spots.append(dict(delta_b_sigma=mult, status="RUN FAILED (point-count mismatch)"))

    summ = {
        "design": "PICO-RAM comparator power-gating",
        "reference": {
            "paper": "Zhiyu Chen et al., PICO-RAM ... 6T Thin-Cell-Compatible Layout, IEEE JSSC 60(1):308, 2025",
            "open_preprint": "arXiv:2407.12829",
            "mechanism_quotes": [
                "A second low-power comparator (Cmp2) is added to power gate Cmp1 and TSPCs.",
                "It has a slightly higher threshold (set by Vref) than Cmp1 to disable the main path of ADC most of the time.",
                "Cmp2 is auto-zeroed by SAZ before conversion, allowing it to maintain a low-power profile with near-minimum sizing while achieving minimal offset.",
                "leading to a 55.8% energy reduction of the local ADCs without compromising accuracy.",
            ],
        },
        "flow": "sky130A tt, ngspice (WSL), schematic-level (non-extracted), VDD=1.8 V, 27C; "
                "per-decision energy = -VDD*INTEG(i(Vsupply)) over one 12 ns decision window "
                "(evaluation + precharge recovery); Cmp1-fired is MEASURED as MAX v(cclk1).",
        "mapping": {
            "cmp1": "committed StrongARM, exact sizing of eda/hero/comparators/strongarm.spice (28 um total W), nominal",
            "cmp2": f"near-minimum StrongARM, all devices W={W2}/L={L2} um (sky130 01v8 minimum width), "
                    f"~{28/(11*W2):.1f}x less device width than Cmp1",
            "one_sided_vs_window": "PICO-RAM uses ONE Cmp2 (its ADC input is a monotonic time-domain ramp; "
                                   "a single higher threshold is crossed before Cmp1's). Our primitive is a STATIC "
                                   "comparison, so the ambiguity band needs both edges: the same near-minimum Cmp2 is "
                                   "instantiated TWICE at +-V_g (their dual threshold becomes a symmetric window).",
            "gating": "real in-netlist clock gating: amb=INV(NAND(outn_a,outp_b)); cclk1=INV(NAND(clk_raw,amb)); "
                      "baseline uses a matched 2-stage buffer on the same counted logic supply, so clock-driver "
                      "energy is charged to both modes",
            "offset_reference": "ideal series DC sources at the Cmp2 input-pair gates (in silicon: reference-ladder tap; "
                                "in PICO-RAM: 'set by Vref')",
        },
        "gating_threshold": {
            "V_g_mV": VG * 1e3,
            "choice": "V_g = V_T = 23.414 mV, the committed PBNN sigmoid scale: only decisions inside the "
                      "inherently near-random +-V_T band strobe the precise comparator",
        },
        "ensemble": {
            "grid": "60 midpoints, uniform over +-10*V_T (+-234.14 mV differential, 0.9 V common mode)",
            "primary": "uniform +-5*V_T (30 inner points)",
            "note": "the headline ratio DEPENDS on the ensemble width (wider range -> more gated-off easy "
                    "decisions -> larger saving); three widths reported",
        },
        "headline": {
            "measured_energy_ratio_gated_over_ungated": primary["ratio_gated_over_ungated"],
            "measured_saving_pct": primary["saving_pct"],
            "ensemble": "uniform +-5*V_T",
            "p_fire_cmp1_measured": primary["p_fire_measured"],
            "decision_error_rate_nominal": primary["error_rate"],
        },
        "ensembles": ens,
        "per_point": [dict(vd_mV=r["vd"] * 1e3, E_base_fJ=r["e_base"] * 1e15,
                           E_gated_fJ=r["e_gated"] * 1e15, cmp1_fired=bool(r["fired"]),
                           ans_base=r["ans_base"], ans_gated=r["ans_gated"], err=r["err"],
                           gated_parts_fJ={k: v * 1e15 for k, v in r["g_parts"].items()})
                      for r in rows],
        "accuracy_vs_coarse_offset": {
            "measured_nominal_error_rate": primary["error_rate"],
            "analytic_model_LABELED": {
                "formula": "P_err = 2*E[(delta-V_g)^+]/(2*V_r), E[(d-c)^+] = s*pdf(c/s)-c*Q(c/s), "
                           "delta~N(0,s^2) per coarse comparator; error requires a coarse threshold "
                           "to cross zero, i.e. |delta| > V_g",
                "sigma2_no_autozero_mV": SIGMA2 * 1e3,
                "sigma2_no_autozero_note": f"Pelgrom AVT={AVT_N*1e3:.1f} mV.um / sqrt({W2}*{L2}) -- near-minimum "
                                           "Cmp2 WITHOUT auto-zero (ASSUMED AVT, same as run_offset_mc.py)",
                "P_err_no_autozero_pm5VT": p_err_analytic(SIGMA2, 5 * VT),
                "sigma2_autozero_target_mV": SIGMA_AZ * 1e3,
                "P_err_autozero_pm5VT": p_err_analytic(SIGMA_AZ, 5 * VT),
                "conclusion": "near-minimum sizing alone (sigma ~ 0.85*V_g) would break the no-accuracy-loss "
                              "claim; the auto-zero the paper applies to Cmp2 ('auto-zeroed by SAZ') is what "
                              "makes near-minimum sizing safe -- consistent with their design choice",
            },
            "measured_spot_checks_delta_b": spots,
        },
        "comparison_to_paper": {
            "picoram_claim": "55.8% energy reduction of the local ADCs, no accuracy loss",
            "scope_difference": "PICO-RAM's number is for their WHOLE local time-domain ADC (Cmp1 + TSPC "
                                "counters power-gated, monotonic-ramp input, one Cmp2, auto-zeroed); ours is the "
                                "comparator-pair PRIMITIVE (StrongARM Cmp1 clock-gated by a near-minimum window "
                                "pair) on a static input ensemble -- qualitatively comparable, not the same scope",
            "our_measured_saving_pct_primary": primary["saving_pct"],
        },
        "assumptions": [
            "schematic-level, non-extracted: RATIOS are the deliverable; absolute fJ are schematic-level",
            "ideal differential input sources (comparator kickback does not disturb the source)",
            "offset references +-V_g are ideal DC sources in series with the input-pair gates",
            "tt corner, 27C, nominal devices except the labeled offset spot checks",
            "uniform input ensemble (stated widths); the ratio transfers only with the ensemble stated",
            "coarse strobe leads the main strobe by 3 ns in a 12 ns window (single-cycle primitive; "
            "PICO-RAM's time-domain ADC amortizes the coarse decision differently)",
            f"AVT={AVT_N*1e3:.1f} mV.um is a sky130-class assumption (not the PDK mismatch model), "
            "reused from run_offset_mc.py for consistency",
        ],
        "reproduce": "wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd <repo> && python3 eda/design_survey/repro/picoram_gating.py'",
    }
    out = HERE / "picoram_gating_summary.json"
    out.write_text(json.dumps(summ, indent=2))
    print(f"\nPRIMARY (uniform +-5*V_T): E_gated/E_base = {primary['ratio_gated_over_ungated']:.3f} "
          f"(saving {primary['saving_pct']:.1f}%), p_fire = {primary['p_fire_measured']:.2f}, "
          f"errors = {primary['error_rate']:.3f}")
    print(f"-> {out.name}")


if __name__ == "__main__":
    main()
