#!/usr/bin/env python3
"""R7 (B7 / plan 3.5): "trinity" time-mux tunable-barrier feasibility envelope.

The thesis main line proposes ONE sMTJ array serving both PBNN (p-bit write) and RC (fading-memory
node). But the two uses want DIFFERENT thermal-stability factors Delta = E_b/kT:
  PBNN p-bit : Delta = 4.91  (calibrated Device-A; tau_max(0V)=tau_0*exp(Delta)/2 = 67.8 ns)
  RC node    : Delta ~ 3.8   (ns-scale telegraph; tau_max = 22.4 ns, telegraph_lowbarrier.py)
A FIXED device cannot be both. This script quantifies the barrier-tuning REQUIREMENT to time-multiplex
them, maps it to a VCMA gate voltage and a temperature equivalent, compares to published tunable-
barrier ranges, and registers the honest constrained-architecture limitation. Closes errata R7.

Grounding: device/arrhenius.py (Delta, tau_0=1ns, tau_max=tau_0*exp(Delta)/2). kT=25.85 meV @300K.
Honesty: VCMA tuning rate is a literature order-of-magnitude (reported ~1-3 kT/V); report the
REQUIREMENT and the ratio, not a silicon-verified number. Frame the trinity as a constrained,
time-multiplexed, NOT-concurrently-demonstrated architecture.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

DELTA_PBNN = 4.91
DELTA_RC = 3.8
TAU0 = 1.0e-9
KT_meV_300 = 25.852          # k_B*T at 300 K
T0 = 300.0
# representative VCMA barrier-tuning efficiency (literature order-of-magnitude):
# reported VCMA can shift the stability factor by ~1-3 kT per volt at the free layer.
VCMA_dDelta_per_V = 2.0      # kT/V (mid-range assumption; report sensitivity)


def tau_max_ns(Delta):
    return TAU0 * math.exp(Delta) / 2.0 * 1e9


def main():
    dD = DELTA_PBNN - DELTA_RC
    Eb_pbnn = DELTA_PBNN * KT_meV_300
    Eb_rc = DELTA_RC * KT_meV_300
    dEb = dD * KT_meV_300
    frac = dD / DELTA_PBNN

    print("=" * 90)
    print("R7 trinity tunable-barrier feasibility envelope (time-mux PBNN p-bit <-> RC node)")
    print("=" * 90)
    print("mode      Delta   E_b(meV @300K)   tau_max(0V)")
    print("  PBNN     %.2f     %6.1f           %.1f ns" % (DELTA_PBNN, Eb_pbnn, tau_max_ns(DELTA_PBNN)))
    print("  RC       %.2f     %6.1f           %.1f ns" % (DELTA_RC, Eb_rc, tau_max_ns(DELTA_RC)))
    print("-" * 90)
    print("required barrier swing:  dDelta = %.2f   dE_b = %.1f meV   = %.1f%% of E_b(PBNN)"
          % (dD, dEb, frac * 100))

    # (1) VCMA voltage needed
    v_vcma = dD / VCMA_dDelta_per_V
    print("\n(1) VCMA gate:   at ~%.1f kT/V (literature mid-range) -> V_gate ~ %.2f V to drop "
          "Delta 4.91->3.8" % (VCMA_dDelta_per_V, v_vcma))
    for rate in (1.0, 3.0):
        print("      sensitivity: %.1f kT/V -> %.2f V" % (rate, dD / rate))

    # (2) temperature equivalent (self-heating bridges it, but uncontrolled)
    # Delta = E_b/kT ; same E_b: Delta_RC/Delta_PBNN = T_PBNN/T_RC -> T_RC = T0*Delta_PBNN/Delta_RC
    T_rc = T0 * DELTA_PBNN / DELTA_RC
    print("\n(2) temperature: holding E_b fixed, Delta 4.91->3.8 needs T %.0f K -> %.0f K "
          "(+%.0f K) -- self-heating CAN bridge it but is uncontrolled / couples to retention"
          % (T0, T_rc, T_rc - T0))

    # (3) vs published tunable-barrier devices
    print("\n(3) vs prior art: a ~%.0f%% (dDelta~%.1f) barrier swing is WITHIN demonstrated VCMA "
          "ranges" % (frac * 100, dD))
    print("      - Kent A-sMTJ (arXiv:2509.13458, 2025): voltage-tunable stability")
    print("      - HKUST VCMA dual-function macro (VLSI 2026): mode-switchable anisotropy")
    print("      => the tuning REQUIREMENT is physically plausible per prior art.")

    concl = (
        "R7 verdict (constrained-architecture feasibility envelope, NOT a demonstrated capability): "
        "time-muxing PBNN (Delta=4.91, tau_max=67.8 ns) and RC (Delta~3.8, tau_max=22.4 ns) on one "
        "sMTJ requires a barrier swing of dDelta=%.2f (dE_b=%.1f meV = %.0f%% of E_b) -- achievable "
        "via a VCMA gate (~%.2f V at ~%.0f kT/V, within demonstrated ranges: Kent A-sMTJ 2025, HKUST "
        "VCMA macro VLSI 2026) or a ~%.0f K temperature rise (uncontrolled). BUT: (i) the two modes "
        "are mutually exclusive in time (mode-MUX, not concurrent); (ii) RC's low barrier conflicts "
        "with PBNN write/retention and with read-disturb; (iii) NO published macro time-muxes p-bit "
        "write and RC free-evolution on the same physical array. => the thesis must present the "
        "trinity as a CONSTRAINED, time-multiplexed, VCMA-gated PROPOSAL with this quantified tuning "
        "envelope and the barrier conflict registered as a limitation -- not as a proven concurrent "
        "capability. Honesty: VCMA kT/V is literature order-of-magnitude; report the requirement+ratio."
        % (dD, dEb, frac * 100, v_vcma, VCMA_dDelta_per_V, T_rc - T0))
    print("\n" + "=" * 90 + "\n" + concl + "\n" + "=" * 90)

    out = dict(Delta_PBNN=DELTA_PBNN, Delta_RC=DELTA_RC, dDelta=round(dD, 3),
               Eb_PBNN_meV=round(Eb_pbnn, 2), Eb_RC_meV=round(Eb_rc, 2), dEb_meV=round(dEb, 2),
               frac_pct=round(frac * 100, 1), tau_max_PBNN_ns=round(tau_max_ns(DELTA_PBNN), 1),
               tau_max_RC_ns=round(tau_max_ns(DELTA_RC), 1),
               vcma_V_at_2kT_per_V=round(v_vcma, 3), vcma_dDelta_per_V=VCMA_dDelta_per_V,
               T_rc_equiv_K=round(T_rc, 1), conclusion=concl)
    (HERE / "trinity_barrier_summary.json").write_text(json.dumps(out, indent=2))
    print("wrote trinity_barrier_summary.json")


if __name__ == "__main__":
    main()
