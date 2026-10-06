#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快照工具：在动手改之前留一个可回退的点。

用法:
    python tools/snapshot.py                 打快照并打 tag
    python tools/snapshot.py --label before-t01-cards
    python tools/snapshot.py --list          列出全部快照
    python tools/snapshot.py --diff <tag>    与某快照比对文件清单差异

为什么需要：本项目大量产物是规范与数据，改错一次可能波及几十个文件。
git 能回退，但前提是你知道「回退到哪个点」。快照就是那些点。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TAG_PREFIX = "snap"
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "_archive", "runs",
             "node_modules", ".pytest_cache"}
GENERATED = {"gate-manifest.json", "gate-report.json"}


def run(args, check=True):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError("命令失败: %s\n%s\n%s" % (" ".join(args), r.stdout, r.stderr))
    return r


def git(*args, check=True):
    return run(["git", *args], check=check)


def is_repo():
    return run(["git", "rev-parse", "--git-dir"], check=False).returncode == 0


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect():
    files = {}
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        if p.name in GENERATED:
            continue
        files[str(p.relative_to(ROOT)).replace("\\", "/")] = sha256(p)
    return files


def cmd_snapshot(label):
    if not is_repo():
        print("不是 git 仓库；请先 git init", file=sys.stderr)
        return 2

    files = collect()
    dirty = git("status", "--porcelain", check=False).stdout.strip()

    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", label).strip("-") if label else "auto"
    tag = "%s-%s-%s" % (TAG_PREFIX, ts, safe)

    # 先落盘清单，保证快照可独立校验
    payload = {
        "tag": tag,
        "label": label or "",
        "created_at": _dt.datetime.now().astimezone().isoformat(),
        "file_count": len(files),
        "dirty": bool(dirty),
        "files": files,
    }
    (ROOT / "gate-manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")

    # 提交（若脏）并打 tag
    if dirty:
        git("add", "-A")
        git("commit", "-m", "chore(snapshot): %s" % (label or "auto"), "--no-verify")
    head = git("rev-parse", "HEAD").stdout.strip()
    git("tag", "-a", tag, "-m", "snapshot: %s" % (label or "auto"))

    print("快照已建立")
    print("  tag         %s" % tag)
    print("  commit      %s" % head[:12])
    print("  文件数      %d" % len(files))
    print("  脏工作区    %s" % ("是（已一并提交）" if dirty else "否"))
    print()
    print("回退到本快照:")
    print("  git reset --hard %s" % tag)
    return 0


def cmd_list():
    if not is_repo():
        print("不是 git 仓库", file=sys.stderr)
        return 2
    out = git("tag", "-l", "%s-*" % TAG_PREFIX, "--sort=-creatordate").stdout.strip()
    if not out:
        print("还没有快照")
        return 0
    for line in out.splitlines():
        subj = git("tag", "-l", "--format=%(contents:subject)", line).stdout.strip()
        date = git("log", "-1", "--format=%ci", line, check=False).stdout.strip()
        print("%-44s %s  %s" % (line, date[:19], subj))
    return 0


def cmd_diff(tag):
    """与某个快照比对。

    历史 bug（已修）：本函数原先只读 `<tag>:gate-manifest.json`，但该文件被
    `.gitignore` 忽略，**任何 tag 里都没有它** —— 于是 `--diff` 永远返回
    1「快照内没有 gate-manifest.json」，回退工具形同虚设。

    修法：以 **git 树**为准做比对（`git diff --name-status <tag> HEAD`），
    再单独报告工作区未提交的改动。若该 tag 恰好带了清单，则额外做一次内容哈希核对。
    """
    if not is_repo():
        print("不是 git 仓库", file=sys.stderr)
        return 2

    if git("rev-parse", "--verify", "%s^{commit}" % tag, check=False).returncode != 0:
        print("快照/标签 %s 不存在。用 --list 查看可用快照。" % tag, file=sys.stderr)
        return 1

    # (1) 与当前 HEAD 的**已提交**差异
    r = git("diff", "--name-status", tag, "HEAD", check=False)
    if r.returncode != 0:
        print("无法比对 %s：%s" % (tag, r.stderr.strip()), file=sys.stderr)
        return 1

    buckets = {"A": [], "D": [], "M": []}
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code, path = parts[0][0], parts[-1]
        buckets["A" if code == "A" else "D" if code == "D" else "M"].append(path)

    print("与 %s 比对（已提交部分，tag -> HEAD）：" % tag)
    for label, key in (("新增", "A"), ("删除", "D"), ("变更", "M")):
        items = sorted(buckets[key])
        print("  %s %d" % (label, len(items)))
        for k in items[:30]:
            print("    %s %s" % ({"A": "+", "D": "-", "M": "~"}[key], k))
        if len(items) > 30:
            print("    ...（另有 %d 项）" % (len(items) - 30))

    # (2) 工作区未提交的改动（回退前必须知道这些会不会丢）
    dirty = [ln for ln in git("status", "--porcelain", check=False).stdout.splitlines() if ln.strip()]
    print("  工作区未提交 %d 项" % len(dirty))
    for ln in dirty[:30]:
        print("    %s" % ln)
    if len(dirty) > 30:
        print("    ...（另有 %d 项）" % (len(dirty) - 30))

    # (3) 若该 tag 恰好带了清单，做一次内容哈希核对（锦上添花，不依赖它）
    m = git("show", "%s:gate-manifest.json" % tag, check=False)
    if m.returncode == 0:
        try:
            prev = json.loads(m.stdout).get("files", {})
        except Exception:
            prev = {}
        if prev:
            cur = collect()
            changed = sorted(k for k in set(cur) & set(prev) if cur[k] != prev[k])
            print("  附带清单核对：交集 %d 项，哈希不一致 %d 项"
                  % (len(set(cur) & set(prev)), len(changed)))

    print()
    print("回退到该快照（丢弃工作区改动）:  git reset --hard %s" % tag)
    print("只回退提交、保留改动:             git reset --soft %s" % tag)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="快照工具")
    ap.add_argument("--label", default=None, help="快照标签，如 before-t01-cards")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--diff", default=None, metavar="TAG")
    a = ap.parse_args(argv)
    if a.list:
        return cmd_list()
    if a.diff:
        return cmd_diff(a.diff)
    return cmd_snapshot(a.label)


if __name__ == "__main__":
    sys.exit(main())