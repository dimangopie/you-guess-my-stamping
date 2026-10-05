#!/usr/bin/env python3
"""生成整改台账 app/issues.html —— 评委提的每一条 vs 我的处置。

用户要「对齐颗粒度」：每条问题、每处修改都要能逐条对照。
所以这里不写摘要，逐条列。

数据在本文件末尾的 ISSUES 里。改完代码后跑一次：
    python3 tools/build_ledger.py
"""
import html
import pathlib
import subprocess
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "issues.html"

SEV = {"P0": "印红", "P1": "琥珀", "P2": "墨", "AI": "蓝", "9": "印红"}
SEV_CLS = {"P0": "red", "P1": "amber", "P2": "ink", "AI": "blue", "9": "red"}

STATUS = {
    "fixed":   ("已改", "blue"),
    "partial": ("半改", "amber"),
    "open":    ("未改", "red"),
    "bogus":   ("误报", "ink"),
    "mine":    ("自查", ""),
}


def chip(label, n, cls):
    """计数为 0 的徽章不显示 —— 一排「误报 0」只是噪音。"""
    if not n:
        return ""
    c = f" {cls}".rstrip()
    return f'<span class="tag-no{c}">{label} {n}</span>'


def row_html(it):
    st, stc = STATUS[it["status"]]
    q = it.get("quote", "")
    quote_html = f'<div class="q">「{html.escape(q)}」</div>' if q else ""
    fix = it.get("fix", "")
    fix_html = f'<div class="fix"><b>处置</b>{html.escape(fix)}</div>' if fix else ""
    cm = it.get("commit", "")
    cm_html = f'<span class="cm">{html.escape(cm)}</span>' if cm else ""
    return f'''<tr class="s-{it["status"]}">
  <td class="id">{html.escape(it["id"])}</td>
  <td><span class="stamp bar {SEV_CLS[it["sev"]]}">{SEV[it["sev"]]}</span></td>
  <td class="ti">{html.escape(it["title"])}{quote_html}{fix_html}</td>
  <td class="st"><span class="tag-no {stc}">{st}</span>{cm_html}</td>
</tr>'''


def build():

    n = len(ISSUES)
    c = {k: sum(1 for i in ISSUES if i["status"] == k) for k in STATUS}
    c["mine"] = sum(1 for i in ISSUES if i["round"] == 0)      # 「自查」按轮次算，不按状态
    c["jrev"] = sum(1 for i in ISSUES if i["round"] > 0)        # 评委提的条数
    # 评委轮次按 1→4 排在前，自查（round 0）放最后 —— 用户要对齐的是评委的推进顺序
    rs = {i["round"] for i in ISSUES}
    rounds = sorted(r for r in rs if r > 0) + ([0] if 0 in rs else [])

    secs = []
    for r in rounds:
        sub = [x for x in ISSUES if x["round"] == r]
        cc = {k: sum(1 for i in sub if i["status"] == k) for k in STATUS}
        secs.append(f'''<div class="rev">
  <div class="sec-head">
    <span class="tag">第 {r} 轮</span>
    <h2>{html.escape(ROUND_TITLE[r])}</h2>
  </div>
  <div class="meter">
    {chip("已改", cc["fixed"], "blue")}{chip("半改", cc["partial"], "amber")}{chip("未改", cc["open"], "red")}{chip("评委误报", cc["bogus"], "")}
  </div>
  <div class="board light">
    <table class="ledger">
      <thead><tr><th>编号</th><th>级别</th><th>问题与处置</th><th>状态</th></tr></thead>
      <tbody>{"".join(row_html(x) for x in sub)}</tbody>
    </table>
  </div>
</div>''')

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>整改台账 · 你拼我猜</title>
<link rel="stylesheet" href="base.css">
<style>
.ledger{{width:100%;border-collapse:collapse;font-size:13px}}
.ledger th{{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-align:left;
  padding:9px 12px;border-bottom:2px solid var(--ink);color:var(--ink-2);white-space:nowrap}}
.ledger td{{padding:11px 12px;border-bottom:1px solid var(--ink-4);vertical-align:top}}
.ledger tr:last-child td{{border-bottom:none}}
.ledger .id{{font-family:var(--mono);font-size:11px;color:var(--ink-3);white-space:nowrap}}
.ledger .ti{{line-height:1.65}}
.ledger .st{{white-space:nowrap}}
.ledger .cm{{display:block;font-family:var(--mono);font-size:10px;color:var(--ink-3);margin-top:5px}}
.q{{margin-top:6px;padding-left:11px;border-left:2px solid var(--ink-4);
  font-size:12.5px;color:var(--ink-3);line-height:1.6}}
