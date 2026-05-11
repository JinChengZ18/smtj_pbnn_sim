"""08 -- Non-ideality ablation: systematic study of how each device
non-ideality affects PBNN inference accuracy (requires PyTorch).

Produces two figures:

  1. ``figures/08a_psw_nonideality_curves.png`` — P_sw(theta) curve
     distortion for each non-ideality channel, using the Chapter 2.3
     device model. Six panels:
       (a) CV(Delta) — D2D thermal-stability variation
       (b) sigma_rel(V_th) — threshold-shift D2D
       (c) sigma_rel(V_T) — slope D2D
       (d) sigma_C2C — cycle-to-cycle noise
       (e) p_max — back-hopping plateau
       (f) combined calibrated device

  2. ``figures/08b_nonideality_accuracy.png`` — MNIST test accuracy
     vs. non-ideality strength for each channel, evaluated in
     FULL_STACK mode.

This is the ablation companion to experiment 07 (which only swept
CV(Delta)). By isolating each non-ideality channel, one can see which
device parameter most strongly limits inference quality and where the
design margin lies.

Run from the repo root:

    python experiments/08_nonideality_ablation.py
"""

from __future__ import annotations

from pathlib import Path
import sys
from dataclasses import replace

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


# =============================================================================#
# Colour palette (kept in sync with the Ising-model demo)                      #
# =============================================================================#

PURPLE = {
    "darkest":  "#4B1369",
    "dark":     "#6E2C91",
    "medium":   "#8E54A8",
    "primary":  "#A97DBE",
    "light":    "#C4A7D4",
    "paler":    "#DCC6E6",
    "palest":   "#EFE6F4",
    "accent":   "#D97706",
    "gray":     "#6B6B6B",
}


def _set_style():
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Liberation Sans",
                            "Helvetica", "DejaVu Sans"],
        "mathtext.fontset": "stix",
        "font.size": 12,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 9,
        "axes.linewidth": 1.0,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "axes.grid": True,
        "grid.color": "#E8E8E8",
        "grid.linewidth": 0.6,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    })


def _gradient_colors(n, start_hex, end_hex):
    s = np.array([int(start_hex[i:i+2], 16) for i in (1, 3, 5)]) / 255.0
    e = np.array([int(end_hex[i:i+2], 16) for i in (1, 3, 5)]) / 255.0
    return [tuple((1 - k / max(n - 1, 1)) * s + (k / max(n - 1, 1)) * e)
            for k in range(n)]


# =============================================================================#
# Part 1: P_sw curve visualisation (NumPy only, no torch required)             #
# =============================================================================#

