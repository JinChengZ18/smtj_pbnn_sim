# 附录A 代码与数据可用性

本文的全部仿真、训练与电路评估均可由公开代码与公开数据复现。本附录给出软件构成、运行环境与逐项结果的复现入口。

## A.1 软件构成

仿真框架 `smtj_pbnn_sim` 以 Python 实现，分为四个相互独立又可组合的部分：

- **器件层**：SOT-MTJ 的热激活 Néel–Brown 开关模型与标定后的行为级 Sigmoid 写入概率 $$P_\mathrm{sw}(V)$$，并配套一个宏自旋 LLG 数值求解器作为交叉验证。
- **网络层**：概率二值神经网络 (PBNN) 的二值线性层/卷积层、sign-STE 反传与时域展开 (T 次 Bernoulli 采样) 推理，以及确定性 BNN 与全精度/INT8 基线。
- **储备池层**：以 sMTJ 电报噪声节点构成的储备池计算 (reservoir computing) 与记忆容量评估。
- **PPA 层**：在统一工艺参数下组合每次乘累加 (MAC) 的能量、时延与面积，用于与数字基线的能效对照。

电路评估部分基于开源 sky130 工艺设计套件 (PDK) 与开源 EDA 工具链 (ngspice、Magic、KLayout、OpenVAF、netgen)，用于把仿真器的外围能量输入 (读出灵敏放大器、写入驱动、写线 IR、SAR/电阻串 DAC 等) 锚定到可验证的晶体管级与版图级数据。

## A.2 运行环境

Python 3.10 及以上；核心依赖为 PyTorch、NumPy、SciPy、Matplotlib、pandas (网络/仿真) 与 PyYAML。

数据集训练在单张消费级 GPU 或 CPU 上即可完成；本文 MNIST 与表格任务的单次训练在分钟量级。

电路评估在 Linux 环境 (本文使用 WSL Ubuntu) 下通过原生 ngspice 与 sky130A PDK 运行；Windows 侧仅用于纯文本/绘图脚本。

## A.3 关键结果的复现入口

下表把正文与附录的主要结论对应到可直接运行的脚本 (均位于 `experiments/`，从仓库根目录运行)。

| 结论 | 复现脚本 |
|---|---|
| 器件 Sigmoid 标定与晶圆平均斜率 $$\beta_s$$ | `02_wafer_average_mc.py` |
| MNIST PBNN-MLP 精度与基线对照 | `05_mnist_pbnn.py` |
| 时域展开采样次数 $$T$$ 的精度-能耗折中 | `06_sweep_T_vs_accuracy.py` |
| PBNN-CNN 在 Fashion-MNIST / CIFAR-10 的扩展 (附录B) | `05a_fashion_mnist_pbnn_cnn.py`, `05a_cifar10_pbnn_cnn.py` |
| 储备池 vs 数字 ESN 的能效对照 | `16_rc_hardware_ppa.py` |
| 每次 MAC 的 PPA 分解 | `04_ppa_breakdown.py` |
| 主要结论对随机数种子的稳健性 (附录C) | `21_seed_independence.py` |

电路侧的外围能量锚定脚本位于 `eda/` (例如读出灵敏放大器提取、写入驱动与写线 IR、电阻串 DAC 与计数器能量)，其方法与待补足项记录在仓库的工程文档中。

## A.4 数据可用性

- MNIST、Fashion-MNIST 与 CIFAR-10 均为公开标准数据集，经 torchvision 自动下载；UCI 表格任务取自 UCI 机器学习库。
- 器件模型的标定靶值来自正文第 2 章所述的 SOT-MTJ 测量数据。
- sky130 PDK 为公开开源工艺套件，电路评估所需的全部工艺常数随其分发。
