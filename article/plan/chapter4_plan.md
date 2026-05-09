# 第四章 基于 sMTJ 的概率二值网络硬件仿真器(规划)

本章计划在前章 sMTJ 器件模型与 PBNN 算法的基础上，构建基于 PyTorch 的端到端硬件仿真流水线。本文为该章的规划文档：先调查既有相关仿真器的能力边界与缺口、提出仿真器的分层架构与代码组织、给出章节的小节安排与验证策略，作为后续撰写与代码实现的基础。

## 4.1 既有仿真工作的能力边界

为定位本章工作，先对既有的相关仿真器作一次梳理。可将其按其原生支持的对象划入四个簇，每簇内部成熟度高，但相对sMTJ-PBNN这一具体目标都各自缺口明显。

### 4.1.1 确定性CIM加速器仿真器

NeuroSim系列由Yu课题组维护，是该领域使用最广的工具链。早期版本MLP+NeuroSim以C++实现单层感知机评估[^cim_neurosim_validation]；DNN+NeuroSim V2.0将NeuroSim与PyTorch对接，支持RRAM、PCM、STT-MRAM、FeFET、ECRAM等器件的训练与推理基准[^cim_dnn_neurosim_v2]；最新的V1.5重构了流程，将PyTorch行为仿真与C++硬件估算以trace-CSV接口解耦，并引入TensorRT后训练量化、设备级与电路级两种非理想注入模式[^cim_neurosim_v15]。MNSIM 2.0以行为级建模为目标，建立从器件到接口、PE、缓冲、互连的层次化结构，支持混合精度网络的推理精度评估[^cim_mnsim2]。MICSim在NeuroSim V1.3的硬件估算基础上加入Transformer算子并对接HuggingFace[^cim_micsim]。这一簇的统一假设是权重为确定性多比特，单元的随机性仅作为误差源进入精度评估，并不充当计算资源；其架构亦围绕ADC、缓冲、片上网络的层次组织，与本工作以单比特概率采样为核心信号的图景偏离明显。

### 4.1.2 模拟存算加速器仿真器

IBM aihwkit以PyTorch原生构件方式实现模拟阵列(Analog Tile)，覆盖全连接、卷积、LSTM层及相应的模拟SGD优化器，支持设备-设备变异、循环-循环变异、电导响应曲线、读出与权重噪声等[^cim_aihwkit]；其核心C++/CUDA后端可仿真多种器件物理与晶体管工艺约束，并提供以PCM硬件测量校准的统计噪声模型[^cim_aihwkit_apl]。aihwkit亦实现硬件感知训练(hardware-aware training)，把噪声注入前向通路、保持反向通路理想，以训练抗噪鲁棒网络。aihwkit的局限在于其权重以连续电导编码、噪声为加性扰动；二值随机权重、Bernoulli采样语义以及由Arrhenius律决定的Sigmoid型概率台阶不在其原生模型范围之内，强行通过自定义算子接入会丢失其PCM专用的诸多校准与流水线。

### 4.1.3 sMTJ器件级与p比特级仿真器

ARM公开的MRAM仿真框架以s-LLGS方程为内核，提供Python(ODE/SDE求解)与Verilog-A(idt/idtmod数值积分)两套紧凑模型，并以Fokker-Planck求解器(数值FVM与解析两种)校准至给定写错误率，已用OOMMF微磁仿真验证[^smtj_arm_compact][^smtj_arm_fpe]。Pham等人公开的STT/SHE-MTJ NGSPICE紧凑模型亦给出相近能力并兼容开源仿真链[^smtj_ngspice]。这些工具关注器件层面的随机翻转事件与切换误差率统计，输出形式为电流-时间-翻转概率的散点或拟合曲面，并不直接接入神经网络仿真。p比特级方面，Aadit等人公开的GPU加速模拟退火框架在CUDA上以受变异修正的p比特为采样源，对MAX-CUT等问题获得相对CPU两个数量级的加速[^psl_gpu_sa]，CIM-Optimizer与基于p比特的稀疏伊辛机仿真[^aadit]主要服务于组合优化任务，更新规则为同步Gibbs或全异步随机异步，与PBNN所需按层有序前馈的更新模式不一致。Kaiser等人在2022年Phys. Rev. Applied中发表了基于sMTJ的in situ玻尔兹曼机硬件感知学习电路与仿真[^kaiser_insitu_bm]，是迄今最贴近本工作的先例，但仍以无向玻尔兹曼机为对象，不涉及前馈PBNN在大规模图像数据集上的精度评估。

