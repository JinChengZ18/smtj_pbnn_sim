# 子模块设计空间调研与方案对比 (2026-06-29)

> 指令③：开多智能体子代理从 arXiv / 开放获取期刊提取各电路子模块的同类设计，做多方案性能对比，
> 论证针对本任务（sMTJ-PBNN/RC，sky130 130nm，V_T≈23mV 判决窗、低阻 776Ω SOT 写线、读出 ADC 主导能耗）
> 为何这样设计、有哪些优点。同时为偏薄的对照图（如 Chapter04_local_18）提供更多数据点。
>
> 来源工作流 `wf_3df4813c-07b`（6 智能体：3 调研 + 3 对比，254k tokens，85 工具调用，含 WebSearch/WebFetch）。
> **结构化原始数据**（每子模块 6 篇真实文献 + 两轴对比 + 论证 + figure_data）：
> [`../../../eda/design_survey/submodule_survey.json`](../../../eda/design_survey/submodule_survey.json)。
> **对照图**：各子模块的设计空间对比已作为子图 (c) 内嵌于 `Chapter04_local_16`（读出 SA）、
> `Chapter04_local_18`（写线 IR 预畸变）、`Chapter05_local_09`（列共享 SAR），由
> [`../../../eda/gen_supplement_figs.py`](../../../eda/gen_supplement_figs.py) 的 `design_cmp_panel()`
> 直接在图内标注（不用 legend）生成，再经 `article/ppt/` 的链路加 (a)(b)(c) 并入 `article/figs/`。

引用核验说明：以下均为子代理经 WebSearch/WebFetch 找到的真实论文；少数仅有摘要/付费正文的条目，其
**数值**（mV 失调、fJ/op、节点）已在 JSON 中标 *unverified*，引入论文时须复核或仅作定性引用。

## 1. 读出灵敏放大器（C1：斜率匹配 TIA + StrongARM）

**方案对比轴**：输入折合失调 / V_T（越小越好） vs 每次判决读出能量（fJ）。

| 选项 | 失调/V_T (σ) | 读出能量 | 备注 |
|---|---|---|---|
| **本文**（斜率匹配 TIA+StrongARM, sky130, plain + 写-DAC trim） | **0.39** | **48 fJ** | 唯一把失调按绝对 V_T 窗口预算、并处理 SOT 写线 IR 的方案 |
| 单帽自调零两级电压 SA（28nm STT-MRAM, Dong ISSCC 2018） | 0.32 | ~30 fJ | 同样针对低 TMR 小窗；但单比特存储读、无 popcount/ADC 摊销 |
| 电荷舵双尾动态比较器（28nm, JPCS 2022） | 0.29 | 5.4 fJ | σ=6.9mV；显式指出 StrongARM 受共模/裕度限制 → 双尾为升级路径 |
| Xcel-RAM 10T-SRAM XNOR + 双级 ADC（TCAS-I 2019） | ~1（ADC-LSB 级） | 1914 fJ | 直接含 XNOR-popcount + ADC 摊销（分区）；电荷域 SRAM |
| 单片 RRAM+CMOS XNOR-BNN, 共享 flash ADC（Yin/Yu TED 2020） | ~1 | ~250 fJ | 最近的电阻 CIM 类比：98.5% MNIST、24 TOPS/W |
| 电流采样失调容忍 SA, 小电流 NVM（Chang JSSC 2013） | ~0.6* | ~80 fJ* | *数值未核实；电流模分支，小电流regime相关 |

**为何本设计**（要点）：读出难点不是 TMR 余量而是 V_T≈23mV 绝对窗内取样 → 把失调"规格反演"地预算到
V_T（斜率匹配跨阻 R_TI=V_in/(2·PC_FS·LSB_I) 把 mV 失调线性折算为 popcount LSB；sky130 MC σ=9.21mV=0.39V_T
→ σ_pc≈2–4）。项目 Pareto 已证 plain StrongARM 在 V_in≥0.5V、MNIST 扇入下为 Pareto 最优（精度损失落在
单次噪声内），自调零/斩波仅在低 V_in/宽扇入角点才挣回 1.7× 能量；残余每列系统失调用既有写-DAC 3–4 trim-bit
近免费抵消。相对 Dong/双尾/Chang，本方案在同一 V_T 归一化轴上失调相近，但独有：失调按绝对 V_T 预算、写-DAC
trim 摊销、显式处理 776Ω 低阻写线 IR。

