# `eda/testbenches/` — ngspice/Spectre 测试台与回归

电路级测试台，以及对照 `smtj_pbnn_sim` Python 模型的**双仿真器回归** (P1 验证门)。

计划内容：
- `regression_sigmoid.*` — 扫 46 个标定点、每点 N=100–1000 种子瞬态 MC、统计 P_sw(V)，断言 R²≥0.99 且还原 $V_\mathrm{th}/V_T$ (对照 `src/.../device/calibration.py`)。
- `regression_telegraph.*` — 长瞬态自相关 → $\tau(V)$、时间平均 → $\tanh$，对照 `device/telegraph.py` (`relaxation_time`/`stationary_mean`)。
- `regression_energy.*` — $\int V\!\cdot\!I$ over 一次写 → 断言 0.78 pJ。
- 写路径 (P2)、差分读 (P3)、读出/ADC (P4)、IR-drop (P5) 各自的测试台。

所有 MC **记录 seed 与 Spectre `noiseseed`** (默认每次换新种子 → 不可复现)。镜像 `tests/test_calibration.py`、`tests/test_telegraph.py` 的断言契约。
