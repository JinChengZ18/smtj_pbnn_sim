#!/usr/bin/env python3
"""C3/F3 SAR cap-DAC SWITCHING energy, TRANSIENT-MEASURED in sky130 (not the analytic series).

sar_capdac_energy.py grounds the cap-DAC term with the closed-form Ginsburg/Chandrakasan
switching-energy series (conventional) and a ~/10 monotonic estimate. This script REPLACES the
formula with a real ngspice transient: a b-bit binary-weighted charge-redistribution cap array
whose bottom plates are switched between Vref and gnd through REAL sky130 CMOS transmission gates
across a full successive-approximation code sequence, with the energy drawn from Vref measured as
  E_capdac = Vref * integral(I_vref dt)
over the whole conversion (ngspice .meas integral of the Vref-branch current). Two schemes:

  conventional : every bit is first tentatively set to 1 (bottom plate -> Vref); after the
                 comparator decision the bit is either kept or pulled back down to gnd. The
                 up-then-maybe-down transitions are the classic high-energy SAR sequence.
  monotonic    : (set-and-down / Liu 2010) the array starts all-Vref (sampled), and each step
                 only ever pulls ONE sub-array DOWN to gnd or leaves it -- no up-transitions, no
                 tentative MSB pre-charge -> the well-known ~order-of-magnitude lower cap-DAC E.

The analytic series is the AVERAGE switching energy over all output codes, so the transient is
AVERAGED over a representative set of codes (all 2^b for b<=8 is cheap enough at b=6, a random
sample at b=7,8) to compare like-for-like. The comparator decision is not simulated here (it is the
EXTRACTED StrongARM SA, 48 fJ -- see sa_postlayout); we impose each code as the switching stimulus
and measure only the cap-DAC charge from Vref.

CRITICAL on what is counted: the analytic Ginsburg/Chandrakasan series counts ONLY the energy
drawn from Vref during the b BIT-TRIAL transitions, with the sampled reference state already
established. So the transient integrates the Vref power ONLY over the SAR trial phases and EXCLUDES
the phase-0 sample/reset (which one-time-charges the array to its initial state -- a sampling cost,
not a switching cost, and not in the analytic series). This is stated in the JSON.

Cap model: lumped linear capacitors of value C_u = 1.5 fF for the unit element (binary-weighted
2^i * C_u for bit i, plus a dummy LSB), the SAME C_u the analytic model uses. sky130 MIM
(cap_mim_m3) area density camimc ~ 2.0 fF/um^2, so C_u=1.5 fF ~ a 0.87x0.87 um MIM unit -- a
realistic matched SAR element; the switching energy depends on the cap VALUE and the switch
sequence, not on the small MIM voltage nonlinearity, so lumped C is the right, clean primitive
here and the bottom-plate SWITCHES are real sky130 CMOS. (Stated explicitly in the JSON.)

MUST RUN IN WSL (native ngspice + sky130):
  wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd <repo>; python3 eda/testbenches/sar_capdac_tran.py'
"""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = "/opt/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
RUN = HERE / "_sar_capdac_tran.spice"

CU_fF = 1.5          # unit cap [fF] (matched SAR element; MIM-validated, same as analytic model)
VREF = 1.0           # reference voltage [V]
E_COMP_fJ = 48.0     # EXTRACTED sky130 StrongARM comparator (sa_postlayout) -- NOT re-derived here

# transient timing: one SAR step per TSTEP; switches settle in << TSTEP (RC of C_u*Ron ~ ps).
TSTEP = 5e-9         # per-bit settling window [s]
TRISE = 50e-12       # switch gate edge [s]


def e_conv_units(N):
    """Analytic conventional SAR avg switching energy in units of C_u*Vref^2 (Ginsburg/Chandrakasan)."""
    return sum(2.0 ** (N + 1 - 2 * i) * (2 ** i - 1) for i in range(1, N + 1))


# ----------------------------------------------------------------------------------------------
# A real sky130 CMOS bottom-plate switch: transmission gate from `src` to the cap bottom plate
# `node`, gate controlled by a digital control node `ctl` (and its complement `ctlb`). When ctl is
# high the TG connects `node` to Vref-side src; the harness uses two TGs per bottom plate (one to
# Vref, one to gnd) with complementary control so the plate is always driven (no floating).
# ----------------------------------------------------------------------------------------------
def tg(idx, src, node, ctl, ctlb):
    return (f"XTGn{idx} {src} {ctl}  {node} 0   sky130_fd_pr__nfet_01v8 W=2 L=0.15\n"
            f"XTGp{idx} {src} {ctlb} {node} vdd sky130_fd_pr__pfet_01v8 W=4 L=0.15\n")


