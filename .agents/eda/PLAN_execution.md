# 创新优先 · 可分步执行方案 (execution plan)

> 把 [`research/2026-06-27_innovation_replan.md`](research/2026-06-27_innovation_replan.md) 与
> [`ROADMAP.md`](ROADMAP.md) 的创新主线（A0 方法学 / A1+A2 Hero / A3 第二篇）**落实成带 DoD 的有序步骤**。
> 续传真相源仍是 [`STATUS.md`](STATUS.md)；本文件是"下一步具体做什么"的执行清单。
> 图例：✅ 完成 · ◑ first-cut · ⬜ 未开始 · 🖱️ 需 GUI/人工收尾

## 0. 本会话后的状态快照 (2026-06-26)
- **工具链已原生齐备**（无需 Docker）：`Ubuntu-24.04-EDA` 内 ngspice-46 + OpenVAF-Reloaded +
  sky130A + KLayout + **Magic 8.3.668** + **netgen 1.5.321 (LVS, `~/eda/netgen/bin`)**。
- **真实提取数已落地**：写线 IR-drop（R3，`extraction/writeline/`）、SA 版后寄生/能量（R1/R5，
  `hero/sa_postlayout.py`）、SA 器件集 9→11 + DRC 0 违例 + LVS 工具链打通。
- **闭环基础设施在位**：`hero/readout_mapping.py`（mV→popcount→精度）、`hero/hero_mnist_sweep.py`、
  `interface/load_tech_params.py`、`device/variation.py` 的 `sigma_sense_offset` 通道。

## 0b. 完成度总览（对齐蓝本 `2026-06-27_innovation_replan.md`）
蓝本三层创新 + 两层贡献的当前落地状态（建模/电路级，**版图布线为收尾，按指令暂缓**）：

| 蓝本贡献 | 内容 | 状态 |
|---|---|---|
| **A0** 反向设计方法学 | finding→sky130 PEX 数→论断位移→闭回算法栈 | ✅ 全链路打通（见增补文档） |
| **A1=C1** 斜率匹配 p-bit 读出 | SA 失调按 V_T 预算；σ=0.39·V_T(N=120)；plain SA 帕累托最优 | ✅ 建模/电路级 |
| **A2=C2** 摊销写-DAC 微调 | 3–4 trim-bit、<1% 写能 | ✅ 建模 |
| **A3=C3** RC 等能量套利 | {N,M,b} 前沿 + 地标 ADC；诚实 ~30–35× | ✅ 建模 |
| **B1** 校准 .va + 双仿真器 + **LLG 验证** | R²=1.0 回归 + LLG 阈值 0.01·V_T 吻合 | ✅ |
| **B2/B4/B5/B6** 写驱动/差分读/ADC/IR | 端到端写 1.6pJ、SA 23–74fJ、IR vs N | ◑ first-cut（电路级数已出） |
| **B7/B8** 三位一体/自适应-T | 受限可行性包络 / ~50% 少写 | ✅（B7 仅可行性） |

- **错误/论断修正**：E1/E2 已修；**R1–R7 全部已处理**（R2/R4/R6/R7 收口为设计边界，R1/R3/R5 有真实提取数）。
- **📄 论文整合**：EDA 协同设计内容已整合进正文——第四章 4.6 节（读出/写通路协同设计、操作波形，图 4.15–4.21）与第五章 5.5/5.6 节（储备池读出协同、双模架构，图 5.8）。原独立增补稿已并入章节并移除。
- **目标期刊**（经 [`research/2026-06-27_plan_validation.md`](research/2026-06-27_plan_validation.md) 复核修正）：**JxCDC（最佳，物理建模/仿真+超越CMOS器件电路）> TVLSI（实测"鼓励非必须"）> TED（紧凑模型+SPICE）> IOP NCE（神经形态/RC）> TCAS-I**（蓝本把 TCAS-I 排太前——它对纯仿真最苛刻）。不投 Nat.Electron./ISSCC（需实测硅）。框架：以晶圆标定模型为可信锚，开源 PDK 作可复现性卖点。
- **仍待（均为门控/收尾，非主干）**：版图布线→全 LVS→版后 PEX（**指令①：所有设计冻结后再做**）；Xschem 原理图导出（需装 Xschem + GUI/批渲染）；版图 GDS 渲染图（需 KLayout GUI/xvfb）。

## 0c. 前向设计（仿真器发现 → 创新电路）+ 仿真器反向补充
> 纠正"只反驳自己、无前向创新"：以下是**仿真发现倒逼出的新设计**，不是对旧论断的修正。

