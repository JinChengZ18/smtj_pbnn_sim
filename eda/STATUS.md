# EDA 工作状态与断点续传 (STATUS)

> **这是长时程任务的单一续传点。** 新会话从这里开始：读本文件 →（如需细节）读 [`ROADMAP.md`](ROADMAP.md) → 看 task 板。
> 每完成一步就更新「当前状态」与「验证账本」，并 commit。本文件优先级高于 README 的状态段。

## 当前状态  （last update: 2026-06-26, commit 17dbd01）

- **路线**：开源 ngspice（本机无 EDA 许可证）。回归目标钉死 `Vth=0.895783 V / VT=0.023414 V`。
- **当前阶段**：**P1（keystone）进行中**。
- **已完成**：`.va` 模型 + Python 金标准 + 随机写 harness（均验证 PASS）；EDA 工作区/勘误/计划已落仓并 FF 到 master。
- **下一步（唯一卡点）**：装 `ngspice≥43` + `OpenVAF-Reloaded` → 跑 `python eda/testbenches/run_regression.py`（task #10）。装工具需本机操作（用户侧；`.codex-eda-downloads/`/`.codex-eda-stage/` 疑似正在下载中）。
- **其后**：P2 写路径（task #3）。

## 续传协议（新会话照做）

1. 读本文件「当前状态」。
2. `git -C <repo> log --oneline -5` 看最近提交。
3. 跑（无需 EDA，确认 Python 侧仍绿）：
   `python eda/testbenches/gen_golden.py && python eda/testbenches/psw_mc_harness.py`
4. 跑 `python eda/testbenches/run_regression.py`：打印「未找到 ngspice/openvaf」⇒ 卡点仍是装工具；否则看是否 PASS（R²≥0.99）。
5. 读 [`ROADMAP.md`](ROADMAP.md) 找当前阶段，按下方 DoD 推进；每产一个可信数即更新 [`../docs/errata.md`](../docs/errata.md) 与本文件。

## 决策账本（已钉死，勿重议）

| ID | 决策 |
|---|---|
| D1 | 工具：无许可证 → 开源 `ngspice≥43` + `OpenVAF-Reloaded` + `sky130`；商用 (Virtuoso/Spectre/ASAP7) 留待有许可证 |
| D2 | 回归目标：`Vth=0.895783, VT=0.023414`（βs=42.71）；源于章节标定 0.894/44.6（errata N1） |
| D3 | 器件模型：新写 MIT `eda/models/smtj_sot.va`；不复用 Hikstor 专有 PDK；不 port 全 LLG |
| D4 | 随机性：harness 拥有 RNG（seeded、event-driven）；`.va` 保持代数（OpenVAF 安全） |
| D5 | vgsot-sim：拟作 submodule 挂 `eda/vendor/` 作 LLG 真值参考 — **待用户确认后执行** |
| D6 | `article/` 为交付稿，不放本地引用（见 memory: article-dir-is-deliverable） |

## 验证账本（checkpoints，可复现）

| 检查 | 命令 | 结果 | 状态 |
|---|---|---|---|
| `.va` 参数 vs 实测 46 点 (A,P→AP) | `gen_golden.py` | R²=0.9919, RMSE=0.0347 | ✅ |
| 欧姆写能量 (0.9V,776Ω,0.75ns) | `gen_golden.py` | 0.783 pJ | ✅ |
| τ(0V) | `gen_golden.py` | 67.8 ns | ✅ |
| 随机写 harness 复现 Sigmoid (N=2000) | `psw_mc_harness.py` | max\|err\|=0.019 < 4σ | ✅ |
| ngspice DC 扫描 V(psw) vs 金标准 | `run_regression.py` | 待装工具 | ⏳ |

## 各阶段 Definition of Done（DoD）

| 阶段 | 完成判据 | 状态 |
|---|---|---|
| **P0** | 工具/PDK 路线定、回归目标钉死、模型基底定 | ✅ |
| **P1** | `.va` 写好 ✅ + Python 金标准 PASS ✅ + 随机写 harness PASS ✅ + **ngspice `run_regression` PASS** ⏳ | 进行中 |
| **P2** | 写路径网表跑通；含驱动端到端写能量（数）；0.75ns 可行性结论；P_sw 复现 → errata R1/R4 | ⬜ |
| **P3** | 差分列 + SA；CMRR/残余失调 vs N；SA 失调 vs V_T → errata R2 | ⬜ |
| **P4** | CSA/ADC 读出能量/延迟/噪底；子阵列上限；外围占比重算 → errata R1 | ⬜ |
| **P5** | 单列/小 tile PEX；IR-drop vs 尺寸（含 776Ω 写线）→ errata R3 | ⬜ |
| **P6** | extraction LUT → interface 构造 extracted TechParams → 重跑 MNIST PPA → errata R1/R2 resolved | ⬜ |
| **P7** | 低势垒 τ(V) 验证；无扰动读 + 读回作用界；读出 TIA+ADC 噪声 → MC 损失 → errata R6/R7 | ⬜ |

## 工件清单

| 路径 | 作用 | 可运行 |
|---|---|---|
| `models/smtj_sot.va` | MIT Verilog-A SOT-sMTJ 紧凑模型（代数核 + Sigmoid/τ/⟨s⟩ 观测） | 需 OpenVAF |
| `testbenches/gen_golden.py` | Python 金标准生成（回归目标 + 校准验证） | ✅ 纯 Python |
| `testbenches/psw_mc_harness.py` | 随机写 harness（seeded Bernoulli 复现 p-bit + 写能量） | ✅ 纯 Python |
| `testbenches/regression_psw.spice` | ngspice DC 扫描回归网表 | 需 ngspice |
| `testbenches/run_regression.py` | 编译 `.va` + 跑 ngspice + 断言（工具缺失则优雅退出） | 需 ngspice+OpenVAF |
| `testbenches/golden_*.{csv,json}`, `mc_summary.json` | 金标准/验证结果（已提交） | — |
| `interface/`, `extraction/` | 回灌仿真器的接口与提取数据（P6） | 待填 |
| `SETUP_opensource.md` / `OPEN_SOURCE_FEASIBILITY.md` | 安装运行 / ③ 可行性矩阵 | — |
| `research/*` | 调研报告 + vgsot 整合决策 | — |
