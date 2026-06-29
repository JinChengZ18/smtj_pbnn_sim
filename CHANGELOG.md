# Changelog & Project Reference

This document serves dual purpose: **version changelog** for the `smtj_pbnn_sim` package, and **project reference** for maintainers (consolidated from the former HANDOFF.md and LOCAL_AGENT_BRIEF.md).

---

## Architecture & Design Decisions

### Physics grounding (where every default number comes from)

| Symbol | Default | Source |
|---|---|---|
| V_th_nom | 0.894 V | Chapter 2.3 Table 2.3-3, Device A P->AP, 100-shot Sigmoid fit |
| V_T_nom | 1/44.6 = 0.02242 V | same |
| beta_s_nom | 44.6 V^-1 | same |
| Delta_nom | 4.91 | Chapter 2.3 Table 2.3-9, NB inversion of V_th(t_w) |
| V_c0_nom | 0.857 V | same |
| tau_0 | 1 ns | Chapter 2.3 prior |
| eta_c | 5.34 | Chapter 2.3 S2.3.5 (beta_s_meas / beta_NB_fit) |
| CV(Delta) | 7.7 % | Chapter 2.3 S2.3.6, Brinkman-decomposed PDK baseline |
| R_P | 4.9 kOhm | Chapter 2.3 S2.3.3, Device A R_AP/R_P readout |
| TMR | 1.0 (100 %) | Chapter 2.3 Table 2.3-1 typical 100-120 % |
| R_SOT | 776 Ohm | Chapter 2.3 Table 2.3-2 |
| V_wr | 0.9 V | Chapter 2.3 S2.3.3 (V_th+ at 0.75 ns) |
| t_w | 0.75 ns | Chapter 2.3 S2.3.3 |
| E_write | ~0.78 pJ | derived: V^2/R * t (matches Chapter 2.3) |

Every constant appears in YAML form (not hardcoded) under `configs/`. To swap to a different operating point, edit the YAML; nothing in the source needs to change.

### Lazy torch dispatch

NumPy is the primary backend in the device layer; torch is only invoked when explicitly requested (e.g., via `device=` argument to `VariationSampler.sample`). This lets the calibration scripts and most unit tests run in a torch-free CI. Don't unify them.

### YAML schema with explicit sections

`device:` block has `operating_point`, `neel_brown`, `resistance`, plus a top-level `eta_c`. A YAML file alone fully specifies a device configuration.

### Three forward modes share theta

Same trained checkpoint runs in all three modes (SOFTWARE, HARDWARE_AWARE, FULL_STACK); no software-vs-hardware fork.

### `mode='delta'` as default for variation

Aligns the simulator with the Chapter 2.3 PDK Brinkman decomposition (CV on Delta, not on Sigmoid parameters directly).

### Open design questions

1. **Tile vs. weight granularity for variation.** Current implementation draws variation per weight; should it be per *cell* (with N samples per weight on a multi-cell tile) for higher fidelity? Probably yes for a future iteration.

2. **Read-path noise model.** Chapter 2.3 doesn't characterize read-noise statistics. Suggest leaving at 0 until empirical data appears.

3. **eta_c temperature dependence.** eta_c is treated as a constant. Chapter 2.3 hints at sub-domain dynamics that may be temperature-or pulse-shape-dependent. Revisit if temperature variation is added.

4. **IR-drop activation.** `array.ir_drop.estimate_ir_drop` is a stub. For sub-arrays > 256x256 it should be enabled in `array.tile.Tile` and propagated to the per-bit-line voltage.

5. **Compatibility with Chapter 4 PBNN training math.** The current CLT forward is the Peters-Welling formulation. If the chapter-4 derivation uses LAR-net style local reparameterization with covariance terms, `bernoulli_pm1_clt_forward` may need to gain a covariance argument.

---

## Known Traps & Gotchas

### The 843 vs 894 mV question

In `mode='delta'` the per-cell V_th is computed from the NB closed form `V_th(t_p) = V_c0 * (1 - ln(t_p / tau_0 / ln2) / Delta)`. With chapter parameters Delta = 4.91, V_c0 = 0.857 V, this gives 843.2 mV at t_p = 0.75 ns -- which is **NOT** the measured Sigmoid center (894 mV). The ~50 mV offset is the well-known NB-vs-measurement mismatch (Chapter 2.3 S2.3.5), and `eta_c = 5.34` corrects the slope, not the center.