### 4.1.4 PBNN算法实现与变分推断工具

PBNN的算法层面已有若干公开的PyTorch复现，包括Peters等人原始论文的复现仓库以及Shayer等人局部重参数化方法的实现，主要展示算法可行性而无硬件建模[^pbnn_repro_peters]。Bayes-by-Backprop类Bayesian神经网络的PyTorch工具如Kumar Shridhar的PyTorch-BayesianCNN、TyXe等[^bnn_torch_bayescnn][^bnn_tyxe]提供了变分后验、局部重参数化与梯度方差缩减等组件，但其权重为连续高斯而非Bernoulli，不能直接迁移至单比特随机权重场景。

### 4.1.5 综合判断与本章定位

将上述四簇能力对照本工作目标，即同时承担sMTJ Sigmoid采样、单比特Bernoulli权重、CLT高斯化前向、时域展开、阵列级XNOR-popcount与PPA估算，可以看到没有一个既有工具是该交集的天然载体：CIM类工具假设确定性权重，aihwkit的统计噪声不是Bernoulli分布，ARM/NGSPICE的紧凑模型不进神经网络，p比特类工具不做前馈推理，PBNN/BNN工具不接器件物理。因此本章选择以PyTorch自行搭建仿真流水线，复用社区已成熟的器件级与PPA估算成果(Arrhenius P_sw拟合参数、NeuroSim校准的工艺常数、aihwkit验证过的硬件感知训练范式)，但在网络层与采样层独立实现，以恰好匹配sMTJ-PBNN的语义需求。

## 4.2 仿真器总体架构

依据上节得出的定位，本章构建的sMTJ-PBNN仿真器组织为五个解耦层次，配合一条贯穿各层的时域展开支柱。每一层只面向相邻层暴露最小接口，便于单元测试与独立替换。

层次自底向上依次为器件层、阵列电路层、网络层、PPA估算层与实验基准层。器件层把第二章建立的sMTJ磁化动力学模型与电路级SPICE行为模型抽象为可微的紧凑函数，输出在给定写入电压、脉冲宽度与温度下的Bernoulli参数；阵列电路层把N个器件并行组织成子阵列，模拟位线电流求和、外围DAC与计数器的有限精度行为；网络层基于PyTorch nn.Module实现PBNNLinear、PBNNConv2d及STE反向传播算子，并以CLT为捷径在训练时绕过显式逐样本采样；PPA层在给定网络结构、阵列配置与时域展开因子T的条件下输出能耗、延迟与面积；实验层封装训练循环、推理流程、不确定性量化与对照实验脚本。

时域展开作为横向支柱被五层共享。该模块管理T步采样的迭代调度、Bernoulli样本生成的数值实现、温度参数$\beta$与采样次数T的退火/衰减曲线，从而将器件层的单次写入概率提升为网络层的统计期望、并把PPA层的单步能耗乘以采样次数以得到完整推理代价。这一组织把时域展开的算法语义与各层的物理模型严格分离，便于在固定网络与阵列条件下扫描T，研究"采样次数-精度-能效"三者关系。

各层与PyTorch自动微分的对接遵循同一原则：前向通路完整保留器件物理与阵列非理想，反向通路在不影响梯度估计无偏性的前提下采用最廉价的近似。具体而言，sign算子的反向使用Bengio等人[^ste]提出的直通估计器；Bernoulli采样的反向通过CLT得到的高斯均值-方差表达直接求导；器件变异的随机抽样视为常数场而不参与反向。该选择保证了任何由本仿真器训练出的网络都可以在不修改梯度图的前提下，通过仅替换前向算子实现"训练时CLT近似、推理时显式时域采样"的两种模式切换。

仿真器的整体分层与各模块依赖如下图所示。

