# Critical re-validation of the innovation plan (2026-06-27)

The innovation plan (`2026-06-27_innovation_replan.md`) was distilled from an earlier conversation; its
novelty / prior-art / venue claims were web-grounded once but never independently re-checked. This is
an adversarial re-validation by three parallel web-grounded agents (citations, novelty, venue). Net:
the plan's *direction* holds, but several specific claims are wrong and must be corrected before any of
this reaches the manuscript.

## 1. Prior-art citations — no pure hallucinations, but four substantive errors
Every arXiv ID / DOI / patent resolves to a real document, but:

| plan claim | status | correction |
|---|---|---|
| Closed-loop sMTJ (Nano Lett. **2024**, arXiv:2407.08665) | real | journal is **2025** (Koh et al., MIT, *Nano Lett.* 25(10):3799). Preempts generic closed-loop, NOT a V_th-tracking write driver specifically. |
| Kent "voltage-tunable / antiferromagnetic sMTJ" (arXiv:2509.13458) | **mis-attributed** | The ID is real & Kent is an author, but the paper is *"Tunable Random Telegraph Noise in **stable perpendicular** MTJs"* — **STT-pulse-actuated** RTN, **not** antiferromagnetic, **not** a voltage-tunable barrier. It does **NOT** preempt the tunable-barrier "trinity" device. Drop the AFM/VCMA characterization. |
| HKUST VCMA dual-function macro (VLSI 2026, 411 TOPS/W) | real but provisional | Future-dated conf (on HKUST portal). Implements deterministic IMC + **stochastic Poisson neurons**, NOT p-bit / reservoir. Preempts a generic dual-mode VCMA macro, NOT a p-bit/RC one. |
| Offset-cancel SA (ISSCC 2018 + US9111623/US10726897B1) | real | US9111623 is **2015** not 2018; all are **two-phase / sample-and-hold + trim**, not continuous chopper/auto-zero. Preempts generic offset cancellation only. |
| Measured p-bit ASIC (Nat. Electron. 2025, s41928-025-01439-6 **and** -01458-3) | one paper + one commentary | **-01439-6** is the real measured 130 nm CMOS + VCMA-MTJ-entropy ASIC (integer factorization). **-01458-3 is a News & Views commentary about it**, not a second measured paper. Stop citing it as evidence; the "desk-reject" inference is overstated. |

## 2. Novelty
- **Slope-matched p-bit readout — GENUINELY NOVEL.** No sMTJ/MRAM PBNN-CIM paper ties the readout
  comparator's input-referred offset spec to the device switching-probability sigmoid slope. Must cite &
  distinguish: **arXiv:2403.19374** (SOT-MRAM PBNN-CIM — budgets readout by **TMR margin**, ideal
  comparator: the status quo this displaces) and **arXiv:2410.16915** (extracts the p-bit sigmoid
  slope/shift but **compensates in software/Boltzmann training with an ideal comparator** — the sharpest
  near-miss). Claim the *quantitative offset-vs-V_T co-design law*, not "first to notice the slope matters".
- **RC iso-energy {N,M,b} — PARTIALLY NOVEL.** Danger paper: **arXiv:2601.21807** (2026, "Ensemble RC
  for Physical Systems") **already sweeps ensemble M and ADC bits b and shows 2–4-bit suffices** — so the
  "low-resolution readout is optimal" sub-claim is **already published**. Surviving novelty: the
  **memory-capacity-per-Joule** objective, **including N** in the trade (others fix the reservoir), and the
  **column-shared-ADC** energy amortization on telegraph-noise sMTJ nodes. Reframe and cite 2601.21807
  prominently. Also cite arXiv:2507.09776 (SNR-optimal ADC for IMC) and the memristor-RC ADC-bottleneck work.

## 3. Venue — the plan over-ranks TCAS-I
Avoiding Nature Electronics / ISSCC for a simulation-only open-PDK paper is correct (ISSCC requires
measured silicon by identity; Nature Electronics now has a measured competitor). But within the journal
family the ranking should be:

1. **IEEE JxCDC** — purpose-built for beyond-CMOS device-driven circuits incl. **physics-based modeling/
   simulation** and neuromorphic/non-Boolean; open-access. Likely the single best fit.
2. **IEEE TVLSI** — measurements "encouraged… not essential"; rewards device→circuit→system co-design.
3. **IEEE TED** — if framed as compact-model/device-physics driving circuit behavior (model+SPICE, no fab).
4. **IOP Neuromorphic Computing & Engineering** — best if framed as neuromorphic/RC; spintronic co-sim in scope.
5. **IEEE TCAS-I** — *riskiest* of the family for sim-only (its guidelines ask experimental validation of
   principal claims); viable only with a strongly methodology/theory framing.
Conference companions for early disclosure: DATE / ASP-DAC / DAC.
Framing: lead with the wafer-calibrated model as the credibility anchor; cast open-PDK as a
**reproducibility** choice, and pre-empt the "why no measured circuit" question explicitly.

## 4. Actions applied to the plan
- Venue line corrected (JxCDC/TVLSI/TED/NCE first; TCAS-I downgraded).
- C3 reframed to MC/Joule + N + shared-ADC; 2601.21807 cited as the work it differentiates from.
- Trinity feasibility note corrected: arXiv:2509.13458 does **not** preempt a tunable-barrier device
  (it is STT-actuated RTN); the genuine prior art for tunable stochasticity is that RTN paper + the HKUST
  Poisson-neuron macro, neither of which is a p-bit/RC dual-mode array.
- Citation years/types fixed; -01458-3 removed as "measured silicon".
- Manuscript related-work must cite/distinguish 2403.19374 and 2410.16915 for the readout contribution.
