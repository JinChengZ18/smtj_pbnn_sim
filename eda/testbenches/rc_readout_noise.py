#!/usr/bin/env python3
"""P7 (errata R6): readout TIA+ADC noise -> RC memory-capacity loss.

The thesis says the readout shot-noise/ADC is the REAL limiter of the sMTJ reservoir,
yet ppa/reservoir_energy.py bills the readout as ~free. This first-cut quantifies the
readout PRECISION requirement: take a noise-free mean-field reservoir (isolates the
readout from device shot noise), pass its state features through a B-bit ADC + additive
read noise, and measure the linear memory capacity (Jaeger 2001) vs (ADC bits, noise).

Mean-field isolates the readout effect; the device shot-noise path is exp-14's domain.
The ADC/TIA *energy* mapping (NeuroSim/CrossSim) is the next step -- here we establish
how many bits the readout needs, i.e. that readout precision (not the device) gates RC.

Run: python eda/testbenches/rc_readout_noise.py    (pure Python; reuses smtj_pbnn_sim)
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np

from smtj_pbnn_sim.reservoir import (ReservoirConfig, SMTJReservoir,
                                     memory_capacity, tasks)

HERE = Path(__file__).resolve().parent
MAX_DELAY = 25
MF = dict(n_nodes=120, mode="meanfield", effective_spectral_radius=0.6,
          effective_input_scale=0.5, dt=8e-9, seed=1)


def adc(X, bits):
    """Uniform mid-tread B-bit ADC over the symmetric full-scale of X."""
    if not bits:
        return X
    vfs = float(np.max(np.abs(X))) * 1.0001 + 1e-12
    step = 2 * vfs / (2 ** bits - 1)
    return np.clip(np.round(X / step) * step, -vfs, vfs)


def main():
    u = tasks.memory_capacity_inputs(1200, seed=2)
    res = SMTJReservoir(ReservoirConfig(**MF), n_inputs=1)
    X = res.run(u, washout=100)
    ua = u[100:]
    mc0, _ = memory_capacity(X, ua, max_delay=MAX_DELAY)
    rng = np.random.default_rng(7)
    sd = float(np.std(X))
    print(f"baseline memory capacity (mean-field, full precision): MC0 = {mc0:.2f}")

    print("\nADC resolution sweep (per-node readout quantization):")
    print("  bits   MC      MC/MC0")
    adc_rows = []
    for B in (3, 4, 5, 6, 8, 10, None):
        mc, _ = memory_capacity(adc(X, B), ua, max_delay=MAX_DELAY)
        tag = "inf" if not B else str(B)
        print(f"  {tag:>4}  {mc:5.2f}    {mc/mc0:5.3f}")
        adc_rows.append(dict(adc_bits=tag, mc=mc, frac=mc / mc0))

    print("\nRead-noise sweep (additive Gaussian on states, as fraction of state std):")
    print("  noise/sd   MC      MC/MC0")
    noise_rows = []
    for f in (0.0, 0.02, 0.05, 0.10, 0.20):
        Xn = X + rng.normal(0.0, f * sd, X.shape)
        mc, _ = memory_capacity(Xn, ua, max_delay=MAX_DELAY)
        print(f"  {f:6.2f}    {mc:5.2f}    {mc/mc0:5.3f}")
        noise_rows.append(dict(read_noise_frac=f, mc=mc, frac=mc / mc0))

    # knee: smallest bit count keeping >=95% of MC0
    knee = next((r["adc_bits"] for r in adc_rows if r["frac"] >= 0.95 and r["adc_bits"] != "inf"), ">10")
    summ = dict(MC0=mc0, adc_sweep=adc_rows, noise_sweep=noise_rows,
                bits_for_95pct_MC=knee,
                note=("mean-field isolates the readout; readout precision (ADC bits + TIA noise) "
                      "gates RC memory capacity. Energy mapping (NeuroSim ADC) is the next step (R6)."))
    (HERE / "rc_readout_summary.json").write_text(json.dumps(summ, indent=2))
    print(f"\n=> readout needs ~{knee} ADC bits to keep >=95% of MC; "
          f"this precision requirement IS the claim-(e) limiter (errata R6).")


if __name__ == "__main__":
    main()