If you want the network to use the measured 894 mV as the center, set `mode='sigmoid_direct'` in your variation YAML and supply `sigma_V_th_rel`. This trades physical NB->Sigmoid coupling for direct operating-point statistics.

### NB->Sigmoid analytic slope formula

In an earlier version the formula was `beta_NB = (Delta/V_c0) * ln(t_p/tau_0)`, which is **wrong** when t_p < tau_0 (gives negative beta). The correct closed form, obtained by differentiating the NB expression at P_sw = 1/2:

    beta_NB = 2 * ln(2) * (Delta / V_c0)   (independent of t_p)

This matches Chapter 2.3 Table 2.3-9 (beta_NB ~ 7.94 V^-1) exactly.

### Variation field shape vs. tile shape

`PBNNLinear._ensure_variation` draws a field of shape `(out_features, in_features)`. This means each *weight* has its own (V_th, V_T) -- not each cell. If you later move to a tile-based mapping where one weight maps to multiple cells, override `_ensure_variation` to draw with the tile-aware shape.

### Variation and the write voltage

The write voltage is computed from *nominal* device parameters: `V_wr = V_th_nom + V_T_nom * theta` (the DAC/driver is calibrated once against the nominal device). Each cell's switching probability then depends on its own physical parameters after D2D variation: `p_i = sigmoid((V_wr - V_th_i) / V_T_i)`. Without variation this simplifies to `sigmoid(theta)`; with variation the per-cell threshold shift and slope change modify the soft probability.

Note that this variation effect is visible in FULL_STACK mode (which uses the soft p for Bernoulli sampling) but not in HARDWARE_AWARE mode (which always uses hard binary `sign(theta)` in the forward).

### Gradients in three modes

* `SOFTWARE` and `HARDWARE_AWARE` -- both use hard binary weights `sign(theta)` in the forward via the `_harden()` STE trick: `p_hard = (theta >= 0).detach() + p_soft - p_soft.detach()`. Forward values are always binary; backward gradients flow through `sigmoid(theta)` (SOFTWARE) or the device Sigmoid (HARDWARE_AWARE), giving smooth `dp/dtheta = p_soft * (1 - p_soft)`.
* `FULL_STACK` -- wrapped in `torch.no_grad()`; gradients **don't** flow. Always train in HARDWARE_AWARE mode and only switch to FULL_STACK at evaluation. When switching modes, use `calibrate_bn()` to recalibrate BatchNorm running statistics for the new mode's preactivation distribution.

### Training pipeline design

* All hidden layers use `binarize_output=False`; binarization is done externally as BN -> sign_ste, which normalizes preactivations to O(1) before the STE clips at |z| <= 1.
* Training uses `sample=False` (deterministic CLT mean). The sign_ste provides the binary stochastic structure; CLT sampling noise adds O(sqrt(N)) variance that BN normalizes away but attenuates gradients.
* Post-training theta scaling (x100) makes `sigmoid(theta)` near 0/1 for near-deterministic FULL_STACK. `sign(theta)` is invariant to this scaling.

### T_full_stack=1 is degenerate

A T=1 explicit-sample pass is equivalent to a single Bernoulli draw, which has very high variance. The CLT path (HARDWARE_AWARE mode with `sample=True`) is a much better approximation. For inference, T >= 8.

### PPA constants are placeholders for CMOS peripherals

As of 0.4.0 the peripheral **energies** are sky130-grounded: `e_smtj_read` (~48 fJ, extracted StrongARM SA), `e_dac_step` (~34 fJ) and `e_count_inc` (~19 fJ) via `eda/testbenches/dac_counter_energy.py`, plus the physically-derived `e_smtj_write` (SOT channel dissipation). Only the **area** constants (`a_smtj_cell`, `a_sot_track`, `a_dac`, `a_counter`) remain 28 nm order-of-magnitude — replace via sky130 layout extraction before absolute area claims (plan in `.agents/eda/PPA_grounding_plan.md`).

