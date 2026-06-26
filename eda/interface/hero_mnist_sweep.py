#!/usr/bin/env python3
"""Hero (A1) closed loop -- the RIGOROUS accuracy half.

Trains a PBNN-MLP on MNIST (baseline PDK D2D variation), then -- at INFERENCE -- injects
a readout sense-amp offset via the new device/variation.py `sigma_sense_offset_V` channel
and re-evaluates FULL_STACK accuracy. Produces accuracy vs (sense offset / V_T): the
hero figure's accuracy axis. The extracted sky130 SA offset sigma (run_offset_mc.py)
drops onto this curve; auto-zero -> smaller offset -> recovered accuracy.

The SA offset is modelled as an inference-time per-cell V_th-equivalent decision shift
(first-cut; a per-output-column systematic refinement is future work).

Run (Windows, GPU): python eda/interface/hero_mnist_sweep.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import torch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP                       # noqa: E402
from smtj_pbnn_sim.nn.pbnn_linear import DeviceLayerParams, ForwardMode, PBNNLinear  # noqa: E402
from smtj_pbnn_sim.device.variation import VariationConfig                    # noqa: E402
from smtj_pbnn_sim.data.mnist import get_mnist_loaders                        # noqa: E402
from smtj_pbnn_sim.train.train_loop import train_one_epoch, evaluate          # noqa: E402
from smtj_pbnn_sim.nn.losses import binary_cross_entropy_loss                 # noqa: E402
from smtj_pbnn_sim.utils.seeding import set_global_seed                       # noqa: E402

VTH_NOM, VT_NOM = 0.895783, 0.023414
EPOCHS = 12
OFFSETS_mV = [0, 5, 10, 15, 20, 23.4, 30]


def make_model(sense_off_V, device, T=16):
    # sigmoid_direct centers V_th at the calibrated nominal (0.8958 V). delta mode would
    # center it at the NB-bridge value 0.843 V -> a ~53mV systematic shift that corrupts
    # FULL_STACK (the trap the thesis docs warn about). Isolate the SA offset: no other
    # D2D (sigma_V_th_rel=sigma_V_T_rel=0), only the sense offset perturbs at inference.
    vc = VariationConfig(mode="sigmoid_direct", sigma_V_th_rel=0.0, sigma_V_T_rel=0.0,
                         sigma_sense_offset_V=sense_off_V, seed=42)
    dp = DeviceLayerParams(V_th_nom=VTH_NOM, V_T_nom=VT_NOM, R_P_nom=4900.0,
                           TMR_nom=1.0, Delta_nom=4.91, V_c0_nom=0.857, eta_c=5.34)
    return PBNN_MLP(hidden=1024, device_params=dp, variation_cfg=vc,
                    T_full_stack=T).to(device)


def main():
    set_global_seed(0)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}")
    tr, te = get_mnist_loaders(root=str(REPO / "data" / "mnist"),
                               batch_size=128, num_workers=0)
    crit = binary_cross_entropy_loss

    # --- train (baseline D2D, NO sense offset; SA offset is an inference-time read error) ---
    model = make_model(0.0, device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for e in range(EPOCHS):
        _, tra = train_one_epoch(model, tr, opt, crit, device,
                                 mode=ForwardMode.HARDWARE_AWARE)
        if (e + 1) % 3 == 0 or e == 0:
            print(f"epoch {e+1}/{EPOCHS} train_acc={tra:.4f}", flush=True)
    with torch.no_grad():                       # theta x100 -> near-deterministic FULL_STACK
        for m in model.modules():
            if isinstance(m, PBNNLinear):
                m.theta.mul_(100.0)
    ckpt = {k: v.detach().cpu() for k, v in model.state_dict().items()}

    # --- sweep inference-time sense offset, eval FULL_STACK accuracy ---
    rows = []
    for off_mV in OFFSETS_mV:
        mo = make_model(off_mV * 1e-3, device)
        mo.load_state_dict(ckpt)
        _, acc = evaluate(mo, te, crit, device, mode=ForwardMode.FULL_STACK)
        print(f"sense_offset={off_mV:>4} mV  off/V_T={off_mV/1e3/VT_NOM:4.2f}  "
              f"FULL_STACK acc={acc*100:.2f}%", flush=True)
        rows.append(dict(offset_mV=off_mV, off_over_VT=off_mV / 1e3 / VT_NOM,
                         acc_pct=acc * 100))

    # --- per-COLUMN systematic offset (the CORRECT model: one SA per output column) ---
    # A forward hook adds a per-output-neuron offset (popcount units) to each PBNNLinear
    # output BEFORE BN+sign -- i.e. the SA's per-column decision shift. The SA's volts->popcount
    # mapping (via P3's 5.1uA/popcount LSB + the readout transimpedance, B5) places sigma_offset
    # on this axis. Unlike per-cell, this is NOT averaged out.
    base = make_model(0.0, device)
    base.load_state_dict(ckpt)
    col_rows = []
    for spc in [0.0, 0.5, 1.0, 2.0, 4.0, 8.0]:
        gen = torch.Generator(device=device).manual_seed(7)
        handles = []
        for m in base.modules():
            if isinstance(m, PBNNLinear):
                off = torch.randn(m.out_features, generator=gen, device=device) * spc
                handles.append(m.register_forward_hook(
                    lambda mod, i, o, off=off: o + off))
        _, acc = evaluate(base, te, crit, device, mode=ForwardMode.FULL_STACK)
        for h in handles:
            h.remove()
        print(f"col_offset_sigma={spc:>4} popcount  FULL_STACK acc={acc*100:.2f}%", flush=True)
        col_rows.append(dict(sigma_popcount=spc, acc_pct=acc * 100))

    acc0 = rows[0]["acc_pct"]
    summ = dict(epochs=EPOCHS, VT_mV=VT_NOM * 1e3, acc_at_offset0_pct=acc0, rows=rows,
                per_column_sweep=col_rows,
                note=("Hero accuracy axis: SA offset injected at inference via the R2 "
                      "sigma_sense_offset_V channel. Extracted sky130 SA sigma "
                      "(run_offset_mc.py) drops onto this curve. Per-cell first-cut; "
                      "per-column-systematic refinement is future work."))
    (Path(__file__).resolve().parent / "hero_mnist_summary.json").write_text(
        json.dumps(summ, indent=2))
    print(f"\nbaseline acc (offset=0) = {acc0:.2f}%; curve written to hero_mnist_summary.json")


if __name__ == "__main__":
    main()
