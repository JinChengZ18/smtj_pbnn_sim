# Architecture

This document describes the simulator's dependency graph, data flow, and call chains. It complements the layered-architecture summary in `README.md` with concrete code references.

## 1. Dependency graph

Modules respect strict layering. Higher layers import from lower layers, never the reverse.

```
                        ┌─────────────────────────────┐
   experiments/         │ experiments/0*.py            │
                        │ src/.../scripts/_*_train.py  │
                        └─────────────┬───────────────┘
                                      │
                ┌─────────────────────┴──────────────────────┐
                ▼                     ▼                      ▼
       ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
       │ train/         │    │ ppa/           │    │ data/          │
       │ ─────          │    │ ─────          │    │ ─────          │
       │ train_loop     │    │ tech_params    │    │ mnist          │
       │ inference      │    │ energy/lat/    │    │                │
       │ uncertainty    │    │ area           │    │                │
       │ compare_       │    │                │    │                │
       │   baseline     │    │                │    │                │
       └────────┬───────┘    └────────────────┘    └────────────────┘
                │  (no peer dependencies among the three)
                ▼
       ┌────────────────────────────────────────────┐
       │ nn/                                         │
       │ ─────                                       │
       │ pbnn_linear, pbnn_conv  ◄── ste, clt        │
       │ batchnorm, losses                           │
       └────────────────┬───────────────────────────┘
                        │
                        ▼
       ┌────────────────────────────────────────────┐
       │ array/  (only used in FULL_STACK mode)      │
       │ ─────                                       │
       │ tile  ◄─── crossbar, periphery, ir_drop     │
       └────────────────┬───────────────────────────┘
                        │
                        ▼
       ┌────────────────────────────────────────────┐
       │ device/                                     │
       │ ─────                                       │
       │ arrhenius (compact models, NB rate)         │
       │ tmr (resistance / SOT energy)               │
       │ variation (D2D sampling, NB or direct mode) │
       │ calibration (fits real data → YAML)         │
       │ llg_dynamics (reference only, not runtime)  │
       │ telegraph (stateful two-state RTN, RC node) │
       └────────────────────────────────────────────┘

       ┌────────────────────────────────────────────┐
       │ sampling/  (cross-cutting; used by nn/, array/)
       │ ─────                                       │
       │ bernoulli_smtj, unfold, schedules           │
       └────────────────────────────────────────────┘

       ┌────────────────────────────────────────────┐
       │ reservoir/  (parallel pipeline for RC)      │
       │ ─────                                       │
       │ node (SMTJReservoir, uses device.telegraph) │
       │ readout (closed-form ridge regression)      │
       │ tasks (NARMA-10, MC, Mackey-Glass, ...)     │
       │ metrics (NRMSE, linear memory capacity)     │
       └────────────────────────────────────────────┘

       ┌────────────────────────────────────────────┐
       │ utils/  (used everywhere)                   │
       │ ─────                                       │
       │ seeding, io, logging                        │
       └────────────────────────────────────────────┘
```

The forbidden direction `device → nn` is enforced by convention; if broken, the device layer becomes useless for offline calibration scripts that don't have `nn/` set up (e.g., the chapter-2 verification plots).

Reservoir computing (v0.3.0) is a sibling pipeline that *reuses* the same calibrated device but bypasses `nn/` and `array/` entirely: `experiments/14–19` → `reservoir/` → `device.telegraph` (which itself sits on `device.arrhenius`). Energy accounting for this pipeline lives in `ppa.reservoir_energy`. There is no autograd loop on the reservoir side — only the linear readout is trained, in closed form.

## 2. Three forward modes — call chain

Every `PBNNLinear.forward(x, mode=...)` call routes differently:

### `ForwardMode.SOFTWARE`
```
PBNNLinear.forward(x, mode=SOFTWARE)
  └─ p = sigmoid(theta)                       (no device, no variation)
  └─ z = bernoulli_pm1_clt_forward(p, x)
        └─ mu = (2p - 1) @ x.T                (analytic mean)
        └─ sigma2 = 4 p (1 - p) @ x.T**2      (analytic variance)
        └─ z = mu + sigma * randn             (reparam sample)
  └─ z = z + bias
  └─ z = sign_ste(z)                          (if binarize_output)
```

### `ForwardMode.HARDWARE_AWARE` (default during training)
```
PBNNLinear.forward(x, mode=HARDWARE_AWARE)
  └─ _ensure_variation(device)
        └─ VariationSampler.sample(...)
              └─ if mode='delta': sample Delta_i, propagate via NB
              └─ if mode='sigmoid_direct': sample (V_th, V_T) directly
              └─ result stored in V_th_field, V_T_field buffers
  └─ V_wr = V_th_field + V_T_field * theta    (per-cell write voltage)
  └─ p = psw_sigmoid(V_wr, V_th_field, V_T_field)  (device Sigmoid)
  └─ z = bernoulli_pm1_clt_forward(p, x)      (CLT-Gaussian sample)
  └─ z = z + bias
  └─ z = sign_ste(z)
```

