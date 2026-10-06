#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把全库文本文件统一为 LF 行尾（`.gitattributes` 已声明 `* text=auto eol=lf`）。

动因：Windows 上 `open(..., "w")` 默认把 `\n` 翻成 `\r\n`，而 Gate 0 的 `line_endings`
要求全库 LF。实测已被 T01/T02/T03/T05/T08 各撞过一次，**每次都会让整仓库无法提交**。

**本工具是并行作业规程 §2 P6 指定的收尾命令。**

原实现只硬编码了某一个会话自己的 18 个文件，换个会话就没用（实测：库里 42 个文件待修，
它报 0）。现改为全库遍历。

用法:
    python tools/normalize_lf.py            # 归一
    python tools/normalize_lf.py --dry-run  # 只报告，不改
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "_archive", "runs",
             "node_modules", ".pytest_cache"}
SUFFIXES = {".py", ".yaml", ".yml", ".json", ".cfg", ".toml", ".sh", ".ps1", ".cmd",
            ".md", ".txt", ".rst", ".svg", ".log", ".gitattributes", ".gitignore",
            ".editorconfig"}
#: 检索会话的临时产物与全文缓存：已被 .gitignore 排除，不必归一
SCRATCH = ("_", ".pdfcache", ".venuecache")


def _is_scratch(parts) -> bool:
    parts = list(parts)
    if len(parts) >= 2 and parts[0] == "docs" and parts[1] == "results/README.md":
        return any(x.startswith(SCRATCH) for x in parts[2:])
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="全库 LF 行尾归一")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    hit, total_crlf = [], 0
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in SUFFIXES:
            continue
        parts = p.relative_to(ROOT).parts
        if any(x in SKIP_DIRS for x in parts) or _is_scratch(parts):
            continue
        raw = p.read_bytes()
        if b"\r\n" not in raw:
            continue
        n = raw.count(b"\r\n")
        hit.append((str(p.relative_to(ROOT)).replace("\\", "/"), n))
        total_crlf += n
        if not a.dry_run:
            p.write_bytes(raw.replace(b"\r\n", b"\n"))

    for name, n in hit[:40]:
        print("  %-56s %5d 处 CRLF -> LF" % (name, n))
    if len(hit) > 40:
        print("  …（另有 %d 个文件）" % (len(hit) - 40))
    print("%s：%d 个文件 / %d 处" % ("待修" if a.dry_run else "已归一", len(hit), total_crlf))
    return 0


if __name__ == "__main__":
    sys.exit(main())