### CSV column units

The CSV at `data/smtj_psw_curves/measured_0p75ns.csv` stores **V in volts and t_p in seconds**. The chapter-2 figure script worked in mV and ns. If you add new measurements, follow the volts/seconds convention.

### Backwards compatibility for variation modes

`VariationConfig` defaults to `mode="delta"`. If you load an old YAML written before the rewrite, it may not have `mode:` -- the YAML reader will default to `"delta"`, which requires `Delta_nom` and `V_c0_nom` in the device YAML. Make sure those keys exist before loading.

---

## Extension Guide

### New devices / batches

1. Add a new CSV under `data/smtj_psw_curves/` (columns: `V, t_p, P_sw, device_id, direction, n_reps`).
2. Run `python experiments/01_device_calibration.py` -- modify the script to point to the new CSV and pick the desired `(device_id, direction)` as primary.
3. The new YAML lands in `configs/device/`; reference it from your experiment YAML by editing the `device:` block.

### New networks

1. Drop new architecture file under `src/smtj_pbnn_sim/scripts/_<arch>_train.py`, following the structure of `_mnist_train.PBNN_MLP`.
2. Wire in `cli.train_entry`'s `dataset` dispatch.
3. Add a new YAML under `configs/experiment/`.
4. Add a thin wrapper under `experiments/`.

### New PPA technology nodes

`TechParams` is a dataclass; subclass it or instantiate with custom constants. To swap globally, edit `ppa.tech_params.default_28nm()`.

### Adding a sigmoid-direct calibration path

If only operating-point Sigmoid distributions are available (no NB inversion), use `VariationConfig(mode="sigmoid_direct", ...)` and supply `sigma_V_th_rel` / `sigma_V_T_rel` directly. The bridge through Delta is bypassed.

---

## Protected Files

Files that should NOT be modified unless you have a specific reason:

| File | Why |
|---|---|
| `device/arrhenius.py` | Locked to Chapter 2.3 closed forms; verified analytically |
| `device/calibration.py` | Locked to fitting routines verified against real data |
| `data/smtj_psw_curves/measured_0p75ns.csv` | Source of truth |
| `tests/test_arrhenius.py` | Regression hard-rails for the chapter physics |
| `tests/test_calibration.py` | Regression hard-rails for the chapter physics |
| `tests/test_variation.py` | Regression hard-rails for the chapter physics |
| `tests/test_tmr.py` | Regression hard-rails for the chapter physics |
| `tests/test_ppa.py` | Regression hard-rails for the chapter physics |

---

## Reproducibility

* All experiments use the seed in their config or a hard-coded seed of 42.
* `utils.seeding.set_global_seed` seeds Python, NumPy, and Torch.
* The MNIST experiment writes `runs/<name>/resolved.yaml` alongside `best.pt`, so any run can be reproduced with `smtj-train --config runs/<name>/resolved.yaml`.
* Training metrics are persisted to `runs/<name>/metrics.csv` with per-epoch loss, accuracy, and wall-clock timing.

---

## 0.4.0 -- sky130 EDA co-design grounding, figure/article refinement, seed-independence

Grounds the simulator's CMOS-peripheral PPA inputs in an open-source sky130 (130 nm/1.8 V) flow, refines the thesis figures and prose to journal grade, restructures the appendices, and adds a reviewer-requested seed-independence study. No change to the device physics or the core PBNN/RC math.

### Added -- sky130 EDA co-design (`eda/`)

* Readout: StrongARM sense-amp extracted on sky130 (input-referred offset 0.39 V_T, decision energy ~48 fJ, replacing the 5 fJ placeholder, errata R1); slope-matched TIA front-end; column-shared SAR readout.
* Write path: voltage-mode resistor-string write-DAC (adopted after a binary-weighted current-steering first cut failed monotonicity at INL ~1.7 LSB), IR-aware per-row write pre-distortion, and write-line IR extracted via Magic extresist (N=256 round-trip ~16.5% of R_SOT).
* Journal schematics (Xschem -> SVG -> cairosvg) for the readout SA, the write path, and the SAR readout, plus a device->array->periphery->modes architecture diagram.
* `eda/testbenches/dac_counter_energy.py`: grounds `e_dac_step` (~34 fJ) and `e_count_inc` (~19 fJ) in sky130 (ngspice analog core + sky130 stdcell-capacitance digital estimate).

