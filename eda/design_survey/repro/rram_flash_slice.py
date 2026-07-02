#!/usr/bin/env python3
"""Tier-0 reproduction: the flash-ADC readout SLICE of the RRAM XNOR-BNN macro
(S. Yin, X. Sun, S. Yu, J.-S. Seo, IEEE TED 67(10):4185, 2020; open preprint
arXiv:1909.07514), rebuilt in OUR sky130 + ngspice flow so its two comparison axes
(code-edge offset, readout energy per conversion) are measured in the SAME flow as
our column-shared SAR -- not transcribed from the paper.

WHAT THE OPEN RECORD SAYS (verbatim, arXiv:1909.07514)
-------------------------------------------------------
* "the testchip design includes a 128x64 1T1R array, row decoder, level shifter,
  eight 8-to-1 column multiplexers, eight 3-bit flash ADCs, and two 64-to-1 column
  decoders for RRAM cell-level programming."
* "Each 3-bit flash ADC consists of seven voltage-mode sense amplifiers (VSAs),
  whose outputs generate seven thermometer-coded bits that represent eight levels."
* "Each VSA compares the read bitline (RBL) voltage of the selected column with a
  reference voltage. Seven reference voltages of an ADC are calibrated for the
  eight columns that the ADC is connected to."
* "To make a balance between area and throughput, we share one flash ADC by eight
  columns."
* "our VSA and ADC design did not include offset compensation circuits or
  techniques."

WHAT THIS SCRIPT BUILDS (one slice = 1/8 of their readout, mapped to OUR flow)
------------------------------------------------------------------------------
* ONE 3-bit flash ADC: 7 comparators strobed in parallel. Comparator = OUR
  StrongARM latch SA, sizing read VERBATIM from eda/hero/comparators/strongarm.spice
  (their VSA schematic is not public; StrongARM is the same-flow voltage-mode SA,
  and matches their "no offset compensation" statement).
* Reference generation: a resistor ladder giving 7 UNIFORM taps across the
  popcount-mapped input range of OUR readout (fan-in 256). Yin et al. instead use
  per-ADC CALIBRATED references over a CONFINED bitcount range (-13..11 out of
  +-64); the generation circuit is not public. The ladder is our sky130 vehicle
  for "7 static reference levels"; the deviation is documented in the JSON.
* ONE 8-to-1 CMOS transmission-gate input mux (repo TG sizing, sar_capdac_tran.py),
  channel 0 selected, 7 off channels loading the shared node as in a real mux.

INPUT RANGE (OUR readout mapping, stated -- fan-in 256 is not a row of
readout_mapping_summary.json, so it is DERIVED from the committed law):
  readout_mapping.py law: PC_FS = 3*sqrt(F) = 48 @ F=256; LSB_V = V_in/(2*PC_FS)
  with V_in = 0.6 V (StrongARM usable differential swing, repo headline case)
  -> LSB_V = 6.25 mV/popcount, TIA output = V_CM +- V_in/2 = 0.9 +- 0.3 V.
  Flash range [0.6, 1.2] V, taps at 0.675..1.125 V (75 mV = 12 popcounts / flash LSB).

MEASUREMENTS
------------
(a) mc     : per-code-edge input-referred offset. Pelgrom Vth mismatch (AVT =
             5 mV*um, the repo assumption) injected on the SAME four devices per
             comparator as run_offset_mc.py (input pair + latch pair), 28 draws
             per MC sample, all 7 comparators simulated TOGETHER (shared mux node,
             shared ladder -> kickback crosstalk included). Per-edge offset = input
             sweep value where that comparator's decision flips, minus the ideal tap.
(b) energy : transient supply energy of one full conversion (all 7 comparators
             strobed at once), code-averaged over all 8 codes; ladder static power
             measured from its own rail; clock-driver and mux-select energies
             measured separately. SCHEMATIC-LEVEL (no extraction) -- the flash/SAR
             comparison is made as RATIOS against our own schematic-level single
             StrongARM measured in the same deck style.
(c) ron    : TG mux on-resistance across the input range (DC), vs the ladder
             Thevenin impedance (exact circuit math) -> mux insertion effect.

RUN (WSL, native ngspice + sky130):
  wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd <repo> && \
      python3 eda/design_survey/repro/rram_flash_slice.py all [N] [workers]'
  subcommands: smoke | mc [N] [workers] | energy | ron | summarize
"""
from __future__ import annotations

import json
import math
import random
import re
import statistics
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RUNDIR = HERE / "_flash_runs"
SA_NETLIST = REPO / "eda" / "hero" / "comparators" / "strongarm.spice"
LIB = "/opt/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
OUT_JSON = HERE / "rram_flash_slice_summary.json"

