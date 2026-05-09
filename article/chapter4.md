# 第四章 基于sMTJ的概率二值网络硬件仿真器

本章在前两章sMTJ器件物理与概率二值网络（Probabilistic Binary Neural Network，PBNN）算法的基础上，构造一条端到端的硬件仿真流水线，以PyTorch为前端、以校准后的紧凑器件模型为后端，贯穿器件、阵列、网络、采样、性能-功耗-面积（Power-Performance-Area，PPA）与实验六个层次。仿真器的目标不是替代器件级电路仿真器或SPICE，而是为算法层面的设计选择提供量化反馈：在固定网络拓扑、采样次数与器件变异强度的条件下输出训练精度、推理鲁棒性与能耗、延迟、面积估计，使得"采样次数取多少"、"$$V_\mathrm{th}$$写电压允许多大失配"、"sMTJ阵列与数字MRAM在训练能耗上谁占优"等问题能以可复现的数据回答，而不是停留在数量级直觉。完整代码已经实现并通过六十一项单元测试，十三个实验脚本均能从一份YAML配置端到端运行，本章的论述与图表全部来自这一实现。

## 4.1 sMTJ-PBNN硬件工作原理

本节先把sMTJ-PBNN在硬件上如何完成一次前向计算的图景叙述清楚，作为后续仿真器各层抽象的物理参照。叙述自下而上分为三步：阵列内的二值内积如何在电流域里完成、概率神经元如何由器件的随机翻转过程天然实现、以及一次完整的闭环前向如何由多步采样得到稳定的期望输出。

### 4.1.1 阵列内的二值内积与电流域读出

二值神经网络（Binary Neural Network，BNN）通过将浮点乘加替换为按位同或（XNOR）与位计数（popcount），相对全精度网络在能效上有数量级提升。基于非易失性存储器的存内计算（Compute-in-Memory，CIM）架构能在阵列内部直接完成XNOR运算，进一步消除了访存瓶颈。当确定性BNN向PBNN演进时，系统不再以确定性比特为运算载体，而需要原生的随机比特生成源。磁隧道结（Magnetic Tunnel Junction，MTJ），尤其是工作于亚临界区的随机磁隧道结（stochastic MTJ，sMTJ），其热涨落驱动的翻转过程具有真实的物理随机性，可作为天然真随机数发生器（True Random Number Generator，TRNG）[^neel1949][^brown1963]。这一物理特性使MRAM阵列同时承担两重身份：既是确定性权重的存储与计算载体，又是概率计算所需的物理熵源。

考虑全连接层第$$j$$个输出神经元的预激活值$$z_j=\sum_{i=1}^{N} w_{ji} x_i$$。当输入$$x_i$$与权重$$w_{ji}$$均限定在$$\{-1,+1\}$$时，单次乘积可严格等价于比特域$$\{0,1\}$$中的XNOR仿射映射$$w_{ji}x_i=2\,\mathrm{XNOR}(x_i^{(b)}, w_{ji}^{(b)})-1$$。代入并整理得$$z_j=2k_j-N$$，其中$$k_j=\mathrm{popcount}\!\bigl(\mathrm{XNOR}(\boldsymbol{x}^{(b)},\boldsymbol{w}_j^{(b)})\bigr)$$是输入与权重的符号匹配位数。这一变换将$$N$$次实数乘法压缩为一次位计数。

在MRAM阵列的物理层，权重的逻辑态由MTJ的平行电导$$G_P$$与反平行电导$$G_\mathrm{AP}$$表征，输入$$x_i$$以位线电压驱动施加于单元。理想化情形下，单元输出电流可写为$$I_{ji}=I_\mathrm{mis}+(I_\mathrm{mat}-I_\mathrm{mis})\,\mathrm{XNOR}(x_i^{(b)},w_{ji}^{(b)})$$，其中$$I_\mathrm{mat}$$与$$I_\mathrm{mis}$$分别对应符号匹配与不匹配时的单元电流。同列各单元电流由基尔霍夫电流定律自动汇聚为列电流$$I_j=NI_\mathrm{mis}+(I_\mathrm{mat}-I_\mathrm{mis})k_j$$，由此可由列电流线性反演出二值内积

$$
z_j=\alpha_I I_j+\beta_I,\qquad \alpha_I=\frac{2}{I_\mathrm{mat}-I_\mathrm{mis}},\quad \beta_I=-N\!\left(1+\frac{2I_\mathrm{mis}}{I_\mathrm{mat}-I_\mathrm{mis}}\right)。
$$

传统数字实现中XNOR与popcount是两个独立步骤，逐位匹配由逻辑门完成、累加由加法树或计数器完成；而在MRAM阵列内，匹配通过单元电导响应实现、累加由KCL自动完成，两者被统一为单一物理过程，从根本上消除了数字乘法器的开销。为进一步抑制工艺漂移与共模噪声，本工作采用差分读出结构：每一权重位由一对互补MTJ单元$$(G^+_i,G^-_i)$$表示，输入以差分电压$$\pm V_\mathrm{read}/2$$编码至单元两端。在双端差分驱动下逐项展开可得$$I_\mathrm{col}^\mathrm{diff}=(\delta G\cdot V_\mathrm{read}/2)\sum_i w_i x_i$$，其中$$\delta G=G_P-G_\mathrm{AP}$$，列电流严格正比于符号内积，偏置项天然消除。这一双端差分架构是阵列层物理层的目标拓扑，也是本仿真器`array/crossbar.py`中`xnor_popcount_diff`算子的设计依据。

### 4.1.2 sMTJ写入概率与天然伯努利采样

PBNN要求节点具备随机二值输出。当施加于MTJ的写入脉冲接近临界阈值时，器件状态演化由双稳态势阱中的热涨落主导，其翻转概率$$P_\mathrm{sw}$$随激励幅值与脉宽呈连续单调S型变化。第二章已经推导，Arrhenius律在过渡区作Taylor展开后有

$$
P_\mathrm{sw}(V,t_\mathrm{p})\approx \sigma\!\left(\frac{V-V_\mathrm{th}(t_\mathrm{p},\Delta)}{V_T}\right)，
$$

其中$$V_\mathrm{th}$$与$$V_T$$由势垒$$\Delta$$、attempt time $$\tau_0$$、临界电压$$V_\mathrm{c0}$$与脉冲宽度$$t_\mathrm{p}$$决定，桥式公式$$\beta_\mathrm{NB}=2\ln 2\cdot\Delta/V_\mathrm{c0}$$把NB（Néel-Brown）斜率与Sigmoid斜率连接起来。这一Sigmoid近似不是工程拟合，而是物理参数化形式：增益$$\beta_s=1/V_T$$与偏置$$-\beta_s V_\mathrm{th}$$严格由底层物理参数决定，可作为器件-算法协同优化的入口[^krizakova2022]。

MTJ的写入结果$$m\in\{0,1\}$$构成天然的伯努利样本$$m\sim\mathrm{Bernoulli}(P_\mathrm{sw})$$，经$$2m-1$$的极性反演直接对应PBNN所需的概率神经元$$\xi\sim 2\,\mathrm{Bernoulli}(p)-1$$。与传统CMOS方案"均匀随机数发生器加概率比较器"的级联实现相比，sMTJ把随机熵源与计算节点在器件层面原位融合，避免了独立TRNG模块带来的面积与能耗开销。这一融合带来的能量优势在第七节的横向对比中以4.2倍的训练能耗差异定量给出。

由此，PBNN在MRAM-CIM架构内的前向传播被重构为物理与数学严格对应的闭环迭代。上一层生成的随机二值向量$$\boldsymbol{x}^{(r)}$$驱动MRAM阵列与固化权重$$\boldsymbol{W}$$执行XNOR-CIM运算，列电流向量正比于$$\boldsymbol{a}^{(r)}=\boldsymbol{W}\boldsymbol{x}^{(r)}$$；列端的数模混合电路把$$\boldsymbol{a}^{(r)}$$映射为下一层目标翻转概率$$\boldsymbol{p}^{(r+1)}=g(\boldsymbol{a}^{(r)})$$，并据此生成对应的物理写入激励参数；写入激励驱动后级采样MTJ阵列发生热随机翻转，输出新一轮独立状态$$\boldsymbol{x}^{(r+1)}\sim 2\,\mathrm{Bernoulli}(\boldsymbol{p}^{(r+1)})-\boldsymbol{1}$$。第一次迭代的输入$$\boldsymbol{x}^{(0)}$$来自确定性原始数据（如图像像素经量化后的二值编码），随机采样从第二层起逐层引入。

