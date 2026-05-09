"""Command-line entry points for the simulator.

Three commands are exposed:

    smtj-cal     -- fit Sigmoid params from measured P_sw data
    smtj-train   -- run a training experiment from a YAML config
    smtj-eval    -- evaluate a trained checkpoint, optionally in full-stack mode
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional


def _add_calibrate_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--data", type=str, required=True,
                   help="CSV file with columns V, t_p, P_sw[, device_id]")
    p.add_argument("--out", type=str, required=True,
                   help="Output YAML path for the calibrated device config")


def calibrate_entry(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="smtj-cal",
                                     description="Calibrate sMTJ Sigmoid parameters.")
    _add_calibrate_args(parser)
    parser.add_argument("--device-id", type=str, default=None,
                        help="If set, restrict the fit to a single device_id.")
    parser.add_argument("--direction", type=str, default=None,
                        help="If set, restrict the fit to a single direction.")
    parser.add_argument("--eta-c", type=float, default=5.34,
                        help="C2C narrowing factor written into the output YAML.")
    args = parser.parse_args(argv)

    import pandas as pd
    from .device.calibration import (
        fit_sigmoid_params,
        fit_per_device_direction,
        write_device_yaml,
    )

    data = pd.read_csv(args.data)

    if args.device_id is not None and "device_id" in data.columns:
        data = data[data["device_id"] == args.device_id]
    if args.direction is not None and "direction" in data.columns:
        data = data[data["direction"] == args.direction]

    if {"device_id", "direction"}.intersection(data.columns) and \
            (args.device_id is None or args.direction is None):
        # Per-group summary on stdout, then fit the user's intended group
        summary = fit_per_device_direction(data)
        print(summary.to_string(index=False))
        if args.device_id is None or args.direction is None:
            print("\nPass --device-id and --direction to write a YAML for one group.")
            return 0

    sp = fit_sigmoid_params(data)
    write_device_yaml(sigmoid=sp, out_path=args.out, eta_c=args.eta_c)
    print(f"Calibrated: V_th = {sp.V_th:.4f} V, V_T = {sp.V_T:.4f} V, "
          f"beta_s = {sp.beta_s:.2f} V^-1, R^2 = {sp.r2:.4f}, n = {sp.n_points}")
    return 0


def _add_train_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", type=str, required=True,
                   help="Experiment YAML config under configs/experiment/")
    p.add_argument("--out", type=str, default="runs/",
                   help="Output directory for checkpoints and logs")


def train_entry(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="smtj-train",
                                     description="Train a PBNN model.")
    _add_train_args(parser)
    args = parser.parse_args(argv)

    # Defer the import so the CLI is fast for --help.
    from .utils.io import load_yaml
    cfg = load_yaml(args.config)
    name = cfg.get("name", Path(args.config).stem)
    out_dir = Path(args.out) / name

    # Dispatch on dataset; today only MNIST is wired.
    dataset = cfg.get("dataset", "mnist")
    if dataset == "mnist":
        from .scripts._mnist_train import run as _run
    else:
        raise NotImplementedError(f"Dataset '{dataset}' not yet wired in CLI.")
    return _run(cfg, out_dir)


def _add_eval_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--checkpoint", type=str, required=True)
    p.add_argument("--config", type=str, required=True)
    p.add_argument("--mode", type=str, default="hardware_aware",
                   choices=["software", "hardware_aware", "full_stack"])
    p.add_argument("--T", type=int, default=16,
                   help="Sample count for full_stack and ensembles")


def eval_entry(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="smtj-eval",
                                     description="Evaluate a trained PBNN.")
    _add_eval_args(parser)
    args = parser.parse_args(argv)

    from .utils.io import load_yaml
    from .scripts._mnist_eval import run as _run
    cfg = load_yaml(args.config)
    return _run(cfg, args.checkpoint, args.mode, args.T)


if __name__ == "__main__":
    sys.exit(train_entry())