# ---------------------------------------------------------------- design constants
VT = 0.023414                  # Bernoulli window V_T [V] (repo constant)
AVT_N = 5.0e-3                 # sky130-class NMOS Pelgrom AVT [V*um] (repo ASSUMPTION)
V_LO, V_HI = 0.6, 1.2          # popcount-mapped TIA output range, fan-in 256 (see header)
V_CM = 0.9
NBITS = 3
NCOMP = 2**NBITS - 1           # 7
LSB_FLASH = (V_HI - V_LO) / 2**NBITS          # 75 mV
LSB_V_PC = 0.00625             # 6.25 mV/popcount (readout_mapping law @ F=256, V_in=0.6)
TAPS = [round(V_LO + k * LSB_FLASH, 6) for k in range(1, 8)]   # 0.675 .. 1.125
R_TI = 1225.0                  # ohm = LSB_V_PC / LSB_I (5.102 uA/pc) -- TIA Thevenin R
# Kickback sizing is a MEASURED design constraint, not a free choice. Two failure
# modes were hit and fixed during bring-up (see `diag` subcommand + JSON notes):
#  (1) a first-cut 10 uA / 180 kohm BARE-tap string: the StrongARM strobe kick
#      (~4-5 fC of gate charge per comparator) collapsed tap4 from 0.900 V to 0.52 V
#      -> every code edge railed HIGH;
#  (2) stiff taps (100 uA + decaps) with a bare shared input node: the SHARED input
#      is kicked by all SEVEN comparators while each tap takes only one comparator's
#      kick -> every code edge railed LOW. Placing the matching cap on the BITLINE
#      side of the mux does NOT fix this: the mux R_on isolates it, so the input
#      node still takes the full instantaneous kick (measured intermediate state).
# The committed design therefore KICK-MATCHES the two networks AT THE NODES: a
# C_ADC = 7 x C_tap decap DIRECTLY on the shared flash input node, so both
# comparator terminals deflect by ~ the same Q/C during the strobe and the
# differential error largely cancels; the residual mean edge shift is MEASURED and
# reported (Yin et al.'s per-ADC reference CALIBRATION would absorb exactly this
# kind of systematic). The price -- also measured -- is that C_ADC slows channel
# switching through the mux (tau = (R_TI + R_on) * C_ADC), the true mux-insertion
# cost of hanging a latch-type comparator bank directly on a muxed input.
I_LADDER = 100e-6              # ladder standing current [A] (kickback-recovery bound)
C_DECAP = 0.5e-12              # per-tap decoupling cap [F]
C_ADC = 7 * C_DECAP            # kick-matching decap on the shared input node [F]
R_SEG = LSB_FLASH / I_LADDER               # 750 ohm per 75 mV segment
R_END = (V_LO + LSB_FLASH) / I_LADDER      # 6.75 kohm (0 -> 0.675 and 1.125 -> 1.8)
R_TOTAL = 2 * R_END + 6 * R_SEG            # 18 kohm across 1.8 V
T_CYCLE = 10e-9                # conversion cycle [ns] (strobe + precharge), repo clk period
SEED = 20260702

MC_SWEEP = 0.040               # +-40 mV around each ideal tap (matches run_offset_mc range)
MC_STEP = 0.004                # 4 mV; adds sqrt(step^2/12)=1.2mV quantization in quadrature
                               # to a ~9 mV sigma -> <1% inflation (documented)

# ---------------------------------------------------------------- comparator factory
def load_sa_core():
    """Element lines + META of the committed StrongARM netlist (read-only reuse)."""
    text = SA_NETLIST.read_text()
    meta = re.search(r"^\*\s*META\s+(.*)$", text, re.MULTILINE).group(1)
    win = float(re.search(r"win_default=([\d.]+)", meta).group(1))
    wl_exprs = re.search(r"wl=(\S+)", meta).group(1).split(",")
    wl = [eval(e, {"__builtins__": {}}, {"win": win}) for e in wl_exprs]  # noqa: S307
    lines = [ln for ln in text.splitlines()
             if ln.strip() and not ln.startswith("*")]
    return lines, win, [AVT_N / math.sqrt(a) for a in wl]


def sa_instance(k, lines, win, offs, vdd_node="vdd"):
    """Instance k (1..7) of the committed StrongARM core: element names suffixed,
    local nodes renamed, vinp -> shared mux node `vin`, vinn -> ladder tap k."""
    local = {"vinp": "vin", "vinn": f"tap{k}",
             "g1": f"g1_{k}", "g2": f"g2_{k}", "g3": f"g3_{k}", "g4": f"g4_{k}",
             "ntail": f"nt_{k}", "da": f"da_{k}", "db": f"db_{k}",
             "outp": f"op{k}", "outn": f"on{k}", "vdd": vdd_node}
    out = []
    for ln in lines:
        toks = ln.split()
        toks[0] = f"{toks[0]}_{k}"
        toks = [local.get(t, t) for t in toks]
        out.append(" ".join(toks))
    return "\n".join(out).format(win=win, os0=offs[0], os1=offs[1],
                                 os2=offs[2], os3=offs[3])


# ---------------------------------------------------------------- netlist pieces
def ladder(rail="vddl"):
    lines = [f"RlT {rail} tap7 {R_END:.1f}"]
    for k in range(7, 1, -1):
        lines.append(f"Rl{k} tap{k} tap{k-1} {R_SEG:.1f}")
    lines.append(f"RlB tap1 0 {R_END:.1f}")
    for k in range(1, 8):
        lines.append(f"Cdec{k} tap{k} 0 {C_DECAP*1e12:.1f}p")
    return "\n".join(lines)


def mux(body_p="vdd"):
    """8:1 TG mux: ch0 selected (src0 through R_TI), ch1..7 off (dummy bus).
    TG sizing = repo (sar_capdac_tran.py): nfet W=2/0.15, pfet W=4/0.15."""
    lines = ["Vsrc src0 0 DC 0.9",
             f"Rti0 src0 min0 {R_TI:.0f}",
             f"Cadc vin 0 {C_ADC*1e12:.2f}p",
             f"XTGn0 min0 mseln0 vin 0 sky130_fd_pr__nfet_01v8 W=2 L=0.15",
             f"XTGp0 min0 mselp0 vin {body_p} sky130_fd_pr__pfet_01v8 W=4 L=0.15",
             "Vmseln0 mseln0 0 1.8", "Vmselp0 mselp0 0 0",
             "Vdum dum0 0 DC 0.9",
             "Vmoffn moffn 0 0", "Vmoffp moffp 0 1.8"]
    for j in range(1, 8):
        lines += [f"Rti{j} dum0 min{j} {R_TI:.0f}",
                  f"XTGn{j} min{j} moffn vin 0 sky130_fd_pr__nfet_01v8 W=2 L=0.15",
                  f"XTGp{j} min{j} moffp vin {body_p} sky130_fd_pr__pfet_01v8 W=4 L=0.15"]
    return "\n".join(lines)