| 前向设计 | 由哪条发现倒逼 | 结果 | 状态 |
|---|---|---|---|
| **F1 IR 感知逐行写预畸变** | 写线 IR 压降使远端单元写概率塌陷 | `hero/ir_aware_writedac.py`：N=256 不补偿时 p_sw 0.90(近)→0.016(远)；逐行预畸变码 0–148mV(~5 写-DAC 位，静态查表自提取片阻)→各行均匀 0.90。与逐列 V_th trim 合成**位置+器件感知写-DAC**。**承载电路经仿真选型**（`run_write_dac.py`）：电流舵接 776Ω 低阻写负载非单调(INL≈1.7LSB)→改电压型电阻串(6–7bit，LSB 1.6–3.1mV<V_T/7，单调，覆盖预畸变+微调)+写驱动缓冲 | ✅ 新设计+拓扑 |
| **F2 斜率匹配读出（含前端电路）** | SA 失调按 V_T(伯努利窗)预算 | 跨阻协同律 `R_TI=V_in/(2·PC_FS·LSB_I)`（`readout_mapping.py`）→ **sky130 电路实现**：电阻跨阻 R_TI=613Ω + StrongARM，`run_readout_frontend.py` 仿真整条链路，提取失调在电路中映射 σ_pc≈2.5 popcount（≈理想律 85%，余为 SA 有限输入阻抗负载）<膝点 → plain SA 足够 | ✅（电路级闭合） |
| **F3 列共享时分复用中分辨 SAR 读出** | RC 读出比较器主导、b-线性 | 比较器=提取 StrongARM(48fJ)；cap-DAC 能量经 sky130 电容密度坐实（`sar_capdac_energy.py`：假设值落单调/常规上下界间，b=8 阵列51–509fJ 与比较器384fJ 同量级）→ 摊销共享比较器(列共享时分复用)为能量杠杆 | ✅ 架构+能量坐实 |

**仿真器反向补充（据 EDA 数据修真实并重跑）**：
- `ppa/reservoir_energy.py`：读出原计"近免费"，已补**地标 SAR ADC 项**（比较器=提取 SA 48fJ）→ exp16 原生输出 **30×**（非 38×）；12 个 PPA 测试全过。
- `extraction/peripheral_energy.yaml` + `interface/load_tech_params.py`：`e_smtj_read` 5fJ 占位 → **48fJ 提取 SA**；per-MAC 793→860fJ，**写占比 98.7%→93.8%、读 0.6%→5.6%**（R1 落地）。

## 0d. 蓝本批判性复核（指令②，详见 [`research/2026-06-27_plan_validation.md`](research/2026-06-27_plan_validation.md)）
旧计划取自旧对话、未独立复核；3 个联网对抗智能体复核后的**必改项**：
- **引用错误**：arXiv:2509.13458（Kent）被**错描**——实为"稳定垂直 MTJ 的可调 RTN（STT 脉冲驱动）"，**非**反铁磁/电压可调势垒，**不预占三位一体可调势垒器件**；Nat.Electron. **-01458-3 是评论非实测论文**（"秒拒"论据被夸大）；Nano Lett 是 **2025**、专利 US9111623 是 **2015**。
- **C3 仅部分新颖**：arXiv:2601.21807(2026) **已证 2–4bit ADC 够用** → "低分辨最优"非我方；存活新颖性 = **MC/焦耳目标 + 纳入 N + 列共享 ADC**。须显式引并区分。
- **C1 确属新颖**：须引并区分 arXiv:2403.19374（TMR 余量现状）与 arXiv:2410.16915（sigmoid 感知但软件补偿、理想比较器）；只主张**定量 offset-vs-V_T 协同律**。
- **期刊**：见 0b（JxCDC/TVLSI/TED/NCE 先于 TCAS-I）。

---

## Phase 0 — 工具链网关 ✅ (本会话达成；Docker 改为可选)
| | 步骤 | 工具 | DoD | 状态 |
|---|---|---|---|---|
|0.1| ngspice+OpenVAF→OSDI→DC 回归 | ngspice-46 | `run_regression.py` R²=1.0 | ✅ |
|0.2| Magic ≥8.3.306 + sky130A techfile 加载 | Magic 8.3.668 | techfile 无版本错 | ✅ |
|0.3| KLautout sky130 PCell DRC | KLayout | `run_drc.sh` 0 违例 | ✅ |
|0.4| Magic 提取链 (extract→ext2spice / extresist) | Magic | `run_pex.sh`/`run_extresist.sh` 通 | ✅ |
|0.5| LVS netgen (Tim Edwards) | netgen 1.5.321 | `-batch lvs` 跑通 sky130A_setup | ✅ |
> 结论：Phase 0 **满足**。IIC-OSIC-TOOLS Docker 仅作可移植性备份，非阻塞。

