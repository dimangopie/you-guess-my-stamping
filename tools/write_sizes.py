#!/usr/bin/env python3
"""记录整页/移动端截图应有的高度，供 delivery_audit.py 断言。

K3 第四轮抓到：delivery_audit.py 读 preview/_sizes.json，但这个文件
**全仓库没有任何地方生成它** —— 于是那条"尺寸断言"结构上永远不会执行，
而 check.sh 照样打绿字。同一个失败模式换了个位置重演。
这个脚本就是补上生成端。
"""
import json, pathlib, subprocess, sys

root = pathlib.Path(__file__).resolve().parent.parent
pv = root / "preview"
out = {}
for f in sorted(list((pv / "full").glob("*.png"))):
    r = subprocess.run(["identify", "-format", "%h", str(f)], capture_output=True, text=True)
    if r.stdout.strip():
        out["full/" + f.name] = int(r.stdout)
(pv / "_sizes.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"  ✓ 写入 preview/_sizes.json（{len(out)} 条）")
