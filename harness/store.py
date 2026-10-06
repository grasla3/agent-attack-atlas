# -*- coding: utf-8 -*-
"""`runs/` 落盘。依据 `docs/README.md` **D1**：文件为真相源，不建 SQLite 索引。

目录约定（`docs/runner-design.md` §6）：
    runs/<batch_id>/batch.json
    runs/<batch_id>/<method_id>/<target_id>/trial-<i>.json
    runs/<batch_id>/summary.json

**为什么单 trial 必须自足**：汇总不可复算。本项目已吃过一次亏——
「聚合掩盖维度」（`docs/judgment-discipline.md` §5.2 的 M1–M5）。
只存汇总就是那件事在存储层的重演。
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe(s: str) -> str:
    """路径安全化。`method_id` 含点号（`T06.LIT-B-105.foo`）故保留点。"""
    return _SAFE.sub("_", str(s))


def new_batch_id(prefix: str = "batch") -> str:
    return "%s-%s" % (prefix, uuid.uuid4().hex[:12])


def batch_dir(batch_id: str, runs_dir: Path | None = None) -> Path:
    return (runs_dir or (ROOT / "runs")) / _safe(batch_id)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_batch(batch_id: str, meta: Dict[str, Any], runs_dir: Path | None = None) -> Path:
    p = batch_dir(batch_id, runs_dir) / "batch.json"
    write_json(p, meta)
    return p


def save_trial(batch_id: str, method_id: str, target_id: str, index: int,
               payload: Dict[str, Any], runs_dir: Path | None = None,
               arm: str = "adversarial") -> Path:
    """落一次 trial。`arm` 决定文件名后缀——**两臂各存各的**，
    配对关系靠 `(index, arm)` 复原，不靠汇总。"""
    suffix = "" if arm == "adversarial" else "-%s" % _safe(arm)
    p = (batch_dir(batch_id, runs_dir) / _safe(method_id) / _safe(target_id)
         / ("trial-%d%s.json" % (index, suffix)))
    write_json(p, payload)
    return p


def save_summary(batch_id: str, summary: Dict[str, Any], runs_dir: Path | None = None) -> Path:
    p = batch_dir(batch_id, runs_dir) / "summary.json"
    write_json(p, summary)
    return p


def load_trials(batch_id: str, runs_dir: Path | None = None) -> List[Dict[str, Any]]:
    """回读一个批次的全部 trial。用于**复算**——这是 D1 要求的能力。"""
    base = batch_dir(batch_id, runs_dir)
    if not base.exists():
        raise FileNotFoundError("批次不存在：%s" % base)
    return [read_json(p) for p in sorted(base.rglob("trial-*.json"))]