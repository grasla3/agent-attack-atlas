#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T02 派生脚本生成器 v2：**从卡读取**（不再硬编码 7 条）。

每份脚本：统一 CLI（--grid / --dry-run / --out）、exit code、S1–S5 五条标准自述。
S4：不夹带载荷正文——本类多数方法的"操作"本身就是攻击，脚本只声明结构。
"""
import io, glob, os, sys, yaml
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
D = r"外部组件"
S = os.path.join(D, "scripts")
sys.path.insert(0, D)
from T02 import ENTRY_TOOL, NON_PARAMETRIC  # noqa: E402

TPL = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""{title}

派生脚本 —— 由 methods/T02/T02.py（类模块）+ 本卡参数生成，**不是手写**。
重新生成：python methods/T02/gen_scripts.py

卡：        methods/T02/cards/{stem}.yaml
机制出处：  {mech}（见 docs/domain-and-literature.md）
投放入口：  {vec} -> {tool}
证据层：    {ev}（judge.verifier = {verifier}）
篡改目标：  {goals}
覆盖档位：  {covs}
参数来源：  {psrc}   ← card = 取自卡上/逐方法表；fallback:... = 回退（需人工确认）
不可参数化：{nonparam}

S1 自足：读本文件 + 卡即可实现，不需回查文献。
S2 出处：构造对回卡上 provenance_components（见 plan 的 origin 字段）。
S3 可组合：档位经 --grid 展开，不硬编码。
S4 不夹带载荷正文：本文件不含任何载荷文本；本类多数方法的"操作"本身就是攻击。
S5 接口统一：与其他方法脚本同一套 CLI 与 exit code。

依赖：标准库 + pyyaml。无网络调用（NF2）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from T02 import build_plan, plan_grid, spec_from_card, validate  # noqa: E402

METHOD_ID = "{mid}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description={title!r})
    ap.add_argument("--grid", action="store_true", help="按 tamper_goal × coverage 档位展开（S3）")
    ap.add_argument("--dry-run", action="store_true", default=True, help="只产出计划（本交付形态不要求运行）")
    ap.add_argument("--out", help="把计划写到该路径（默认 stdout）")
    a = ap.parse_args(argv)

    spec = spec_from_card(METHOD_ID)
    errs = validate(spec)
    if errs:
        print("[FAIL] 构造规格不合格：", file=sys.stderr)
        for e in errs:
            print("   - %s" % e, file=sys.stderr)
        return 2

    plans = plan_grid(spec) if a.grid else [build_plan(spec, dry_run=a.dry_run)]
    text = json.dumps(plans if a.grid else plans[0], ensure_ascii=False, indent=1)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print("计划已写出：%s" % a.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

os.makedirs(S, exist_ok=True)
n = 0
for p in sorted(glob.glob(os.path.join(D, "cards", "*.yaml"))):
    stem = os.path.basename(p)[:-5]
    c = yaml.safe_load(open(p, encoding="utf-8"))
    mid = c["method_id"]
    vec = c["provenance_components"]["vector"]; vec = vec["ref"] if isinstance(vec, dict) else vec
    ex = c.get("execution") or {}
    goals = [d.split(":", 1)[1] for d in (c.get("dimensions") or []) if isinstance(d, str) and d.startswith("tamper_goal:")]
    txt = TPL.format(
        title=c["title"], stem=stem, mech=c["mechanism_ref"], vec=vec,
        tool=ENTRY_TOOL.get(vec, "log_ingest"), ev=c["judge"]["evidence_layer"],
        verifier=c["judge"]["verifier"], goals=goals or "（由类模块逐方法表给出）",
        covs="（由类模块 COVERAGE_GRID 给出）",
        psrc=("card" if goals else "由 T02.GOAL_GRID / TAMPER_OBJECT 给出"),
        nonparam=("是（见 T02.NON_PARAMETRIC）" if mid in NON_PARAMETRIC else "否（纯参数化）"),
        mid=mid,
    )
    open(os.path.join(S, stem + ".py"), "w", encoding="utf-8", newline="\n").write(txt)
    n += 1
    print("  写出 scripts/%-58s %s" % (stem + ".py", c["mechanism_ref"]))
print("\n共 %d 份派生脚本" % n)