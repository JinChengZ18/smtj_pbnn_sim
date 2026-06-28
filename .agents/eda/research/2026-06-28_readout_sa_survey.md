# Readout sense-amp design survey + positioning (2026-06-28)

Web-grounded comparative survey (adversarial agent) to position the slope-matched p-bit readout against
the dynamic-comparator and sMTJ/MRAM/p-bit-CIM literature, with quantitative anchors. Internal record;
the deliverable wording lives in `article/supplement_eda_codesign.md` §2 (journal-grade, no project codes).

## Quantitative landscape (sense amplifiers)
| design | input offset σ | energy/decision | node | source |
|---|---|---|---|---|
| StrongARM single-tail | ~12 mV (untrimmed) | 11–19 fJ | 65 nm | Razavi SSC-Mag 2015; 11 fJ/10 GHz SA |
| Dual strong-arm (DSA) 2-stage | **8.5 mV** (meas., 6 dies; ~30% < conv.) | iso-cap | 28 nm FDSOI | Papadopoulou/Nikolić ASSCC 2017 |
| double-tail (DTSA) | ≳ DSA | ~51 fJ | 65 nm | DTSAL 2024 |
| StrongARM + single-cap auto-zero | **>60% σ reduction** | +cap, **−15% area vs dual-cap, no timing penalty** | 28 nm MRAM | Dong et al. ISSCC 2018 30.2 |

## Philosophy gap (the seam our contribution fills)
- **MRAM-CIM camp** (Dong ISSCC'18; STT-BNN TVLSI'22; SOT-PBNN-CIM arXiv:2403.19374): rigorous offset
  cancellation, but budgeted against a **deterministic TMR / reference-cell margin** (e.g., 2403.19374
  uses a P+AP reference cell, TMR 156%, a ~1.5 mV signal band) → auto-zero is **always on**.
- **p-bit/PBNN camp** (arXiv:2403.19374; p-bit variation arXiv:2410.16915 parametrizes the sigmoid slope
  α with σ(α)≈0.3; measured VC-MTJ p-bit ASIC Nat.Electron. 2025 s41928-025-01439-6): the **slope is the
  operative quantity**, but the comparator is **idealized / offset not modeled**, or variation is
  compensated in the weight matrix, not the readout.
- **Neither budgets the sense-amp offset against the device's own sigmoid slope V_T (Bernoulli window).**

## Novelty (confirmed) + improvement adopted
- Novelty = the missing bridge: budget σ_OS against **V_T** (not TMR margin) + a transimpedance law
  R_TI = V_in/(2·PC_FS·LSB_I), PC_FS≈3√(fan-in), giving a closed-form predicate for when a plain SA
  suffices vs needs cancellation. (Components — StrongARM offset, single-cap auto-zero, slope-as-parameter
  — are each prior art; the decision rule joining them is not.)
- **Improvement ADOPTED — fan-in/slope-gated *conditional* auto-zero:** because V_T is fixed but the
  per-popcount signal scales with fan-in, enable the (Dong-style, single-cap, decode-hidden) auto-zero
  **only** in the high-fan-in / low-V_in / steep-slope columns that cross the curve knee; ship the bare
  StrongARM elsewhere. This turns Dong's *always-on* cancellation into an only-when-needed one — matching
  the boundary already quantified in `eda/hero/pareto_offset_cancellation.py` (V_in≤~0.4 V / wide fan-in).
- **Optional incremental:** a DSA latch (8.5 mV) drops the baseline offset ~30% at iso-area vs the plain
  StrongARM — a drop-in topology choice, not the contribution.

## Improvement REJECTED (honest record)
The agent also proposed **√N de-rating** of the offset budget by folding in the inference's N sampling
cycles. **This is invalid here:** the SA offset is a *fixed per-column systematic* (one SA per output
column), so averaging N Bernoulli samples of the same cell through the same SA reduces sampling *noise*
but **not** the systematic offset — it shifts every sample's decision identically. (√N would only help if
the offset were re-randomised per sample, e.g., time-interleaved SAs — not the per-column design.) This is
consistent with our per-column-systematic model (`hero_mnist_sweep.py`, readout_mapping). Do NOT put √N in
the manuscript.

## Sources
Razavi, *StrongARM Latch*, IEEE SSC-Mag 2015 · Papadopoulou/Milovanović/Nikolić, DSA latch, ASSCC 2017 ·
Dong et al., 1 Mb 28 nm STT-MRAM single-cap offset-cancel SA, ISSCC 2018 30.2 · Gu et al., SOT-MRAM
PBNN-CIM, arXiv:2403.19374 · P-bit variation extraction, arXiv:2410.16915 · Hung et al., STT-BNN,
IEEE TVLSI 2022 · Integrated VC-MTJ p-computer, Nature Electronics 8:784 (2025) / arXiv:2412.08017.
