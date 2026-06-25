# `eda/interface/` — 把 EDA 提取值回灌 `smtj_pbnn_sim` 的接口 (「新接口」)

本目录是 `eda/` 与主仿真器之间的**单向接口**：读取 `eda/extraction/` 的可信数值，
构造仿真器可读的配置 / dataclass，使「替换不成熟内容」成为一次**配置注入**而非代码耦合。

**接口原则**：`smtj_pbnn_sim` 不 import `eda/` 任何内容；本目录把提取数写入仿真器现有入口
(YAML 配置 / `TechParams` 实例 / 替换函数)，可随时回退到原占位值做对照。

计划模块：
- `load_tech_params.py` — 由 `extraction/periphery_energy.yaml`+`write_energy.yaml`+`area.yaml` 构造一个
  「extracted」`ppa.tech_params.TechParams`，供 `experiments/04_ppa_breakdown.py`、`06_sweep_T_*` 直接使用。
- `ir_drop_lut.py` — 由 `extraction/ir_drop.*` 提供查表式压降，替换 `array/ir_drop.estimate_ir_drop`。
- `sense_offset_channel.py` — 把 P3 的 SA 失配分布作为 `sigma_sense_offset` 通道加进 `device/variation.py` 的扫描。
- `ams_cosim/` (可选) — wreal AMS 共仿桥：从 PyTorch 流一小撮 MAC 过提取网表 (P6 杀手图)。

**验收**：用 extracted `TechParams` 重跑 MNIST PPA，得到替换占位符后的每-MAC 能量/外围占比，回填论文 (勘误 R1/R2)。
