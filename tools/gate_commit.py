#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""带门禁的提交包装器。

存在的理由：Git 钩子在 Windows 上必然经过 MSYS 的 sh，而某些受限环境
（含 DSH 沙箱）无法启动 sh —— 钩子根本不会执行。本包装器把门禁
从「钩子」搬到「命令」，因此**在任何环境下都强制生效**。

用法:
    python tools/gate_commit.py -m "feat(methods): 新增 T01 的 12 张卡"
    python tools/gate_commit.py -m "..." --gate all
    python tools/gate_commit.py -m "..." --skip-gate      # 仅紧急，且会留痕

行为:
    1. 跑门禁；未通过则**不提交**
    2. 通过则 git add -A 并提交（带 --no-verify，避免钩子在能跑的环境里跑第二遍）
    3. 提交后打印本次提交的内容摘要，便于回退时定位
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent


def run(args, check=False):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError("命令失败: %s\n%s\n%s" % (" ".join(args), r.stdout, r.stderr))
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description="带门禁的提交包装器")
    ap.add_argument("-m", "--message", required=True)
    ap.add_argument("--gate", default="0", choices=["0", "1", "2", "all"])
    ap.add_argument("--skip-gate", action="store_true")
    a = ap.parse_args(argv)

    if not a.skip_gate:
        print("=" * 68)
        print("[gate_commit] 先跑门禁（Gate %s）" % a.gate)
        print("=" * 68)
        r = run([sys.executable, "tools/gates.py", "--gate", a.gate])
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        if r.returncode != 0:
            print()
            print("=" * 68)
            print("[gate_commit] 门禁未通过，**未提交**。")
            print("             先修问题，或确认是误报后用豁免标记。")
            print("             详见 docs/rollback.md §4「门禁自己挂了怎么办」。")
            print("             仅紧急可用： --skip-gate （会在提交信息里留痕）")
            print("=" * 68)
            return 1
        print("[gate_commit] 门禁通过")
    else:
        a.message = a.message + "\n\n[gate-skipped] 本次提交绕过了门禁（--skip-gate）"
        print("[gate_commit] ⚠️ 已绕过门禁，提交信息中已留痕")

    run(["git", "add", "-A"], check=True)
    n_staged = len(run(["git", "diff", "--cached", "--name-only"], check=True).stdout.strip().splitlines())
    if n_staged == 0:
        print("[gate_commit] 没有暂存内容，未提交")
        return 0

    r = run(["git", "commit", "--no-verify", "-m", a.message])
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        return r.returncode

    head = run(["git", "rev-parse", "--short", "HEAD"], check=True).stdout.strip()
    files = run(["git", "show", "--stat", "--oneline", "HEAD"], check=True).stdout
    print()
    print("[gate_commit] 已提交 %s，共 %d 个文件" % (head, n_staged))
    print("[gate_commit] 回退本次提交： git reset --hard HEAD~1")
    print("[gate_commit]              git reset --soft HEAD~1  （保留改动）")
    return 0


if __name__ == "__main__":
    sys.exit(main())