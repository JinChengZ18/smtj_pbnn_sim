# EDA 工作状态与断点续传 (STATUS)

> **这是长时程任务的单一续传点。** 新会话从这里开始：读本文件 →（如需细节）读 [`ROADMAP.md`](ROADMAP.md) → 看 task 板。
> 每完成一步就更新「当前状态」与「验证账本」，并 commit。本文件优先级高于 README 的状态段。

## 当前状态  （last update: 2026-06-26）

- **路线**：开源 ngspice（本机无 EDA 许可证）。工具链已装齐并验证：**ngspice-46 + OpenVAF-reloaded 20260616**（已加入当前用户 PATH；路径亦记于 `eda/tools.local.json`）。回归目标 `Vth=0.895783 V / VT=0.023414 V`。
- **当前阶段**：**P1 已完成 ✅**；**P2 first-cut 已完成**（理想脉冲+串阻驱动；待 sky130 CMOS 驱动细化）。
- **已完成**：
  - P1：`.va` 编译通过 → OSDI → ngspice DC 扫描对金标准 **R²=1.000000**（全开源链路打通）。
  - P2 first-cut：`write_mc_harness.py` 跑通 12 次瞬态 — 0.75ns 脉冲 rise≈40ps（可行）；10Ω 理想驱动下信道能量≈0.80 pJ、驱动开销 1.3%；P_sw 在交付电压上复现。
  - vgsot-sim 作 submodule 接入 `eda/vendor/vgsot-sim`（决策 D5 执行）。
- **下一步**：P2 细化（sky130 CMOS 写驱动替换理想脉冲，量化真实驱动开销/短路能量 → errata R4）；可并行 P3（差分读+SA）。装 sky130 见 SETUP（建议 WSL2）。
- **ngspice-46 要点（已踩坑，勿重犯）**：OSDI 加载命令是 **`osdi`**（非 `pre_osdi`），经 cwd 的 `.spiceinit` 在**解析前**加载；OSDI 器件需 **`.model <name> <va模块>`** 卡（本项目用 `.model smtj_sot smtj_sot`），实例 `N1 ... smtj_sot`；**SPICE 首行=标题**（Python 生成的网表必须以 `*` 注释开头，否则首条 `.model`/元件被当标题吞掉）；`.va` 参数可经 `.model smtj_sot smtj_sot Delta=3.8` 覆盖（P7 用）。

## 续传协议（新会话照做）

1. 读本文件「当前状态」。
2. `git -C <repo> log --oneline -5` 看最近提交。
3. 跑（无需 EDA，确认 Python 侧仍绿）：
   `python eda/testbenches/gen_golden.py && python eda/testbenches/psw_mc_harness.py`
4. 跑 `python eda/testbenches/run_regression.py`，确认 OSDI 编译和 ngspice DC 扫描仍 PASS（R²≥0.99）。
5. 读 [`ROADMAP.md`](ROADMAP.md) 找当前阶段，按下方 DoD 推进；每产一个可信数即更新 [`../docs/errata.md`](../docs/errata.md) 与本文件。

## 决策账本（已钉死，勿重议）

| ID | 决策 |
|---|---|
| D1 | 工具：无许可证 → 开源 `ngspice≥43` + `OpenVAF-Reloaded` + `sky130`；商用 (Virtuoso/Spectre/ASAP7) 留待有许可证 |
| D2 | 回归目标：`Vth=0.895783, VT=0.023414`（βs=42.71）；源于章节标定 0.894/44.6（errata N1） |
| D3 | 器件模型：新写 MIT `eda/models/smtj_sot.va`；不复用 Hikstor 专有 PDK；不 port 全 LLG |
| D4 | 随机性：harness 拥有 RNG（seeded、event-driven）；`.va` 保持代数（OpenVAF 安全） |
| D5 | vgsot-sim 已作 submodule 接入 `eda/vendor/vgsot-sim`（LLG 真值参考；内含 Hikstor 专有 PDK，**勿复制进 MIT 仓库/论文**） |
| D6 | `article/` 为交付稿，不放本地引用（见 memory: article-dir-is-deliverable） |

## 验证账本（checkpoints，可复现）

