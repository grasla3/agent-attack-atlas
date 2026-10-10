# -*- coding: utf-8 -*-
"""证据包校验：重算 SHA-256 并与 manifest 对账；不一致即失败（退出码 1）。

用法：
    python tools/verify_evidence.py --manifest evidence/manifest.json --root evidence [--summary <path>]

CI 中由 .github/workflows/verify-evidence.yml 调用：对账结果写入 job summary，
证据包作为 artifact 上传（artifact 摘要由平台计算）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="evidence/manifest.json")
    ap.add_argument("--root", default="evidence")
    ap.add_argument("--summary", default=None, help="把 Markdown 对账表追加写入该文件（CI 的 job summary）")
    args = ap.parse_args()

    root = Path(args.root)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    files = manifest.get("files") or []
    if not files:
        print("manifest 中没有 files 条目")
        return 1

    rows, bad = [], 0
    for entry in files:
        rel = entry["file"]
        p = root / rel
        if not p.exists():
            rows.append((rel, entry.get("bytes"), "缺失", "FAIL"))
            bad += 1
            continue
        size_ok = p.stat().st_size == entry.get("bytes")
        digest = sha256(p)
        hash_ok = digest == entry.get("sha256")
        ok = size_ok and hash_ok
        bad += 0 if ok else 1
        rows.append((rel, p.stat().st_size, digest[:16], "OK" if ok else "FAIL"))

    width = max(len(r[0]) for r in rows)
    lines = ["%-*s %10s %18s %6s" % (width, "file", "bytes", "sha256[:16]", "check"),
             "-" * (width + 38)]
    lines += ["%-*s %10s %18s %6s" % (width, r[0], r[1], r[2], r[3]) for r in rows]
    s = manifest.get("summary") or {}
    lines += ["", "文件 %d 个；文献源 %s 个 / %s 轮 / %s 个检索式；仓库取向 %s 组；代码级检索 %s 式"
              % (len(rows), s.get("literature_sources"), s.get("literature_rounds"),
                 s.get("literature_queries"), s.get("repository_orientations"),
                 s.get("code_search_queries")),
              "检索窗口：%s" % s.get("run_window"),
              "对账结果：%s" % ("全部一致（%d/%d）" % (len(rows), len(rows)) if bad == 0 else "%d 处不一致" % bad)]
    print("\n".join(lines))

    if args.summary:
        md = ["## 检索证据包哈希对账", "", "| 文件 | 字节 | SHA-256（前 16 位） | 判定 |", "|---|---:|---|---|"]
        md += ["| `%s` | %s | `%s` | %s |" % (r[0], r[1], r[2], r[3]) for r in rows]
        md += ["", "**结论：%s**" % ("全部一致（%d/%d）" % (len(rows), len(rows)) if bad == 0 else "%d 处不一致" % bad),
               "", "检索窗口：%s" % s.get("run_window"),
               "", "对账基准：`%s`（manifest 随证据包一同提交，任一文件被改动都会在此失败）" % args.manifest, ""]
        with open(args.summary, "a", encoding="utf-8") as fh:
            fh.write("\n".join(md))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())