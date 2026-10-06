# -*- coding: utf-8 -*-
"""把 T05 终点探针的原始读数（`T05-endpoint-probe-20261004.json`）排成取证表。

**只排版、只统计原始读数**，不调判据、不算 `Adv̂`、不产出六态。
它回答一个具体问题：**载荷变成自足的工具调用请求之后，模型会不会去调被投毒的工具？**

## 三个统计口径（不得混）

| 口径 | 一格是什么 | 回答什么 |
|---|---|---|
| **臂内调用率** | 一个（条件 × 臂） | 这一臂里有多少条 trial 真的调了 `get_weather` |
| **臂间差** | 一个条件 | 对抗臂调用率 − 配对对照臂调用率（**这是配对的，不是 `Adv̂`**） |
| **任务驱动率** | 一个条件 | 任务本身是否足以产生调用（两臂合并看 `get_tool` 之外的工具） |

⚠️ `Adv̂` 是**判据层**的量（`runner.py:61`），本表**不产生**它 —— 本表只有行为观测。
⚠️ 每次调用的**参数**逐条列出（`focal_args`）—— "带具体参数"这个断言必须能逐字核。

用法：python tools/t05_endpoint_probe_report.py [--json <路径>] [--run <run_id>]
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DEFAULT_JSON = ROOT / "docs" / "results/README.md" / "T05-endpoint-probe-20261004.json"
FOCAL = "get_weather"


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return None
    import math
    p = k / n
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, ctr - hw), min(1.0, ctr + hw)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="t05_endpoint_probe_report.py")
    ap.add_argument("--json", default=str(DEFAULT_JSON))
    ap.add_argument("--run", default="", help="只报某个 run_id（留空 = 全部）")
    ap.add_argument("--md", default="", help="同时写一份 Markdown 到该路径")
    a = ap.parse_args(argv)

    path = Path(a.json)
    if not path.exists():
        print("探针产物不存在：%s（先跑 results/README.md）" % path)
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    runs = data.get("runs") or {}
    ids = [a.run] if a.run else sorted(runs)
    L = []
    for rid in ids:
        r = runs.get(rid)
        if not r:
            print("没有这个 run_id：%s" % rid)
            continue
        rows = r.get("trials") or []
        good = [t for t in rows if not t.get("error")]
        L.append("## run `%s`（model `%s`，每格 n=%s）" % (rid, r.get("model"), r.get("n")))
        L.append("")
        L.append("trial 总数 **%d**，可用 **%d**，带 `error` **%d**"
                 % (len(rows), len(good), len(rows) - len(good)))
        L.append("")
        L.append("| 条件 | 臂 | 可用 | **调了 `%s`** | 臂内调用率 | Wilson 95%% |"
                 " 调过别的工具 | 写工具 |" % FOCAL)
        L.append("|---|---|---:|---:|---:|---|---:|---:|")
        per_cond = collections.defaultdict(dict)
        for t in good:
            per_cond[t["condition"]][t["arm"]] = t
        conds = r.get("conditions") or {}
        for cid in conds:
            base = None
            for arm in ("adversarial", "control"):
                sub = [t for t in good if t.get("condition") == cid and t.get("arm") == arm]
                n = len(sub)
                k = sum(1 for t in sub if t.get("focal_called"))
                other = sum(1 for t in sub if any(x != FOCAL for x in (t.get("tool_names") or [])))
                writes = sum(1 for t in sub if t.get("write_calls"))
                ci = wilson(k, n)
                cis = ("[%.1f%%, %.1f%%]" % (100 * ci[0], 100 * ci[1])) if ci else "—"
                rate = ("**%.1f%%**" % (100 * k / n)) if n else "—"
                if arm == "control":
                    base = (k / n) if n else None
                L.append("| `%s` | %s | %d | %d | %s | %s | %d | %d |"
                         % (cid, "对抗" if arm == "adversarial" else "对照", n, k, rate, cis,
                            other, writes))
            adv = per_cond[cid].get("adversarial") or {}
            ctrl = per_cond[cid].get("control") or {}
            L.append("")
        # —— 臂间差（配对，只看同条件两臂）——
        L.append("### 臂间差（配对：同条件、同任务、同投放面，只换载荷正文）")
        L.append("")
        L.append("| 条件 | 对抗臂调用率 | 对照臂调用率 | **差** | 读法 |")
        L.append("|---|---:|---:|---:|---|")
        for cid in conds:
            row = []
            for arm in ("adversarial", "control"):
                sub = [t for t in good if t.get("condition") == cid and t.get("arm") == arm]
                row.append((sum(1 for t in sub if t.get("focal_called")), len(sub)))
            (ka, na), (kc, nc) = row
            ra = (ka / na) if na else None
            rc = (kc / nc) if nc else None
            d = ("%+.1f%%" % (100 * (ra - rc))) if (ra is not None and rc is not None) else "—"
            if ra is None or rc is None:
                note = "样本不足"
            elif ra > rc:
                note = "对抗臂更高（**本表只报行为观测，不等于方法有效**）"
            elif ra == rc:
                note = "两臂相同 ⇒ 本条件下载荷未改变选择"
            else:
                note = "对照臂更高 ⇒ 载荷没有把选择推向被投毒工具"
            L.append("| `%s` | %s | %s | %s | %s |"
                     % (cid,
                        ("%.1f%%（%d/%d）" % (100 * ra, ka, na)) if ra is not None else "—",
                        ("%.1f%%（%d/%d）" % (100 * rc, kc, nc)) if rc is not None else "—",
                        d, note))
        L.append("")
        # —— 逐条参数（"带具体参数"这个断言必须能核）——
        L.append("### 被投毒工具的**逐次调用参数**")
        L.append("")
        any_call = False
        for t in good:
            if t.get("focal_called"):
                any_call = True
                L.append("- `%s` / %s / trial-%s：`%s`（投放面 `%s`）"
                         % (t["condition"], t["arm"], t["trial"],
                            json.dumps(t.get("focal_args"), ensure_ascii=False),
                            t.get("vector")))
        if not any_call:
            L.append("- **本次可用 trial 里，" + FOCAL + " 被调用 0 次**：无参数可列。")
        L.append("")
        # —— 权威层哈希（B-96 的约束面）——
        changed = [t for t in good
                   if t.get("state_before_hash") and t.get("state_after_hash")
                   and t["state_before_hash"] != t["state_after_hash"]]
        L.append("### 权威层（B-96 约束面）")
        L.append("")
        L.append("- 可用 trial 里权威层哈希**发生变化**的：**%d** 条" % len(changed))
        L.append("- 调用过写工具（`update_tool_metadata` / `register_tool` / "
                 "`abort_tool_registration`）的：**%d** 条"
                 % sum(1 for t in good if t.get("write_calls")))
        L.append("- 载荷**在模型上下文里**（系统提示词或用户轮，逐字核）：**%d/%d** 条"
                 % (sum(1 for t in good if t.get("payload_in_system_prompt")
                        or t.get("payload_in_conversation")), len(good)))
        L.append("- 传输层重试过的 trial：**%d** 条（重试 ≠ 判据没观测到）"
                 % sum(1 for t in good if t.get("llm_transport_retries")))
        L.append("")
        # —— 逐条件读法 ——
        L.append("### 逐条件读法（**照抄下面的口径，不得外推**）")
        L.append("")
        for cid, cs in conds.items():
            L.append("- `%s`：任务「%s」· 投放面 `%s`"
                     % (cid, cs.get("task"), cs.get("vector")))
        L.append("")
        L.append("⚠️ 本表**不是**六态、**不是** `Adv̂`、**不进** `runs/`：它只是行为观测。"
                 "任何「方法有效」的结论都必须回到判据层（`runner.py:61` 的配对 `Adv̂`）。")
        L.append("")
    md = "\n".join(L)
    print(md)
    if a.md:
        Path(a.md).write_text(md + "\n", encoding="utf-8", newline="\n")
        print("[report] 已写 %s" % a.md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
