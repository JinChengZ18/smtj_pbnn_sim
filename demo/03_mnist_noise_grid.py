"""Demo 03: visualize each Experiment 07 noise type on a real MNIST digit.

Produces a 2x4 grid showing how each input-level perturbation distorts
the same input image.

Output: demo/figures/03_mnist_noise_grid.png
"""

from __future__ import annotations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load_mnist_sample(target_digit=7):
    """Try to load an MNIST sample; fallback to synthetic glyph."""
    try:
        import numpy as np
        import torchvision
        ds = torchvision.datasets.MNIST(
            root=str(REPO / "data" / "mnist"), train=False, download=False)
        for img, lbl in ds:
            if lbl == target_digit:
                return np.array(img, dtype=float) / 255.0, lbl
    except Exception:
        pass
    import numpy as np
    img = np.zeros((28, 28))
    img[5:8, 5:23] = 1.0
    for i, j in zip(range(7, 26), range(22, 7, -1)):
        if 0 <= i < 28 and 0 <= j < 28:
            img[i, max(j - 1, 0):j + 1] = 1.0
    return img, target_digit


def _gaussian_noise(x, sigma):
    import torch
    return x + sigma * torch.randn_like(x)


def _salt_pepper(x, frac):
    import torch
    out = x.clone()
    mask = torch.rand_like(x)
    out[mask < frac / 2] = 0.0
    out[(mask >= frac / 2) & (mask < frac)] = 1.0
    return out


def _speckle(x, sigma):
    import torch
    return x * (1.0 + sigma * torch.randn_like(x))


def _gaussian_blur(x, sigma):
    import torch
    if sigma <= 0:
        return x
    k = max(3, int(2 * round(3 * sigma) + 1))
    coords = torch.arange(k, dtype=x.dtype) - (k - 1) / 2
    g = torch.exp(-(coords ** 2) / (2 * sigma * sigma))
    g = g / g.sum()
    g_h = g.view(1, 1, 1, k); g_v = g.view(1, 1, k, 1)
    x = torch.nn.functional.conv2d(x, g_h, padding=(0, k // 2))
    x = torch.nn.functional.conv2d(x, g_v, padding=(k // 2, 0))
    return x


def _cutout(x, size):
    import torch
    if size <= 0:
        return x
    out = x.clone()
    B, C, H, W = out.shape
    for b in range(B):
        cy = torch.randint(0, H, (1,)).item()
        cx = torch.randint(0, W, (1,)).item()
        y0 = max(0, cy - size // 2); y1 = min(H, cy + size // 2)
        x0 = max(0, cx - size // 2); x1 = min(W, cx + size // 2)
        out[b, :, y0:y1, x0:x1] = 0.0
    return out


def _brightness(x, b):
    return (x + b).clamp(0.0, 1.0)


def _pgd_like(x, eps):
    """Sign-aligned random ε pattern as a visual proxy for PGD."""
    import torch
    pattern = torch.sign(torch.randn_like(x))
    return (x + eps * pattern).clamp(0.0, 1.0)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import torch

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 13,
        "savefig.bbox": "tight",
    })

    PURPLE_DARK = "#4B1369"

    primary_img, primary_label = _load_mnist_sample(target_digit=7)

    def _to_tensor(img):
        return torch.from_numpy(np.asarray(img, dtype=np.float32))[None, None]

    def _to_np(t):
        return t[0, 0].cpu().numpy()

    x = _to_tensor(primary_img)
    torch.manual_seed(42)
    noisy = {
        "Original":
            primary_img,
        r"Gaussian, $\sigma$ = 0.5":
            _to_np(_gaussian_noise(x.clone(), 0.5)),
        "Salt-and-pepper, f = 0.20":
            _to_np(_salt_pepper(x.clone(), 0.20)),
        r"Speckle, $\sigma$ = 0.5":
            _to_np(_speckle(x.clone(), 0.5)),
        r"Gaussian blur, $\sigma$ = 1.5":
            _to_np(_gaussian_blur(x.clone(), 1.5)),
        "Cutout, 14 × 14 px":
            _to_np(_cutout(x.clone(), 14)),
        "Brightness, +0.3":
            _to_np(_brightness(x.clone(), 0.3)),
        r"PGD-like, $\epsilon$ = 0.1":
            _to_np(_pgd_like(x.clone(), 0.1)),
    }

    # Tighter 2x4 grid, no separate title row — title goes via suptitle
    fig, axes = plt.subplots(2, 4, figsize=(15, 8.5))

    keys = list(noisy.keys())
    for idx, key in enumerate(keys):
        row = idx // 4
        col = idx % 4
        ax = axes[row, col]
        ax.imshow(noisy[key], cmap="gray_r", vmin=0, vmax=1,
                  interpolation="nearest")
        ax.set_xticks([])
        ax.set_yticks([])
        if key == "Original":
            for spine in ax.spines.values():
                spine.set_edgecolor(PURPLE_DARK)
                spine.set_linewidth(2.5)
        else:
            for spine in ax.spines.values():
                spine.set_edgecolor("#9CA3AF")
                spine.set_linewidth(1.0)
        ax.set_title(key, fontsize=14,
                     color=PURPLE_DARK,
                     fontweight="bold" if key == "Original" else "normal",
                     pad=8)

    fig.suptitle(
        f"Input perturbations applied to one MNIST digit "
        f"(label = {primary_label})",
        fontsize=20, fontweight="bold", color=PURPLE_DARK, y=1.02)

    fig.text(0.5, 0.015,
             "(g) weight perturbation and full PGD-10 are model-level effects "
             "and are not visualised here; the (h) panel shows a sign-aligned "
             r"$\epsilon$ pattern as a visual proxy.",
             ha="center", va="bottom", fontsize=11, style="italic",
             color="#444")

    plt.subplots_adjust(top=0.92, bottom=0.06, left=0.03, right=0.97,
                         wspace=0.10, hspace=0.18)

    out_path = REPO / "demo" / "figures" / "03_mnist_noise_grid.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    print(f"Saved: {out_path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