def _pulse_ctl(name, hi):
    """A static digital control level (1.8 V if hi else 0) as a PWL-ish constant source.
    We emit per-step control as PWL in build_netlist; this helper is for a constant rail."""
    return f"V{name} {name} 0 {'1.8' if hi else '0'}\n"


def build_netlist(b, scheme, d):
    """Full ngspice transient deck for a b-bit charge-redistribution cap-DAC switching sequence.

    Topology: b binary-weighted caps (bit i, MSB=i0, value 2^(b-1-i)*C_u) + one dummy LSB cap C_u,
    all TOP plates tied to node `top` (the comparator summing node; left floating/high-Z here, only
    a tiny C_top to gnd for numerical reference). Each cap BOTTOM plate is driven through a pair of
    real sky130 TGs to Vref or gnd according to a per-step, per-scheme control PWL. The energy is
    integral of Vref-branch current * Vref over the SAR trial phases (sample phase excluded).
    d = the b-bit decision pattern (MSB first), d[i] in {0,1}.
    """
    caps = [2 ** (b - 1 - i) for i in range(b)]     # weight of bit i in units of C_u (MSB first)
    n = b
    lines = []
    lines.append(f"* SAR cap-DAC transient: b={b} scheme={scheme} C_u={CU_fF}fF Vref={VREF}V")
    lines.append(f".lib {LIB} tt")
    lines.append("Vdd vdd 0 1.8")
    lines.append(f"Vref vref 0 {VREF}")
    lines.append("Vgndref gndref 0 0")
    lines.append("Ctop top 0 1f")                   # tiny ref cap so `top` is defined
    # binary-weighted caps + dummy LSB
    for i in range(n):
        lines.append(f"C{i} top bp{i} {caps[i] * CU_fF}f")
    lines.append(f"Cdum top bpd {CU_fF}f")          # dummy LSB unit cap (standard SAR array)

    # ----- per-bottom-plate control PWL: bottom plate goes to Vref when ctl high, gnd when low.
    # We synthesise, for each bottom plate, the time waveform of its "connect-to-Vref" control,
    # then realise the connection with two real TGs (to vref / to gnd) + complementary gate PWLs.
    # TIMELINE: phase 0 = sample/reset; phases 1..b = SAR bit trials. The CONVENTIONAL scheme adds
    # ONE final resolve phase (b+1) so the LAST bit's keep/pull-down edge is actually simulated
    # (the tentative-set in phase k is resolved in phase k+1, so the b-th trial needs a (b+1)-th
    # phase). Monotonic needs no resolve phase (each step is already the final transition).
    n_phase = (b + 2) if scheme == "conventional" else (b + 1)
    t_phase = [k * TSTEP for k in range(n_phase + 1)]   # phase k spans [t_phase[k], t_phase[k+1])

    def ctl_waveform(connect_vref_per_phase):
        """Build a PWL string (node value 0/1.8) over the phases from a list of bools (len n_phase)."""
        pts = []
        for k in range(n_phase):
            v = "1.8" if connect_vref_per_phase[k] else "0"
            t0 = t_phase[k]
            pts.append(f"{t0:.4e} {v}")
            pts.append(f"{t0 + TRISE:.4e} {v}")
        pts.append(f"{t_phase[n_phase]:.4e} {pts[-1].split()[-1]}")
        return "PWL(" + " ".join(pts) + ")"

    # Decide, per scheme, the connect-to-Vref schedule for each bottom plate across phases.
    # connect[plate][phase] = True if that plate's bottom is tied to Vref in that phase.
    plates = [f"bp{i}" for i in range(n)] + ["bpd"]
    connect = {p: [False] * n_phase for p in plates}

    if scheme == "conventional":
        # phase 0: reset all bottom plates to gnd (sample). dummy stays gnd throughout.
        # phases 1..b test bit (k-1): tentatively set that plate to Vref (up edge); the (imposed)
        # decision d[bit] is resolved in the NEXT phase (keep at Vref if 1, pull back to gnd if 0).
        # phase b+1 (resolve) holds every plate at its final decided value, so the b-th bit's
        # keep/pull-down edge is simulated.
        for k in range(1, b + 1):
            bit = k - 1
            for j in range(n):
                if j < bit:
                    connect[f"bp{j}"][k] = (d[j] == 1)        # already-decided higher bits held
                elif j == bit:
                    connect[f"bp{j}"][k] = True               # tentative set-to-Vref (the up edge)
                else:
                    connect[f"bp{j}"][k] = False              # untested -> gnd
        for j in range(n):                                    # phase b+1: final resolved state
            connect[f"bp{j}"][b + 1] = (d[j] == 1)
    elif scheme == "monotonic":
        # set-and-down (Liu 2010): phase 0 SAMPLE with ALL bottom plates at Vref. Each step pulls
        # exactly one sub-array DOWN to gnd if its decision is 0, else leaves it at Vref. No up
        # transitions, no tentative MSB precharge. dummy held at Vref (part of the sampled array).
        for p in plates:
            connect[p][0] = True
        for k in range(1, n_phase):
            bit = k - 1
            for j in range(n):
                if j < bit:
                    connect[f"bp{j}"][k] = (d[j] == 1)        # earlier bits: down if decided 0
                elif j == bit:
                    connect[f"bp{j}"][k] = (d[bit] == 1)      # this bit: pull down iff decision 0
                else:
                    connect[f"bp{j}"][k] = True               # untested still at Vref (sampled)
            connect["bpd"][k] = True
    else:
        raise ValueError(scheme)

    # emit control PWLs + real TG pairs for every bottom plate
    idx = 0
    for p in plates:
        wf = ctl_waveform(connect[p])
        wfb = ctl_waveform([not x for x in connect[p]])
        lines.append(f"Vctl_{p} ctl_{p} 0 {wf}")
        lines.append(f"Vctlb_{p} ctlb_{p} 0 {wfb}")
        lines.append(tg(idx, "vref", p, f"ctl_{p}", f"ctlb_{p}").rstrip())
        idx += 1
        lines.append(tg(idx, "gndref", p, f"ctlb_{p}", f"ctl_{p}").rstrip())
        idx += 1

    tstop = t_phase[n_phase]
    t_sample_end = t_phase[1]      # end of phase 0 (sample/reset); SAR trials are phases 1..b
    # Energy DRAWN from Vref = integral(-v(vref)*i(Vref) dt). We take the cumulative energy at the
    # end of the conversion MINUS the cumulative energy at the end of the sample phase, so the
    # one-time sample/reset array precharge is EXCLUDED (it is a sampling cost, not in the analytic
    # switching series). t_sample_end is sampled just after the phase settles.
    lines.append(".control")
    lines.append(f"  tran {TRISE/4:.4e} {tstop:.4e} uic")
    lines.append("  let pwr = -v(vref)*i(Vref)")          # power delivered by source to network
    lines.append("  let ene = integ(pwr)")
    lines.append("  meas tran e_sample find ene at=" + f"{t_sample_end*0.999:.4e}")
    lines.append("  meas tran e_end find ene at=" + f"{tstop*0.999:.4e}")
    lines.append("  let e_trial = e_end - e_sample")
    lines.append("  print e_trial")
    lines.append("  print e_sample")
    lines.append("  print e_end")
    lines.append("  quit")
    lines.append(".endc")
    lines.append(".end")
    return "\n".join(lines) + "\n"