### 4.1.3 闭环前向、期望恢复与误差分类

PBNN单次前向传播仅给出样本输出$$s^{(r)}$$，而网络推断的真实语义依赖于统计期望$$\mathbb{E}[s]=\sum_i w_i(2p_i-1)$$。对$$T$$个独立样本求均值$$\bar s_T=T^{-1}\sum_{r=1}^{T}s^{(r)}$$，依大数定律可渐近收敛于$$\mathbb{E}[s]$$，估计方差以$$\mathcal{O}(1/T)$$衰减。这一关系决定了概率网络在硬件实现中固有的精度与吞吐率的权衡：采样次数越多，估计方差越小，但延迟与能耗也越大。MRAM-CIM的高并行列求和能力可同时利用空间并行（多个MTJ单元独立翻转）与时间复用（同一单元重复写入生成bit-stream）两种方式获取样本，从而部分缓解这一权衡。本仿真器在第六节的实验结果中给出了$$T$$取4时MNIST精度即可达到$$T=64$$渐近值的0.17个百分点之内的具体证据。

需要强调的是，期望恢复的收敛性依赖于零均值误差假设$$\mathbb{E}[\epsilon]=0$$。实际硬件中存在两类统计性质截然不同的误差：由MTJ热涨落引起的逐周期独立的循环间随机性（Cycle-to-Cycle，C2C）满足$$\mathbb{E}[\epsilon_\mathrm{C2C}]=0$$，可被多次采样平均消除，是支撑Bernoulli采样的有用随机源；而由器件制造离散性与寄生效应引起的器件间系统误差（Device-to-Device，D2D）在同一次推断中保持不变，$$\mathbb{E}[\epsilon_\mathrm{D2D}]\neq 0$$，无法通过增加采样次数由大数定律消除。综合电路级与器件级非理想，第$$r$$次采样的实际硬件输出可统一建模为

$$
s^{(r)}=\underbrace{\sum_i w_i x_i^{(r)}}_{\text{理想内积}}+\underbrace{\epsilon_\mathrm{IR}+\epsilon_\mathrm{leak}+\epsilon_{V_\mathrm{th}}}_{\text{D2D系统误差}}+\underbrace{\epsilon_\mathrm{noise}}_{\text{C2C随机误差}}。
$$

这一统计区分是MRAM-CIM概率计算可靠性的核心论点，亦决定了仿真器内部各层的设计取舍。仿真器的器件层把D2D误差实现为对每个物理位置抽取一次后保持不变的偏移场，C2C误差则在每次前向调用中重新抽样；阵列层的差分双端驱动与动态校准机制设计目标是把$$\mathbb{E}[\epsilon_\mathrm{IR}]$$与$$\mathbb{E}[\epsilon_\mathrm{leak}]$$压制到可忽略水平，同时保留$$\epsilon_\mathrm{noise}$$以支撑可靠的概率计算；网络层的硬件感知训练则使梯度能够感知到由D2D失配引起的Sigmoid偏移，避免训练-推理失配。后续各节将逐层展开这些设计的具体形态。

## 4.2 既有仿真工作的能力边界与本章定位

为定位本章工作，先对相关仿真工具作一次梳理。可将其按原生支持的对象划入四个簇：确定性CIM加速器、模拟存算加速器、sMTJ器件级与p-bit级、PBNN算法与变分推断工具。每一簇内部都已成熟，但相对sMTJ-PBNN的具体目标都各自缺口明显。

确定性CIM加速器仿真器以Yu课题组维护的NeuroSim系列为代表。早期版本MLP+NeuroSim以C++实现单层感知机评估[^cim_neurosim_validation]；DNN+NeuroSim V2.0将其与PyTorch对接，支持电阻随机存储器（Resistive Random-Access Memory，ReRAM）、相变随机存储器（Phase-Change RAM，PCRAM）、自旋转移矩磁随机存储器（Spin-Transfer-Torque MRAM，STT-MRAM）、铁电场效应晶体管（Ferroelectric FET，FeFET）、电化学随机存储器（Electrochemical RAM，ECRAM）等器件的训练与推理基准[^cim_dnn_neurosim_v2]；最新的V1.5重构了流程，将PyTorch行为仿真与C++硬件估算以trace-CSV接口解耦，引入TensorRT后训练量化以及设备级与电路级两种非理想注入模式[^cim_neurosim_v15]。MNSIM 2.0以行为级建模为目标，从器件经接口、处理单元（Processing Element，PE）、缓冲到互连建立层次化模型，支持混合精度网络的推理精度评估[^cim_mnsim2]。MICSim在NeuroSim V1.3的硬件估算基础上加入Transformer算子并接入HuggingFace[^cim_micsim]。这一簇的统一假设是权重为确定性多比特，单元的随机性仅以误差源进入精度评估而不充当计算资源，其架构亦围绕模拟数字转换器（Analog-to-Digital Converter，ADC）、缓冲与片上网络组织，与本工作以单比特概率采样为核心信号的图景偏离明显。

模拟存算加速器仿真器以IBM的aihwkit为代表。aihwkit以PyTorch原生构件实现模拟阵列，覆盖全连接、卷积、长短期记忆（Long Short-Term Memory，LSTM）层及对应的模拟随机梯度下降（Stochastic Gradient Descent，SGD）优化器，支持D2D变异、C2C变异、电导响应曲线、读出与权重噪声等[^cim_aihwkit]；其C++与CUDA后端可仿真多种器件物理与晶体管工艺约束，并提供以PCM硬件测量校准的统计噪声模型[^cim_aihwkit_apl]。aihwkit亦实现硬件感知训练，把噪声注入前向通路、保持反向通路理想，以训练抗噪鲁棒网络。aihwkit的局限是其权重以连续电导编码、噪声为加性扰动；二值随机权重、Bernoulli采样语义以及由Arrhenius律决定的Sigmoid型概率台阶不在其原生模型范围之内，通过自定义算子接入会失去其PCM专用的诸多校准与流水线。

sMTJ器件级仿真器关注随机翻转事件的统计性质而不直接接入神经网络。ARM公开的MRAM紧凑模型以随机Landau-Lifshitz-Gilbert-Slonczewski（s-LLGS）方程为内核，提供Python（常微分方程与随机微分方程求解）与Verilog-A（idt/idtmod数值积分）两套实现，并以Fokker-Planck求解器校准至给定写错误率，已用OOMMF微磁仿真验证[^smtj_arm_compact]。Pham等人公开的STT/SHE-MTJ NGSPICE紧凑模型亦给出相近能力并兼容开源仿真链[^smtj_ngspice]。这些工具的输出形式为电流-时间-翻转概率的散点或拟合曲面。p-bit级方面，Onizawa等人的GPU加速模拟退火框架以受变异修正的p-bit为采样源，对最大割（MAX-CUT）等组合优化问题获得相对CPU两个数量级的加速[^psl_gpu_sa]；Camsari等人在Proc. IEEE 2020上系统综述了p-bit的电路实现与Bernoulli发生器的能耗代价[^cmos_pbit_camsari]；Borders等人在Nature 2019上展示了基于sMTJ的整数因子分解原型机[^borders_factor]；Sutton等人在Sci. Adv. 2020上将其扩展为自治概率协处理器原型[^sutton_pbit]。这些工作主要服务于组合优化任务，更新规则为同步Gibbs或全异步，与PBNN所需的按层有序前馈不一致。Kaiser等人在Phys. Rev. Applied 2022发表了基于sMTJ的in-situ玻尔兹曼机硬件感知学习电路与仿真[^kaiser_insitu_bm]，是迄今最贴近本工作的先例，但仍以无向玻尔兹曼机为对象，不涉及前馈PBNN在大规模图像数据集上的精度评估。

