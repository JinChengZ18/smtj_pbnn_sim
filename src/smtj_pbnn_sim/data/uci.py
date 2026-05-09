"""UCI tabular dataset loaders for the PBNN benchmark suite.

Each ``load_*`` function returns ``(X, y, classes)`` where:

  * ``X``       -- np.ndarray (N, d), float32, raw features.
  * ``y``       -- np.ndarray (N,),  int64,  class indices [0..C-1].
  * ``classes`` -- list of original class labels (for reporting).

Datasets are downloaded once from the UCI repository and cached under
``root`` (default ``./data/uci``) so subsequent runs are offline.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
import numpy as np

UCI_BASE = "https://archive.ics.uci.edu/ml/machine-learning-databases"


def _download(url: str, dest: Path) -> Path:
    """Download ``url`` to ``dest`` if not already cached."""
    dest = Path(dest)
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
        dest.write_bytes(data)
    return dest


# ---------------------------------------------------------------------------
# Iris  (150 x 4, 3 classes)
# ---------------------------------------------------------------------------

def load_iris(root: str | Path = "./data/uci"):
    p = _download(f"{UCI_BASE}/iris/iris.data", Path(root) / "iris.data")
    X, y_str = [], []
    for line in p.read_text().strip().splitlines():
        parts = line.strip().split(",")
        if len(parts) != 5:
            continue
        X.append([float(x) for x in parts[:4]])
        y_str.append(parts[4])
    classes = sorted(set(y_str))
    y = np.array([classes.index(s) for s in y_str], dtype=np.int64)
    return np.array(X, dtype=np.float32), y, classes


# ---------------------------------------------------------------------------
# Wisconsin Breast Cancer Diagnostic  (569 x 30, binary)
# ---------------------------------------------------------------------------
# UCI removed the Pima Indians Diabetes dataset for ethical reasons. WDBC
# is a comparable classic binary medical-classification benchmark.

def load_wdbc(root: str | Path = "./data/uci"):
    p = _download(f"{UCI_BASE}/breast-cancer-wisconsin/wdbc.data",
                  Path(root) / "wdbc.data")
    X, y_str = [], []
    for line in p.read_text().strip().splitlines():
        parts = line.strip().split(",")
        if len(parts) < 32:
            continue
        # Column 0 is the patient ID (drop), column 1 is the label (M/B),
        # columns 2..31 are the 30 numeric features.
        X.append([float(x) for x in parts[2:32]])
        y_str.append(parts[1])
    classes = sorted(set(y_str))  # ['B', 'M'] -> B=0, M=1
    y = np.array([classes.index(s) for s in y_str], dtype=np.int64)
    return np.array(X, dtype=np.float32), y, classes


# ---------------------------------------------------------------------------
# Yeast  (1484 x 8, 10 classes)
# ---------------------------------------------------------------------------

def load_yeast(root: str | Path = "./data/uci"):
    p = _download(f"{UCI_BASE}/yeast/yeast.data", Path(root) / "yeast.data")
    X, y_str = [], []
    for line in p.read_text().strip().splitlines():
        parts = line.split()
        if len(parts) < 10:
            continue
        # First column is the protein sequence name (drop), columns 1..8 are
        # features, column 9 is the class label.
        X.append([float(x) for x in parts[1:9]])
        y_str.append(parts[9])
    classes = sorted(set(y_str))
    y = np.array([classes.index(s) for s in y_str], dtype=np.int64)
    return np.array(X, dtype=np.float32), y, classes


# ---------------------------------------------------------------------------
# Statlog Vehicle Silhouettes  (846 x 18, 4 classes)
# ---------------------------------------------------------------------------

def load_vehicle(root: str | Path = "./data/uci"):
    files = [f"xa{c}.dat" for c in "abcdefghi"]
    rows = []
    for f in files:
        p = _download(f"{UCI_BASE}/statlog/vehicle/{f}", Path(root) / f)
        for line in p.read_text().strip().splitlines():
            parts = line.split()
            if len(parts) < 19:
                continue
            rows.append(parts)
    X = np.array([[float(x) for x in r[:18]] for r in rows], dtype=np.float32)
    y_str = [r[18] for r in rows]
    classes = sorted(set(y_str))
    y = np.array([classes.index(s) for s in y_str], dtype=np.int64)
    return X, y, classes


# ---------------------------------------------------------------------------
# Spambase  (4601 x 57, binary)
# ---------------------------------------------------------------------------

def load_spambase(root: str | Path = "./data/uci"):
    p = _download(f"{UCI_BASE}/spambase/spambase.data",
                  Path(root) / "spambase.data")
    arr = np.loadtxt(p, delimiter=",")
    X = arr[:, :57].astype(np.float32)
    y = arr[:, 57].astype(np.int64)
    return X, y, [0, 1]


# ---------------------------------------------------------------------------
# Statlog Satimage  (6435 x 36, 6 classes)
# ---------------------------------------------------------------------------

def load_satimage(root: str | Path = "./data/uci"):
    train_path = _download(f"{UCI_BASE}/statlog/satimage/sat.trn",
                           Path(root) / "sat.trn")
    test_path = _download(f"{UCI_BASE}/statlog/satimage/sat.tst",
                          Path(root) / "sat.tst")
    arr = np.vstack([np.loadtxt(train_path), np.loadtxt(test_path)])
    X = arr[:, :36].astype(np.float32)
    y_raw = arr[:, 36].astype(np.int64)
    classes = sorted(np.unique(y_raw).tolist())
    y = np.array([classes.index(c) for c in y_raw], dtype=np.int64)
    return X, y, classes


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

DATASETS = {
    "iris":     (load_iris,     "Iris (150 x 4, 3 cls)"),
    "wdbc":     (load_wdbc,     "WDBC (569 x 30, 2 cls)"),
    "yeast":    (load_yeast,    "Yeast (1484 x 8, 10 cls)"),
    "vehicle":  (load_vehicle,  "Vehicle (846 x 18, 4 cls)"),
    "spambase": (load_spambase, "Spambase (4601 x 57, 2 cls)"),
    "satimage": (load_satimage, "Satimage (6435 x 36, 6 cls)"),
}
