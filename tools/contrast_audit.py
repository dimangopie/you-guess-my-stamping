#!/usr/bin/env python3
"""对比度普查 —— 按「底色」而不是按「令牌」检查可读性。

为什么需要这个脚本（K3 三轮的原话）：

  第一轮：「base.css 在深色面上认认真真标了 6.14:1 / 4.40:1，
          却从没在浅色面上量过一次。」
  第三轮：「上一轮你说'从没在浅色面上量过一次'—— 这一轮你在深色面上也没量。」
  第四轮：「对比度普查脚本（唯一还没做的那条 P0，也是我最想看的）。」

前两轮我都是**按类名批量换色**，不看那个类名落在什么底色上，
于是修好了浅底、弄坏了深底（让 .lbl 在 --screen 上掉到 1.43:1），
反过来又漏掉深底上真正的错（.wrong .board .top .c2 的 2.27:1）。

人眼看不出来，也没法靠"记得每个类名用在哪"来保证。所以做一次普查。

## 背景判定

核心是「这个颜色画在什么底色上」。做法：
  1. 从 base.css 的 :root 读出全部令牌
  2. 扫**全站**（base.css + 13 个页面）收集 选择器 → 背景色
  3. 对一个带 color 的规则，从它自己的选择器开始，
     逐级往左退（.a .b .c → .a .b → .a），取第一个声明了背景的祖先
  4. 都找不到 → 页面默认底 --paper
  5. 算 WCAG 对比度

这是启发式，不是渲染引擎。它会漏（比如 JS 动态加的 class、
伪元素、渐变背景），但**它能抓住系统性的「深底/浅底用错档」**，
而那正是前三轮反复出问题的地方。

用法：
    python3 tools/contrast_audit.py          # 只列不合格的
    python3 tools/contrast_audit.py -v       # 全部列出
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"

# ── WCAG ──────────────────────────────────────────────────────────
def _lum(hexcolor):
    h = hexcolor.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    except ValueError:
        return None
    ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]

def contrast(fg, bg):
    l1, l2 = _lum(fg), _lum(bg)
    if l1 is None or l2 is None:
        return None
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)

# ── 令牌 ──────────────────────────────────────────────────────────
def load_tokens():
    css = (APP / "base.css").read_text(encoding="utf-8")
    root = re.search(r':root\s*\{(.*?)\n\}', css, re.S)
    toks = {}
    if root:
        for m in re.finditer(r'(--[\w-]+)\s*:\s*(#[0-9A-Fa-f]{3,8})', root.group(1)):
            toks[m.group(1)] = m.group(2)
    return toks

TOKENS = load_tokens()

def resolve(val):
    """把 color 的值解析成 #rrggbb；解析不了返回 None。"""
    if not val:
        return None
    val = val.strip().rstrip("!important").strip()
    m = re.match(r'var\(\s*(--[\w-]+)\s*(?:,([^)]*))?\)', val)
    if m:
        if m.group(1) in TOKENS:
            return TOKENS[m.group(1)]
        return resolve(m.group(2)) if m.group(2) else None
    m = re.match(r'(#[0-9A-Fa-f]{3,8})\b', val)
    if m:
        return m.group(1)
    named = {"#fff": "#ffffff", "#000": "#000000", "white": "#ffffff", "black": "#000000"}
    return named.get(val.lower())

# ── 扫规则 ────────────────────────────────────────────────────────
def style_blocks(path):
    s = path.read_text(encoding="utf-8")
    return re.findall(r'<style[^>]*>(.*?)</style>', s, re.S)

