"""End-to-end training energy estimator (PBNN sMTJ array vs. FP-NN MRAM).

Models the per-batch energy cost of one *training step* (forward +
backward + weight update) for two hardware architectures:

  * **PBNN** -- weights stored as T sMTJ cells per weight; inference does
    T stochastic samples; latent ``theta`` lives in SRAM/DRAM and is
    cheap to update.
  * **FP-NN (baseline)** -- weights stored as ``mram_bits_per_weight``
    digital MRAM bits per weight (default INT8); inference reads all
    bits and runs digital INT8 MACs; weight updates write all bits per
    weight.

A full training step has *three* MAC passes: forward (output), backward
input gradient ``W^T @ dL/dy``, and backward weight gradient
``dL/dy @ x^T``. We account for all three in the per-step total.

Energy components per batch, summed across one fully-connected layer of
``rows x cols`` weights:

  PBNN:
      E_fwd       = batch * rows * cols * T * E_per_MAC
      E_bwd_input = batch * rows * cols * E_int8_mac
                       + rows * cols * T * E_smtj_read     (re-read W^T)
      E_bwd_weight= batch * rows * cols * E_int8_mac
      E_thup      = rows * cols * 4 * E_sram_byte          (theta float32 update)

  FP-NN:
      E_fwd       = batch * rows * cols *
                       (E_int8_mac + bits * E_mram_read)
      E_bwd_input = batch * rows * cols *
                       (E_int8_mac + bits * E_mram_read)   (re-read W^T)
      E_bwd_weight= batch * rows * cols * E_int8_mac        (weights
                       not needed; activations are SRAM-cached)
      E_wwup      = rows * cols * bits * E_mram_write       (weight write)

(``E_per_MAC`` is the inference-time PBNN per-MAC energy from
:func:`smtj_pbnn_sim.ppa.energy.per_mac_energy`, dominated by sMTJ
writes. ``E_int8_mac`` includes digital multiplier+accumulator with
control overhead; ``E_mram_read`` is per-cell sense-amp energy.)

Notes
-----
* All energies are returned in joules.
* The model assumes weights are local (no DRAM streaming during
  training); add ``e_dram_byte * mac_bytes`` if your scenario differs.
* For multi-layer networks, sum per-layer energies; helper
  :func:`network_training_energy` does this.
"""

from __future__ import annotations

from typing import Iterable, Optional
from .tech_params import TechParams, MemoryParams, MEMORIES, default_28nm
from .energy import per_mac_energy


def pbnn_step_energy(rows: int, cols: int, T: int, batch: int,
                      tech: TechParams | None = None) -> dict[str, float]:
    """Energy of one training step for one PBNN-array layer.

    A full step has *three* MAC passes: forward, backward-input,
    backward-weight.  Returns a dict with keys ``forward``,
    ``backward_input``, ``backward_weight``, ``theta_update``, ``total``
    (joules).
    """
    tech = tech or default_28nm()
    e_mac = per_mac_energy(tech)
    macs_per_sample = rows * cols
    e_fwd = batch * macs_per_sample * T * e_mac
    # Backward input gradient: digital INT8 mul through STE,
    # plus T stochastic re-reads of W for the W^T product.
    e_bwd_input = (batch * macs_per_sample * tech.e_int8_mac
                   + macs_per_sample * T * tech.e_smtj_read)
    # Backward weight gradient: outer product dL/dy @ x^T -- pure
    # digital, no array involvement.
    e_bwd_weight = batch * macs_per_sample * tech.e_int8_mac
    # Latent theta sits in SRAM (4 bytes per weight, fp32)
    e_theta = macs_per_sample * 4 * tech.e_sram_byte
    total = e_fwd + e_bwd_input + e_bwd_weight + e_theta
    return {
        "forward":         e_fwd,
        "backward_input":  e_bwd_input,
        "backward_weight": e_bwd_weight,
        "backward":        e_bwd_input + e_bwd_weight,  # convenience
        "theta_update":    e_theta,
        "total":           total,
    }