### `ForwardMode.FULL_STACK` (eval / PPA only)
```
PBNNLinear.forward(x, mode=FULL_STACK, T=T)
  └─ _ensure_variation(device)
  └─ p = device Sigmoid (same as HARDWARE_AWARE)
  └─ with torch.no_grad():            # ← gradients DON'T flow
        for t in 1..T:
          w_t = bernoulli_from_theta(p)        (explicit ±1 sample)
          z_t = F.linear(x, w_t)
          z = z + z_t
        z = z / T
  └─ z = z + bias
  └─ z = sign_ste(z)                  # STE still applied (safe in no_grad)
```

The `θ` parameter is shared across all three modes; no separate software/hardware checkpoints are needed.

## 3. Data flow at training time

```
   Chapter-2.3 CSV  ─→  experiments/01_device_calibration.py
                          ─→ fit_per_device_direction() / fit_sigmoid_params()
                          ─→ write_device_yaml()
                              configs/device/sot_smtj_devA_pAP_0p75ns.yaml
                                 ↓
   configs/experiment/mnist_lenet.yaml  (references device YAML)
                                 ↓
                         smtj-train CLI
                          ─→ scripts/_mnist_train.run()
                              ─→ DeviceLayerParams from YAML
                              ─→ VariationConfig from YAML
                              ─→ PBNN_MLP construction
                                  ─→ PBNNLinear._ensure_variation
                                      ─→ VariationSampler.sample
                                  ─→ training loop
                                      ─→ HARDWARE_AWARE forward
                                      ─→ binary_cross_entropy_loss
                                      ─→ optimizer.step()
                              ─→ runs/mnist_pbnn_mlp/best.pt
                                       runs/mnist_pbnn_mlp/resolved.yaml
```

## 4. Data flow at evaluation time (PPA-grade)

```
   runs/mnist_pbnn_mlp/best.pt
                  ↓
       experiments/06_sweep_T_vs_accuracy.py
                  ↓
       evaluate(model, mode=FULL_STACK, T=T)
            ↓ explicit T-step Bernoulli sampling
                  ↓
       layer_inference_energy(rows, cols, T, tech)
            (counts MAC operations × per-MAC energy from tech_params)
                  ↓
       figures/06_sweep_T.png  (accuracy ↔ energy)
```

## 5. Backend dispatch

Some modules support both NumPy and Torch backends; they detect the input type at runtime via `type(x).__module__.startswith("torch")`:

| Module | NumPy | Torch | Notes |
|---|:-:|:-:|---|
| `device.arrhenius` | ✓ | ✓ | duck-typed exp / expm1 / sigmoid |
| `device.tmr` | ✓ | ✓ | linear combination, no special ops |
| `device.variation` | ✓ | ✓ | NumPy primary; converts to torch when `device=` is passed |
| `device.calibration` | ✓ | — | NumPy/SciPy only; no torch |
| `array.periphery` | ✓ | ✓ | duck-typed clamp / round |
| `array.ir_drop` | ✓ | — | scalar arithmetic |
| `array.crossbar` | — | ✓ | `F.linear` requires torch |
| `array.tile` | — | ✓ | uses crossbar |
| `nn.*` | — | ✓ | autograd requires torch |
| `sampling.bernoulli_smtj` | — | ✓ | autograd-aware torch generator |
| `sampling.unfold` | — | ✓ | accepts callable returning tensor |
| `sampling.schedules` | ✓ | — | scalar / list arithmetic |
| `ppa.*` | ✓ | — | scalar arithmetic |
| `device.telegraph` | ✓ | — | NumPy two-state CTMC, no autograd |
| `reservoir.*` | ✓ | — | NumPy node pool + closed-form ridge readout |

This split lets calibration scripts and unit tests run in a torch-free environment while runtime code (training / eval) uses torch.

## 6. Key design choices

* **Variation field is per-weight, not per-cell.** A single PBNNLinear weight is treated as one cell; tile-based mapping (e.g., one weight = 4 cells with 1 Bernoulli vote each) requires overriding `_ensure_variation`.

* **CLT shortcut over T-step sampling at training time.** We never unroll the time-domain T loop in the autograd graph; the reparameterized Gaussian gives the same expectation gradient with zero variance, at one MAC per layer instead of T MACs.

* **STE sign at output, not at input.** Each PBNN layer binarizes its *own* output. Activations are already binary by the time they reach the next layer's input.

* **YAML over command-line flags.** Experiments are reproducible via a single config file. Hardcoded constants are explicitly disallowed in the source (every `DeviceLayerParams` has a default that mirrors the chapter primary reference, but production scripts always overwrite from YAML).

* **`runs/<name>/resolved.yaml` written alongside checkpoints.** The effective config (after CLI overrides, defaults, and computed values like `R_AP = R_P * (1 + TMR)`) is dumped. Reproducing a run is `smtj-train --config runs/<name>/resolved.yaml`.
