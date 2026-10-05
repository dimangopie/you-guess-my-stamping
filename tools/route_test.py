#!/usr/bin/env python3
"""pwa.js 的 routeTo 单元测试。

跳转本身没法截图验证 —— Firefox headless 的 --screenshot 抓不到
「加载期就 location.replace」的页面（截图直接失败）。
所以把路由拆成纯函数 routeTo(key)，在这里断言。

绿=全过，红=有失败（读数同 canvas_invariants.py）。
"""
import os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path("/home/mango/workspace/.ffwork")
FF = "/snap/firefox/current/usr/lib/firefox/firefox"

CASES = [
    ("room", "room.html"), ("/room", "room.html"),
    ("#/compose", "compose.html"), ("COMPOSE", "compose.html"),
    ("  /plaza  ", "plaza.html"), ("#guess", "guess.html"),
    ("nosuch", None), ("", None), ("#/", None),
]


def main():
    (WORK / "app").mkdir(parents=True, exist_ok=True)
    (WORK / "home").mkdir(exist_ok=True)
    (WORK / "shots").mkdir(exist_ok=True)
    (WORK / "app" / "pwa.js").write_bytes((ROOT / "app" / "pwa.js").read_bytes())
    js = ",".join('[%s,%s]' % (repr(a).replace("'", '"'),
                              "null" if b is None else '"%s"' % b) for a, b in CASES)
    page = '''<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script src="pwa.js"></script>
<script>
var cases=[%s];
var out=cases.map(function(c){
  var got=window.YPWC_ROUTE_TO(c[0]); var ok=(got===c[1]);
  return (ok?"PASS":"FAIL")+"  routeTo("+JSON.stringify(c[0])+") = "+JSON.stringify(got)+"  期望 "+JSON.stringify(c[1]);
});
var bad=out.filter(function(s){return s.indexOf("FAIL")===0}).length;
document.body.style.cssText="margin:0;font:13px/1.6 monospace;padding:10px;white-space:pre;background:"+(bad?"#FF0000":"#00CC00");
document.body.textContent="routeTo "+(cases.length-bad)+"/"+cases.length+"\\n"+out.join("\\n");
</script></body></html>''' % js
    q = WORK / "app" / "_routetest.html"
    q.write_text(page, encoding="utf-8")
    shot = WORK / "shots" / "routetest.png"
    shot.unlink(missing_ok=True)
    subprocess.run([FF, "--headless", "--no-remote", "--window-size=900,320",
                    "--screenshot", str(shot), f"file://{q}"],
                   env={**os.environ, "HOME": str(WORK / "home")},
                   capture_output=True, timeout=90)
    if not shot.exists():
        print("     routeTo 单元测试：渲染失败"); return 1
    r = subprocess.run(["convert", str(shot), "-format", "%[pixel:p{450,160}]", "info:"],
                       capture_output=True, text=True)
    col = r.stdout.strip().lower()
    if "0,204,0" in col:
        print(f"  \033[32m✓\033[0m routeTo 单元测试 {len(CASES)}/{len(CASES)} 通过"
              f"（#/room · /room · COMPOSE · 空白 · 未知路由不干预）")
        return 0
    print("     routeTo 有断言失败（涂红）"); return 1


if __name__ == "__main__":
    sys.exit(main())