# ---------------------------------------------------------------- (a) offset MC
def mc_deck(offsets, edges, sweep=MC_SWEEP, step=MC_STEP):
    """One MC sample: full slice, per-edge vd sweep of the ch0 source around the
    ideal tap; decision read at 2.4 ns (clk high 0.5..2.6 ns -- the low-CM taps
    regenerate slowly, so the strobe is longer than the repo harness), 2.5 ns trans."""
    lines, win, _sig = load_sa_core()
    body = [f"* rram flash slice offset-MC sample (sky130)",
            f".lib {LIB} tt",
            "Vdd vdd 0 1.8", "Vss vss 0 0",
            "VddL vddl 0 1.8",
            "Vclk clk 0 PULSE(0 1.8 0.5n 50p 50p 2.1n 10n)",
            ladder(), mux()]
    for k in range(1, 8):
        body.append(sa_instance(k, lines, win, offsets[k - 1]))
    # foreach + `destroy all` (NOT dowhile + let): each tran otherwise accumulates
    # its plot in memory and the per-tran cost grows superlinearly with iteration
    # count -- a 147-tran loop slowed ~100x by its tail in bring-up. foreach keeps
    # the loop variable as a SHELL variable, immune to destroy.
    ctl = [".control"]
    for k in edges:
        n = int(round(2 * sweep / step)) + 1
        vals = " ".join(f"{TAPS[k-1] + (-sweep + i*step):.6f}" for i in range(n))
        ctl += [f"foreach vsw {vals}",
                "  alter @vsrc[dc] = $vsw",
                "  tran 5p 2.5n",
                f"  meas tran vop find v(op{k}) at=2.4n",
                f"  meas tran von find v(on{k}) at=2.4n",
                f"  echo PT {k} $vsw $&vop $&von",
                "  destroy all",
                "end"]
    ctl += ["quit", ".endc", ".end"]
    return "\n".join(body + ctl) + "\n"


def run_ngspice(deck_text, tag):
    RUNDIR.mkdir(exist_ok=True)
    deck = RUNDIR / f"_{tag}.spice"
    deck.write_text(deck_text)
    r = subprocess.run(["ngspice", "-b", deck.name], cwd=RUNDIR,
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    (RUNDIR / f"_{tag}.log").write_text(out)
    return out


def edge_offsets_from(out):
    """Parse PT lines (absolute swept input vsw) -> {edge: input-referred offset [V]}
    = zero-crossing of (vop-von) vs vsw, minus the ideal tap."""
    pts = {}
    for m in re.finditer(r"PT\s+(\d+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)",
                         out):
        k = int(m.group(1))
        pts.setdefault(k, []).append((float(m.group(2)),
                                      float(m.group(3)) - float(m.group(4))))
    res = {}
    for k, pp in pts.items():
        pp.sort()
        off = float("nan")
        for (v0, d0), (v1, d1) in zip(pp, pp[1:]):
            if d0 == d1 or (d0 < 0) == (d1 < 0):
                continue
            off = v0 - d0 * (v1 - v0) / (d1 - d0) - TAPS[k - 1]
            break
        res[k] = off
    return res


def draw_offsets(sample_idx, sig):
    rng = random.Random(SEED + sample_idx)
    return [[rng.gauss(0, s) for s in sig] for _ in range(NCOMP)]


def mc_sample(args):
    """Kept for the smoke/diag paths: one deck with several edges."""
    idx, edges = args
    _lines, _win, sig = load_sa_core()
    out = run_ngspice(mc_deck(draw_offsets(idx, sig), edges), f"flash_mc_s{idx}")
    offs = edge_offsets_from(out)
    rec = {"sample": idx, "edges_mV": {str(k): (offs.get(k, float("nan")) * 1e3)
                                      for k in edges}}
    (RUNDIR / f"mc_s{idx}.json").write_text(json.dumps(rec))
    return rec


def mc_edge_task(args):
    """ONE (sample, edge) pair per ngspice process (21 transients). ngspice-46's
    per-`tran` cost in a long control loop grows superlinearly with the number of
    already-run trans (measured ~40x by tran ~100 even with `destroy all`), so a
    147-tran per-sample deck stalls; 21-tran decks stay in the fast regime."""
    idx, k = args
    _lines, _win, sig = load_sa_core()
    out = run_ngspice(mc_deck(draw_offsets(idx, sig), edges=(k,)),
                      f"flash_mc_s{idx}e{k}")
    return idx, k, edge_offsets_from(out).get(k, float("nan"))


def cmd_mc(n, workers, edges=tuple(range(1, 8))):
    print(f"[mc] N={n} samples, {workers} workers, edges={list(edges)}, "
          f"one (sample,edge) per process", flush=True)
    per = {i: {} for i in range(n)}
    tasks = [(i, k) for i in range(n) for k in edges]
    ndone = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(mc_edge_task, t): t for t in tasks}
        for f in as_completed(futs):
            idx, k, off = f.result()
            per[idx][str(k)] = off * 1e3
            ndone += 1
            if len(per[idx]) == len(edges):
                rec = {"sample": idx, "edges_mV": per[idx]}
                (RUNDIR / f"mc_s{idx}.json").write_text(json.dumps(rec))
                print(f"  sample {idx} complete "
                      f"({ndone}/{len(tasks)} tasks): "
                      f"{ {k: round(v, 2) for k, v in per[idx].items()} }", flush=True)
    recs = [{"sample": i, "edges_mV": per[i]} for i in range(n) if per[i]]
    (RUNDIR / "mc_results.json").write_text(json.dumps(recs, indent=1))
    print("[mc] wrote _flash_runs/mc_results.json", flush=True)
    return recs


