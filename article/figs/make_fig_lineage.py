"""
Draw Fig. 1.2 as a four-lane academic lineage diagram.

Top to bottom:
  1. recurrent / energy-based binary models (Ising -> ... -> DBN/DBM),
  2. the memoryless-sampling branches: optimization (simulated annealing),
     directed stochastic-binary (sigmoid belief net) and feedforward binary
     compute (BNN / PBNN),
  3. the shared p-bit / sMTJ sampling primitive, drawn in the middle as a hub,
  4. the stateful-dynamics branch: reservoir computing (ESN/LSM -> physical
     reservoir -> probabilistic-binary RC).

The primitive feeds two uses: memoryless Bernoulli sampling (upward, to the
optimization / inference models) and stateful telegraph dynamics (downward, to
the reservoir node). PBNN (memoryless) and probabilistic-binary RC (stateful)
sit on the same vertical axis with the shared device between them, so the
figure carries the "one device, two uses" reading. Reservoir computing is a
parallel, non-equilibrium paradigm joined to the rest only at the device, not
a chronological descendant of the energy-based lineage.
"""
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


INK = "#2E1F4D"
PURPLE = "#563A86"
PURPLE_MID = "#8467B1"
PURPLE_FILL = "#E9E2F3"
PURPLE_FAINT = "#F7F4FB"
ACCENT_FILL = "#EEE4D2"
GRAY = "#55515B"
RULE = "#D7D1E0"


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "mathtext.fontset": "dejavusans",
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def anchors(x, y, w, h):
    return {
        "left": (x, y + h / 2),
        "right": (x + w, y + h / 2),
        "top": (x + w / 2, y + h),
        "bottom": (x + w / 2, y),
        "center": (x + w / 2, y + h / 2),
    }


def box(
    ax,
    x,
    y,
    w,
    h,
    title,
    descriptor,
    year=None,
    fill=PURPLE_FILL,
    edge=PURPLE,
    title_size=10.8,
    descriptor_size=8.9,
    year_size=8.3,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.025,rounding_size=0.08",
        linewidth=1.12,
        edgecolor=edge,
        facecolor=fill,
        zorder=2,
    )
    ax.add_patch(patch)
    title_lines = title.count("\n") + 1
    title_y = 0.74 if year and title_lines > 1 else 0.70 if year else 0.65
    descriptor_y = 0.37 if year else 0.25

    ax.text(
        x + w / 2,
        y + h * title_y,
        title,
        ha="center",
        va="center",
        fontsize=title_size,
        color=INK,
        fontweight="semibold",
        linespacing=0.90,
        zorder=3,
    )
    ax.text(
        x + w / 2,
        y + h * descriptor_y,
        descriptor,
        ha="center",
        va="center",
        fontsize=descriptor_size,
        color=GRAY,
        style="italic",
        linespacing=0.96,
        zorder=3,
    )
    if year:
        ax.text(
            x + w / 2,
            y + h * 0.13,
            year,
            ha="center",
            va="center",
            fontsize=year_size,
            color=GRAY,
            style="italic",
            zorder=3,
        )
    return anchors(x, y, w, h)


def arrow(
    ax,
    start,
    end,
    label=None,
    dashed=False,
    rad=0.0,
    label_offset=(0.0, 0.0),
    label_size=8.2,
):
    relation = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=11.2,
        linewidth=1.18,
        linestyle=(0, (4.0, 2.3)) if dashed else "solid",
        color=PURPLE_MID if dashed else INK,
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=1,
        shrinkB=1,
        zorder=1,
    )
    ax.add_patch(relation)
    if label:
        x_mid = (start[0] + end[0]) / 2 + label_offset[0]
        y_mid = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(
            x_mid,
            y_mid,
            label,
            ha="center",
            va="center",
            fontsize=label_size,
            color=GRAY,
            linespacing=0.98,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.1},
            zorder=4,
        )


def lane_title(ax, y, title):
    ax.text(0.15, y + 0.13, title, fontsize=9.5, color=GRAY, fontweight="semibold")
    ax.plot([0.15, 13.00], [y, y], color=RULE, linewidth=0.78, zorder=0)


fig, ax = plt.subplots(figsize=(12.35, 7.95))
ax.set_xlim(0, 13.2)
ax.set_ylim(0, 9.45)
ax.axis("off")

