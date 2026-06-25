# `eda/models/` — Verilog-A 器件紧凑模型

Verilog-A SOT-sMTJ 紧凑模型 (P1 keystone)。

计划文件：
- `smtj_sot.va` — 三端宏：SOT 写分支 ($R_\mathrm{SOT}=776\,\Omega$)、MTJ 读分支 ($R_P=4.9$k/$R_\mathrm{AP}=9.8$k)、
  事件驱动 + 显式种子的随机切换 (概率写 + telegraph 两模式)。
- 暴露参数 (按勘误 N1 的回归目标值)：`Vth=0.8958`、`VT=0.0234`、`Delta=4.91`、`Vc0=0.857`、`tau0=1e-9`、`seed`。

基底选择 (P0 决定)：fork ARM `mram_simulation_framework` 的 `llg_spherical_solver.va` 并**加自旋霍尔 SOT 写分支**
(它是 STT/VCMA、无 SOT)，或从 Rajpoot NGSPICE STT/SHE 模型改写。

⚠️ 随机性用 seeded `$rdist` + `@(cross/timer)` 离散事件，**不要**用裸模拟瞬态噪声 (见 ROADMAP/勘误 N3)。