# ---------------------------------------------------------------- (b) energy
CODE_MID = [round(V_LO + (c + 0.5) * LSB_FLASH, 6) for c in range(8)]  # 0.6375..1.1625


def energy_deck():
    """Nominal slice, 9 conversion cycles (10 ns each; strobe high 2..4 ns of each
    cycle). Cycle 0 = settle (excluded). Cycles 1..8 step through all 8 codes.
    Mux switches ch0 -> ch1 at 46 ns (between strobes). Separate rails:
    vddc = 7 comparators, vddl = ladder, vddm = mux TG bodies, clk & selects own
    drivers -> each energy term measured on its own branch."""
    lines, win, _sig = load_sa_core()
    zero = [0.0, 0.0, 0.0, 0.0]
    # ch0 codes for cycles 0..4, ch1 codes for cycles 5..8 (all 8 codes in 1..8)
    ch0_seq = [CODE_MID[4], CODE_MID[0], CODE_MID[2], CODE_MID[4], CODE_MID[6]]
    ch1_seq = [CODE_MID[1], CODE_MID[3], CODE_MID[5], CODE_MID[7]]

    def pwl(seq, t0):
        pts, t, v = [], 0.0, seq[0]
        pts.append(f"0 {seq[0]}")
        for i, vv in enumerate(seq[1:], start=1):
            tsw = (t0 + i) * T_CYCLE * 1e9 - 4.5   # switch 5.5 ns into previous cycle
            pts.append(f"{tsw:.1f}n {v}")
            pts.append(f"{tsw + 0.2:.1f}n {vv}")
            v = vv
        return "PWL(" + " ".join(pts) + ")"

    body = ["* rram flash slice ENERGY transient (sky130, schematic-level)",
            f".lib {LIB} tt",
            "VddC vddc 0 1.8", "Vss vss 0 0",
            "VddL vddl 0 1.8", "VddM vddm 0 1.8",
            "Vclk clk 0 PULSE(0 1.8 2n 100p 100p 2n 10n)",
            ladder(),
            # mux: ch0 active src (PWL codes), ch1 active-after-switch, 2..7 off
            f"Vsrc src0 0 {pwl(ch0_seq, 0)}",
            f"Rti0 src0 min0 {R_TI:.0f}",
            f"Cadc vin 0 {C_ADC*1e12:.2f}p",
            "XTGn0 min0 sn0 vin 0 sky130_fd_pr__nfet_01v8 W=2 L=0.15",
            "XTGp0 min0 sp0 vin vddm sky130_fd_pr__pfet_01v8 W=4 L=0.15",
            "Vsn0 sn0 0 PWL(0 1.8 45.8n 1.8 46n 0)",
            "Vsp0 sp0 0 PWL(0 0 45.8n 0 46n 1.8)",
            f"Vsrc1 src1 0 {pwl(ch1_seq, 5)}",
            f"Rti1 src1 min1 {R_TI:.0f}",
            "XTGn1 min1 sn1 vin 0 sky130_fd_pr__nfet_01v8 W=2 L=0.15",
            "XTGp1 min1 sp1 vin vddm sky130_fd_pr__pfet_01v8 W=4 L=0.15",
            "Vsn1 sn1 0 PWL(0 0 45.8n 0 46n 1.8)",
            "Vsp1 sp1 0 PWL(0 1.8 45.8n 1.8 46n 0)",
            "Vdum dum0 0 DC 0.9", "Vmoffn moffn 0 0", "Vmoffp moffp 0 1.8"]
    for j in range(2, 8):
        body += [f"Rti{j} dum0 min{j} {R_TI:.0f}",
                 f"XTGn{j} min{j} moffn vin 0 sky130_fd_pr__nfet_01v8 W=2 L=0.15",
                 f"XTGp{j} min{j} moffp vin vddm sky130_fd_pr__pfet_01v8 W=4 L=0.15"]
    for k in range(1, 8):
        body.append(sa_instance(k, lines, win, zero, vdd_node="vddc"))
    ctl = [".control", "tran 10p 90n",
           "let pclk = -v(clk)*vclk#branch",
           "let pmux = -v(sn0)*vsn0#branch - v(sp0)*vsp0#branch "
           "- v(sn1)*vsn1#branch - v(sp1)*vsp1#branch"]
    for c in range(1, 9):
        t0, t1 = c * 10, (c + 1) * 10
        ctl += [f"meas tran qc{c} INTEG vddc#branch from={t0}n to={t1}n",
                f"meas tran eck{c} INTEG pclk from={t0}n to={t1}n",
                f"echo EC {c} $&qc{c} $&eck{c}"]
    ctl += ["meas tran ql INTEG vddl#branch from=10n to=90n",
            "echo EL $&ql",
            "meas tran emux INTEG pmux from=44n to=50n",
            "echo EMUX $&emux",
            # kickback on ladder taps during cycle-2 strobe (22..24n), residual at 29.9n
            "meas tran t4min MIN v(tap4) from=21n to=26n",
            "meas tran t4max MAX v(tap4) from=21n to=26n",
            "meas tran t4res FIND v(tap4) at=31.9n",
            "meas tran t1min MIN v(tap1) from=21n to=26n",
            "meas tran t1max MAX v(tap1) from=21n to=26n",
            "meas tran t1res FIND v(tap1) at=31.9n",
            "echo KICK $&t4min $&t4max $&t4res $&t1min $&t1max $&t1res",
            # shared input node settling: after mux switch (ch1 code1 target at 51.9n)
            "meas tran vin_a FIND v(vin) at=51.9n",
            "meas tran vin_b FIND v(vin) at=61.9n",
            "echo VINSET $&vin_a $&vin_b",
            "quit", ".endc", ".end"]
    return "\n".join(body + ctl) + "\n"


