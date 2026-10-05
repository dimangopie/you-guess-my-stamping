#!/usr/bin/env python3
"""画布页的浏览器级不变量 —— 静态检查抓不到的那些。

K3 第五轮的原话：
  「这次四个 bug 里没有一个会被它（layout_invariants.py）抓到：
    fixed 溢出、横向滚动条、元素重叠、overflow:auto 的裁切 ——
    全都是『量了数值但没量关系』。」

确实。layout_invariants.py 是纯静态的 CSS 文本检查，
而这次四个 bug 全是**渲染后**才存在的几何关系。这个脚本把浏览器拉进来，真渲染真测量。

五条断言，每条对应一个真实发生过的 bug：
  A. 画布页不滚            —— 改前 1440 下滚 64px、1024 下滚 547px
  B. 无横向溢出            —— position:fixed 的浮层把整页顶出 15px
  C. 轨道内的元素不溢出     —— 左轨压到 200px 时转盘右侧被切 92px
  D. 画布是正方形          —— 曾出现 544x368 的长方
  E. 重发按钮落在画布内     —— 曾相对外层定位、溢出画布右缘 45px

读数方式：探针把整屏涂绿（全过）或涂红（有失败），脚本读中心像素。
为什么不用 console / title：Firefox headless 的这两种输出都不好取。
为什么不用 CDP：本机没有 Chromium。
"""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
WORK = pathlib.Path("/home/mango/workspace/.ffwork")
FF = "/snap/firefox/current/usr/lib/firefox/firefox"

# 1024x768 是老笔记本 / iPad 横屏 —— 上一轮正是它掉进了无人区。
VIEWPORTS = [(1024, 768), (1280, 800), (1440, 900), (1920, 1080)]
PAGES = ["compose.html"]

PROBE = r'''<script>
(function(){
  var fails=[];
  var de=document.documentElement;

  // A. 不滚
  var dy = de.scrollHeight - innerHeight;
  if (dy > 2) fails.push("纵向要滚 "+dy+"px");

  // B. 无横向溢出
  var dx = de.scrollWidth - innerWidth;
  if (dx > 2) fails.push("横向溢出 "+dx+"px");

  // C. 轨道内不溢出
  document.querySelectorAll(".sheet, .canvas-box, .canvas-fit").forEach(function(e){
    if (e.scrollWidth  > e.clientWidth  + 2)
      fails.push((e.className||"?").split(" ")[0]+" 横向裁切 "+(e.scrollWidth-e.clientWidth)+"px");
    if (e.scrollHeight > e.clientHeight + 2)
      fails.push((e.className||"?").split(" ")[0]+" 纵向裁切 "+(e.scrollHeight-e.clientHeight)+"px");
  });

  // D/E. 画布是正方形，且按钮在画布里
  var c=document.querySelector(".canvas");
  if (c) {
    var C=c.getBoundingClientRect();
    if (Math.abs(C.width-C.height) > 2)
      fails.push("画布非正方 "+Math.round(C.width)+"x"+Math.round(C.height));
    var btn=document.getElementById("resetBtn");
    if (btn) {
      var T=btn.getBoundingClientRect();
      if (!(T.left>=C.left-1 && T.right<=C.right+1 && T.top>=C.top-1 && T.bottom<=C.bottom+1))
        fails.push("重发按钮溢出画布");
    }
  } else {
    fails.push("找不到 .canvas");
  }

  // 涂色：绿=全过，红=有失败
  var d=document.createElement("div");
  d.style.cssText="position:fixed;inset:0;z-index:2147483647;background:"+(fails.length?"#FF0000":"#00CC00");
  document.body.appendChild(d);
  if (fails.length) {
    var p=document.createElement("pre");
    p.style.cssText="position:fixed;left:0;top:0;z-index:2147483647;color:#fff;"
      +"font:16px/1.6 monospace;padding:20px;margin:0;white-space:pre-wrap";
    p.textContent=fails.join("\n");
    document.body.appendChild(p);
  }
})();
</script>
</body>'''


def check(page, w, h):
    """渲染并返回 (是否通过, 失败说明)"""
    (WORK / "home").mkdir(parents=True, exist_ok=True)
    (WORK / "shots").mkdir(parents=True, exist_ok=True)
    q = WORK / "app" / page
    q.parent.mkdir(parents=True, exist_ok=True)
    q.write_text((APP / page).read_text(encoding="utf-8").replace("</body>", PROBE, 1),
                 encoding="utf-8")
    shot = WORK / "shots" / f"inv_{page}_{w}x{h}.png"
    subprocess.run([FF, "--headless", "--no-remote", f"--window-size={w},{h}",
                    "--screenshot", str(shot), f"file://{q}"],
                   env={**os.environ, "HOME": str(WORK / "home")},
                   capture_output=True, timeout=120)
    if not shot.exists():
        return False, "渲染失败"
    r = subprocess.run(["convert", str(shot),
                        "-format", "%%[pixel:p{%d,%d}]" % (w // 2, h // 2), "info:"],
                       capture_output=True, text=True)
    col = r.stdout.strip().lower()
    if "0,204,0" in col or "00cc00" in col:
        return True, ""
    return False, "涂红（中心像素 " + col + "）"


def main():
    bad = []
    for page in PAGES:
        for w, h in VIEWPORTS:
            ok, why = check(page, w, h)
            if not ok:
                bad.append(f"{page} {w}x{h}: {why}")
    for b in bad:
        print("     " + b)
    if not bad:
        print(f"  \033[32m✓\033[0m 画布不变量：{len(PAGES)} 页 × {len(VIEWPORTS)} 视口全部通过"
              f"（不滚 / 无横向溢出 / 无裁切 / 画布正方 / 按钮在画布内）")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
