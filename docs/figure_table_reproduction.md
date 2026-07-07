# 图表复现指南

本文把学位论文正文 (第 1、4、5 章) 与附录 B/C/D 中的每一张图、每一张表对应到仓库中可运行的生成脚本、运行命令、原始产出文件与 (对表而言) 已入库的数据源，供复核与重跑。面向读者的简版复现入口见 `article/appendix_A_code_availability.md` §A.3；本文是其完整对照。所有命令均从仓库根目录运行 (电路原理图的 WSL 步骤除外，另见对应小节)。

## 1. 运行环境

Python 3.10 及以上，编辑式安装即可导入仿真包：`pip install -e .`。核心依赖为 torch、numpy、scipy、matplotlib、pandas、PyYAML。安装后实验以 `python experiments/NN_name.py` 运行；若未做编辑式安装，命令前加 `PYTHONPATH=src`。

图的编号与合成额外需要 python-pptx、PyMuPDF (`import fitz`)、Pillow，以及 LibreOffice (`C:/Program Files/LibreOffice/program/soffice.exe`)。

第 4.6 节与附录 D 的电路级数值 (Family B) 需要开源 EDA 工具链，本文在 WSL Ubuntu 下运行：ngspice ≥ 43 (启用 OSDI)、OpenVAF-Reloaded、SkyWater sky130A PDK、Xschem、Magic、Netgen、KLayout、cairosvg。发行版名为 `Ubuntu-24.04-EDA`，安装与版本约束见 `eda/SETUP_opensource.md`。纯解析的 EDA 脚本 (写能量、SAR 电容能量等) 只需 python3 + numpy。

按是否需要 torch 分：

- 无需 torch：`01_device_calibration`、`02_wafer_average_mc`、`03_nb_cross_pulse_width`、`04_ppa_breakdown`、`13_training_energy` (解析能量模型)；Family B 的 EDA 分析面板在已入库 JSON 上离线复现时亦不需 torch。
- 需要 torch：`05`、`06`、`07`、`08` (Part 2)、`09`、`10` (首次运行需联网下载 UCI)、`11`、`12`，以及卷积扩展 `05a_*`、`06a_*` 与 `21_seed_independence`。

数据集：MNIST、Fashion-MNIST、CIFAR-10 由 torchvision 自动下载，UCI 表格任务由 `10_uci_benchmarks.py` 首次运行时联网获取；器件标定靶值随库分发于 `data/smtj_psw_curves/measured_0p75ns.csv`，不需下载。

## 2. 复现流水线

论文正文各图的最终资产统一命名为 `article/figs/Chapter0*_local_NN.png`；附录图命名为 `article/figs/Appendix{B,C,D}_NN.*`。生成器分三类，编号资产的产生有以下几条路径。

三类生成器：

- **Family A — 数据图/表**：`experiments/NN_name.py` 画出原始图到 `figures/NN_*.png`，并把表所依据的数值写入 `runs/<name>_<时间戳>/*.csv`。
- **Family B — EDA 电路图/表**：`eda/` 下的电路原理图脚本与器件-电路协同分析脚本，需要 WSL EDA 工具链重算底层数值，但由已入库结果 JSON 可离线重画。
- **Family C — 概念/原理图**：`demo/*.py` 与 `article/figs/make_fig_*.py`，纯 matplotlib 绘制，数据点取自文献并硬编码，无需 torch/数据集。

原始图变为编号资产的几条路径：

1. **章节 deck 合成 (最常见)**：原始无字母面板经 `article/ppt/Chapter0*_local.pptx` 合成，面板字母 `(a)(b)(c)` 在 deck 中添加、不烘焙进原图，再裁剪导出为编号 PNG。第 4、5 章绝大多数 Family A 图为此路径 (由用户手工维护的 deck 合成)。
2. **脚本直接写编号资产**：少数脚本直接写出 `Chapter0*_local_NN.png`，不经 deck，见下表标注。
3. **附录 B/C 复制改名**：附录图不经任何 deck，`figures/…png` 与 `article/figs/Appendix{B,C}_NN.png` 字节完全一致，为手工复制改名编号。
4. **附录 D / 电路原理图**：由 `postprocess_schematic_svg.py` 直接写出编号 SVG，再由 cairosvg 光栅化，不经 deck。