PBNN算法层面已有若干公开的PyTorch复现，包括Peters等人原始论文的复现仓库[^pbnn_peters]以及Shayer等人局部重参数化方法的实现，主要展示算法可行性而无硬件建模。Bayes-by-Backprop类工具如PyTorch-BayesianCNN[^bnn_bayescnn]、TyXe[^bnn_tyxe]提供了变分后验与方差缩减组件，但其权重为连续高斯而非Bernoulli，不能直接迁移至单比特随机权重场景。

将上述四簇能力对照本工作目标，即同时承担sMTJ Sigmoid采样、单比特Bernoulli权重、基于中心极限定理（Central Limit Theorem，CLT）的高斯化前向、时域展开、阵列级XNOR-popcount与PPA估算，可以看到没有一个既有工具是该交集的天然载体。本章因此选择以PyTorch自行搭建仿真流水线，复用社区已成熟的器件级与PPA估算结果（Arrhenius $$P_\mathrm{sw}$$拟合参数、NeuroSim校准的工艺常数、aihwkit验证过的硬件感知训练范式），但在网络层与采样层独立实现，以匹配sMTJ-PBNN的语义需求。

## 4.3 仿真器总体架构与模块实现

仿真器组织为五个解耦层次，配合一条贯穿各层的时域展开支柱。每一层只面向相邻层暴露最小接口，便于单元测试与独立替换。层次自底向上依次为器件层、阵列电路层、网络层、PPA估算层与实验基准层。器件层把第二章建立的sMTJ磁化动力学模型抽象为可微的紧凑函数，输出在给定写电压、脉冲宽度与温度下的Bernoulli参数；阵列电路层把$$N$$个器件并行组织为子阵列，仿真位线电流求和、外围数模转换器（Digital-to-Analog Converter，DAC）与计数器的有限精度行为；网络层基于`torch.nn.Module`实现`PBNNLinear`、`PBNNConv2d`及直通估计器（Straight-Through Estimator，STE）反向传播算子，并以CLT为捷径在训练时绕过显式逐样本采样；PPA层在给定网络结构、阵列配置与时域展开因子$$T$$的条件下输出能耗、延迟与面积；实验层封装训练循环、推理流程、不确定性量化与对照实验脚本。时域展开作为横向支柱被五层共享，管理$$T$$步采样的迭代调度、Bernoulli样本生成的数值实现以及采样次数$$T$$的退火与衰减曲线，从而将器件层的单次写概率提升为网络层的统计期望、并把PPA层的单步能耗乘以采样次数得到完整推理代价。这一组织把时域展开的算法语义与各层的物理模型严格分离，使得"采样次数-精度-能效"三者在固定网络与阵列条件下能够独立扫描。各层与PyTorch自动微分的对接遵循同一原则：前向通路完整保留器件物理与阵列非理想，反向通路在不影响梯度估计无偏性的前提下采用最廉价的近似。Sign算子的反向使用Bengio等人[^ste]提出的直通估计器，Bernoulli采样的反向通过CLT得到的高斯均值与方差表达直接求导，器件变异的随机抽样视为常数场而不参与反向。这一选择保证了任何由本仿真器训练出的网络都可以在不修改梯度图的前提下，通过仅替换前向算子实现"训练时CLT近似、推理时显式时域采样"的两种模式切换。仿真器的整体分层与各模块依赖如图4.1所示。

![图4.1 sMTJ-PBNN仿真器分层架构](./figs/fig_simulator_arch.png)

器件层以一组紧凑函数把sMTJ的物理行为封装为可微的概率算子。仓库`device/arrhenius.py`实现了`psw_sigmoid`、`vth_neel_brown`与解析斜率函数，并在`device/calibration.py`中以非线性最小二乘对第二章的实测$$P_\mathrm{sw}(V,t_\mathrm{p})$$散点拟合得到$$(V_\mathrm{th},V_T)$$。在Device A、$$P\to\mathrm{AP}$$、$$t_\mathrm{p}=0.75\,\mathrm{ns}$$参考点上，拟合给出$$V_\mathrm{th}=895.8\,\mathrm{mV}$$、$$\beta_s=42.7\,\mathrm{V}^{-1}$$、$$R^2=0.992$$，与第二章的标定值$$894\,\mathrm{mV}$$、$$44.6\,\mathrm{V}^{-1}$$、$$0.993$$分别相差$$1.8\,\mathrm{mV}$$、$$1.9\,\mathrm{V}^{-1}$$与$$0.001$$，处于46点测量数据集的拟合噪声范围之内，这一一致性是后续所有上层结果的基础。变异模块`device/variation.py`接受由实测数据估计的$$(V_\mathrm{th},V_T)$$方差与协方差，对每个物理位置抽取一组保持不变的偏移量；变异来源既可以是直接对Sigmoid操作点的相对扰动（`mode="sigmoid_direct"`），也可以是先对势垒$$\Delta$$采样、再经NB-to-Sigmoid桥式公式$$\beta_\mathrm{NB}=2\ln 2\cdot\Delta/V_\mathrm{c0}$$传播至Sigmoid斜率（`mode="delta"`）。后者更贴近物理，因为第二章指出主导D2D通道是无量纲的热稳定因子$$\Delta$$，其变异系数（Coefficient of Variation，CV）在300mm晶圆上约为7.7%，经Brinkman分解归因为66%来自MTJ柱直径、27%来自界面各向异性、7%来自饱和磁化。两万样本的Monte Carlo校验给出wafer-mean $$\beta_s=42.37\,\mathrm{V}^{-1}$$，与第二章$$42.3\,\mathrm{V}^{-1}$$相差$$0.07\,\mathrm{V}^{-1}$$，桥式公式的解析-数值偏差在CV($$\Delta$$)的0%至60%范围内均不超过0.2%。需要指出的一个易错点是，delta模式从NB桥式得到的$$V_\mathrm{th}$$中心值约为$$0.843\,\mathrm{V}$$，而Sigmoid直接拟合得到的$$V_\mathrm{th,nom}=0.894\,\mathrm{V}$$，两者间存在约$$50\,\mathrm{mV}$$的系统偏差，折算为$$2.26\,V_T$$；如果训练时按Sigmoid标定写电压、推理时却按NB采样的$$V_\mathrm{th}$$读取概率，系统会在每个权重上叠加这一偏差，导致FULL_STACK评估精度大幅下降。本仿真器在`PBNNLinear._load_from_state_dict`处显式强制变异场重抽，且推理脚本默认对预训练检查点使用`variation_cfg=None`，以避免该陷阱。TMR模块`device/tmr.py`把P与AP两阻态的电导比$$G_P/G_\mathrm{AP}$$转化为位线电流贡献的实际幅值；自旋轨道矩（Spin-Orbit Torque，SOT）通道的写能耗按Ohmic耗散公式$$E_\mathrm{write}=V_\mathrm{wr}^2 t_\mathrm{w}/R_\mathrm{SOT}$$给出，在第二章参考点$$V_\mathrm{wr}=0.90\,\mathrm{V}$$、$$R_\mathrm{SOT}=776\,\Omega$$、$$t_\mathrm{w}=0.75\,\mathrm{ns}$$下计算得$$0.78\,\mathrm{pJ}$$，这是PPA层中唯一物理量地标定的能量数。`device/llg_dynamics.py`保留了一份基于s-LLGS方程的macrospin参考实现，仅在校准阶段使用，不参与神经网络前向。

阵列电路层把器件层的Bernoulli样本组织为$$M\times N$$的子阵列。仓库`array/crossbar.py`实现XNOR-popcount，`array/periphery.py`以4到6比特DAC把潜参数$$\theta_{ij}$$转换为写电压并下发到行驱动，计数器以有限位整数累计$$T$$步的结果。可选的`array/ir_drop.py`以阻性梯子近似金属线压降，在$$256\times 256$$以下子阵列、典型工艺线宽下其对单比特读出的影响可被外围数字阈值吸收[^cim_neurosim_v15]，仅以扫描方式评估而非默认开启。`array/tile.py`封装一次完整的子阵列调用，作为网络层算子的最小硬件单元。