def parse_rules(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    css = re.sub(r'@(?:media|supports)[^{]*\{', '', css)   # 摊平媒体查询
    out = []
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
        sel, body = m.group(1).strip(), m.group(2)
        if any(sel.startswith(x) for x in ("@", "from", "to", "0%", "100%")):
            continue
        out.append((sel, body))
    return out

# 全站收集「选择器 → 底色」
BG = {}
for f in [APP / "base.css"] + sorted(APP.glob("*.html")):
    blocks = [f.read_text(encoding="utf-8")] if f.suffix == ".css" else style_blocks(f)
    for css in blocks:
        for sel, body in parse_rules(css):
            m = re.search(r'(?:^|;)\s*background(?:-color)?\s*:\s*([^;]+)', body)
            if m:
                c = resolve(m.group(1).split()[0])
                if c:
                    for one in sel.split(","):
                        BG.setdefault(one.strip(), c)

PAGE_BG = TOKENS.get("--paper", "#F2EFE4")

def effective_bg(sel):
    """从最具体的选择器逐级往左退，找第一个有背景的祖先。

    退法有两种，都要试：
      ① 空格前缀：.a .b .c → .a .b → .a
      ② **剥连字符**：.gate-top .gk → .gate-top → .gate
         （BEM 风格的类名把「容器」写在「部位」前面，
          .gate-top 的背景其实来自 .gate{background:--screen}。
          第一版没有这一步，把 .nav .logo / .gate-top .gk / #score .throw
          全判成了「页面默认 --paper」，一口气误报十几条。）
    """
    for one in sel.split(","):
        parts = re.split(r'\s+', one.strip())
        for n in range(len(parts), 0, -1):
            head = parts[:n]
            # ① 原样
            cands = [" ".join(head)]
            # ② 把最后一段逐级剥连字符
            last = head[-1]
            stem = re.sub(r':{1,2}[\w-]+(\([^)]*\))?', '', last)
            while "-" in stem:
                stem = stem.rsplit("-", 1)[0]
                cands.append(" ".join(head[:-1] + [stem]))
            # ③ 单个祖先：.wrong .board .top .c2 的真正底色来自 .board，
            #    它不是任何前缀。第二版只试前缀，把这一整类判成了页面默认。
            for seg in reversed(head):
                cands.append(seg)
            for cand in cands:
                if cand in BG:
                    return BG[cand], cand
                clean = re.sub(r':{1,2}[\w-]+(\([^)]*\))?', '', cand)
                if clean in BG:
                    return BG[clean], clean
    return PAGE_BG, "（页面默认 --paper）"

# ── 普查 ──────────────────────────────────────────────────────────
rows, fails = [], []
for f in sorted(APP.glob("*.html")) + [APP / "base.css"]:
    blocks = [f.read_text(encoding="utf-8")] if f.suffix == ".css" else style_blocks(f)
    for css in blocks:
        for sel, body in parse_rules(css):
            m = re.search(r'(?:^|;)\s*color\s*:\s*([^;]+)', body)
            if not m:
                continue
            fg = resolve(m.group(1))
            if not fg:
                continue                       # inherit / currentColor / 渐变文字，跳过
            sm = re.search(r'font-size\s*:\s*([\d.]+)px', body)
            fw = re.search(r'font-weight\s*:\s*(\d{3}|bold)', body)
            big = bool(sm and float(sm.group(1)) >= 18) or \
                  bool(sm and float(sm.group(1)) >= 14 and fw and
                       (fw.group(1) == "bold" or int(fw.group(1)) >= 700))
            need = 3.0 if big else 4.5
            bg, src = effective_bg(sel)
            r = contrast(fg, bg)
            if r is None:
                continue
            rows.append((r, need, f.name, sel.strip()[:52], fg, bg, src[:24], big))
            if r < need:
                fails.append(rows[-1])

rows.sort()
if "-v" in sys.argv:
    print(f"{'比值':>6} {'需要':>5}  文件 / 选择器")
    for r, need, fn, sel, fg, bg, src, big in rows:
        flag = "✗" if r < need else " "
        print(f"{r:6.2f} {need:5.1f} {flag} {fn:<12} {sel:<54} {fg} on {bg}  ← {src}")
else:
    print(f"普查 {len(rows)} 条带 color 的规则（底色靠启发式判定）\n")
    if not fails:
        print("  \033[32m✓\033[0m 全部达标（正文 ≥4.5:1，大字 ≥3:1）")
    for r, need, fn, sel, fg, bg, src, big in fails:
        tag = "大字" if big else "正文"
        print(f"  \033[31m✗\033[0m {r:5.2f}:1（{tag}需 {need}）  {fn:<12} {sel}")
        print(f"        {fg} 画在 {bg} 上   ← 底色来自 {src}")

sys.exit(1 if fails else 0)
