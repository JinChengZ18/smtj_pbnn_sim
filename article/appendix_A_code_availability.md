# 附录A 代码与数据可用性

本文的全部仿真、训练与电路评估均可由公开代码与公开数据复现。本附录给出软件构成、运行环境与逐项结果的复现入口。

## A.1 软件构成

仿真框架 `smtj_pbnn_sim` 以Python实现，分为四个相互独立又可组合的部分：

- **器件层**：SOT-MTJ的热激活Néel–Brown开关模型与标定后的行为级Sigmoid写入概率$$P_\mathrm{sw}(V)$$，并配套一个宏自旋LLG数值求解器作为交叉验证。
- **网络层**：概率二值神经网络 (PBNN) 的二值线性层/卷积层、sign-STE反传与时域展开 (T次Bernoulli采样) 推理，以及确定性BNN与全精度/INT8基线。
- **储备池层**：以sMTJ电报噪声节点构成的储备池计算 (reservoir computing) 与记忆容量评估。
- **PPA层**：在统一工艺参数下组合每次乘累加 (MAC) 的能量、时延与面积，用于与数字基线的能效对照。

电路评估部分基于开源sky130工艺设计套件 (PDK) 与开源EDA工具链 (ngspice、Magic、KLayout、OpenVAF、netgen)，用于把仿真器的外围能量输入 (读出灵敏放大器、写入驱动、写线IR、SAR/电阻串DAC等) 锚定到可验证的晶体管级与版图级数据。

## A.2 运行环境

Python 3.10及以上；核心依赖为PyTorch、NumPy、SciPy、Matplotlib、pandas (网络/仿真) 与PyYAML。

数据集训练在单张消费级GPU或CPU上即可完成；本文MNIST与表格任务的单次训练在分钟量级。

电路评估在Linux环境 (本文使用WSL Ubuntu) 下通过原生ngspice与sky130A PDK运行；Windows侧仅用于纯文本/绘图脚本。

## A.3 关键结果的复现入口

下表把正文与附录的主要结论对应到可直接运行的脚本 (均位于 `experiments/`，从仓库根目录运行)。

| 结论 | 复现脚本 |
|---|---|
| 器件Sigmoid标定与晶圆平均斜率$$\beta_s$$ | `02_wafer_average_mc.py` |
| MNIST PBNN-MLP精度与基线对照 | `05_mnist_pbnn.py` |
| 时域展开采样次数$$T$$的精度-能耗折中 | `06_sweep_T_vs_accuracy.py` |
| PBNN-CNN在Fashion-MNIST / CIFAR-10的扩展 (附录B) | `05a_fashion_mnist_pbnn_cnn.py`, `05a_cifar10_pbnn_cnn.py` |
| 储备池vs数字ESN的能效对照 | `16_rc_hardware_ppa.py` |
| 每次MAC的PPA分解 | `04_ppa_breakdown.py` |
| 主要结论对随机数种子的稳健性 (附录C) | `21_seed_independence.py` |

电路侧的外围能量锚定脚本位于 `eda/` (例如读出灵敏放大器提取、写入驱动与写线IR、电阻串DAC与计数器能量)。

## A.4 数据可用性

- MNIST、Fashion-MNIST与CIFAR-10均为公开标准数据集，经torchvision自动下载；UCI表格任务取自UCI机器学习库。
- 器件模型的标定靶值来自正文第2章所述的SOT-MTJ测量数据。
- sky130 PDK为公开开源工艺套件，电路评估所需的全部工艺常数随其分发。