网络层以`torch.nn.Module`为容器实现两种基本层。`PBNNLinear`持有可训练张量$$\boldsymbol{\Theta}\in\mathbb{R}^{M\times N}$$，前向时按运行模式路由出三档行为。SOFTWARE档使用理想的$$p_{ij}=\sigma(\theta_{ij})$$，不引入任何器件信息，主要用于复现已发表PBNN工作的基线。HARDWARE_AWARE档使用名义校准写电压$$V_\mathrm{wr}=V_\mathrm{th,nom}+V_T\cdot\theta_{ij}$$，把潜参数视为以名义器件为基准的逻辑标度，实际开关概率由每个单元的物理参数$$(V_{\mathrm{th},ij},V_{T,ij})$$决定；这是默认训练模式，在没有变异时退化为$$\sigma(\theta_{ij})$$，在有变异时让梯度感知到设备失配引起的概率梯度变化。FULL_STACK档显式调用阵列层$$T$$次，由计数器累计估计期望，是评估模式，匹配真实硬件的推理行为。三档对应同一份$$\boldsymbol{\Theta}$$检查点，无需重新训练。为了让批归一化（Batch Normalization，BN）的滑动统计在三档之间保持一致，仓库采用了硬二值STE技巧（`nn/pbnn_linear.py:_harden`）：前向输出$$p_\mathrm{hard}=\mathbb{1}[\theta\ge 0]$$对应$$w=\mathrm{sign}(\theta)\in\{-1,+1\}$$，反向梯度通过$$p_\mathrm{soft}=\sigma(\theta)$$回传，保留$$\partial p/\partial\theta=p_\mathrm{soft}(1-p_\mathrm{soft})$$的平滑性，使三档共用相同的硬二值前向、BN running stats可跨档复用。CLT高斯化前向（`nn/clt.py`）在训练阶段把矩阵向量积$$\boldsymbol{w}\boldsymbol{x}$$近似为$$\mathcal{N}(\mu,\sigma^2)$$，其中$$\mu=(2\sigma(\boldsymbol{\Theta})-1)\boldsymbol{x}$$、$$\sigma^2=4\sigma(\boldsymbol{\Theta})(1-\sigma(\boldsymbol{\Theta}))\boldsymbol{x}^{\odot 2}$$。CLT路径以单次解析计算代替$$T$$次显式抽样，在$$N\ge 256$$的层中与显式蒙特卡洛在5σ意义上一致（单元测试`tests/test_torch_nn.py::test_clt_mean_matches_explicit_sampling`以500次采样的标准误为基准对比，所有元素的误差z-score均小于5），因此训练阶段的每步计算复杂度与一次确定性矩阵乘法相同，而不是$$T$$倍。`PBNNConv2d`通过`torch.nn.functional.unfold`把卷积展开为等效Toeplitz矩阵以复用同一逻辑；`nn/batchnorm.py`提供的`BinaryBatchNorm1d`与`BinaryBatchNorm2d`针对二值激活的离散尺度作了归一化项参数化的微调，避免标准BN在低位宽下的尺度漂移；损失模块`nn/losses.py`在标准交叉熵之外提供互信息正则与权重二值化正则两个可选项。

时域展开模块`sampling/bernoulli_smtj.py`接受$$(\theta_{ij},V_{\mathrm{th},ij},V_{T,ij})$$返回单次$$\pm 1$$样本，沿真实Bernoulli路径而非Gumbel等连续松弛实现，以保证与硬件一致；`sampling/unfold.py`在迭代中维护$$T$$步累加器并在末端归一化为期望估计；`sampling/schedules.py`持有$$\beta(t)$$与按层深递增的$$T$$调度，便于扫描"采样次数-精度"曲线。PPA层引用NeuroSim V1.5在40nm/28nm工艺下校准的电路级常数（SRAM和MTJ读写能量、ADC与DAC单位能量、H-tree互连能量、单元面积）[^cim_neurosim_v15]作为系数库，在本仿真器的算子粒度下叠加：`ppa/energy.py`将单次$$T$$步前向的能量分解为DAC驱动、行写入、位线读出与计数累加四项，`ppa/latency.py`将延迟分解为DAC建立、sMTJ翻转脉冲、电流积分与计数四段，`ppa/area.py`按子阵列规模、外围电路份额与片上互连给出面积估计，常数表完整列于`tech_params.py`并标注校准来源。该层仅作为相对比较的标尺，绝对数值在工艺切换或外围电路重新设计后须重新校准。最上层把上述各层组合为可执行实验：`train/train_loop.py`提供通用训练循环，接受任意网络与运行模式与优化器组合；`train/inference.py`提供单次采样、$$T$$步集成与不确定性量化三种调用方式；`train/compare_baseline.py`封装与数字BNN、aihwkit基线在同一数据集与网络拓扑下的精度-能效对比。运行时由`utils/io.py:make_run_dir`统一创建带时间戳的输出目录，`utils/logging.py:MetricsLogger`持续记录每轮的损失、精度与时间到CSV，运行结束时dump JSON摘要，确保任何实验都可以原样回放。

## 4.4 校准、算子验证与时域展开收敛

仿真器各层的可信度由三类证据支撑。器件层的Sigmoid响应与方差结构由第二章的实测散点直接拟合得到，且其参数化形式由Arrhenius律的过渡区Taylor展开自然导出，无须假设；算子层的CLT近似由合成线性问题上与显式蒙特卡洛的相对熵收敛行为验证；PPA层的工艺常数借用NeuroSim V1.5经40nm/28nm RRAM-CIM macro post-layout硅验证后的校准值[^cim_neurosim_v15]，仅作相对比较用。三类证据各自独立，避免循环论证。

第二章的NB跨脉冲宽度反演工作在仿真器中通过实验`03_nb_cross_pulse_width.py`复现：以四个脉冲宽度（$$0.75/1/2/5\,\mathrm{ns}$$）的$$V_\mathrm{th}(t_\mathrm{w})$$拟合恢复底层势垒与临界电压，得到Device A的$$\Delta=5.19$$、$$V_\mathrm{c0}=882\,\mathrm{mV}$$（$$\mathrm{AP}\to P$$）与$$\Delta=4.91$$、$$V_\mathrm{c0}=857\,\mathrm{mV}$$（$$P\to\mathrm{AP}$$），与第二章的标定值在小数点后两位上一致。NB-Sigmoid桥式给出的解析$$\beta_\mathrm{NB}$$与拟合$$\beta_s$$之比在所有四个工作点上相差不超过2%，意味着本仿真器在不同操作点之间外推时无须重新拟合。

时域展开的收敛性由实验`06_sweep_T_vs_accuracy.py`直接给出。表4.1报告了已训练的MNIST PBNN多层感知机（Multi-Layer Perceptron，MLP，拓扑$$784\to 1024\to 1024\to 10$$）在不同$$T$$下的FULL_STACK测试精度与单次推理能耗。

| $$T$$ | 测试精度 | 单次推理能耗 |
|---|---|---|
| 1 | 96.91% | 0.156 µJ |
| 2 | 97.21% | 0.312 µJ |
| 4 | 97.51% | 0.624 µJ |
| 8 | 97.62% | 1.248 µJ |
| 16 | 97.64% | 2.496 µJ |
| 32 | 97.60% | 4.991 µJ |
| 64 | 97.68% | 9.983 µJ |

可以看到，$$T=4$$时测试精度已达到97.51%，与$$T=64$$的渐近上限97.68%相差仅0.17个百分点；$$T=8$$进一步收敛至97.62%，此后的额外采样收益小于0.1个百分点而能耗按线性递增。因此后文的鲁棒性与能耗对比中默认采用$$T=4$$作为部署目标，这一选择把PBNN的推理能耗压缩至$$T=64$$版本的十六分之一，而精度损失在测量噪声以内。$$T=1$$点本身已能给出96.91%的精度，原因是后训练时把潜参数$$\theta$$作了乘100的标度处理，使得$$\sigma(\theta)$$几乎都饱和在0或1，Bernoulli样本接近确定性，$$T$$主要补偿那些$$\theta$$仍处于0附近的少数权重。

