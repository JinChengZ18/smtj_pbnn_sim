# Changelog

## 0.1.0 — Cloud session, initial implementation

### Added — verified

* Real Chapter 2.3 measurement CSV at
  `data/smtj_psw_curves/measured_0p75ns.csv` (46 rows, 4 device/direction
  combinations, t_w = 0.75 ns, 100-shot Wilson CIs implicit in n_reps).
* `device.arrhenius` — Néel-Brown closed form, Sigmoid form, and the
  analytic NB→Sigmoid bridge with the corrected formula
  `β_NB = 2 ln(2) · Δ/V_c0` (independent of t_p).
  - Verified to give 7.94 V⁻¹ for chapter primary parameters,
    exactly matching Table 2.3-9.
* `device.calibration` — per-(device, direction) Sigmoid fit and
  cross-pulse-width NB inversion.
  - Reproduces chapter V_th = 894 mV / β_s = 44.6 V⁻¹ to within
    fitting noise on the real CSV.
* `device.variation` — D2D sampler with two modes: `delta` (samples
  Δ_i, propagates via NB bridge) and `sigmoid_direct` (samples V_th /
  V_T directly). NumPy primary, torch optional.
  - At PDK baseline CV(Δ) = 7.7 %, wafer-mean β_s = 42.37 V⁻¹ matches
    chapter joint prediction 42.3 V⁻¹ to <1 %.
* `device.tmr` — three-terminal SOT-MTJ description (R_P, R_AP, R_SOT,
  V_read) plus `sot_write_energy` returning V²/R_SOT · t_p.
  - Verified to give 0.78 pJ at 0.9 V / 0.75 ns / 776 Ω, exact chapter
    value.
* `ppa.tech_params` with `e_smtj_write` as a derived property; per-MAC
  energy 793 fJ at chapter operating point (98.7 % from sMTJ write).
* `ppa.energy`, `ppa.latency`, `ppa.area` — composers above
  `tech_params`. T-scaling verified.
* `array.ir_drop` — first-order resistive-ladder estimator (pure
  Python).
* `array.periphery` — DAC and counter quantization, NumPy/torch
  duck-typed.
* `sampling.schedules` — `constant_T`, `layer_depth_T`,
  `beta_schedule` (pure Python).
* Experiments 01–04 (no torch): device calibration, wafer-average MC,
  NB cross-pulse-width inversion, PPA breakdown. All run end-to-end
  and write figures to `figures/`.
* Tests: 49 passing, 6 deferred (torch).
  - `test_arrhenius.py` — 10 tests
  - `test_calibration.py` — 6 tests
  - `test_variation.py` — 5 tests
  - `test_tmr.py` — 4 tests
  - `test_ppa.py` — 7 tests
  - `test_schedules.py` — 7 tests
  - `test_array_pure.py` — 10 tests
* YAML configs:
  - `configs/device/sot_smtj_devA_pAP_0p75ns.yaml` (primary reference)
  - `configs/array/256x256.yaml`
  - `configs/experiment/mnist_lenet.yaml`
* Documentation:
  - `README.md`, `HANDOFF.md`, `LOCAL_AGENT_BRIEF.md`
  - `docs/calibration_guide.md`, `docs/physics_grounding.md`,
    `docs/architecture.md`

### Added — coded but not run

These are present in the source tree, will run once torch is installed,
and have unit tests gated by `pytest.importorskip("torch")`:

* `nn.pbnn_linear`, `nn.pbnn_conv` — three forward modes
  (SOFTWARE / HARDWARE_AWARE / FULL_STACK).
* `nn.ste`, `nn.clt`, `nn.batchnorm`, `nn.losses`.
* `sampling.bernoulli_smtj`, `sampling.unfold`.
* `array.crossbar`, `array.tile`.
* `train.train_loop`, `train.inference`, `train.uncertainty`,
  `train.compare_baseline`.
* `data.mnist`.
* `scripts/_mnist_train.py`, `scripts/_mnist_eval.py` — CLI
  implementations.
* `cli.py` — `smtj-train`, `smtj-eval`, `smtj-cal` entry points.
* Experiments 05 (MNIST training), 06 (T sweep), 07 (variation sweep).
* `tests/test_torch_nn.py` — 6 tests of STE, CLT, three-mode parity.

### Known issues / deferred

See `HANDOFF.md` §5 for the full list. Top three:

1. PPA peripheral constants (DAC, counter, sense, area) are 28 nm
   order-of-magnitude defaults; replace with NeuroSim V1.5 floorplan
   output for absolute claims.
2. Variation field is per-weight, not per-cell; sub-sampling per cell
   needs a future override.
3. The 843 vs 894 mV discrepancy between NB-derived V_th and measured
   V_th is by design but documented in `LOCAL_AGENT_BRIEF.md` for the
   next agent to revisit.

### Decisions

* **Lazy torch dispatch in device layer.** NumPy is the primary
  backend; torch is only invoked when explicitly requested (e.g., via
  `device=` argument to `VariationSampler.sample`). This lets the
  calibration scripts and most unit tests run in a torch-free CI.
* **YAML schema with explicit sections.** `device:` block has
  `operating_point`, `neel_brown`, `resistance`, plus a top-level
  `eta_c`. Designed so a YAML file alone fully specifies a device
  configuration.
* **`mode='delta'` as default for variation.** Aligns the simulator
  with the Chapter 2.3 PDK Brinkman decomposition (CV on Δ, not on
  Sigmoid parameters directly).
* **Three forward modes share `θ`.** Same trained checkpoint runs in
  all three modes; no software-vs-hardware fork.

### Verification log

| Check | Expected (Chapter 2.3) | Got | Status |
|---|---|---|---|
| Device A P→AP V_th fit | 894 mV | 895.8 mV | ✓ within 5 mV |
| Device A P→AP β_s fit | 44.6 V⁻¹ | 42.7 V⁻¹ | ✓ within 3 V⁻¹ |
| Device A P→AP R² | 0.993 | 0.992 | ✓ within 0.001 |
| NB analytic β_NB | 7.94 V⁻¹ | 7.94 V⁻¹ | ✓ exact |
| AP→P NB inversion Δ | 5.15 | 5.19 | ✓ within 0.04 |
| AP→P NB inversion V_c0 | 884 mV | 882 mV | ✓ within 2 mV |
| Wafer β at CV(Δ)=7.7% | 42.3 V⁻¹ | 42.37 V⁻¹ | ✓ within 0.1 V⁻¹ |
| SOT write energy | 0.78 pJ | 0.78 pJ | ✓ exact |
| PPA per-MAC energy | n/a | 793 fJ | informational |
| Unit tests | n/a | 49 passed, 1 skipped | ✓ |
