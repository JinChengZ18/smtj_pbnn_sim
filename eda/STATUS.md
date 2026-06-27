# EDA 工作状态与断点续传 (STATUS)

> **这是长时程任务的单一续传点。** 新会话从这里开始：读本文件 →（如需细节）读 [`ROADMAP.md`](ROADMAP.md) → 看 task 板。
> 每完成一步就更新「当前状态」与「验证账本」，并 commit。本文件优先级高于 README 的状态段。

## 当前状态  （last update: 2026-06-26，仓库迁英文路径 + Magic 升级 8.3.668 解锁 PEX 路线）

- **⭐ 战略转向（2026-06-27 顶刊重审）**：计划从"验证优先 P1–P7"改为**创新优先**。验证 ≠ 顶刊贡献，且多数候选新电路 2024–26 已被做掉；新颖性 = **规格反转 + 闭环 + 反向设计方法学**。主线：**Hero=斜率匹配 p-bit 读出（C1+C2，SA 失调按 V_T 预算 + 闭环 MNIST 92.8%→~97%，关 R2）**；**第二篇=RC 等能量 {N,M,b} 套利（C3，修 R6）**。**P1–P7 first-cut 降为基础/支撑层**。目标期刊 TCAS-I/TVLSI/TED（不投 Nat.Electron./ISSCC）。详见 [`research/2026-06-27_innovation_replan.md`](research/2026-06-27_innovation_replan.md) 与 ROADMAP 顶部「创新优先重排」。ROADMAP 另列**两层贡献层级**：Tier A=创新（A0 方法学 / A1-A2 Hero / A3 第二篇），Tier B=大论文基础工程（B1–B9，引先验为实现基础，单独不投顶刊但是合格学位工作），+ 大论文章节映射。
- **路线**：开源 ngspice（本机无 EDA 许可证）。工具链已装齐并验证：**ngspice-46 + OpenVAF-reloaded 20260616**（已加入当前用户 PATH；路径亦记于 `eda/tools.local.json`）。回归目标 `Vth=0.895783 V / VT=0.023414 V`。
- **当前阶段**：**P1 已完成 ✅**；**P2 first-cut 已完成**（理想脉冲+串阻驱动；待 sky130 CMOS 驱动细化）。
- **已完成**：
  - P1：`.va` 编译通过 → OSDI → ngspice DC 扫描对金标准 **R²=1.000000**（全开源链路打通）。
  - P2 first-cut：`write_mc_harness.py` 跑通 12 次瞬态 — 0.75ns 脉冲 rise≈40ps（可行）；10Ω 理想驱动下信道能量≈0.80 pJ、驱动开销 1.3%；P_sw 在交付电压上复现。
  - vgsot-sim 作 submodule 接入 `eda/vendor/vgsot-sim`（决策 D5 执行）。
  - **Hero(A1)：sky130 StrongARM SA**（`hero/strongarm_sa.spice`，vind=+20mV→outp=1.8V）→ **输入折合失调 σ=11.05mV=0.47·V_T**（`run_offset_mc.py`，关 R2 的核心可信数）→ **闭环 MNIST**（per-column σ=8→96.35%）→ **版图导出 GDS**（`hero/layout/`，sky130 PCell 9 器件，611 shapes）。Magic/TCL 被版本卡（需 Magic≥8.3.306），改用 KLayout PCell 流。