CLT路径与显式$$T$$步采样的一致性在合成数据与实际任务两个尺度上验证。合成数据上，单元测试`test_clt_mean_matches_explicit_sampling`随机生成$$M=64,N=256,B=8$$的概率张量并把CLT解析均值与500次显式Bernoulli样本的均值比较，所有元素的z-score均小于5σ；`test_clt_sample_variance_decreases_with_N`验证CLT输出的标准差按$$\sqrt{N}$$增长，与理论一致。在MNIST PBNN-MLP上，SOFTWARE档（理想Sigmoid）训练得到的检查点经$$\theta\times 100$$标度后再用FULL_STACK $$T=4$$评估，精度从HARDWARE_AWARE训练时的96.98%回升至97.51%，差距与Bernoulli样本数从无穷大降到$$T=4$$的截断误差量级一致。

非理想性对精度的影响通过实验`08_nonideality_ablation.py`系统性地拆解。以变异强度$$\sigma_\mathrm{rel}(V_\mathrm{th})$$、$$\sigma_\mathrm{rel}(V_T)$$、循环噪声$$\sigma_\mathrm{C2C}$$与back-hopping平台$$p_\mathrm{max}$$为四个独立扫描轴，固定其余三项为零并以FULL_STACK $$T=64$$评估测试精度。结果显示$$V_\mathrm{th}$$的相对失配是唯一显著瓶颈：在$$\sigma_\mathrm{rel}(V_\mathrm{th})=20\%$$时精度从97.5%降至92.8%，而$$\sigma_\mathrm{rel}(V_T)$$在80%扰动下仍保持97.5%，$$\sigma_\mathrm{C2C}$$在3$$V_T$$扰动下亦保持97.7%。Back-hopping的曲线呈台阶状：从理想$$p_\mathrm{max}=1.0$$至Device A实测的$$p_\mathrm{max}=0.72$$，精度仅下降0.5个百分点；但当$$p_\mathrm{max}$$跌破0.60后精度急剧崩塌。综合$$V_\mathrm{th}$$、$$V_T$$的D2D加上back-hopping与C2C的现实组合（5%-10%-1$$V_T$$-0.72）给出97.0%的精度，与无非理想的97.5%相差0.5个百分点。这一结论把硬件设计的优先级清晰地指向DAC校准精度：$$V_T$$的slope抖动会被BN自动吸收，C2C噪声会被$$T$$步平均消除，真正决定网络精度的是$$V_\mathrm{th}$$的绝对位置稳定性。

## 4.5 训练流水线与基础精度

训练循环以`smtj-train --config`为入口，由YAML完全描述实验：数据集、网络拓扑、运行模式、优化器、学习率调度器、采样次数与变异配置。训练默认使用HARDWARE_AWARE档，这一档的硬二值前向使得损失函数的梯度面与SOFTWARE档几乎一致，但在反向传播时让梯度感知到由变异引起的Sigmoid斜率变化。训练结束后，`train_loop.py`把潜参数$$\theta$$统一乘以100作为部署预处理，这一步不改变$$\mathrm{sign}(\theta)$$因而不影响HARDWARE_AWARE的精度，但可使FULL_STACK下的Bernoulli样本几乎确定性，从而让$$T=4$$就能匹配$$T=64$$的精度。

MNIST基线由实验`05_mnist_pbnn.py`完成。同一份PBNN-MLP拓扑（$$784\to 1024\to 1024\to 10$$、隐藏层1024、batch 128、Adam学习率$$10^{-3}$$、20轮）在三档下的测试精度依次为96.98%（HARDWARE_AWARE）、97.51%（FULL_STACK $$T=4$$）与97.68%（FULL_STACK $$T=64$$）；软件档（无变异）给出97%左右，差距被收入HARDWARE_AWARE档的训练通量。为评估"二值随机权重"相对"高位宽确定性权重"的代价，本实验同时训练了相同拓扑的全精度MLP在四个比特宽度下的量化感知训练（Quantization-Aware Training，QAT）变体，使用对称INT-N量化加STE反向传播。表4.2汇总最佳测试精度。

| 架构 | 最佳测试精度 | 相对FP32差距 |
|---|---|---|
| FP-MLP FP32（理想） | 98.51% | 基准 |
| FP-MLP INT8（QAT） | 98.33% | $$-0.18$$pp |
| FP-MLP INT4（QAT） | 98.43% | $$-0.08$$pp |
| FP-MLP INT2（QAT） | 98.21% | $$-0.30$$pp |
| PBNN-MLP（二值$$\pm 1$$） | 96.98% | $$-1.53$$pp |

值得指出三点。第一，MNIST足够简单，QAT能把INT2（三值等价）拉至FP32的0.3个百分点之内，比特宽度与精度的常识曲线在此被压平；第二，PBNN相对INT2的差距是1.23个百分点，这是从三值（$$-1,0,+1$$）走至二值（$$-1,+1$$，无零选项）的结构性代价，而不是训练程序的不足；第三，PBNN与全精度baseline相差1.53个百分点是在相同epoch预算下的等价值，而非训练失败的表征，这与第七节中PBNN在硬件能耗上的优势构成对偶取舍。

PBNN-MLP的拓扑在UCI六个表格数据集上的迁移实验由`10_uci_benchmarks.py`给出。表4.3中PBNN-MLP在六类规模与类别数差异巨大的任务上表现稳定。

| 数据集 | 形状 | 类别数 | PBNN-MLP | FP-MLP | 文献基线 |
|---|---|---|---|---|---|
| Iris | $$150\times 4$$ | 3 | 91.11% | 100.00% | 96.7%[^uci_iris] |
| WDBC | $$569\times 30$$ | 2 | 98.84% | 98.84% | 96.5%[^uci_wdbc] |
| Yeast | $$1484\times 8$$ | 10 | 51.89% | 62.14% | 62.0%[^uci_yeast] |
| Vehicle | $$846\times 18$$ | 4 | 74.22% | 86.33% | 84.0%[^uci_statlog] |
| Spambase | $$4601\times 57$$ | 2 | 91.67% | 94.93% | 94.0%[^uci_spambase] |
| Satimage | $$6435\times 36$$ | 6 | 86.70% | 92.19% | 91.0%[^uci_statlog] |

WDBC上PBNN与FP完全持平且超过文献基线2.3个百分点，说明在特征数足够的医疗判别任务上，二值权重的容量损失被网络的冗余补偿。在Spambase和Satimage这类规模较大的数据集上，PBNN落后FP在3至5个百分点之间，差距随训练样本规模扩大而单调收窄；而在样本数最少的Iris和特征数最少且类别最多的Yeast上，差距扩大至7至10个百分点，这与"二值容量在小样本与低维度上代价显著"的直觉一致。这组结果说明PBNN-MLP不是为MNIST特别调优的构造，而是一个通用的小规模MLP替代品。

优化器与学习率调度的影响由实验`11_optimizer_scheduler_study.py`系统评估。在固定相同拓扑、相同epoch预算的条件下扫描八种优化器（带动量SGD、Adam、AdamW、NAdam、RAdam、Adamax、RMSprop与Lion[^lion]）与五种学习率调度（常数、StepLR、CosineAnnealingLR[^cosine]、OneCycleLR[^onecycle]、ExponentialLR），结果显示所有自适应优化器的最佳测试精度落在96.46%至97.16%的0.7个百分点带内，只有带动量SGD以94.41%明显落后，差距源于二值权重通过`_harden`与STE传出的梯度方差较大，对自适应per-parameter标度有依赖。学习率调度对结果的影响显著大于优化器选择：OneCycleLR配合Adam给出97.90%（整轮训练中最高），CosineAnnealingLR给出97.71%，而ExpLR与常数学习率均只有96.83%与96.81%。结合实际部署考虑，本仿真器把OneCycleLR配Adam（$$\mathrm{max\_lr}=5\times 10^{-3}$$、$$\mathrm{pct\_start}=0.3$$）作为推荐配置。为解释优化器之间的差异，实验`12_loss_landscape.py`以Goff和Li过滤器归一化的二维随机方向投影绘制损失景观：同样初始化、12轮后，带动量SGD在景观中找到的极小值是$$L(\theta^*)=2.17$$、Adam是1.38、Lion是1.14；Lion的局部曲率最尖，但绝对底部最深。在所有27个checkpoint的共享PCA投影上，三种优化器从同一初始点出发去往三个明显不同的方向（PC1加PC2解释92.7%的方差），Adam与带动量SGD大致同向但Adam走得更远，Lion几乎正交；成对线性插值显示带动量SGD与Lion之间存在高度0.90的损失垒，Adam与Lion之间为0.65，而带动量SGD与Adam之间仅0.30。这说明Lion在二值权重的STE梯度面上找到了一个与Adam或带动量SGD定性不同的basin。