## 2. 写驱动 + DAC + 逐行 IR 预畸变（C2）

**对比轴**：N=256 高列远端残余写电压误差（mV，越低越好；V_T=23mV 参考） vs 电路层完整度（DAC 拓扑+稳压轨+能量账，0–5）。

| 选项 | 残余误差 | 完整度 | 备注 |
|---|---|---|---|
| **本文**（电阻串写-DAC + 逐行 IR 预畸变 + 稳压 0.9V 轨 + 列 trim） | **12 mV** | **5** | 唯一给出二值 SOT P_sw 逐行 IR 补偿 + 拓扑/轨/能量账 |
| Truong 2019（寄生电阻自适应编程，建模后预畸变）MDPI Materials | 26 mV | 1 | 最接近的"建模寄生再开环预畸变"思路；纯算法/SPICE 模型，3Ω 线阻下保 ~100% |
| Zhu 2020（SPICE 线阻预补偿，位置电压抬升）IET CDS | 30 mV | 1 | 给出 far-cell droop ~N_col² 标度律 |
| Kim 2021（迭代注水写保真优化）arXiv 2112.02842 | 148 mV | 0 | 重要性加权非均匀写能量，~40% 写能省；纯编码层、不处理 IR |
| Cassuto 2019（1S1R 高线阻写信道模型, V/2 vs V/3）arXiv 1912.02963 | 148 mV | 0 | 形式化位置相关衰减；高阻 RRAM regime（与我们低阻相反） |
| VECOM 2023（变异韧性编码 + SA 失调补偿）ICCAD/arXiv 2312.11042 | 148 mV | 1 | 窄窗+trim 纪律，但读侧 trim、不碰写线 |
| Yoon 2026（130nm CMOS 集成 sMTJ p-bit 栅压驱动）arXiv 2604.14446 | 148 mV | 2 | 同 130nm+低势垒 sMTJ；锚定 mV 级偏置分辨率与可变阈值 trim；单器件无阵列 IR |

**为何本设计**：低阻 SOT 写线（R_SOT=776Ω 与列写线寄生同量级）在 N=256 高列上提取标定给出约 148mV（16.5%）IR 压降，
把远端写点拉到 ~0.75V 跌破 0.896V 标定点，沿 P_sw Sigmoid 抬高远端写错误——而 V_T 仅 23mV，148mV 远超一个判决窗。
文献给两半（Truong/Zhu 的开环位置预畸变思路 + N² 标度律；Kim 的写能量优化）但都停在模型/编码层、无电路实现；
本设计在电路层合一：电阻串写-DAC + 逐行 I_wr·R_par(row) 预畸变 + 稳压 0.9V 轨（ngspice+sky130 显示 1.8V 驱动入 776Ω
约一半能量丢在 Ron 分压、端到端 ~1.6pJ；稳压轨拉回接近 0.783pJ Ohmic 基线）+ 列 trim。

## 3. 列共享时分复用 SAR ADC 读出（C3）

**对比轴**：SA 失调 / V_T（0=文献未报） vs 比较器/读出能量（fJ）。

| 选项 | 失调/V_T | 能量 | 备注 |
|---|---|---|---|
| **本文**（列共享时分 SAR：1 StrongARM + 电荷再分配 cap-DAC，跨 M 节点摊销） | **0.39** | **48 fJ**（比较器 b-线性项） | 唯一含已提取比较器能量 + 对 V_T 预算的失调 |
| Liu/Zhang 2023 列并行时分 SAR/SS 混合（可重构 2–8b, 55nm） | 0（未报） | 44.8 fJ/conv-step | 最接近的共享拓扑；但 SAR/SS 混合需全局斜坡块 |
| PICO-RAM 2024 电荷域 CIM + 时域 ADC + 比较器门控 | 0（"minimal"） | -55.8%（门控省能） | 最强"比较器主导能耗"佐证；时域门控=我们空间共享的时域对偶 |
| Murmann 数据集 ADC 能量/面积回归（Krishnan/Cao 2024） | 0 | 整器 ~2×/bit | 关键外部校验：整器能耗随 ENOB 指数增；我们的 b-线性仅指比较器分量 |
| StrongARM-for-SAR 失调优化（arXiv 2209.07259, 2022） | 0（仅相对） | — | 同比较器族；强调失调是设计关键参数 |
| 忆阻全模拟 RC, ADC 在读出边界（Zhong/Wu, Nat. Electron. 2022） | 0 | — | 同 RC 语境确认 ADC 是待摊销的能耗/延迟开销 |
| 图像传感器列并行两步 SAR/SS（Kim/Kwon ~2018） | 0（CDS） | — | 列共享摊销的架构先祖；CDS 失调不可移植到固定 V_T 窗 |

