#!/usr/bin/env python3
"""布局不变量 —— 锁死已经修过的、肉眼看不出来的坑。

每一条都对应一个真实发生过的 bug：

  A. grid item 上的 margin-left:auto 会吸收自由空间、使 justify-self:stretch
     失效，元素退化成 fit-content（宽随内容变）。若其后代带 aspect-ratio，
     高度就跟着跳。.bay 踩过：宽在 342↔395 之间漂，画布高跟着变。

  B. 十张牌用 flex-wrap + 手算宽度：10 张 + 9 个 5px 间隙 = 45px，
     公式少减 1px 就换行，行高直接翻倍。

  C. 会换行的抬头里放变长文本（#ans 从「— — — —」变成真答案）→ +1 行高。

  D. 进度条的宽度百分比相对 flex item 解析，而该 item 的宽度又依赖文本宽度
     → 反馈回路。#fill 必须脱离文档流。
"""
import pathlib, re, sys

idx = pathlib.Path("app/index.html").read_text(encoding="utf-8")
bad = []

# ── A. .bay 不得用 auto margin 右对齐 ──
m = re.search(r'\.bay\{([^}]*)\}', idx)
if not m:
    bad.append(".bay 规则不见了")
else:
    b = m.group(1)
    if "margin-left:auto" in b:
        bad.append(".bay 又用回 margin-left:auto —— 宽度会随内容变")
    if "justify-self:end" not in b:
        bad.append(".bay 缺 justify-self:end")
    if "width:100%" not in b:
        bad.append(".bay 缺 width:100%")

# ── B. 十张牌必须是 grid ──
m = re.search(r'\.hand-row\{([^}]*)\}', idx)
if not m:
    bad.append(".hand-row 规则不见了")
else:
    b = m.group(1)
    if "flex-wrap" in b:
        bad.append(".hand-row 又用 flex-wrap —— 1px 误差就换行")
    if "grid" not in b:
        bad.append(".hand-row 必须是 grid")
    if "min-height" not in b:
        bad.append(".hand-row 缺 min-height，空状态会塌")

# ── C. 样张抬头不得换行 ──
m = re.search(r'\.tpaper>\.sheet-hd\{([^}]*)\}', idx)
if m and "nowrap" not in m.group(1):
    bad.append(".tpaper>.sheet-hd 又会换行 —— #ans 变长就 +1 行")

# ── D. 进度条必须脱离文档流 ──
m = re.search(r'\.thinbar i\{([^}]*)\}', idx)
if not m:
    bad.append(".thinbar i 规则不见了")
elif "position:absolute" not in m.group(1):
    bad.append(".thinbar i 必须 position:absolute —— 否则宽度会参与祖先的尺寸计算")

for b in bad:
    print("     " + b)
if not bad:
    print("  \033[32m✓\033[0m 未被破坏（.bay / .hand-row / .sheet-hd / .thinbar i）")
sys.exit(1 if bad else 0)