## 4.6 鲁棒性与跨任务稳健性

工程上一个二值随机权重网络若不具备相对全精度网络的某种独立优势，则没有部署价值。本节通过两组实验回答PBNN到底在哪里占优：推理时的输入扰动鲁棒性与硬件比特翻转鲁棒性。

实验`07_baseline_comparison.py`对四种网络架构（PBNN $$T=4$$、PBNN $$T=64$$、确定性BNN、全精度FP-NN，共享拓扑$$784\to 1024\to 1024\to 10$$）在八种扰动类型下做了全面扫描，扰动包括加性高斯噪声、椒盐噪声、speckle乘性噪声、高斯模糊、cutout遮挡、亮度位移、权重高斯扰动与十步投影梯度下降（Projected Gradient Descent，PGD）对抗攻击。表4.4汇总了每种扰动中等强度下的测试精度。

| 扰动 | 参数 | PBNN $$T=4$$ | BNN | FP-NN |
|---|---|---|---|---|
| 加性高斯 | $$\sigma=0.5$$ | 95.84 | 95.48 | 97.48 |
| 椒盐 | $$f=0.20$$ | 89.33 | 88.54 | 94.40 |
| Speckle | $$\sigma=0.5$$ | 96.31 | 95.63 | 97.48 |
| 高斯模糊 | $$\sigma=1.5$$ | 94.82 | 94.36 | 85.43 |
| Cutout | $$k=14$$px | 75.50 | 75.17 | 82.29 |
| 亮度位移 | $$b=0.3$$ | 54.65 | 52.88 | 40.47 |
| 权重扰动 | $$\sigma_w=0.05$$ | 97.44 | 94.81 | 97.78 |
| PGD-10 | $$\epsilon=0.1$$ | 52.12 | 50.03 | 36.85 |

从定性角度，FP-NN在保持输入分布的扰动（高斯、椒盐、speckle、cutout）上有可测的优势，因为连续权重对小幅度线性扰动的吸收最为有效；PBNN在扭曲输入分布的扰动（模糊、亮度位移）上反超，因为二值权重对像素绝对值的依赖更弱；在权重空间扰动和PGD对抗攻击上，PBNN的优势最为显著。在权重扰动$$\sigma_w=0.5$$这一更激烈的工况下（表外），PBNN $$T=4$$仍保持93%以上，而BNN降至9.35%、FP-NN降至14%，体现了stochastic averaging对独立权重扰动的天然抑制：$$T$$次采样把每个权重的方差除以$$T$$。在PGD对抗攻击下，PBNN比FP-NN高出约15个百分点，其来源既包括Sign函数的梯度遮蔽，也包括前向采样带来的随机性扰乱了攻击者梯度的精度。

实验`09_hardware_bitflip.py`揭示PBNN在硬件层面更深层的优势：每个物理单元承担相同的权重重要性。FP-NN每个权重以8比特INT编码，最高有效位（Most Significant Bit，MSB）承载50%的动态范围；PBNN每个权重以$$T$$个独立Bernoulli样本编码，每个样本恒等地承担$$1/T$$的重要性。把这两种编码暴露在均匀单比特翻转概率$$p$$下，得到表4.5。

| $$p_\mathrm{flip}$$ | PBNN $$T=8$$ | PBNN $$T=64$$ | BNN（1比特） | FP-NN（8比特） |
|---|---|---|---|---|
| 0.000 | 97.55 | 97.59 | 96.59 | 98.42 |
| 0.020 | 97.31 | 97.66 | 96.28 | 97.65 |
| 0.050 | 97.30 | 97.45 | 95.06 | 92.44 |
| 0.100 | 96.26 | 96.73 | 91.22 | 52.32 |

差距在$$p\ge 0.05$$时显现：在5%翻转率下PBNN $$T=64$$仍保持97.45%，而FP-NN降至92.44%；在10%翻转率下FP-NN降至52.32%，PBNN $$T=64$$保持96.73%，差距达到44个百分点。把单MSB翻转作为极端情形：在每个权重上翻转最高位时，FP-NN的精度从98.41%（仅翻最低位）降至3.41%（翻最高位），95个百分点的差距源于位置编码下不同位的非等权地位；PBNN的同等极端情形是把所有$$T$$个样本一起翻转，但单个样本翻转的影响只有$$2/T$$。这一观察解释了为什么PBNN $$T=64$$在$$p=0.05$$下的有效错误幅度落在以0.1为中心的窄分布内，而FP-NN的有效错误幅度则呈现一个长拖尾，最大值可达1.5（超过满量程）。

## 4.7 硬件能效与跨架构横向对比

本节把PBNN sMTJ与多种有竞争性的CIM架构置于同一训练任务上做能耗对比。任务是20轮的MNIST PBNN-MLP训练（batch 128，共9380个mini-batch），每个mini-batch包含三次MAC pass：前向、反向输入梯度（$$W^\top\partial L/\partial y$$）与反向权重梯度（$$\partial L/\partial y\cdot x^\top$$）。仓库`ppa/training_energy.py`按这一拆解逐架构计算总能耗，所有非物理量地标定的常数都来自下文表格中所引文献。

仓库的`MEMORIES`注册表收录了五种主流CIM存储器（STT-MRAM[^stt_apalkov]、ReRAM[^reram_wong]、PCRAM[^pcram_burr]、铁电随机存储器（Ferroelectric RAM，FeRAM）[^feram_mikolajick]、SRAM-CIM[^sram_khwa]）与三种概率二值存储模式（sMTJ自身、Lin等人的随机ReRAM[^stoch_reram_lin]、Camsari等人2020综述中的CMOS p-bit ASIC[^cmos_pbit_camsari]）。每个条目以per-bit读能、per-cell写能、写延迟与每权重比特数四个参数描述，并附文献出处。CMOS p-bit ASIC条目特别值得展开：Camsari等人在Proc. IEEE 2020[^cmos_pbit_camsari]报告的per-update能量为5pJ，这一数已经包含了加权和、阈值与Bernoulli发生三段操作，5ns完成；同时Borders等人在Nature 2019[^borders_factor]上展示了基于sMTJ的整数因子分解原型，Sutton等人在Sci. Adv. 2020[^sutton_pbit]上展示了自治概率协处理器，这两个工作合起来给出了CMOS p-bit实测数据的边界。本仿真器把这5pJ作为CMOS p-bit ASIC的per-sample能量，与sMTJ的0.78pJ每样本（物理量地标定的Ohmic值）直接比较。

20轮训练总能耗的横向对比汇总于表4.6，按总能耗升序排列。

| 架构 | 前向 | 反向 | 写或$$\theta$$更新 | 总能耗 |
|---|---|---|---|---|
| FP-NN SRAM-CIM（易失） | 2.24J | 4.47J | 0.00J | 6.71J |
| FP-NN STT-MRAM | 4.02J | 6.26J | 0.14J | 10.42J |
| FP-NN FeRAM | 4.02J | 6.26J | 0.70J | 10.98J |
| PBNN sMTJ（$$T=4$$） | 7.09J | 4.47J | 0.35J | 11.91J |
| PBNN CMOS-PRNG（$$T=4$$） | 8.97J | 4.47J | 0.35J | 13.79J |
| FP-NN ReRAM | 4.02J | 6.26J | 6.99J | 17.27J |
| PBNN CMOS p-bit（$$T=4$$） | 44.70J | 4.47J | 0.35J | 49.52J |
| FP-NN PCRAM | 20.12J | 22.35J | 13.97J | 56.44J |
| PBNN stoch-ReRAM（$$T=4$$） | 447.97J | 4.48J | 0.35J | 452.80J |