![图4.1 sMTJ-PBNN仿真器分层架构](./figs/fig_simulator_arch.png)

## 4.3 各层模块设计

### 4.3.1 器件层

器件层以一组紧凑函数把sMTJ的物理行为封装为可微的概率算子。核心算子来自前文的Arrhenius律的过渡区Sigmoid化简

$$
P_\mathrm{sw}(V, t_\mathrm{p}) \;\approx\; \sigma\!\left(\frac{V - V_0(t_\mathrm{p}, \Delta)}{V_T}\right),
$$

其中$V_0$与$V_T$由势垒$\Delta$、attempt time $\tau_0$、临界电压$V_\mathrm{c}$与脉冲宽度$t_\mathrm{p}$决定，由器件层的calibration模块对实测$P_\mathrm{sw}(V, t_\mathrm{p})$散点拟合得到。变异模块接受由前章实验数据估计的$(V_0, V_T)$方差与协方差，对每个物理位置抽取一组保持不变的偏移量，模拟器件-器件失配；TMR模块按MTJ两阻态比例计算位线电流贡献的实际幅值。为校验该层与微磁仿真的一致性，本层另保留一份基于s-LLGS方程的macrospin参考实现，仅在校准阶段使用，不参与神经网络前向，以避免成为运行瓶颈。Verilog-A层面的对应实现可借助ARM公开的紧凑模型框架[^smtj_arm_compact]验证，本仿真器仅以其拟合好的$(V_0, V_T)$参数为入口。

### 4.3.2 阵列电路层

阵列层把器件层的Bernoulli样本组织为$M\times N$的子阵列，模拟一次行激活下的XNOR-popcount。设输入$\mathbf{x}\in\{-1,+1\}^N$驱动行线，第$i$列的位线电流可写为

$$
I_i^\mathrm{BL} \;=\; \sum_{j=1}^{N} G_{ij}\, x_j \;=\; \sum_{j=1}^{N} \tilde{w}_{ij}\, x_j \cdot \Delta G \;+\; \mathrm{const},
$$

其中$G_{ij}$依sMTJ瞬时阻态在$G_\mathrm{P}$与$G_\mathrm{AP}$之间取值，$\tilde{w}_{ij}\in\{-1,+1\}$。外围模块以4–6位DAC把潜参数$\theta_{ij}$转换为写入电压并下发到行驱动；计数器模块对T步累加结果作有限精度的整数累计。可选的IR-drop模块以阻性梯子近似金属线压降，对网络精度的边际影响以扫掠方式评估而非默认开启，这是因为在$256\times 256$以下子阵列、典型工艺线宽下其对单比特读出的影响可被外围数字阈值吸收[^cim_neurosim_v15]。tile模块封装一次完整的子阵列调用，作为网络层算子的最小硬件单元。

### 4.3.3 网络层

网络层以PyTorch nn.Module为容器实现两种基本层。PBNNLinear以可训练张量$\boldsymbol{\Theta}\in\mathbb{R}^{M\times N}$为参数，前向时按训练或推理模式路由：训练模式直接以CLT高斯化路径输出$z\sim\mathcal{N}(\mu, \sigma^2)$，由$\mu = (2\sigma(\boldsymbol{\Theta}) - 1)\mathbf{x}$、$\sigma^2 = 4\sigma(\boldsymbol{\Theta})(1 - \sigma(\boldsymbol{\Theta}))\mathbf{x}^{\odot 2}$解析给出，sign算子反向使用STE近似[^ste]；推理模式调用阵列层T次，由计数器累计估计$\hat\mu$。PBNNConv2d以等效Toeplitz展开复用同一逻辑。批归一化模块按Shayer等人方案[^pbnn_lar]适配二值激活与随机权重的均值方差，避免标准BatchNorm在低位宽下的尺度漂移。损失模块除标准交叉熵外，提供互信息正则与对比散度选项，前者用于判别任务的特征解耦，后者保留对生成式扩展的兼容性。

### 4.3.4 时域展开层

