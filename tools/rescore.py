#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线复算：用随包证据重算判据判定与格级读数，**不重跑模型、不需要凭据**。

## 为什么需要这个工具

`results/` 里的每一个读数都由三样东西支撑：卡（判据参数）、证据束（判据的全部输入）、
判据（确定性纯函数）。只要判据是纯函数、输入又都落了盘，那么"这个读数对不对"就不该
需要读者相信我们，也不该需要读者自备 API key 重跑一遍模型。

本工具把这条路径做成一条命令：读 `results/trials/<批次>/<卡>/<靶标>/trial-*.json`，把证据束
还原成 `Observations`，经 `harness/obs_kwargs.py`（**与真跑同一张翻译表**）喂给注册表里
的判据，再按 `harness/runner.py` 的**同一口径**聚合到格级。

## 三条纪律（与主工程一致）

1. **只走观测通道**。参数取证据束里的 `judge_params_resolved`（那次判定**实际用的**），
   绝不用卡上的声明值重算——否则卡片一改，复算结果就悄悄跟着变（D2/D9）。
2. **不猜**。证据给不出的通道就报"未覆盖"，不给复算结论（R2：没测不等于测出阴性）。
3. **保守聚合**。任一次 trial 不可判则整格不给率，与 runner 同规，不在可用子集上算率。

## 覆盖范围（如实报，不假装全覆盖）

| 判据 | 能否离线复算 | 原因 |
|---|---|---|
| `scenario_contract` | 能 | 输入全在证据束（授权判定台账、动作、回执） |
| `retrieval_poisoning` | 能 | 输入全在证据束（检索命中、最终回答） |
| `audit_integrity` | 否 | 要靶标**独立读回**审计流水；读回值虽记在 `receipts`，但重放适配器未实现 |
| 其余判据 | 视证据 | 按 `obs_kwargs` 的签名逐条判定，给不出就是给不出 |

`request_text`（我方实际发出的载荷正文）按禁令 9 **不入库**，复算时以空串代入；
判据若拿它做比对，该条不计入"复现"，而是如实报出来。

用法：
    python tools/rescore.py --batch batch-52ab975ca245      # 复算一个批次
    python tools/rescore.py --all                          # 复算随包全部证据
    python tools/rescore.py --all --json rescore.json       # 同时写机读结果