lane_title(ax, 8.95, "Recurrent / energy-based binary models")
lane_title(ax, 6.78, "Memoryless sampling: optimization & inference")
lane_title(ax, 4.60, "Shared hardware sampling primitive")
lane_title(ax, 2.55, "Stateful dynamics: reservoir computing (temporal processing)")

# Lane 1 -- energy-based main line.
ising = box(ax, 0.22, 7.71, 1.42, 0.82, "Ising model", "binary energy", "1925", fill=PURPLE_FAINT)
hopfield = box(ax, 1.96, 7.71, 1.68, 0.82, "Hopfield\nnetwork", "attractor dynamics", "1982")
stoch_hopfield = box(
    ax, 3.98, 7.55, 1.98, 0.98, "Stochastic\nHopfield", "Glauber sampling",
    fill=ACCENT_FILL, edge=INK,
)
boltzmann = box(ax, 6.30, 7.55, 1.82, 0.98, "Boltzmann\nmachine", "hidden units + learning", "1985")
rbm = box(ax, 8.48, 7.55, 1.54, 0.98, "RBM", "harmonium", "1986")
dbn = box(ax, 10.36, 7.55, 1.58, 0.98, "DBN / DBM", "depth", "2006 / 2012", fill=PURPLE_FAINT)

arrow(ax, ising["right"], hopfield["left"], "energy\nneuron", label_offset=(0, 0.44))
arrow(ax, hopfield["right"], stoch_hopfield["left"], "thermal\nnoise", label_offset=(0, 0.44))
arrow(ax, stoch_hopfield["right"], boltzmann["left"], "learning\nmodel", label_offset=(0, 0.44))
arrow(ax, boltzmann["right"], rbm["left"], "bipartite", label_offset=(0, 0.44))
arrow(ax, rbm["right"], dbn["left"], "stack /\ndepth", label_offset=(0, 0.44))

# Lane 2 -- memoryless-sampling branches: optimization, directed stochastic
# binary units, modern feedforward binary compute and PBNN.
anneal = box(
    ax, 2.64, 5.48, 1.98, 0.88, "Simulated\nannealing", "temperature schedule", "1983",
    fill=PURPLE_FAINT, edge=PURPLE_MID, title_size=10.1,
)
sbn = box(
    ax, 5.04, 5.48, 1.92, 0.88, "Sigmoid\nbelief net", "directed binary units", "1992",
    fill=PURPLE_FAINT, edge=PURPLE_MID, title_size=10.0,
)
bnn = box(
    ax, 7.72, 5.48, 1.84, 0.88, "BNN", "feedforward\nXNOR + STE",
    fill=PURPLE_FILL, title_size=10.8,
)
pbnn = box(
    ax, 10.14, 5.28, 2.58, 1.08, "PBNN", "Bernoulli binary weights\nlayerwise sampling", "2018",
    fill=ACCENT_FILL, edge=INK, title_size=11.3, descriptor_size=8.7,
)

arrow(ax, stoch_hopfield["bottom"], anneal["top"], "optimization\nbranch", dashed=True, rad=0.16, label_offset=(-0.62, -0.42))
arrow(ax, boltzmann["bottom"], sbn["top"], "directed\ncounterpart", dashed=True, rad=0.10, label_offset=(0.02, -0.42))
arrow(ax, bnn["right"], pbnn["left"])
arrow(ax, sbn["right"], pbnn["bottom"], "directed\nstochastic semantics", dashed=True, rad=-0.26, label_offset=(0.12, -0.52), label_size=8.0)

# Lane 3 (middle) -- shared hardware sampling primitive. The same device feeds
# the memoryless-sampling branches above and the stateful reservoir below.
primitive = FancyBboxPatch(
    (0.34, 3.50),
    12.48,
    0.96,
    boxstyle="round,pad=0.025,rounding_size=0.08",
    linewidth=1.06,
    edgecolor=PURPLE,
    facecolor=PURPLE_FAINT,
    zorder=0,
)
ax.add_patch(primitive)
ax.text(
    0.58, 4.16, "p-bit / sMTJ", fontsize=10.6, color="white", fontweight="semibold",
    ha="left", va="center",
    bbox={"boxstyle": "round,pad=0.26,rounding_size=0.06", "facecolor": PURPLE, "edgecolor": PURPLE},
)
ax.text(2.70, 4.16, r"$P(s_i=+1\mid I_i)=\sigma(2\beta I_i)$", fontsize=11.0, color=INK, ha="left", va="center")
ax.text(6.05, 4.16, "shared local Sigmoid sampling primitive", fontsize=9.3, color=GRAY, ha="left", va="center")