该层是仿真器的特征模块。bernoulli_smtj算子接受单元$(\theta_{ij}, V_0, V_T, \Delta_{ij})$返回单次$\pm 1$样本，由对器件层Sigmoid的Inverse-CDF采样实现，并在推理阶段强制走真实的Bernoulli路径而非Gumbel等连续松弛，以保证与硬件一致；unfold算子在迭代中维护T步累加器并在末端归一化为期望估计；schedules模块持有$\beta(t)$与$T(\text{layer})$的调度策略，支持单层均匀T、按层深递增T以及与精度目标耦合的自适应T三种模式，便于扫掠"采样次数-精度"曲线。

### 4.3.5 PPA估算层

PPA层不重复造轮子，而是引用NeuroSim V1.5在40nm/28nm工艺下校准的电路级常数(SRAM/MTJ读写能量、ADC/DAC单位能量、H-tree互连能量、单元面积)[^cim_neurosim_v15]作为系数库，在本仿真器的算子粒度下叠加。具体而言，单次T步前向的能量被分解为DAC驱动、行写入、位线读出与计数累加四项；延迟分解为DAC建立、sMTJ翻转脉冲、电流积分与计数四段；面积按子阵列规模、外围电路份额与片上互连给出。采用的常数表完整附录于源码中并标注校准来源，便于他人复核。需要强调的是，该层仅作为相对比较的标尺，绝对数值在工艺切换或外围电路重设计后须重新校准。

### 4.3.6 实验基准层

最上层实现训练循环、推理评估与对照实验。训练脚本支持纯软件模式(理想$\sigma(\Theta)$采样、不引入器件变异)、硬件感知训练模式(注入$(V_0, V_T)$变异并以CLT前向)与全栈仿真模式(显式T步采样)三档；推理脚本提供单次采样、T步集成与不确定性量化三种调用方式；对照模块封装与数字BNN、STT-BNN[^sttbnn]、SOT-BNN[^fan]、aihwkit基线[^cim_aihwkit]在同一数据集与网络拓扑下的精度-能效对比。

## 4.4 代码目录组织

整个仿真器以单一Python包`smtj_pbnn_sim`组织，按上节五层架构分模块，配以独立的实验脚本目录、单元测试目录与外部数据目录。建议的代码目录结构如下。