### Added -- experiments + supplement

* `experiments/21_seed_independence.py`: re-runs the four headline conclusions over 8 seeds; all are seed-robust (PBNN MNIST 97.01%+-0.17, T64-T4 gap 0.21+-0.11 pp, RC memory capacity 2.11+-0.22, RC energy advantage 30.2x, device beta_s 9.51+-0.01).
* `experiments/05a_*` CNN extension on Fashion-MNIST / CIFAR-10.
* `article/supplement_eda_codesign.md` integrated into chapters 4-5.

### Changed -- PPA grounding

* `tech_params`: `e_smtj_read` 5 fJ -> 48 fJ, `e_dac_step` 5 fJ -> 34 fJ, `e_count_inc` 0.5 fJ -> 19 fJ (all sky130-grounded); per-MAC peripheral share ~1% -> ~11%, with the SOT write still ~89%. Only the four AREA constants remain 28 nm placeholders (plan in `.agents/eda/PPA_grounding_plan.md`).
* `tests/test_ppa.py`: write-fraction threshold updated to the grounded breakdown. Full suite: 111 passing (torch included).

### Changed -- article / figures

* Figure production norms: generators bake no panel letters, figure numbers, Chinese, or hard-coded chapter strings; in-figure math uses real subscripts; comparison plots label points directly (no legend). Recorded in `.agents/eda/research/2026-06-28_figure_conventions.md`.
* Analysis figures unified into the chapter decks (`article/ppt/Chapter0{4,5}_local.pptx`); the separate autofigs decks were removed.
* Architecture diagram moved from Chapter 4 (图4.23) to Chapter 5 (图5.10), where it caps the unified three-mode discussion.
* Appendices restructured: A = code & data availability (new), B = CNN extension (was A), C = seed-independence (new).
* Trial-and-error / correction footnotes added (device V_th anchoring, read-energy 5->48 fJ, write-line IR, CIFAR-10 convergence).

---

## 0.3.0 -- sMTJ reservoir-computing extension (hardware eval + device optimization)

New research direction: repurpose the *same* calibrated sMTJ device as the
dynamical substrate of a physical reservoir computer (RC), instead of a
memoryless PBNN p-bit. Planning doc: `article/plan/chapter5_rc_plan.md`.

### Added -- stateful device physics

* **`device/arrhenius.py::neel_brown_rate`** -- additive: exposes the
  continuous-time Néel-Brown hazard rate `W(V) = (1/tau_0) exp[-Delta(1-V/V_c0)]`
  that already underlies `psw_neel_brown`. Needed because RC uses the rate, not
  a pulse-integrated probability. Existing closed forms untouched; all
  `test_arrhenius.py` rails still pass.
* **`device/telegraph.py`** -- stateful two-state random-telegraph-noise model:
  a population of superparamagnetic sMTJs as a continuous-time Markov process
  with the exact two-state propagator (any `dt`). Closed forms:
  `stationary_mean(V) = tanh(Delta V/V_c0)` (the nonlinearity) and
  `relaxation_time(V) = 1/(r_up+r_dn)` (the tunable fading memory, ~68 ns at
  zero bias for the Chapter 2.3 device). NumPy-only; not in the PBNN forward path.

### Added -- reservoir layer (`src/smtj_pbnn_sim/reservoir/`)

* `node.py` -- `SMTJReservoir`: fixed random pool of telegraph nodes, input
  injection + optional spectral-radius-scaled recurrence, per-node Delta
  heterogeneity, ensemble averaging (devices/node), and a noise-free
  `meanfield` mode (the RC analogue of PBNN `software` mode). Couplings are
  specified in ESN-effective units and converted to volts via the steep
  transfer slope `Delta/V_c0` to stay in the echo-state regime.
* `readout.py` -- closed-form ridge readout (the only trained part).
* `tasks.py` -- NARMA-10, memory-capacity input, product-memory (nonlinear),
  sine/square.
