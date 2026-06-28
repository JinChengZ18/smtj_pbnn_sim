# 开源 EDA (ngspice) 可行性矩阵

回答 ③：在没有商用许可证、只用开源工具链的前提下，路线图各阶段能做到哪些、哪些受限。

**开源工具链**：`ngspice ≥ 43` (OSDI) + `OpenVAF-Reloaded` (编译 Verilog-A → `.osdi`) + `sky130` 开源 CMOS PDK
(做外围晶体管) + `Xschem` (原理图) + `Magic`/`KLayout` (版图/PEX)。安装见 [`../../eda/SETUP_opensource.md`](../../eda/SETUP_opensource.md)。

> 当前机器已安装 ngspice 46 与 OpenVAF-Reloaded `20260616-2-gc592eed6`，并完成
> Verilog-A → OSDI → ngspice 的端到端回归。

## 一条关键约束（决定开源路线的形态）

**OpenVAF 是紧凑模型编译器，`.va` 内部的 `$random`/`$rdist`、`@(cross)` 事件、跨时间步持久状态在 OSDI 路径上不可靠。**
因此开源路线**不能**把随机伯努利抽样与时序状态机放进 `.va`（这正是 Hikstor PDK 的 `@cross`+持久 `mtj_state` 写法只适用于 Spectre 的原因）。

**采用的设计**（已落到 `eda/models/smtj_sot.va`）：`.va` 只做**代数**部分——双态电阻读支路 (状态由控制节点 `st` 给定) + R_SOT 写支路 + 把校准 Sigmoid/τ(V)/⟨s⟩ 作为**可观测探针节点**暴露；**随机抽样与时序逻辑放在 harness**（Python 拥有 RNG、按 trial 设状态/积分能量）。这既 OpenVAF 安全、又比 `$random` 更可复现。

## 可行性矩阵

| 阶段 | 开源 ngspice 可做？ | 说明 / 受限点 |
|---|---|---|
| **P1 器件 .va + 46 点回归** | ✅ **已完成** | `.va` 暴露 Sigmoid 观测 → 86 点 DC 扫描对照金标准；`max|err|=3.51e-4`、R²=1.00000。随机性在 harness。|
| **P2 写路径 (DAC+驱动+0.75ns脉冲)** | ✅ 可做 | sky130 CMOS 子电路 + `.va` 写支路；瞬态测脉冲建立与能量。随机写=harness 按 trial 抽 u、设状态。|
| **P3 差分读 + 灵敏放大** | ✅ 可做 | sky130 CMOS 灵敏放大；失配 MC 用 ngspice `.control` 里的 `sgauss()/agauss()` 自写循环 (无 Spectre `statistics{}`，循环自己写)。|
| **P4 读出 CSA/ADC + 外围能量** | ✅ 可做 | 原理图级；瞬态/积分电源电流给读出能量；`.noise` 给噪底。|
| **P5 IR-drop 版图 + PEX** | ⚠️ **部分** | Magic/KLayout 可做提取，但开源 PEX 弱于 Quantus；对论文级估计够用，绝对精度打折。|
| **P6 接口回灌 + 共仿** | ✅ LUT 路 / ❌ 真 AMS | LUT-export (Python 编排 ngspice 逐 MAC/逐工作点 → 查表回灌仿真器) 可做；**真 wreal AMS 无开源等价**，用 **Python-in-the-loop** 替代。|
| **P7 RC telegraph + 读出噪声** | ✅ 可做 | telegraph 时序在 Python (pbnn_sim 已是 NumPy)；读出 TIA+ADC 噪声用 ngspice `.noise`/瞬态。τ(V) 验证亦可由 `.va` 观测 + Python 比对。|
| 数字 T 步 RNM 环 | ⚠️ 替代 | ngspice 无 wreal；用 XSPICE code-model / B-source 行为 FSM，或 **Python 脚本套 ngspice** 逐步驱动 (推荐)。|

**结论**：**整条计划基本都能用开源 ngspice 完成**，两点折中——(i) PEX 精度弱于商用；(ii) AMS 共仿改为 Python-in-the-loop。工具安装与 P1 OSDI 回归门槛已经跨过。

## 现在就能做 vs 装好工具后才能做

- **现在 (仅 Python，已完成)**：`eda/models/smtj_sot.va`、`eda/testbenches/gen_golden.py` (已跑，R²=0.9919/0.78pJ PASS)、`golden_psw.csv`、`regression_psw.spice`、`run_regression.py`。
- **已验证命令**：`python eda/testbenches/run_regression.py` → 编译 `.va`、跑 ngspice、对金标准断言 R²≥0.99。脚本在工具缺失时会打印安装指引并优雅退出。

## 按顺序的下一步

1. ~~安装 ngspice≥43 + OpenVAF-Reloaded；跑通 P1 回归。~~ ✅
2. P2 写路径子电路 (sky130) + harness 随机写 + 能量积分。
3. P3 差分列 + 灵敏放大 + 自写失配 MC。
…按 ROADMAP 依赖图推进，每阶段产数即更新 `../errata.md`。
