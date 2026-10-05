#!/usr/bin/env bash
# 交付自检 —— 每次提交前跑一遍
# 这个脚本的存在理由：原型迭代中反复出现「交付物与代码脱钩」
# （截图印着已删的元素、文档还在描述已改的交互）。
# 视觉产出没法自动验证，但「过期关键词」和「引用完整性」可以。
set -u
cd "$(dirname "$0")"

fail=0

# ⚠ 台账必须在**任何交付物审计之前**生成。
#   否则「第 8 组重写 issues.html」会把它的 mtime 推到「第 5 组检查截图」之后，
#   造成同一个脚本第一次跑绿、第二次跑红 —— 检查结果取决于这是第几次跑。
python3 "$(dirname "$0")/tools/build_ledger.py" >/dev/null 2>&1 || fail=1
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

echo "── 2. 标签配平 ──"
python3 - <<'PY' || fail=1
import pathlib, re, sys
bad=[]
for f in sorted(pathlib.Path("app").glob("*.html")):
    s=f.read_text(encoding="utf-8")
    for tag in ("style","script","head","body","html"):
        o=len(re.findall(r'<'+tag+r'[\s>]', s)); c=len(re.findall(r'</'+tag+r'>', s))
        if o!=c: bad.append(f"{f.name}: <{tag}> {o} 开 / {c} 闭")
# 未闭合的 <style> 会把后面整个文档当 CSS —— 这类错误浏览器会「恢复」，
# 页面看起来正常，但结构与作者意图完全不同。作者自己踩过一次
# （用 str.replace("</style>", X) 往前面插内容，把闭合标签替换掉了）。
for b in bad: print("     "+b)
import pathlib as _pl
_n = len(list(_pl.Path("app").glob("*.html")))
if not bad: print(f"  \033[32m✓\033[0m {_n} 页的 style/script/head/body/html 全部配平")
sys.exit(1 if bad else 0)
PY

echo "── 3. 引用完整性（死 id / 死锚点）──"
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

echo "── 4. 设计系统纪律 ──"
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
# 使用面要扫全站：token 定义在 base.css，但绝大多数使用写在 13 个页面里。
# 只扫 base.css 会把「页面专用 token」（如 --amber-ink / --red-ink）全部误报成死令牌。
import glob
used=set()
for _f in ['app/base.css'] + sorted(glob.glob('app/*.html')):
    used |= set(re.findall(r'var\((--[\w-]+)', open(_f, encoding='utf-8').read()))
dead=sorted(tok-used)
if dead: print(f"  \033[31m✗\033[0m 死令牌: {', '.join(dead)}"); sys.exit(1)
print("  \033[32m✓\033[0m base.css 无重复定义 / 括号配平 / 无死令牌")
PY

ext=$(grep -o 'https\?://' app/*.html | wc -l)
[ "$ext" -eq 0 ] && ok "零外部资源" || no "外部资源 $ext 处"

neon=$(grep -l -E 'neon|cookiebar|captcha|sysbar' app/*.html 2>/dev/null | wc -l)
[ "$neon" -eq 0 ] && ok "无已撤回的 v2 语言残留" || no "$neon 页残留 v2 元素"

echo "── 5. 脚本语法 ──"
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

echo "── 6. 对比度普查（按底色）──"
python3 "$(dirname "$0")/tools/contrast_audit.py" >/tmp/_ct.txt 2>&1 || {
  grep -E '✗|画在' /tmp/_ct.txt | sed 's/^/  /' | head -12; fail=1; }
if grep -q '全部达标' /tmp/_ct.txt; then
  n=$(grep -o '普查 [0-9]* 条' /tmp/_ct.txt | head -1)
  ok "对比度全部达标（$n）"
fi

echo "── 7. 交付物新鲜度 ──"
python3 "$(dirname "$0")/tools/delivery_audit.py" || fail=1

echo "── 8. 布局不变量（锁死已修过的坑）──"
python3 "$(dirname "$0")/tools/layout_invariants.py" || fail=1

echo "── 9. 画布不变量（浏览器级）──"
# 真渲染真测量。静态检查抓不到 fixed 溢出、横向滚动条、元素重叠、overflow 裁切 ——
# 这几条全是「量了数值但没量关系」，必须把浏览器拉进来。
if command -v firefox >/dev/null 2>&1 || [ -x /snap/firefox/current/usr/lib/firefox/firefox ]; then
  python3 "$(dirname "$0")/tools/canvas_invariants.py" || fail=1
else
  echo "     （无浏览器，跳过）"
fi

echo "── 10. PWA 接线 ──"
python3 "$(dirname "$0")/tools/pwa_selectors.py" || fail=1

echo "── 11. 路由单元测试 ──"
# routeTo 是纯函数，可以直接断言。跳转本身没法截图验证 ——
# Firefox headless 的 --screenshot 抓不到「加载期就 location.replace」的页面（截图直接失败）。
if [ -x /snap/firefox/current/usr/lib/firefox/firefox ] || command -v firefox >/dev/null 2>&1; then
  python3 "$(dirname "$0")/tools/route_test.py" || fail=1
else
  echo "     （无浏览器，跳过）"
fi


echo "── 12. 整改台账 ──"
python3 "$(dirname "$0")/tools/verify_quotes.py" || fail=1
if [ -f app/issues.html ]; then
  n=$(grep -c 'class="s-' app/issues.html 2>/dev/null || echo 0)
  [ "$n" -gt 0 ] && ok "整改台账 app/issues.html（$n 条）" || no "台账页为空"
else
  no "缺 app/issues.html"
fi

echo
[ "$fail" -eq 0 ] && printf '\033[32m全部通过\033[0m\n' || printf '\033[31m有检查未通过\033[0m\n'
exit $fail
