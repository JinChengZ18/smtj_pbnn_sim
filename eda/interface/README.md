# `eda/interface/` — 把 EDA 提取值回灌 `smtj_pbnn_sim`

本目录是 `eda/` 与主仿真器之间的单向接口：读取 `eda/extraction/` 的提取值，重算并对照仿真器的
能量/精度，使「用电路提取值替换占位」可审计。主仿真器不 import `eda/`；读出能量与写线 IR 已折入
仿真器默认值（`ppa/tech_params.py`、`array/ir_drop.py`），本目录用于审计与精度耦合实验。

| 脚本 | 作用 | 运行 |
|---|---|---|
| `load_tech_params.py` | 读取 `extraction/peripheral_energy.yaml`，对照 28 nm 占位基线重算每-MAC 与 MNIST PPA 能量 | `PYTHONPATH=../../src python load_tech_params.py` |
| `hero_closed_loop.py` | 器件物理失调位移 + 概率位精度（解析） | `PYTHONPATH=../../src python hero_closed_loop.py` |
| `hero_mnist_sweep.py` | 注入 `sigma_sense_offset` 通道、扫描 → MNIST 精度（需 torch/GPU） | `PYTHONPATH=../../src python hero_mnist_sweep.py` |

各脚本将结果摘要写入同目录 `*_summary.json`。
