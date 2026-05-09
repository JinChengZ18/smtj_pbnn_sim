"""Global seeding for reproducibility."""

from __future__ import annotations

import os
import random
import numpy as np
import torch


def set_global_seed(seed: int) -> None:
    """Seed Python, NumPy and Torch generators consistently.

    Note that bitwise reproducibility across CUDA versions also requires
    setting ``torch.use_deterministic_algorithms(True)``, which is left to
    the caller because it can affect performance.
    """
    seed = int(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
