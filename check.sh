#!/usr/bin/env bash
# 交付自检 —— 每次提交前跑一遍
# 这个脚本的存在理由：原型迭代中反复出现「交付物与代码脱钩」
# （截图印着已删的元素、文档还在描述已改的交互）。
# 视觉产出没法自动验证，但「过期关键词」和「引用完整性」可以。
set -u
cd "$(dirname "$0")"

fail=0
ok(){ printf '  \033[32m✓\033[0m %s\n' "$1"; }
no(){ printf '  \033[31m✗\033[0m %s\n' "$1"; fail=1; }

echo "── 1. 结构 ──"
n=$(ls app/*.html | wc -l)
echo "     页面 $n 个"

dead=$(grep -o 'href="#"' app/*.html | wc -l)
[ "$dead" -le 4 ] && ok "死链 href=\"#\" = $dead（其余由 JS 接管）" || no "死链 href=\"#\" = $dead，偏多"

# 引用了不存在的页面
miss=0
for f in app/*.html; do
  for h in $(grep -oE 'href="[a-z0-9_-]+\.html' "$f" | sed 's/href="//' | sort -u); do
    [ -f "app/$h" ] || { echo "     缺: $(basename "$f") → $h"; miss=$((miss+1)); }
  done
done
[ "$miss" -eq 0 ] && ok "无悬空链接" || no "悬空链接 $miss 处"

echo "── 2. 引用完整性（死 id / 死锚点）──"
python3 - <<'PY' || fail=1
import re, pathlib, sys
bad=0
for f in sorted(pathlib.Path("app").glob("*.html")):
    t=f.read_text(encoding="utf-8")
    ids=set(re.findall(r'\bid="([^"]+)"', t))
    refs=set()
    for pat in (r'\$\("#?([A-Za-z0-9_-]+)"\)', r'getElementById\("#?([A-Za-z0-9_-]+)"\)',
                r'querySelector\("#([A-Za-z0-9_-]+)"\)'):
        refs |= set(re.findall(pat, t))
    for r in sorted(refs-ids):
        print(f"     {f.name}: 死引用 #{r}"); bad+=1
    for a in sorted(set(re.findall(r'href="#([A-Za-z0-9_-]+)"', t))-ids):
        print(f"     {f.name}: 死锚点 #{a}"); bad+=1
print("  \033[32m✓\033[0m 无死引用 / 无死锚点" if not bad else f"  \033[31m✗\033[0m {bad} 处")
sys.exit(1 if bad else 0)
PY

echo "── 3. 设计系统纪律 ──"
redef=$(grep -lE '^\.(nav|btn|sheet|ticket|stamp|seal|board|stats|meters|dot|mode|idx|stubcard|snap|hole|bind|label|slot|creased|laminated|struck|field|window-sign|queue-no|gauge|pip|ico|ibtn|say)\{' app/*.html 2>/dev/null | wc -l)
[ "$redef" -eq 0 ] && ok "无顶格零件重定义" || no "有 $redef 页重定义了共享零件"

python3 - <<'PY' || fail=1
import re, pathlib, collections, sys
t=pathlib.Path("app/base.css").read_text(encoding="utf-8")
c=collections.Counter(s.strip() for s in re.findall(r'^([.\w][^{]*?)\{', t, re.M)
                  if not s.startswith('@') and '%' not in s)
dup=[s for s,n in c.items() if n>1]
if dup: print(f"  \033[31m✗\033[0m base.css 重复定义: {', '.join(dup)}"); sys.exit(1)
if t.count('{')!=t.count('}'): print("  \033[31m✗\033[0m base.css 括号不配平"); sys.exit(1)
tok=set(re.findall(r'(--[\w-]+)\s*:', t))
used=set(re.findall(r'var\((--[\w-]+)', t))
dead=sorted(tok-used)
if dead: print(f"  \033[31m✗\033[0m 死令牌: {', '.join(dead)}"); sys.exit(1)
print("  \033[32m✓\033[0m base.css 无重复定义 / 括号配平 / 无死令牌")
PY

ext=$(grep -o 'https\?://' app/*.html | wc -l)
[ "$ext" -eq 0 ] && ok "零外部资源" || no "外部资源 $ext 处"

neon=$(grep -l -E 'neon|cookiebar|captcha|sysbar' app/*.html 2>/dev/null | wc -l)
[ "$neon" -eq 0 ] && ok "无已撤回的 v2 语言残留" || no "$neon 页残留 v2 元素"

echo "── 4. 脚本语法 ──"
bad=0
for f in app/*.html; do
  python3 -c "
import re,sys,subprocess,pathlib
t=pathlib.Path('$f').read_text(encoding='utf-8')
js='\n'.join(re.findall(r'<script>(.*?)</script>',t,re.S))
if js.strip():
    pathlib.Path('/tmp/_chk.js').write_text(js,encoding='utf-8')
    sys.exit(subprocess.run(['node','--check','/tmp/_chk.js'],capture_output=True).returncode)
" || { echo "     $f 语法错误"; bad=$((bad+1)); }
done
[ "$bad" -eq 0 ] && ok "全部页面 JS 通过 node --check" || no "$bad 页语法错误"

echo "── 5. 交付物新鲜度 ──"
python3 - <<'PY' || fail=1
import pathlib, sys
app=pathlib.Path("app"); pv=pathlib.Path("preview")
stale=[]
for p in sorted(app.glob("*.html")):
    v=pv/f"app-{p.stem}.png"
    if not v.exists(): stale.append(f"{p.stem}(无图)")
    elif p.stat().st_mtime>v.stat().st_mtime: stale.append(p.stem)
for f in sorted((pv/"full").glob("*.png")):
    sp=app/f"{f.name.split('-')[0]}.html"
    if sp.exists() and sp.stat().st_mtime>f.stat().st_mtime: stale.append(f"full/{f.name}")
if stale: print(f"  \033[31m✗\033[0m 截图过期: {', '.join(stale)}"); sys.exit(1)
print("  \033[32m✓\033[0m 全部截图新于源文件")
PY

# 已删除的元素不该再出现在交付物里
stale_kw=0
for kw in '001337' '开通会员' '回 执' '签收' '物理拨杆' '自转转盘'; do
  hits=$(grep -rl "$kw" preview/ README.md index.html 2>/dev/null | tr '\n' ' ')
  [ -n "$hits" ] && { echo "     过期关键词「$kw」出现在: $hits"; stale_kw=$((stale_kw+1)); }
done
[ "$stale_kw" -eq 0 ] && ok "交付物无已删元素的残留描述" || no "$stale_kw 个过期关键词"

echo "── 6. 布局不变量（锁死已修过的坑）──"
python3 "$(dirname "$0")/tools/layout_invariants.py" || fail=1

echo "── 7. PWA 接线 ──"
python3 "$(dirname "$0")/tools/pwa_selectors.py" || fail=1

echo
[ "$fail" -eq 0 ] && printf '\033[32m全部通过\033[0m\n' || printf '\033[31m有检查未通过\033[0m\n'
exit $fail
