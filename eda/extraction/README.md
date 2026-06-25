# `eda/extraction/` — 提取的 PPA 数据 (替换占位符的可信数)

存放从电路级仿真/版图寄生提取得到的、用来**替换 `smtj_pbnn_sim` 占位常数**的可信数值。

计划产物：
- `periphery_energy.{yaml,csv}` — 含真实驱动/SA/ADC/计数器开销的每项能量，替换 `tech_params.py` 的 `e_dac_step`/`e_smtj_read`/`e_count_inc` (P2/P4)。
- `write_energy.yaml` — 器件级 (0.78 pJ) 与含驱动端到端写能量 (P2)。
- `column_lut.*` — 列在 (θ, T, corner) 上的能量/失调/传输特性查找表 (P6 接口用)。
- `ir_drop.*` — PEX 线压降 vs 阵列尺寸，替换 `array/ir_drop.py` 空桩 (P5)。
- `area.yaml` — 版图提取面积，替换 `a_*` (P4/P5)。

这些文件由 `eda/interface/` 单向读入仿真器；仿真器本身不依赖本目录。