def single_comp_deck():
    """Same-flow single StrongARM reference (schematic-level, ideal sources,
    half-LSB overdrive 37.5 mV) -- denominator for flash/SAR comparator ratios."""
    lines, win, _sig = load_sa_core()
    body = ["* single StrongARM reference cycle energy (sky130, schematic-level)",
            f".lib {LIB} tt",
            "VddC vddc 0 1.8", "Vss vss 0 0",
            "Vclk clk 0 PULSE(0 1.8 2n 100p 100p 2n 10n)",
            "Vinp vin 0 DC 0.9375",
            f"Vinn tap1 0 DC {TAPS[3]}",   # tap4 = 0.900 V; node named tap1 for reuse
            sa_instance(1, lines, win, [0.0] * 4, vdd_node="vddc")]
    ctl = [".control", "tran 10p 90n"]
    for c in range(1, 9):
        t0, t1 = c * 10, (c + 1) * 10
        ctl += [f"meas tran qc{c} INTEG vddc#branch from={t0}n to={t1}n",
                f"echo EC {c} $&qc{c} 0"]
    ctl += ["quit", ".endc", ".end"]
    return "\n".join(body + ctl) + "\n"


def parse_energy(out):
    cyc = {}
    for m in re.finditer(r"EC\s+(\d)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", out):
        cyc[int(m.group(1))] = (1.8 * -float(m.group(2)),   # E from vddc [J]
                                float(m.group(3)))          # E from clk driver [J]
    res = {"E_comp_cycle_fJ": {c: v[0] * 1e15 for c, v in cyc.items()},
           "E_clk_cycle_fJ": {c: v[1] * 1e15 for c, v in cyc.items()}}
    m = re.search(r"EL\s+([-+0-9.eE]+)", out)
    if m:
        res["E_ladder_8cyc_fJ"] = 1.8 * -float(m.group(1)) * 1e15
    m = re.search(r"EMUX\s+([-+0-9.eE]+)", out)
    if m:
        res["E_mux_transition_fJ"] = float(m.group(1)) * 1e15
    m = re.search(r"KICK\s+" + r"\s+".join([r"([-+0-9.eE]+)"] * 6), out)
    if m:
        g = [float(x) for x in m.groups()]
        res["kickback"] = {"tap4_min_V": g[0], "tap4_max_V": g[1], "tap4_at_29p9n_V": g[2],
                           "tap1_min_V": g[3], "tap1_max_V": g[4], "tap1_at_29p9n_V": g[5]}
    m = re.search(r"VINSET\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", out)
    if m:
        res["vin_after_mux_switch_V"] = {"at_51p9n": float(m.group(1)),
                                         "at_61p9n": float(m.group(2))}
    return res


def cmd_energy():
    print("[energy] flash slice transient (90 ns, 9 cycles)...", flush=True)
    out = run_ngspice(energy_deck(), "flash_energy")
    res = parse_energy(out)
    print("[energy] single-comparator reference transient...", flush=True)
    out1 = run_ngspice(single_comp_deck(), "flash_single_comp")
    res1 = parse_energy(out1)
    res["single_comp_E_cycle_fJ"] = res1.get("E_comp_cycle_fJ", {})
    (RUNDIR / "energy_results.json").write_text(json.dumps(res, indent=1))
    print("[energy] wrote _flash_runs/energy_results.json", flush=True)
    return res


# ---------------------------------------------------------------- (c) mux R_on
def ron_deck():
    return "\n".join([
        "* TG mux on-resistance vs input level (sky130, repo TG sizing)",
        f".lib {LIB} tt",
        "Vdd vdd 0 1.8",
        "Vsw src 0 DC 0.9",
        "XTGn src gn out 0 sky130_fd_pr__nfet_01v8 W=2 L=0.15",
        "XTGp src gp out vdd sky130_fd_pr__pfet_01v8 W=4 L=0.15",
        "Vgn gn 0 1.8", "Vgp gp 0 0",
        "Iload out 0 DC 10u",
        ".control",
        "dc vsw 0.6 1.2 0.01",
        "let ron = (v(src)-v(out))/10u",
        "meas dc rmin MIN ron",
        "meas dc rmax MAX ron",
        "meas dc rmid FIND ron WHEN v(src)=0.9001",
        "echo RON $&rmin $&rmax $&rmid",
        "quit", ".endc", ".end"]) + "\n"


def cmd_ron():
    print("[ron] TG DC sweep 0.6..1.2 V @ 10 uA...", flush=True)
    out = run_ngspice(ron_deck(), "flash_ron")
    m = re.search(r"RON\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", out)
    res = {"R_on_min_ohm": float(m.group(1)), "R_on_max_ohm": float(m.group(2)),
           "R_on_mid_ohm": float(m.group(3))} if m else {"error": out[-2000:]}
    (RUNDIR / "ron_results.json").write_text(json.dumps(res, indent=1))
    print(f"[ron] {res}", flush=True)
    return res


# ---------------------------------------------------------------- ladder math (exact)
def ladder_thevenin():
    rth = {}
    for k in range(1, 8):
        r_below = (V_LO + k * LSB_FLASH) / I_LADDER
        r_above = R_TOTAL - r_below
        rth[k] = r_below * r_above / R_TOTAL
    return rth