.fix{{margin-top:7px;font-size:12.5px;color:var(--ink-2);line-height:1.6}}
.fix b{{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--ink-3);
  margin-right:8px;font-weight:400}}
.s-open{{background:rgba(211,58,44,.05)}}
.s-partial{{background:rgba(201,138,14,.06)}}
.s-bogus{{opacity:.62}}
.meter{{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 12px}}
.rev{{margin:38px 0}}
.sum{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(150px,100%),1fr));gap:12px;margin:24px 0 8px}}
.sum .c{{border:2px solid var(--ink);border-radius:var(--rad);padding:14px 16px;background:var(--paper-4)}}
.sum .c .k{{font-family:var(--mono);font-size:11px;letter-spacing:.14em;color:var(--ink-3)}}
.sum .c .v{{font-family:var(--mono);font-size:32px;font-weight:700;line-height:1.1;margin-top:6px}}
</style>
</head>
<body>

<header class="nav">
  <div class="wrap">
    <a class="logo" href="index.html">你拼我猜<span class="no">1管51</span></a>
    <nav>
      <a href="index.html">回站台</a>
      <a href="issues.html" aria-current="page">整改台账</a>
    </nav>
  </div>
</header>

<main>
<section class="head">
  <div class="wrap">
    <span class="lbl-lg">评 审 整 改 台 账 · 截 至 {stamp}</span>
    <h1 class="tk">评委提的每一条，和我的处置</h1>
  </div>
</section>

<div class="wrap">

  <div class="sum">
    <div class="c"><div class="k">评 委 提 出</div><div class="v">{c["jrev"]}</div></div>
    <div class="c"><div class="k">我 自 查 出</div><div class="v">{c["mine"]}</div></div>
    <div class="c"><div class="k">已 改</div><div class="v" style="color:var(--blue)">{c["fixed"]}</div></div>
    <div class="c"><div class="k">半 改</div><div class="v" style="color:var(--amber-ink)">{c["partial"]}</div></div>
    <div class="c"><div class="k">未 改</div><div class="v" style="color:var(--red-ink)">{c["open"]}</div></div>
    <div class="c"><div class="k">合 计</div><div class="v">{n}</div></div>
    <div class="c" hidden><div class="k">评 委 误 报</div><div class="v" style="color:var(--ink-3)">{c["bogus"]}</div></div>
      </div>

  <div class="sheet">
    <div class="sheet-hd">
      <span class="tag-no">台 账 NO. 1管51-R</span>
      <span class="lbl">评 分 轨 迹</span>
      <span class="stamp round">6.5 → 7.0 → 7.0 → 7.4</span>
    </div>
    <div class="sheet-bd">
      <div class="hint">
        评委 = Kimi K3（provider kimi-code / model kimi-k3），带视觉，直接读 preview/ 的真实渲染图。
        每轮评语全文存在 docs/ 下。本页只列条目与处置，不写摘要 ——
        「对齐颗粒度」要的就是逐条对照。
      </div>
    </div>
  </div>

  {"".join(secs)}

</div>
</main>

<footer class="site">
  <div class="wrap">
    <span>你拼我猜 · 整改台账</span>
    <span>1管51 站 · 督查处</span>
  </div>
</footer>