---

## Phase 1 — Hero (A1 斜率匹配 p-bit 读出 + A2 摊销写-DAC) — 主线 ~60%
**目标**：min 读出能量+面积 @ iso-精度(≥97% MNIST)；产出 accuracy-vs-(V_offset/V_T) Pareto + 闭环图。**关 R2**。

| | 步骤 | 工具 | DoD | 状态 |
|---|---|---|---|---|
|1.1| StrongARM SA sky130 原理图级仿真 | ngspice+sky130 | vind→outp 翻转正确 | ✅ `hero/strongarm_sa.spice` |
|1.2| SA 输入折合失调 MC | ngspice MC | σ_offset/V_T | ✅ `run_offset_mc.py` **N=120 firmed: σ=9.21mV=0.39·V_T**（N=24 早值 0.47 偏高）|
|1.3| 闭环 σ_offset→MNIST | PyTorch | per-column σ→精度曲线 | ✅ `hero_mnist_sweep.py`(97.0→96.35%) |
|1.4| 读出跨阻映射 mV→popcount→精度 | Python | 协同律 + 设计边界 | ✅ `readout_mapping.py` |
|1.5| SA 器件版图 GDS + DRC | KLayout | 11 器件 DRC 0 违例 | ✅ `layout/`(23.1×18.7µm) |
|1.6| SA 版后寄生 C + 能量/失调估算 | Magic PEX | 器件 C 提取 + 能量量级 | ◑ `sa_postlayout.py`(35.25fF;23–74fJ) |
|1.7| **SA 器件间布线 (tail/交叉耦合/输入栅/precharge)** | KLayout/Magic GUI | 连通且 DRC 0 | 🖱️ `layout/LVS_GUI_CHECKLIST.md` |
|1.8| **Netgen LVS = layout vs `strongarm_sa_core.spice`** | netgen | "Circuits match uniquely" | 🖱️ 待 1.7 |
|1.9| **路由后 PEX (extresist R+C) → tt/ss/ff 后仿** | Magic+ngspice | 版后失调/延迟/能量含寄生 | ⬜ 待 1.8 |
|1.10| **回填**：真实 `e_smtj_read`(~50fJ 量级)→P6 接口→重跑 MNIST PPA | Python | 外围占比位移数 | ⬜ 待 1.9（关 R1）|
|1.11| Pareto：accuracy vs (V_offset/V_T)，{无/4×面积/单容自调零/两相斩波} | Python | Pareto + 设计边界 | ✅ `pareto_offset_cancellation.py`（V_in≥0.5 plain 最优；≤0.4 才需自调零）|
|1.12| **C2 摊销写-DAC**：3–4 trim-bit V_th 微调，代价<1% 写预算 | Python | trim→精度恢复曲线 | ✅ `write_dac_trim.py`（σ_col=8: 96.35%→b3 96.82%≈基线；静态码摊销→<1%写能）|
|1.13| Xschem 原理图+`.sym`+测试台 → SVG/PDF（"导出原理图"工件）| Xschem | hero 原理图图 | ⬜（需装 Xschem）|
|1.14| Hero 闭环图（σ_offset→栈→92.8%→~97% @ iso 读能）| Python/绘图 | 论文 hero 图 | ⬜ 汇总 1.10/1.11 |

**Phase 1 下一步（最小动作）**：1.7 GUI 布线 → 1.8 LVS → 1.9 路由后 PEX → 1.10 回填。1.11/1.13/1.14 可并行（不依赖布线）。

---

## Phase 2 — 第二篇 (A3/C3 RC 等能量套利) — 修 R6
| | 步骤 | 工具 | DoD | 状态 |
|---|---|---|---|---|
|2.1| 低势垒 τ(V)/⟨s⟩ 器件级验证 | .va+ngspice | Δ=3.8 旋钮成立 | ✅ `telegraph_lowbarrier.py` |
|2.2| 读出 ADC/噪声→记忆容量 first-cut | Python | 读出是限制者 | ◑ `rc_readout_noise.py`(MC0=6.38) |
|2.3| **三方 {N,M,b} MC/焦耳等高线** | Python | iso-能量 frontier | ✅ `rc_isoenergy.py`（读出非免费；效率拐点 b~5–6 列共享；b10=230×能量换3.66×MC）|
|2.4| **sky130 ADC 能量地标**（SAR 比较器=提取的 SA 48fJ）→ 回灌 2.3 | Python（吃 sa_postlayout）| 地标 E_adc(b) | ✅ 迭代进 `rc_isoenergy.py`（读出主导88–99%；b线性→惩罚温和；杠杆=摊销比较器）；TIA 前端偏置能量待 |
|2.5| 重算 ~38× vs 数字 ESN（端到端口径，含 2.4 地标 ADC 读出）| Python | 诚实比值 | ✅ `testbenches/rc_energy_recompute.py`（Ch5 配置 N=100/ens=96/L=1000，来自 exp16）：38× 加地标 ADC→**~30×(per-node 8b)/~35×(列共享)**，优势稳健（ESN 的 O(N²) 10.2µJ 压倒）|