排名首先告诉我们四件事。第一，SRAM-CIM以6.71J排在最便宜位置但其易失，在无写保持成本的训练阶段占优，而部署阶段需要外部刷新，不在本表的统计范围；在非易失架构中STT-MRAM以10.42J最低。第二，PBNN sMTJ以11.91J排在第四，是STT-MRAM的1.14倍——本仿真器评估的所有非易失CIM选项中PBNN比STT-MRAM贵14%，比ReRAM、PCRAM都更低，与FeRAM几乎持平。这一定位与第六节的鲁棒性结果合起来给出明确的取舍：为换取在比特翻转率5%至10%下精度保持在97%以上的属性（对照FP-NN在同一条件下的52.32%），付出14%的训练能耗溢价是合理的。第三，把PBNN的随机源从sMTJ换为Camsari 2020测得的CMOS p-bit ASIC，总能耗升至49.52J，是sMTJ的4.2倍，这4.2倍不是实现差异而是磁性器件相对CMOS的物理优势：sMTJ的Ohmic写能是$$V^2 t/R$$，在第二章工作点上算出$$0.78\,\mathrm{pJ}$$，而具有可比噪声裕度的CMOS Bernoulli发生器在同等时钟下需要约$$5\,\mathrm{pJ}$$。第四，以PCRAM作为权重存储的FP-NN（56.44J）和以随机ReRAM作为概率源的PBNN（452.80J）都在训练阶段成本不可承受，因为它们的per-cell写能在50至100pJ量级，无法承受每个mini-batch里数十亿次的读写。

为给sMTJ的物理量地优势提供一个可独立验证的能量拆解，实验`04_ppa_breakdown.py`在第二章参考点上把单次MAC的能量分解为DAC编程（5fJ，28nm数字默认值）、sMTJ SOT写（$$0.78\,\mathrm{pJ}$$，物理量地）、sMTJ读（5fJ，28nm数字默认值）与计数器累加（0.5fJ），累计793fJ每MAC，sMTJ写在其中占98.7%。这一比例的极端不对称给出网络层级的优化优先级：任何缩短脉冲宽度、降低写电压或增大$$R_\mathrm{SOT}$$的器件改进，会按$$V^2 t/R$$线性回报到全网能耗；反之，优化外围DAC或计数器的能耗对全网能耗的影响在1%量级，意义不大。本章在第五节确立的$$T=4$$工作点正是建立在这一权衡之上：$$T$$是PPA能耗的线性乘子，而$$T=4$$至$$T=64$$之间的精度增益不足0.2个百分点，因此$$T$$的过度增大是浪费。

## 4.8 局限与后续工作

本仿真器在三个层面有未尽事项，对应三个方向的扩展。物理层面，器件层尚未涵盖循环引入的1/f噪声漂移、长时间使用造成的TMR下降与势垒退化等老化效应；`device/llg_dynamics.py`的s-LLGS macrospin参考实现虽足以校准Sigmoid斜率，但不足以捕捉子畴动力学带来的非Markovian行为。要把sMTJ-PBNN推到工业部署所需的MTBF评估，需要把ARM与NGSPICE紧凑模型引入，把Fokker-Planck求解器作为离线校准工具，维护写错误率随$$V_\mathrm{wr}$$、$$t_\mathrm{p}$$、温度与累积写次数的统计模型，再由本仿真器的器件层接入。电路与系统层面，阵列规模目前停留在子阵列级，对$$256\times 256$$以上的tile互连压降只以IR-drop模块作了边际评估；在更大tile或多tile互连下，H-tree或mesh的非线性影响须用更细致的模型替代。PPA层的工艺常数源自NeuroSim V1.5在40nm/28nm的硅校准，本仿真器原样复用，未作工艺缩放；在迁移至5nm或更先进节点之前，$$V_\mathrm{wr}$$、$$R_\mathrm{SOT}$$与外围DAC的能耗均须重测。算法层面，本仿真器的网络层目前只覆盖前馈MLP和CNN拓扑，因为CLT高斯化前向的统计假设（权重独立加和后中心极限）在这两类拓扑上严格成立。把PBNN扩展至Transformer类网络需要重新评估CLT在自注意力子层中的有效性边界：softmax内部的归一化与$$QK^\top$$的相关结构会破坏独立性假设，可能需要把CLT替换为基于概率分布矩匹配的更广泛近似。同时，$$T$$步采样的批级并行在自回归解码场景下不能被简单地展开为CLT，因此推理时延的优化路径与本章建立的训练时延优化路径不会自动复用。这些问题留作后续工作。

## 参考文献

[^neel1949]: Néel L. Théorie du traînage magnétique des ferromagnétiques en grains fins avec application aux terres cuites. *Annales de Géophysique*, 1949, 5: 99–136.

