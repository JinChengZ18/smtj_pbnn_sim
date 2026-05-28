# Calibration guide

How to fit P_sw(V) measurements into a device YAML that the simulator can consume.

## Input format

Place your CSV under `data/smtj_psw_curves/`. Required columns:

| Column | Unit | Notes |
|---|---|---|
| `V` | volts | write voltage (signed or absolute, but consistent within a curve) |
| `t_p` | seconds | pulse width |
| `P_sw` | dimensionless | switching probability in [0, 1] |

Optional but recommended columns:

| Column | Notes |
|---|---|
| `device_id` | string identifier; enables per-device fits |
| `direction` | e.g. "AP->P" / "P->AP"; enables per-direction fits |
| `n_reps` | number of single-shot experiments per row |

The reference CSV `measured_0p75ns.csv` has all six columns and 46 rows; follow that schema.

## Operating-point Sigmoid fit

```python
import pandas as pd
from smtj_pbnn_sim.device.calibration import (
    fit_sigmoid_params, fit_per_device_direction, write_device_yaml,
)

df = pd.read_csv("data/smtj_psw_curves/your_data.csv")

# All groups at once:
print(fit_per_device_direction(df))

# Pick one group as primary (e.g., the cleanest curve):
sub = df[(df.device_id == "A") & (df.direction == "P->AP")]
sp = fit_sigmoid_params(sub)
print(f"V_th = {sp.V_th*1000:.1f} mV  beta_s = {sp.beta_s:.1f} V^-1  R^2 = {sp.r2:.3f}")

# Write the device YAML:
write_device_yaml(
    sigmoid=sp,
    out_path="configs/device/your_device.yaml",
    eta_c=5.34,
    R_P=4.9e3, TMR=1.0, R_SOT=776.0,
)
```

## Cross-pulse-width Néel-Brown fit

If you have V_th measured at multiple t_p values (extracted from hysteresis sweeps), fit (Δ, V_c0):

```python
from smtj_pbnn_sim.device.calibration import fit_neel_brown_from_vth_vs_tw

vth_table = pd.DataFrame({
    "t_p":  [0.75e-9, 1.0e-9, 2.0e-9, 5.0e-9],
    "V_th": [0.869,   0.820,  0.702,  0.546],   # AP->P, Device A
})
nb = fit_neel_brown_from_vth_vs_tw(vth_table, tau_0=1e-9)
print(f"Delta = {nb.Delta:.2f}  V_c0 = {nb.V_c0*1000:.0f} mV  R^2 = {nb.r2:.4f}")
```

The recovered (Δ, V_c0) feed the variation sampler in `mode="delta"`.

## Computing η_c

η_c is the empirical narrowing factor relating the analytic NB slope to the measured Sigmoid slope:

    eta_c = beta_s_measured / beta_NB_analytic

with `beta_NB_analytic = 2 * ln(2) * Delta / V_c0`. For the chapter primary reference: 44.6 / 7.94 ≈ 5.62 (chapter reports 5.34 from MC fitting; the 5% difference is due to logistic-vs-Gumbel curvature discussed in Chapter 2.3 §2.3.5 and §2.3.6).

## Deploying the YAML

In `configs/experiment/<your_exp>.yaml`:

```yaml
device:
  operating_point:
    V_th_nom: 0.894
    V_T_nom:  0.022422
    t_p:      0.75e-9
  neel_brown:
    Delta_nom: 4.91
    V_c0_nom:  0.857
    tau_0:     1.0e-9
  eta_c: 5.34
  resistance:
    R_P_nom: 4.9e3
    TMR_nom: 1.0
    R_SOT:   776.0

variation:
  enabled: true
  mode: delta
  cv_delta: 0.077
  seed: 42
```

The training script will pick all of these up automatically.

## Verifying

After running the calibration, verify against `experiments/01_device_calibration.py` output:

* The fitted V_th must match Chapter 2.3 to <5 mV
* The fitted β_s must match to <3 V⁻¹
* R² must exceed 0.99 for clean curves (P→AP for both Device A and B)
* AP→P curves may have lower R² due to back-hopping plateau (Device A, V > 940 mV) or two-stage transition (Device B, 840–860 mV) -- this is a known device-physics artifact, not a fit failure.