# ---------------------------------------------------------------- summary
def summarize():
    if (RUNDIR / "mc_results.json").exists():
        mc = json.loads((RUNDIR / "mc_results.json").read_text())
    else:   # salvage path: aggregate whatever per-sample JSONs completed
        mc = [json.loads(p.read_text())
              for p in sorted(RUNDIR.glob("mc_s*.json"))]
        mc.sort(key=lambda r: r["sample"])
    en = json.loads((RUNDIR / "energy_results.json").read_text())
    ron = json.loads((RUNDIR / "ron_results.json").read_text())
    _lines, win, sig = load_sa_core()

    per_edge = {k: [] for k in range(1, 8)}
    n_nan = 0
    for r in mc:
        for ks, v in r["edges_mV"].items():
            if v == v:                      # not NaN
                per_edge[int(ks)].append(v)
            else:
                n_nan += 1
    edge_stats = {}
    pooled = []
    for k, vals in per_edge.items():
        if len(vals) >= 2:
            edge_stats[k] = {"tap_V": TAPS[k - 1], "N": len(vals),
                             "mean_mV": statistics.mean(vals),
                             "sigma_mV": statistics.stdev(vals)}
            pooled += [v - statistics.mean(vals) for v in vals]
    sigma_pooled = statistics.stdev(pooled) if len(pooled) > 1 else float("nan")
    all_edges = [v for vs in per_edge.values() for v in vs]
    sigma_raw = statistics.stdev(all_edges)
    # measured DNL: per-sample adjacent-edge spacing error in flash LSB
    dnl = []
    for r in mc:
        e = r["edges_mV"]
        for k in range(1, 7):
            a, b = e.get(str(k)), e.get(str(k + 1))
            if a is not None and b is not None and a == a and b == b:
                dnl.append((b - a) / (LSB_FLASH * 1e3))
    sigma_dnl = statistics.stdev(dnl) if len(dnl) > 1 else float("nan")
    mean_dnl = statistics.mean(dnl) if dnl else float("nan")

    ec = en["E_comp_cycle_fJ"]
    eck = en["E_clk_cycle_fJ"]
    e1 = en["single_comp_E_cycle_fJ"]
    e_comp7 = statistics.mean([ec[str(c)] if str(c) in ec else ec[c] for c in range(1, 9)])
    e_clk = statistics.mean([eck[str(c)] if str(c) in eck else eck[c] for c in range(1, 9)])
    e_1c = statistics.mean([e1[str(c)] if str(c) in e1 else e1[c] for c in range(1, 9)])
    e_ladder_conv = en["E_ladder_8cyc_fJ"] / 8.0
    p_ladder_uW = e_ladder_conv * 1e-15 / T_CYCLE * 1e6

    rth = ladder_thevenin()
    kb = en.get("kickback", {})

    summary = {
        "_about": ("Same-flow (sky130+ngspice) reproduction of the flash-ADC readout "
                   "slice of the RRAM XNOR-BNN macro (Yin et al., IEEE TED 67(10):4185, "
                   "2020; arXiv:1909.07514): one 3-bit flash ADC (7 StrongARM comparators, "
                   "repo sizing) + resistor-ladder references + 8:1 TG input mux, measured "
                   "on the same two axes as our column-shared SAR. Script: "
                   "rram_flash_slice.py (subcommands mc/energy/ron/summarize)."),
        "design": "RRAM XNOR-BNN flash-ADC slice",
        "citation": ("S. Yin, X. Sun, S. Yu, J.-S. Seo, \"High-Throughput In-Memory "
                     "Computing for Binary Deep Neural Networks with Monolithically "
                     "Integrated RRAM and 90nm CMOS,\" IEEE Trans. Electron Devices "
                     "67(10):4185-4192, 2020. Open preprint arXiv:1909.07514 (quotes "
                     "below are from the preprint full text)."),
        "architecture_confirmation_quotes": [
            "\"the testchip design includes a 128x64 1T1R array, row decoder, level "
            "shifter, eight 8-to-1 column multiplexers, eight 3-bit flash ADCs, and two "
            "64-to-1 column decoders for RRAM cell-level programming.\"",
            "\"Eight ADCs (shared among 64 columns) and eight column multiplexers occupy "
            "20% and 12% area of the XNOR-RRAM core, respectively\"",
            "\"Each 3-bit flash ADC consists of seven voltage-mode sense amplifiers "
            "(VSAs), whose outputs generate seven thermometer-coded bits that represent "
            "eight levels.\"",
            "\"Each VSA compares the read bitline (RBL) voltage of the selected column "
            "with a reference voltage. Seven reference voltages of an ADC are calibrated "
            "for the eight columns that the ADC is connected to.\"",
            "\"To make a balance between area and throughput, we share one flash ADC by "
            "eight columns.\"",
            "\"please note that our VSA and ADC design did not include offset "
            "compensation circuits or techniques.\"",
        ],
        "mapping_to_our_flow": {
            "input_range_V": [V_LO, V_HI],
            "input_range_provenance": ("readout_mapping.py law PC_FS=3*sqrt(F)=48 @ "
                                       "F=256, LSB_V=V_in/(2*PC_FS)=6.25 mV/pc with "
                                       "V_in=0.6 V -> TIA output 0.9+-0.3 V. F=256 is "
                                       "not a committed row of readout_mapping_summary"
                                       ".json; it is DERIVED from the committed law "
                                       "(stated range assumption)."),
            "taps_V": TAPS,
            "flash_LSB_mV": LSB_FLASH * 1e3,
            "flash_LSB_popcounts": LSB_FLASH / LSB_V_PC,
            "comparator": ("StrongARM latch SA, sizing read verbatim from "
                           "eda/hero/comparators/strongarm.spice (win=%.1f um)" % win),
            "sigma_Vth_per_device_mV": [s * 1e3 for s in sig],
            "ladder": {"R_total_ohm": R_TOTAL, "R_segment_ohm": R_SEG,
                       "R_end_ohm": R_END, "I_ladder_uA": I_LADDER * 1e6,
                       "C_decap_per_tap_pF": C_DECAP * 1e12,
                       "note": ("uniform 7-tap string across the 1.8 V rail + "
                                f"{C_DECAP*1e12:g} pF tap decaps. The stiffness is a "
                                "MEASURED constraint, not a free choice: a first-cut "
                                "10 uA bare-tap string collapsed tap4 from 0.900 to "
                                "0.52 V under the StrongARM strobe kick (~4-5 fC) and "
                                "railed every code edge -- a real flash failure mode "
                                "this reproduction surfaced. E_ladder scales "
                                "~1/R_total down to that kickback-recovery bound.")},
            "mux": {"topology": "8:1 CMOS transmission gates, 1 selected + 7 off on "
                                "the shared node",
                    "tg_sizing": "nfet 2/0.15, pfet 4/0.15 (repo TG, sar_capdac_tran.py)",
                    "source_model": f"TIA as Thevenin source with R_out = R_TI = "
                                    f"{R_TI:.0f} ohm (labeled assumption)",
                    "C_ADC_pF": C_ADC * 1e12,
                    "C_ADC_role": ("kick-matching decap DIRECTLY on the shared flash "
                                   "input node, C_ADC = 7 x C_tap: the input is "
                                   "kicked by all 7 comparators while each tap takes "
                                   "one comparator's kick. Without it (or with the "
                                   "cap on the bitline side of the mux, where R_on "
                                   "isolates it) every code edge rails -- both "
                                   "intermediate states were measured in bring-up.")},
        },
        "fidelity_deviations": [
            "Yin et al. references are per-ADC CALIBRATED over a CONFINED bitcount "
            "range (-13..11 of +-64; 'An automatic algorithm is employed to determine "
            "the reference voltages'); their generation circuit is not public. We use "
            "an UNCALIBRATED uniform resistor ladder across the full popcount-mapped "
            "range -- the plain-flash baseline their calibration then improves on.",
            "Their comparator is a 90 nm 1.2 V 'voltage-mode sense amplifier' (schematic "
            "not public); ours is the repo 130 nm/1.8 V StrongARM SA -- the same-flow "
            "voltage-mode SA. Ratios, not absolute mV/fJ, are the transferable result.",
            "Their mux is thick-oxide with 2-5 V gate drive ('the analog multiplexer "
            "gate voltage can be as high as 2-5V'); ours is a 1.8 V CMOS TG.",
            "Schematic-level netlists (no layout extraction) for ALL flash-slice "
            "numbers; our SAR comparator anchor 48 fJ is extracted -- so flash-vs-SAR "
            "energy is quoted as a comparator-count RATIO x the SAME schematic-level "
            "per-strobe energy, plus labeled absolute schematic-level terms.",
        ],
        "offset_mc": {
            "method": ("Pelgrom Vth offsets (AVT=5 mV*um assumption, same as "
                       "run_offset_mc.py) on input pair + latch pair of each of the 7 "
                       "comparators (28 draws/sample); all 7 comparators + ladder + mux "
                       "simulated together; per-edge offset = source sweep value where "
                       "that comparator's decision flips minus the ideal tap. Sweep "
                       f"+-{MC_SWEEP*1e3:.0f} mV in {MC_STEP*1e3:.0f} mV steps "
                       "(quantization adds <1% to a ~9 mV sigma, in quadrature)."),
            "N_samples": sum(1 for r in mc
                             if any(v == v for v in r["edges_mV"].values())),
            "N_note": ("N=40+ was planned; the run is time-bound by host throughput "
                       "(~0.4 sky130 transients/s aggregate on this machine), so the "
                       "committed result is the largest COMPLETED subset. Rerun with "
                       "more samples: wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd <repo> "
                       "&& OMP_NUM_THREADS=1 python3 eda/design_survey/repro/"
                       "rram_flash_slice.py mc <N> <workers>' then `summarize`. "
                       "Per-edge sigma SE ~ sigma/sqrt(2(N-1)); pooled sigma uses "
                       "7N edge measurements."),
            "edges_lost_to_sweep_range": n_nan,
            "per_edge": edge_stats,
            "sigma_pooled_mV_about_edge_means": sigma_pooled,
            "sigma_raw_all_edges_mV": sigma_raw,
            "sigma_over_VT_pooled": sigma_pooled / (VT * 1e3),
            "single_comparator_wall_mV": 9.21,
            "single_comparator_wall_over_VT": 0.393,
            "edge_sigma_in_flash_LSB": sigma_pooled / (LSB_FLASH * 1e3),
            "edge_sigma_in_popcounts": sigma_pooled / (LSB_V_PC * 1e3),
            "DNL_sigma_LSB_measured": sigma_dnl,
            "DNL_mean_LSB_measured": mean_dnl,
        },
        "energy": {
            "level": "SCHEMATIC-LEVEL (no extraction) -- house norm: ratios headline",
            "T_cycle_ns": T_CYCLE * 1e9,
            "E_7comp_per_conversion_fJ_schematic": e_comp7,
            "E_per_comparator_strobe_fJ_schematic": e_comp7 / 7.0,
            "single_StrongARM_same_flow_fJ_schematic": e_1c,
            "E_clk_driver_per_conversion_fJ": e_clk,
            "E_ladder_per_conversion_fJ": e_ladder_conv,
            "P_ladder_uW_measured": p_ladder_uW,
            "E_mux_select_transition_fJ": en.get("E_mux_transition_fJ"),
            "per_cycle_detail_fJ": {"comp7": ec, "clk": eck, "single": e1},
            "sar_anchor": {"E_comp_extracted_fJ_per_strobe": 48.0,
                           "E_sar_b8_comparator_fJ": 384.0,
                           "source": "sar_capdac_tran_summary.json / sa_postlayout"},
            "architecture_ratios": {
                "comparator_strobes_flash_3b": 7,
                "comparator_strobes_sar_3b": 3,
                "flash_over_sar_same_b3": 7.0 / 3.0,
                "comparator_strobes_flash_8b_would_be": 255,
                "comparator_strobes_sar_8b": 8,
                "flash_over_sar_same_b8": 255.0 / 8.0,
                "note": ("2^b-1 parallel comparators vs b sequential strobes; the "
                         "per-strobe energy is the SAME measured StrongARM in both, "
                         "so the ratio is exact and transfers across nodes"),
            },
        },
        "mux_insertion": {
            "R_on_ohm": ron,
            "ladder_R_thevenin_ohm": {str(k): rth[k] for k in rth},
            "ladder_R_th_max_ohm": max(rth.values()),
            "R_on_vs_ladder_note": ("mux R_on sits in the INPUT path in series with "
                                    f"R_TI={R_TI:.0f} ohm; ladder R_th loads the "
                                    "REFERENCE path. Settling time constants: input "
                                    "(R_TI+R_on)*C_vin, reference R_th*C_tap -- both "
                                    "measured below via residuals in the transient."),
            "kickback_measured": kb,
            "vin_settling_after_mux_switch": {
                "measured_V": en.get("vin_after_mux_switch_V"),
                "target_at_51p9n_V": CODE_MID[1],
                "target_at_61p9n_V": CODE_MID[3],
                "note": ("mux ch0->ch1 switch at 46 ns; 51.9 ns is just before the "
                         "next strobe (5.9 ns dwell), 61.9 ns one cycle later. "
                         "tau = (R_TI+R_on)*C_ADC -- the kick-matching decap "
                         "directly trades against channel-switch settling."),
            },
        },
        "assumptions": [],   # filled by caller-facing block below
    }
    summary["assumptions"] = [
        "AVT = 5 mV*um sky130-class Pelgrom coefficient (repo assumption, not the PDK "
        "mismatch model) -> sigma/V_T and flash-vs-SAR ratios transfer, absolute mV do not.",
        "Input range [0.6, 1.2] V = popcount-mapped TIA swing for fan-in 256 derived "
        "from the committed readout_mapping law (F=256 is not a committed row).",
        f"Ladder standing current 100 uA (R_total = 18 kohm) + {C_DECAP*1e12:g} pF tap "
        f"decaps + {C_ADC*1e12:g} pF kick-matching input decap, sized by the measured "
        "StrongARM kickback (a bare 180 kohm string railed all code edges); ladder "
        "energy scales ~1/R_total down to that measured bound. Yin et al.'s VSA "
        "kickback and reference-driver power are not public.",
        "TIA modeled as Thevenin source with R_out = R_TI = 1225 ohm.",
        "T_cycle = 10 ns per conversion (strobe 2 ns + precharge 8 ns), matching the "
        "repo MC harness clk; Yin et al. report a 6.5 ns RBL-settling critical path.",
        "All flash-slice energies are schematic-level (no extraction).",
        "Their VSA schematic is not public; StrongARM (repo sizing) stands in as the "
        "same-flow voltage-mode SA without offset compensation, which matches their "
        "stated design.",
    ]
    OUT_JSON.write_text(json.dumps(summary, indent=2))
    print(f"wrote {OUT_JSON}")
    return summary


