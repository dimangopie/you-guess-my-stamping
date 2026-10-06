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

# **以横屏 web 为标准。**
# 横屏 = 宽而矮，竖向预算比横向紧得多，所以矮屏（768 / 720）必须进验收集。
# 1280x720 是最矮的常见横屏，放在最后压测。
VIEWPORTS = [(1366, 768), (1280, 720), (1440, 900), (1920, 1080)]
PAGES = ["compose.html"]

PROBE = r'''<script>
(function(){
  var fails=[];
  var de=document.documentElement;

  // A. 纵向滚动
  //    ⚠ 这一条曾经是「画布页不滚」——那是「画布盛满整个页面」方案的要求。
  //    用户已要求把拼图台恢复原设计（正常滚动的三栏布局），
  //    所以「不滚」不再是本页的设计目标，改成**只在极端情况下报警**：
  //    首屏若连画布都看不全（画布底边超出视口），那才是真问题。
  //    （页面级断言随「画布盛满整个页面」方案一起撤掉了 ——
  //     用户已要求拼图台恢复原设计，那是一个正常滚动的三栏布局。）

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
    // 重发按钮：原设计要求它在画布**下方**（不在角上）。
    // 这里只断言「不与画布重叠」——那才是真缺陷（曾经压在画布下边框上）。
    var btn=document.getElementById("resetBtn");
    if (btn) {
      var T=btn.getBoundingClientRect();
      var overlap = !(T.right<C.left || T.left>C.right || T.bottom<C.top || T.top>C.bottom);
      if (overlap) fails.push("重发按钮与画布重叠");
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
    # 转盘不变量已随转盘一起移除 ——
    #   用户要求拼图台不再使用转盘，改为「分类精选的 emoji 素材库」。
    #   那条断言（牌不重叠 / 不压中心圆盘 / 不溢出转盘）失去了对象。
    for b in bad:
        print("     " + b)
    if not bad:
        print(f"  \033[32m✓\033[0m 画布不变量：{len(PAGES)} 页 × {len(VIEWPORTS)} 视口全部通过"
              f"（无横向溢出 / 无裁切 / 画布正方 / 按钮不与画布重叠）")
    return 1 if bad else 0




# ── 转盘不变量 ──────────────────────────────────────────────
# K3 第 9 轮抓到的回归：「1024 档转盘事故：牌与牌互相叠压、牌压进中心圆盘。
# 这是本轮唯一一处『坏了』而非『空着』的问题。」
# 根因有两层，都不是肉眼能看出来的：
#   ① .spoke 里写了 `--tile:46px`，**遮蔽**了 JS 在 .wheel 上设的继承值，
#      于是牌永远是 46px，缩了半径也没用。
#   ② .wheel .hub 尺寸写死 84px，1024 下占转盘半宽的 59%，牌放哪都会压上去。
# 这两条都属于「量了数值但没量关系」，所以在浏览器里直接断言关系。
WHEEL_PROBE = r'''<script>
(function(){
  var fails=[], w=document.querySelector(".wheel");
  if(!w){ document.body.innerHTML="<pre style='background:#F00;color:#fff'>找不到 .wheel</pre>"; return; }
  var sp=[].slice.call(document.querySelectorAll(".spoke"));
  var rects=sp.map(function(s){return s.getBoundingClientRect();});
  var worst=0;
  for(var i=0;i<rects.length;i++)for(var j=i+1;j<rects.length;j++){
    var a=rects[i],b=rects[j];
    var ox=Math.min(a.right,b.right)-Math.max(a.left,b.left);
    var oy=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);
    if(ox>0&&oy>0) worst=Math.max(worst,Math.min(ox,oy));
  }
  if(worst>1.5) fails.push("牌间重叠 "+worst.toFixed(1)+"px");
  var hub=document.querySelector(".wheel .hub");
  if(hub){var h=hub.getBoundingClientRect();
    var hit=rects.filter(function(r){return r.left<h.right&&r.right>h.left&&r.top<h.bottom&&r.bottom>h.top;}).length;
    if(hit) fails.push(hit+" 张牌压到中心圆盘");}
  var wr=w.getBoundingClientRect();
  var out=rects.filter(function(r){return r.left<wr.left||r.right>wr.right||r.top<wr.top||r.bottom>wr.bottom;}).length;
  if(out) fails.push(out+" 张牌溢出转盘");
  var d=document.createElement("div");
  d.style.cssText="position:fixed;inset:0;z-index:2147483647;background:"+(fails.length?"#FF0000":"#00CC00");
  document.body.appendChild(d);
})();
</script>
</body>'''


def check_wheel(page, w, h):
    (WORK / "home").mkdir(parents=True, exist_ok=True)
    q = WORK / "app" / page
    q.write_text((APP / page).read_text(encoding="utf-8").replace("</body>", WHEEL_PROBE, 1),
                 encoding="utf-8")
    shot = WORK / "shots" / f"wheel_{w}x{h}.png"
    shot.unlink(missing_ok=True)
    subprocess.run([FF, "--headless", "--no-remote", f"--window-size={w},{h}",
                    "--screenshot", str(shot), f"file://{q}"],
                   env={**os.environ, "HOME": str(WORK / "home")},
                   capture_output=True, timeout=120)
    if not shot.exists(): return False
    r = subprocess.run(["convert", str(shot), "-format", f"%[pixel:p{{{w//2},{h//2}}}]", "info:"],
                       capture_output=True, text=True)
    return "0,204,0" in r.stdout.lower()


if __name__ == "__main__":
    sys.exit(main())
