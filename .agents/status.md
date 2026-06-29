# Project status

Developer-facing progress log for `smtj_pbnn_sim`: what is implemented and the
headline result per experiment. User-facing usage lives in the top-level
[`README.md`](../README.md); full version history is in
[`CHANGELOG.md`](../CHANGELOG.md); code architecture in
[`architecture.md`](./architecture.md).

## PBNN — memoryless p-bit use

* **Device, calibration, variation, TMR, PPA layers**: implemented and verified against the measurement data.
* **Network and training pipeline**: fully working. MNIST PBNN-MLP achieves **96.98% test accuracy** (HARDWARE_AWARE) and **97.68%** (FULL_STACK T=64) after 20 epochs. Sampling count T=8 already reaches 97.62% — the practical sweet spot for both accuracy and energy.
* **D2D variation**: properly coupled via nominal-calibration write voltage; verified by unit test and experiment 08 non-ideality ablation.
* **Multi-noise robustness (exp 07, T=4)**: 8 noise types (Gaussian, salt-pepper, speckle, blur, cutout, brightness, weight perturb, PGD-10). PBNN at T=4 (sweet spot from exp 06) wins blur, brightness shift, weight perturbation, and PGD-10 attacks; FP-NN wins additive Gaussian, salt-pepper, speckle, and cutout. T=4 robustness matches T=64 within 1pp on every panel.
* **Hardware bit-flip robustness (exp 09)**: at p=0.10 cell flip rate, PBNN T=64 holds **96.73%** vs FP-NN **52.32%**. PBNN's per-cell weight equality (1/T) eliminates the MSB-dominance failure mode of digital CIM, where a single MSB flip drops FP-NN from 98.42% to **3.41%**.
* **Cross-task generalization (exp 10)**: same PBNN-MLP recipe on six UCI tabular datasets (Iris, WDBC, Yeast, Vehicle, Spambase, Satimage). PBNN matches FP-MLP exactly on WDBC (98.84%) and stays within 5pp on larger datasets — validating the architecture as a generic small-MLP replacement, not just an MNIST construction.
* **Bit-width sweep (exp 05, MNIST)**: PBNN-MLP (binary ±1) compared against FP-MLP at FP32 (98.51%), INT8 (98.33%), INT4 (98.43%), INT2 (98.21%) under matched 20-epoch QAT training. PBNN at 96.98% trails INT2 by 1.23 pp — the structural cost of binary (no zero option) vs ternary, which is small relative to the hardware-side advantages quantified in exps 09 and 13.
* **Optimizer / scheduler study (exp 11)**: 8 optimizers (SGD, Adam, AdamW, NAdam, RAdam, Adamax, RMSprop, Lion 2023) × 5 LR schedules. All adaptive optimizers cluster within 0.7pp; SGD-mom trails by 2.6pp. Best recipe: **Adam + OneCycleLR**, reaching **97.90%** test accuracy in 15 epochs.
* **Loss-landscape analysis (exp 12)**: filter-normalized 2D random-direction contours, shared-PCA per-epoch trajectories, and pairwise linear interpolation between optima — explains optimizer accuracy spread by basin geometry.
* **End-to-end training energy (exp 13, T=4, 9 architectures)**: hardware-mapped energy across **4 PBNN variants** (sMTJ, CMOS p-bit ASIC per Camsari 2020 / Borders 2019 / Sutton 2020, stoch-ReRAM, CMOS-PRNG) and **5 FP-NN variants** (STT-MRAM, ReRAM, PCRAM, FeRAM, SRAM-CIM), all with literature citations. Result spread: SRAM-CIM 6.7 J (cheapest, volatile) → PBNN sMTJ **11.9 J** → CMOS p-bit ASIC 49.5 J → stoch-ReRAM 452.8 J. PBNN sMTJ is **1.14×** the STT-MRAM training cost and **4.2× cheaper** than the published CMOS p-bit ASIC — quantifying sMTJ's intrinsic device-physics advantage over CMOS-only probabilistic computing.

## Reservoir computing — stateful telegraph use (v0.3.0)

Reuses the *same* calibrated sMTJ as a stateful random-telegraph node instead of
a memoryless p-bit: its voltage-tunable relaxation time provides fading memory
and its `tanh` switching provides nonlinearity, so only a linear readout is trained.