---

## Phase 3 — 支撑/基础层 (Tier B，引先验，不独立成文)
| | 步骤 | DoD | 状态 |
|---|---|---|---|
|3.1| 写通路 sky130 CMOS 驱动端到端（替理想脉冲）→ R4 端到端写能 | 含短路/开关能量数 | ✅ `run_write_driver.sh`（交付0.9V→端到端1.61pJ=2.05×欧姆；需稳压写轨）|
|3.2| 写线 IR-drop 路由后列级 popcount 误差 vs N → R3 坐实 | 列级误差曲线 | ◑（B6；Track B 已给金属 R vs N）|
|3.3| 差分列失配残余（已 first-cut）整理为 B4 证据 | — | ◑ `diff_column.py` |
|3.4| 自适应-T 早退控制器（B8）量化省写能量 | T-甜点省能数 | ✅ `testbenches/adaptive_t.py`（SPRT 早退：iso-精度下 E[T]≈9.6 vs 固定 T=22 → **~57% 少写**，~50% 跨前沿）|
|3.5| 三位一体可调势垒 mode-MUX **仅受限架构可行性包络**（B7）| 可行性 + 势垒冲突登记 | ✅ `testbenches/trinity_barrier.py`（ΔΔ=1.11=22.6%·E_b → VCMA ~0.56V/+88K；时分互斥+势垒冲突=限制；关 R7）|
|3.6| **双模型策略（指令②）**：行为级为主力迭代 + LLG（vgsot-sim）做验证 | Python | LLG↔行为 sigmoid 一致性（R²/阈值）| ✅ `testbenches/llg_validate.py`（自热ON：阈值 LLG 0.896V vs 行为 0.8958V 差 0.01·V_T；R²=0.92；高压过驱平台为已知 LLG 特征）|

> **设备模型策略（指令② 2026-06-26）**：保留两套器件模型。**主力 = 标定行为级**（`eda/models/smtj_sot.va` + `gen_golden.py`，便宜、用于全工作流迭代）；**验证 = LLG 宏自旋求解器**（`eda/vendor/vgsot-sim`，计算量大，物理一手核对）。`llg_validate.py` 是桥：定期用 LLG 复核行为级 sigmoid/阈值。**可选**：vgsot-sim 亦可转写 Verilog-A 直接进 ngspice 共仿（重；非当前主线，记为后续）。

---

## 横向（持续）
- **勘误回填**：R1(1.10)、R2(1.8/1.9)、R3(3.2)、R4(3.1)、R5(2.5/1.9)、R6(2.5)、R7(3.5) → 拿到数即回填 `article/` 与 `../errata.md` 的「回填检查表」。
- **诚实支柱**（每篇必写）：RNG 在 Python harness；报比值非绝对(130nm 悲观)；Magic R-PEX 仅量级；端到端能量基线 6.95 pJ/bit；MTJ-in-GDS=黑盒+不可制造声明；`.va` RC 区未独立验证。
- **纪律**：阵列只到单列/原理图标注级，**绝不做 256×256 全 DRC-clean GDS**。
- **`.docx` 同步**：改 `article/*.md` 后 watcher ~4–5min 重生 `.docx`，与 `.md` 一起提交。

## 立即可开工的 5 个动作（按杠杆排序）
1. **1.7 GUI 布线 SA**（解锁 1.8–1.10 整条 Hero 版后链；清单已备 `LVS_GUI_CHECKLIST.md`）。
2. **1.11 Pareto 扫描**（纯 Python，不等布线；把 1.4 的设计边界扩成 accuracy-vs-V_offset/V_T 曲线）。
3. **2.3 RC {N,M,b} 等高线**（纯 Python，扩 `rc_readout_noise.py`；推进第二篇）。
4. **1.13 装 Xschem + 画 hero 原理图**（"导出原理图"工件；与布线并行）。
5. **3.1 sky130 写驱动端到端**（ngspice+sky130，给 R4 端到端写能，补 Track B 的写侧）。