### 2.1 电路原理图通用流程 (Family B，需 WSL)

第 4.14、4.18、5.8 图与附录 D 的原理图 (D.1–D.7、D.9、D.10) 共用四步。以脚本内约定的短名 `<base>` 为参数：

1. `python eda/hero/schematics/gen_<base>_sch.py` — 纯 Python 写出 `eda/hero/schematics/<base>.sch` 网表。
2. WSL：`bash eda/hero/schematics/build_schematics.sh <base>.sch` — Xschem 导出 `<base>.svg`，cairosvg 光栅化 `<base>.png/.pdf` (原始未裁剪，PNG 默认 2400 px 宽)。
3. `python eda/hero/schematics/postprocess_schematic_svg.py <base>` — 裁剪 viewBox、叠加彩色虚线模块框、下标化标签，写出编号 `article/figs/<编号>.svg` (`<base>`→`<编号>` 映射硬编码在该脚本的 `GROUPS` 字典中)。
4. WSL cairosvg：把编号 `.svg` 光栅化为编号 `.png/.pdf`。

`<base>`→编号映射：`strongarm_sa`→Chapter04_local_14；`writepath`→Chapter04_local_18；`sar_readout`→Chapter05_local_08；`double_tail`→AppendixD_01；`dsa`→AppendixD_02；`current_sampling`→AppendixD_03；`dong_autozero`→AppendixD_04；`current_steering_dac`→AppendixD_05；`r2r_dac`→AppendixD_06；`yoon_pbit_driver`→AppendixD_07；`rram_flash_slice`→AppendixD_09；`picoram_gating`→AppendixD_10。

### 2.2 EDA 分析面板通用流程 (Family B)

第 4.15、4.16、4.17 图与 5.9 图 (器件-电路协同分析面板) 由两条命令按顺序重建：

```
python eda/gen_supplement_figs.py && python eda/build_ppt_figs.py
```

`gen_supplement_figs.py` 从已入库的结果 JSON 确定性地画出无字母面板到 `figures/panels/ch0*_NN_*.png` (headless matplotlib，无需 WSL)，并把无字母的合成图直接写入 `article/figs/` 作占位。`build_ppt_figs.py` 把面板追加进 `article/ppt/Chapter0*_local.pptx`，在 deck 中加 `(a)(b)(c)`，经 LibreOffice→PDF→PyMuPDF 裁剪，覆盖写出带字母的编号资产。必须按顺序跑两条命令；只跑第一条会在 `article/figs/` 留下无字母占位图。重算底层 JSON 才需 WSL 下的 ngspice / Magic / vgsot-sim；由已入库 JSON 重画则完全离线。例外：图 4.21 为单面板，`gen_supplement_figs.py` 直接写入 `article/figs/Chapter04_local_21.png`，不进 deck。

### 2.3 表格数值的核对

`runs/` 下已入库对应实验的结果 CSV/JSON，因此表格数值可直接从已入库文件核对，无需重跑 torch/GPU 实验。同一实验有多个时间戳 run 时，下表给出与文章口径一致的规范 run 目录。附录 D 的比较表由 `eda/design_survey/comparison_results.json` 及各 `*_summary.json` 重建，同样无需重跑电路仿真。

## 3. 第 1 章 (Family C，概念图)

