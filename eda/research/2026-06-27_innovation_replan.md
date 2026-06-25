# 顶刊标准的创新性重审 (2026-06-27)

> 产出方式：6-智能体工作流（新颖性扫描 / 电路设计 / 期刊定位 / EDA 出图 / 器件-电路协同 + 对抗式新颖性核查），全部联网核实先验工作。
> 触发：用户指出"目前的工作仅在于打通工作流，但没有创新；应根据文章/仿真的新结论反过来做电路设计与优化，并用 EDA 导出原理图/版图"。

## 1. 核心判断

当前 P1–P7 first-cut 是**验证层**（复现标定、确认数字、打通链路）。更尖锐的事实：候选"新电路"在 2024–2026 大多已被做掉，**新颖性不能是"造了个新电路"**。站得住的 delta 有三层：

1. **规格反转**：把读出失调按器件自身 Sigmoid 斜率 V_T=23.4mV（伯努利判决窗口）预算，而非确定性 TMR 余量。
2. **闭环**：提取数 → PyTorch 栈 → 系统精度/能量位移。
3. **反向设计方法学本身**（finding → sky130 PEX 数 → 论断位移 → 闭回算法栈）作为论文级绑定贡献。

## 2. Hero 贡献（旗舰，唯一"strong"）—— C1

**"斜率匹配的 p-bit 读出"：V_T(器件 Sigmoid 斜率) ↔ SA 输入折合失调 的协同设计。**

- 非显然反转：finding (c) 说 V_T 斜率被 BatchNorm 吸收、"对精度无关"；但 V_T 决定读出电路成本——SA 失调=伪装成 V_th 偏移的每列误差，正是 Exp.08 证明致命的那一类。
- 先验空白（已核实）：arXiv:2403.19374（SOT-MRAM PBNN CIM）、HXNOR-PBNN 都建了 PBNN 列但把比较器当理想，从不把 SA 失调关联到器件 Sigmoid 斜率；Nat.Commun. s41467-024-48152-0 研究 p-bit Sigmoid 但非 CIM 读路、非 vs SA 失调。
- 优化：min 读出能量+面积 @ iso-精度(≥97% MNIST)；变量 = {V_T(器件，经势垒/脉宽), SA 失调消除强度(无/单容自调零/两相斩波)}；产出 accuracy-vs-(V_offset/V_T) Pareto。
- 闭环：σ_offset → `device/variation.py` 的 `sigma_sense_offset` 通道 → MNIST 92.8%→~97%；真实 `e_smtj_read` 喂回 P6 接口。**关 errata R2**。

### 捆绑 C2（同一篇"校准半边"，moderate）
**摊销写-DAC：每列 V_th 微调折叠进现有写-DAC。** 因为写占 98.7%、DAC 本在关键路径，校准近乎免费——把论文"DAC 校准+温漂补偿"指令量化落地（3–4 trim bit 恢复 ~97%，代价 <1% 写预算）。自参考闭环复用 C1 的 SA。

## 3. 第二篇 —— C3（moderate）

**RC 等能量三方套利：联合优化 {N, M, b} 的 MC/焦耳**，Δ≈3.8 telegraph 节点 + **列共享低分辨 ADC**。解决 `rc_readout_noise`(读出限制) vs `reservoir_energy`(读出免费) 矛盾，证明 MC-最优读出是廉价低分辨/时域而非 ≥10bit。先验：量化读出 RC 有（arXiv:2604.06075 等）但固定储池只扫 bit；**三方联合 frontier + 设备特定 tau(V) 是新的**。诚实重做 ~38× vs 数字 ESN。

## 4. 降级项（不独立成文，引为先验）

| 候选 | 评级 | 先验/原因 | 去向 |
|---|---|---|---|
| V_th 跟踪写驱动 | incremental | 闭环 sMTJ 概率稳定已发表(Nano Lett.2024/arXiv:2407.08665)；领域转向原位学习(arXiv:2504.14070) | C2 的摊销微调，支撑 |
| 自调零/斩波 SA | likely-done | ISSCC 2018、14nm、专利(US9111623…) | 保留 SA，但卖 V_T 协同预算+闭环 |
| 三位一体可调势垒(C4) | incremental | 器件已被抢先：Kent A-sMTJ arXiv:2509.13458(2025)、HKUST VCMA 双功能宏 VLSI 2026 | 仅作"受限架构可行性包络"子节，引为先验 |
| 自适应-T 早退 | incremental | 教科书随机计算 + 主流早退 | 支撑（量化省写能量） |
| 开源 `.va` 单独成文 | overrated | ARM/Rajpoot 等紧凑模型众多 | 复现性支柱，附于 hero |

