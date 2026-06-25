# `eda/` — sMTJ-PBNN 器件-电路协同设计与验证工作区

本目录是把 `smtj_pbnn_sim` 从**纯算法/行为级评估器**推进到**可信电路级验证**的工作区，
并构建二者之间的**接口**：用 EDA (Verilog-A + Spectre/ngspice + 版图/寄生提取) 产出的可信数值，
替换仿真器中被标注为「28nm 数量级占位符」的不成熟内容 (CMOS 外围能量/延迟/面积、IR-drop 空桩)，
并在电路级证实或修正论文的几条承重论断。

## 为什么需要这个目录 (定位)

- `smtj_pbnn_sim` 目前**独立运作**：器件 Sigmoid/Néel-Brown、差分 XNOR-popcount、T 步展开、训练
  都是真实且经晶圆校准的；但 PPA 层除 SOT 写能量 (0.78 pJ, $V^2t/R$) 外，全部外围常数是占位值，
  IR-drop 是空桩，**没有任何晶体管网表 / SPICE / 版图 / PDK**。
- 本工作不是「换个更高级仿真器」，而是**新增一层 + 做接口**：
  器件 Verilog-A 模型 → Spectre/ngspice 电路仿真 → 版图/寄生提取 → 把提取数值**回灌** `smtj_pbnn_sim`。

## 关键事实 (已网络核实，详见 research/)

- **没有任何 PDK 自带可用的 SOT-MTJ**：开源 (sky130/IHP SG13G2) 与 foundry-academic (GF22FDX eMRAM)
  都不含可编辑的 SOT-MTJ。**任何路线都必须自带 Verilog-A 的 MTJ 模型**，CMOS PDK 只做外围。
- **ARM `mram_simulation_framework`** (BSD-3) 是好骨架，但**只支持 STT/VCMA、不含 SOT**——须自行加自旋霍尔写分支。
- **NeuroSim V1.5 无 MTJ 单元** (SRAM/RRAM/FeFET/nvCap)，只能给 CMOS 外围估能耗/面积；sMTJ 写能量须自仿。
- 混合信号结构 (模拟随机写/读核 + 数字 T 步展开环) → 需 **AMS + 实数建模 (RNM)**。
- 随机切换须**事件驱动 + 显式种子** ($rdist on @(cross/timer))，**不能**用裸模拟瞬态噪声。

## 目录结构

```
eda/
├── README.md
├── ROADMAP.md                          # 分阶段计划 (可落实为 agentic 工作流)；与 todo 同步
├── OPEN_SOURCE_FEASIBILITY.md          # ③ ngspice 各阶段可行性矩阵
├── SETUP_opensource.md                 # 开源工具链 (ngspice+OpenVAF) 安装与运行
├── research/
│   ├── 2026-06-26_eda_assessment.md    # 已事实核查的调研报告 (工具选型 + 待办)
│   └── vgsot_integration_decision.md   # ② vgsot-sim 整合决策
├── models/
│   └── smtj_sot.va                     # ★ MIT Verilog-A SOT-sMTJ 紧凑模型 (P1)
├── testbenches/
│   ├── gen_golden.py                   # Python 金标准生成 (已跑: R²=0.9919, 0.78pJ)
│   ├── golden_psw.csv / golden_summary.json
│   ├── regression_psw.spice            # ngspice DC 扫描回归网表
│   └── run_regression.py               # 编译.va+跑ngspice+对金标准断言 (装好工具一键)
├── extraction/                         # 提取的 PPA LUT/能量-面积表 (替换占位符)
└── interface/                          # 回灌 smtj_pbnn_sim 的 Python 胶水 (「新接口」)
```

## 与主仓库的关系 / 接口设计

| `smtj_pbnn_sim` 中的占位/空桩 | `eda/` 中的可信替代 | 接口落点 |
|---|---|---|
| `ppa/tech_params.py` 外围常数 (e_dac/e_read/e_count/a_*) | `extraction/` 提取的能量-面积表 | `interface/` 构造一个由提取值填充的 `TechParams` |
| `ppa/energy.py` `per_mac_energy` | 含真实 ADC/驱动开销的每-MAC 能量 | 同上，重算并回灌 |
| `array/ir_drop.py` (空桩) | `extraction/` PEX 线压降 | 替换 `estimate_ir_drop` 为查表/拟合 |
| `device/` 行为 Sigmoid/telegraph | `models/` Verilog-A 模型 (回归一致) | 双仿真器回归测试 (research §5) |
| `device/variation.py` | + `sigma_sense_offset` 通道 (来自 SA 失配 MC) | 新增变异通道 |

> 接口原则：`smtj_pbnn_sim` 不依赖 `eda/`；`eda/` 单向地把可信常数/查表写入仿真器可读的配置
> (YAML / Python dataclass)，使「替换占位符」是一次**配置注入**而非代码耦合。

## 当前状态

- [x] 调研完成并事实核查 (research/)
- [x] 勘误登记并修复 E1/E2 (`../docs/errata.md`)
- [x] 路线图与 todo 计划 (ROADMAP.md + 会话 todo)
- [x] ② vgsot-sim 整合决策：新写 MIT `.va`，不复用 Hikstor PDK；vgsot 作 submodule 真值参考
- [x] ③ 开源可行性矩阵 (OPEN_SOURCE_FEASIBILITY.md)
- [x] P0 决策：无许可证 → 开源 ngspice 路线；回归目标钉死 0.8958V/0.0234V (errata N1)
- [~] **P1 进行中**：`smtj_sot.va` 已写；Python 金标准已验证 (对实测 46 点 R²=0.9919、写能量 0.783 pJ、τ(0V)=67.8ns)；ngspice 回归脚手架就绪
- [ ] **当前卡点**：装 ngspice≥43 + OpenVAF-Reloaded → `python eda/testbenches/run_regression.py` (见 SETUP_opensource.md)
- [ ] P2–P7：见 ROADMAP.md

## 相关文件

- 调研报告：[`research/2026-06-26_eda_assessment.md`](research/2026-06-26_eda_assessment.md)
- 路线图：[`ROADMAP.md`](ROADMAP.md)
- 勘误：[`../docs/errata.md`](../docs/errata.md)
- 物理标定审计：[`../docs/physics_grounding.md`](../docs/physics_grounding.md)
