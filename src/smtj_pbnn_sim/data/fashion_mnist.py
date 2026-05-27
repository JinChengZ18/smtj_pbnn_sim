"""Fashion-MNIST data loaders for PBNN-CNN experiments.

Mirrors the MNIST loader API. Fashion-MNIST is a drop-in replacement for
MNIST (28x28 grayscale, 10 classes, 60K/10K split) on substantially
harder content (clothing items rather than digits). Baseline accuracy is
~5 percentage points below MNIST on the same MLP, making it a clean
intermediate between MNIST and natural-image datasets while preserving
the existing data pipeline.
"""

from __future__ import annotations

from pathlib import Path

import torchvision
from torch.utils.data import DataLoader
from torchvision import transforms


# Channel mean/std from the Fashion-MNIST training set
FASHION_MNIST_MEAN = (0.2860,)
FASHION_MNIST_STD = (0.3530,)


def get_fashion_mnist_loaders(
    root: str | Path = "./data/fashion_mnist",
    batch_size: int = 128,
    num_workers: int = 2,
    pin_memory: bool = True,
    download: bool = True,
) -> tuple[DataLoader, DataLoader]:
    """Return Fashion-MNIST train and test DataLoaders.

    Args:
        root: Local root for the Fashion-MNIST cache.
        batch_size: Mini-batch size for both splits.
        num_workers: DataLoader worker count.
        pin_memory: Pin memory for faster GPU transfer.
        download: Whether to download if missing.

    Returns:
        ``(train_loader, test_loader)``.
    """
    root = str(Path(root).expanduser())
    Path(root).mkdir(parents=True, exist_ok=True)

    train_tf = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(FASHION_MNIST_MEAN, FASHION_MNIST_STD),
    ])
    test_tf = train_tf

    train_set = torchvision.datasets.FashionMNIST(
        root=root, train=True, transform=train_tf, download=download)
    test_set = torchvision.datasets.FashionMNIST(
        root=root, train=False, transform=test_tf, download=download)

    train_loader = DataLoader(
        train_set, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=pin_memory, drop_last=False)
    test_loader = DataLoader(
        test_set, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=pin_memory, drop_last=False)
    return train_loader, test_loader