def _write_csv(path, header, rows):
    """Write a simple CSV with header and rows."""
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _part1_psw_curves(out_dir: Path) -> None:
    """Visualise how each non-ideality distorts the P_sw(theta) curve."""
    import matplotlib.pyplot as plt
    from smtj_pbnn_sim.device.arrhenius import psw_sigmoid

    _set_style()

    # Chapter 2.3 primary-reference nominal parameters
    V_th_nom = 0.894
    V_T_nom  = 1.0 / 44.6  # 0.02242 V

    theta = np.linspace(-6.0, 6.0, 601)
    p_ideal = 1.0 / (1.0 + np.exp(-theta))  # sigmoid(theta)

    rng = np.random.default_rng(2024)

    fig, axes = plt.subplots(2, 3, figsize=(14.0, 8.0))
    ax = axes.ravel()

    def _plot_common(a, title):
        a.plot(theta, p_ideal, "--", color=PURPLE["accent"],
               lw=1.3, alpha=0.6, label=r"ideal $\sigma(\theta)$", zorder=2)
        a.set_xlabel(r"latent parameter $\theta$")
        a.set_ylabel(r"$P_{\rm sw}(\theta)$")
        a.set_title(title)
        a.set_xlim(theta.min(), theta.max())
        a.set_ylim(-0.02, 1.05)

    # ------ (a) joint D2D: V_th + V_T spread ------
    # Uses sigmoid_direct mode centered at V_th_nom to isolate
    # the effect of D2D spread without the NB center offset.
    d2d_values = [0.0, 0.05, 0.10, 0.20, 0.30]
    n_dev = 5000
    colors_a = _gradient_colors(len(d2d_values), PURPLE["darkest"],
                                PURPLE["accent"])
    _plot_common(ax[0],
                 r"D2D:  $V_{\rm th}$+$V_T$ jointly")
    for i, sv in enumerate(d2d_values):
        if sv == 0.0:
            p = p_ideal.copy()
        else:
            V_th_arr = rng.normal(V_th_nom, sv * V_th_nom, size=n_dev)
            V_T_arr = np.maximum(
                rng.normal(V_T_nom, 2 * sv * V_T_nom, size=n_dev), 1e-4)
            V_wr = V_th_nom + V_T_nom * theta[None, :]
            p = psw_sigmoid(V_wr,
                            V_th_arr[:, None],
                            V_T_arr[:, None]).mean(axis=0)
        lw = 2.4 if sv == 0.0 else 1.6
        label = (f"$\\sigma_{{V_{{\\rm th}}}}={sv*100:.0f}\\%$"
                 if sv > 0 else "0 (ideal)")
        ax[0].plot(theta, p, "-", color=colors_a[i], lw=lw,
                   label=label, zorder=3)
    ax[0].legend(loc="lower right", frameon=False)

    # ------ (b) sigma_rel(V_th) — threshold shift D2D ------
    svth_values = [0.0, 0.02, 0.05, 0.10, 0.20]
    colors_b = _gradient_colors(len(svth_values), PURPLE["darkest"],
                                PURPLE["accent"])
    _plot_common(ax[1], r"D2D:  $\sigma_{\rm rel}(V_{\rm th})$")
    for i, sv in enumerate(svth_values):
        if sv == 0.0:
            p = p_ideal.copy()
        else:
            V_th_arr = rng.normal(V_th_nom, sv * V_th_nom, size=n_dev)
            V_wr = V_th_nom + V_T_nom * theta[None, :]
            p = psw_sigmoid(V_wr,
                            V_th_arr[:, None],
                            np.full((n_dev, 1), V_T_nom)).mean(axis=0)
        lw = 2.4 if sv == 0.0 else 1.6
        label = f"$\\sigma_{{\\rm rel}}={sv*100:.0f}\\%$" if sv > 0 else "0 (ideal)"
        ax[1].plot(theta, p, "-", color=colors_b[i], lw=lw,
                   label=label, zorder=3)
    ax[1].legend(loc="lower right", frameon=False)

    # ------ (c) sigma_rel(V_T) — slope D2D ------
    svt_values = [0.0, 0.05, 0.10, 0.30, 0.60]
    colors_c = _gradient_colors(len(svt_values), PURPLE["darkest"],
                                PURPLE["accent"])
    _plot_common(ax[2], r"D2D:  $\sigma_{\rm rel}(V_T)$")
    for i, sv in enumerate(svt_values):
        if sv == 0.0:
            p = p_ideal.copy()
        else:
            V_T_arr = np.maximum(
                rng.normal(V_T_nom, sv * V_T_nom, size=n_dev), 1e-4)
            V_wr = V_th_nom + V_T_nom * theta[None, :]
            p = psw_sigmoid(V_wr,
                            np.full((n_dev, 1), V_th_nom),
                            V_T_arr[:, None]).mean(axis=0)
        lw = 2.4 if sv == 0.0 else 1.6
        label = f"$\\sigma_{{\\rm rel}}={sv*100:.0f}\\%$" if sv > 0 else "0 (ideal)"
        ax[2].plot(theta, p, "-", color=colors_c[i], lw=lw,
                   label=label, zorder=3)
    ax[2].legend(loc="lower right", frameon=False)

    # ------ (d) sigma_C2C — cycle-to-cycle noise ------
    # sigma_C2C is in volts; we express in multiples of V_T for the label.
    sc2c_multiples = [0.0, 0.5, 1.0, 2.0, 4.0]
    colors_d = _gradient_colors(len(sc2c_multiples), PURPLE["darkest"],
                                PURPLE["accent"])
    _plot_common(ax[3], r"C2C noise  $\sigma_{\rm C2C}$")
    n_cycles = 3000
    for i, m in enumerate(sc2c_multiples):
        sigma = m * V_T_nom
        if sigma == 0.0:
            p = p_ideal.copy()
        else:
            eps = rng.normal(0.0, sigma, size=(n_cycles, len(theta)))
            V_wr = V_th_nom + V_T_nom * theta[None, :] + eps
            p = psw_sigmoid(V_wr,
                            np.full_like(V_wr, V_th_nom),
                            np.full_like(V_wr, V_T_nom)).mean(axis=0)
        lw = 2.4 if m == 0.0 else 1.6
        label = (f"$\\sigma_{{\\rm C2C}}={m:g}\\,V_T$"
                 if m > 0 else "0 (ideal)")
        ax[3].plot(theta, p, "-", color=colors_d[i], lw=lw,
                   label=label, zorder=3)
    ax[3].legend(loc="lower right", frameon=False)

    # ------ (e) p_max — back-hopping plateau ------
    pm_values = [1.0, 0.95, 0.85, 0.72, 0.55]
    colors_e = _gradient_colors(len(pm_values), PURPLE["darkest"],
                                PURPLE["accent"])
    _plot_common(ax[4], r"back-hopping  $p_{\rm max}$")
    for i, pm in enumerate(pm_values):
        p = np.clip(p_ideal, 1.0 - pm, pm)
        lw = 2.4 if pm == 1.0 else 1.6
        label = f"$p_{{\\rm max}}={pm:g}$" + ("  (ideal)" if pm == 1.0 else "")
        ax[4].plot(theta, p, "-", color=colors_e[i], lw=lw,
                   label=label, zorder=3)
    ax[4].legend(loc="lower right", frameon=False)

    # ------ (f) combined calibrated device ------
    # D2D (sigma_V_th=5%, sigma_V_T=10%) + back-hopping + C2C
    _plot_common(ax[5], "combined: D2D + plateau + C2C")

    V_wr_grid = V_th_nom + V_T_nom * theta[None, :]

    # D2D only (sigma_V_th=5%, sigma_V_T=10%)
    V_th_d2d = rng.normal(V_th_nom, 0.05 * V_th_nom, size=n_dev)
    V_T_d2d = np.maximum(
        rng.normal(V_T_nom, 0.10 * V_T_nom, size=n_dev), 1e-4)
    p_d2d = psw_sigmoid(V_wr_grid,
                        V_th_d2d[:, None],
                        V_T_d2d[:, None]).mean(axis=0)

    # D2D + plateau (p_max = 0.72)
    p_d2d_plat = np.clip(
        psw_sigmoid(V_wr_grid,
                    V_th_d2d[:, None],
                    V_T_d2d[:, None]),
        1.0 - 0.72, 0.72).mean(axis=0)

    # D2D + plateau + C2C (sigma = 1.0 V_T)
    sigma_c2c = 1.0 * V_T_nom
    eps = rng.normal(0.0, sigma_c2c, size=(n_dev, len(theta)))
    V_wr_noisy = V_wr_grid + eps
    p_all = np.clip(
        psw_sigmoid(V_wr_noisy,
                    V_th_d2d[:, None],
                    V_T_d2d[:, None]),
        1.0 - 0.72, 0.72).mean(axis=0)

    ax[5].plot(theta, p_d2d, "-", color=PURPLE["medium"], lw=1.6,
               label=r"D2D ($\sigma_{V_{\rm th}}=5\%$)", zorder=3)
    ax[5].plot(theta, p_d2d_plat, "-", color=PURPLE["primary"], lw=1.6,
               label="+ plateau ($p_{\\rm max}=0.72$)", zorder=3)
    ax[5].plot(theta, p_all, "-", color=PURPLE["darkest"], lw=2.4,
               label="+ C2C ($\\sigma=1\\,V_T$)", zorder=4)
    ax[5].legend(loc="lower right", frameon=False)

    fig.suptitle(
        "Effect of each non-ideality on $P_{\\rm sw}(\\theta)$"
        " (Chapter 2.3 device model)",
        fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = out_dir / "08a_psw_nonideality_curves.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Part 1 saved: {out.relative_to(REPO)}")