# Second row inside the strip: the two complementary uses of the same device.
ax.text(0.58, 3.74, "memoryless sampling", fontsize=8.4, color=PURPLE, fontweight="semibold", ha="left", va="center")
ax.text(2.78, 3.74, r"$w_{ij}\sim\mathrm{Bern}(\sigma(\theta_{ij}))$   (Ising / PBNN)", fontsize=8.5, color=GRAY, ha="left", va="center")
ax.text(7.20, 3.74, "stateful dynamics", fontsize=8.4, color=PURPLE, fontweight="semibold", ha="left", va="center")
ax.text(9.18, 3.74, r"$\tau(V)$ as fading memory   (reservoir)", fontsize=8.5, color=GRAY, ha="left", va="center")

# Lane 4 -- stateful-dynamics branch: reservoir computing. A parallel,
# non-equilibrium paradigm joined to the rest only at the device level.
esn = box(
    ax, 2.64, 1.15, 2.10, 0.98, "ESN / LSM", "fixed reservoir,\ntrained readout", "2001 / 2002",
    fill=PURPLE_FAINT, edge=PURPLE_MID, title_size=10.2,
)
phys_rc = box(
    ax, 5.30, 1.15, 2.80, 0.98, "Physical reservoir", "photonic, memristive,\nspintronic media", "2011 → 2017",
    fill=PURPLE_FILL, title_size=10.4, descriptor_size=8.4,
)
pb_rc = box(
    ax, 10.14, 1.05, 2.58, 1.08, "Probabilistic\nbinary RC", "sMTJ telegraph node,\nrelaxation as memory", "this work",
    fill=ACCENT_FILL, edge=INK, title_size=11.0, descriptor_size=8.6,
)

arrow(ax, esn["right"], phys_rc["left"], "physical\nsubstrate", label_offset=(0, 0.42))
arrow(ax, phys_rc["right"], pb_rc["left"], "stochastic node\nvs. deterministic\noscillator", label_offset=(0.02, 0.40), label_size=7.8)

# Same-device coupling. Dashed = implementation compatibility, not descent.
# Upward: memoryless sampling feeds the optimization / inference branches.
for x_pos, y_top in [(3.63, 5.48), (6.00, 5.48), (11.43, 5.28)]:
    ax.plot(
        [x_pos, x_pos], [4.46, y_top],
        color=PURPLE_MID, linewidth=0.86, linestyle=(0, (3.0, 2.2)), alpha=0.82, zorder=0,
    )
# Downward: stateful dynamics feeds the reservoir node (same vertical axis as PBNN).
ax.plot(
    [11.43, 11.43], [2.13, 3.50],
    color=PURPLE_MID, linewidth=0.98, linestyle=(0, (3.0, 2.2)), alpha=0.92, zorder=0,
)

# Compact legend.
legend_y = 0.42
ax.add_patch(
    FancyArrowPatch((7.74, legend_y), (8.26, legend_y), arrowstyle="-|>", mutation_scale=9.4, linewidth=1.15, color=INK)
)
ax.text(8.36, legend_y, "chronological / structural path", fontsize=8.3, color=GRAY, va="center")
ax.add_patch(
    FancyArrowPatch((11.00, legend_y), (11.52, legend_y), arrowstyle="-|>", mutation_scale=9.4, linewidth=1.15, linestyle=(0, (4.0, 2.3)), color=PURPLE_MID)
)
ax.text(11.62, legend_y, "conceptual / device-sharing link", fontsize=8.3, color=GRAY, va="center")

out_dir = Path(__file__).resolve().parent
png_path = out_dir / "Chapter01_local_02.png"
pdf_path = out_dir / "fig_lineage.pdf"
fig.savefig(png_path, dpi=320, bbox_inches="tight", facecolor="white")
fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
# keep the legacy filename in sync for any external references
fig.savefig(out_dir / "fig_lineage.png", dpi=320, bbox_inches="tight", facecolor="white")
print(f"saved {png_path.name}")
print(f"saved {pdf_path.name}")