| 编号 | 标题 | 生成脚本 · 命令 | 原始产出 → 编号资产 | 依赖/备注 |
|---|---|---|---|---|
| 图 1.1 | AI 规模演进与冯诺依曼架构的能耗结构 | `article/figs/make_fig_scaling.py` · `cd article/figs && python make_fig_scaling.py` | `fig_scaling_gap.png` → (Chapter01_local.pptx) → `Chapter01_local_01.png` | matplotlib/numpy；数据点硬编码 (Horowitz 2014 / Sze 2020 / NVIDIA)；按相对路径写出，须先 cd |
| 图 1.2 | 二值随机模型的发展脉络与两类用法 | `article/figs/make_fig_lineage.py` · `python article/figs/make_fig_lineage.py` | 直接写 `Chapter01_local_02.png` (+`fig_lineage.pdf`) | 纯手绘概念图；不经 deck |
| 图 1.3 | PBNN 前向流水线及空间/时域展开对比 | `article/figs/make_fig_spacetime.py` · `cd article/figs && python make_fig_spacetime.py` | `fig_space_time.png` → (Chapter01_local.pptx) → `Chapter01_local_03.png` | 同图 1.1；须先 cd |
| 表 1.1 | PBNN 算法需求与 sMTJ 器件物理属性的对应关系 | 无生成器 (手写) | `article/chapter01.md` 内联表 (L199–206) | 定性概念表，文献引用支撑，无数据源 |

## 4. 第 4 章

### 4.1 图 4.1–4.21

