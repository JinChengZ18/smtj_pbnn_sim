# `smtj_pbnn_sim`

PyTorch-based hardware simulator for **stochastic SOT-MTJ-based probabilistic binary neural networks (PBNN)**.

## Status

* **Device, calibration, variation, TMR, PPA layers**: implemented and verified against the  measurement data.
* **Network and training pipeline**: fully working. MNIST PBNN-MLP achieves **96.98% test accuracy** (HARDWARE_AWARE) and **97.68%** (FULL_STACK T=64) after 20 epochs. Sampling count T=8 already reaches 97.62% — the practical sweet spot for both accuracy and energy.
* **D2D variation**: properly coupled via nominal-calibration write voltage; verified by unit test and experiment 08 non-ideality ablation.
* **Multi-noise robustness (exp 07, T=4)**: 8 noise types (Gaussian, salt-pepper, speckle, blur, cutout, brightness, weight perturb, PGD-10). PBNN at T=4 (sweet spot from exp 06) wins blur, brightness shift, weight perturbation, and PGD-10 attacks; FP-NN wins additive Gaussian, salt-pepper, speckle, and cutout. T=4 robustness matches T=64 within 1pp on every panel.
* **Hardware bit-flip robustness (exp 09)**: at p=0.10 cell flip rate, PBNN T=64 holds **96.73%** vs FP-NN **52.32%**. PBNN's per-cell weight equality (1/T) eliminates the MSB-dominance failure mode of digital CIM, where a single MSB flip drops FP-NN from 98.42% to **3.41%**.
* **Cross-task generalization (exp 10)**: same PBNN-MLP recipe on six UCI tabular datasets (Iris, WDBC, Yeast, Vehicle, Spambase, Satimage). PBNN matches FP-MLP exactly on WDBC (98.84%) and stays within 5pp on larger datasets — validating the architecture as a generic small-MLP replacement, not just an MNIST construction.
* **Bit-width sweep (exp 05, MNIST)**: PBNN-MLP (binary ±1) compared against FP-MLP at FP32 (98.51%), INT8 (98.33%), INT4 (98.43%), INT2 (98.21%) under matched 20-epoch QAT training. PBNN at 96.98% trails INT2 by 1.23 pp — the structural cost of binary (no zero option) vs ternary, which is small relative to the hardware-side advantages quantified in exps 09 and 13.
* **Optimizer / scheduler study (exp 11)**: 8 optimizers (SGD, Adam, AdamW, NAdam, RAdam, Adamax, RMSprop, Lion 2023) × 5 LR schedules. All adaptive optimizers cluster within 0.7pp; SGD-mom trails by 2.6pp. Best recipe: **Adam + OneCycleLR**, reaching **97.90%** test accuracy in 15 epochs.
* **Loss-landscape analysis (exp 12)**: filter-normalized 2D random-direction contours, shared-PCA per-epoch trajectories, and pairwise linear interpolation between optima — explains optimizer accuracy spread by basin geometry.
* **End-to-end training energy (exp 13, T=4, 9 architectures)**: hardware-mapped energy across **4 PBNN variants** (sMTJ, CMOS p-bit ASIC per Camsari 2020 / Borders 2019 / Sutton 2020, stoch-ReRAM, CMOS-PRNG) and **5 FP-NN variants** (STT-MRAM, ReRAM, PCRAM, FeRAM, SRAM-CIM), all with literature citations. Result spread: SRAM-CIM 6.7 J (cheapest, volatile) → PBNN sMTJ **11.9 J** → CMOS p-bit ASIC 49.5 J → stoch-ReRAM 452.8 J. PBNN sMTJ is **1.14×** the STT-MRAM training cost and **4.2× cheaper** than the published CMOS p-bit ASIC — quantifying sMTJ's intrinsic device-physics advantage over CMOS-only probabilistic computing.
* **61 unit tests** pass (49 torch-free + 12 torch-dependent).
* **Experiments 01–13**: all run end-to-end and produce figures.

Full details in [`CHANGELOG.md`](./CHANGELOG.md) and code architecture in [`docs/architecture.md`](./docs/architecture.md).

## Layered architecture