* `metrics.py` -- NRMSE and linear memory capacity (Jaeger 2001).

### Added -- PPA for RC (`ppa/reservoir_energy.py`)

* `smtj_rc_*` and `digital_esn_*` energy on the Chapter-2.3 `tech_params`
  footing; digital ESN bracketed between conventional digital MAC and an
  optimistic in-array CIM lower bound.

### Added -- experiments

* `14_rc_prototype.py` -- viability: mean-field MC ~ 6.6, NARMA-10 NRMSE ~ 0.61;
  real device (ensemble=96) MC ~ 2.0, NRMSE ~ 0.81. Surfaces the shot-noise limit.
* `15_rc_device_optimization.py` -- **device guidance**: optimal barrier tracks
  task timescale, `tau* ~ 2.3 dt`; RC optimum `Delta ~ 3.5` sits *below* the
  PBNN write device's `Delta = 4.91` (RC wants a more superparamagnetic, lower-
  barrier device); memory/nonlinearity Pareto set by operating-point bias.
* `16_rc_hardware_ppa.py` -- **hardware eval**: sMTJ-RC replaces the digital
  ESN's O(N^2) recurrent matmul with O(N x ensemble) analog physics; ~38x lower
  energy than a conventional digital ESN and ~8x better energy-per-MC, though an
  idealized ADC-free CIM ESN remains a cheaper floor (honest bracket).

### Added -- tests

* `tests/test_telegraph.py`, `tests/test_reservoir.py`, and RC-energy cases in
  `tests/test_ppa.py`. Suite: 61 -> 93 passing.

---

## 0.2.0 -- Local session, training pipeline and variation fix

### Fixed -- training pipeline (from non-functional to working)

* **`binarize_output=False` for hidden layers** -- `_mnist_train.PBNN_MLP` was constructed with `binarize_output=True`, which applied `sign_ste` to raw preactivations of magnitude ~28 (from 784 or 1024 input sums). The STE gradient clips to zero for `|z| > 1`, killing all learning. Fixed by setting `binarize_output=False` and binarizing externally via BN -> sign_ste, which normalizes preactivations to O(1) first.

* **`sample=False` during training** -- CLT sampling noise of O(sqrt(N)) ~ 28 was being normalized away by BN in the forward pass but attenuated backward gradients by 1/sigma_raw per layer. Fixed by using the deterministic CLT mean (`sample=False`) during training; the sign_ste already provides the essential binary stochastic structure.

* **Hard binary STE (`_harden`)** -- the network previously used infinitesimal soft weights `2*sigmoid(theta)-1 in [-1,1]` amplified by BN gain, achieving 97.7% train accuracy but 10% on FULL_STACK (all p ~ 0.5). Added `_harden()` method that snaps p to {0,1} in the forward (`p_hard = (theta >= 0).float()`) while flowing gradients through `sigmoid(theta)` in the backward. Applied in both SOFTWARE and HARDWARE_AWARE modes for train and eval, ensuring BN running stats are consistent and FULL_STACK receives meaningful p values.

* **Post-training theta scaling** -- after training, `theta` magnitudes are ~0.5, so `sigmoid(theta)` ~ 0.6 and Bernoulli draws in FULL_STACK are noisy. Added post-training scaling of theta x 100, making `sigmoid(theta)` near 0 or 1 for near-deterministic FULL_STACK. `sign(theta)` is invariant to positive scaling, so HARDWARE_AWARE eval is unaffected.

* **Checkpoint loading for lazy variation buffers** -- variation fields `V_th_field` and `V_T_field` are initialized as empty tensors (shape 0) and populated lazily on first forward. Loading from a checkpoint with populated buffers caused a `size mismatch` error. Added `_load_from_state_dict` override to resize buffers before `copy_()`.

* **BN calibration for cross-mode evaluation** -- added `calibrate_bn()` in `train_loop.py` to recalibrate BN running stats when switching from HARDWARE_AWARE (training) to FULL_STACK (evaluation). Resets running mean/var and re-estimates over 50 batches of forward passes in the target mode.

### Fixed -- variation model