| 编号 | 标题 | 生成脚本 · 命令 | 原始产出 → 编号资产 | 依赖/备注 |
|---|---|---|---|---|
| 图 4.1 | 单层闭环前向的硬件实现示意 | `demo/04_pbnn_hardware_principle.py` · `python demo/04_pbnn_hardware_principle.py` | 直接写 `Chapter04_local_01.png` (+.pdf) | 概念图，纯 matplotlib |
| 图 4.2 | 分层硬件仿真器的模块组织 | `demo/01_simulator_framework.py` · `python demo/01_simulator_framework.py` | `demo/figures/01_simulator_framework.png` → (Chapter04_local.pptx，编辑后合成) → `Chapter04_local_02.png` | ⚠ 现 HEAD 脚本输出与已入库资产不一致，重跑不能精确复现；见 §7 |
| 图 4.3 | MNIST 上 PBNN-MLP 的端到端验证 (a/b/c) | `experiments/05_mnist_pbnn.py` + `experiments/06_sweep_T_vs_accuracy.py` (+ `demo/02_pbnn_mlp_architecture.py`) | 面板 b=`figures/05_mnist_training_curves.png`，c=`figures/06_sweep_T.png`，a=`demo/figures/02_pbnn_mlp_architecture.png` → (deck) → `Chapter04_local_03.png` | 多源合成图；torch + MNIST |
| 图 4.4 | UCI 六类表格任务上的训练曲线 | `experiments/10_uci_benchmarks.py` | `figures/10_uci_accuracy_curves.png` → `Chapter04_local_04.png` | torch；首次联网下载 UCI；另产 `10_uci_residual_curves.png` (副产物，未入图) |
| 图 4.5 | 优化器与学习率调度的对比 (a/b) | `experiments/11_optimizer_scheduler_study.py` | `figures/11a_optimizers.png` + `11b_schedulers.png` → `Chapter04_local_05.png` | torch + MNIST |
| 图 4.6 | 损失景观与 checkpoint 轨迹 (a/b/c) | `experiments/12_loss_landscape.py` | `figures/12a_landscape_contours.png` + `12b_pca_trajectories.png` + `12c_optimum_interp.png` → `Chapter04_local_06.png` | torch + MNIST |
| 图 4.7 | 八类输入扰动在单个 MNIST 样本上的可视化 | `demo/03_mnist_noise_grid.py` · `python demo/03_mnist_noise_grid.py` | `demo/figures/03_mnist_noise_grid.png` → `Chapter04_local_07.png` | 真正生成器为 demo/03 (非 exp 07/08) |
| 图 4.8 | PBNN、BNN、FP-NN 在八类扰动下的精度衰减 | `experiments/07_baseline_comparison.py` | `figures/07_baseline_noise_robustness.png` → `Chapter04_local_08.png` | 曲线数据同落 `runs/07_baseline_*/noise_*.csv` (即表 4.4) |
| 图 4.9 | 概率二值编码与数字 MRAM 位编码的比特价值对比 | `demo/04_encoding_comparison.py` · `python demo/04_encoding_comparison.py` | `demo/figures/04_encoding_comparison_fixed.png` → (deck) → `Chapter04_local_09.png` | 概念/编码图 |
| 图 4.10 | 硬件比特翻转鲁棒性扫描 (a/b/c) | `experiments/09_hardware_bitflip.py` | `figures/09a_per_bit_sensitivity.png` + `09b_bitflip_accuracy.png` + `09c_effective_error_dist.png` → `Chapter04_local_10.png` | torch + MNIST |
| 图 4.11 | 非理想性对 sMTJ Sigmoid 响应曲线的影响 | `experiments/08_nonideality_ablation.py` (Part 1) | `figures/08a_psw_nonideality_curves.png` → `Chapter04_local_11.png` | 解析曲线，无需 torch |
| 图 4.12 | 非理想性消融下的测试精度 | `experiments/08_nonideality_ablation.py` (Part 2) | `figures/08b_nonideality_accuracy.png` → `Chapter04_local_12.png` | torch + MNIST；同 run 另写六个 `sweep_*.csv` |
| 图 4.13 | 九种存储器架构训练总能耗对比 | `experiments/13_training_energy.py` | `figures/13a_training_energy_breakdown.png` → (Chapter04_local.pptx slide 13 换图) → `Chapter04_local_13.png` | 解析能量模型，无需 torch；数值同表 4.6 (2026-07-08 起与规范 run 一致) |
| 图 4.14 | StrongARM 灵敏放大器电路 | 电路原理图流程 (§2.1)，`<base>=strongarm_sa` | → `Chapter04_local_14.{svg,png,pdf}` | WSL EDA 工具链 |
| 图 4.15 | 斜率匹配读出的失调预算与帕累托 (a/b/c) | EDA 分析面板流程 (§2.2)，`gen_supplement_figs.py` fig2 | `figures/panels/ch04_15_*` → (build_ppt_figs) → `Chapter04_local_15.png` | 数据源 `eda/hero/offset_mc_summary.json`、`pareto_offset_cancellation_summary.json`、`comparison_results.json`；离线可复现 |
| 图 4.16 | 写通路能量与供电完整性 (a/b) | EDA 分析面板流程，`gen_supplement_figs.py` fig3 | `figures/panels/ch04_16_*` → `Chapter04_local_16.png` | 数据源 `eda/extraction/writeline/ir_drop_summary.json`；面板 b 的驱动数为 fig3 内联 ngspice 实测数组 |
| 图 4.17 | IR 感知逐行写预畸变 (a/b/c) | EDA 分析面板流程，`gen_supplement_figs.py` fig5 | `figures/panels/ch04_17_*` → `Chapter04_local_17.png` | 数据源 `eda/hero/ir_aware_writedac_summary.json` + `comparison_results.json`；配套实验 `experiments/20_write_ir_drop.py` (非本图生成器) |
| 图 4.18 | 写通路电路 | 电路原理图流程 (§2.1)，`<base>=writepath` | → `Chapter04_local_18.{svg,png,pdf}` | WSL EDA 工具链 |
| 图 4.19 | 三类操作的瞬态波形 | `eda/testbenches/plot_waveforms.py` · `python eda/testbenches/plot_waveforms.py` | 脚本写 `Supplement_local_11.{png,svg,pdf}`，须改名为 `Chapter04_local_19.*` | ⚠ 目标名陈旧，见 §7；数据源 `write_tran.csv`/`sa_tran.csv` (ngspice 瞬态) |
| 图 4.20 | 工作模式流水线与相位时序 | `eda/testbenches/plot_pipeline.py` · `python eda/testbenches/plot_pipeline.py` | 直接写 `Chapter04_local_20.{png,svg,pdf}` | 概念/时序图，纯 matplotlib |
| 图 4.21 | 器件双模型一致性 | `eda/gen_supplement_figs.py` fig1 · `python eda/gen_supplement_figs.py` | 直接写 `Chapter04_local_21.png` (单面板，不经 deck) | 数据源 `eda/testbenches/llg_validate_summary.json` + `golden_psw.csv`；底层重算需 `eda/vendor/vgsot-sim` (LLG)，不需 ngspice |

