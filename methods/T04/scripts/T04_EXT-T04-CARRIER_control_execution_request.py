#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T04 派生脚本 · T04.EXT-T04-CARRIER.control_execution_request

本文件由类模块 methods/T04/T04.py + 卡上参数**确定性派生**：同参数生成同一份。
它不手写任何构造逻辑 —— 构造逻辑只有一份，在类模块里。

来源：本项目自建（EXT），见卡
methods/T04/cards/T04_EXT-T04-CARRIER_control_execution_request.yaml。
本脚本**不携带任何载荷正文**（S4 / 禁令 9）：只声明投放规格与判据面。

用法:
    python T04_EXT-T04-CARRIER_control_execution_request.py --plan
"""
import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import T04  # noqa: E402  （类模块）

METHOD_ID = "T04.EXT-T04-CARRIER.control_execution_request"

#: 本方法的参数（与卡上 execution.args 一致）
PARAMS = {
    "entry_point": "任务上下文",
    "target_surface": "control_interface_now",
    "control_tool": "execute_manipulation",
    "artifact_kind": "动作指令",
    "placement": "task_context",
    "granularity": "单次控制调用",
    "budget_grid": [1],
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true", help="输出执行计划（不执行）")
    a = ap.parse_args(argv)
    print(json.dumps({"method_id": METHOD_ID, "params": PARAMS,
                      "note": "构造规格由类模块持有；本脚本只声明参数（S4：不夹带载荷正文）"},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
