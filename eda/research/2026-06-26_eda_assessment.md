# EDA 工具选型与电路设计工作评估 (2026-06-26)

> 产出方式：读全项目 + 一次 7-智能体工作流 (工具选型 / 器件模型桥接 / 电路模块 / 验证方法学 /
> 储池电路 / PDK 可行性) + 一个对抗式事实核查智能体。所有工具、紧凑模型、PDK 可用性均经网络核实。
> 本文件是可引用的持久记录；勘误见 [`../../docs/errata.md`](../../docs/errata.md)，落地计划见 [`../ROADMAP.md`](../ROADMAP.md)。

被引用的论文论断 (供下文对照)：
- **(a)** 差分双单元读出消除共模/IR/漏电偏置：$I_\mathrm{col}^\mathrm{diff}\propto\delta G\cdot V_\mathrm{read}/2\cdot\sum w_i x_i$
- **(b)** 793 fJ/MAC，写能量占 98.7%，外围优化「意义不大」
- **(c)** $V_\mathrm{th}$ 绝对位置稳定性是唯一精度瓶颈 ($\sigma_\mathrm{rel}(V_\mathrm{th})=20\%\to92.8\%$)
- **(c2)** 256×256、$R_P\sim5$k 下 IR-drop 可忽略
- **(d)** sMTJ 0.78 pJ/样本 vs CMOS p-bit 5 pJ = 4.2× 物理优势
- **(e)** RC 模拟物理比数字 ESN 低 ~38× 能量；读出散粒噪声/ADC 是真正限制者

---

## 1. 现状定位：评估器 vs 电路设计层

| 维度 | 现状 | 物理可信度 |
|---|---|---|
| 器件 $P_\mathrm{sw}(V,t_p)$ Sigmoid、Néel-Brown、$\tau(V)$ | 真实晶圆校准 | ✅ |
| 差分 XNOR-popcount、T 步展开、训练 | 行为级正确 | ✅ 算法 |
| SOT 写能量 0.78 pJ = $V^2t/R$ | 唯一物理量地标定 | ✅ (仅欧姆沟道) |
| CMOS 外围 (DAC 5 fJ、读 5 fJ、计数 0.5 fJ、面积、延迟) | 代码明标「28nm 数量级占位符」 | ❌ 猜测 |
| IR-drop | 文档化空桩 (无求解器、从不调用) | ❌ |
| 晶体管网表/SPICE/版图/PDK/灵敏放大/写驱动/ADC | 全部不存在 | ❌ |

**结论**：要补的不是「更高级的仿真器」，而是一层**器件-电路验证层**，把占位数升级为提取数，
并在电路级证实/修正论断 (a)–(e)。最有价值的结果往往是几条承重论断在真实电路仿真下**位移**。

## 2. 三个必须先纠正的认知

1. **分层栈，不是「Virtuoso 还是别的」二选一**：
   微磁 (mumax3/OOMMF，解释 CV(Δ)=7.7%) → **Verilog-A 紧凑模型 (你的桥接对象)** → 电路仿真 (Spectre/ngspice)
   → 版图 + 寄生提取 (Quantus)。你那条 Python Sigmoid 紧凑模型**本身就是 Verilog-A 层的内容**，只是写在了 Python 里。
2. **没有 PDK 自带 MTJ (承重事实)**：每条路线都得自带 Verilog-A 的 MTJ，用 CMOS PDK 只做外围。
3. **混合信号** (模拟随机写/读核 + 数字 DAC/计数器 T 步环) → 必须 **AMS + 实数建模 (RNM)**；
   纯模拟 SPICE 跑不动 `T×MC×阵列`，纯数字仿真器没有器件物理。

## 3. 工具选型 (已核实)

### 3.1 主推 (有大学许可证)
**Cadence Virtuoso Studio + Spectre AMS Designer**，分工：

| 任务 | 工具/分析 | 验证/替换 |
|---|---|---|
| 器件 sMTJ | 自写 **Verilog-A** (模拟分支) | 桥接 Sigmoid |
| DAC + 计数器 + FSM | **Verilog-AMS / wreal RNM** | 让 T 步环可仿真 |
| 差分读/写驱动/灵敏放大 | **Spectre X** 瞬态/噪声 | (a)(b)(d) |
| D2D 变异传播 | **Spectre MC / FMC** | (c) |
| 器件热噪声 / 读 ADC 噪底 | **瞬态噪声 (trannoise)** | p-bit 前提 + (e) |
| 256×256 寄生 | **Quantus QRC** 提取 + 后仿 | (c2) |

### 3.2 免费/无许可证回退 (已核实可行)
`ngspice ≥ 43` (OSDI 接口) + **`OpenVAF-Reloaded` (OSDI 0.4)** 编译 Verilog-A + `Xschem` + `Magic/KLayout`，
CMOS 用 **sky130 或 IHP SG13G2**，MTJ 用自写 Verilog-A 共仿。
- ⚠️ **不要用 Xyce** (截至 2024–25 仍用 ADMS、未集成 OpenVAF/OSDI)。
- ⚠️ 原 OpenVAF 2023 年底后停维护，用活跃 fork `OpenVAF-Reloaded`；论文方法里**钉死版本**。

