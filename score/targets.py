# -*- coding: utf-8 -*-
"""目标能力对齐（`score/targets.py`）：把画像的**工具清单**展开成卡的 `required_actions` 词表。

## 解决什么问题

`required_actions` **没有受控词表**（全库 152 个动作名、141 个单类独有，
见 `targets/README.md` §3.1）。实测：这 152 个名字里**只有 3 个**与 AgentDojo 的工具名
逐字相同 ⇒ 只按字符串比对，"适用性"取决于**巧合**，加多少份画像都救不了。

`targets/capability-aliases.yaml` 把目标**确有**的机制能力（带源码证据）接到卡的词表上，
本模块负责读取与展开。

## ⚠️ 两条必须同报的口径差异

1. **本模块的展开口径 ≠ `tools/cardcheck.py` 规则 17 的纯字符串口径**：
   规则 17 不认别名。报告里**两个覆盖率必须并列**，不得只报大的那个。
2. **"结构上可行" ≠ "我们投得进去"**：别名只回答 V6 那一问（方法与目标是否相配）。
   投放面与观测装置是**另一回事**——投失败记 `untested`、装置不足记 `not_applicable`
   （`docs/README.md` **D17**）。故 `score/prior.py` 的适用性与 runner 的阶段 3b
   可以不一致，对账只在**两边都有**的格上做。

## 为什么放在 `score/`

`harness/runner.py` 已经依赖 `score/core.py`；若把本模块放进 `harness/`，
`score/prior.py` 就要反向 import `harness` → **成环**。放这里，两边都能用，且不成环。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
ALIASES_PATH = ROOT / "targets" / "capability-aliases.yaml"

_CACHE: Dict[str, Any] = {}


def load_aliases(path: Optional[Path] = None) -> Dict[str, Any]:
    """读对齐表（带缓存）。文件不存在 ⇒ 返回空表（**不报错**：对齐是可选增强）。"""
    key = str(path or ALIASES_PATH)
    if key not in _CACHE:
        p = Path(key)
        if not p.exists():
            _CACHE[key] = {"version": None, "targets": {}}
        else:
            import yaml
            _CACHE[key] = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return _CACHE[key]


def alias_map(target_id: str, aliases: Optional[Dict[str, Any]] = None
              ) -> Dict[str, Dict[str, Any]]:
    """`动作名 -> {capability, source, reason}`。供审计与报告引用。"""
    a = aliases if aliases is not None else load_aliases()
    tgt = (a.get("targets") or {}).get(target_id) or {}
    out: Dict[str, Dict[str, Any]] = {}
    for cap in tgt.get("capabilities") or []:
        for act in cap.get("actions") or []:
            out[str(act)] = {"capability": cap.get("id"),
                             "source": cap.get("source"),
                             "reason": cap.get("reason")}
    return out


def excluded_actions(target_id: str, aliases: Optional[Dict[str, Any]] = None
                     ) -> Dict[str, str]:
    """`动作名 -> 排除理由`。**不写排除项等于默认全都通**，故这一份也提供给报告。"""
    a = aliases if aliases is not None else load_aliases()
    tgt = (a.get("targets") or {}).get(target_id) or {}
    out: Dict[str, str] = {}
    for row in tgt.get("excluded") or []:
        for act in row.get("actions") or []:
            out[str(act)] = "%s：%s" % (row.get("family"), row.get("reason"))
    return out


def expand_tools(profile: Dict[str, Any], target_id: Optional[str] = None,
                 aliases: Optional[Dict[str, Any]] = None
                 ) -> Tuple[Set[str], Dict[str, Any]]:
    """画像能承载的动作集合（**直接命中 ∪ 有据别名**），外加一份展开说明。

    返回 `(actions, detail)`；`detail` 里分开列出"逐字命中"与"经别名"，
    报告要能看出覆盖里有多少来自别名——**那是本表引入的口径，必须可见**。
    """
    tid = target_id or str(profile.get("target_id") or "")
    raw = {str(x) for x in (profile.get("tools") or [])}
    amap = alias_map(tid, aliases)
    aliased = {a for a in amap if a not in raw}
    return raw | aliased, {
        "target_id": tid,
        "raw_tools": len(raw),
        "direct": sorted(raw),
        "aliased": sorted(aliased),
        "aliased_count": len(aliased),
        "alias_version": (aliases if aliases is not None else load_aliases()).get("version"),
        "excluded": excluded_actions(tid, aliases),
    }


def load_profile(target_id: str, targets_dir: Optional[Path] = None) -> Dict[str, Any]:
    d = targets_dir or (ROOT / "targets")
    return json.loads((d / ("%s.json" % target_id)).read_text(encoding="utf-8"))


def flatten_text(value: Any) -> List[str]:
    """把对齐表里的动作字段（可能是嵌套 list）摊平。留作工具函数给报告用。"""
    out: List[str] = []
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, Iterable):
        for v in value:
            out.extend(flatten_text(v))
    return out