## 5. 目标期刊

**IEEE TCAS-I / TVLSI / TED。不投 Nature Electronics / ISSCC** —— 它们 2025 已发表实测 130nm CMOS p-bit ASIC（Nat.Electron. s41928-025-01439-6、s41928-025-01458-3），sky130 纯仿/开源 PEX 会秒拒。晶圆校准的 46 点模型是让 TCAS-I 可信的近硅锚点。

## 6. 重排的创新优先计划（替换验证优先 P1–P7）

- **Phase 0 网关**：WSL2 上 IIC-OSIC-TOOLS Docker（Xschem/Magic/Netgen/ngspice + sky130A），共享 OpenVAF `.osdi`。解锁 P4/P5 的版图/GDS/PEX。
- **Phase 1 Hero (~60%)**：C1+C2 —— 设计+优化+版图+PEX 斜率匹配 SA + 摊销写-DAC；闭环到 MNIST。全工件集 + hero 图。
- **Phase 2 第二篇**：C3 —— 扩展 `rc_readout_noise.py` 出 MC/焦耳等高线 + 一个 sky130 TIA+低分辨 ADC 切片（提取能量），修复 R6。
- **Phase 3 支撑(不独立)**：旧 P2/P3 数字确认、V_th 驱动、自适应-T、开源 `.va` → 支撑/支柱。
- **纪律**：阵列只到单列/原理图标注级；绝不做 256×256 全 DRC-clean GDS。

## 7. 最小可投稿工件集（用户要的"导出原理图/版图"）

1. Xschem 原理图+`.sym`+测试台（SA 在 2T2MTJ 列，与 `smtj_sot.va` 经 `.osdi` 共仿）→ SVG/PDF。
2. ngspice MC（≥200–500 次，种子记录；RNG 在 Python harness）：失调分布 overlay 在 V_T=23.4mV 线 + popcount 误差 vs N（对照 P3 的 0.06√N）。
3. Magic DRC-clean 版图(`.mag`) + Netgen LVS（MTJ 两侧网表一致打桩）+ KLayout DRC + 面积(µm²)。
4. **GDS**：sky130 真实 CMOS 层做外围 + **MTJ 作显式标注的黑盒抽象 cell（非工艺 datatype）+ "layout-intent/不可制造"声明**。
5. Magic ext2spice 电容 PEX → tt/ss/ff 后仿（失调/延迟/能量含寄生）。
6. **Hero 闭环图**：σ_offset → `interface/load_tech_params.py` → MNIST 92.8%→~97% @ iso 读能 + 修正 `e_smtj_read` 重跑 P6 PPA。

## 8. 必写的诚实支柱（否则被拒）

1. RNG 留 Python harness（OpenVAF 不能 `$rdist/@cross`）—— 随机后仿共仿 #1 风险，未去风险。
2. sky130=130nm/1.8V → 所有结论用**比值**（V_offset/V_T、MC/焦耳、能量占比），绝不报绝对值（130nm 失调会更大，故事更强但要诚实测）。
3. Magic PEX：电容够用，**电阻/IR 粗集总、串扰/VPP 未建模** → 776Ω 写线 IR 与 BL/WL RC 仅量级级，低于商用(Quantus/StarRC)。
4. 能量基准用端到端 **~6.95 pJ/bit**，停止单引未证实的 5 pJ（errata R5）。
5. `.va` 在 RC 低势垒区重参数化、未独立晶圆验证 → 写成限制。
6. 投稿前做 2025–2026 ISSCC/IEDM/VLSI 定向检索（p-bit 领域快，如 CMOS 集成 sMTJ p-bit arXiv:2604.14446, 2026）。

## 主要先验来源
- 实测 CMOS p-bit ASIC：Nat.Electron. s41928-025-01439-6、s41928-025-01458-3 (2025)
- 闭环 sMTJ：Nano Lett. 2024 / arXiv:2407.08665；原位学习 CMOS p-bit arXiv:2504.14070
- 可调势垒器件：Kent A-sMTJ arXiv:2509.13458 (2025)；HKUST VCMA 双功能宏 VLSI 2026
- PBNN-CIM：arXiv:2403.19374；HXNOR-PBNN；p-bit Sigmoid 协同 Nat.Commun. s41467-024-48152-0
- 失调消除 SA：ISSCC 2018 (Dong)；专利 US9111623/US10726897B1
- 量化 RC 读出：arXiv:2604.06075；ADC 能量模型 arXiv:2404.06553；MC~√N Sci.Rep. s41598-017-10257-6
- 开源流程：IIC-OSIC-TOOLS (github.com/iic-jku/iic-osic-tools)；Magic PEX (opencircuitdesign.com)