### 3.3 CMOS 衬底 (外围)
- 有大学 Cadence：**ASAP7** (7nm 预测 PDK，BSD，含 Virtuoso techfile/DRC/LVS/PEX) 或 FreePDK45；
  无 MPW 费、无 NDA；诚实声明 ASAP7「非可制造、仅学术」。
- 全开源：IHP SG13G2 / sky130 (130nm 会高估 CMOS 能量/面积，但所有**相对**结论仍成立)。

### 3.4 明确不做
- ❌ **Sentaurus TCAD**：器件已晶圆校准，材料/工艺级仿真零增量。
- ❌ **GF 22FDX eMRAM MPW**：是 STT 不是 SOT、IP 加密不可改偏置、数月 + 花钱。
- ⚠️ **NeuroSim V1.5** 只覆盖 CMOS 外围 (~1.3%)，给不出占 98.7% 的 sMTJ 写能量——已在 `tech_params.py`/§4.3 更正。

### 3.5 决策依据
三家商用栈 (Cadence/Synopsys/Siemens) 能力均够；**理性选择依据是大学许可证 + 生态熟悉度，不是功能表**。
Cadence 学术装机面最广、自旋-CIM 教程最多，故为默认。

## 4. MTJ 模型从哪来

| 来源 | 许可 | 适配度 | 备注 |
|---|---|---|---|
| **ARM `mram_simulation_framework`** | BSD-3 | s-LLGS+FP 骨架好，**但 STT/VCMA、无 SOT** | 须自加自旋霍尔写分支 + 三端解耦读/写；论文 `llg_dynamics.py` 已点名此工具 |
| **Rajpoot NGSPICE STT/SHE** (arXiv:2208.14055) | 开源宣称 | 拓扑最近 (SHE=SOT 机制 + 随机热噪声) | **Papers-with-Code 无公开代码**，须联系作者确认 |
| **Camsari/Purdue p-bit** (arXiv:1809.04028) | 散见论文 | 行为辅助模型范式 (tanh+RNG)，非器件模型 | 给 PBNN p-bit 抽象的引用谱系 |

**做法**：先在免费 ngspice 把 Verilog-A 跑通去风险，再消耗付费许可证；
写之前先按勘误 N1 把回归目标工作点定为自动拟合值 ($V_\mathrm{th}=895.8$ mV、$V_T=23.4$ mV、$\beta_s=42.7$ V⁻¹)。

## 5. 值得做的工作 (按「可信度增益/工作量」排序，映射到论断)

> 详细分阶段、依赖、工作量见 [`../ROADMAP.md`](../ROADMAP.md)。

| # | 工作 | 工具/分析 | 验证/修正 | 预期位移 |
|---|---|---|---|---|
| **1 ★** | Verilog-A SOT-sMTJ 单元 + 46 点 Sigmoid/τ(V)/0.78pJ 回归 (先 ngspice) | 瞬态 MC | 器件-电路桥；解锁全部 | — |
| **2** | 写路径：5b DAC + SOT 驱动 + 0.75ns 脉冲 + 随机写 | 瞬态 + 多种子 | (b)(d) | 0.75ns 可行性？真实写能量 > 0.78pJ |
| **3** | 差分双单元列 + 电流型灵敏放大 | MC 失配 | (a)；测 (c) | SA 失调 10–30mV ≈ $V_T$ 或撼动 (c) |
| **4** | 读出 (CSA vs 电荷积分+ADC) | 瞬态/噪声 | 改写 (b) | 外围占比 <1% → 20–40% |
| **5** | IR-drop PEX (单列/小 tile) | Quantus 后仿 | (c2) | 写线 (776Ω) 压降是真风险 |
| **6** | **接口**：提取 LUT 回灌 pbnn_sim + 重跑 MNIST PPA + wreal 共仿 | LUT/AMS | 落地 (b)(c) | 「一个 MNIST 数字穿过提取列」杀手图 |
| **7** | RC：低势垒 τ(V) 验证 + 无扰动读 + 读出 TIA/ADC 噪声 | 瞬态噪声 | (e)；三位一体限制 | 解决 readout-free 矛盾 |

### RC 路径要点
- RC 节点是**另一个器件** (低势垒 Δ≈3.5–4.3，$\tau_\mathrm{max}$ 从 ~68ns 降到 ~22ns)，须重参数化 ARM s-LLGS。
- **无扰动读**：4 端解耦 + 量化读回作用 (读偏置把 τ 移动多少)——RC 方案前提，目前是假设。
- **模拟读出 TIA+ADC 噪声 = 论断 (e) 真正所在地**；`reservoir_energy.py` 把读出当近乎免费，与正文矛盾，须解决。
- **三位一体势垒冲突** (PBNN Δ=4.91 vs RC ~3.8)：作为诚实限制/提案陈述，非已证明能力。

