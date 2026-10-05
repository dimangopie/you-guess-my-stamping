#!/usr/bin/env python3
"""核验台账里每条引文是否真的能在 docs/ 的评审全文里找到。

K3 第五轮的原话：
  「你把 48 条引文逐条去仓库里找出处：能在 docs/*.md 找到 8 条，
    只存在于 build_ledger.py 40 条。第 2、3、4 轮的评审全文，在你的仓库里一个字都没有。」
  「『引用原话』这个做法没有解决转述失真，它把转述失真制度化了。」

这个脚本让「不是原话的说成原话」变成结构性不可能：
  · 每条 quote 必须在 docs/NN-review-k3-rN.md 里找到**连续的子串**
  · 找不到的，要么改成真原话，要么显式标 paraphrase=True

用连续子串而不是模糊匹配 —— 因为失真恰恰发生在「大致是这个意思」的地方。
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def load_issues():
    src = (ROOT / "tools" / "build_ledger.py").read_text(encoding="utf-8")
    ns = {}
    body = src[src.find("ISSUES = ["):]
    exec(body.split("\nif __name__")[0], ns)
    return ns["ISSUES"]


def doc_text(round_no):
    """第 N 轮的评审全文"""
    for f in DOCS.glob(f"*review-k3-r{round_no}.md"):
        return f, f.read_text(encoding="utf-8")
    return None, ""


def normalize(s):
    """去掉空白与换行差异 —— 中文引文里的换行不该算失真。"""
    return re.sub(r"\s+", "", s)


def main():
    issues = load_issues()
    miss, ok, para = [], 0, 0
    for it in issues:
        q = (it.get("quote") or "").strip()
        if not q:
            continue
        if it.get("paraphrase"):
            para += 1
            continue
        r = it.get("round", 0)
        f, txt = doc_text(r) if r > 0 else (None, "")
        if not txt:
            miss.append((it["id"], q[:42], f"第 {r} 轮没有评审全文存档"))
            continue
        if normalize(q) in normalize(txt):
            ok += 1
        else:
            miss.append((it["id"], q[:42], "在评审全文里找不到这段连续文字"))

    print(f"  引文核验：{ok} 条逐字可查 · {para} 条已标「复述」 · {len(miss)} 条查无出处")
    for i, q, why in miss:
        print(f"    ✗ {i:<8} 「{q}…」  {why}")
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(main())
