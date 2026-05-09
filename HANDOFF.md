# Handoff Notes — `smtj_pbnn_sim`

This document is for the next agent (or human) who will continue work on
the simulator on a local machine. It describes what's done, what's left,
how to verify, and how to extend.

---

## 1. State at handoff

### 1.1 What's complete and verified

The **device, calibration, variation, TMR, and PPA layers** are fully
implemented and tested against the real Chapter 2.3 measurement data.
All 32 unit tests pass without PyTorch installed (`pytest tests/`).

Specifically:

* `device.arrhenius` — Néel-Brown (cross-pulse-width) and Sigmoid
  (operating-point) compact models, with the analytic NB→Sigmoid bridge
  $\beta_{NB} = 2\ln 2 \cdot \Delta/V_{c0}$. Verified to give 7.94 V⁻¹ for
  the chapter primary reference (Δ = 4.91, V_c0 = 0.857 V).
* `device.calibration` — fits per-(device, direction) Sigmoids; reproduces
  V_th = 895.8 mV, β_s = 42.7 V⁻¹, R² = 0.992 for Device A P→AP from the
  measured CSV (chapter reports 894 mV / 44.6 V⁻¹ / 0.993).
* `device.variation` — sampling Δ_i ∼ N(μ_Δ, (CV·μ_Δ)²) and propagating
  through the NB→Sigmoid bridge. At PDK baseline CV(Δ) = 7.7%, the
  wafer-mean β_s reproduces the joint prediction to <1%.
* `device.tmr` — three-terminal resistance description (R_P, R_AP, R_SOT)
  and `sot_write_energy` returning 0.78 pJ at 0.9 V / 0.75 ns / 776 Ω
  (matches Chapter 2.3 exactly).
* `ppa.tech_params` — SOT write energy enters as a derived property from
  V_wr, R_SOT, t_p, so changing V_wr re-derives the per-MAC energy
  automatically; sMTJ write dominates 98.7% of the per-MAC budget.

The **network and sampling layers** (`nn/`, `sampling/`, the MNIST
`scripts/_mnist_*.py`, the CLI) are written but **not yet executed** —
this sandbox couldn't install PyTorch (CPU wheel from `download.pytorch.org`
is not in the egress whitelist; PyPI default torch wheel ships GPU libs
that exceed the 9 GB disk). The torch-dependent unit tests under
`tests/test_torch_nn.py` are auto-skipped when torch is missing; they
will run when torch is present.

The **experiments folder** has four scripts (01–04) that run without
torch and reproduce Chapter 2.3 figures, plus three (05–07) that require
torch and are wired to the trained checkpoint.

### 1.2 What's left

Everything below requires a local PyTorch install:

| Item | Notes |
|---|---|
| MNIST training smoke run | `python experiments/05_mnist_pbnn.py`. Should converge to >97% test acc on a 1024-hidden 3-layer PBNN-MLP within ~5 epochs. |
| T-vs-accuracy sweep | `python experiments/06_sweep_T_vs_accuracy.py` after step above. |
| Variation robustness sweep | `python experiments/07_variation_sweep.py`. |
| `test_torch_nn.py` | Should pass once torch is installed; covers STE, CLT-Gaussian forward, three-mode parity. |
| CIFAR-10 PBNN-CNN | Not yet wired. Use `PBNNConv2d` from `smtj_pbnn_sim.nn.pbnn_conv` to build a small CNN; copy the structure of `_mnist_train.PBNN_MLP`. |
| Baseline comparison | `train.compare_baseline.BaselineResult` schema is defined; populate `configs/baseline/{stt_bnn, sot_bnn, aihwkit}.yaml` from published numbers, then write `experiments/08_ppa_compare_baseline.py`. |
| Calibration guide | `docs/calibration_guide.md` exists as a brief stub (see below); expand once the local agent has run more calibration cases. |

---

## 2. Quick-start for the local agent

```bash
# 1. Clone / unpack and install in editable mode (CPU-only torch is fine):
cd smtj_pbnn_sim
pip install -e .
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Run the non-torch tests first (must pass):
pytest tests/ -v
#   expect: 32 passed, 1 skipped (torch tests)

# 3. Reproduce chapter-2.3 figures:
python experiments/01_device_calibration.py
python experiments/02_wafer_average_mc.py
python experiments/03_nb_cross_pulse_width.py
python experiments/04_ppa_breakdown.py

# 4. Re-run all tests including torch:
pytest tests/ -v
#   expect: ~38 passed, 0 skipped

# 5. Train MNIST and reproduce the system-level figures:
python experiments/05_mnist_pbnn.py
python experiments/06_sweep_T_vs_accuracy.py
python experiments/07_variation_sweep.py
```

If a step fails, see Section 5 below for known traps.

---

## 3. Code organization (current)