* **Variation cancellation bug** -- `_p_hardware()` and `_p_soft_for_sampling()` computed write voltage as `V_wr = V_th_field + V_T_field * theta`, which when fed into `psw_sigmoid(V_wr, V_th_field, V_T_field) = sigmoid((V_wr - V_th) / V_T)` simplified to `sigmoid(theta)` -- D2D variation cancelled completely. Fixed by using nominal parameters for V_wr: `V_wr = V_th_nom + V_T_nom * theta` (the DAC is calibrated against nominal device parameters), while each cell's switching probability uses its own V_th_i and V_T_i from the variation field.

* **Experiment 07 evaluation mode** -- changed from HARDWARE_AWARE (which always uses `sign(theta)`, invariant to variation) to FULL_STACK with BN calibration per variation level, so D2D variation is visible in the Bernoulli sampling.

### Added

* `nn.losses.binarization_regularizer` -- penalizes `p*(1-p)` to encourage theta toward larger magnitudes. Available via `bin_alpha` config key (default 0.0).
* Two new tests in `test_torch_nn.py`:
  - `test_variation_changes_soft_p_in_full_stack` -- verifies that D2D
    variation actually shifts FULL_STACK output.
  - `test_no_variation_hardware_aware_matches_software` -- verifies that
    without variation, HARDWARE_AWARE = SOFTWARE.

* Experiment 08: comprehensive non-ideality ablation study with two figures -- P_sw curve distortion visualization and accuracy-vs-parameter-strength for 5 factors (joint D2D, V_th shift, V_T slope, C2C noise, back-hopping) plus combined scenario.
* Two new tests for C2C noise and p_max:
  - `test_c2c_noise_increases_full_stack_variance`
  - `test_p_max_clamps_full_stack_output`

### Changed

* `configs/experiment/mnist_lenet.yaml` -- epochs 5 -> 20, added `bin_alpha: 0.0`.
* `.gitignore` -- added `data/mnist/`, `.claude/settings.local.json`.
* Test count: 60 passing (49 torch-free + 11 torch-dependent).

### Verification log (training pipeline)

| Check | Expected | Got | Status |
|---|---|---|---|
| MNIST train accuracy (20 epochs) | >95% | 96.82% | pass |
| MNIST test accuracy (HARDWARE_AWARE) | >95% | 96.82% | pass |
| MNIST test accuracy (FULL_STACK T=64) | >95% | 97.5% | pass |
| Three-mode parity (SOFTWARE=HW_AWARE=FULL_STACK) | match | pass | pass |
| Variation effect visible in FULL_STACK | diff > 0 | pass | pass |
| Unit tests | all pass | 60 passed | pass |
| Experiments 01-08 | all run | pass | pass |

---

## 0.1.0 -- Cloud session, initial implementation

### Added -- verified

* Real Chapter 2.3 measurement CSV at `data/smtj_psw_curves/measured_0p75ns.csv` (46 rows, 4 device/direction combinations, t_w = 0.75 ns, 100-shot Wilson CIs implicit in n_reps).
* `device.arrhenius` -- Neel-Brown closed form, Sigmoid form, and the analytic NB->Sigmoid bridge with the corrected formula `beta_NB = 2 ln(2) * Delta/V_c0` (independent of t_p).
  - Verified to give 7.94 V^-1 for chapter primary parameters,
    exactly matching Table 2.3-9.
* `device.calibration` -- per-(device, direction) Sigmoid fit and cross-pulse-width NB inversion.
  - Reproduces chapter V_th = 894 mV / beta_s = 44.6 V^-1 to within
    fitting noise on the real CSV.
* `device.variation` -- D2D sampler with two modes: `delta` (samples Delta_i, propagates via NB bridge) and `sigmoid_direct` (samples V_th / V_T directly). NumPy primary, torch optional.
  - At PDK baseline CV(Delta) = 7.7 %, wafer-mean beta_s = 42.37 V^-1
    matches chapter joint prediction 42.3 V^-1 to <1 %.
* `device.tmr` -- three-terminal SOT-MTJ description (R_P, R_AP, R_SOT, V_read) plus `sot_write_energy` returning V^2/R_SOT * t_p.
  - Verified to give 0.78 pJ at 0.9 V / 0.75 ns / 776 Ohm, exact chapter
    value.
