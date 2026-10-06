#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 method_id 精确点名跑一个批次。

与 `python -m harness.cli run --case T05 --limit K` 的区别：`--limit` 按文件名排序取前 K 张，
本脚本只跑 `--cards` 列出的那些方法，调用量全部落在指定的格上。

批次元数据（批次 id、靶标指纹 `env.adapter_module_sha256`、`env.llm_endpoint`）随证据落盘，
用于判断两次实验是否可比。端点经 `--base-url` 指定时，证据里记 `llm_endpoint.overridden=true`，
该批次不得与走其它端点的批次合并统计。

用法：
    $env:DEEPSEEK_API_KEY='...'          # 凭据只走环境变量
    python tools/run_batch.py --case T03 --n 10 --cards "T03.B-47.confused_deputy_capability_gate"
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))



def main(argv=None) -> int:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(prog="run_batch.py")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--model", default="deepseek-v4-pro")
    ap.add_argument("--base-url", default="https://api.deepseek.com/v1")
    ap.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    ap.add_argument("--cards", required=True, help="逗号分隔的 method_id 列表")
    ap.add_argument("--case", required=True, help="方法类别，如 T03")
    a = ap.parse_args(argv)

    if not os.environ.get(a.api_key_env):
        raise SystemExit("环境变量 %s 未设置（凭据只走环境变量）" % a.api_key_env)

    import harness.adapter_mcp_local as ad
    from harness import runner
    from harness.cli import (condition_env, load_cards, judge_for_factory,
                             observers_for, payload_for_factory, payload_meta_factory)

    want = [x.strip() for x in a.cards.split(",") if x.strip()]
    all_cards = {c.get("method_id"): c for c in load_cards(a.case)}
    missing = [w for w in want if w not in all_cards]
    if missing:
        raise SystemExit("卡不存在：%s" % missing)
    cards = [all_cards[w] for w in want]

    adapter = ad.McpLocalTarget(model=a.model, base_url=a.base_url,
                                api_key_env=a.api_key_env, condition="native")
    print("[run] target=%s cards=%d n=%d model=%s base_url=%s"
          % (adapter.target_id, len(cards), a.n, a.model, a.base_url))
    for c in cards:
        j = c["judge"]
        print("      - %-46s judge=%-16s layer=%-9s" % (c["method_id"], j["verifier"],
                                                        j["evidence_layer"]))
    import hashlib
    _mf = getattr(ad, "__file__", None)
    _sha = None
    if _mf:
        with open(_mf, "rb") as _f:
            _sha = hashlib.sha256(_f.read()).hexdigest()
    env = {"model": a.model, "payload_source": "per_method_spec",
           "driver": "results/README.md",
           # 靶标指纹：靶标文本是**代码的函数**（工具描述进系统提示词、也进权威投影）
           # ⇒ 没有这一栏，跨批不可比（与 harness/cli.py 同规）。
           "adapter_module": (_mf or "").split(chr(92))[-1].split("/")[-1],
           "adapter_module_sha256": _sha,
           "llm_endpoint": {"api_base": a.base_url, "api_key_env": a.api_key_env,
                            "overridden": True}}
    env.update(condition_env(adapter))
    inner = payload_for_factory(a.case, adapter)

    def payload_for(card, plan, trial, arm):
        adapter.bind_card(card)          # 靶标据此决定回读哪个 (entity_id, field)
        return inner(card, plan, trial, arm)

    res = runner.run_matrix(adapter=adapter, cards=cards,
                            judge_for=judge_for_factory(adapter),
                            payload_for=payload_for,
                            # ⚠️ **必须跟着 `--case` 走**（2026-10-05 修）。
                            # 原来写死成 `payload_meta_factory("T05")`：载荷用的是**对的**
                            # 类模块（上一行的 `payload_for` 走 `a.case`），但元数据用 T05 模块
                            # 去解析别的类的卡 ⇒ 回落成兜底值（`carrier="text_only"`、
                            # `scope="generic"`）⇒ 证据里**唯一说明"这一格测的是什么构造"的字段
                            # 是错的。实测被它带偏过一次：据此把 `kb_doc` 载荷误判成兜底探针
                            # （批次 `batch-34473424043d`，见
                            # `results/README.md` §3）。
                            # 属**驱动记账缺陷**，不改任何判据。
                            payload_meta_for=payload_meta_factory(a.case),
                            n=a.n, observers=observers_for(adapter), env=env)
    print("[run] batch_id = %s" % res.batch_id)
    print("[run] 六态（只数方法）= %s" % json.dumps(res.six_state_counts(), ensure_ascii=False))
    for c in res.cells:
        print("  %-46s %-13s v_adv=%-6s v_ctrl=%-6s Adv̂=%-6s n=%s/%s"
              % (c.method_id, c.six_state, c.v_adv, c.v_ctrl, c.adv_hat,
                 c.n_adv, c.n_ctrl))
        for nt in (c.notes or []):
            print("      note:", nt[:160])
    d = ROOT / "runs" / res.batch_id
    print("[run] 产物：%s" % d)
    print("[run] 直读靶场返回（选了哪个工具 / 什么实参）：")
    for mid in want:
        for f in sorted((d / mid).glob("*/trial-*.json")):
            t = json.loads(f.read_text(encoding="utf-8"))
            ch = (t.get("receipts") or [])
            con = next((r for r in ch if r.get("kind") == "mcp_local_construct"), {})
            seq = [c.get("tool") for c in (t.get("tool_calls") or [])]
            print("   %-12s arm=%-11s six=%-12s reason=%-30s seq=%s focal_calls=%s"
                  % (mid.split(".")[1], t.get("arm"), t.get("six_state"),
                     t.get("verdict_reason"), seq, con.get("focal_tool_calls")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