```
smtj_pbnn_sim/
├── README.md                    user-facing quick start
├── HANDOFF.md                   this file
├── pyproject.toml
├── configs/
│   ├── device/sot_smtj_devA_pAP_0p75ns.yaml   primary reference
│   ├── array/256x256.yaml
│   └── experiment/mnist_lenet.yaml
├── data/smtj_psw_curves/
│   └── measured_0p75ns.csv      real Chapter 2.3 data, 46 points
├── docs/
│   ├── calibration_guide.md
│   └── physics_grounding.md     where every number comes from
├── experiments/
│   ├── 01_device_calibration.py        no torch
│   ├── 02_wafer_average_mc.py          no torch
│   ├── 03_nb_cross_pulse_width.py      no torch
│   ├── 04_ppa_breakdown.py             no torch
│   ├── 05_mnist_pbnn.py                torch
│   ├── 06_sweep_T_vs_accuracy.py       torch
│   └── 07_variation_sweep.py           torch
├── figures/                     experiment outputs (PNG)
├── scripts/extract_chapter2_data.py    data ingestion utility
├── src/smtj_pbnn_sim/
│   ├── device/                  arrhenius, tmr, variation, calibration, llg_dynamics
│   ├── array/                   crossbar, periphery, tile, ir_drop
│   ├── nn/                      pbnn_linear, pbnn_conv, ste, clt, batchnorm, losses
│   ├── sampling/                bernoulli_smtj, unfold, schedules
│   ├── ppa/                     tech_params, energy, latency, area
│   ├── train/                   train_loop, inference, uncertainty, compare_baseline
│   ├── data/mnist.py
│   ├── scripts/                 _mnist_train, _mnist_eval (CLI implementations)
│   ├── utils/                   seeding, io, logging
│   └── cli.py                   smtj-cal, smtj-train, smtj-eval entry points
└── tests/
    ├── conftest.py
    ├── test_arrhenius.py        10 tests, no torch
    ├── test_calibration.py      6 tests, no torch
    ├── test_variation.py        5 tests, no torch
    ├── test_tmr.py              4 tests, no torch
    ├── test_ppa.py              7 tests, no torch
    └── test_torch_nn.py         ~6 tests, torch only
```

---

## 4. Physics grounding (where every default number comes from)

| Symbol | Default | Source |
|---|---|---|
| V_th_nom | 0.894 V | Chapter 2.3 Table 2.3-3, Device A P→AP, 100-shot Sigmoid fit |
| V_T_nom | 1/44.6 ≈ 0.02242 V | same |
| β_s_nom | 44.6 V⁻¹ | same |
| Δ_nom | 4.91 | Chapter 2.3 Table 2.3-9, NB inversion of V_th(t_w) |
| V_c0_nom | 0.857 V | same |
| τ_0 | 1 ns | Chapter 2.3 prior |
| η_c | 5.34 | Chapter 2.3 §2.3.5 (β_s_meas / β_NB_fit) |
| CV(Δ) | 7.7 % | Chapter 2.3 §2.3.6, Brinkman-decomposed PDK baseline |
| R_P | 4.9 kΩ | Chapter 2.3 §2.3.3, Device A R_AP/R_P readout |
| TMR | 1.0 (100 %) | Chapter 2.3 Table 2.3-1 typical 100–120 % |
| R_SOT | 776 Ω | Chapter 2.3 Table 2.3-2 |
| V_wr | 0.9 V | Chapter 2.3 §2.3.3 (V_th+ at 0.75 ns) |
| t_w | 0.75 ns | Chapter 2.3 §2.3.3 |
| E_write | ≈0.78 pJ | derived: V²/R · t (matches Chapter 2.3) |

Every constant appears in YAML form (not hardcoded) under `configs/`. To
swap to a different operating point, edit the YAML; nothing in the source
needs to change.

---

## 5. Known traps and gotchas

### 5.1 Sandbox vs. local: PyTorch availability

The repo uses lazy torch dispatch in the device layer (NumPy primary,
torch only when an explicit `torch.device` is passed to the variation
sampler). This is intentional, so calibration and PPA scripts can run
without torch. Don't unify them — it's how `pytest` runs in CI without
torch.

### 5.2 NB→Sigmoid analytic slope formula

In an earlier version I had `β_NB = (Δ/V_c0)·ln(t_p/τ_0)`, which is
**wrong** when t_p < τ_0 (gives negative β). The correct closed form,
obtained by differentiating the NB expression at P_sw = 1/2, is

    β_NB = 2 · ln(2) · (Δ / V_c0)   (independent of t_p)

This matches Chapter 2.3 Table 2.3-9 (β_NB ≈ 7.94 V⁻¹) exactly. If you
re-derive and disagree, check that you're matching the **logistic slope**
(β/4 at center) to the **NB slope** (½ · ln 2 · Δ/V_c0 at center).

### 5.3 Variation field shape vs. tile shape

`PBNNLinear._ensure_variation` draws a field of shape `(out_features,
in_features)`. This means each *weight* has its own (V_th, V_T) — not
each cell. If you later move to a tile-based mapping where one weight
maps to multiple cells, override `_ensure_variation` to draw with the
tile-aware shape.

### 5.4 Gradients in three modes

* `SOFTWARE` and `HARDWARE_AWARE` — gradients flow through `θ` via the
  CLT-Gaussian forward (`bernoulli_pm1_clt_forward`) and through the
  STE sign at the output. Standard.