```
smtj_pbnn_sim/
├── README.md
├── pyproject.toml
├── configs/
│   ├── device/
│   │   ├── stt_smtj_default.yaml
│   │   ├── sot_smtj_default.yaml
│   │   └── vcma_smtj_default.yaml
│   ├── array/
│   │   ├── 256x256.yaml
│   │   └── 512x512.yaml
│   └── experiment/
│       ├── mnist_lenet.yaml
│       └── cifar10_resnet18.yaml
├── src/
│   └── smtj_pbnn_sim/
│       ├── __init__.py
│       ├── device/
│       │   ├── __init__.py
│       │   ├── arrhenius.py        # P_sw(V, t_p) Sigmoid 紧凑模型
│       │   ├── llg_dynamics.py     # macrospin s-LLGS 参考实现, 仅校准用
│       │   ├── tmr.py              # P/AP 阻态与电流贡献
│       │   ├── variation.py        # device-to-device 变异抽样
│       │   └── calibration.py      # 对实测 P_sw 散点拟合 (V_0, V_T)
│       ├── array/
│       │   ├── __init__.py
│       │   ├── crossbar.py         # XNOR-popcount 与位线电流求和
│       │   ├── periphery.py        # DAC, 行驱动, 计数器, 量化
│       │   ├── ir_drop.py          # 金属线压降 (可选)
│       │   └── tile.py             # 子阵列封装
│       ├── nn/
│       │   ├── __init__.py
│       │   ├── pbnn_linear.py      # PBNNLinear, 训练/推理双路径
│       │   ├── pbnn_conv.py        # PBNNConv2d
│       │   ├── ste.py              # 直通估计器 autograd Function
│       │   ├── clt.py              # CLT 高斯化前向
│       │   ├── batchnorm.py        # 适配二值激活的 BatchNorm
│       │   └── losses.py           # 交叉熵, 互信息, 对比散度
│       ├── sampling/
│       │   ├── __init__.py
│       │   ├── bernoulli_smtj.py   # 接器件层的 Bernoulli 抽样
│       │   ├── unfold.py           # T 步展开与累加
│       │   └── schedules.py        # beta(t) 与 T(layer) 调度
│       ├── ppa/
│       │   ├── __init__.py
│       │   ├── energy.py
│       │   ├── latency.py
│       │   ├── area.py
│       │   └── tech_params.py      # 工艺常数 (NeuroSim 校准)
│       ├── train/
│       │   ├── __init__.py
│       │   ├── train_loop.py
│       │   ├── inference.py
│       │   ├── uncertainty.py
│       │   └── compare_baseline.py # 数字 BNN, STT-BNN, aihwkit 等对照
│       ├── data/
│       │   ├── __init__.py
│       │   ├── mnist.py
│       │   ├── cifar.py
│       │   └── augment.py
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── seeding.py
│       │   ├── logging.py
│       │   └── io.py
│       └── cli.py
├── tests/
│   ├── test_arrhenius.py
│   ├── test_calibration.py
│   ├── test_crossbar.py
│   ├── test_clt_match_sampling.py  # 验证 CLT 与显式采样在大 N 下一致
│   ├── test_pbnn_linear_grad.py    # 数值梯度对 STE 的健全性
│   ├── test_unfold_convergence.py  # 验证 T 步均值 O(1/sqrt T) 收敛
│   └── test_ppa_consistency.py
├── experiments/
│   ├── 01_device_calibration.py    # 用第 2 章实测数据拟合 (V_0, V_T)
│   ├── 02_clt_validation.py        # 比对 CLT 解析与显式采样 (合成数据)
│   ├── 03_mnist_pbnn.py            # MNIST + LeNet-5 基线
│   ├── 04_cifar_pbnn.py            # CIFAR-10 + ResNet-18 基线
│   ├── 05_robustness_sweep.py      # 变异强度扫描
│   ├── 06_sweep_T_vs_accuracy.py   # T 与精度/能效曲线
│   ├── 07_array_size_vs_energy.py  # 阵列规模与能效
│   └── 08_ppa_compare_baseline.py  # 与 STT-BNN, aihwkit 等的横向对比
├── data/
│   ├── smtj_psw_curves/            # 实测散点 (来自第 2 章或公开文献)
│   └── README.md
├── notebooks/                      # 探索性分析, 不参与回归
├── figures/                        # 实验输出图
└── docs/
    ├── module_api.md
    ├── calibration_guide.md
    └── reproducibility.md
```

该结构有几项约定可显著减少后续维护开销。所有运行参数集中在`configs/`下的YAML，代码内部不允许硬编码工艺常数或网络超参，便于实验复现。`src/`采用扁平化模块路径，单层不再多套子包，避免长导入路径降低代码可读性。`tests/`下的每一项均对应一段已知解析或数值上界(例如CLT与显式采样在大N下的KL散度上界、T步均值的标准差上界)，构成回归测试的硬约束。`experiments/`下脚本编号对应章节内实验，配合`configs/experiment/`的YAML一一对照，便于评审复核。`data/`下的实测散点通过Git LFS或可下载链接管理，不进入主仓库。

模块的依赖图严格按照分层进行，严禁高层向低层注入(例如不允许网络层直接调用器件层的具体物理参数，必须经由阵列层打包)，以保证每一层都可以独立替换。当未来需要将物理载体由MTJ更换为其他随机器件时，只需重写`device/`目录下的若干模块即可，而无须改动网络层与上层基础设施。

## 4.5 章节内容规划

依据上述代码结构，本章在论文中的内容组织如下。各小节大致与`experiments/`脚本一一对应，便于把仿真结果直接落入论文图表。

4.1 既有仿真工作的能力边界(本节已写)

4.2 仿真器总体架构(本节已写)

4.3 各层模块设计

  4.3.1 sMTJ器件行为模型与变异

  4.3.2 阵列电路模型与外围量化

  4.3.3 PBNN算子: STE反向传播与CLT高斯化前向

  4.3.4 时域展开模块

  4.3.5 PPA估算层