## 6. 风险与方法学纪律

1. **可复现 MC**：钉版本、写死并记录每个 seed / Spectre `noiseseed` (默认每次换新种子)。否则 CV(Δ)/论断(c) 图不可复现。
2. **随机切换 = 事件驱动 + 种子** ($rdist on @(cross/timer))，**非**裸模拟 trannoise (注入连续高斯、自适应步长采样次数不定、生不出离散跳变)。头号实现风险。
3. **第 1 周确认**：大学 Cadence/Synopsys 席位 + Europractice 成员资格、论文算「教学」还是「研究」用途。整条商用路线时间线挂在此。
4. **范围纪律**：DRC-clean 256×256 GDS 是博士级工作；版图只做一列/小 tile 做 PEX，256×256 停在 schematic + 寄生标注级。Schematic + Verilog-A 共仿已能移动 (a)(b)(d)。

## 7. 论文叙事框架

**两层方法学**：Python 仿真器 = 已校准的算法/行为层；Virtuoso+Spectre 共仿 Verilog-A = 新增的器件-电路验证层。
方法章**逐项列出每个 Spectre 结果替换了哪个占位符**，使「从数量级猜测升级到提取数」可审计。
最强新贡献：展示 (b)(c2) 乃至 (c) 在真实电路仿真下**位移**——把自己的结论拿去电路级证伪，远比只复现数字有分量。

## 8. 已核实事实附录 (可直接进论文参考)

- ✅ `ngspice ≥ v39` (2023-01-31) 起含 OSDI 接口，运行时加载 OpenVAF 编译的 `.osdi` Verilog-A 模型。
- ✅ **无任何开源 PDK 含 MTJ/MRAM**：sky130 有 ReRAM (Weebit/HfO₂)，IHP SG13G2 是 SiGe BiCMOS；MTJ 必须自带 Verilog-A 共仿。
- ✅ ARM `mram_simulation_framework` 为 BSD-3，提供 `llg_spherical_solver.va` + Python s-LLGS + Fokker-Planck + Spectre 测试台；**STT/VCMA 两端、无 SOT 分支**。
- ✅ Rajpoot arXiv:2208.14055 真实、覆盖 SHE (SOT 相关机制)、拓扑最近，但**无公开代码**，须向作者索取。
- ✅ NeuroSim V1.5 (arXiv:2505.02314, 2025-05) 是快速阵列级 PPA 估算器，器件库 SRAM/RRAM/FeFET/nvCap，**无 MTJ 单元**，与 Spectre 互补 (非替代)。
- ✅ ASAP7 (ASU/ARM) BSD、学术认证、与厂商无关的 7nm FinFET **预测** PDK，含 Virtuoso techfile/BSIM-CMG/DRC/LVS/PEX；非可制造。
- ✅ GF 22FDX eMRAM 是 STT (Everspin)，Europractice 可达，但 eMRAM IP 为**加密存储器编译器宏**，不能改偏置当随机 SOT p-bit。
- ✅ 混合信号结构确需 AMS + RNM；纯 Spectre `T×MC×阵列` 不可解。

### 对调研中过度声明的纠正 (对抗式核查)
- ⚠️ 个别智能体一度称 ARM 框架「支持 SOT」——**误读**；它是 STT/VCMA，须自加 SOT。
- ⚠️ 「Camsari 2020、5 pJ」**未能干净核实**；可核实者为 6.95 pJ/bit (MDPI 2024)；端到端口径比较。
- ⚠️ 「用 NeuroSim 替换能量占位」只对 CMOS 外围成立，不含 sMTJ 写。

## 主要来源
- Spectre AMS Designer / Spectre X / FMC / Quantus：cadence.com 产品页
- ARM s-LLGS：github.com/ARM-software/mram_simulation_framework；arXiv:2106.04976
- Rajpoot NGSPICE STT/SHE：arXiv:2208.14055 (+ IOP 3161/012023, 2024 MC follow-up)
- Camsari p-bit：arXiv:1809.04028；Borders 2019 Nature 573；Sutton 2020 Sci Adv 6 eabb2823
- NeuroSim V1.5：arXiv:2505.02314；github.com/neurosim
- ngspice OSDI：ngspice.sourceforge.io/osdi.html；OpenVAF(-Reloaded)：github.com/pascalkuthe/OpenVAF
- 开源 PDK：github.com/IHP-GmbH/IHP-Open-PDK；github.com/RTimothyEdwards/open_pdks；ASAP7 asap.asu.edu
- CMOS p-bit 能量：nature.com/articles/s41467-024-46645-6；mdpi.com/2079-9292/15/12/2510