[^brown1963]: Brown W F. Thermal fluctuations of a single-domain particle. *Physical Review*, 1963, 130(5): 1677–1686. [doi:10.1103/PhysRev.130.1677](https://doi.org/10.1103/PhysRev.130.1677)

[^krizakova2022]: Krizakova V, Perumkunnil M, Couet S, Gambardella P, Garello K. Spin-orbit torque switching of magnetic tunnel junctions for memory applications. *Journal of Magnetism and Magnetic Materials*, 2022, 562: 169692. [doi:10.1016/j.jmmm.2022.169692](https://doi.org/10.1016/j.jmmm.2022.169692)

[^cim_neurosim_validation]: Lu A, Peng X, Luo Y, Yu S. NeuroSim simulator for compute-in-memory hardware accelerator: validation and benchmark. *Frontiers in Artificial Intelligence*, 2021, 4: 659060. [doi:10.3389/frai.2021.659060](https://doi.org/10.3389/frai.2021.659060)

[^cim_dnn_neurosim_v2]: Peng X, Huang S, Jiang H, Lu A, Yu S. DNN+NeuroSim V2.0: an end-to-end benchmarking framework for compute-in-memory accelerators for on-chip training. *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*, 2021, 40(11): 2306–2319. [doi:10.1109/TCAD.2020.3043731](https://doi.org/10.1109/TCAD.2020.3043731)

[^cim_neurosim_v15]: Lu A, Peng X, Li W, Jiang H, Yu S. NeuroSim V1.5: improved software backbone for benchmarking compute-in-memory accelerators with device and circuit-level non-idealities. *arXiv preprint*, 2024. [arXiv:2504.02314](https://arxiv.org/abs/2504.02314)

[^cim_mnsim2]: Zhu Z, Sun H, Qiu K, Xia L, Krishnan G, Dai G, Niu D, Chen X, Hu X S, Cao Y, Xie Y, Wang Y, Yang H. MNSIM 2.0: a behavior-level modeling tool for memristor-based neuromorphic computing systems. *Proc. ACM Great Lakes Symposium on VLSI*, 2020: 83–88. [doi:10.1145/3386263.3407647](https://doi.org/10.1145/3386263.3407647)

[^cim_micsim]: Wang C, Yu C, Wang Y, Li B, Yang H. MICSim: a modular simulator for mixed-signal compute-in-memory based AI accelerator. *arXiv preprint*, 2024. [arXiv:2409.14838](https://arxiv.org/abs/2409.14838)

[^cim_aihwkit]: Rasch M J, Moreda D, Gokmen T, Le Gallo M, Carta F, Goldberg C, El Maghraoui K, Sebastian A, Narayanan V. A flexible and fast PyTorch toolkit for simulating training and inference on analog crossbar arrays. *Proc. IEEE International Conference on Artificial Intelligence Circuits and Systems*, 2021: 1–4. [doi:10.1109/AICAS51828.2021.9458494](https://doi.org/10.1109/AICAS51828.2021.9458494)

[^cim_aihwkit_apl]: Le Gallo M, Lammie C, Buechel J, Carta F, Fagbohungbe O, Mackin C, Tsai H, Narayanan V, Sebastian A, El Maghraoui K, Rasch M J. Using the IBM analog in-memory hardware acceleration kit for neural network training and inference. *APL Machine Learning*, 2023, 1(4): 041102. [doi:10.1063/5.0168089](https://doi.org/10.1063/5.0168089)

[^smtj_arm_compact]: Garcia-Redondo F, Lopez-Vallejo M, Stanley-Marbell P. A compact model for scalable MTJ simulation. *Proc. International Conference on Synthesis, Modeling, Analysis and Simulation Methods and Applications to Circuit Design*, 2021: 1–4. [doi:10.1109/SMACD52803.2021.9636229](https://doi.org/10.1109/SMACD52803.2021.9636229)

[^smtj_ngspice]: Pham C, Mandal A, Tomiyasu R, Lebedev A, Naeemi A. Novel STT/SHE MTJ compact model compatible with NGSPICE. *arXiv preprint*, 2022. [arXiv:2208.14055](https://arxiv.org/abs/2208.14055)

[^psl_gpu_sa]: Onizawa N, Sasaki R, Hanyu T. GPU-accelerated simulated annealing based on p-bits with real-world device-variability modeling. *Scientific Reports*, 2025, 15: 6614. [doi:10.1038/s41598-025-90520-3](https://doi.org/10.1038/s41598-025-90520-3)

[^cmos_pbit_camsari]: Camsari K Y, Sutton B M, Datta S. p-Bits for probabilistic spin logic. *Proceedings of the IEEE*, 2020, 108(8): 1335–1340. [doi:10.1109/JPROC.2020.2966869](https://doi.org/10.1109/JPROC.2020.2966869)

[^borders_factor]: Borders W A, Pervaiz A Z, Fukami S, Camsari K Y, Ohno H, Datta S. Integer factorization using stochastic magnetic tunnel junctions. *Nature*, 2019, 573: 390–393. [doi:10.1038/s41586-019-1557-9](https://doi.org/10.1038/s41586-019-1557-9)

[^sutton_pbit]: Sutton B M, Faria R, Ghantasala L A, Jaiswal R, Camsari K Y, Datta S. Autonomous probabilistic coprocessing with petaflops-equivalent capacity. *Science Advances*, 2020, 6(20): eabb2823. [doi:10.1126/sciadv.abb2823](https://doi.org/10.1126/sciadv.abb2823)

[^kaiser_insitu_bm]: Kaiser J, Borders W A, Camsari K Y, Fukami S, Ohno H, Datta S. Hardware-aware in situ learning based on stochastic magnetic tunnel junctions. *Physical Review Applied*, 2022, 17: 014016. [doi:10.1103/PhysRevApplied.17.014016](https://doi.org/10.1103/PhysRevApplied.17.014016)

[^pbnn_peters]: Peters J W T, Welling M. Probabilistic binary neural networks. *arXiv preprint*, 2018. [arXiv:1809.03368](https://arxiv.org/abs/1809.03368)

[^bnn_bayescnn]: Shridhar K, Laumann F, Liwicki M. A comprehensive guide to Bayesian convolutional neural networks with variational inference. *arXiv preprint*, 2019. [arXiv:1901.02731](https://arxiv.org/abs/1901.02731)

[^bnn_tyxe]: Ritter H, Karaletsos T. TyXe: pyro-based Bayesian neural nets for PyTorch. *arXiv preprint*, 2021. [arXiv:2110.00276](https://arxiv.org/abs/2110.00276)

[^ste]: Bengio Y, Léonard N, Courville A. Estimating or propagating gradients through stochastic neurons for conditional computation. *arXiv preprint*, 2013. [arXiv:1308.3432](https://arxiv.org/abs/1308.3432)

[^stt_apalkov]: Apalkov D, Khvalkovskiy A, Watts S, Nikitin V, Tang X, Lottis D, Moon K, Luo X, Chen E, Ong A, Driskill-Smith A, Krounbi M. Spin-transfer torque magnetic random access memory (STT-MRAM). *ACM Journal on Emerging Technologies in Computing Systems*, 2013, 9(2): 13. [doi:10.1145/2463585.2463589](https://doi.org/10.1145/2463585.2463589)

[^reram_wong]: Wong H-S P, Lee H-Y, Yu S, Chen Y-S, Wu Y, Chen P-S, Lee B, Chen F T, Tsai M-J. Metal-oxide RRAM. *Proceedings of the IEEE*, 2012, 100(6): 1951–1970. [doi:10.1109/JPROC.2012.2190369](https://doi.org/10.1109/JPROC.2012.2190369)

[^pcram_burr]: Burr G W, Brightsky M J, Sebastian A, Cheng H-Y, Wu J-Y, Kim S, Sosa N E, Papandreou N, Lung H-L, Pozidis H, Eleftheriou E, Lam C H. Recent progress in phase-change memory technology. *IEEE Journal on Emerging and Selected Topics in Circuits and Systems*, 2016, 6(2): 146–162. [doi:10.1109/JETCAS.2016.2547718](https://doi.org/10.1109/JETCAS.2016.2547718)

[^feram_mikolajick]: Mikolajick T, Schroeder U, Slesazeck S. The past, the present, and the future of ferroelectric memories. *IEEE Transactions on Electron Devices*, 2020, 67(4): 1434–1443. [doi:10.1109/TED.2020.2976148](https://doi.org/10.1109/TED.2020.2976148)

[^sram_khwa]: Khwa W-S, Chen J-J, Li J-F, Si X, Yang E-Y, Sun X, Liu R, Chen P-Y, Li Q, Yu S, Chang M-F. A 65nm 4Kb algorithm-dependent computing-in-memory SRAM unit-macro with 2.3ns and 55.8TOPS/W fully parallel product-sum operation for binary DNN edge processors. *IEEE International Solid-State Circuits Conference*, 2018: 496–498. [doi:10.1109/ISSCC.2018.8310401](https://doi.org/10.1109/ISSCC.2018.8310401)

[^stoch_reram_lin]: Lin Y-H, Wang C-H, Lee M-H, Lee D-Y, Lin Y-Y, Lee F-M, Lung H-L, Wang K-Y, Tseng T-Y, Lu C-Y. Performance impacts of analog ReRAM non-ideality on neuromorphic computing. *IEEE Transactions on Electron Devices*, 2019, 66(3): 1289–1295. [doi:10.1109/TED.2019.2894273](https://doi.org/10.1109/TED.2019.2894273)

[^uci_iris]: Fisher R A. The use of multiple measurements in taxonomic problems. *Annals of Eugenics*, 1936, 7(2): 179–188. [doi:10.1111/j.1469-1809.1936.tb02137.x](https://doi.org/10.1111/j.1469-1809.1936.tb02137.x)

[^uci_wdbc]: Wolberg W H, Mangasarian O L. Multisurface method of pattern separation for medical diagnosis applied to breast cytology. *Proceedings of the National Academy of Sciences USA*, 1990, 87(23): 9193–9196. [doi:10.1073/pnas.87.23.9193](https://doi.org/10.1073/pnas.87.23.9193)

[^uci_yeast]: Horton P, Nakai K. A probabilistic classification system for predicting the cellular localization sites of proteins. *Proc. International Conference on Intelligent Systems for Molecular Biology*, 1996, 4: 109–115.

[^uci_statlog]: King R D, Feng C, Sutherland A. Statlog: comparison of classification algorithms on large real-world problems. *Applied Artificial Intelligence*, 1995, 9(3): 289–333. [doi:10.1080/08839519508945477](https://doi.org/10.1080/08839519508945477)

[^uci_spambase]: Cranor L F, LaMacchia B A. Spam!. *Communications of the ACM*, 1998, 41(8): 74–83. [doi:10.1145/280324.280336](https://doi.org/10.1145/280324.280336)

[^lion]: Chen X, Liang C, Huang D, Real E, Wang K, Liu Y, Pham H, Dong X, Luong T, Hsieh C-J, Lu Y, Le Q V. Symbolic discovery of optimization algorithms. *Advances in Neural Information Processing Systems*, 2023, 36. [arXiv:2302.06675](https://arxiv.org/abs/2302.06675)

[^cosine]: Loshchilov I, Hutter F. SGDR: stochastic gradient descent with warm restarts. *International Conference on Learning Representations*, 2017. [arXiv:1608.03983](https://arxiv.org/abs/1608.03983)

[^onecycle]: Smith L N, Topin N. Super-convergence: very fast training of neural networks using large learning rates. *Proc. SPIE Defense + Commercial Sensing*, 2019, 11006: 1100612. [doi:10.1117/12.2520589](https://doi.org/10.1117/12.2520589)
