"""MNIST data loaders for PBNN experiments."""

from __future__ import annotations

from pathlib import Path
import torch
from torch.utils.data import DataLoader
import torchvision
from torchvision import transforms


def get_mnist_loaders(
    root: str | Path = "./data/mnist",
    batch_size: int = 128,
    num_workers: int = 2,
    pin_memory: bool = True,
    download: bool = True,
) -> tuple[DataLoader, DataLoader]:
    """Return MNIST train and test DataLoaders.

    Args:
        root: Local root for the MNIST cache.
        batch_size: Mini-batch size for both splits.
        num_workers: DataLoader worker count.
        pin_memory: Pin memory for faster GPU transfer.
        download: Whether to download if missing.

    Returns:
        ``(train_loader, test_loader)``.
    """
    root = str(Path(root).expanduser())
    Path(root).mkdir(parents=True, exist_ok=True)

    # Standard MNIST normalization; images are flattened by the model.
    train_tf = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])
    test_tf = train_tf

    train_set = torchvision.datasets.MNIST(
        root=root, train=True, transform=train_tf, download=download)
    test_set = torchvision.datasets.MNIST(
        root=root, train=False, transform=test_tf, download=download)

    train_loader = DataLoader(
        train_set, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=pin_memory, drop_last=False)
    test_loader = DataLoader(
        test_set, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=pin_memory, drop_last=False)
    return train_loader, test_loader
