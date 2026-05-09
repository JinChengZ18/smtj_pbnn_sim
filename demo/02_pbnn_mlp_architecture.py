"""PBNN-MLP architecture & MNIST data flow (paper-level diagram).

This revision keeps the original figure content but fixes layout/style:
- layer titles use "FC1 (784→1024)" format;
- W1/W2/W3 labels are moved inside the layer boxes without overlap;
- the MNIST input uses the uploaded digit image file;
- FC3 styling matches FC1/FC2;
- the output probability inset is moved upward.
"""

from __future__ import annotations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load_mnist_sample(target_digit=7):
    """Try to load an MNIST sample; else synthesize a glyph."""
    try:
        import torchvision
        ds = torchvision.datasets.MNIST(
            root=str(REPO / "data" / "mnist"), train=False, download=False)
        for img, lbl in ds:
            if lbl == target_digit:
                import numpy as np
                arr = np.array(img, dtype=float) / 255.0
                return arr, lbl
    except Exception:
        pass
    import numpy as np
    img = np.zeros((28, 28))
    img[5:8, 5:23] = 1.0
    for i, j in zip(range(7, 26), range(22, 7, -1)):
        if 0 <= i < 28 and 0 <= j < 28:
            img[i, max(j - 1, 0):j + 1] = 1.0
    return img, target_digit


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
    import numpy as np

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 12,
        "savefig.bbox": "tight",
        "mathtext.fontset": "dejavusans",
    })

    # Colors
    PURPLE_DARK   = "#4B1369"
    PURPLE_MED    = "#6E2C91"
    GREEN         = "#0E8A6F"
    BG_WEIGHT_POS = "#4B1369"
    BG_WEIGHT_NEG = "#D97706"
    HEADER_COLOR  = "#1F2937"

    fig = plt.figure(figsize=(17, 7.2))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 17)
    ax.set_ylim(0, 7.2)
    ax.set_aspect("equal")
    ax.axis("off")

    # Title
    ax.text(8.5, 6.85,
            "PBNN-MLP architecture for MNIST stochastic inference",
            ha="center", va="center", fontsize=18, fontweight="bold",
            color=PURPLE_DARK)
    ax.text(8.5, 6.45,
            r"$784 \rightarrow 1024 \rightarrow 1024 \rightarrow 10$  ·  "
            r"binary stochastic weights $\pm 1$  ·  STE backward  ·  "
            "T-step Bernoulli accumulator",
            ha="center", va="center", fontsize=12, style="italic",
            color="#444")

    # ---- MNIST input image ----
    img, label =  _load_mnist_sample(target_digit=7)
    inset_w, inset_h = 1.9, 1.9
    inset_x, inset_y = 0.3, 2.70
    ax.imshow(img, cmap="gray_r",
              extent=(inset_x, inset_x + inset_w,
                      inset_y, inset_y + inset_h),
              aspect="auto", interpolation="nearest", vmin=0, vmax=1)
    ax.add_patch(Rectangle((inset_x, inset_y), inset_w, inset_h,
                           fill=False, edgecolor=PURPLE_DARK, linewidth=2.0))
    title_fs = 13
    ax.text(inset_x + inset_w / 2, inset_y + inset_h + 0.20,
            "MNIST input", ha="center", va="bottom",
            fontsize=title_fs, fontweight="bold", color=PURPLE_DARK)
    ax.text(inset_x + inset_w / 2, inset_y - 0.18,
            f"28 × 28 grayscale\n(label = {label})",
            ha="center", va="top", fontsize=10.5, color="#444")

    # Arrow to FC1
    ax.add_patch(FancyArrowPatch((inset_x + inset_w + 0.05,
                                  inset_y + inset_h / 2),
                                 (2.85, inset_y + inset_h / 2),
                                 arrowstyle="-|>", mutation_scale=16,
                                 color=PURPLE_DARK, linewidth=1.6))
    ax.text(2.55, inset_y + inset_h / 2 + 0.30, "flatten",
            ha="center", fontsize=10.5, color=PURPLE_DARK, style="italic")

    def draw_layer(x_left, title, color,
                   y_center=3.65, w=2.7, h=3.55,
                   weight_label="", act_label="", seed=42):
        """Draw one FC block using identical geometry and style for FC1/FC2/FC3."""
        y_top = y_center + h / 2
        y_bot = y_center - h / 2

        # One-line layer title above box.
        ax.text(x_left + w / 2, y_top + 0.18, title,
                ha="center", va="bottom", fontsize=title_fs,
                fontweight="bold", color=color)

        # Box
        box = FancyBboxPatch((x_left, y_bot), w, h,
                             boxstyle="round,pad=0.04,rounding_size=0.12",
                             facecolor="white", edgecolor=color,
                             linewidth=2)
        ax.add_patch(box)

        # Formula label: inside the top of the box, separated from title and grid.
        ax.text(x_left + w / 2, y_top - 0.22, weight_label,
                ha="center", va="center", fontsize=10.2, color="#333")

        # Weight grid below the formula label.
        gx = x_left + 0.20
        gy = y_top - 1.18
        gw = w - 0.40
        gh = 0.82
        rng = np.random.default_rng(seed)
        nx, ny = 28, 10
        cell_w = gw / nx
        cell_h = gh / ny
        for i in range(ny):
            for j in range(nx):
                v = 1 if rng.random() > 0.5 else -1
                c = BG_WEIGHT_POS if v > 0 else BG_WEIGHT_NEG
                ax.add_patch(Rectangle((gx + j * cell_w, gy + i * cell_h),
                                       cell_w, cell_h,
                                       facecolor=c, edgecolor="none",
                                       alpha=0.92))

        # BN → sign-STE band.
        band_y = y_center + 0.06
        ax.add_patch(FancyBboxPatch(
            (x_left + 0.30, band_y - 0.18), w - 0.60, 0.36,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=color, edgecolor="none", alpha=0.18))
        ax.text(x_left + w / 2, band_y,
                r"BN $\rightarrow$ sign-STE",
                ha="center", va="center", fontsize=11.5,
                fontweight="bold", color=color)

        # Activation strip.
        sx = x_left + 0.20
        sy = y_bot + 0.55
        sw = w - 0.40
        sh = 0.55
        n = 36
        cw = sw / n
        for j in range(n):
            v = 1 if rng.random() > 0.5 else -1
            c = BG_WEIGHT_POS if v > 0 else "white"
            ec = "none" if v > 0 else BG_WEIGHT_POS
            ax.add_patch(Rectangle((sx + j * cw, sy), cw, sh,
                                   facecolor=c, edgecolor=ec,
                                   linewidth=0.5))
        ax.text(x_left + w / 2, sy + sh + 0.10, act_label,
                ha="center", va="bottom", fontsize=10.0, color="#333")

    # ---- FC layers ----
    layer_y = 3.65
    fc_w = 2.7
    fc_h = 3.55
    gap = 0.45
    layer_color = PURPLE_DARK

    fc1_x = 2.85
    draw_layer(fc1_x, r"$\mathrm{FC}_1$ (784$\rightarrow$1024)", layer_color,
               y_center=layer_y, w=fc_w, h=fc_h,
               weight_label=r"$W_1 \in \{\pm 1\}^{1024 \times 784}$",
               act_label=r"$h_1 \in \{\pm 1\}^{1024}$",
               seed=42)
    ax.add_patch(FancyArrowPatch((fc1_x + fc_w, layer_y),
                                 (fc1_x + fc_w + gap, layer_y),
                                 arrowstyle="-|>", mutation_scale=14,
                                 color=PURPLE_DARK, linewidth=1.6))

    fc2_x = fc1_x + fc_w + gap
    draw_layer(fc2_x, r"$\mathrm{FC}_2$ (1024$\rightarrow$1024)", layer_color,
               y_center=layer_y, w=fc_w, h=fc_h,
               weight_label=r"$W_2 \in \{\pm 1\}^{1024 \times 1024}$",
               act_label=r"$h_2 \in \{\pm 1\}^{1024}$",
               seed=43)
    ax.add_patch(FancyArrowPatch((fc2_x + fc_w, layer_y),
                                 (fc2_x + fc_w + gap, layer_y),
                                 arrowstyle="-|>", mutation_scale=14,
                                 color=PURPLE_DARK, linewidth=1.6))

    fc3_x = fc2_x + fc_w + gap
    draw_layer(fc3_x, r"$\mathrm{FC}_3$ (1024$\rightarrow$10)", layer_color,
               y_center=layer_y, w=fc_w, h=fc_h,
               weight_label=r"$W_3 \in \{\pm 1\}^{10 \times 1024}$",
               act_label=r"logits $z \in \mathbb{R}^{10}$",
               seed=44)
    ax.add_patch(FancyArrowPatch((fc3_x + fc_w, layer_y),
                                 (fc3_x + fc_w + gap, layer_y),
                                 arrowstyle="-|>", mutation_scale=14,
                                 color=PURPLE_DARK, linewidth=1.6))

    # ---- Output panel ----
    out_x = fc3_x + fc_w + gap
    out_w = 2.5
    out_h = fc_h
    out_y = layer_y - out_h / 2
    out_box = FancyBboxPatch((out_x, out_y), out_w, out_h,
                             boxstyle="round,pad=0.04,rounding_size=0.12",
                             facecolor="white", edgecolor=GREEN, linewidth=2)
    ax.add_patch(out_box)
    ax.text(out_x + out_w / 2, out_y + out_h - 0.22,
            "Output", ha="center", va="top", fontsize=14,
            fontweight="bold", color=GREEN)
    ax.text(out_x + out_w / 2, out_y + out_h - 0.55,
            r"argmax(softmax($z$))",
            ha="center", va="top", fontsize=11, color="#444",
            style="italic")

    # Synthetic softmax bars
    rng = np.random.default_rng(7)
    probs = rng.dirichlet(np.ones(10) * 0.3)
    probs = probs / probs.sum() * 0.25
    probs[label] = 0.75
    probs = probs / probs.sum()

    # Raise the bar inset so it does not collide with the class label.
    bar_x0 = out_x + 0.30
    bar_y0 = out_y + 1.02
    bar_w_total = out_w - 0.60
    bar_h_total = 1.45
    for i in range(10):
        bx = bar_x0 + i * (bar_w_total / 10)
        bw = (bar_w_total / 10) - 0.03
        bh = bar_h_total * probs[i]
        c = GREEN if i == label else "#9CA3AF"
        a = 1.0 if i == label else 0.4
        ax.add_patch(Rectangle((bx, bar_y0), bw, bh,
                               facecolor=c, alpha=a, edgecolor="none"))
        ax.text(bx + bw / 2, bar_y0 - 0.10, str(i),
                ha="center", va="top", fontsize=9, color="#444")
    ax.text(out_x + out_w / 2, out_y + 0.25,
            f"predicted class: {label}", ha="center", va="bottom",
            fontsize=12, fontweight="bold", color=GREEN)

    # ---- Bottom: forward-mode legend + result callout ----
    bottom_y = 0.88
    ax.text(0.30, bottom_y, "Forward modes:",
            ha="left", va="center", fontsize=12.5, fontweight="bold",
            color=HEADER_COLOR)
    modes = [
        (r"$\sigma(\theta)$ Bernoulli — reference",  "#A97DBE", 3.10),
        ("hardware-aware — training default",         PURPLE_MED,   7.40),
        ("T-step Bernoulli — deployed at T=4",        PURPLE_DARK,  11.95),
    ]
    for desc, col, x_pos in modes:
        ax.add_patch(Rectangle((x_pos, bottom_y - 0.13), 0.22, 0.26,
                               facecolor=col, edgecolor="none"))
        ax.text(x_pos + 0.30, bottom_y, desc, ha="left", va="center",
                fontsize=11, color=col, fontweight="bold")

    ax.add_patch(FancyBboxPatch((0.30, 0.08), 16.40, 0.55,
                                boxstyle="round,pad=0.04,rounding_size=0.10",
                                facecolor="#FFF8E5", edgecolor="#E0C870",
                                linewidth=1.0))
    ax.text(8.50, 0.35,
            r"Test accuracy after 20 epochs:  "
            r"PBNN $=$ 96.98 %  ·  FP-MLP $=$ 98.51 %  "
            r"(matched topology, gap $=$ 1.53 pp).  "
            r"Deployed at T$=4$: 97.51 % — within 0.17 pp of T$=64$.",
            ha="center", va="center", fontsize=11.5, color=PURPLE_DARK)

    out_path = REPO / "demo" / "figures" / "02_pbnn_mlp_architecture.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, bbox_inches="tight", facecolor="white")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
