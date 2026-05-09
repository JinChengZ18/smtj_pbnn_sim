# Local Agent Brief

You're picking up `smtj_pbnn_sim` from a cloud-side agent that couldn't
install PyTorch. This brief is the 5-minute orientation; for full
context read [`HANDOFF.md`](./HANDOFF.md) and
[`docs/physics_grounding.md`](./docs/physics_grounding.md).

## What you're inheriting

A working sMTJ-PBNN simulator with:

* Real Chapter 2.3 measurement data (46 points, 4 device/direction
  combinations) at `data/smtj_psw_curves/measured_0p75ns.csv`.
* Device, calibration, variation, TMR, PPA layers fully tested
  (49 unit tests pass without torch).
* Network and sampling layers (PBNNLinear, PBNNConv2d, STE, CLT,
  Bernoulli sampler, T-step unfold) coded and reviewed but unrun.
* Three end-to-end experiment scripts (MNIST training, T-vs-accuracy,
  variation sweep) wired up.
* All physics constants traceable to specific Chapter 2.3 locations.

## What was verified in the cloud sandbox

| Check | Result |
|---|---|
| Calibration on real CSV | V_th = 895.8 mV vs chapter 894 mV; β_s = 42.7 vs chapter 44.6; R² = 0.992 vs chapter 0.993 |
| NB analytic slope formula | β_NB = 7.94 V⁻¹ exactly matches Table 2.3-9 |
| NB cross-pulse-width inversion | Δ = 5.19 vs chapter 5.15; V_c0 = 882 mV vs chapter 884 mV |
| Wafer-mean β_s at CV(Δ) = 7.7 % | 42.37 V⁻¹ vs chapter joint prediction 42.3 V⁻¹ |
| SOT write energy | 0.78 pJ at 0.9 V / 0.75 ns / 776 Ω, exactly chapter |
| 49 unit tests | All pass |

## What you need to do

### Step 1 — install torch and re-test (5 minutes)

```bash
cd smtj_pbnn_sim
pip install -e .
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

pytest tests/ -v
# Expected: ~55 passed, 0 skipped
# (49 we already verified + ~6 from tests/test_torch_nn.py)
```

If `test_torch_nn.py` fails, the failure is in the network layer; fix
before proceeding. The most likely failure modes are listed in
HANDOFF.md §5.

### Step 2 — sanity-run existing experiments (10 minutes)

```bash
# These four already passed in the cloud (no torch needed) — re-running
# locally just confirms identical figures:
python experiments/01_device_calibration.py
python experiments/02_wafer_average_mc.py
python experiments/03_nb_cross_pulse_width.py
python experiments/04_ppa_breakdown.py
```

Compare the resulting `figures/01_*.png` ... `figures/04_*.png` to the
cloud-generated ones (shipped in the package). They should be
bit-identical except for matplotlib backend differences.

### Step 3 — first MNIST run (30 minutes on CPU, 5 min on GPU)

```bash
python experiments/05_mnist_pbnn.py
```

Expected outcome:

* `runs/mnist_pbnn_mlp/best.pt` written
* `runs/mnist_pbnn_mlp/resolved.yaml` written
* test accuracy >97 % after 5 epochs of a 1024-hidden 3-layer
  PBNN-MLP in `hardware_aware` mode

If accuracy stalls below 90 %, inspect:
1. is `θ` actually getting gradients? Check
   `model.fc1.theta.grad.abs().max()` after one backward call.
2. is BN running stats divergent? Try `model.eval()` between epochs.
3. did the variation sampler produce sane (V_th, V_T) fields? Print
   `model.fc1.V_th_field.mean().item()` — should be near 0.843 V (the
   NB-derived V_th at t_w = 0.75 ns, which is the ``mode='delta'``
   center, not 0.894 V which is the operating-point measurement).
   The discrepancy between 843 and 894 mV is intentional: the chapter
   reference is the measured Sigmoid center, while our delta-mode
   variation sampler propagates Δ through the NB closed form which
   centers at 843 mV. Section 4 below gives the option to switch to
   the measured 894 mV center.