* **Stateful device physics (`device/telegraph.py`)**: two-state continuous-time Markov model with the exact propagator (any `dt`); closed forms `stationary_mean(V) = tanh(ΔV/V_c0)` (nonlinearity) and `relaxation_time(V) = 1/(r↑+r↓)` (fading memory, ~68 ns at zero bias for the Chapter 2.3 device). Plus `device.arrhenius.neel_brown_rate` exposing the continuous-time hazard rate. NumPy-only; not in the PBNN forward path.
* **Reservoir layer (`reservoir/`)**: `SMTJReservoir` — fixed random pool of telegraph nodes with input injection, optional spectral-radius-scaled recurrence, per-node Δ heterogeneity, ensemble averaging (devices/node), and a noise-free `meanfield` mode (RC analogue of PBNN `software`). Closed-form ridge `readout.py` (the only trained part); `tasks.py` (NARMA-10, memory-capacity, product-memory, sine/square); `metrics.py` (NRMSE, linear memory capacity, Jaeger 2001).
* **Prototype & computability (exp 14)**: mean-field memory capacity ≈ 6.6, NARMA-10 NRMSE ≈ 0.61; real device (ensemble = 96) MC ≈ 2.0, NRMSE ≈ 0.81 — surfaces the readout shot-noise limit.
* **Device-optimization guidance (exp 15)**: optimal barrier tracks the task timescale, τ\* ≈ 2.3·dt; the RC optimum **Δ ≈ 3.5–4.3 sits below the PBNN write device's Δ = 4.91** (RC wants a more superparamagnetic, lower-barrier device); the memory/nonlinearity trade-off is set by operating-point bias.
* **Hardware PPA (exp 16)**: sMTJ-RC replaces the digital ESN's O(N²) recurrent matmul with O(N × ensemble) analog physics — **~30× lower energy** (per-node 8-bit; ~35× with a column-shared SAR) than a conventional digital ESN once the physical sky130 ADC is billed, though an idealized ADC-free CIM ESN remains a cheaper floor (honest bracket).
* **Variation tolerance & noise (exp 17)**: D2D Δ heterogeneity, harmful to PBNN, instead *raises* node diversity and benefits RC; the real limit is readout signal-to-noise.
* **Benchmark breadth (exp 18)**: Mackey-Glass chaotic single-step prediction and information-processing-capacity (IPC) decomposition by polynomial degree.
* **Temperature as a τ knob (exp 19)**: zero-bias τ is strongly Arrhenius in temperature; a thermal-clock recipe (system clock following τ(T)) keeps memory capacity near-constant across a wide temperature range, and lets a target operating temperature constrain the barrier to fabricate.

## EDA co-design grounding & robustness (v0.4.0)

Grounds the CMOS-peripheral PPA inputs in an open-source sky130 (130 nm/1.8 V) flow and adds a seed-independence study; device physics and the PBNN/RC math are unchanged.

* **Readout (sky130 StrongARM SA)**: input-referred offset σ ≈ 0.39·V_T (120-sample MC), decision energy ≈ 48 fJ — replaces the 5 fJ placeholder (errata R1). A slope-matched TIA maps the offset to ~2.5 popcount, so a plain comparator is Pareto-optimal at MNIST fan-in (auto-zero only for low-V_in / wide-fan-in columns).
* **Write path**: voltage-mode resistor-string write-DAC (adopted after a binary-weighted current-steering first cut failed monotonicity at INL ~1.7 LSB), IR-aware per-row pre-distortion, and write-line IR extracted via Magic extresist (N=256 round-trip ~16.5% of R_SOT).
* **PPA grounded in sky130**: energies — `e_smtj_read` 48 fJ, `e_dac_step` ~34 fJ, `e_count_inc` ~19 fJ (`dac_counter_energy.py`); per-MAC peripheral share ~1% → ~11%, write still ~89%. Areas — first-order from real `sky130_fd_sc_hd` cell areas + design rules (`area_estimate.py`): 2T cell ~4.6 µm² (write FET for 1.16 mA dominates), DAC ~800, counter ~630 µm² (256×256 tile ~0.67 mm², periphery comparable to array). DRC-clean GDS extraction is the remaining refinement (`.agents/eda/PPA_grounding_plan.md`).
* **Seed-independence (exp 21)**: the four headline results are robust across 8 seeds — PBNN MNIST 97.01%±0.17, T64−T4 gap 0.21±0.11 pp, RC memory capacity 2.11±0.22, RC energy advantage 30.2×, device β_s 9.51±0.01 (Appendix C).
* **CNN extension (exp 05a)**: PBNN-CNN on Fashion-MNIST (88.1%) and CIFAR-10 (67.2%); the binary-capacity cost grows with task difficulty (Appendix B).

## Tests & experiments

* **111 unit tests** pass (61 before the RC extension; added telegraph, reservoir, RC-energy, CNN-extension, and PPA-grounding cases).
* **Experiments 01–13** (PBNN), **14–19** (reservoir computing), **20** (write-line IR-drop) and **21** (seed-independence) all run end-to-end and produce figures; 01–04, 13 and 16 are torch-free.