* `ppa.tech_params` with `e_smtj_write` as a derived property; per-MAC energy 793 fJ at chapter operating point (98.7 % from sMTJ write).
* `ppa.energy`, `ppa.latency`, `ppa.area` -- composers above `tech_params`. T-scaling verified.
* `array.ir_drop` -- first-order resistive-ladder estimator (pure Python).
* `array.periphery` -- DAC and counter quantization, NumPy/torch duck-typed.
* `sampling.schedules` -- `constant_T`, `layer_depth_T`, `beta_schedule` (pure Python).
* Experiments 01-04 (no torch): device calibration, wafer-average MC, NB cross-pulse-width inversion, PPA breakdown. All run end-to-end and write figures to `figures/`.
* Tests: 49 passing, 6 deferred (torch).
  - `test_arrhenius.py` -- 10 tests
  - `test_calibration.py` -- 6 tests
  - `test_variation.py` -- 5 tests
  - `test_tmr.py` -- 4 tests
  - `test_ppa.py` -- 7 tests
  - `test_schedules.py` -- 7 tests
  - `test_array_pure.py` -- 10 tests
* YAML configs:
  - `configs/device/sot_smtj_devA_pAP_0p75ns.yaml` (primary reference)
  - `configs/array/256x256.yaml`
  - `configs/experiment/mnist_lenet.yaml`
* Documentation:
  - `README.md`, `HANDOFF.md`, `LOCAL_AGENT_BRIEF.md`
  - `docs/calibration_guide.md`, `docs/physics_grounding.md`,
    `docs/architecture.md`

### Added -- coded but not run

These are present in the source tree, will run once torch is installed, and have unit tests gated by `pytest.importorskip("torch")`:

* `nn.pbnn_linear`, `nn.pbnn_conv` -- three forward modes (SOFTWARE / HARDWARE_AWARE / FULL_STACK).
* `nn.ste`, `nn.clt`, `nn.batchnorm`, `nn.losses`.
* `sampling.bernoulli_smtj`, `sampling.unfold`.
* `array.crossbar`, `array.tile`.
* `train.train_loop`, `train.inference`, `train.uncertainty`, `train.compare_baseline`.
* `data.mnist`.
* `scripts/_mnist_train.py`, `scripts/_mnist_eval.py` -- CLI implementations.
* `cli.py` -- `smtj-train`, `smtj-eval`, `smtj-cal` entry points.
* Experiments 05 (MNIST training), 06 (T sweep), 07 (baseline comparison).
* `tests/test_torch_nn.py` -- 6 tests of STE, CLT, three-mode parity.

### Known issues / deferred

See "Known Traps & Gotchas" section above for the full list. Top three:

1. PPA peripheral constants (DAC, counter, sense, area) are 28 nm order-of-magnitude defaults; replace with NeuroSim V1.5 floorplan output for absolute claims.
2. Variation field is per-weight, not per-cell; sub-sampling per cell needs a future override.
3. The 843 vs 894 mV discrepancy between NB-derived V_th and measured V_th is by design but documented in "Known Traps" above for future review.

### Verification log

| Check | Expected (Chapter 2.3) | Got | Status |
|---|---|---|---|
| Device A P->AP V_th fit | 894 mV | 895.8 mV | pass (within 5 mV) |
| Device A P->AP beta_s fit | 44.6 V^-1 | 42.7 V^-1 | pass (within 3 V^-1) |
| Device A P->AP R^2 | 0.993 | 0.992 | pass (within 0.001) |
| NB analytic beta_NB | 7.94 V^-1 | 7.94 V^-1 | exact |
| AP->P NB inversion Delta | 5.15 | 5.19 | pass (within 0.04) |
| AP->P NB inversion V_c0 | 884 mV | 882 mV | pass (within 2 mV) |
| Wafer beta at CV(Delta)=7.7% | 42.3 V^-1 | 42.37 V^-1 | pass (within 0.1 V^-1) |
| SOT write energy | 0.78 pJ | 0.78 pJ | exact |
| PPA per-MAC energy | n/a | 793 fJ | informational |
| Unit tests | n/a | 49 passed, 1 skipped | pass |
