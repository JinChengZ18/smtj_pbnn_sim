"""Calibration of sMTJ compact-model parameters from measured data.

Two fitting routines are provided, matching the two-tier model of
Chapter 2.3:

* :func:`fit_sigmoid_params` -- operating-point logistic fit of P_sw(V) at
  a fixed pulse width. Output: (V_th, V_T, R^2). When the input CSV carries
  ``device_id`` and/or ``direction`` columns, :func:`fit_per_device_direction`
  groups by them and returns one fit per group.

* :func:`fit_neel_brown_from_vth_vs_tw` -- linear regression of V_th(t_w)
  vs ln(t_w / tau_0) over multiple pulse widths to extract Delta and V_c0,
  the cross-pulse-width NB parameters.

Both routines accept dataframes with all voltages in volts and all times
in seconds. The CSV produced by ``scripts/extract_chapter2_data.py``
already follows this convention.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import math

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


# =============================================================================#
# Operating-point Sigmoid fit                                                   #
# =============================================================================#

@dataclass
class SigmoidParams:
    """Fitted Sigmoid parameters for one (device, direction) group."""
    V_th: float           # Sigmoid center [V]
    V_T: float            # slope parameter k [V]; beta_s = 1 / V_T
    beta_s: float         # logistic slope [V^-1]
    rmse: float
    r2: float
    n_points: int
    t_p: float            # pulse width at which the fit applies [s]


def _sigmoid(V: np.ndarray, V_th: float, V_T: float) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-(V - V_th) / V_T))


def fit_sigmoid_params(
    data: pd.DataFrame,
    *,
    initial_V_th: Optional[float] = None,
    initial_V_T: Optional[float] = None,
    bounds_V_T: tuple[float, float] = (1e-4, 0.5),
) -> SigmoidParams:
    """Fit a 2-parameter logistic to a P_sw(V) scatter at fixed pulse width.

    Args:
        data: DataFrame with columns ``V`` (volts) and ``P_sw``. Optional
            column ``t_p`` (seconds) is used if present.
        initial_V_th: Initial guess for the center; defaults to interpolating
            P_sw = 0.5 from the data.
        initial_V_T: Initial guess for the slope.
        bounds_V_T: Bounds for V_T during fitting.

    Returns:
        :class:`SigmoidParams`.
    """
    required = {"V", "P_sw"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Calibration data missing columns: {missing}")
    if len(data) < 4:
        raise ValueError("At least 4 data points needed for Sigmoid fitting.")

    V = data["V"].to_numpy(dtype=np.float64)
    P = data["P_sw"].to_numpy(dtype=np.float64)
    P = np.clip(P, 1e-6, 1.0 - 1e-6)

    if initial_V_th is None:
        order = np.argsort(V)
        V_sorted, P_sorted = V[order], P[order]
        if P_sorted.min() < 0.5 < P_sorted.max():
            initial_V_th = float(np.interp(0.5, P_sorted, V_sorted))
        else:
            initial_V_th = float(np.mean(V))
    if initial_V_T is None:
        initial_V_T = max(1e-3, 0.05 * (V.max() - V.min()))

    p0 = [initial_V_th, initial_V_T]
    lo = [-np.inf, bounds_V_T[0]]
    hi = [+np.inf, bounds_V_T[1]]

    popt, _ = curve_fit(_sigmoid, V, P, p0=p0, bounds=(lo, hi), maxfev=20_000)
    V_th_fit, V_T_fit = float(popt[0]), float(popt[1])
    pred = _sigmoid(V, V_th_fit, V_T_fit)
    rmse = float(np.sqrt(np.mean((pred - P) ** 2)))
    ss_res = float(np.sum((P - pred) ** 2))
    ss_tot = float(np.sum((P - P.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    t_p_val = float(data["t_p"].iloc[0]) if "t_p" in data.columns else float("nan")

    return SigmoidParams(
        V_th=V_th_fit, V_T=V_T_fit, beta_s=1.0 / V_T_fit,
        rmse=rmse, r2=r2, n_points=int(len(data)), t_p=t_p_val,
    )


def fit_per_device_direction(data: pd.DataFrame) -> pd.DataFrame:
    """Per (device_id, direction) Sigmoid fit.

    Returns a DataFrame with one row per group containing the fitted
    parameters. Groups whose fit fails record the error message instead.
    """
    by = []
    for col in ("device_id", "direction"):
        if col in data.columns:
            by.append(col)
    if not by:
        raise ValueError(
            "Per-group fit needs at least one of 'device_id', 'direction'."
        )
    rows = []
    for keys, group in data.groupby(by):
        if not isinstance(keys, tuple):
            keys = (keys,)
        rec: dict = dict(zip(by, keys))
        try:
            sp = fit_sigmoid_params(group)
            rec.update(asdict(sp))
            rec["error"] = ""
        except Exception as e:  # noqa: BLE001
            rec.update({"V_th": math.nan, "V_T": math.nan, "beta_s": math.nan,
                        "rmse": math.nan, "r2": math.nan,
                        "n_points": len(group), "t_p": math.nan,
                        "error": str(e)})
        rows.append(rec)
    return pd.DataFrame(rows)


# =============================================================================#
# Cross-pulse-width Néel-Brown fit                                              #
# =============================================================================#

@dataclass
class NBParams:
    """Néel-Brown parameters extracted from V_th(t_w) regression."""
    Delta: float
    V_c0: float
    tau_0_assumed: float
    r2: float
    n_points: int


def fit_neel_brown_from_vth_vs_tw(
    df: pd.DataFrame,
    *,
    tau_0: float = 1e-9,
) -> NBParams:
    """Fit (Delta, V_c0) from V_th vs ln(t_w) measurements.

    The NB closed form gives

        V_th(t_w) = V_c0 * (1 - ln(t_w / tau_0 / ln 2) / Delta).

    Re-arranging,

        V_th(t_w) = V_c0 + (V_c0 / Delta) * ln(ln 2)
                    - (V_c0 / Delta) * ln(t_w / tau_0)
                  = a - b * ln(t_w / tau_0),

    so a linear regression of V_th on x = ln(t_w / tau_0) yields slope
    -b = -V_c0 / Delta and intercept a = V_c0 * (1 + ln(ln 2) / Delta).
    Solving gives Delta = -a / b * (1 + ln(ln 2)/Delta-self-consistent),
    handled here by a one-step fixed-point iteration.

    Args:
        df: DataFrame with columns ``t_p`` (seconds) and ``V_th`` (volts).
            ``V_th`` is the half-switch voltage at each pulse width.
        tau_0: Assumed attempt time prior [s]; default 1 ns.

    Returns:
        :class:`NBParams` together with the regression R^2.
    """
    required = {"t_p", "V_th"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"NB fit needs columns: {missing}")
    if len(df) < 3:
        raise ValueError("At least 3 (t_p, V_th) points needed for NB fit.")

    x = np.log(df["t_p"].to_numpy(dtype=np.float64) / tau_0)
    y = df["V_th"].to_numpy(dtype=np.float64)

    # Linear regression y = a + m * x  with m = -V_c0 / Delta.
    A = np.vstack([np.ones_like(x), x]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    a, m = float(coef[0]), float(coef[1])
    if m >= 0:
        raise ValueError(
            f"V_th vs ln(t_w) slope must be negative; got {m}."
        )

    # First-pass Delta from b = V_c0 / Delta and a = V_c0 + b * ln(ln 2);
    # solve self-consistently in one step.
    b = -m
    Delta_guess = max(1.0, b / 0.05)        # crude initial; refined below
    for _ in range(8):
        V_c0 = a - b * math.log(math.log(2.0)) * 0.0  # leading order: V_c0 ~= a
        # NB closed form V_th(t_p) = V_c0 (1 - ln(t/tau0/ln2) / Delta)
        # => V_th = V_c0 + V_c0/Delta * ln(ln 2) - (V_c0/Delta) * ln(t/tau0)
        # => intercept a = V_c0 + b * ln(ln 2);  slope m = -b = -V_c0/Delta
        V_c0 = a - b * math.log(math.log(2.0))
        Delta = V_c0 / b
        Delta_guess = Delta

    # Goodness-of-fit:
    y_pred = a + m * x
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    return NBParams(
        Delta=Delta_guess, V_c0=V_c0, tau_0_assumed=tau_0,
        r2=r2, n_points=int(len(df)),
    )


# =============================================================================#
# YAML serialization                                                            #
# =============================================================================#

def write_device_yaml(
    *,
    sigmoid: SigmoidParams,
    out_path: str | Path,
    nb: Optional[NBParams] = None,
    eta_c: Optional[float] = None,
    R_P: float = 4.9e3,
    TMR: float = 1.0,
    R_SOT: float = 776.0,
    note: str = "",
) -> None:
    """Serialize calibration outputs to a device YAML config.

    The schema matches what ``configs/device/<name>.yaml`` is expected to
    look like, and what the experiment scripts read.
    """
    import yaml
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict = {
        "device_type": "sot_smtj",
        "operating_point": {
            "V_th_nom": sigmoid.V_th,
            "V_T_nom":  sigmoid.V_T,
            "beta_s":   sigmoid.beta_s,
            "t_p":      sigmoid.t_p,
            "fit_r2":   sigmoid.r2,
            "fit_rmse": sigmoid.rmse,
            "n_points": sigmoid.n_points,
        },
        "resistance": {
            "R_P_nom":  R_P,
            "TMR_nom":  TMR,
            "R_SOT":    R_SOT,
        },
    }
    if nb is not None:
        payload["neel_brown"] = {
            "Delta_nom": nb.Delta,
            "V_c0_nom":  nb.V_c0,
            "tau_0":     nb.tau_0_assumed,
            "fit_r2":    nb.r2,
            "n_points":  nb.n_points,
        }
    if eta_c is not None:
        payload["eta_c"] = float(eta_c)
    if note:
        payload["note"] = note
    with out_path.open("w") as f:
        yaml.safe_dump(payload, f, sort_keys=False)