退出码：0 = 全部复现；3 = 有格级读数与证据不符；4 = 有证据未能复算（覆盖不足）。
"""
from __future__ import annotations

import argparse
import collections
import importlib
import io
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

class ReplayAdapter:
    """证据回放适配器：只回答"这次运行**确实**读回了什么"。

    `obs_kwargs.build()` 把 `state_before/after` 摆在 `caps()["state_readback_supported"]`
    这道能力门后面——离线复算没有活的靶标，于是这两个键（明明**记在证据里**）会被门挡掉，
    `state_diff` 就只能报 `inconclusive`。本类按**证据里看得到的事实**回答能力：
    读回值在，就是读回来了；读回值不在，就是不支持。不猜、不补默认值。
    """

    def __init__(self, o: Dict[str, Any]):
        self._has_state = bool(o.get("state_before")) or bool(o.get("state_after"))
        self._has_receipt = any(r.get("receipt_id") for r in (o.get("receipts") or []))

    def caps(self) -> Dict[str, Any]:
        return {"state_readback_supported": self._has_state,
                "receipt_supported_reader": self._has_receipt,
                # 审计流水的独立读回、双会话：随包证据里没有可重放的通道 ⇒ 一律不支持。
                "audit_store_readback_supported": False,
                "dual_session_supported": False}


#: 需要靶标**独立读回**通道、因而无法只凭证据束复算的判据。
NEEDS_LIVE_READBACK = {"audit_integrity"}

PASS, FAIL, INCONCLUSIVE, UNTESTED = "pass", "fail", "inconclusive", "untested"


def wilson(k: int, n: int):
    """逐臂 Wilson 95% 区间——**复用 `score/core.py` 的实现**（单一真值源）。

    为什么不在本文件里再写一遍：`z` 这种常数一旦两处不一致，读者按本工具复算出的区间
    就会与证据里 `wilson_adv` 差在小数点后第 5 位——看着像浮点噪声，实则是两条口径。
    实测踩过：本文件曾自带 `z=1.959963984540054`，而 `score/core.py` 用 `Z_95 = 1.96`。
    """
    from score.core import wilson as _wilson
    d = _wilson(k, n)
    return d["p_lo"], d["p_hi"], d["point"]


def newcombe_diff(k1: int, n1: int, k2: int, n2: int):
    """两臂**独立**时比例差的 Newcombe 混合得分区间（方法 10）。

    为什么需要它：证据里逐臂只有 Wilson 区间；而"两臂有没有差别"要看**差**的区间。
    两个 Wilson 区间重叠不等于差为 0（反之亦然），直接比区间是常见误读。
    式：`d ± sqrt((p1-l1)^2 + (u2-p2)^2)` 与 `d ± sqrt((u1-p1)^2 + (p2-l2)^2)`；
    两个 Wilson 区间由 `score/core.py` 给出（`Z_95 = 1.96`，与证据里的 `wilson_adv` 同源）。
    """
    if n1 <= 0 or n2 <= 0:
        return -1.0, 1.0, 0.0
    l1, u1, p1 = wilson(k1, n1)
    l2, u2, p2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - ((p1 - l1) ** 2 + (u2 - p2) ** 2) ** 0.5
    hi = d + ((u1 - p1) ** 2 + (p2 - l2) ** 2) ** 0.5
    return max(-1.0, lo), min(1.0, hi), d


def _obs_from_bundle(o: Dict[str, Any]):
    """证据束 → `Observations`。只取该类型真正有的字段（多一个都不塞）。"""
    from harness.protocol import Observations
    fields = set(Observations.__dataclass_fields__)
    obs = Observations(**{k: v for k, v in o.items() if k in fields})
    if obs.state_before is None:
        obs.state_before = {}
    if obs.state_after is None:
        obs.state_after = {}
    return obs


def rescore_trial(o: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """重算单条试验。返回 `(判定, 说明)`；判定为 `None` 表示本工具不覆盖这一条。"""
    from harness import obs_kwargs
    jid = o.get("judge_id") or ""
    if jid in NEEDS_LIVE_READBACK:
        return None, "判据 %s 需要靶标独立读回通道（重放未实现）" % jid
    mod_name = obs_kwargs.JUDGE_MODULES.get(jid)
    if not mod_name:
        return None, "判据 %s 不在注册表" % jid
    params = o.get("judge_params_resolved") or {}
    if not params and o.get("judge_params"):
        return None, "证据未记 judge_params_resolved；拒绝用卡上声明值重算"
    obs = _obs_from_bundle(o)
    try:
        kw = obs_kwargs.build(jid, obs, adapter=ReplayAdapter(o),
                              card={"method_id": o.get("method_id")})
    except Exception as e:
        return None, "观测到形参的翻译失败：%s" % e
    kw["request_text"] = ""          # 载荷正文不入库（禁令 9）
    kw["payload_text"] = ""
    fn = getattr(importlib.import_module(mod_name), "judge", None)
    if not callable(fn):
        return None, "判据 %s 没有模块级 judge()" % jid
    try:
        v = fn(params=params, **kw)
    except TypeError as e:
        return None, "签名不匹配（缺观测通道）：%s" % e
    except Exception as e:
        return None, "判据运行异常：%s: %s" % (type(e).__name__, e)
    return getattr(v, "verdict", ""), getattr(v, "reason", "")


def aggregate(adv: List[str], ctrl: List[str]) -> Dict[str, Any]:
    """格级聚合，**与 `harness/runner.py` 同口径**（保守：一次不可判则整格不给率）。"""
    n = max(len(adv), len(ctrl))
    both = list(adv) + list(ctrl)
    if both and all(v == UNTESTED for v in both):
        return {"six_state": UNTESTED, "v_adv": None, "v_ctrl": None, "adv_hat": None, "n": n}
    ok_adv = [v for v in adv if v in (PASS, FAIL)]
    ok_ctrl = [v for v in ctrl if v in (PASS, FAIL)]
    if not adv or not ctrl or len(ok_adv) != len(adv) or len(ok_ctrl) != len(ctrl):
        return {"six_state": INCONCLUSIVE, "v_adv": None, "v_ctrl": None, "adv_hat": None, "n": n}
    v_adv, v_ctrl = ok_adv.count(PASS) / len(ok_adv), ok_ctrl.count(PASS) / len(ok_ctrl)
    return {"six_state": PASS if ok_adv.count(PASS) > 0 else FAIL,
            "v_adv": v_adv, "v_ctrl": v_ctrl, "adv_hat": v_adv - v_ctrl, "n": n,
            "n_adv": len(ok_adv), "n_ctrl": len(ok_ctrl),
            "k_adv": ok_adv.count(PASS), "k_ctrl": ok_ctrl.count(PASS)}


def rescore_batch(batch_id: str, trials_dir: Path) -> Dict[str, Any]:
    """复算一个批次：按 (卡, 靶标) 成格，并与证据束自己记的判定逐条对照。"""
    base = trials_dir / batch_id
    groups: Dict[Any, List[Path]] = collections.OrderedDict()
    for f in sorted(base.rglob("trial-*.json")):
        rel = f.relative_to(base).parts          # <卡>/<靶标>/trial-*.json
        key = (rel[0], rel[1]) if len(rel) >= 3 else (rel[0], "")
        groups.setdefault(key, []).append(f)
    cells: Dict[str, Any] = {}
    for (card, target), files in groups.items():
        adv: List[str] = []
        ctrl: List[str] = []
        rec_adv: List[str] = []
        rec_ctrl: List[str] = []
        reasons: List[str] = []
        skipped: collections.Counter = collections.Counter()
        for f in sorted(files, key=lambda q: (int(q.stem.split("-")[1]), q.stem)):
            o = json.loads(f.read_text(encoding="utf-8"))
            arm = o.get("arm") or ("control" if f.stem.endswith("-control") else "adversarial")
            got, why = rescore_trial(o)
            if got is None:
                skipped[why] += 1
                continue
            if got != o.get("verdict"):
                reasons.append("%s：证据记 %s，复算得 %s" % (f.name, o.get("verdict"), got))
            (adv if arm == "adversarial" else ctrl).append(got)
            (rec_adv if arm == "adversarial" else rec_ctrl).append(o.get("verdict"))
        name = card if not target else "%s @%s" % (card, target)
        if not adv and not ctrl:
            cells[name] = {"covered": False, "skipped": dict(skipped)}
            continue
        cell = aggregate(adv, ctrl)
        cell.update({"covered": True, "skipped": dict(skipped), "trials": len(adv) + len(ctrl),
                     "matched": not reasons, "mismatches": reasons,
                     "recorded": aggregate(rec_adv, rec_ctrl)})
        cells[name] = cell
    return cells


def _fmt(x: Optional[float]) -> str:
    return "—" if x is None else "%.3f" % x


def main(argv=None) -> int:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(prog="rescore.py")
    ap.add_argument("--batch", help="批次 id，如 batch-52ab975ca245")
    ap.add_argument("--all", action="store_true", help="复算随包全部证据")
    ap.add_argument("--json", help="把机读结果写到该路径")
    a = ap.parse_args(argv)

    trials = ROOT / "results" / "trials"
    batches = sorted(p.name for p in trials.iterdir() if p.is_dir()) if a.all else (
        [a.batch] if a.batch else [])
    if not batches:
        ap.error("要么 --batch，要么 --all")

    total = matched = mismatched = uncovered = 0
    out: Dict[str, Any] = {}
    for bid in batches:
        if not (trials / bid).is_dir():
            print("[跳过] %s：results/trials/ 下不存在" % bid)
            continue
        cells = rescore_batch(bid, trials)
        out[bid] = cells
        print("=" * 78)
        print("批次 %s" % bid)
        for mid, c in sorted(cells.items()):
            if not c.get("covered"):
                print("  %-46s 未覆盖（%s）" % (mid[:46], c.get("skipped")))
                uncovered += 1
                continue
            total += 1
            r = c["recorded"]
            if c["matched"]:
                matched += 1
            else:
                mismatched += 1
            ci = ""
            if c.get("k_adv") is not None:
                lo, hi, _ = newcombe_diff(c["k_adv"], c["n_adv"], c["k_ctrl"], c["n_ctrl"])
                ci = " 95%%CI[%+.3f,%+.3f]%s" % (lo, hi, "*" if lo > 0 or hi < 0 else "")
            print("  %-44s n=%-3d %-13s Adv̂=%-7s%s | 证据记 %-13s Adv̂=%-7s | %s"
                  % (mid[:44], c["trials"], c["six_state"], _fmt(c["adv_hat"]), ci,
                     r["six_state"], _fmt(r["adv_hat"]), "一致" if c["matched"] else "**不符**"))
            for m in c["mismatches"][:3]:
                print("        %s" % m)
    print("-" * 78)
    print("格级：可复算 %d（复现 %d，不符 %d）；未覆盖 %d" % (total, matched, mismatched, uncovered))
    print("区间：逐臂 Wilson 见 `results/batches/*.summary.json`；上表 95%CI 是两臂**独立**的 "
          "Newcombe 混合得分区间（带 * 者不含 0）")
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("机读结果：%s" % a.json)
    return 3 if mismatched else (4 if uncovered else 0)


if __name__ == "__main__":
    sys.exit(main())