### 4.2 表 4.1–4.6

| 编号 | 标题 | 生成脚本 · 命令 | 数据来源 (已入库 run) | 依赖/备注 |
|---|---|---|---|---|
| 表 4.1 | 不同采样次数下 MNIST PBNN-MLP 全栈推理精度与能耗 | `experiments/06_sweep_T_vs_accuracy.py` | `runs/06_sweep_T_20260502_054343/results.csv` (列 T, accuracy, energy_uJ) | 逐行核对一致；依赖 `runs/mnist_pbnn_mlp/best.pt` |
| 表 4.2 | MNIST 上 PBNN-MLP、BNN-MLP 与 QAT FP-MLP 的最佳测试精度 | `experiments/05_mnist_pbnn.py` | `runs/05_mnist_pbnn_20260509_092543/{summary.json, fp_*_metrics.csv}` | PBNN 96.98%、FP32/INT8/INT4/INT2=98.51/98.33/98.43/98.21% 已核对；⚠ BNN 行 97.05% 数据源缺口，见 §7 |
| 表 4.3 | PBNN-MLP 在六类 UCI 表格任务上的迁移精度 | `experiments/10_uci_benchmarks.py` | `runs/10_uci_20260502_071140/summary.csv` (列 pbnn_best_acc, fp_best_acc, ref_baseline) | 六行逐行核对一致 |
| 表 4.4 | 八类输入、权重与对抗扰动下的 MNIST 测试精度 | `experiments/07_baseline_comparison.py` | `runs/07_baseline_20260511_192151/noise_*.csv` (8 个文件) | 列 param, pbnn_T4, bnn, fp |
| 表 4.5 | 均匀单比特翻转率下不同权重编码的 MNIST 测试精度 | `experiments/09_hardware_bitflip.py` | `runs/09_hardware_bitflip_20260502_061419/bitflip_sweep.csv` (列 p_flip, pbnn_T8, pbnn_T64, bnn, fp_8bit) | 八行逐行核对一致 |
| 表 4.6 | 九种存储器/p-bit 架构的训练能耗分解 | `experiments/13_training_energy.py` | 规范 run `runs/13_training_energy_20260706_225408/breakdown.csv` (列 forward_J, backward_J, write_or_theta_J, total_J) | 2026-07-08 已修正：文章值与规范 run 一致，见 §7 |

## 5. 第 5 章 (无编号表)