- **下一步（创新优先）**：**Phase 0 网关** = WSL2 + IIC-OSIC-TOOLS Docker（Xschem/Magic/Netgen/ngspice + sky130A）+ 共享 `.osdi`（即用户正在装的 PDK）；随后 **Phase 1 Hero** = 斜率匹配 p-bit 读出 SA（C1）→ 版图/PEX → 闭环 MNIST。旧 P2/P3/P4/P5 细化并入 Hero/第二篇作支撑证据。
- **🗺️ 可分步执行清单**：创新主线（A0/A1+A2 Hero/A3 第二篇）已拆成带 DoD 的有序步骤 + "立即可开工 5 动作"，见 [`PLAN_execution.md`](PLAN_execution.md)。**Phase 0 工具链网关本会话已原生达成**（Magic 8.3.668 + netgen 1.5.321 + ngspice/OpenVAF/sky130A/KLayout 全齐，Docker 改为可选）。
- **⚡ 可立刻开工（2026-06-26 Magic 升级新解锁）**：Magic 8.3.668 解除版本卡 → Hero(A1) SA 的 **routing → Netgen LVS → Magic `ext2spice` PEX → 版后 offset/能量**（喂 errata **R3 IR-drop / R5 端到端能量**，即原 P5）。**已完成第一步**：`run_pex.sh` 验证 Magic extract→ext2spice 工具链通（9 器件 + 寄生 C，器件级）。**接下来**：①给 `sa_devices.gds` 加器件间互连(routing)；②确认/装对 LVS netgen（apt 的是网格生成器）；③重跑 PEX 含 `extresist` 取可信 R/C。
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
| D7 | 路径：**保留仓库现位置 + 用 ASCII build dir** `~/smtj_eda_build` 跑工具（`run_drc.sh` 模式）；不整体迁移仓库（迁移要重连 5 个 worktree + 孤立 MEMORY.md，高成本低收益）。详见 [`MANUAL_SETUP_NEEDED.md`](MANUAL_SETUP_NEEDED.md) §2 |
| D8 | ~~Magic/TCL 版图+PEX 被版本卡（8.3.105 < 需 8.3.306）~~ → **已解决（2026-06-26）**：Magic 从源码升级到 **8.3.668**（≥8.3.306），sky130A techfile 正常加载，Magic/TCL **routing→LVS→PEX 路线已解锁**（`ext2spice` 工具链已实跑通，见验证账本）。KLayout PCell 仍为 GDS 生成器（两者读同一 GDS）。详见 [`MANUAL_SETUP_NEEDED.md`](MANUAL_SETUP_NEEDED.md) §1。**LVS 注意**：`/usr/bin/netgen`(apt) 是网格生成器，非 LVS netgen(Tim Edwards) |

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
| P6 接口：提取值回灌 → MNIST PPA | `interface/load_tech_params.py` | per-MAC 793→818 fJ (+3%，写+驱动)；MNIST T=4 5.91→6.09µJ；read/ADC 待 P4 | ✅ first-cut |
| P7 读出 ADC/噪声 → 记忆容量 (R6) | `rc_readout_noise.py` | MC0=6.38；ADC≤10bit/读噪声≥2% 显著掉 MC（10bit→62%，2%噪→47%）→ 读出精度是限制者 | ✅ first-cut |
| Hero(A1) 闭环基础设施：R2 通道 + 决策位移 | `hero_closed_loop.py` + `variation.py` | `sigma_sense_offset_V` 通道已接(10mV→9.89mV)；offset=V_T 时 Δp_sw=0.23（per-列系统偏置） | ✅ first-cut |
| **Hero(A1) SA 输入折合失调 MC（sky130 真跑）** | `eda/hero/run_offset_mc.py`（WSL ngspice+sky130） | StrongARM σ_offset=**11.05mV=0.47·V_T**，3σ=1.42·V_T → 平 SA 再注入近半判决窗的 V_th 偏移（N=24 MC，AVT 假设） | ✅ |
| Hero(A1) 失调-面积协同 | `run_offset_mc.py 24 4` | 4× 输入对面积 → σ/V_T 降到 <0.1（远低于 0.3·V_T 预算；exact 值受网格分辨率限） | ◑ 定性 |
| Hero(A1) 精度轴：sense offset → MNIST | `interface/hero_mnist_sweep.py`（GPU，12ep→97.4%train） | baseline **96.80%**；per-cell sense offset 0→30mV(1.28·V_T) 精度**几乎不变**(96.8%) → **per-cell 模型欠估**；SA 失调是 per-输出列系统性(一列一个 SA)，需 per-column 模型才显真实退化：**per-column σ=0→8 popcount → 97.0%→96.35%**（随 σ 增大；per-cell 平）。SA 伏特→popcount 精确映射待 B5 读出跨阻 | ◑ first-cut |
| **Hero(A1) 版图导出 → GDS（"导出版图"交付）** | `eda/hero/layout/gen_sa_layout.py`（WSL KLayout sky130 PCells） | StrongARM 9 器件（5 NMOS+4 PMOS，带保护环）→ `sa_devices.gds`：top `strongarm_sa_devs`，17.5×18.7µm，**611 shapes，sky130 真层号**（diff 65/20, poly 66/20, li1 67/20, met1 68/20…）。Magic/TCL 路线被版本卡（Magic 8.3.105 < 需 8.3.306）→改 KLayout PCell 流。**DRC 已通过：0 violations**（`run_drc.sh`，经 ASCII build dir `/home/lenovo/smtj_eda_build` 跑 sky130A_mr.drc；器件级，布线 DRC 待加互连）。WSL 链坑（~~CJK 路径破坏 `-rd input` UTF-8 解析~~【迁英文路径后已不适用】 / `/tmp` 空闲清空 / `bash -lc` 内变量丢失）已由 build-dir 方案规避 | ✅ 器件版图 + DRC 0-violation |
| **Hero(A1) B5 读出映射：mV→popcount→精度（闭环合拢）** | `eda/hero/readout_mapping.py`（纯 Python，吃上游 JSON） | 跨阻 `LSB_V=LSB_I·R_TI` 桥接 P3 的 5.1µA/pc、SA 的 11.05mV、per-column 精度曲线；协同律 `σ_pc=σ_offset_V·2·PC_FS/V_in`。**最大增益读出下 plain SA 0.47·V_T → σ_pc≈3–5 → 精度跌<0.15pp**（R_TI≈400–700Ω）；仅 V_in=0.4V+宽扇入越膝点（−0.14pp）。结论=**量化设计边界**（何时省/需自调零），非「必须自调零」 | ✅ first-cut（闭环 mV→精度合拢）|
| **Hero(A1) Magic PEX 工具链解锁验证**（Magic 升级后） | `eda/hero/layout/run_pex.sh`（WSL Magic 8.3.668） | `gds read→load→extract all→ext2spice` 跑通：从 `sa_devices.gds` 提出器件 + 器件/局部互连寄生 C（cthresh 0）→ `sa_pex.spice` | ✅ 工具链通 |
| **Track B 写线 IR-drop（R3）+ 写能量开销（R5）** | `eda/extraction/writeline/`（KLayout 标定带 + Magic `extresist` + Python 标度） | extresist 自校验 poly 47.96 vs techfile 48.2 Ω/sq；往返金属 R vs 776Ω：N≤64 可忽略(<5%)、**N=256 met1/2 W=1µm=128Ω=16.5%**(IR148mV，高角19%)、N=1024=66%、**li1 灾难(kΩ)**。148mV 跌破 0.8958V 写点→p_sw 位移（高列上限）。指引=写线 met2+/加宽/分段，N≥256 预算 ~10–20% | ✅ first-cut（真实提取数）|
| **Track A SA 版后（器件集修正 + 寄生 + LVS 工具链）** | `gen_sa_layout.py`(11器件) + `run_pex.sh` + `sa_postlayout.py` + netgen | 版图器件集 9→**11**（补 Mp3/Mp4，匹配原理图），**DRC 0 违例**，提取 **11 MOSFET + 35.25 fF 器件 C**；SA 动态能 ~**23–74 fJ/决策**（5–15× 5fF 占位→R1 读出低估）；失调对称布线设计律→R2。netgen 1.5.321 LVS 工具链打通（设备级；完整 LVS 待布线，见 `layout/LVS_GUI_CHECKLIST.md`） | ◑ first-cut（布线/全 LVS 待 GUI 收尾）|
| **1.11 C1 失调消除 Pareto（accuracy vs V_offset/V_T）** | `eda/hero/pareto_offset_cancellation.py`（纯 Python，吃 hero_mnist_summary + 协同律）| {无/4×面积/单容自调零/两相斩波}×读出工作点；噪声地板 0.15pp。**V_in≥0.5V/MNIST 扇入 → plain SA Pareto 最优**（差落噪声内）；**仅 V_in≤0.4V/宽扇入 → 自调零挣回成本**（边界 layer1≤0.35V、layer2≤0.40V）。规格反转=按 V_T 预算失调、非 TMR 余量 | ✅（关 R2 设计边界）|
| **2.3+2.4 RC 等能量 {N,M,b} 套利（R6，地标 ADC 能量）** | `eda/testbenches/rc_isoenergy.py`（MC(N,M,b)+SAR 能量 E_adc=b·E_comp+2^b·E_capDAC，**E_comp=48fJ 取自提取 SA**）| 读出**非免费且主导 RC 能量**（比较器即使 b=3 占 88–99%）→ 驳 reservoir_energy「免费」；比较器 **b-线性** → 分辨率惩罚温和（b3→b10 仅 **38×能量换3.66×MC**，非粗模 230×）→ 杠杆是**摊销比较器**（列共享 SA+下采样 M<N），中高分辨 b~8 可负担 | ✅（关 R6；2.4 地标）|
| **3.1 sky130 CMOS 写驱动端到端（R4）** | `eda/testbenches/run_write_driver.sh`（WSL ngspice+sky130，扫 W_p）| 1.8V CMOS 反相器驱 776Ω：交付 0.9V（W_p≈7µm）→ E_dev=0.785pJ（对上基线）但 E_vdd≈**1.61pJ=2.05×欧姆**（驱动开销105%，Ron/776分压）；过驱(W_p≥16)→E_dev涨1.9–2.9pJ。**需稳压~0.9V写轨** | ✅（关 R4，端到端~1.6pJ）|
| **1.12 C2 摊销写-DAC V_th trim** | `eda/hero/write_dac_trim.py`（纯 Python，吃 hero 精度曲线）| 既有每列写-DAC 加 **3–4 trim-bit** 抵消每列 V_th/失调：σ_col=8 popcount 96.35%→b3 96.82%≈基线（σ_col=4→b3；12→b5）。静态每列码、校准时设一次→摊销近零，写占 98.7% → trim **<1% 写能**。量化论文"DAC 校准+温漂补偿"，配 C1 成 Hero 校准半边 | ✅（C2；关 R4 校准侧）|
| **B1-val 双模型：LLG（vgsot-sim）验证行为级 sigmoid（指令②）** | `eda/testbenches/llg_validate.py`（驱动 vgsot-sim MC P_sw vs I_SOT，自热ON，200 trials/点，映射 V=I·776）| **LLG 物理独立复现标定行为级 sigmoid**：阈值 **LLG 0.8960V vs 行为级 V_th 0.8958V → 差 0.2mV=0.01·V_T**；上升区 R²=0.92、RMSE=0.067(≈MC噪声)。高压(>0.92V)LLG P_sw 平台低于行为级=**过驱进动回切**（真实 LLG 特征，行为级单调 sigmoid 不含）→ 行为级在**阈值工作区**有效。**双模型策略落地**：行为级主力迭代、LLG 验证 | ✅（验证 B1）|
| **3.5/R7 三位一体可调势垒可行性包络** | `eda/testbenches/trinity_barrier.py`（纯 Python，吃 arrhenius Δ/τ_max）| PBNN(Δ4.91,τ67.8ns)↔RC(Δ3.8,τ22.4ns) 需 **ΔΔ=1.11=22.6%·E_b**（28.7meV）→ VCMA ~0.56V（@2kT/V，在 Kent2025/HKUST2026 已证范围）或 +88K。**但时分互斥、低势垒冲突写/保持/读扰、无已证并发宏** → 受限架构提案+限制 | ✅（关 R7） |
| **3.4/B8 自适应-T 早退采样控制器** | `eda/testbenches/adaptive_t.py`（纯 Python，SPRT/CI 早退 over p-bit Bernoulli）| **iso-精度下** E[T]≈9.6 vs 固定 T=22 同误差 → **~57% 少写**（~50% 跨前沿，Wald 左移）；写占 98.7% → ~1:1 传到系统写能。Exp.06 T-甜点落地为每决策序贯控制器 | ✅（B8 支撑）|