| Layer | Modules | Purpose |
|---|---|---|
| Device | `device.arrhenius`, `device.tmr`, `device.variation`, `device.calibration`, `device.llg_dynamics` | Compact `P_sw(V, t_p)` Sigmoid + Néel-Brown forms; CV(Δ) = 7.7% wafer variation; SOT-channel write-energy. |
| Array  | `array.crossbar`, `array.periphery`, `array.tile`, `array.ir_drop` | XNOR-popcount column current sum, DAC/counter, optional IR-drop. |
| Network | `nn.pbnn_linear`, `nn.pbnn_conv`, `nn.deterministic_bnn`, `nn.ste`, `nn.clt`, `nn.batchnorm`, `nn.losses` | PyTorch `nn.Module`s; STE backward; CLT-Gaussian forward shortcut; deterministic BNN baseline. |
| Sampling | `sampling.bernoulli_smtj`, `sampling.unfold`, `sampling.schedules` | Time-domain unfolding, T-step accumulator, β / T schedules. |
| PPA | `ppa.energy`, `ppa.latency`, `ppa.area`, `ppa.tech_params` | Power/performance/area; SOT write-energy from Ohmic dissipation. |
| Experiment | `train.train_loop`, `train.inference`, `train.uncertainty`, `train.compare_baseline` | End-to-end training, T-step inference, uncertainty quantification. |

## Three runtime modes

`PBNNLinear` and `PBNNConv2d` support three forward configurations:

* `software` — ideal `σ(θ)` Bernoulli sampling, no device variation. Reference for published PBNN baselines.
* `hardware_aware` — inject calibrated D2D variation via nominal-calibration write voltage; hard binary forward with smooth STE gradient through device Sigmoid. **Default training mode.**
* `full_stack` — explicit T-step Bernoulli sampling through the device + array layers; matches inference-time hardware behavior.

The same `θ` checkpoint is usable in all three modes without modification.

## Quick start

```bash
# install (editable):
pip install -e .

# Run unit tests (no torch needed for most):
pytest tests/ -v

# Reproduce  figures (no torch):
python experiments/01_device_calibration.py        # fits real Sigmoid data
python experiments/02_wafer_average_mc.py           # CV-Delta sweep
python experiments/03_nb_cross_pulse_width.py       # NB inversion
python experiments/04_ppa_breakdown.py              # energy / area

# Train MNIST PBNN-MLP (needs torch):
python experiments/05_mnist_pbnn.py
python experiments/06_sweep_T_vs_accuracy.py
python experiments/07_baseline_comparison.py
python experiments/08_nonideality_ablation.py
python experiments/09_hardware_bitflip.py
python experiments/10_uci_benchmarks.py        # needs internet on first run
python experiments/11_optimizer_scheduler_study.py
python experiments/12_loss_landscape.py
python experiments/13_training_energy.py        # analytic, no torch needed
```

## Calibration data

Real  measurements are shipped at:
```
data/smtj_psw_curves/measured_0p75ns.csv
```
46 points across (Device A, Device B) × (AP→P, P→AP) at t_w = 0.75 ns, 100 cycles per voltage, H_x = 200 Oe.

To add new measurements, see [`docs/calibration_guide.md`](./docs/calibration_guide.md).

## Physics grounding

Every default constant in the simulator traces to a specific location in . See [`docs/physics_grounding.md`](./docs/physics_grounding.md) for the audit table.

## Reproducibility

Every experiment is parameterized by a single YAML under `configs/experiment/`. The training script writes `runs/<name>/resolved.yaml` alongside the checkpoint, so any run can be rerun with `smtj-train --config runs/<name>/resolved.yaml`.

## Layout

```
smtj_pbnn_sim/
├── README.md
├── CHANGELOG.md                        (version history + project reference)
├── pyproject.toml
├── configs/{device, array, experiment} (all parameters live in YAML, not in code)
├── data/smtj_psw_curves/               (real  measurements)
├── docs/
│   ├── calibration_guide.md
│   ├── experiment_findings.md
│   └── physics_grounding.md
├── experiments/                        (01–04 no torch, 05–08 torch)
├── figures/                            (experiment outputs)
├── scripts/extract_chapter2_data.py    (data ingestion)
├── src/smtj_pbnn_sim/                  (the package)
└── tests/                              (61 unit tests)
```

## License

MIT (template; replace before publishing).