| 编号 | 标题 | 生成脚本 · 命令 | 原始产出 → 编号资产 | 依赖/备注 |
|---|---|---|---|---|
| 图 5.1 | 基于随机 sMTJ 节点的储备池计算原理 | `demo/05_reservoir_computing_principle.py` · `python demo/05_reservoir_computing_principle.py` | `demo/figures/05_reservoir_computing_principle.png` → (Chapter05_local.pptx) → `Chapter05_local_01.png` | Family C；numpy/matplotlib + reservoir 模块 |
| 图 5.2 | sMTJ 储备池计算原型 | `experiments/14_rc_prototype.py` | `figures/14_rc_prototype.png` → `Chapter05_local_02.png` | 指标仅打印 stdout，无 CSV |
| 图 5.3 | 面向 RC 的器件优化指导 | `experiments/15_rc_device_optimization.py` | `figures/15_rc_device_optimization.png` → `Chapter05_local_03.png` | 同上 |
| 图 5.4 | 温度依赖与时钟补偿 | `experiments/19_rc_temperature.py` | `figures/19_rc_temperature.png` → `Chapter05_local_04.png` | ⚠ 实验-图号偏移 (exp 19→图 5.4)；见 §7 |
| 图 5.5 | 储备池的变异容忍与噪声极限 | `experiments/17_rc_robustness.py` | `figures/17_rc_robustness.png` → `Chapter05_local_05.png` | exp 17→图 5.5 |
| 图 5.6 | 基准广度与处理容量 | `experiments/18_rc_benchmarks.py` | `figures/18_rc_benchmarks.png` → `Chapter05_local_06.png` | exp 18→图 5.6；容量为 summed-r² 代理 (非 Dambre IPC) |
| 图 5.7 | 储备池的硬件 PPA 评估 | `experiments/16_rc_hardware_ppa.py` | `figures/16_rc_hardware_ppa.png` → `Chapter05_local_07.png` | exp 16→图 5.7；亦为图 5.9 的能量依据 |
| 图 5.8 | 列共享逐次逼近读出电路 | 电路原理图流程 (§2.1)，`<base>=sar_readout` | → `Chapter05_local_08.{svg,png,pdf}` | WSL EDA 工具链 |
| 图 5.9 | 储备池读出的能量—记忆容量协同 (a/b/c) | EDA 分析面板流程 (§2.2)，`gen_supplement_figs.py` fig4 | `figures/panels/ch05_09_*` → (build_ppt_figs) → `Chapter05_local_09.png` (fig4 亦直接写合成图) | 数据源 `eda/testbenches/rc_isoenergy_summary.json`、`rc_energy_recompute_summary.json`、`comparison_results.json` |
| 图 5.10 | 由器件到系统的整体架构层次 | `eda/hero/schematics/gen_arch2.py` · `python eda/hero/schematics/gen_arch2.py` 后 cairosvg 光栅化 | `eda/hero/schematics/arch_stack.svg` (+光栅化 png/pdf) → `Chapter05_local_10.png` | 纯 Python 构建 SVG，非 Xschem；不经 `build_schematics.sh` |

## 6. 附录 B / C / D

### 6.1 附录 B (PBNN-CNN 扩展，Family A，复制改名编号)

| 编号 | 标题 | 生成脚本 · 命令 | 产出/数据源 | 依赖/备注 |
|---|---|---|---|---|
| 图 B.1 | Fashion-MNIST 上 PBNN-CNN 与基线的训练曲线 | `experiments/05a_fashion_mnist_pbnn_cnn.py` | `figures/05a_fashion_mnist_training_curves.png` →(复制改名)→ `article/figs/AppendixB_01.png` | torch + Fashion-MNIST |
| 图 B.2 | CIFAR-10 上 PBNN-CNN 与基线的训练曲线 | `experiments/05a_cifar10_pbnn_cnn.py` | `figures/05a_cifar10_training_curves.png` → `AppendixB_02.png` | 60 轮，实际需 GPU |
| 图 B.3 | Fashion-MNIST PBNN-CNN 全栈 T 扫描 | `experiments/06a_fashion_mnist_sweep_T_vs_accuracy.py` | `figures/06a_fashion_mnist_sweep_T.png` → `AppendixB_03.png` | 依赖 `runs/fashion_mnist_pbnn_cnn/best.pt` (已入库) |
| 图 B.4 | CIFAR-10 PBNN-CNN 全栈 T 扫描 | `experiments/06a_cifar10_sweep_T_vs_accuracy.py` | `figures/06a_cifar10_sweep_T.png` → `AppendixB_04.png` | 依赖 `runs/cifar10_pbnn_cnn/best.pt` (已入库) |
| 表 B.1 | 两数据集 CNN 的最佳测试精度 | `05a_fashion_mnist_pbnn_cnn.py` + `05a_cifar10_pbnn_cnn.py` | `runs/05a_*_<ts>/{metrics.csv, bnn_metrics.csv, fp_*_metrics.csv}` | ⚠ 数据源 CSV 未入库，须重跑 05a，见 §7 |
| 表 B.2 | 两数据集 CNN 在 T=1..64 下的全栈精度 | `06a_fashion_mnist_sweep_T_vs_accuracy.py` + `06a_cifar10_sweep_T_vs_accuracy.py` | `runs/06a_*_sweep_T_<ts>/results.csv` (列 T, accuracy, energy_uJ) | ⚠ CSV 未入库；用已入库 best.pt 重跑 06a 可复现 |