4.4 校准与验证

  4.4.1 器件层校准: 用第二章实测$P_\mathrm{sw}(V, t_\mathrm{p})$散点拟合$(V_0, V_T)$与变异统计

  4.4.2 算子层验证: CLT解析路径与显式T步采样在合成线性问题上的一致性

  4.4.3 PPA层校准: 复用NeuroSim V1.5在40nm/28nm下的电路常数并标注对照来源

4.5 训练与推理流水线

  4.5.1 三档运行模式: 纯软件、硬件感知、全栈仿真

  4.5.2 训练超参与稳定性: 学习率、权重衰减、$\theta$初始化、梯度裁剪

  4.5.3 推理时的不确定性量化: T步集成的方差作为置信度

4.6 实验结果与讨论

  4.6.1 MNIST与CIFAR-10基线: PBNN相对数字BNN的精度差距与时域展开必要性

  4.6.2 采样次数-精度曲线: T取值与目标精度的依赖关系

  4.6.3 变异敏感度: $V_0$与$V_T$扰动对精度的影响

  4.6.4 阵列规模-能效权衡: 不同子阵列尺寸下的能量构成

  4.6.5 横向对比: 与STT-BNN[^sttbnn]、SOT-BNN[^fan]、Huang等PBNN工作[^huang]、aihwkit基线[^cim_aihwkit]在同一网络拓扑下的精度-能效定位

4.7 局限与后续工作

  讨论范围: 训练时未涵盖的器件老化效应、读写循环引入的1/f噪声漂移、片上互连在更大网络下的非线性影响, 以及向Transformer类网络迁移时CLT高斯化在自注意力子层的有效性边界

## 4.6 验证策略小结

仿真器各层的可信度由三层证据支撑。器件层的Sigmoid响应与方差结构由第二章的实测散点直接拟合得到，且其参数化形式由Arrhenius律的过渡区Taylor展开自然导出，无须假设；算子层的CLT近似由合成线性问题上与显式蒙特卡洛采样的KL散度收敛行为验证；PPA层的工艺常数借用NeuroSim V1.5经40nm/28nm RRAM-CIM macro post-layout硅验证后的校准值[^cim_neurosim_v15]，仅作相对比较用。三层证据各自独立，避免循环论证。

## 参考文献(本章新增项)

