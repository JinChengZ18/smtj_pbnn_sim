"""CIFAR-10 data loaders for PBNN-CNN experiments.

Reads CIFAR-10 from the Hugging Face ``uoft-cs/cifar10`` mirror's parquet
files (``train-00000-of-00001.parquet`` and
``test-00000-of-00001.parquet``) under ``<root>/`` instead of the
canonical ``cifar-10-batches-py`` tar.gz. This avoids the unreachable
Toronto mirror in the canonical torchvision download path while still
exposing the same ``(train_loader, test_loader)`` API used by the
experiment scripts.

Parquet schema (HuggingFace ``uoft-cs/cifar10``, ``plain_text`` config):
  - ``img``: dict ``{"bytes": <PNG-encoded bytes>, "path": None}``
  - ``label``: int in [0, 9]

The first __getitem__ access decodes the PNG to a PIL.Image lazily.
For 50K train + 10K test images at 32x32, the in-memory parquet table
takes ~180MB; we keep it as an in-process Python list of (PIL.Image,
label) pairs after one decode pass to amortise PNG decoding cost across
epochs.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from PIL import Image
import torch
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms


CIFAR10_MEAN = (0.4914, 0.4822, 0.4465)
CIFAR10_STD = (0.2470, 0.2435, 0.2616)


class CIFAR10Parquet(Dataset):
    """CIFAR-10 dataset backed by the HuggingFace parquet files.

    Parameters
    ----------
    root : path-like
        Directory containing ``train.parquet`` and ``test.parquet``.
    train : bool
        If True load the training split (50000), else test split (10000).
    transform : callable, optional
        Torchvision transform applied to each PIL.Image on __getitem__.
    """

    def __init__(self, root: str | Path, *, train: bool = True,
                 transform: Optional[callable] = None):
        try:
            import pyarrow.parquet as pq
        except ImportError as e:
            raise ImportError(
                "CIFAR10Parquet requires pyarrow. Install with: "
                "pip install pyarrow") from e

        root = Path(root).expanduser()
        fname = "train.parquet" if train else "test.parquet"
        path = root / fname
        if not path.exists():
            raise FileNotFoundError(
                f"CIFAR-10 parquet not found at {path}. Download from "
                "https://hf-mirror.com/datasets/uoft-cs/cifar10/resolve/main/"
                f"plain_text/{fname.replace('.parquet', '-00000-of-00001.parquet')}")

        table = pq.read_table(str(path))
        img_col = table.column("img").to_pylist()
        self._labels = table.column("label").to_pylist()
        # Decode all PNGs once up front (PIL keeps them lazily-decoded
        # internally, so this is cheap memory-wise — ~180MB for 60k 32x32
        # RGB images held as PIL objects).
        self._images: list[Image.Image] = [
            Image.open(io.BytesIO(d["bytes"])).convert("RGB") for d in img_col
        ]
        # Materialise pixel data so subsequent __getitem__ calls don't
        # need to seek into the underlying BytesIO each time.
        for im in self._images:
            im.load()
        self.transform = transform

    def __len__(self) -> int:
        return len(self._labels)

    def __getitem__(self, idx: int) -> tuple:
        img = self._images[idx]
        if self.transform is not None:
            img = self.transform(img)
        return img, int(self._labels[idx])


def get_cifar10_loaders(
    root: str | Path = "./data/cifar10",
    batch_size: int = 128,
    num_workers: int = 2,
    pin_memory: bool = True,
    download: bool = False,                # parquet must be pre-downloaded
    augment: bool = True,
) -> tuple[DataLoader, DataLoader]:
    """Return CIFAR-10 train and test DataLoaders backed by parquet.

    Args:
        root: Directory containing ``train.parquet`` and ``test.parquet``
            (HuggingFace ``uoft-cs/cifar10`` plain_text split).
        batch_size: Mini-batch size for both splits.
        num_workers: DataLoader worker count.
        pin_memory: Pin memory for faster GPU transfer.
        download: Accepted for API parity with the MNIST loader but
            ignored; the parquet files must already exist under ``root``.
        augment: If True, apply random crop + horizontal flip on the
            training split.

    Returns:
        ``(train_loader, test_loader)``.
    """
    root = Path(root).expanduser()
    root.mkdir(parents=True, exist_ok=True)

    normalize = transforms.Normalize(CIFAR10_MEAN, CIFAR10_STD)
    if augment:
        train_tf = transforms.Compose([
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            normalize,
        ])
    else:
        train_tf = transforms.Compose([
            transforms.ToTensor(),
            normalize,
        ])
    test_tf = transforms.Compose([
        transforms.ToTensor(),
        normalize,
    ])

    train_set = CIFAR10Parquet(root=root, train=True,  transform=train_tf)
    test_set  = CIFAR10Parquet(root=root, train=False, transform=test_tf)

    train_loader = DataLoader(
        train_set, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=pin_memory, drop_last=False)
    test_loader = DataLoader(
        test_set, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=pin_memory, drop_last=False)
    return train_loader, test_loader