def measure(b, scheme, d):
    """Return (E_trial_J, E_sample_J, raw_text) for one b-bit code d under one scheme."""
    RUN.write_text(build_netlist(b, scheme, d))
    out = subprocess.run(["ngspice", "-b", RUN.name], cwd=HERE,
                         capture_output=True, text=True)
    txt = out.stdout + out.stderr
    mt = re.search(r"e_trial\s*=\s*([-+0-9.eE]+)", txt)
    ms = re.search(r"e_sample\s*=\s*([-+0-9.eE]+)", txt)
    if not mt:
        return None, None, txt
    return float(mt.group(1)), (float(ms.group(1)) if ms else None), txt


def codes_for(b):
    """Representative output codes to average the switching energy over (matches the analytic
    AVERAGE-over-codes series). All 2^b for b<=6; a fixed pseudo-random sample otherwise."""
    if b <= 6:
        return list(range(2 ** b))
    import random
    rng = random.Random(20260630)
    return sorted(set([0, 2 ** b - 1] + [rng.randrange(2 ** b) for _ in range(62)]))


def bits_msb_first(code, b):
    return [(code >> (b - 1 - i)) & 1 for i in range(b)]


def main():
    print("=" * 92)
    print("C3/F3 SAR cap-DAC SWITCHING energy -- TRANSIENT-measured in sky130 "
          f"(C_u={CU_fF} fF, Vref={VREF} V)")
    print("comparator = %.0f fJ (EXTRACTED StrongARM, NOT re-derived here)" % E_COMP_fJ)
    print("=" * 92)
    print("  b  scheme        E_capdac meas(fJ)  E_capdac analytic(fJ)  E_comp b*48(fJ)  E_total(fJ)"
          "   #codes")
    rows = []
    schemes = ["conventional", "monotonic"]
    for b in (6, 7, 8):
        e_conv_analytic = e_conv_units(b) * CU_fF * VREF ** 2     # fJ (avg over codes)
        e_mono_analytic = e_conv_analytic / 10.0
        codes = codes_for(b)
        for scheme in schemes:
            analytic = e_conv_analytic if scheme == "conventional" else e_mono_analytic
            evals, esamp, nbad = [], [], 0
            for code in codes:
                e_J, es_J, txt = measure(b, scheme, bits_msb_first(code, b))
                if e_J is None:
                    nbad += 1
                    continue
                evals.append(e_J)
                if es_J is not None:
                    esamp.append(es_J)
            if not evals:
                print(f"  {b}  {scheme:12s}  DID NOT CONVERGE -> reporting null (NOT fabricating)")
                rows.append(dict(b=b, scheme=scheme, E_capdac_fJ_measured=None,
                                 E_capdac_fJ_analytic=round(analytic, 2),
                                 E_comp_fJ=round(b * E_COMP_fJ, 1), E_total_fJ=None,
                                 n_codes=0, converged=False))
                continue
            e_fJ = (sum(evals) / len(evals)) * 1e15           # mean over codes
            e_fJ_max = max(evals) * 1e15
            e_samp_fJ = (sum(esamp) / len(esamp)) * 1e15 if esamp else None
            e_comp = b * E_COMP_fJ
            e_total = e_comp + e_fJ
            print(f"  {b}  {scheme:12s}  {e_fJ:14.2f}   {analytic:18.2f}   {e_comp:13.1f}  "
                  f"{e_total:11.1f}   {len(evals)}{'(' + str(nbad) + ' bad)' if nbad else ''}")
            rows.append(dict(b=b, scheme=scheme,
                             E_capdac_fJ_measured=round(e_fJ, 3),
                             E_capdac_fJ_measured_worstcode=round(e_fJ_max, 3),
                             E_sample_fJ_excluded=round(e_samp_fJ, 3) if e_samp_fJ else None,
                             E_capdac_fJ_analytic=round(analytic, 2),
                             E_comp_fJ=round(e_comp, 1), E_total_fJ=round(e_total, 1),
                             capdac_frac_of_total=round(e_fJ / e_total, 4) if e_total else None,
                             n_codes=len(evals), n_bad=nbad, converged=True))

    # validation verdict vs the analytic series (per-b, per-scheme, code-averaged measured)
    verdict_bits = []
    for r in rows:
        if r["converged"] and r["E_capdac_fJ_analytic"]:
            ratio = r["E_capdac_fJ_measured"] / r["E_capdac_fJ_analytic"]
            verdict_bits.append(f"b{r['b']}/{r['scheme'][:4]}: meas/analytic={ratio:.2f}")
    notes = (
        "Cap-DAC SWITCHING energy measured by transient charge integration from Vref "
        "(E = -integral(v(vref)*i(Vref) dt)), AVERAGED over output codes (all 2^b for b=6, a fixed "
        "pseudo-random 64-code sample for b=7,8) to match the analytic AVERAGE-over-codes series. "
        "The one-time sample/reset array precharge (phase 0) is EXCLUDED from the switching energy "
        "(it is a sampling cost, reported separately as E_sample_fJ_excluded). Bottom plates are "
        "switched Vref<->gnd through REAL sky130 CMOS transmission gates. Comparator energy is the "
        "EXTRACTED StrongARM SA (48 fJ), added analytically as b*E_comp -- NOT simulated here. Two "
        "schemes: conventional (tentative set-to-Vref then keep/pull-down) vs monotonic "
        "set-and-down (sample all-Vref, only down-transitions).")
    what = (
        "SIMULATED (ngspice transient, sky130): the cap-DAC bottom-plate switching charge drawn "
        "from Vref, through real CMOS TG switches, for b=6,7,8, both schemes. "
        "EXTRACTED (prior, sa_postlayout): comparator energy 48 fJ/decision. "
        "ANALYTIC (for comparison only): the Ginsburg/Chandrakasan conventional series and its /10 "
        "monotonic estimate from sar_capdac_energy.py. The cap is a lumped linear C_u=1.5 fF "
        "(MIM-density-validated); not simulated: the comparator, the SAR control logic, MIM "
        "voltage-nonlinearity, and the SS/single-slope hybrid (see hybrid field).")
    out = dict(method="ngspice transient charge-redistribution; E=-integral(v(vref)*i(Vref))",
               C_u_fF=CU_fF, Vref=VREF, E_comp_fJ_extracted=E_COMP_fJ,
               decision_pattern="alternating (1,0,1,0,...) imposed stimulus",
               rows=rows, validation=verdict_bits, notes=notes,
               what_is_simulated_vs_analytic=what,
               hybrid_SAR_SS="not done (see optional task 4)")
    (HERE / "sar_capdac_tran_summary.json").write_text(json.dumps(out, indent=2))
    print("\nvalidation vs analytic:", " | ".join(verdict_bits))
    print("wrote sar_capdac_tran_summary.json")


if __name__ == "__main__":
    main()