## 各阶段 Definition of Done（DoD）

| 阶段 | 完成判据 | 状态 |
|---|---|---|
| **P0** | 工具/PDK 路线定、回归目标钉死、模型基底定 | ✅ |
| **P1** | `.va` ✅ + Python 金标准 ✅ + 随机写 harness ✅ + ngspice `run_regression` R²=1.0 ✅ | ✅ Done |
| **P2** | first-cut ✅（理想驱动）+ **sky130 CMOS 驱动端到端 ✅**（`run_write_driver.sh`：交付0.9V→端到端1.61pJ=2.05×欧姆，需稳压写轨）→ errata R4 关 | ✅ Done |
| **P3** | first-cut ✅（MTJ 差分消除精确；失配残余 ~0.06√N popcount，sub-LSB 至 N≈256）；待 sky130 SA 晶体管失调 vs V_T → errata R2 | ◑ 部分 |
| **P4** | CSA/ADC 读出能量/延迟/噪底；子阵列上限；外围占比重算 → errata R1 | ◑ 部分（sky130 SA 动态能 ~23–74 fJ/决策 first-cut，`sa_postlayout.py`；ADC/CSA 待）|
| **P5** | 单列/小 tile PEX；IR-drop vs 尺寸（含 776Ω 写线）→ errata R3 | ◑ first-cut（写线金属 R vs N 已 extresist 提取，N=256→16.5%·776Ω；li1 灾难；待路由后列级 popcount 误差）|
| **P6** | first-cut ✅（interface 读 extraction → 重跑 MNIST PPA，写+驱动 per-MAC +3%）；待 P4 ADC 数落地后报外围占比位移 (R1) | ◑ 部分 |
| **P7** | τ(V)/⟨s⟩ ✅ + 读出 ADC/噪声→MC (R6) ✅first-cut（读出精度是限制者）；待无扰动读+读回作用界、读出能量映射(NeuroSim)、三位一体势垒冲突 (R7) | ◑ 部分 |

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
| `testbenches/rc_readout_noise.py` | P7 读出 ADC/噪声→记忆容量 (R6)（纯 Python，复用 reservoir） | ✅ 纯 Python |
| `interface/load_tech_params.py` | P6 接口：extraction → 重跑 MNIST PPA（单向回灌） | ✅ 纯 Python |
| `hero/layout/gen_sa_layout.py` + `sa_devices.gds` | Hero(A1) SA 器件版图导出 → GDS（sky130 PCells，611 shapes；"导出版图"交付） | 需 KLayout |
| `hero/readout_mapping.py` | Hero(A1) B5：读出跨阻把 SA mV→popcount→MNIST 精度（闭环合拢 + 协同律） | ✅ 纯 Python |
| `extraction/peripheral_energy.yaml` | 提取的外围能量（写=P2；读/DAC/计数待 P4） | — |
| `SETUP_opensource.md` / `OPEN_SOURCE_FEASIBILITY.md` | 安装运行 / ③ 可行性矩阵 | — |
| `research/*` | 调研报告 + vgsot 整合决策 | — |