### Step 4 — system-level experiments (1–2 hours)

```bash
python experiments/06_sweep_T_vs_accuracy.py     # ~15 min
python experiments/07_variation_sweep.py         # ~15 min
```

These reload the checkpoint from step 3 and produce two more figures.

### Step 5 — extension work

The next chunks of work, in priority order:

1. **CIFAR-10 PBNN-CNN.** Use `PBNNConv2d` from
   `smtj_pbnn_sim.nn.pbnn_conv`. Add
   `src/smtj_pbnn_sim/scripts/_cifar_train.py` patterned on
   `_mnist_train.py`, then add `experiments/08_cifar_pbnn.py`.
2. **Baseline comparison.** Populate `configs/baseline/{stt_bnn,
   sot_bnn, aihwkit}.yaml` from published numbers; write
   `experiments/09_compare_baseline.py`. The `BaselineResult`
   schema is at `train.compare_baseline`.
3. **Chapter 5 figures.** Once 06/07/08/09 are reproducible, lift the
   key plots into the thesis chapter.

## A few specific things to watch

### The 843 vs 894 mV question

In `mode='delta'` the per-cell V_th is computed from the NB closed form
$V_{th}(t_p) = V_{c0}(1 - \ln(t_p/\tau_0/\ln 2)/\Delta)$. With chapter
parameters Δ = 4.91, V_c0 = 0.857 V, this gives 843.2 mV at
t_p = 0.75 ns — which is **NOT** the measured Sigmoid center (894 mV).
The ~50 mV offset is the well-known NB-vs-measurement mismatch
(Chapter 2.3 §2.3.5), and `eta_c = 5.34` corrects the slope, not the
center.

If you want the network to use the measured 894 mV as the center, set
`mode='sigmoid_direct'` in your variation YAML and supply
`sigma_V_th_rel`. This trades physical NB→Sigmoid coupling for direct
operating-point statistics.

### Gradient flow caveats

* `FULL_STACK` mode is wrapped in `torch.no_grad()`. Don't use it during
  training.
* The STE sign at the end of every PBNNLinear/PBNNConv2d layer is
  applied **after** the bias add. If your output layer should not
  binarize (typical for the classifier), construct it with
  `binarize_output=False`. The MNIST template does this correctly.

### Disk discipline

A full MNIST training writes ~50 MB to `runs/mnist_pbnn_mlp/`. If you
plan to do a CV(Δ) sweep with N=10 checkpoints, that's 500 MB. Add the
`runs/` directory to `.gitignore` (already done) and clean periodically.

## Files you'll touch most

| File | Purpose |
|---|---|
| `configs/experiment/*.yaml` | per-experiment hyperparameters |
| `src/smtj_pbnn_sim/scripts/_*_train.py` | per-dataset training entry |
| `src/smtj_pbnn_sim/nn/pbnn_linear.py` | core PBNN layer |
| `experiments/0*.py` | runnable experiment scripts |

## Files you should NOT touch unless you know why

| File | Why |
|---|---|
| `device/arrhenius.py` | locked to Chapter 2.3 closed forms; verified analytically |
| `device/calibration.py` | locked to fitting routines verified against real data |
| `data/smtj_psw_curves/measured_0p75ns.csv` | source of truth |
| `tests/test_arrhenius.py`, `tests/test_calibration.py`, `tests/test_variation.py`, `tests/test_tmr.py`, `tests/test_ppa.py` | regression hard-rails for the chapter physics |

## Quick reference

* Status overview: [`README.md`](./README.md)
* Full handoff: [`HANDOFF.md`](./HANDOFF.md)
* Chapter constants table: [`docs/physics_grounding.md`](./docs/physics_grounding.md)
* Adding measurements: [`docs/calibration_guide.md`](./docs/calibration_guide.md)
* Architecture: see `README.md` "Layered architecture" section

If anything in the docs contradicts the code, the code wins — but flag
the discrepancy back to the chapter author and update the docs.