def fp_step_energy(rows: int, cols: int, batch: int,
                    tech: TechParams | None = None,
                    memory: MemoryParams | None = None) -> dict[str, float]:
    """Energy of one training step for one FP-NN CIM-backed layer.

    A full step has *three* MAC passes: forward, backward-input,
    backward-weight.  The first two need cell reads (weights for fwd,
    weights again for the W^T pass); the third (weight gradient) reads
    only activations, which we treat as SRAM-cached.

    Parameters
    ----------
    memory : MemoryParams or None
        Per-cell read/write energies. Defaults to STT-MRAM
        (``MEMORIES["stt_mram"]``) for backward compatibility with the
        original Experiment 13 numbers.

    Returns a dict with keys ``forward``, ``backward_input``,
    ``backward_weight``, ``weight_write``, ``total`` (joules).
    """
    tech = tech or default_28nm()
    memory = memory or MEMORIES["stt_mram"]
    macs_per_sample = rows * cols
    bits = memory.bits_per_weight
    # Weight-side MAC: digital INT8 compute + read all cells of the weight
    e_per_mac_w = tech.e_int8_mac + bits * memory.e_read_per_bit
    # Activation-side MAC: weights not needed; activations cached in SRAM
    e_per_mac_act = tech.e_int8_mac
    e_fwd = batch * macs_per_sample * e_per_mac_w
    e_bwd_input = batch * macs_per_sample * e_per_mac_w
    e_bwd_weight = batch * macs_per_sample * e_per_mac_act
    e_write = macs_per_sample * bits * memory.e_write_per_cell
    total = e_fwd + e_bwd_input + e_bwd_weight + e_write
    return {
        "forward":         e_fwd,
        "backward_input":  e_bwd_input,
        "backward_weight": e_bwd_weight,
        "backward":        e_bwd_input + e_bwd_weight,
        "weight_write":    e_write,
        "total":           total,
    }


def pbnn_stoch_step_energy(rows: int, cols: int, T: int, batch: int,
                            storage: str,
                            tech: TechParams | None = None
                            ) -> dict[str, float]:
    """Per-batch training energy for a probabilistic-binary architecture
    using a non-sMTJ stochastic device.

    Three storage variants are modelled:

    * ``storage="stoch_reram"`` — each weight uses T ReRAM cells with
      probabilistic SET/RESET switching (Lin et al. 2018, IEEE EDL 39).
      Per-sample write energy = E_reram_write per cell (~50 pJ); read
      energy = E_reram_read per bit.

    * ``storage="cmos_pbit"`` — published CMOS p-bit ASIC class
      (Camsari et al. 2020, Proc IEEE 108(8); Sutton et al. 2020,
      Sci Adv 6 eabb2823; Borders et al. 2019, Nature 573).  Each
      sample = one full p-bit update including weighted-sum + threshold
      + Bernoulli draw, taken at 5 pJ per spin-update at 5 ns clock —
      the per-cell cost in the Camsari 2020 hardware compendium.  Note:
      this 5 pJ already includes the weighted-sum compute, so we do
      *not* add an additional INT8 MAC cost on top.

    * ``storage="cmos_prng"`` — synthesizable lower bound: each weight
      uses T binary SRAM bits, with a 32-bit LFSR + comparator producing
      pseudo-random Bernoulli samples (per-sample LFSR cost ≈ 3 fJ;
      Hayashida et al. 2020, Nat Electron 3).  Per-sample energy =
      E_int8_mac (weighted-sum) + 3 fJ (LFSR + SRAM read + comparator);
      no high-energy device write because SRAM holds the binary state
      cheaply.  This is more optimistic than the Camsari 2020 ASIC
      because it omits weighted-sum LUT overhead absorbed into their
      5 pJ figure.

    Returns the same dict structure as :func:`pbnn_step_energy`.
    """
    tech = tech or default_28nm()
    macs_per_sample = rows * cols

    if storage == "stoch_reram":
        mem = MEMORIES["reram"]
        e_per_sample = (tech.e_dac_step
                         + mem.e_write_per_cell
                         + mem.e_read_per_bit
                         + tech.e_count_inc)
        e_fwd = batch * macs_per_sample * T * e_per_sample
        # Backward-input: digital INT8 + T ReRAM re-reads of W (transpose)
        e_bwd_input = (batch * macs_per_sample * tech.e_int8_mac
                       + macs_per_sample * T * mem.e_read_per_bit)
        e_bwd_weight = batch * macs_per_sample * tech.e_int8_mac
        # theta lives in SRAM (cheap, 4 B/weight)
        e_theta = macs_per_sample * 4 * tech.e_sram_byte
    elif storage == "cmos_pbit":
        # Camsari 2020 CMOS p-bit ASIC: 5 pJ per spin update including
        # weighted-sum + threshold + Bernoulli generator (no separate
        # INT8 MAC needed).
        e_per_sample = 5.0e-12
        e_fwd = batch * macs_per_sample * T * e_per_sample
        # Backward: still needs digital INT8 to compute gradients.
        # Activations cached in SRAM as in fp_step_energy.
        e_bwd_input = batch * macs_per_sample * tech.e_int8_mac
        e_bwd_weight = batch * macs_per_sample * tech.e_int8_mac
        # theta in SRAM
        e_theta = macs_per_sample * 4 * tech.e_sram_byte
    elif storage == "cmos_prng":
        # ~3 fJ per Bernoulli draw (LFSR step + SRAM read + comparator),
        # plus the digital INT8 weighted-sum.
        e_per_sample = 3.0e-15
        e_fwd = batch * macs_per_sample * T * (tech.e_int8_mac + e_per_sample)
        # Backward-input: digital INT8; weight bits already in SRAM (~free)
        e_bwd_input = batch * macs_per_sample * tech.e_int8_mac
        e_bwd_weight = batch * macs_per_sample * tech.e_int8_mac
        # theta in SRAM
        e_theta = macs_per_sample * 4 * tech.e_sram_byte
    else:
        raise ValueError(
            f"unknown storage {storage!r}; expected one of "
            f"'stoch_reram', 'cmos_pbit', 'cmos_prng'.")

    total = e_fwd + e_bwd_input + e_bwd_weight + e_theta
    return {
        "forward":         e_fwd,
        "backward_input":  e_bwd_input,
        "backward_weight": e_bwd_weight,
        "backward":        e_bwd_input + e_bwd_weight,
        "theta_update":    e_theta,
        "total":           total,
    }