| 检查 | 命令 | 结果 | 状态 |
|---|---|---|---|
| `.va` 参数 vs 实测 46 点 (A,P→AP) | `gen_golden.py` | R²=0.9919, RMSE=0.0347 | ✅ |
| 欧姆写能量 (0.9V,776Ω,0.75ns) | `gen_golden.py` | 0.783 pJ | ✅ |
| τ(0V) | `gen_golden.py` | 67.8 ns | ✅ |
| 随机写 harness 复现 Sigmoid (N=2000) | `psw_mc_harness.py` | max\|err\|=0.019 < 4σ | ✅ |
| ngspice DC 扫描 V(psw) vs 金标准 | `run_regression.py` | 86 点 max\|err\|=3.5e-4, **R²=1.000000** | ✅ |
| P2 写路径瞬态：0.75ns 脉冲可行性 | `write_mc_harness.py` | rise≈40 ps ≪ 0.75 ns | ✅ |
| P2 信道能量 + 驱动开销（10Ω 理想驱动） | `write_mc_harness.py` | E_sot≈0.80 pJ, overhead 1.3% | ✅ first-cut |
| P3 差分列偏置消除（匹配，claim a） | `diff_column.py` | 线性 max-err 9e-6 popcount | ✅ |
| P3 失配残余失调 vs N（σ_Rp7%/σ_TMR4%） | `diff_column.py` | ~0.06·√N popcount（16/64/256→0.30/0.62/0.97，sub-LSB 至 N≈256） | ✅ first-cut |
| P7a 低势垒 τ(V)/⟨s⟩（Δ=3.8） | `telegraph_lowbarrier.py` | τ_max(0V)=22.35 ns，τ rel-err<1.6e-4 | ✅ |

## 各阶段 Definition of Done（DoD）

| 阶段 | 完成判据 | 状态 |
|---|---|---|
| **P0** | 工具/PDK 路线定、回归目标钉死、模型基底定 | ✅ |
| **P1** | `.va` ✅ + Python 金标准 ✅ + 随机写 harness ✅ + ngspice `run_regression` R²=1.0 ✅ | ✅ Done |
| **P2** | first-cut ✅（理想驱动：能量/开销/0.75ns 可行性/P_sw）；待 sky130 CMOS 驱动端到端 → errata R4 | ◑ 部分 |
| **P3** | first-cut ✅（MTJ 差分消除精确；失配残余 ~0.06√N popcount，sub-LSB 至 N≈256）；待 sky130 SA 晶体管失调 vs V_T → errata R2 | ◑ 部分 |
| **P4** | CSA/ADC 读出能量/延迟/噪底；子阵列上限；外围占比重算 → errata R1 | ⬜ |
| **P5** | 单列/小 tile PEX；IR-drop vs 尺寸（含 776Ω 写线）→ errata R3 | ⬜ |
| **P6** | extraction LUT → interface 构造 extracted TechParams → 重跑 MNIST PPA → errata R1/R2 resolved | ⬜ |
| **P7** | τ(V)/⟨s⟩ first-cut ✅（Δ=3.8 τ_max=22.35ns）；待无扰动读+读回作用界、读出 TIA+ADC 噪声 (R6)、三位一体势垒冲突 (R7) | ◑ 部分 |

## 工件清单

| 路径 | 作用 | 可运行 |
|---|---|---|
| `models/smtj_sot.va` | MIT Verilog-A SOT-sMTJ 紧凑模型（代数核 + Sigmoid/τ/⟨s⟩ 观测） | 需 OpenVAF |
| `testbenches/gen_golden.py` | Python 金标准生成（回归目标 + 校准验证） | ✅ 纯 Python |
| `testbenches/psw_mc_harness.py` | 随机写 harness（seeded Bernoulli 复现 p-bit + 写能量） | ✅ 纯 Python |
| `testbenches/regression_psw.spice` | ngspice DC 扫描回归网表 | 需 ngspice |
| `testbenches/run_regression.py` | P1：编译 `.va` + 跑 ngspice + 断言（工具缺失则优雅退出） | 需 ngspice+OpenVAF |
| `testbenches/write_path.spice` | P2 写路径瞬态网表（脉冲 + 驱动 + SOT 写支路） | 需 ngspice |
| `testbenches/write_mc_harness.py` | P2 Python-in-the-loop：能量/开销/0.75ns 可行性/随机写 | 需 ngspice+OpenVAF |
| `testbenches/diff_column.py` | P3 差分列 claim(a)：偏置消除 + 失配残余 MC（电阻级，无需 .va） | 需 ngspice |
| `testbenches/telegraph_lowbarrier.py` | P7a 低势垒 τ(V)/⟨s⟩ 验证（.va 观测 vs 解析，Δ=3.8） | 需 ngspice+OpenVAF |
| `tools.local.json` | 机器本地工具路径（gitignored） | — |
| `vendor/vgsot-sim` (submodule) | 用户 LLG 全物理模型（真值参考；含 Hikstor PDK，版权隔离） | 需 `pip install -e` |
| `testbenches/golden_*.{csv,json}`, `mc_summary.json` | 金标准/验证结果（已提交） | — |
| `interface/`, `extraction/` | 回灌仿真器的接口与提取数据（P6） | 待填 |
| `SETUP_opensource.md` / `OPEN_SOURCE_FEASIBILITY.md` | 安装运行 / ③ 可行性矩阵 | — |
| `research/*` | 调研报告 + vgsot 整合决策 | — |