* `FULL_STACK` — wrapped in `torch.no_grad()`; gradients **don't** flow.
  Always train in HARDWARE_AWARE mode and only switch to FULL_STACK at
  evaluation. The training script does this automatically; user scripts
  should follow the same convention.

### 5.5 `T_full_stack=1` is degenerate

A T=1 explicit-sample pass is equivalent to a single Bernoulli draw,
which has very high variance. The CLT path (HARDWARE_AWARE mode with
`sample=True`) is a much better approximation in this regime. For
inference, T should be ≥8.

### 5.6 PPA constants are placeholders for CMOS peripherals

`tech_params.TechParams.e_dac_step`, `e_smtj_read`, `e_count_inc`, and
all areas are 28 nm order-of-magnitude defaults. The **only** PPA number
that's actually grounded in Chapter 2.3 is `e_smtj_write` (the SOT
channel dissipation). For absolute energy/latency comparisons against
e.g. STT-BNN, replace the CMOS constants with NeuroSim V1.5
floorplan-derived numbers. The relative T-scaling is correct as-is.

### 5.7 CSV column units

The CSV at `data/smtj_psw_curves/measured_0p75ns.csv` stores **V in
volts and t_p in seconds**. The chapter-2 figure script worked in mV and
ns. The conversion happens in `scripts/extract_chapter2_data.py`. If you
add new measurements, follow the volts/seconds convention.

### 5.8 Backwards compatibility for variation modes

`VariationConfig` defaults to `mode="delta"`. The legacy
`mode="sigmoid_direct"` mode is kept for cases where only operating-point
Sigmoid statistics are available. If you load an old YAML written before
the rewrite, it may not have `mode:` — the YAML reader will default to
`"delta"`, which requires `Delta_nom` and `V_c0_nom` in the device YAML.
Make sure those keys exist before loading.

---

## 6. Extending the simulator

### 6.1 New devices / batches

1. Add a new CSV under `data/smtj_psw_curves/` (columns:
   `V, t_p, P_sw, device_id, direction, n_reps`).
2. Run `python experiments/01_device_calibration.py` — modify the script
   to point to the new CSV and pick the desired `(device_id, direction)`
   as primary.
3. The new YAML lands in `configs/device/`; reference it from your
   experiment YAML by editing the `device:` block.

### 6.2 New networks

1. Drop new architecture file under `src/smtj_pbnn_sim/scripts/_<arch>_train.py`,
   following the structure of `_mnist_train.PBNN_MLP`.
2. Wire in `cli.train_entry`'s `dataset` dispatch.
3. Add a new YAML under `configs/experiment/`.
4. Add a thin wrapper under `experiments/`.

### 6.3 New PPA technology nodes

`TechParams` is a dataclass; subclass it or instantiate with custom
constants. To swap globally, edit `ppa.tech_params.default_28nm()`.

### 6.4 Adding a sigmoid-direct calibration path

If only operating-point Sigmoid distributions are available (no NB
inversion), use `VariationConfig(mode="sigmoid_direct", ...)` and supply
`sigma_V_th_rel` / `sigma_V_T_rel` directly. The bridge through Δ is
bypassed.

---

## 7. Open design questions for the next agent

1. **Tile vs. weight granularity for variation.** Current implementation
   draws variation per weight; should it be per *cell* (with N samples
   per weight on a multi-cell tile) for higher fidelity? Probably yes
   for a future iteration.

2. **Read-path noise model.** Chapter 2.3 doesn't characterize
   read-noise statistics. Should we assume 0 for now or add a small
   Gaussian on G_P, G_AP? Suggest leaving at 0 until empirical data
   appears.

3. **eta_c temperature dependence.** η_c is treated as a constant.
   Chapter 2.3 hints at sub-domain dynamics that may be temperature- or
   pulse-shape-dependent. Revisit if temperature variation is added.

4. **IR-drop activation.** `array.ir_drop.estimate_ir_drop` is a stub.
   For sub-arrays > 256×256 it should be enabled in `array.tile.Tile`
   and propagated to the per-bit-line voltage, which then modulates the
   per-cell V_wr. Only matters at very large arrays.

5. **Compatibility with Chapter 4 PBNN training math.** The current CLT
   forward is the Peters-Welling formulation. If the chapter-4 derivation
   uses LAR-net style local reparameterization with covariance terms,
   `bernoulli_pm1_clt_forward` may need to gain a covariance argument.
   Cross-check before training.

---

## 8. Reproducibility

* All experiments use the seed in their config or a hard-coded seed of 42.
* `utils.seeding.set_global_seed` seeds Python, NumPy, and Torch.
* The MNIST experiment writes `runs/<name>/resolved.yaml` with the full
  resolved config alongside `best.pt`, so any run can be reproduced via
  `smtj-train --config runs/<name>/resolved.yaml`.

---

## 9. Contact / questions

If anything in this document conflicts with what you find in the code,
the code is the source of truth — but flag the discrepancy for the next
update of this file.