### 6.2 附录 C (种子稳健性，Family A)

| 编号 | 标题 | 生成脚本 · 命令 | 产出/数据源 | 依赖/备注 |
|---|---|---|---|---|
| 图 C.1 | 主要结论的随机数种子稳健性 (4 面板) | `experiments/21_seed_independence.py` · `python experiments/21_seed_independence.py 8` | `figures/21_seed_independence.png` →(复制改名)→ `AppendixC_01.png` | torch + MNIST；8 个种子各训练一次 |
| 表 C.1 | 头部结论在 8 个种子下的均值±标准差 | `experiments/21_seed_independence.py` · `python experiments/21_seed_independence.py 8` | `runs/21_seed_independence/seed_independence.json` (`summary` 块) | 已入库，五行均值/标准差与文章逐项吻合 |

### 6.3 附录 D (电路比较)

图 D.1–D.7、D.9、D.10 为电路原理图，走 §2.1 通用流程 (`<base>`→编号映射见 §2.1)。图 D.8、D.11 与表 D.1–D.4 为纯 Python / 已入库 JSON，可离线复现；表 D.5–D.7 为手写定性能力矩阵。

| 编号 | 标题 | 生成脚本 · 命令 | 产出/数据源 | 依赖/备注 |
|---|---|---|---|---|
| 图 D.1–D.7, D.9, D.10 | 各读出比较器 / 写入 DAC / p-bit 驱动链 / 闪存 ADC 切片 / 门控对 原理图 | 电路原理图流程 (§2.1) | → `AppendixD_{01,02,03,04,05,06,07,09,10}.{svg,png,pdf}` | WSL EDA 工具链 |
| 图 D.8 | 两种 SAR 电容 DAC 开关方案的能耗对照 | `eda/hero/schematics/gen_sar_switching_fig.py` · `python …/gen_sar_switching_fig.py` | 直接写 `AppendixD_08.png` + `.svg` (无 pdf)；数据源 `eda/testbenches/sar_capdac_tran_summary.json` (b=8) | matplotlib，无需 WSL |
| 图 D.11 | 本方案 SAR 能耗与 Andrulis 下界的自洽检验 | `eda/design_survey/repro/andrulis_adc_model.py` · `python …/andrulis_adc_model.py` | 直接写 `AppendixD_11.png` (仅 png)；数据源 `sar_capdac_tran_summary.json` + `comparison_results.json` | matplotlib，无需 WSL |
| 表 D.1 | 五种读出比较器的输入折合失调 (N=120) | `eda/design_survey/comparison_driver.py` · `python …/comparison_driver.py` | `comparison_results.json` → `readout_sa`；上游 MC (WSL) `eda/hero/run_offset_mc.py` | 3σ 列由 σ/V_T 推导 |
| 表 D.2 | 三种写入 DAC 的线性度 (6 bit, 200 mV) | `eda/design_survey/comparison_driver.py` | `comparison_results.json` → `write_dac`；上游 (WSL) `eda/hero/run_write_dac.py` | — |
| 表 D.3 | 三种 IR 补偿方案的残余写误差 (N=256) | `eda/design_survey/repro/truong_predistort.py` + `zhu_boost.py` · `python …/truong_predistort.py; python …/zhu_boost.py` | `truong_predistort_summary.json` + `zhu_boost_summary.json` | ⚠ 不在 `comparison_results.json` 中；纯 Python，无需 ngspice |
| 表 D.4 | 两种 SAR 开关方案的单次转换能 (b=8) | `eda/design_survey/comparison_driver.py` | `comparison_results.json` → `sar_adc`；上游 (WSL) `eda/testbenches/sar_capdac_tran.py` | — |
| 表 D.5–D.7 | 读出/写入/SAR 文献能力覆盖 (定性) | 无生成器 (手写) | `article/appendix_D_circuit_comparison.md` 内联表；判定依据 `eda/design_survey/submodule_survey.json` | 引文支撑的 ✓/∼/✗ 矩阵，无数值生成器 |

