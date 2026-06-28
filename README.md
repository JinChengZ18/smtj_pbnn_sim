# `smtj_pbnn_sim`

PyTorch-based hardware simulator for **stochastic SOT-MTJ probabilistic computing**. The same calibrated sMTJ device is used two ways: as a **memoryless Bernoulli p-bit** for **probabilistic binary neural networks (PBNN)**, and as a **stateful random-telegraph node** for **reservoir computing (RC)** — a temporal-processing extension that exploits the device's voltage-tunable relaxation time as fading memory.

> **Project status and per-experiment results**: [`.agents/status.md`](./.agents/status.md). Full version history: [`CHANGELOG.md`](./CHANGELOG.md). Code architecture: [`docs/architecture.md`](./docs/architecture.md).

## Layered architecture

| Layer | Modules | Purpose |
|---|---|---|
| Device | `device.arrhenius`, `device.tmr`, `device.variation`, `device.calibration`, `device.llg_dynamics`, `device.telegraph` | Compact `P_sw(V, t_p)` Sigmoid + Néel-Brown forms; CV(Δ) = 7.7% wafer variation; SOT-channel write-energy; stateful two-state telegraph model (RC). |
| Array  | `array.crossbar`, `array.periphery`, `array.tile`, `array.ir_drop` | XNOR-popcount column current sum, DAC/counter, optional IR-drop. |
| Network | `nn.pbnn_linear`, `nn.pbnn_conv`, `nn.deterministic_bnn`, `nn.ste`, `nn.clt`, `nn.batchnorm`, `nn.losses` | PyTorch `nn.Module`s; STE backward; CLT-Gaussian forward shortcut; deterministic BNN baseline. |
| Sampling | `sampling.bernoulli_smtj`, `sampling.unfold`, `sampling.schedules` | Time-domain unfolding, T-step accumulator, β / T schedules. |
| Reservoir | `reservoir.node`, `reservoir.readout`, `reservoir.tasks`, `reservoir.metrics` | Fixed random telegraph-node pool, trained ridge readout, temporal tasks (NARMA-10, memory capacity, Mackey-Glass), NRMSE / memory-capacity metrics. |
| PPA | `ppa.energy`, `ppa.latency`, `ppa.area`, `ppa.tech_params`, `ppa.reservoir_energy` | Power/performance/area; SOT write-energy from Ohmic dissipation; sMTJ-RC vs digital-ESN energy. |
| Experiment | `train.train_loop`, `train.inference`, `train.uncertainty`, `train.compare_baseline` | End-to-end training, T-step inference, uncertainty quantification. |

## Two ways to use the device

### Memoryless p-bit (PBNN)

`PBNNLinear` and `PBNNConv2d` support three forward configurations:

* `software` — ideal `σ(θ)` Bernoulli sampling, no device variation. Reference for published PBNN baselines.
* `hardware_aware` — inject calibrated D2D variation via nominal-calibration write voltage; hard binary forward with smooth STE gradient through device Sigmoid. **Default training mode.**
* `full_stack` — explicit T-step Bernoulli sampling through the device + array layers; matches inference-time hardware behavior.

The same `θ` checkpoint is usable in all three modes without modification.

### Stateful node (reservoir computing)

`SMTJReservoir` (in `reservoir.node`) leaves the *same* device free to evolve instead of resetting it each step, turning it into a random-telegraph dynamical node. The voltage-tunable relaxation time `τ(V) = 1/(r↑+r↓)` supplies fading memory and the `tanh(ΔV/V_c0)` transfer supplies nonlinearity, so only a linear ridge readout is trained — no recurrent weight matrix is stored or learned. A noise-free `meanfield` mode mirrors PBNN's `software` mode. RC favours a lower-barrier (more superparamagnetic) device than PBNN; the device-optimization guidance is summarized in [`.agents/status.md`](./.agents/status.md).

## Quick start

```bash
# install (editable):
pip install -e .

# Run unit tests (no torch needed for most):
pytest tests/ -v

# Reproduce device figures (no torch):
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

# Reservoir computing (reuses the same device as a stateful node):
python experiments/14_rc_prototype.py            # viability: memory capacity, NARMA-10
python experiments/15_rc_device_optimization.py  # barrier / timescale matching guidance
python experiments/16_rc_hardware_ppa.py         # sMTJ-RC vs digital ESN energy
python experiments/17_rc_robustness.py           # D2D variation + read-noise limits
python experiments/18_rc_benchmarks.py           # Mackey-Glass + memory/nonlinear capacity (summed-r^2 proxy)
python experiments/19_rc_temperature.py          # temperature as a tau knob
python experiments/20_write_ir_drop.py           # write-line IR drop + IR-aware pre-distortion

# Principle demos (figures):
python demo/05_reservoir_computing_principle.py
```

## Calibration data

Real device measurements are shipped at:
```
data/smtj_psw_curves/measured_0p75ns.csv
```
46 points across (Device A, Device B) × (AP→P, P→AP) at t_w = 0.75 ns, 100 cycles per voltage, H_x = 200 Oe.

To add new measurements, see [`docs/calibration_guide.md`](./docs/calibration_guide.md).

## Physics grounding

Every default constant in the simulator traces to a specific, documented physical source. See [`docs/physics_grounding.md`](./docs/physics_grounding.md) for the audit table.

## Reproducibility

Every experiment is parameterized by a single YAML under `configs/experiment/`. The training script writes `runs/<name>/resolved.yaml` alongside the checkpoint, so any run can be rerun with `smtj-train --config runs/<name>/resolved.yaml`.

## Layout

```
smtj_pbnn_sim/
├── README.md
├── CHANGELOG.md                        (version history + project reference)
├── pyproject.toml
├── configs/{device, array, experiment} (all parameters live in YAML, not in code)
├── data/smtj_psw_curves/               (real device measurements)
├── docs/                               (user-facing: how to understand / reproduce)
│   ├── architecture.md
│   ├── calibration_guide.md
│   ├── experiment_findings.md          (expected per-experiment results)
│   └── physics_grounding.md
├── .agents/                            (internal: project status, errata ledger, EDA plans)
├── demo/                               (principle-figure scripts, incl. 05 reservoir computing)
├── experiments/                        (01–13 PBNN, 14–19 reservoir computing, 20 write IR-drop)
├── figures/                            (experiment outputs)
├── scripts/extract_chapter2_data.py    (data ingestion)
├── src/smtj_pbnn_sim/                  (device · array · nn · sampling · reservoir · ppa · train)
└── tests/                              (95 unit tests)
```

## License

MIT.
