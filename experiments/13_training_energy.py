"""13 -- End-to-end training energy across 8 CIM architectures.

Estimates the total energy spent during one full MNIST training run
(PBNN-MLP topology, 20 epochs, batch 128, 9380 mini-batches), with
every NN operation mapped onto specific physical storage and compute
primitives.

Architectures compared
----------------------

Three probabilistic-binary variants (T=4 stochastic samples per weight,
the sweet spot from Experiment 06):

  * PBNN sMTJ        — SOT-MTJ stochastic switching, write 0.78 pJ/sample
                        (physics-grounded V^2/R*t).  Garello 2019 etc.
  * PBNN stoch-ReRAM — HfO_x ReRAM with probabilistic SET/RESET, write
                        50 pJ/sample.  Lin 2018 IEEE EDL 39.
  * PBNN CMOS-PRNG   — SRAM bit + 32-bit LFSR + comparator, ~3 fJ/sample.
                        Hayashida 2020 Nat Electron 3.

Five deterministic INT8 FP-NN variants (one bar per memory technology):

  * STT-MRAM, ReRAM, PCRAM, FeRAM (non-volatile)
  * SRAM-CIM (volatile)

All non-sMTJ-write numbers are 28 nm provisional defaults; see
``src/smtj_pbnn_sim/ppa/tech_params.py`` for the full citation list.

Outputs:
  figures/13a_training_energy_breakdown.png    horizontal stacked bars,
                                               8 architectures x (fwd /
                                               bwd / write/theta-update)
  runs/13_training_energy_<ts>/breakdown.csv   per-arch component table

Run from the repo root:

    python experiments/13_training_energy.py
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


def main() -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib + numpy required.")
        sys.exit(1)

    import csv
    import shutil
    from smtj_pbnn_sim.ppa import (
        default_28nm, MEMORIES, network_training_energy,
    )
    from smtj_pbnn_sim.utils.io import make_run_dir

    tech = default_28nm()
    run_dir = make_run_dir("13_training_energy", base=REPO / "runs")

    # ----- Network and training config (matches exp 05 PBNN-MLP) -----
    layer_dims = [(1024, 784), (1024, 1024), (10, 1024)]
    batch = 128
    n_epochs = 20
    train_size = 60000
    n_batches_per_epoch = (train_size + batch - 1) // batch  # 469
    n_steps = n_batches_per_epoch * n_epochs                  # 9380
    T = 4

    print("=== Experiment 13: Multi-architecture training energy ===\n")
    print(f"Network: 784 → 1024 → 1024 → 10")
    print(f"Layers (rows × cols): {layer_dims}")
    print(f"Batch size = {batch}, T = {T} (PBNN variants)")
    print(f"Steps = {n_batches_per_epoch} batches × {n_epochs} epochs "
          f"= {n_steps} mini-batches\n")

    # ----- 9 architecture configs ------------------------------------------
    # Probabilistic-binary references: sMTJ (this work), CMOS p-bit ASIC
    # (Camsari 2020 / Sutton 2020 / Borders 2019), stoch-ReRAM (Lin 2018),
    # synthesizable CMOS-PRNG lower bound.  Deterministic INT8 references:
    # five mainstream CIM memories (STT-MRAM, ReRAM, PCRAM, FeRAM,
    # SRAM-CIM).  See `tech_params.py` and `training_energy.py` for
    # full citations.
    ARCH_CONFIGS = [
        # (label, arch, kwargs for network_training_energy, write_key)
        ("PBNN sMTJ (T=4)",          "pbnn",       {},                              "theta_update"),
        ("PBNN CMOS p-bit (T=4)",    "pbnn_stoch", {"storage": "cmos_pbit"},        "theta_update"),
        ("PBNN stoch-ReRAM (T=4)",   "pbnn_stoch", {"storage": "stoch_reram"},      "theta_update"),
        ("PBNN CMOS-PRNG (T=4)",     "pbnn_stoch", {"storage": "cmos_prng"},        "theta_update"),
        ("FP-NN STT-MRAM",           "fp",         {"memory": MEMORIES["stt_mram"]}, "weight_write"),
        ("FP-NN ReRAM",              "fp",         {"memory": MEMORIES["reram"]},    "weight_write"),
        ("FP-NN PCRAM",              "fp",         {"memory": MEMORIES["pcram"]},    "weight_write"),
        ("FP-NN FeRAM",              "fp",         {"memory": MEMORIES["feram"]},    "weight_write"),
        ("FP-NN SRAM-CIM",           "fp",         {"memory": MEMORIES["sram_cim"]}, "weight_write"),
    ]

    # ----- Compute energy for every architecture --------------------------
    print(f"{'Architecture':24s} {'forward':>10} {'backward':>10} "
          f"{'write/θup':>10} {'TOTAL':>10}  {'per-step':>10}")
    print("-" * 84)

    results = []
    for label, arch, kwargs, write_key in ARCH_CONFIGS:
        r = network_training_energy(layer_dims, T=T, batch=batch,
                                     n_steps=n_steps, arch=arch,
                                     tech=tech, **kwargs)
        write_J = r[write_key]
        total_J = r["total"]
        per_step_mJ = r["per_step_total"] * 1e3
        print(f"{label:24s} {r['forward']:>8.3f} J {r['backward']:>8.3f} J "
              f"{write_J:>8.3f} J {total_J:>8.3f} J  {per_step_mJ:>8.3f} mJ")
        results.append({
            "label": label,
            "arch": arch,
            "write_key": write_key,
            "forward": r["forward"],
            "backward": r["backward"],
            "write": write_J,
            "total": total_J,
            "per_step_total": r["per_step_total"],
        })
    print()

    # ----- Find min and report ratios -------------------------------------
    min_total = min(r["total"] for r in results)
    pbnn_smtj = next(r for r in results if r["label"].startswith("PBNN sMTJ"))
    fp_stt = next(r for r in results if r["label"] == "FP-NN STT-MRAM")
    print(f"Cheapest architecture: "
          f"{next(r for r in results if r['total'] == min_total)['label']} "
          f"= {min_total:.3f} J")
    print(f"PBNN sMTJ / cheapest         = {pbnn_smtj['total'] / min_total:.2f}×")
    print(f"PBNN sMTJ / FP-NN STT-MRAM   = {pbnn_smtj['total'] / fp_stt['total']:.2f}×")
    print()

    # ----- Save CSV --------------------------------------------------------
    with open(run_dir / "breakdown.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["architecture", "arch_type", "forward_J", "backward_J",
                    "write_or_theta_J", "total_J",
                    "per_step_total_mJ"])
        for r in results:
            w.writerow([r["label"], r["arch"],
                        f"{r['forward']:.6f}",
                        f"{r['backward']:.6f}",
                        f"{r['write']:.6f}",
                        f"{r['total']:.6f}",
                        f"{r['per_step_total'] * 1e3:.6f}"])
    print(f"Breakdown CSV saved: {run_dir / 'breakdown.csv'}")

    # ===== Plot 13a: horizontal stacked bars ==============================
    print("\nGenerating figure ...")
    n = len(results)
    fig, ax = plt.subplots(figsize=(12, 7))
    y_pos = np.arange(n)
    fwd = np.array([r["forward"] for r in results])
    bwd = np.array([r["backward"] for r in results])
    wr = np.array([r["write"] for r in results])
    labels = [r["label"] for r in results]

    # Color: dark for forward, light for backward, orange for write/θ-update
    ax.barh(y_pos, fwd,             color="#4B1369", label="forward")
    ax.barh(y_pos, bwd, left=fwd,   color="#A97DBE", label="backward")
    ax.barh(y_pos, wr,  left=fwd + bwd, color="#D97706",
            label="weight write (FP) / θ-update (PBNN)")

    # Group dividers (visual separation between PBNN and FP groups).
    # 4 PBNN variants + 5 FP variants → divider after index 3 (between
    # last PBNN bar and first FP bar).
    n_pbnn = sum(1 for r in results
                 if r["arch"] in ("pbnn", "pbnn_stoch"))
    ax.axhline(y=n_pbnn - 0.5, color="#888", linestyle=":",
               lw=0.8, alpha=0.7)
    ax.text(0.98, n_pbnn - 0.5,
            "▲ probabilistic binary    ▼ deterministic INT8",
            transform=ax.get_yaxis_transform(),
            ha="right", va="center", fontsize=9, color="#555",
            backgroundcolor="white")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=11)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlabel("Total training energy (20 epochs, 9380 batches) [J, log scale]",
                   fontsize=12)
    ax.set_title("End-to-end training energy across 9 CIM architectures  "
                  f"(MNIST PBNN-MLP, T={T} for probabilistic-binary variants)",
                  fontsize=13)
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(axis="x", which="both", alpha=0.3)
    ax.set_xlim(1.0, 1e3)

    # Annotate totals at the end of each bar
    for i, r in enumerate(results):
        ax.text(r["total"] * 1.05, i, f"{r['total']:.2f} J",
                va="center", fontsize=10, fontweight="bold")

    fig.tight_layout()
    out_a = REPO / "figures" / "13a_training_energy_breakdown.png"
    out_a.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_a, dpi=150, bbox_inches="tight")
    shutil.copy2(out_a, run_dir / "13a_training_energy_breakdown.png")
    print(f"  Figure 13a saved: {out_a.relative_to(REPO)}")

    # ----- Summary -----
    print("\n--- Summary ---")
    print(f"Best (cheapest) architecture: "
          f"{next(r['label'] for r in results if r['total'] == min_total)}")
    pbnn_cmos = next(r for r in results if "CMOS-PRNG" in r["label"])
    fp_sram = next(r for r in results if "SRAM-CIM" in r["label"])
    fp_pcram = next(r for r in results if "PCRAM" in r["label"])
    print(f"  PBNN sMTJ           = {pbnn_smtj['total']:.2f} J")
    print(f"  PBNN CMOS-PRNG      = {pbnn_cmos['total']:.2f} J  "
          f"(softmax-cheap probabilistic binary)")
    print(f"  FP-NN SRAM-CIM      = {fp_sram['total']:.2f} J  "
          f"(volatile, fastest)")
    print(f"  FP-NN PCRAM         = {fp_pcram['total']:.2f} J  "
          f"(highest-write-energy NV)")
    print(f"\nRun directory: {run_dir}")
    print("Done.")


if __name__ == "__main__":
    main()
