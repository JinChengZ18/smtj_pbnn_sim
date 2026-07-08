"""Demo 01: simulator framework diagram.

Block-and-arrow visualization of the 6-layer architecture:
    Device -> Array -> Network -> Sampling -> PPA -> Experiment

with side panels showing principal data inputs and produced artifacts.

Output: demo/figures/01_simulator_framework.png

Run:  python demo/01_simulator_framework.py
"""

from __future__ import annotations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 13,
        "axes.linewidth": 0.0,
        "savefig.bbox": "tight",
    })

    # Color palette
    PURPLE_DARK   = "#4B1369"
    PURPLE_MED    = "#6E2C91"
    PURPLE_LIGHT  = "#A97DBE"
    ORANGE        = "#D97706"
    GREEN         = "#0E8A6F"
    GRAY          = "#6B7280"
    LIGHT_GRAY    = "#E5E7EB"
    HEADER_COLOR  = "#1F2937"   # dark slate, high-contrast (not gray)

    fig = plt.figure(figsize=(16, 11))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 11)
    ax.set_aspect("equal")
    ax.axis("off")

    # ---- Layer boxes (vertical stack) ----
    # Module labels use the actual source identifiers so the block diagram
    # doubles as a module map (matches the numbered article asset). The figure
    # carries no in-figure title -- the caption supplies it.
    layers = [
        (8.4, "Device",
         "tmr · variation · calibration · llg",
         r"compact $P_\mathrm{sw}(V, t_p)$ + Néel–Brown bridge",
         PURPLE_DARK),
        (6.8, "Array",
         "crossbar · periphery · tile · ir_drop",
         "XNOR-popcount column current sum, DAC + counter",
         PURPLE_MED),
        (5.2, "Network",
         "pbnn_linear · ste · clt · bn · losses",
         "torch nn.Modules · STE backward · CLT forward",
         PURPLE_LIGHT),
        (3.6, "Sampling",
         "bernoulli_smtj · unfold · schedules",
         r"T-step Bernoulli accumulator · $\beta$ / T schedules",
         GREEN),
        (2.0, "PPA",
         "energy · latency · area · training_energy",
         "per-MAC energy, T-scaling, MRAM baseline",
         ORANGE),
        (0.4, "Experiment",
         "train · inference · uncertainty",
         "noise · bit-flip · landscape · energy",
         "#374151"),
    ]

    box_w, box_h = 7.0, 1.30
    box_x = 4.5  # leaves room for INPUTS column on left, OUTPUTS on right

    for (y, name, modules, purpose, color) in layers:
        box = FancyBboxPatch((box_x, y), box_w, box_h,
                              boxstyle="round,pad=0.04,rounding_size=0.15",
                              facecolor=color, edgecolor="white",
                              linewidth=2, alpha=0.94)
        ax.add_patch(box)
        # Layer label (left tab)
        ax.text(box_x + 0.22, y + box_h - 0.30, name,
                ha="left", va="top", color="white",
                fontsize=16, fontweight="bold")
        # Modules (top right of box)
        ax.text(box_x + box_w - 0.22, y + box_h - 0.32, modules,
                ha="right", va="top", color="white",
                fontsize=11, family="monospace", alpha=0.96)
        # Purpose
        ax.text(box_x + 0.22, y + 0.18, purpose,
                ha="left", va="bottom", color="white",
                fontsize=11.5, alpha=0.95)

    # ---- Vertical arrows between layers ----
    for i in range(len(layers) - 1):
        y_from = layers[i][0]
        y_to = layers[i + 1][0] + box_h
        arrow = FancyArrowPatch(
            (box_x + box_w / 2, y_from),
            (box_x + box_w / 2, y_to),
            arrowstyle="-|>", mutation_scale=20,
            color=PURPLE_DARK, linewidth=1.8,
            connectionstyle="arc3,rad=0", zorder=1)
        ax.add_patch(arrow)

    # ---- LEFT side: Inputs ----
    # Title placed ABOVE the input boxes (no overlap), strong dark color
    ax.text(2.05, 9.85, "INPUTS", ha="center", va="bottom",
            fontsize=14, fontweight="bold", color=HEADER_COLOR)
    ax.plot([0.45, 3.65], [9.78, 9.78], color=HEADER_COLOR, lw=1.2)

    # Measurement box
    meas_box = FancyBboxPatch((0.45, 7.95), 3.20, 1.55,
                               boxstyle="round,pad=0.04,rounding_size=0.10",
                               facecolor=LIGHT_GRAY, edgecolor=PURPLE_DARK,
                               linewidth=1.4)
    ax.add_patch(meas_box)
    ax.text(2.05, 8.95, "Device Measurements",
            ha="center", va="center", fontsize=15, fontweight="bold",
            color=PURPLE_DARK)
    ax.text(2.05, 8.30,
            r"$P_\mathrm{sw}(V)$ curves",
            ha="center", va="center", fontsize=12,
            color="#444", style="italic")
    arrow_in = FancyArrowPatch((3.65, 8.72), (box_x, 8.95),
                                arrowstyle="-|>", mutation_scale=16,
                                color=PURPLE_DARK, linewidth=1.4)
    ax.add_patch(arrow_in)
    ax.text(4.05, 9.05, "fit", ha="center", va="bottom",
            fontsize=15, color=PURPLE_DARK, style="italic")

    # Datasets box
    data_box = FancyBboxPatch((0.45, 4.40), 3.20, 1.55,
                               boxstyle="round,pad=0.04,rounding_size=0.10",
                               facecolor=LIGHT_GRAY, edgecolor=PURPLE_LIGHT,
                               linewidth=1.4)
    ax.add_patch(data_box)
    ax.text(2.05, 5.40, "Datasets",
            ha="center", va="center", fontsize=15, fontweight="bold",
            color=PURPLE_DARK)
    ax.text(2.05, 4.75,
            "MNIST  ·  UCI tabular suite",
            ha="center", va="center", fontsize=12,
            color="#444")
    arrow_data = FancyArrowPatch((3.65, 5.18), (box_x, 5.55),
                                  arrowstyle="-|>", mutation_scale=16,
                                  color=PURPLE_LIGHT, linewidth=1.4)
    ax.add_patch(arrow_data)
    ax.text(4.05, 5.55, r"$x, y$", ha="center", va="bottom",
            fontsize=15, color=PURPLE_LIGHT, style="italic")

    # ---- RIGHT side: Outputs ----
    # Title placed ABOVE the output column (no overlap)
    ax.text(13.85, 9.85, "OUTPUTS", ha="center", va="bottom",
            fontsize=14, fontweight="bold", color=HEADER_COLOR)
    ax.plot([12.20, 15.50], [9.78, 9.78], color=HEADER_COLOR, lw=1.2)

    out_items = [
        (8.4, "calibrated YAML\ndevice config",       PURPLE_DARK),
        (6.8, "CIM tile area\n+ per-MAC energy",      PURPLE_MED),
        (5.2, "trained checkpoint\nand binary weights", PURPLE_LIGHT),
        (3.6, "T-step inference\naccuracy curves",    GREEN),
        (2.0, "PPA breakdown\nfwd / bwd / write",     ORANGE),
        (0.4, "result figures\nand run logs",         "#374151"),
    ]
    out_x = 12.20
    out_w = 3.30
    for y, label, color in out_items:
        out_box = FancyBboxPatch((out_x, y + 0.05), out_w, box_h - 0.10,
                                  boxstyle="round,pad=0.04,rounding_size=0.10",
                                  facecolor="white", edgecolor=color,
                                  linewidth=1.6)
        ax.add_patch(out_box)
        ax.text(out_x + out_w / 2, y + box_h / 2, label,
                ha="center", va="center", fontsize=11.5,
                color=color, fontweight="bold")
        # Output arrow
        arrow_out = FancyArrowPatch((box_x + box_w, y + box_h / 2),
                                     (out_x, y + box_h / 2),
                                     arrowstyle="-|>", mutation_scale=14,
                                     color=color, linewidth=1.2, alpha=0.85)
        ax.add_patch(arrow_out)


    out_path = REPO / "demo" / "figures" / "01_simulator_framework.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight",
                facecolor="white")
    print(f"Saved: {out_path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
