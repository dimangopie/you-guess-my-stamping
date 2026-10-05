#!/usr/bin/env python3
"""布局不变量 —— 锁死已经修过的、肉眼看不出来的坑。

每一条都对应一个真实发生过的 bug：
  A. grid item 上的 margin-left:auto 会吸收自由空间、使 justify-self:stretch 失效，
     元素退化成 fit-content（宽随内容变）。若其后代带 aspect-ratio，高度就跟着跳。
  B. 十张牌用 flex-wrap + 手算宽度：10 张 + 9 个 5px 间隙 = 45px，公式少减 1px 就换行，
     行高直接翻倍。
  C. 会换行的抬头里放变长文本（#ans 从「— — — —」变成真答案）→ +1 行高。
  D. 油墨滤镜塞进 CSS 变量或 data-URI → Firefox 静默不渲染。
"""
import pathlib, re, sys

idx  = pathlib.Path("app/index.html").read_text(encoding="utf-8")
base = pathlib.Path("app/base.css").read_text(encoding="utf-8")
bad  = []

m = re.search(r'\.bay\{([^}]*)\}', idx)
if not m: bad.append(".bay 规则不见了")
else:
    b = m.group(1)
    if "margin-left:auto" in b: bad.append(".bay 又用回 margin-left:auto —— 宽度会随内容变")
    if "justify-self:end" not in b: bad.append(".bay 缺 justify-self:end")
    if "width:100%" not in b: bad.append(".bay 缺 width:100%")

m = re.search(r'\.hand-row\{([^}]*)\}', idx)
if not m: bad.append(".hand-row 规则不见了")
else:
    b = m.group(1)
    if "flex-wrap" in b: bad.append(".hand-row 又用 flex-wrap —— 1px 误差就换行")
    if "grid" not in b: bad.append(".hand-row 必须是 grid")
    if "min-height" not in b: bad.append(".hand-row 缺 min-height，空状态会塌")

m = re.search(r'\.tpaper>\.sheet-hd\{([^}]*)\}', idx)
if m and "nowrap" not in m.group(1):
    bad.append(".tpaper>.sheet-hd 又会换行 —— #ans 变长就 +1 行")

if "url(#ink-soft)" not in base: bad.append("base.css 丢了 url(#ink-soft)")
# 只有「用 filter:var(...) 中转」才是不渲染的写法。
# 注意 --fiber 也是 data-URI SVG，但它用在 background-image 上，工作正常，不能误报。
if re.search(r'filter:\s*var\(--', base):
    bad.append("油墨滤镜又用 filter:var(...) 中转 —— Firefox 完全不会渲染")
if 'id="ink-soft"' not in idx: bad.append("index.html 少了内联 svg defs")

for b in bad: print("     " + b)
if not bad:
    print("  \033[32m✓\033[0m 未被破坏（.bay / .hand-row / .sheet-hd / 油墨滤镜）")
sys.exit(1 if bad else 0)