[^cim_neurosim_validation]: Lu A, Peng X, Luo Y, Yu S. NeuroSim simulator for compute-in-memory hardware accelerator: validation and benchmark. *Frontiers in Artificial Intelligence*, 2021, 4: 659060. [doi:10.3389/frai.2021.659060](https://doi.org/10.3389/frai.2021.659060)

[^cim_dnn_neurosim_v2]: Peng X, Huang S, Jiang H, Lu A, Yu S. DNN+NeuroSim V2.0: an end-to-end benchmarking framework for compute-in-memory accelerators for on-chip training. *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*, 2021, 40(11): 2306–2319. [doi:10.1109/TCAD.2020.3043731](https://doi.org/10.1109/TCAD.2020.3043731)
[^cim_neurosim_v15]: Lu A, Peng X, Li W, Jiang H, Yu S. NeuroSim V1.5: improved software backbone for benchmarking compute-in-memory accelerators with device and circuit-level non-idealities. [arXiv:2504.02314](https://arxiv.org/abs/2504.02314), 2024.

[^cim_mnsim2]: Zhu Z, Sun H, Qiu K, Xia L, Krishnan G, Dai G, Niu D, Chen X, Hu X S, Cao Y, Xie Y, Wang Y, Yang H. MNSIM 2.0: a behavior-level modeling tool for memristor-based neuromorphic computing systems. *Proc. ACM Great Lakes Symposium on VLSI (GLSVLSI)*, 2020: 83–88. [doi:10.1145/3386263.3407647](https://doi.org/10.1145/3386263.3407647)

[^cim_micsim]: Wang C, Yu C, Wang Y, Li B, Yang H. MICSim: a modular simulator for mixed-signal compute-in-memory based AI accelerator. [arXiv:2409.14838](https://arxiv.org/abs/2409.14838), 2024.

[^cim_aihwkit]: Rasch M J, Moreda D, Gokmen T, Le Gallo M, Carta F, Goldberg C, El Maghraoui K, Sebastian A, Narayanan V. A flexible and fast PyTorch toolkit for simulating training and inference on analog crossbar arrays. *Proc. IEEE International Conference on Artificial Intelligence Circuits and Systems (AICAS)*, 2021: 1–4. [doi:10.1109/AICAS51828.2021.9458494](https://doi.org/10.1109/AICAS51828.2021.9458494)

[^cim_aihwkit_apl]: Le Gallo M, Lammie C, Buechel J, Carta F, Fagbohungbe O, Mackin C, Tsai H, Narayanan V, Sebastian A, El Maghraoui K, Rasch M J. Using the IBM analog in-memory hardware acceleration kit for neural network training and inference. *APL Machine Learning*, 2023, 1(4): 041102. [doi:10.1063/4.0168089](https://doi.org/10.1063/4.0168089)

[^smtj_arm_compact]: Garcia-Redondo F, Lopez-Vallejo M, Stanley-Marbell P. A compact model for scalable MTJ simulation. *Proc. International Conference on Synthesis, Modeling, Analysis and Simulation Methods and Applications to Circuit Design (SMACD)*, 2021: 1–4. [doi:10.1109/SMACD52803.2021.9636229](https://doi.org/10.1109/SMACD52803.2021.9636229)

[^smtj_arm_fpe]: Garcia-Redondo F, Gusak A, Lopez-Vallejo M, Stanley-Marbell P. A Fokker-Planck solver to model MTJ stochasticity. *Proc. European Solid-State Device Research Conference (ESSDERC)*, 2021: 175–178. [doi:10.1109/ESSDERC53440.2021.9631805](https://doi.org/10.1109/ESSDERC53440.2021.9631805)

[^smtj_ngspice]: Pham C, Mandal A, Tomiyasu R, Lebedev A, Naeemi A. Novel STT/SHE MTJ compact model compatible with NGSPICE. [arXiv:2208.14055](https://arxiv.org/abs/2208.14055), 2022.

[^psl_gpu_sa]: Onizawa N, Sasaki R, Hanyu T. GPU-accelerated simulated annealing based on p-bits with real-world device-variability modeling. *Scientific Reports*, 2025, 15: 6614. [doi:10.1038/s41598-025-90520-3](https://doi.org/10.1038/s41598-025-90520-3)

[^kaiser_insitu_bm]: Kaiser J, Borders W A, Camsari K Y, Fukami S, Ohno H, Datta S. Hardware-aware in situ learning based on stochastic magnetic tunnel junctions. *Physical Review Applied*, 2022, 17: 014016. [doi:10.1103/PhysRevApplied.17.014016](https://doi.org/10.1103/PhysRevApplied.17.014016)

[^pbnn_repro_peters]: Peters J W T, Welling M. Probabilistic binary neural networks. [arXiv:1809.03368](https://arxiv.org/abs/1809.03368), 2018. (reference implementation: <https://github.com/COMP6248-Reproducability-Challenge/Reproduction-of-Probabilistic-binary-neural-networks>)

[^pbnn_lar]: Shekhovtsov A, Yanush V. Reparameterizing discrete subset selection for differentiable learning. (LAR-nets line of work on local activation reparameterization). [arXiv:2307.01683](https://arxiv.org/abs/2307.01683), 2023.

[^bnn_torch_bayescnn]: Shridhar K, Laumann F, Liwicki M. A comprehensive guide to Bayesian convolutional neural network with variational inference. [arXiv:1901.02731](https://arxiv.org/abs/1901.02731), 2019. (reference implementation: <https://github.com/kumar-shridhar/PyTorch-BayesianCNN>)

[^bnn_tyxe]: Ritter H, Kukla T, Karaletsos T. TyXe: Pyro-based Bayesian neural nets for PyTorch. [arXiv:2110.00276](https://arxiv.org/abs/2110.00276), 2021.

(已在前文出现的参考文献，包括 [^ste]、[^sttbnn]、[^fan]、[^huang] 等，沿用绪论章节既有编号；本附件仅列出本章新增项。)

