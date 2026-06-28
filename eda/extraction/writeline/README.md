# `writeline/` — 写线 IR 压降与写能量开销

由提取的 sky130 方块电阻标定列写线寄生电阻，评估其对写电压交付与写能量的影响。

## 方法
1. `gen_writeline_straps.py`（KLayout）：生成已知几何的金属条（poly/li1/met1/met2/met3，各
   L=200 µm × W=0.5 µm = 400 方块），两端打标签 → `writeline_straps.gds`。
2. `run_extresist.sh`（Magic）：对金属条 `extract do resistance → extract all → extresist → ext2spice`
   读端到端电阻。校验：提取 poly = 47.96 Ω/□，对 sky130A techfile 的 48.2 Ω/□ 差 0.5%，确认提取流程
   与方块电阻表。
3. `analyze_ir_drop.py`（Python）：把 techfile 方块电阻（TT 与高角）标度到真实列写线，比较寄生串阻、
   IR 压降与能量对 776 Ω 写器件。

sky130 方块电阻（Ω/□）：li1 12.8 · met1 0.125 · met2 0.125 · met3 0.047 · poly 48.2；
接触（Ω）：mcon 9.3 · via1 4.5 · via2 3.41。

## 模型
标定写点：0.9 V 跨 776 Ω、0.75 ns → 0.783 pJ（$$I_\mathrm{write}=1.16\,\mathrm{mA}$$）。片上路径加往返
金属电阻（位线驱动→单元 + 源线单元→回流），$$R_\mathrm{par}=2 R_s (N\cdot\text{pitch}/W)$$ 与 776 Ω
串联；IR 压降 $$=I_\mathrm{write} R_\mathrm{par}$$，附加能量 $$=I_\mathrm{write}^2 R_\mathrm{par} t$$
（均为 $$R_\mathrm{par}/776$$）。假设 cell_pitch = 2 µm；以比值报告。

## 结果（`ir_drop_summary.json`）
| 列高 N | met2, W=1 µm | $$R_\mathrm{par}$$ | IR 压降 | 占 776 Ω |
|---|---|---|---|---|
| 16 | 可忽略 | 8 Ω | 9 mV | 1.0% |
| 64 | 小 | 32 Ω | 37 mV | 4.1% |
| 256 | 显著 | 128 Ω | 148 mV | 16.5%（高角 19%） |
| 1024 | 严重 | 512 Ω | 594 mV | 66% |

N=256 时 met3 加宽（W=2 µm）降至约 3%；li1 灾难性（6.5–26 kΩ），写线勿走 li1/poly。端部过孔栈约加
28 Ω（3.6%），并联过孔可降。

## 结论与设计指引
- IR 压降：小列（N≤64）可忽略（<5%），高列（N≥256）显著（met1/met2 约 16%）。写线走 met2 及以上、
  加宽或对高列分段；N≥256 预算约 10–20% 写裕度。
- 写电压裕度：N=256 的 148 mV 压降使远端单元仅见约 0.75 V，跌破 0.8958 V 标定写点，移动写概率
  Sigmoid → 远端写错误升，除非补偿（IR 感知预畸变，见 `array/ir_drop.py` 与
  `experiments/20_write_ir_drop.py`）。
- 端到端写能量：在 0.783 pJ 器件写之上加 $$R_\mathrm{par}/776$$（N=256 met2 约 +16.5%）。

## 复现
```bash
wsl -d Ubuntu-24.04-EDA -- bash -lc \
  'cd "<repo>/eda/extraction/writeline" && klayout -b -r gen_writeline_straps.py && bash run_extresist.sh'
python eda/extraction/writeline/analyze_ir_drop.py
```
