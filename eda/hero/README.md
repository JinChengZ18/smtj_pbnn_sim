# `eda/hero/` — Hero (A1): slope-matched p-bit readout (sky130)

The flagship innovation (ROADMAP Tier-A A1; closes errata R2). **The contribution is not
"we built a sense amp" (those are mature) — it is budgeting the SA input-referred offset
against the device's OWN sigmoid slope V_T=23.4mV (the Bernoulli decision window, not a
deterministic TMR margin), and closing the loop to MNIST accuracy.** Non-obvious inversion:
Exp.08 finds V_T slope "accuracy-irrelevant" (BatchNorm absorbs it), yet V_T turns out to
SET the readout-circuit cost, because the SA offset is a per-column V_th shift in disguise —
exactly the error class Exp.08 finds fatal.

## Files
| File | What | Run |
|---|---|---|
| `strongarm_sa.spice` | StrongARM latched comparator in sky130 (the differential current-mode SA) | `ngspice -b` (WSL) |
| `run_offset_mc.py` | input-referred offset Monte-Carlo (Pelgrom Vth mismatch) vs V_T; `[N] [area-scale]` | WSL python3 |
| `offset_mc_summary.json` / `offset_mc_s4.json` | offset MC results (1x / 4x input-pair area) | — |
| `../interface/hero_closed_loop.py` | device-physics decision shift + first-cut accuracy (Exp.08 anchors) | Windows python |
| `../interface/hero_mnist_sweep.py` | RIGOROUS accuracy axis: train PBNN-MLP, inject `sigma_sense_offset_V`, sweep -> acc | Windows GPU |

## Results (sky130, ngspice; AVT a sky130-class assumption -> report RATIOS not absolute mV)

- **StrongARM works** in sky130 (vind=+20mV -> outp=1.8V, outn~1uV).
- **Plain SA offset**: sigma_offset = 11.05 mV = **0.47 V_T**, 3sigma = **1.42 V_T** (N=24 MC, 1x).
  -> a plain SA re-injects ~half a decision-window of per-column V_th shift. **This rewrites
  claim (a)/(c): bias cancels at the MTJ level (P3), but the SA offset re-introduces it.**
- **Offset-vs-area co-design**: 4x input-pair area drops the offset well below the 0.3 V_T
  budget (`offset_mc_s4.json` reports ~0.04 V_T, but that is GRID-RESOLUTION-LIMITED at the
  ~1mV floor; Pelgrom 1/sqrt(area) + latch-offset gain-suppression predict a few mV). The
  qualitative co-design (area buys offset margin) is clear; the small-offset value needs a
  finer vind grid. Either way it bounds the SA area to meet a budget, or motivates
  auto-zero/chopper (cited prior art ISSCC 2018).
- **Accuracy axis**: `hero_mnist_sweep.py` injects the offset at inference (the new R2
  `sigma_sense_offset_V` channel) and re-evaluates FULL_STACK MNIST accuracy (see
  `../interface/hero_mnist_summary.json`). NB: use `sigmoid_direct` variation (V_th at
  nominal); `delta` mode centers V_th at the NB-bridge 0.843V (~53mV systematic) and
  corrupts FULL_STACK — the documented checkpoint-inference trap.
  **Result**: baseline 96.80%; a per-cell random offset up to 30mV (1.28 V_T) leaves accuracy
  ~flat (96.8%) — the per-cell model UNDERSTATES, because the offset is small vs V_th=896mV and
  per-cell averaging + theta-x100 tolerate it. The SA offset is per-OUTPUT-COLUMN SYSTEMATIC
  (one SA per column), so the **per-column model is the needed refinement** for the real
  accuracy curve (inject a per-output offset on the preactivation before sign, mapped from the
  SA volts via P3's popcount LSB). This is the key modeling decision for the hero accuracy axis.

## Honest caveats (must appear in the paper)
- AVT is a sky130-class assumption (not the PDK statistical mismatch model); 130nm/1.8V is
  pessimistic -> all conclusions are RATIOS (offset/V_T, area), never absolute mV.
- Offset modelled as per-cell V_th-equivalent (first-cut); per-output-column systematic is
  the refinement.
- RNG owned by the Python harness (OpenVAF/ngspice can't do reliable in-model $rdist).

## Next (the interactive-EDA boundary)
- Auto-zero/chopper SA variant (offset << V_T) — switched-cap, more involved.
- **Magic LAYOUT -> GDS -> Netgen LVS -> ext2spice PEX -> post-layout corner sim** of one
  SA + column slice. This is the "导出版图" deliverable but needs interactive Magic/Xschem
  GUI work (or a scripted tcl flow) — the natural hand-off / decision point.
- Hero figure: extracted sigma_offset -> hero_mnist curve -> accuracy recovery at iso read-energy.