## 7. 已知偏差与注意事项

1. **表 4.6 / 图 4.13 数值陈旧 — 已于 2026-07-08 修正**：文章旧值 (PBNN sMTJ 11.91 J、前向 7.09 J) 取自旧 run `runs/13_training_energy_20260511_214859`；规范 run `20260706_225408` (与 2026-07-08 重跑逐字节一致，模型确定性) 为 12.73 J (前向 7.90 J)。注意本条早先"仅 sMTJ 一行变动"的比对结论**不完整**：stoch-ReRAM 行同样变动 (前向 447.97→448.40 J、总 452.80→453.22 J)。已传播：表 4.6 两行、图 4.13 题注与 4.5 节末正文 (排名改为"仅次于 STT-MRAM 与 FeRAM"、1.14×→1.22×、4.2×→3.9×)、脚注 [^nv_ranking] (含旧占位值的来历说明)；图 4.13 经 deck 换图重导出 (slide 13 内嵌图替换为新 `13a_*.png` 并修正纵横比，LibreOffice→PDF→dpi 419 裁剪)。
2. **图 4.2 不能由当前 HEAD 精确复现**：`demo/01_simulator_framework.py` 现输出 `demo/figures/01_simulator_framework.png`，与已入库 `Chapter04_local_02.png` 不一致 (标题已去除、模块标签改动、并新增 training_energy 项)——该资产由在 `Chapter04_local.pptx` 中编辑后的渲染合成，重跑脚本得到的是旧版式。
3. **图 4.19 生成脚本目标名陈旧**：`eda/testbenches/plot_waveforms.py` 仍写 `Supplement_local_11.{png,svg,pdf}`，而文章资产为 `Chapter04_local_19`。内容一致；运行后须把三个文件改名为 `Chapter04_local_19.*`，或改脚本第 90 行的目标名。
4. **表 4.2 BNN 行 (97.05%) 数据源缺口**：该行不在任一已保存的 05 run 目录 (`20260509_092543` 缺 `bnn_metrics.csv`、`20260506_181751` 为旧格式)。同表 PBNN 与四档 QAT 行已精确核对。重跑 `experiments/05_mnist_pbnn.py` 可重新生成 BNN 行 (脚本第 261 行确写 `bnn_metrics.csv`)。
5. **表 B.1 / 表 B.2 数据源 CSV 未入库**：仓库只保留稳定检查点 `runs/{fashion_mnist_pbnn_cnn,cifar10_pbnn_cnn}/best.pt`，05a/06a 的时间戳 run 目录不在库。表 B.2 可用已入库 best.pt 直接重跑 06a 复现；表 B.1 需重跑 05a。另注：05a 脚本不写 `summary.json`，只写 `metrics.csv`/`bnn_metrics.csv`/`fp_*_metrics.csv`。
6. **`docs/experiment_findings.md` 两处图名陈旧**：第 29 行写 `figures/02_wafer_mc.png` (实际 `figures/02_wafer_average_mc.png`)；第 293 行写 `demo/figures/04_encoding_comparison.png` (实际 `demo/04_encoding_comparison.py` 输出 `demo/figures/04_encoding_comparison_fixed.png`)。
7. **第 5 章实验-图号偏移**：脚本按撰写顺序编号，与章节图号不一致——exp 14→图 5.2、exp 15→图 5.3、exp 19→图 5.4、exp 17→图 5.5、exp 18→图 5.6、exp 16→图 5.7。
8. **储备池实验 14–19 不写 CSV**：指标仅打印到 stdout。`runs/rc/` 下的 CSV 为原型日志，非任何编号图的数据源。
9. **EDA 分析面板须按序跑两条命令**：只跑 `gen_supplement_figs.py` 会在 `article/figs/` 留下无字母占位图，须接着跑 `build_ppt_figs.py` 覆盖为带 `(a)(b)(c)` 的规范资产 (图 4.15/4.16/4.17/5.9)。
