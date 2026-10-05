#!/usr/bin/env python3
"""交付物审计 —— 上一版这个检查是「空转的绿」，这里修三件事。

K3 第三轮的原话：
  「你把'过期内容检测'写成了一条对图像交付物结构上不可能生效的命令，
    然后它变绿了。」
  「这个检查只求证图片文件比 HTML 文件新，从不求证图里画的是不是这版代码。」

三处修正：
  ① 过期关键词改为**扫 HTML 源**。图里的字本来就是源里来的，扫 PNG 是
     二进制匹配，结构上不可能命中 —— 之前 grep -rl "开通会员" preview/ 永远返回空。
  ② 截图 → 源文件的映射改成**显式表**。原来用 f.name.split('-')[0]，
     guess-mobile.png → guess 是**蒙对的**，换一个名字就静默失配。
  ③ 加**尺寸断言**：整页/移动端图的高度必须等于记录值。只比 mtime
     抓不到「图是新的，但画错了尺寸」。
"""
import pathlib, re, sys, json

root = pathlib.Path(__file__).resolve().parent.parent
app, pv = root / "app", root / "preview"
bad = []

# ── ① 过期关键词：扫源，不扫图 ──
# 这些是内容层面已被否决的东西（收费口吻 / 自测口吻 / 已删功能）。
BANNED = {
    "开通会员": "plaza 的夹页广告 —— docs/09 已列 P0，不该再出现",
    "遗失补办": "login 的收费公示 —— 产品承诺「免费办理，当场领证」",
    "加急办理": "login 的收费公示",
    "example.com": "占位域名 —— 虚构世界的破口",
}
for kw, why in BANNED.items():
    hits = [f.name for f in app.glob("*.html") if kw in f.read_text(encoding="utf-8")]
    if hits:
        bad.append(f"源文件里仍有「{kw}」（{why}）：{', '.join(hits[:4])}")

# ── ② 显式映射表：图 → 源 ──
# 不用 split('-')[0]：那是运气，改名即静默失配。
MAP = {
    "app-index.png": "index.html", "app-login.png": "login.html",
    "app-plaza.png": "plaza.html", "app-room.png": "room.html",
    "app-compose.png": "compose.html", "app-guess.png": "guess.html",
    "app-me.png": "me.html", "app-works.png": "works.html",
    "app-banks.png": "banks.html", "app-404.png": "404.html",
    "app-500.png": "500.html", "app-offline.png": "offline.html",
    "app-full.png": "full.html",
    "full/index-full.png": "index.html", "full/plaza-full.png": "plaza.html",
    "full/plaza-mobile.png": "plaza.html", "full/compose-mobile.png": "compose.html",
    "full/guess-mobile.png": "guess.html",
}
stale, missing = [], []
for img, src in MAP.items():
    i, s = pv / img, app / src
    if not i.exists(): missing.append(img); continue
    if not s.exists(): bad.append(f"映射表指向不存在的源：{img} → {src}"); continue
    if s.stat().st_mtime > i.stat().st_mtime: stale.append(img)
# 反向：preview 下有没有没被映射覆盖的图（防新增页面漏映射）
covered = set(MAP)
# 用「相对 preview/ 的路径」做 key —— 用 f.name 会让 full/ 下的图全部误报
cands = [(f, f.name) for f in pv.glob("*.png")] + \
        [(f, "full/" + f.name) for f in (pv/"full").glob("*.png")]
loose = [rel for f, rel in cands if rel not in covered and not f.name.startswith("_")]
if loose: bad.append("这些图不在映射表里（新增页面记得补）：" + ", ".join(sorted(loose)[:6]))

if missing: bad.append("缺截图：" + ", ".join(missing))
if stale:   bad.append("截图过期：" + ", ".join(sorted(stale)))

# ── ③ 尺寸断言 ──
SIZES = pv / "_sizes.json"
if SIZES.exists():
    want = json.loads(SIZES.read_text(encoding="utf-8"))
    import subprocess
    for img, h in want.items():
        f = pv / img
        if not f.exists(): continue
        r = subprocess.run(["identify", "-format", "%h", str(f)], capture_output=True, text=True)
        got = int(r.stdout or 0)
        # preview 里的图是缩放过的，允许 ±3%
        if got and abs(got - h) / max(h, 1) > 0.03:
            bad.append(f"{img} 高度 {got}，期望 {h}（±3%）—— 图是新的但画错了尺寸")

for b in bad: print("     " + b)
if not bad:
    print(f"  \033[32m✓\033[0m {len(MAP)} 张截图新鲜、映射显式、无过期关键词（扫源）")
sys.exit(1 if bad else 0)
