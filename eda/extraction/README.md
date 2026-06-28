# `eda/extraction/` — 提取的 PPA 数据

由电路仿真与版图寄生提取得到的、注入 `smtj_pbnn_sim` 的可信数值。由 `../interface/` 单向读入；
仿真器本身不依赖本目录。

| 文件 / 目录 | 内容 |
|---|---|
| `peripheral_energy.yaml` | 外围能量（sky130 StrongARM 读出 48 fJ 等），由 `../interface/load_tech_params.py` 读入 |
| `writeline/` | 写线 IR 压降与写能量开销的提取与分析（见其 README） |

读出能量与写线 IR 已折入仿真器默认值（`ppa/tech_params.py`、`array/ir_drop.py`），仿真器单独运行即得
可信数值。写-DAC、计数器、面积等仍为数量级占位，待对应 sky130 单元提取后在此补充。