# ---------------------------------------------------------------- driver
def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "all"
    if cmd == "diag":
        # one tran at edge 4, vd=-20mV: watch the tap and comparator-input nodes
        _l, _w, sig = load_sa_core()
        deck = mc_deck(draw_offsets(0, sig), edges=(4,), sweep=0.0, step=1.0)
        deck = deck.replace("  echo PT 4 $&vd $&vop $&von",
                            "  meas tran t4min MIN v(tap4) from=0.5n to=2n\n"
                            "  meas tran t4end FIND v(tap4) at=1.9n\n"
                            "  meas tran g2min MIN v(g2_4) from=0.5n to=2n\n"
                            "  meas tran vinmin MIN v(vin) from=0.5n to=2n\n"
                            "  echo PT 4 $&vd $&vop $&von\n"
                            "  echo DIAG $&t4min $&t4end $&g2min $&vinmin")
        deck = deck.replace("alter @vsrc[dc] = 0.9 + vd",
                            "alter @vsrc[dc] = 0.88 + vd")
        out = run_ngspice(deck, "flash_diag")
        for ln in out.splitlines():
            if ln.startswith(("PT", "DIAG")) or "rror" in ln.lower():
                print(ln)
        return
    if cmd == "smoke":
        _l, _w, sig = load_sa_core()
        out = run_ngspice(mc_deck(draw_offsets(0, sig), edges=(1, 4, 7),
                                  sweep=0.02, step=0.01), "flash_smoke")
        for ln in out.splitlines():
            if ln.startswith("PT") or "rror" in ln:
                print(ln)
        print("edges:", edge_offsets_from(out))
    elif cmd == "mc":
        n = int(args[1]) if len(args) > 1 else 40
        w = int(args[2]) if len(args) > 2 else 10
        cmd_mc(n, w)
    elif cmd == "energy":
        cmd_energy()
    elif cmd == "ron":
        cmd_ron()
    elif cmd == "summarize":
        summarize()
    elif cmd == "all":
        n = int(args[1]) if len(args) > 1 else 40
        w = int(args[2]) if len(args) > 2 else 10
        cmd_mc(n, w)
        cmd_energy()
        cmd_ron()
        summarize()
    else:
        raise SystemExit(f"unknown subcommand {cmd}")


if __name__ == "__main__":
    main()