def network_training_energy(layer_dims: Iterable[tuple[int, int]],
                             T: int, batch: int, n_steps: int,
                             arch: str = "pbnn",
                             tech: TechParams | None = None,
                             memory: MemoryParams | None = None,
                             storage: str | None = None,
                             ) -> dict[str, float]:
    """Total training energy for a multi-layer MLP over ``n_steps`` batches.

    Parameters
    ----------
    layer_dims : iterable of (rows, cols) tuples
        Each layer's weight-matrix shape.
    T : int
        Number of stochastic samples per inference (PBNN only; ignored
        for ``arch="fp"``).
    batch : int
        Mini-batch size.
    n_steps : int
        Total number of training mini-batches (e.g. epochs * batches).
    arch : {"pbnn", "fp"}
        Hardware architecture to estimate.

    Returns
    -------
    dict with keys
        ``forward``, ``backward``, ``write`` (or ``theta_update`` for
        PBNN), ``total`` -- summed over all layers and steps (joules).
        Plus ``per_step_total`` for convenience.
    """
    tech = tech or default_28nm()
    arch_lower = arch.lower()
    keys_pbnn = ("forward", "backward_input", "backward_weight", "theta_update")
    keys_fp = ("forward", "backward_input", "backward_weight", "weight_write")
    if arch_lower == "pbnn":
        keys = keys_pbnn
        per_step = {k: 0.0 for k in keys}
        for rows, cols in layer_dims:
            d = pbnn_step_energy(rows, cols, T, batch, tech)
            for k in keys:
                per_step[k] += d[k]
    elif arch_lower == "pbnn_stoch":
        # Non-sMTJ probabilistic binary (storage="stoch_reram"|"cmos_prng")
        if storage is None:
            raise ValueError(
                "arch='pbnn_stoch' requires storage='stoch_reram' or 'cmos_prng'")
        keys = keys_pbnn
        per_step = {k: 0.0 for k in keys}
        for rows, cols in layer_dims:
            d = pbnn_stoch_step_energy(rows, cols, T, batch, storage, tech)
            for k in keys:
                per_step[k] += d[k]
    elif arch_lower == "fp":
        keys = keys_fp
        per_step = {k: 0.0 for k in keys}
        for rows, cols in layer_dims:
            d = fp_step_energy(rows, cols, batch, tech, memory=memory)
            for k in keys:
                per_step[k] += d[k]
    else:
        raise ValueError(
            f"unknown arch: {arch!r}; expected 'pbnn', 'pbnn_stoch', or 'fp'.")

    per_step["backward"] = (per_step["backward_input"]
                             + per_step["backward_weight"])
    per_step["total"] = sum(per_step[k] for k in keys)

    out = {f"step_{k}": v for k, v in per_step.items()}
    out["n_steps"] = n_steps
    for k in ("forward", "backward_input", "backward_weight", "backward"):
        out[k] = per_step[k] * n_steps
    write_key = ("theta_update" if arch_lower in ("pbnn", "pbnn_stoch")
                  else "weight_write")
    out[write_key] = per_step[write_key] * n_steps
    out["total"] = per_step["total"] * n_steps
    out["per_step_total"] = per_step["total"]
    return out