**为何本设计**：分项能量提取显示比较器占读出能量 88–99%（即使 b=3），且随 b 线性（非 2^b）——与 Murmann"整器随 ENOB
指数"不矛盾（我们的线性仅指比较器分量；cap-DAC 在 b=8 时已与比较器相当）。故真正杠杆是把主导比较器跨列/跨节点
时分复用（列共享 M=N/4 → ADC 仅占 RC 能量约 6%），中分辨 b~8 可负担，相对数字 ESN 保持 ~30–35×。相对 Liu/Zhang
与 PICO-RAM，本设计用纯电荷再分配 cap-DAC 省去全局斜坡块、且唯一给出针对 23mV 窗的显式失调预算。

## 引用清单（真实，待引入论文时复核 unverified 数值）

- Dong et al., "A 1Mb 28nm STT-MRAM ... Single-Cap Offset-Cancelled SA ...," ISSCC 2018 (JSSC 2019).
- "Double-Tail Dynamic Comparator Based on Charge-Steering," J. Phys.: Conf. Ser. 2405:012014, 2022.
- Agrawal et al., "Xcel-RAM," arXiv:1807.00343, 2018 (TCAS-I 2019).
- Yin, Sun, Yu, Seo, "High-Throughput IMC for BNNs with Monolithic RRAM+90nm CMOS," arXiv:1909.07514 (TED 2020).
- Zhang, Ando, Chen, Yoshioka, "ASiM," arXiv:2411.11022, 2024.
- Chang et al., "Offset-Tolerant Current-Sampling SA for Small-Cell-Current NVM," JSSC 2013 *(metrics unverified)*.
- Truong, "Parasitic Resistance-Adapted Programming," Materials 12(24):4097, 2019, doi:10.3390/ma12244097.
- Zhu et al., "Solution to alleviate line resistance on the crossbar array," IET CDS 14(4):498–504, 2020.
- Kim, Jeon, Choi, Guyot, Cassuto, "Optimizing Write Fidelity of MRAMs via Iterative Water-filling," arXiv:2112.02842, 2021.
- Cassuto et al., "Write/Read Channel Models for 1S1R Crossbar ... High Line Resistance," arXiv:1912.02963, 2019 *(author list unverified)*.
- Jang, Nguyen, Yang, "VECOM," ICCAD 2023 / arXiv:2312.11042 *(offset mV unverified)*.
- Yoon et al., "CMOS-integrated superparamagnetic tunnel junction-based p-bit," arXiv:2604.14446, 2026.
- Liu et al. (Zhang group), "Column-Parallel Time-Interleaved SAR/SS ADC for CIM, 2–8b," 2023 *(DOI unconfirmed)*.
- Zhang et al., "PICO-RAM," arXiv:2407.12829, 2024.
- Krishnan/Cao group, "Modeling ADC Energy and Area for CIM," arXiv:2404.06553, 2024.
- "StrongARM Dynamic-Latch Comparator for SAR-ADC," arXiv:2209.07259, 2022 *(absolute metrics unverified)*.
- Zhong, Tang, ..., Wu et al., "Memristor-based analogue reservoir computing," Nat. Electron. 5:672–681, 2022 *(paywalled; ADC details unverified)*.
- Kim, Hong, Kwon, "Column-Parallel Two-Step SAR/SS ADC for CMOS Image Sensors," ~2018 *(venue/DOI unconfirmed)*.
