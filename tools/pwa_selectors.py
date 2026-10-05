#!/usr/bin/env python3
"""pwa.js 注入按钮时用的选择器，必须在真实页面里存在。

为什么单独查这个：pwa.js 是**静默失败**的典型 ——
选择器写错时它不报错、不抛异常，只是什么都不做。
之前把 .nav 写成 .site-nav，页面看起来完全正常，按钮却从未出现。
这类错误没有运行时症状，只能静态查。
"""
import pathlib, re, sys

js = pathlib.Path("app/pwa.js").read_text(encoding="utf-8")
pages = sorted(pathlib.Path("app").glob("*.html"))
bad = []

sels = re.findall(r'querySelector(?:All)?\("([^"]+)"\)', js)
for s in sels:
    # 只检查挂在页面骨架上的选择器（.nav .wrap 这种）
    if " " not in s: continue
    for cls in re.findall(r'\.([A-Za-z][\w-]*)', s):
        missing = [p.name for p in pages
                   if not re.search(r'class="[^"]*\b'+re.escape(cls)+r'\b', p.read_text(encoding="utf-8"))]
        if missing:
            bad.append(f'pwa.js 的 "{s}" 用到 .{cls}，但这些页面没有：{", ".join(missing[:4])}')

# 每个页面都必须挂了 pwa.js，否则按钮只在部分页面出现
for p in pages:
    t = p.read_text(encoding="utf-8")
    if "pwa.js" not in t: bad.append(f"{p.name} 没有引入 pwa.js")
    if 'rel="manifest"' not in t: bad.append(f"{p.name} 没有 link rel=manifest")

for b in bad: print("     " + b)
if not bad:
    print(f"  \033[32m✓\033[0m pwa.js 选择器在 {len(pages)} 个页面均存在，且每页都挂了 manifest + pwa.js")
sys.exit(1 if bad else 0)