# =============================================================================#
# Part 2: Accuracy ablation (requires PyTorch + trained checkpoint)            #
# =============================================================================#

def _part2_accuracy_ablation(out_dir: Path, run_dir: Path | None = None) -> None:
    """Sweep each non-ideality independently and measure PBNN accuracy."""
    try:
        import torch
        import matplotlib.pyplot as plt
    except ImportError:
        print("  Part 2 skipped (PyTorch not available).")
        return

    from smtj_pbnn_sim.device.variation import VariationConfig
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode, DeviceLayerParams
    from smtj_pbnn_sim.nn.losses import binary_cross_entropy_loss
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import evaluate, calibrate_bn
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP

    _set_style()

    ckpt_path = REPO / "runs" / "mnist_pbnn_mlp" / "best.pt"
    if not ckpt_path.exists():
        print(f"  Part 2 skipped: checkpoint not found at {ckpt_path}.")
        print("  Run experiments/05_mnist_pbnn.py first.")
        return

    state = torch.load(ckpt_path, map_location="cpu")
    cfg = state["config"]
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dp_base = _device_params_from_cfg(cfg.get("device", {}))
    model_cfg = cfg.get("model", {})
    hidden = int(model_cfg.get("hidden", 1024))

    train_loader, test_loader = get_mnist_loaders(
        root=cfg.get("data", {}).get("root", "./data/mnist"),
        batch_size=int(cfg.get("data", {}).get("batch_size", 128)),
        num_workers=0,
    )

    T_eval = 64

    def _eval(dp: DeviceLayerParams,
              vc: VariationConfig | None) -> float:
        """Build model, load weights, calibrate BN, evaluate accuracy.

        After loading the checkpoint, the variation buffers (V_th_field,
        V_T_field) are overridden with the checkpoint's values.  We must
        force a fresh re-draw using the *current* dp/vc so that each
        scenario gets variation fields consistent with its config
        (including the no-variation baseline where fields = nominal).
        """
        from smtj_pbnn_sim.nn.pbnn_linear import PBNNLinear
        model = PBNN_MLP(hidden=hidden, device_params=dp,
                          variation_cfg=vc,
                          T_full_stack=T_eval).to(dev)
        model.load_state_dict(state["model_state"], strict=True)
        # Force fresh variation draw with current dp / vc
        for m in model.modules():
            if isinstance(m, PBNNLinear):
                m.device_params = dp
                m.variation_cfg = vc
                m._variation_drawn = False
        calibrate_bn(model, train_loader, dev,
                     mode=ForwardMode.FULL_STACK, T=T_eval)
        _, acc = evaluate(model, test_loader, binary_cross_entropy_loss,
                          dev, mode=ForwardMode.FULL_STACK, T=T_eval)
        return acc

    fig, axes = plt.subplots(2, 3, figsize=(14.0, 8.0))
    ax = axes.ravel()

    def _ax_setup(a, xlabel, title):
        a.set_xlabel(xlabel)
        a.set_ylabel("Test accuracy")
        a.set_title(title)
        a.grid(alpha=0.3)
        a.set_ylim(0.0, 1.02)

    # ------ (a) joint D2D sweep (V_th + V_T together) ------
    # Uses sigmoid_direct mode centered at V_th_nom to isolate the
    # effect of D2D SPREAD without the NB-derived center offset
    # (the known 843 vs 894 mV mismatch).  Ratio sigma_V_T/sigma_V_th
    # = 2 roughly matches the delta-mode physics.
    d2d_vals = [0.0, 0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30]
    accs_a = []
    print("  (a) joint D2D sweep (V_th + V_T):")
    for sv in d2d_vals:
        if sv == 0:
            vc = None
        else:
            vc = VariationConfig(mode="sigmoid_direct",
                                 sigma_V_th_rel=sv,
                                 sigma_V_T_rel=2.0 * sv,
                                 sigma_RP_rel=0.0,
                                 sigma_TMR_rel=0.0,
                                 seed=42)
        acc = _eval(dp_base, vc)
        accs_a.append(acc)
        print(f"       sigma={sv*100:5.1f}%   acc={acc:.4f}")
    ax[0].plot([v * 100 for v in d2d_vals], accs_a, "o-",
               color=PURPLE["dark"], lw=2, ms=5)
    _ax_setup(ax[0],
              r"$\sigma_{\rm rel}(V_{\rm th})$  (%)"
              r"  [$\sigma(V_T) = 2\times$]",
              r"D2D:  $V_{\rm th}$ + $V_T$ jointly")

    # ------ (b) sigma_rel(V_th) sweep ------
    svth_vals = [0.0, 0.02, 0.05, 0.08, 0.10, 0.15, 0.20]
    accs_b = []
    print("(b)  sigma_rel(V_th) sweep:")
    for sv in svth_vals:
        if sv == 0:
            vc = None
        else:
            vc = VariationConfig(mode="sigmoid_direct",
                                 sigma_V_th_rel=sv,
                                 sigma_V_T_rel=0.0,
                                 sigma_RP_rel=0.0,
                                 sigma_TMR_rel=0.0,
                                 seed=42)
        acc = _eval(dp_base, vc)
        accs_b.append(acc)
        print(f"       sigma_rel={sv*100:5.1f}%   acc={acc:.4f}")
    ax[1].plot([v * 100 for v in svth_vals], accs_b, "s-",
               color=PURPLE["dark"], lw=2, ms=5)
    _ax_setup(ax[1], r"$\sigma_{\rm rel}(V_{\rm th})$  (%)",
              r"D2D:  $V_{\rm th}$ shift")

    # ------ (c) sigma_rel(V_T) sweep ------
    svt_vals = [0.0, 0.05, 0.10, 0.20, 0.30, 0.50, 0.80]
    accs_c = []
    print("  (c) sigma_rel(V_T) sweep:")
    for sv in svt_vals:
        if sv == 0:
            vc = None
        else:
            vc = VariationConfig(mode="sigmoid_direct",
                                 sigma_V_th_rel=0.0,
                                 sigma_V_T_rel=sv,
                                 sigma_RP_rel=0.0,
                                 sigma_TMR_rel=0.0,
                                 seed=42)
        acc = _eval(dp_base, vc)
        accs_c.append(acc)
        print(f"       sigma_rel={sv*100:5.1f}%   acc={acc:.4f}")
    ax[2].plot([v * 100 for v in svt_vals], accs_c, "D-",
               color=PURPLE["dark"], lw=2, ms=5)
    _ax_setup(ax[2], r"$\sigma_{\rm rel}(V_T)$  (%)",
              r"D2D:  $V_T$ slope")

    # ------ (d) sigma_C2C sweep ------
    V_T_nom = dp_base.V_T_nom
    sc2c_mults = [0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0]
    accs_d = []
    print("  (d) sigma_C2C sweep:")
    for m in sc2c_mults:
        dp = replace(dp_base, sigma_c2c=m * V_T_nom)
        acc = _eval(dp, None)
        accs_d.append(acc)
        print(f"       sigma_C2C={m:4.2f} V_T   acc={acc:.4f}")
    ax[3].plot(sc2c_mults, accs_d, "^-",
               color=PURPLE["dark"], lw=2, ms=5)
    _ax_setup(ax[3], r"$\sigma_{\rm C2C}$  (multiples of $V_T$)",
              r"C2C noise")

    # ------ (e) p_max sweep ------
    pm_vals = [1.0, 0.95, 0.90, 0.85, 0.80, 0.72, 0.60, 0.55]
    accs_e = []
    print("  (e) p_max sweep:")
    for pm in pm_vals:
        dp = replace(dp_base, p_max=pm)
        acc = _eval(dp, None)
        accs_e.append(acc)
        print(f"       p_max={pm:.2f}   acc={acc:.4f}")
    ax[4].plot(pm_vals, accs_e, "v-",
               color=PURPLE["dark"], lw=2, ms=5)
    ax[4].axvline(0.72, color=PURPLE["accent"], ls="--", lw=1, alpha=0.7,
                  label="Device A AP$\\to$P")
    ax[4].legend(loc="lower left", frameon=False)
    ax[4].invert_xaxis()
    _ax_setup(ax[4], r"$p_{\rm max}$",
              r"back-hopping plateau")

    # ------ (f) combined: D2D + p_max + C2C ------
    # Fix D2D at sigma_V_th=5%, sigma_V_T=10%, sweep C2C at two p_max levels.
    vc_d2d = VariationConfig(mode="sigmoid_direct",
                              sigma_V_th_rel=0.05,
                              sigma_V_T_rel=0.10,
                              sigma_RP_rel=0.0,
                              sigma_TMR_rel=0.0,
                              seed=42)
    sc2c_fine = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]
    combined_rows = []
    print("  (f) combined sweep (D2D + p_max + C2C):")
    for pm, marker, label in [(1.0, "o", "$p_{\\rm max}=1.0$"),
                               (0.72, "s", "$p_{\\rm max}=0.72$")]:
        accs_f = []
        for m in sc2c_fine:
            dp = replace(dp_base, sigma_c2c=m * V_T_nom, p_max=pm)
            acc = _eval(dp, vc_d2d)
            accs_f.append(acc)
            combined_rows.append([pm, m, f"{acc:.6f}"])
            print(f"       p_max={pm:.2f} C2C={m:.1f}V_T   acc={acc:.4f}")
        ax[5].plot(sc2c_fine, accs_f, f"{marker}-",
                   color=PURPLE["dark"] if pm == 1.0 else PURPLE["accent"],
                   lw=2, ms=5, label=f"D2D + {label}")
    ax[5].legend(loc="lower left", frameon=False)
    _ax_setup(ax[5], r"$\sigma_{\rm C2C}$  (multiples of $V_T$)",
              "combined: D2D + plateau + C2C")

    fig.suptitle(
        "Non-ideality ablation: MNIST PBNN-MLP accuracy (FULL\\_STACK, "
        f"$T={T_eval}$)",
        fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = out_dir / "08b_nonideality_accuracy.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Part 2 saved: {out.relative_to(REPO)}")

    # Save per-sweep CSVs
    if run_dir is not None:
        import shutil
        _write_csv(run_dir / "sweep_a_joint_d2d.csv",
                   ["sigma_rel", "accuracy"],
                   [[v, f"{a:.6f}"] for v, a in zip(d2d_vals, accs_a)])
        _write_csv(run_dir / "sweep_b_vth.csv",
                   ["sigma_rel", "accuracy"],
                   [[v, f"{a:.6f}"] for v, a in zip(svth_vals, accs_b)])
        _write_csv(run_dir / "sweep_c_vt.csv",
                   ["sigma_rel", "accuracy"],
                   [[v, f"{a:.6f}"] for v, a in zip(svt_vals, accs_c)])
        _write_csv(run_dir / "sweep_d_c2c.csv",
                   ["sigma_c2c_mult", "accuracy"],
                   [[m, f"{a:.6f}"] for m, a in zip(sc2c_mults, accs_d)])
        _write_csv(run_dir / "sweep_e_pmax.csv",
                   ["p_max", "accuracy"],
                   [[pm, f"{a:.6f}"] for pm, a in zip(pm_vals, accs_e)])
        _write_csv(run_dir / "sweep_f_combined.csv",
                   ["p_max", "sigma_c2c_mult", "accuracy"],
                   combined_rows)
        shutil.copy2(out_dir / "08a_psw_nonideality_curves.png",
                     run_dir / "08a_psw_nonideality_curves.png")
        shutil.copy2(out, run_dir / "08b_nonideality_accuracy.png")
        print(f"  CSVs and figures copied to {run_dir}")


# =============================================================================#
# Main                                                                         #
# =============================================================================#

def main() -> None:
    from smtj_pbnn_sim.utils.io import make_run_dir

    out_dir = REPO / "figures"
    out_dir.mkdir(exist_ok=True)
    run_dir = make_run_dir("08_nonideality", base=REPO / "runs")

    print("=== Experiment 08: Non-ideality ablation ===")
    print()
    print("Part 1: P_sw curve visualisation ...")
    _part1_psw_curves(out_dir)
    print()
    print("Part 2: Accuracy ablation ...")
    _part2_accuracy_ablation(out_dir, run_dir=run_dir)
    print()
    print(f"Run directory: {run_dir}")
    print("Done.")


if __name__ == "__main__":
    main()