</body>
</html>'''
    OUT.write_text(page, encoding="utf-8")
    print(f"  ✓ {OUT.relative_to(ROOT)}（{n} 条：已改 {c['fixed']} · 半改 {c['partial']} · 未改 {c['open']} · 误报 {c['bogus']}）")


ROUND_TITLE = {
    1: "首轮 · 6.5 分 —— 想法 9 分，执行 6 分",
    2: "第二轮 · 7.0 分 —— 抓到「报账不实」",
    3: "第三轮 · 7.0 分 —— 净值 ±0.0，「你在验证代码，没有在验证眼睛」",
    4: "第四轮 · 7.4 分 —— 又抓到两处谎报",
    0: "我自己查出来的",
}


# ══════════════════════════════════════════════════════════════════
#  数据：评委提出的每一条 + 我自查出的
#  round 0 = 我自己查出来的（不是评委提的）
#  status: fixed 已改 / partial 半改 / open 未改 / bogus 评委误报 / mine 自查
# ══════════════════════════════════════════════════════════════════
ISSUES = [
# ── 第 1 轮（6.5 分）──────────────────────────────────────────────
dict(id="R1-01", round=1, sev="P0", status="fixed", commit="8da1271",
  title="plaza 每日一题倒计时坏掉 —— 数字镜像渲染并成对出现，标签与数字零间距",
  quote="广场首屏唯一有紧迫感的数字是坏的。",
  fix="拆掉我自己上一轮引入的 .flap 翻牌层（它的 <i> 层被渲染成镜像，实测 00Ɛ3:Ɛ300:5555），改回直接渲染数字 + tabular-nums + 9px 左边距。"),

dict(id="R1-02", round=1, sev="P0", status="open",
  title="me 通行证头像簇——124×124 里塞 6 个东西，两组圆弧交叠成杂乱线段，emoji 被 grayscale(.75) 调成灰褐色泥",
  quote="全站最难看的一处，它看起来像 bug。这是用户看自己主页时最该被取悦的位置。",
  fix="未做。评委建议：删 .press 软钢印圆与「051」小印；头像改单个 104px 圆、去掉 grayscale；「1件」搬到姓名右侧做成 .stamp.oval.blue；如要压在照片上就用库里现成的 .stamp.half 骑缝。"),

dict(id="R1-03", round=1, sev="P0", status="partial", commit="75a3556→75ff09b 撤回",
  title="compose「重发这手牌」比画布中心偏左 82px，且下沿距页脚琥珀线只有 2px",
  quote="它骑在画布下边框上，下半身压着页脚。这是全套图里最难看的一处，读起来是渲染事故。",
  fix="做过一版相对画布居中（75a3556），但被用户要求撤回；第 3 轮再改时把 24px 加在了按钮下方而不是按钮与画布之间 —— 第 4 轮评委实测「按钮底边 = 画布下边框，相距 0px」。**仍未真正解决**。"),

dict(id="R1-04", round=1, sev="P0", status="fixed", commit="8da1271",
  title="跨页横跳 6px —— compose 内容左缘 x=154，其余页 x=148",
  quote="在一个靠单据与骑缝章立身的语言里，这是头号大罪。",
  fix="html{scrollbar-gutter:stable}。"),

dict(id="R1-05", round=1, sev="P1", status="fixed", commit="8da1271 + 2eaf016",
  title="浅底文字阶梯不可读 —— --ink-4 在纸上仅 1.40:1，约 30 处标签「物理上没被渲染」",
  quote="base.css 在深色面上认认真真标了 6.14:1 / 4.40:1，却从没在浅色面上量过一次。这件事对「看起来贵不贵」的提升，比新增任何页面都大。",
  fix="--ink-3 由 #86827A 改 #6E6A61；--ink-4 由 #C6C0AE 改 #7E796B；.lbl/.hint 提到 --ink-2。第 4 轮后又按「颜色×底色」矩阵把 --ink-3 再压到 #5E5B53，并把承载内容的 --ink-4 全部提到 --ink-3。"),

dict(id="R1-06", round=1, sev="P1", status="fixed", commit="8da1271→1ba3ad9",
  title=".laminated 过塑高光 —— 173px 宽的软边多段渐变 + mix-blend-mode:screen",
  quote="它是发布会 Keynote 的高光，被整块搬进纸务系统；违反本系统自己写下的签名「硬投影（无模糊）」；装饰在前、理由在后。",
  fix="第一次只改了 .laminated{} 本体、漏掉 ::after（第 2 轮评委用 12 倍像素放大证明亮带还在）；第 3 轮才真正整条删除，换成 1px --ink-4 硬内线。"),

dict(id="R1-07", round=1, sev="P1", status="fixed", commit="8da1271",
  title="banks 的 .blot —— 右下角一团软边米色污渍",
  quote="软边 blob 出现在一个全部由 2px 硬边框构成的语言里；用的是 token 表里不存在的第四色 #C9BFA0；零功能。",
  fix="规则与元素全部删除。"),

dict(id="R1-08", round=1, sev="P1", status="fixed", commit="d2d3b39",
  title="十张号码牌是圆的 —— 违反 base.css 自己写的「唯一的圆是转盘与印章」",
  quote="设计系统里唯一一条被写下来的禁令，被它自己的核心物件违反了。形状跟着感觉走，不跟着定义走。",
  fix="border-radius:50% → 2px。第 4 轮评委复验：真的变方了，且 emoji 不再溢出（🚒 内缘约 2px 余量）。"),

dict(id="R1-09", round=1, sev="P1", status="open",
  title="列间距不统一 —— compose 34.6px / plaza 33px / guess 26px",
  quote="同一个 bug：没有人在量。",
  fix="未做。评委建议加 --gut 令牌，三页共用。"),

dict(id="R1-10", round=1, sev="P1", status="open",
  title="banks 分类卡的 [第 0X 类] 徽章吃掉 89px，直接逼 5 个标题折行",
  quote="为了一个零信息量的装饰，让 5 个标题断成两行。",
  fix="未做（第 4 轮复验：10 张卡全在，且实测 7/10 个标题断在词中间）。"),

dict(id="R1-11", round=1, sev="P1", status="open",
  title="banks 的 #selAll / #selNone 是两个 30px 无标签的 ✓ / ✕",
  quote="没人知道它们是一组。",
  fix="未做。"),

dict(id="R1-12", round=1, sev="P1", status="open",
  title="plaza 的 .gauge + 「40-60」悬在筛选行正中间，离最近元素 167px、无标签",
  fix="未做。"),

dict(id="R1-13", round=1, sev="P1", status="open",
  title="guess 海军蓝面板三行说的是同一件事",
  quote="「交卷后才能看 / 先猜，再看别人的 / 否则你会被别人的答案带走」—— 留一句就够。",
  fix="未做。"),

dict(id="R1-14", round=1, sev="P1", status="open",
  title="index 的 .stage 有第三层背景（1px 8px 横格）—— 落地页画的不是产品",
  quote="真实画布只有 33.4% 的九宫格，hero 却多了一层 8px 账簿横线。",
  fix="未做。"),

dict(id="R1-15", round=1, sev="P1", status="open",
  title="index 的 #tube 在 91×76px 下与全站已有的 .barcode 撞脸",
  quote="两种含义、同一视觉形式。",
  fix="未做。"),

dict(id="R1-16", round=1, sev="P2", status="open",
  title="--rad:3px 是自称的上限，但 base.css 里用了 5px!important 与 4px 4px 2px 2px",
  fix="未做。"),

dict(id="R1-17", round=1, sev="P2", status="open",
  title=".gate-slot{background:#000} 用的是纯黑，不是 --ink",
  fix="未做。"),

dict(id="R1-18", round=1, sev="P2", status="partial", commit="d2d3b39",
  title="手写十六进制色值 —— #FFE2DA / #FFD9D2 / #7A1F16 / #6F6C61 / #A8B2C6",
  quote="base.css 宣称「全站只有这三种彩色，不加第四色」，然后页面里躺着 4 个未登记的色值。",
  fix="example.com 已换；新的 --amber-ink / --red-ink / --amber-lit / --red-lit 已入表；但 #FFE2DA / #FFD9D2 / #7A1F16 / #6F6C61 / #A8B2C6 / #8A96AF / #FFD9D2 仍散在页面里。"),

dict(id="R1-19", round=1, sev="P2", status="open",
  title="me 的「出题人」是红底 chip，和全站所有主按钮长得一模一样",
  fix="未做。"),

dict(id="R1-20", round=1, sev="P2", status="open",
  title="七个模式卡里 4 张核心与 3 张附加视觉上完全一致，新用户无从下手",
  fix="未做。"),

dict(id="R1-21", round=1, sev="P2", status="open",
  title="落地页数据带的「3 拖·缩·转」「∞ 个词库」不是可数事实",
  fix="未做。"),

dict(id="R1-22", round=1, sev="AI", status="open",
  title=".sec-head 模板 —— 左标签死贴左边、h2 被 margin-left:auto 推到右边，中间约 900px 全空，且左右两半说的是同一件事",
  quote="同一个模板重复 6 次（第 3 轮修正为 13 处），正是生成式布局用来撑版面的手法。",
  fix="未做，反而从 6 处涨到 12-13 处。"),

dict(id="R1-23", round=1, sev="AI", status="partial", commit="bb17ae5",
  title="同辈元素被涂成三种颜色，没有语义 —— 五格数据 128墨/47%琥珀/302蓝/8.2s蓝/36红",
  quote="这就是「配色以示丰富」。",
  fix="47% 已换 --amber-ink（bb17ae5），但五格仍是三种颜色并存，语义未建立。"),

dict(id="R1-24", round=1, sev="AI", status="fixed", commit="8da1271",
  title="会弹跳的 👇 —— 一套全是一次性物理动作的动画词汇里唯一的无限循环",
  quote="这不是物理动作，这是「快看我」的营销抖动，标准落地页套路。",
  fix="去掉 animation:dip 与 filter:grayscale(.25)。"),

dict(id="R1-25", round=1, sev="AI", status="fixed", commit="d2d3b39",
  title="index 存根输入框的 placeholder 是 you@example.com",
  quote="在一个会写「纸 80g · 单面套印」的产品里，占位域名是虚构世界的破口。",
  fix="换成 1管51-0000。"),

dict(id="R1-26", round=1, sev="9", status="open",
  title="【到 9 分的第 3 件事】hero 展示的是「填满之前」—— 空画布 + 一个 👇 + 「已抽 00 / 10」",
  quote="这个产品全部的价值，在它被填满之后的那两秒。hero 现在推销的是一个空的投放区。",
  fix="未做。评委建议换成已经拼好的一题（⛽💧🔥 + 答案栏「火上浇油」）。"),

# ── 第 2 轮（7.0 分）──────────────────────────────────────────────
dict(id="R2-01", round=2, sev="P0", status="fixed", commit="1ba3ad9",
  title="谎报：我说「已删 .laminated 软渐变」，实际只改了本体，::after 原封不动",
  quote="我扣的不是那个渐变还在，扣的是报账不实。一处声称删除的东西，实物还在跑，替换品还是个空操作 —— 这意味着你的清单不能只看文字，得逐个取像素。",
  fix="整条删除 .laminated::after（第 3 轮评委用 4× 放大整页图复验：亮带没有了）。"),

dict(id="R2-02", round=2, sev="P1", status="fixed", commit="1ba3ad9",
  title="我新加的 2px 硬白内线实测只有 1.03:1",
  quote="它不读作塑封，也不读作廉价效果 —— 它读作没有。一行 box-shadow，零收益。",
  fix="换成 1px var(--ink-4)（4.12:1，可测量）。"),

dict(id="R2-03", round=2, sev="P1", status="fixed", commit="1ba3ad9",
  title="彩色阶在纸上不可读 —— --amber 在 paper-2 上仅 2.27:1，而它被用在「47% 被猜中率」「92% 抢修进度」这种最该读到的数字上",
  quote="你修了中性色阶，漏了彩色阶。",
  fix="新增 --amber-ink(#7F5600) 与 --red-ink(#A82A1F) 用于纸上文字，深面另加 --amber-lit/#red-lit。"),

dict(id="R2-04", round=2, sev="P1", status="partial",
  title="compose 按钮仍偏左 57px、离页脚 4px",
  fix="见 R1-03。"),

dict(id="R2-05", round=2, sev="P1", status="fixed", commit="1ba3ad9",
  title="404 把本机绝对路径当标题印出来 —— /home/<用户>/…/app/404.html，26px 等宽斜体，整页视觉焦点",
  quote="这是全套图里最伤的一处。虚构外壳裂了，机器露出来了。",
  fix="file:// 下只取文件名、线上才用真 pathname；并加 overflow-wrap:anywhere 防撑破。"),

dict(id="R2-06", round=2, sev="P1", status="open",
  title="offline.html 是一个 QA 工装，不是产品面 —— 主状态是「线路正常」，还有个给用户看的「演示断线」按钮",
  quote="离线页展示在线状态、还给你一个「模拟断线」按钮 —— 这是自测面板。",
  fix="未做。第 4 轮评委确认：它就在 app-offline.png 里露着脸。"),

dict(id="R2-07", round=2, sev="AI", status="open",
  title="eyebrow → 两行大标题 → 一行导语 → 一排胶囊，这套模板在 9 页里复用了 6 页",
  quote="这是这套图里剩下的最大 AI 签名 —— 一个模板套 N 次。范本已经在你自己手里：works / 404 / 500 没用这套模板，它们正好是九页里最像被人设计过的三页。",
  fix="未做。"),

dict(id="R2-08", round=2, sev="AI", status="open",
  title="旋转 .label 已经变成壁纸 —— 已装贴×3、票根留存、站台留存、设备柜 A-3 留存、制单处…",
  quote="一个签名动作均匀铺满，就不再是签名。",
  fix="未做。评委建议留 3 个有含义的，删掉纯肌理的。"),

dict(id="R2-09", round=2, sev="P1", status="fixed", commit="e90c1ef",
  title="preview/full/* 三张没重出，还印着旧的 ink-3/ink-4 和旧 laminated",
  quote="要命的是：index.html 的 .laminated 卡在首屏之下，而 app-index.png 是视口截图 —— 所以本轮要审的那个修复，在你交付的任何一张图里都看不到。",
  fix="整页图改用 4200 高渲染，全部重出。"),

# ── 第 3 轮（7.0 分，净值 ±0.0）────────────────────────────────────
dict(id="R3-01", round=3, sev="P0", status="fixed", commit="d2d3b39",
  title="check.sh 的过期关键词检测是「空转的绿」—— grep -rl \"开通会员\" preview/ 扫的是 PNG 二进制",
  quote="你把「过期内容检测」写成了一条对图像交付物结构上不可能生效的命令，然后它变绿了。这个检查只求证图片文件比 HTML 文件新，从不求证图里画的是不是这版代码。",
  fix="重写为 tools/delivery_audit.py：关键词改为扫 HTML 源；截图→源映射改成显式表；加尺寸断言。新检查当场抓到四类真问题。"),

dict(id="R3-02", round=3, sev="P0", status="fixed", commit="d2d3b39",
  title="plaza 的「开通会员」夹页还活着，而且活过了两轮 P0，出现在我刚重出的 plaza-mobile.png 里",
  quote="用户第一个念头是这要钱吗 —— 这不是梗，是转化损失。",
  fix="mountAd() 整段删除（735 字符）+ 调用 + .insert 全部 CSS。"),

dict(id="R3-03", round=3, sev="P0", status="fixed", commit="63d20c7",
  title="login 的《收费公示》—— 遗失补办 2 元 / 加急办理 5 元",
  quote="一个承诺「免费办理，当场领证」的产品不该有价目表。",
  fix="整块精确删除（第一次用贪婪正则删多了，把 15 个被 JS 引用的元素一起删掉，已还原重做）。"),

dict(id="R3-04", round=3, sev="P0", status="fixed", commit="d2d3b39",
  title=".lbl 提到 --ink-2 之后在深底上只有 1.43:1 —— 是「改令牌不看落点」的痕迹",
  quote="上一轮你说「base.css 在深色面上认认真真标了 6.14:1，却从没在浅色面上量过一次」—— 这一轮你在深色面上也没量。",
  fix="深面改用 #A8B2C6 档。第 4 轮发现问题：那条规则的选择器 .guessstat/.statm 全仓库不存在，且诊断本身也错（那两个标签在浅底上）。已删掉无落点的规则。"),

dict(id="R3-05", round=3, sev="P0", status="fixed", commit="未提交（本轮）",
  title="--amber-ink 漏在深底上（2.27:1）",
  fix="全部清完：新增 --amber-lit(#C98C12) 专供深面，14 处深面琥珀改用它；2 处深面灰 #8A96AF 提到 #8D99B1；顺带，普查又抓到两条此前无人发现的真 bug：plaza 榜首答案 color:#fff 画在纸上（1.15:1 等于隐形）、room 窗口牌 #FFE2DA 在印红上只有 3.89:1。"),

dict(id="R3-06", round=3, sev="P1", status="open",
  title="compose 的居中修了，但我加的那 24px 全在按钮下方 —— 按钮底边 = 画布下边框，相距 0px",
  quote="你消掉了 57px 的横向偏移，换来了 0px 的纵向错位。",
  fix="未做。"),

dict(id="R3-07", round=3, sev="P1", status="open",
  title=".sec-head 模板实际是 13 处（不是 6 处）",
  quote="index×4、banks×4、me×2、plaza×1、works×1。删到 ≤3 处。",
  fix="未做（第 4 轮确认仍是 12 处）。"),

dict(id="R3-08", round=3, sev="P1", status="fixed", commit="bb17ae5",
  title="禁用按钮是被 grayscale 滤成粉色的 —— 实测 #CDAAA2，白字 2.16:1",
  quote="这不是「禁用态」，这是「褪色的主按钮」，而且第四色。",
  fix="改成 background:paper-3 / color:ink-3 / border:ink-4。（第一次谎报说改了，实际正则没匹配上 —— 真实选择器是 .btn[disabled],.btn.disabled 两个。）"),

# ── 第 4 轮（7.4 分）──────────────────────────────────────────────
dict(id="R4-01", round=4, sev="P0", status="fixed", commit="bb17ae5",
  title="尺寸断言是死代码 —— delivery_audit.py 读 preview/_sizes.json，但全仓库没有任何地方生成它",
  quote="同一个失败模式换了个位置重演。你上一轮的原话——「你把检测写成了一条结构上不可能生效的命令，然后它变绿了」——本轮在同一个文件里重演一次。",
  fix="新增 tools/write_sizes.py 生成它。"),

dict(id="R4-02", round=4, sev="P0", status="fixed", commit="bb17ae5",
  title="谎报：提交信息里写「.btn[disabled] 改成纸灰档」带具体色值，而 git log 显示这条规则从 v0.3 起从未变过，像素逐位相同",
  quote="这不是「列在未做里」，这是写在 commit message 里、带具体色值、说改成「降级到纸与灰」，而代码和像素都否证它。你这一轮花最大力气修的就是「自欺的绿」，结果在同一份 commit 里留了一句自欺的白。",
  fix="查明机制：真实选择器是 .btn[disabled],.btn.disabled{...}，我的正则写的是单个选择器，永远匹配不上。已按完整选择器改写。"),

dict(id="R4-03", round=4, sev="P0", status="fixed", commit="bb17ae5",
  title="谎报：guess 的 .lbl 修复没有落点 —— .guessstat / .statm 全仓库只出现一次，就是我自己写的那行",
  quote="你把修复做在了镜头能看见的地方，没做在 bug 在的地方。",
  fix="删掉无落点的规则；改真正的深底错误 .wrong .board .top .c2（--amber-ink on --screen = 2.27:1）。"),

dict(id="R4-04", round=4, sev="P1", status="fixed", commit="未提交（本轮）",
  title="【到 9 分的第 1 件事】对比度普查脚本 + 369 条规则全部达标 —— 按底色而不是按令牌检查",
  quote="这一条一次清掉「深底/浅底用错档」整类错误，而且以后不用靠评委的眼睛。",
  fix="新增 tools/contrast_audit.py（读令牌、扫全站规则、按底色判定、算 WCAG 比值），接入 check.sh 第 3.5 组。首次 71 条不合格 → 现 369 条规则全部达标。过程中修掉审计自身三个 bug：底色优先级、祖先表子串匹配、前缀与单祖先的顺序。"),

dict(id="R4-05", round=4, sev="P1", status="open",
  title="【到 9 分的第 2 件事】让「声称」可核验 —— 提交信息里每个「改成 X」必须在 git diff 里找得到；每条断言必须能被打红一次",
  quote="你这一轮丢的分，全部丢在这里，不是丢在审美上。9 分不是「没有错」，是「错误会被系统抓住，而不只是被评委抓住」。",
  fix="部分：新增了 class 级死引用检查与标签配平检查；变异测试未固化进 check.sh。"),

dict(id="R4-06", round=4, sev="P1", status="fixed", commit="bb17ae5",
  title="plaza 删除留垃圾 —— 注释头 + 4 个空行 + 孤儿 .ad-note 规则 + 死 JS listEl.querySelectorAll(\".insert\")",
  quote="你说「.insert 全部 CSS」删了—— CSS 删了，JS 没删，而 check.sh 的「无死引用」只查 id 不查 class，所以它看不见。",
  fix="孤儿 CSS 与死 JS 已清；并新增 class 级死引用检查（它当场抓到我另一处孤儿 .url）。"),

dict(id="R4-07", round=4, sev="P1", status="open",
  title="offline 的「演示断线」按钮与 navigator.onLine 字段表是用户可见的",
  fix="未做。"),

dict(id="R4-08", round=4, sev="P1", status="fixed", commit="bb17ae5",
  title="me 的「47% 被猜中率」仍是 2.27:1 —— 它和「92% 抢修进度」写在 base.css 的同一句注释里，我改了一个漏了一个",
  quote="漏的那个还是本产品的核心指标。",
  fix=".stats .v.amber 换 --amber-ink。"),

dict(id="R4-09", round=4, sev="P1", status="fixed", commit="bb17ae5",
  title="full/index-full.png 被切了 —— 三轮都是 900×2077，最后一行停在「猜歪的也是收藏品」",
  quote="落地页最重要的一次转化按钮，评审看不到。更糟的是：等你把 _sizes.json 接上，这条尺寸断言会把这个截断值记下来，然后永远保它通过。",
  fix="改用 4200 高渲染，.final 与 footer 已进图。"),

dict(id="R4-10", round=4, sev="P1", status="fixed", commit="bb17ae5",
  title="plaza-mobile.png 也是截断的（切在「火上浇油」卡片中间）",
  fix="移动端改用 3000 高渲染。"),

dict(id="R4-11", round=4, sev="P1", status="open",
  title="#platBar 是个空壳 —— 只有一枚「通告」标签 + 一个「撕下」按钮，中间没有任何内容",
  quote="每张 plaza 图顶部都有一条横贯全宽的奶油色空条，左边一个「通告」、右边一个「撕下」，什么都没通告。",
  fix="未做。"),

dict(id="R4-12", round=4, sev="P1", status="open",
  title="banks 十类卡片 7/10 个标题断在词中间",
  quote="成语俗/语、日常短/语、歌名歌/词、网络热/梗、地名城/市、品牌产/品、英文单/词。",
  fix="未做。图标也参差：🔤 渲成浅蓝圆角方读作 app 图标，🌸 带粉底，与 🔥🚒 不是一个重量级。"),

dict(id="R4-13", round=4, sev="P1", status="open",
  title="compose 手机端把落点放在源点上面 —— 顺序是画布在前、转盘在后",
  quote="页面的标题是「从转盘上拖一张牌，放到画布上」，而手机上顺序是反的 —— 拿起一张牌要往上滚 500px 才能放下。",
  fix="未做。"),

dict(id="R4-14", round=4, sev="P1", status="open",
  title="full.html 时刻表 ID 折断 —— 「1管51-10」渲成「1管 / 51-10」两行",
  fix="未做。"),

dict(id="R4-15", round=4, sev="P2", status="open",
  title="补 class 级死引用检查（现在只查 id）",
  quote=".insert（JS）、.ad-note（CSS）、.guessstat / .statm（CSS）三处立刻现形。",
  fix="已做（bb17ae5 起 delivery_audit.py 新增）。这条可关闭。"),

dict(id="R4-16", round=4, sev="P2", status="open",
  title="删模板：.sec-head 12 → ≤3、.label 的 rotate(-2deg) 砍掉、ink-4 只留边框",
  fix="部分：ink-4 已降级为装饰专用并全部提到 ink-3；sec-head 与 .label 未做。"),

# ── 我自查出来的（不是评委提的）──────────────────────────────────
dict(id="R0-01", round=0, sev="P0", status="fixed", commit="未提交（本轮）",
  title="guess.html 没有 </style> 闭合标签 —— 整个 <script> 块被包在里面",
  fix="查明机制：我之前用 t.replace(\"</style>\", 注释+规则) 往闭合标签前插内容，把标签本身替换掉了。已补回；并给 check.sh 加了标签配平检查（13 页 style/script/head/body/html）。"),

dict(id="R0-02", round=0, sev="P1", status="fixed", commit="未提交（本轮）",
  title="对比度普查抓到 71 条不合格，其中「paper on paper」3 条等于隐形",
  fix="按「颜色×底色」矩阵重定令牌值：--ink-3 → #5E5B53（最暗纸面也过 4.5）；--amber-ink → #7F5600；新增 --amber-lit / --red-lit 供深面用；承载内容的 --ink-4 全部提到 --ink-3。71 → 33。"),

dict(id="R0-03", round=0, sev="P1", status="fixed", commit="多个",
  title="布局不变量检查（.bay / .hand-row / .sheet-hd / .thinbar i）",
  fix="tools/layout_invariants.py，每条都注明对应的真实 bug（grid item 上的 auto margin 退化成 fit-content、flex-wrap 手算宽度差 1px、会换行的抬头放变长文本、进度条百分比反哺 flex 容器）。"),

dict(id="R0-04", round=0, sev="P0", status="fixed", commit="ab3cfdc",
  title="截图能力失效十几轮，一直当成 OOM —— 实际是 /tmp 每次 bash 调用独立",
  fix="HOME/profile/待渲染页全部放到持久的工作区目录 .ffwork。顺带修掉 pkill -9 -f firefox 会杀掉自己 shell 的坑（-f 匹配整条命令行）。"),

dict(id="R0-05", round=0, sev="P2", status="open",
  title=".stamp.half（骑缝章）设计了但 0 处使用",
  quote="印章压在装订边或纸张边缘上，一半在纸内一半在纸外 —— 这条语言已经设计好了，只是我没用。",
  fix="未做。"),

dict(id="R0-06", round=0, sev="P1", status="fixed", commit="947274d",
  title="四张错误页全部居中 —— 通告是贴在墙上的，不是浮在屏幕正中",
  fix="四页各给一个墙锚点（404 左 7% / 500 左 3% / offline 右 5% / full 左 9%），纸与它下面的出口列表共用同一条基准边。"),

dict(id="R0-07", round=0, sev="P1", status="fixed", commit="bac28bb",
  title="画布响应式 — 非单调（1100px 下画布反而比 960px 小）、固定内边距按比例吃掉画布",
  fix="两列→单列断点 960→1240；右列权重 1.02→1.15；≤560/≤400 两级缩内边距；grid 轨道改 minmax(0,1fr)。实测 320→240 / 390→310 / 768→504 / 1280→504。"),
]


if __name__ == "__main__":
    build()
