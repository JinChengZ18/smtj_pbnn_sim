# `smtj_pbnn_sim`

PyTorch-based hardware simulator for **stochastic SOT-MTJ-based
probabilistic binary neural networks (PBNN)**, grounded on the
Chapter 2.3 joint write-probability model.

## Status

* **Device, calibration, variation, TMR, PPA layers**: implemented and
  verified against the Chapter 2.3 measurement data — 49 unit tests
  pass without PyTorch.
* **Network and sampling layers**: implemented; tests defined; not yet
  executed in this environment due to lack of installable CPU PyTorch
  in the build sandbox.
* **Experiments 01–04**: runnable without PyTorch; reproduce key
  Chapter 2.3 figures (per-(device, direction) Sigmoid fits, wafer-average
  Monte Carlo, NB cross-pulse-width inversion, PPA breakdown).
* **Experiments 05–07** (MNIST training, T-vs-accuracy, variation
  robustness): coded; require local PyTorch.

For the next agent, start with [`LOCAL_AGENT_BRIEF.md`](./LOCAL_AGENT_BRIEF.md);
full details are in [`HANDOFF.md`](./HANDOFF.md), code architecture in
[`docs/architecture.md`](./docs/architecture.md), and version history
in [`CHANGELOG.md`](./CHANGELOG.md).

## Layered architecture

| Layer | Modules | Purpose |
|---|---|---|
| Device | `device.arrhenius`, `device.tmr`, `device.variation`, `device.calibration`, `device.llg_dynamics` | Compact `P_sw(V, t_p)` Sigmoid + Néel-Brown forms; CV(Δ) = 7.7% wafer variation; SOT-channel write-energy. |
| Array  | `array.crossbar`, `array.periphery`, `array.tile`, `array.ir_drop` | XNOR-popcount column current sum, DAC/counter, optional IR-drop. |
| Network | `nn.pbnn_linear`, `nn.pbnn_conv`, `nn.ste`, `nn.clt`, `nn.batchnorm`, `nn.losses` | PyTorch `nn.Module`s; STE backward; CLT-Gaussian forward shortcut. |
| Sampling | `sampling.bernoulli_smtj`, `sampling.unfold`, `sampling.schedules` | Time-domain unfolding, T-step accumulator, β / T schedules. |
| PPA | `ppa.energy`, `ppa.latency`, `ppa.area`, `ppa.tech_params` | Power/performance/area; SOT write-energy from Ohmic dissipation. |
| Experiment | `train.train_loop`, `train.inference`, `train.uncertainty`, `train.compare_baseline` | End-to-end training, T-step inference, uncertainty quantification. |

## Three runtime modes

`PBNNLinear` and `PBNNConv2d` support three forward configurations:

* `software` — ideal `σ(θ)` Bernoulli sampling, no device variation.
  Reference for published PBNN baselines.
* `hardware_aware` — inject calibrated D2D variation; CLT-Gaussian
  forward for differentiable training. **Default training mode.**
* `full_stack` — explicit T-step Bernoulli sampling through the
  device + array layers; matches inference-time hardware behavior.

The same `θ` checkpoint is usable in all three modes without modification.

## Quick start

```bash
# install (editable):
pip install -e .

# Run unit tests (no torch needed for most):
pytest tests/ -v

# Reproduce Chapter 2.3 figures (no torch):
python experiments/01_device_calibration.py        # fits real Sigmoid data
python experiments/02_wafer_average_mc.py           # CV-Delta sweep
python experiments/03_nb_cross_pulse_width.py       # NB inversion
python experiments/04_ppa_breakdown.py              # energy / area

# Train MNIST PBNN-MLP (needs torch):
python experiments/05_mnist_pbnn.py
python experiments/06_sweep_T_vs_accuracy.py
python experiments/07_variation_sweep.py
```

## Calibration data

Real Chapter 2.3 measurements are shipped at:
```
data/smtj_psw_curves/measured_0p75ns.csv
```
46 points across (Device A, Device B) × (AP→P, P→AP) at t_w = 0.75 ns,
100 cycles per voltage, H_x = 200 Oe.

To add new measurements, see [`docs/calibration_guide.md`](./docs/calibration_guide.md).

## Physics grounding

Every default constant in the simulator traces to a specific location
in Chapter 2.3. See [`docs/physics_grounding.md`](./docs/physics_grounding.md) for
the audit table.

## Reproducibility

Every experiment is parameterized by a single YAML under
`configs/experiment/`. The training script writes
`runs/<name>/resolved.yaml` alongside the checkpoint, so any run can be
rerun with `smtj-train --config runs/<name>/resolved.yaml`.

## Layout

```
smtj_pbnn_sim/
├── README.md
├── HANDOFF.md                          (read this first if continuing the work)
├── pyproject.toml
├── configs/{device, array, experiment} (all parameters live in YAML, not in code)
├── data/smtj_psw_curves/               (real Chapter 2.3 measurements)
├── docs/
│   ├── calibration_guide.md
│   └── physics_grounding.md
├── experiments/                        (01–04 no torch, 05–07 torch)
├── figures/                            (experiment outputs)
├── scripts/extract_chapter2_data.py    (data ingestion)
├── src/smtj_pbnn_sim/                  (the package)
└── tests/                              (32 + 6 unit tests)
```

## License

MIT (template; replace before publishing).
