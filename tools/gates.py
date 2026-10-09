#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git 质量阀门（Gate 0/1/2 的统一入口）。

纯标准库实现，遵循 docs/README.md B4（不引入 numpy/scipy）。

用法:
    python tools/gates.py --list
    python tools/gates.py --gate 0
    python tools/gates.py --gate all
    python tools/gates.py --check dod_count
    python tools/gates.py --json

退出码（docs/README.md D6）:
    0  通过
    1  校验失败（schema / 规则 / 计数不一致）
    2  用法错误
    3  门禁未过（前提未满足 / 判据回归不足 / 正控失败）
    4  离线违规（必要路径出现网络调用）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Windows 控制台默认 GBK，会把中文与符号打出乱码并抛 UnicodeEncodeError。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

EXIT_OK = 0
EXIT_CHECK_FAILED = 1
EXIT_USAGE = 2
EXIT_GATE_BLOCKED = 3
EXIT_OFFLINE_VIOLATION = 4

CODE_SUFFIXES = {".py", ".yaml", ".yml", ".json", ".cfg", ".toml", ".sh", ".ps1", ".cmd"}
TEXT_SUFFIXES = CODE_SUFFIXES | {".md", ".txt", ".rst", ".svg", ".gitattributes", ".gitignore", ".editorconfig"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "_archive", "runs", "node_modules", ".pytest_cache"}
# 由本工具生成的产物：不参与自身检查（否则会自我循环）
GENERATED = {"gate-manifest.json", "gate-report.json"}


def _write_text_lf(path, text):
    """强制 LF 写出。

    Windows 上 Path.write_text 会做换行翻译，把 \\n 变成 \\r\\n ——
    这会让产物哈希在不同机器上不同，直接破坏 C2（逐位可复算）。
    """
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


@dataclass
class Finding:
    level: str          # ERROR | WARN | INFO
    path: str
    line: int
    message: str
    snippet: str = ""


@dataclass
class CheckResult:
    name: str
    gate: int
    status: str = "pass"          # pass | fail | skipped | not_implemented
    findings: list = field(default_factory=list)
    summary: str = ""

    def add(self, level, path, line, message, snippet=""):
        self.findings.append(Finding(level, str(path), line, message, snippet))

    @property
    def errors(self):
        return [f for f in self.findings if f.level == "ERROR"]

    @property
    def warnings(self):
        return [f for f in self.findings if f.level == "WARN"]


#: 检索会话的临时产物与全文缓存：已由 .gitignore 排除，门禁**也必须跳过**。
#: 否则它们会污染 abs_paths / encoding 等检查（实测：ACL 出版流程留下的
#: /Users/... 路径把 abs_paths 报成 WARN，而那不是我们的文件）。
SCRATCH_DIR_PREFIXES = ("_", ".pdfcache", ".venuecache")


def _is_scratch(rel_parts) -> bool:
    parts = list(rel_parts)
    if len(parts) >= 2 and parts[0] == "docs" and parts[1] == "results/README.md":
        return any(x.startswith(SCRATCH_DIR_PREFIXES) for x in parts[2:])
    return False


def iter_files(suffixes=None):
    """遍历仓库内受管文件（跳过 .git / 缓存 / 运行产物 / 归档 / 检索临时产物）。"""
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel_parts = p.relative_to(ROOT).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if _is_scratch(rel_parts):
            continue
        if p.name in GENERATED:
            continue
        if suffixes and p.suffix.lower() not in suffixes:
            continue
        yield p


def rel(p):
    return str(Path(p).relative_to(ROOT)).replace(os.sep, "/")


def read_text(p):
    return p.read_text(encoding="utf-8", errors="replace")


# ───────────────────────── Gate 0 ─────────────────────────

def check_encoding() -> CheckResult:
    """所有文本文件为 UTF-8 且无 BOM。"""
    r = CheckResult("encoding", 0)
    for p in iter_files(TEXT_SUFFIXES):
        raw = p.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            r.add("ERROR", rel(p), 1, "文件带 UTF-8 BOM；本项目要求无 BOM")
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as e:
            r.add("ERROR", rel(p), 1, "非 UTF-8 编码: %s" % e)
    r.summary = "扫描 %d 个文本文件" % sum(1 for _ in iter_files(TEXT_SUFFIXES))
    r.status = "fail" if r.errors else "pass"
    return r


def check_line_endings() -> CheckResult:
    """禁止 CRLF —— C2（逐位可复算）要求行尾一致。"""
    r = CheckResult("line_endings", 0)
    for p in iter_files(TEXT_SUFFIXES):
        raw = p.read_bytes()
        if b"\r\n" in raw:
            n = raw.count(b"\r\n")
            r.add("ERROR", rel(p), 1, "存在 CRLF 行尾 %d 处；须为 LF（.gitattributes 已声明）" % n)
    r.summary = "检查行尾一致性"
    r.status = "fail" if r.errors else "pass"
    return r


def check_dod_count() -> CheckResult:
    """设计规格 的 DoD 复选框实际条数 == 附录 D 的声明值。"""
    r = CheckResult("dod_count", 0)
    prd = ROOT / "设计规格.md"
    if not prd.exists():
        r.status = "skipped"
        r.summary = "设计规格.md 不存在"
        return r
    lines = read_text(prd).splitlines()
    actual = sum(1 for ln in lines if re.match(r"^\s*- \[ \]", ln))
    claim = None
    for ln in lines:
        if "**合计**" in ln and ln.strip().startswith("|"):
            nums = re.findall(r"\*\*(\d+)\*\*", ln)
            if nums:
                claim = int(nums[-1])
    if claim is None:
        r.add("ERROR", "设计规格.md", 0, "附录 D 未找到「**合计** | **N**」声明")
    elif claim != actual:
        r.add("ERROR", "设计规格.md", 0,
              "DoD 计数不一致：实际 %d，附录 D 声明 %d，差 %d" % (actual, claim, actual - claim))
    r.summary = "实际 %d 条；附录 D 声明 %s" % (actual, claim)
    r.status = "fail" if r.errors else "pass"
    return r


def check_negative_assertions() -> CheckResult:
    """负向断言扫描（R18 / 文献综述 §8）。"""
    r = CheckResult("negative_assertions", 0)
    pat_file = ROOT / "spec" / "negative-assertion-patterns.txt"
    if not pat_file.exists():
        r.status = "skipped"
        r.summary = "模式表 spec/negative-assertion-patterns.txt 不存在"
        return r
    pats = []
    for ln in read_text(pat_file).splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        pats.append(re.compile(s))
    scanned = 0
    for p in iter_files({".md", ".txt", ".rst"}):
        if p.name == "negative-assertion-patterns.txt":
            continue
        in_fence = False
        for i, ln in enumerate(read_text(p).splitlines(), 1):
            if ln.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue                                        # 豁免 3：代码块（检索式/模板）
            if "allow-negative-assertion" in ln:
                continue                    # 豁免 1：显式豁免（`#` 或 `<!-- -->` 均可）
            if "~~" in ln:
                continue                                        # 豁免 2：删除线（已废止）
            for pat in pats:
                m = pat.search(ln)
                if m:
                    r.add("ERROR", rel(p), i, "负向断言「%s」" % m.group(0),
                          ln.strip()[:160])
                    break
        scanned += 1
    r.summary = "扫描 %d 个文档，命中 %d 处" % (scanned, len(r.errors))
    r.status = "fail" if r.errors else "pass"
    return r


SECRET_PATTERNS = [
    # 实测假阳性（2026-10-06）：检索档案里他人仓库的路径片段
    # `docs/studies/task-conditioned-least-privilege-head-to-head.md` 含子串 `sk-`，
    # 在无左边界时被报成 key。加左边界后 `sk-` 须自成词首；真 key 总以引号 / 空白 /
    # 行首 / `=` 分隔，故检出不受影响。
    (re.compile(r"(?<![A-Za-z0-9_\-])sk-[A-Za-z0-9][A-Za-z0-9_\-]{19,}"), "OpenAI 风格 API key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "私钥正文"),
    (re.compile(r"(?i)\b(api[_-]?key|secret[_-]?key|session[_-]?secret|access[_-]?token|password|passwd)\b\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']"), "硬编码凭据"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9_\-\.]{20,}"), "Bearer token"),
    # 排除回环与未指定地址：本地靶标不是"真实目标"。
# 实测假阳性：docs/domain-and-literature.md 里的 127.0.0.1:9999（论文复现环境的本地端口）。
(re.compile(r"\b(?!127\.|0\.0\.0\.0)\d{1,3}(\.\d{1,3}){3}:\d{2,5}\b"), "疑似真实目标地址（IP:端口）"),
]


def check_secrets() -> CheckResult:
    """凭据与真实地址扫描（NF3）。"""
    r = CheckResult("secrets", 0)
    for p in iter_files(TEXT_SUFFIXES):
        if p.name in {"negative-assertion-patterns.txt", "gates.py"}:
            continue
        for i, ln in enumerate(read_text(p).splitlines(), 1):
            for pat, label in SECRET_PATTERNS:
                m = pat.search(ln)
                if m:
                    r.add("ERROR", rel(p), i, label, m.group(0)[:60])
                    break
    r.summary = "扫描凭据/私钥/真实地址模式 %d 类" % len(SECRET_PATTERNS)
    r.status = "fail" if r.errors else "pass"
    return r


# ⚠️ 首段至少两个路径字符：否则会把**转义序列**当成路径。实测假阳性（2026-10，
# AgentDojo 邮件正文）：正文写 `...format:\n{"type": ...}`，落到 JSON 里是
# `format:\\n{\\"type\\"...` ⇒ 旧式 `[A-Za-z]:\\[^\s]+` 把 `t:\\n{\\`
# 判成 Windows 绝对路径。那是转义的反斜杠，不是盘符。
ABS_PATH_PATTERNS = [
    (re.compile(r"[A-Za-z]:\\\\[A-Za-z0-9_.\-]{3,}(?:\\\\[^\s\"'<>|]*)?|[A-Za-z]:\\\\[A-Za-z0-9_.\-]{2,}\\\\[^\s\"'<>|]*"), "Windows 绝对路径"),
    (re.compile(r"(?<![\w/])/(home|Users|opt|mnt|srv)/[^\s\"'<>|]+"), "POSIX 绝对路径"),
]


def check_abs_paths() -> CheckResult:
    """绝对路径扫描。

    分级（D10-a）:
      * 代码文件（.py/.yaml/.json/...）—— ERROR。harness/ 与任何代码都不得含绝对路径，
        否则公开仓库无法独立运行。
      * 文档（.md/.txt）—— WARN。溯源引用（如外部组件位置）是正当的，但要可见。
    """
    r = CheckResult("abs_paths", 0)
    for p in iter_files(TEXT_SUFFIXES):
        if p.name in {"gates.py"}:
            continue
        # results/README.md 下是**检索原始记录**（论文里的示例路径、别人的机器路径），
        # 不是我们的代码；按文档对待（WARN），不按代码（ERROR）。
        # 实测假阳性：T05 的 C11 记录里出现论文描述的 `/home/.ssh/id_rsa`——
        # 那是被引论文里的示例，不是本仓库的路径。
        _rel = str(p.relative_to(ROOT)).replace("\\", "/")
        is_doc = p.suffix.lower() in {".md", ".txt", ".rst"} or _rel.startswith("results/README.md")
        for i, ln in enumerate(read_text(p).splitlines(), 1):
            for pat, label in ABS_PATH_PATTERNS:
                m = pat.search(ln)
                if not m:
                    continue
                if "allow-abs-path" in ln:
                    break
                lvl = "WARN" if is_doc else "ERROR"
                r.add(lvl, rel(p), i, label, m.group(0)[:80])
                break
    r.summary = "ERROR %d 处；WARN %d 处" % (len(r.errors), len(r.warnings))
    r.status = "fail" if r.errors else "pass"
    return r


def _sh_candidates():
    """Git for Windows 自带的 sh 可能在这些位置。"""
    out = []
    try:
        r = subprocess.run(["git", "--exec-path"], capture_output=True, text=True)
        if r.returncode == 0:
            p = Path(r.stdout.strip())
            for up in (p.parent, p.parent.parent, p.parent.parent.parent):
                out.append(up / "usr" / "bin" / "sh.exe")
                out.append(up / "bin" / "sh.exe")
    except Exception:
        pass
    out.append(Path("sh"))
    return out


def check_hook_health() -> CheckResult:
    """Git 钩子在本机能否真正执行。

    为什么需要这一项：Git for Windows 执行钩子必然经过 MSYS 的 sh。
    在受限环境（含 DSH 沙箱）里 sh 无法启动，**钩子根本不跑却不会报错**——
    这会让「有门禁」变成错觉。本检查把它变成可见的 WARN。
    """
    r = CheckResult("hook_health", 0)
    ok = None
    for c in _sh_candidates():
        try:
            pr = subprocess.run([str(c), "-c", "exit 0"], capture_output=True, timeout=15)
            if pr.returncode == 0:
                ok = str(c)
                break
        except Exception:
            continue
    hp = ROOT / ".githooks" / "pre-commit"
    if not hp.exists():
        r.add("WARN", ".githooks/pre-commit", 0, "钩子文件不存在")
    if ok is None:
        r.add("WARN", ".githooks/", 0,
              "MSYS sh 无法启动 ⇒ **Git 钩子不会执行**。请改用提交包装器：" 
              "python tools/gate_commit.py -m \"...\"  或  gates.cmd commit -m \"...\"")
        r.summary = "钩子不可用（必须用提交包装器）"
    else:
        r.summary = "钩子可用（sh: %s）" % ok
    r.status = "pass"          # 只警告，不阻塞
    return r


def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_manifest() -> CheckResult:
    """生成/校验受管文件清单哈希（回退与复算的基础）。"""
    r = CheckResult("manifest", 0)
    out = ROOT / "gate-manifest.json"
    current = {}
    for p in iter_files():
        if p.name in {"gate-manifest.json", "gate-report.json"}:
            continue
        current[rel(p)] = _sha256(p)
    if out.exists():
        try:
            prev = json.loads(read_text(out))
        except Exception:
            prev = {}
        prev_files = prev.get("files", {})
        added = sorted(set(current) - set(prev_files))
        removed = sorted(set(prev_files) - set(current))
        changed = sorted(k for k in set(current) & set(prev_files) if current[k] != prev_files[k])
        if added:
            r.add("INFO", "-", 0, "新增 %d 个文件" % len(added), ", ".join(added[:8]))
        if removed:
            r.add("WARN", "-", 0, "删除 %d 个文件" % len(removed), ", ".join(removed[:8]))
        if changed:
            r.add("INFO", "-", 0, "变更 %d 个文件" % len(changed), ", ".join(changed[:8]))
        r.summary = "对比上次清单：+%d / -%d / ~%d" % (len(added), len(removed), len(changed))
    else:
        r.summary = "首次生成清单（%d 个文件）" % len(current)
    payload = {
        "generated_by": "tools/gates.py",
        "file_count": len(current),
        "files": current,
    }
    _write_text_lf(out, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    r.status = "fail" if r.errors else "pass"
    return r


def check_formula_sync() -> CheckResult:
    """规范 ↔ 实现 的常数对账。

    为什么需要这一项：本项目已经发生过三次「文档改了、实现没改」与
    「两处文档各写一个值」的事故（L→I 映射、四因子 C、乘法式 R_m）。
    人眼比对 221 条 DoD 不可靠，故把 `spec/scoring.md` 里的**表格数字**
    与 `score/core.py` 里的**常量**做机械比对。任一处不一致即失败。
    """
    r = CheckResult("formula_sync", 0)
    md = ROOT / "spec" / "scoring.md"
    core_py = ROOT / "score" / "core.py"
    if not md.exists() or not core_py.exists():
        r.status = "skipped"
        r.summary = "spec/scoring.md 或 score/core.py 不存在"
        return r

    sys.path.insert(0, str(ROOT))
    try:
        from score import core as C
    except Exception as e:                                   # pragma: no cover
        r.add("ERROR", "score/core.py", 0, "无法导入参考实现：%s" % e)
        r.status = "fail"
        return r

    text = read_text(md)
    checked = 0

    # (1) §1.1 五个 EXPLOITABILITY 权重
    for name, val in (("W_REACH", C.W_REACH), ("W_ROUNDS", C.W_ROUNDS),
                      ("W_DEPTH", C.W_DEPTH), ("W_PRE", C.W_PRE), ("W_ADAPT", C.W_ADAPT)):
        m = re.search(r"\|\s*`%s`[^|]*\|\s*([0-9.]+)\s*\|" % name, text)
        if not m:
            r.add("ERROR", "spec/scoring.md", 0, "§1.1 未找到权重行 %s" % name)
            continue
        if abs(float(m.group(1)) - val) > 1e-12:
            r.add("ERROR", "spec/scoring.md", 0,
                  "权重不一致 %s：规范 %s vs 实现 %s" % (name, m.group(1), val))
        checked += 1

    # (2) §1.2 L 级别 → I_infosec 表
    for m in re.finditer(r"^\|\s*L([0-6])\s*\|[^|]*\|\s*\*\*([0-9.]+)\*\*\s*\|", text, re.M):
        L, shown = int(m.group(1)), float(m.group(2))
        impl = round(C.i_infosec(L), 2)
        if abs(shown - impl) > 1e-9:
            r.add("ERROR", "spec/scoring.md", 0,
                  "L%d → I_infosec 不一致：规范 %.2f vs 实现 %.2f" % (L, shown, impl))
        checked += 1
    if checked < 5:
        r.add("ERROR", "spec/scoring.md", 0, "§1.2 L→I_infosec 表解析失败（命中 %d 行）" % checked)

    # (3) §1.2 physical_consequence → I_physical 表
    seen_d = set()
    for m in re.finditer(r"^\|\s*`(none|D[0-9]{2}[AB]?|D10[AB])`\s*\|[^|]*\|\s*\*\*([0-9.]+)\*\*",
                         text, re.M):
        key, shown = m.group(1), float(m.group(2))
        if key not in C.I_PHYSICAL_BY_D:
            r.add("ERROR", "spec/scoring.md", 0, "§1.2 出现实现未定义的 physical_consequence：%s" % key)
            continue
        if abs(shown - C.I_PHYSICAL_BY_D[key]) > 1e-9:
            r.add("ERROR", "spec/scoring.md", 0,
                  "%s → I_physical 不一致：规范 %.2f vs 实现 %.2f"
                  % (key, shown, C.I_PHYSICAL_BY_D[key]))
        seen_d.add(key)
    missing = set(C.I_PHYSICAL_BY_D) - seen_d
    if missing:
        r.add("ERROR", "spec/scoring.md", 0,
              "§1.2 I_physical 表缺 %d 项：%s" % (len(missing), ", ".join(sorted(missing))))

    # (4) §3.3 两道封顶的高度
    for const, val in (("CAP_TEXT_ONLY", C.CAP_TEXT_ONLY),
                       ("CAP_UNDER_DELIVERED", C.CAP_UNDER_DELIVERED)):
        m = re.search(r"`%s\s*=\s*([0-9.]+)`" % const, text)
        if not m:
            r.add("ERROR", "spec/scoring.md", 0, "未找到封顶常数 %s" % const)
        elif abs(float(m.group(1)) - val) > 1e-12:
            r.add("ERROR", "spec/scoring.md", 0,
                  "封顶不一致 %s：规范 %s vs 实现 %s" % (const, m.group(1), val))
        else:
            checked += 1

    # (5) §3.3 证据层单调序（键集合必须一致，只要求裸词出现）
    for layer in C.LAYER_RANK:
        if not re.search(r"\b%s\b" % re.escape(layer), text):
            r.add("ERROR", "spec/scoring.md", 0, "§3.3 未提到证据层 %s" % layer)
        else:
            checked += 1

    # (6) §1.7 档位断点
    for brk, name in C.TIER_BREAKS:
        pat = r"\|\s*`?R?\s*[<≥>=]*\s*%s\s*`?\s*\|\s*\*\*%s\*\*\s*\|" % (re.escape(str(brk)), name)
        if not re.search(pat, text):
            # 退一步：只要断点数字与该档位名在同一行即可
            if not re.search(r"%s[^\n]*\*\*%s\*\*" % (re.escape(str(brk)), name), text):
                r.add("WARN", "spec/scoring.md", 0, "§1.7 未核对到档位断点 %s → %s" % (brk, name))

    # (7) 已废止的 v1 符号不得出现在「当前有效」的公式段
    for banned in ("layer_cred =", "neg_ctrl_pass =", "cleanup_pass =", "b_c ="):
        for i, ln in enumerate(text.splitlines(), 1):
            if banned in ln and "附录 A" not in ln:
                # 附录 A 是冻结的 v1 算例，允许出现
                if i > _appendix_a_start(text):
                    continue
                r.add("ERROR", "spec/scoring.md", i, "当前公式段出现已废止符号：%s" % banned)

    r.summary = "核对 %d 项常数 + %d 项 D 轴 + 7 组规则" % (checked, len(seen_d))
    r.status = "fail" if r.errors else "pass"
    return r


def _appendix_a_start(text: str) -> int:
    """返回「附录 A（v1 冻结区）」起始行号；找不到则返回一个极大值。"""
    for i, ln in enumerate(text.splitlines(), 1):
        if ln.startswith("## 附录 A"):
            return i
    return 1 << 30


# ───────────────────────── Gate 1 / 2（占位） ─────────────────────────

def check_card_contract_sync() -> CheckResult:
    """设计文档 ↔ schema 的字段对账。

    为什么需要：本项目已经踩过一次这个坑——`docs/technical-design.md` §2.3 写着
    「字段全集见 `spec/method-card.schema.json`」，**同一张表里**又引入了 schema 里
    根本没有的 `provenance_components`/`provenance_kind`/`composition_of`。
    两个工件互相指认对方为权威，结果谁都不是；而 Gate 1 当时全是 TODO，抓不到。

    做法：文档里用 `<!-- schema-authority: <schema 路径> -->` 声明该节的权威 schema，
    本节出现的每个 snake_case 字段名都必须能在该 schema 的 properties 里找到。
    """
    r = CheckResult("card_contract_sync", 0)
    doc = ROOT / "docs" / "technical-design.md"
    if not doc.exists():
        r.status = "skipped"
        r.summary = "docs/technical-design.md 不存在"
        return r

    lines = read_text(doc).splitlines()
    marker = re.compile(r"<!--\s*schema-authority:\s*(\S+?)\s*-->")
    ident = re.compile(r"`([a-z][a-z0-9_]{2,})`")

    sections = []            # (起始行, schema 路径)
    for i, ln in enumerate(lines):
        m = marker.search(ln)
        if m:
            sections.append((i, m.group(1)))
    if not sections:
        r.add("ERROR", "docs/technical-design.md", 0,
              "未找到任何 `<!-- schema-authority: ... -->` 标记；无法对账")
        r.status = "fail"
        return r

    # 允许的「子字段」名：出现在 schema 的嵌套 properties 里，但不是顶层字段
    def nested_props(schema):
        out = set()
        def walk(n):
            if isinstance(n, dict):
                for k, v in n.items():
                    if k == "properties" and isinstance(v, dict):
                        out.update(v.keys())
                        for vv in v.values():
                            walk(vv)
                    elif isinstance(v, (dict, list)):
                        walk(v)
            elif isinstance(n, list):
                for v in n:
                    walk(v)
        walk(schema)
        return out

    checked = 0
    for idx, (start, schema_rel) in enumerate(sections):
        # 本节范围 = 标记行之后，到**下一个同级或更高级标题**为止。
        # 不能「到下一个标记为止」——那会把后面所有章节的字段都算进来（踩过一次，报了 28 处假阳性）。
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if re.match(r"^#{1,3}\s", lines[j]):
                end = j
                break
        sp = ROOT / schema_rel
        if not sp.exists():
            r.add("ERROR", "docs/technical-design.md", start + 1,
                  "标记声明的 schema 不存在：%s" % schema_rel)
            continue
        schema = json.loads(read_text(sp))
        top = set((schema.get("properties") or {}).keys())
        nested = nested_props(schema)
        body = lines[start + 1:end]
        for j, ln in enumerate(body):
            if ln.lstrip().startswith("```"):
                continue
            if not ln.lstrip().startswith("|"):
                continue
            cells = ln.split("|")
            if len(cells) < 2:
                continue
            # 只看**第一列**（字段名列）。第一列里 `x` / **`x`** / ├ `x` 都要能取到。
            # 不能扫整行——那会把枚举值（local / behavior / text）当成字段名（报了 15 处假阳性）。
            first = cells[1]
            for tok in ident.findall(first):
                if tok in top or tok in nested:
                    continue
                r.add("ERROR", "docs/technical-design.md", start + 2 + j,
                      "本节声明以 %s 为权威，但字段 `%s` 不在其中（文档与契约脱节）"
                      % (schema_rel, tok))
                checked += 1
    # 附加：计数漂移。类会话最先读的是 项目说明/，而 项目说明/ 不在上面的标记覆盖范围内——
    # 实测已发生过一次漂移（项目说明 里写着"47 条规则"，而 schema 已是 44 条）。
    import json as _json
    mc = ROOT / "spec" / "method-card.schema.json"
    if mc.exists():
        S = _json.loads(read_text(mc))
        want = {"必填": len(S["required"]), "属性": len(S["properties"]),
                "规则": len(S["x-validation-rules"]), "校验规则": len(S["x-validation-rules"]),
                "x-validation-rules": len(S["x-validation-rules"])}
        # `(?!\d)` 是必需的：否则「46 条规则22 WARN」（意为「20 条『规则22』的 WARN」）
        # 会被误读成「本行声明了 47 条规则」。实测被 T06 的上报文档撞出过这个假阳性。
        pat = re.compile(r"(\d+)\s*(个?必填|个?属性|条\s*`?x-validation-rules`?|条\s*校验规则|条规则)(?!\d)")
        scanned = 0
        for p in list(ROOT.glob("*.md")) + list((ROOT / "docs").glob("*.md")) + \
                 list((ROOT / "项目说明").glob("*.md")) + list((ROOT / "spec").glob("*.md")):
            if p.name in {"docs/README.md", "ci-coverage.md"}:
                continue          # 提案与覆盖率表按设计会引用历史数字
            for i, ln in enumerate(read_text(p).splitlines(), 1):
                if "allow-count-drift" in ln or "~~" in ln:
                    continue
                for m in pat.finditer(ln):
                    key = m.group(2)
                    key = "必填" if "必填" in key else ("属性" if "属性" in key else "规则")
                    if int(m.group(1)) != want[key]:
                        r.add("ERROR", rel(p), i,
                              "schema 计数漂移：本行写 %s %s，schema 实为 %d" % (m.group(1), key, want[key]),
                              ln.strip()[:120])
                    scanned += 1
        r.summary = "对账 %d 个 schema 节 + %d 处计数引用，发现 %d 处脱节" % (
            len(sections), scanned, len(r.errors))
    r.status = "fail" if r.errors else "pass"
    return r


def check_ci_coverage_sync() -> CheckResult:
    """`docs/ci-coverage.md` 与 `tools/cardcheck.py` 的规则表必须一致。

    设计规格 F6 的 DoD：未实现的规则必须在 ci-coverage.md 显式列为缺口。
    这里把「显式列出」变成机械断言——否则那张表会很快变成历史文档。
    """
    r = CheckResult("ci_coverage_sync", 0)
    doc = ROOT / "docs" / "ci-coverage.md"
    if not doc.exists():
        r.add("ERROR", "docs/ci-coverage.md", 0, "缺口登记表不存在（设计规格 F6 DoD 要求它存在）")
        r.status = "fail"
        return r
    sys.path.insert(0, str(ROOT))
    try:
        from tools import cardcheck
    except Exception as e:                                   # pragma: no cover
        r.add("ERROR", "tools/cardcheck.py", 0, "无法导入：%s" % e)
        r.status = "fail"
        return r

    declared = len(cardcheck.Ctx(ROOT).schema["x-validation-rules"])
    text = read_text(doc)
    mapped = set(cardcheck.RULES)
    if len(mapped) != declared:
        r.add("ERROR", "tools/cardcheck.py", 0,
              "规则表映射 %d 条，schema 声明 %d 条" % (len(mapped), declared))

    # 表头声明的四个计数必须与代码一致
    counts = {"implemented": 0, "structural": 0, "deferred": 0}
    for _i, (_rid, _fn, status, _why) in cardcheck.RULES.items():
        counts[status] = counts.get(status, 0) + 1
    for label, key in (("已实现", "implemented"), ("结构保证", "structural"), ("登记缺口", "deferred")):
        pat = re.compile(r"\|\s*\**\s*%s\s*\**\s*\|\s*\**\s*(\d+)\s*\**\s*条" % label)
        m = pat.search(text)
        if not m:
            r.add("ERROR", "docs/ci-coverage.md", 0, "未找到「%s」计数行" % label)
        elif int(m.group(1)) != counts[key]:
            r.add("ERROR", "docs/ci-coverage.md", 0,
                  "「%s」计数 %s ≠ 代码里的 %d" % (label, m.group(1), counts[key]))

    # 每个 deferred 规则的 rule_id 必须出现在缺口表里
    for i in sorted(cardcheck.RULES):
        rid, _fn, status, _why = cardcheck.RULES[i]
        if status == "deferred" and ("`%s`" % rid) not in text:
            r.add("ERROR", "docs/ci-coverage.md", 0,
                  "规则 %d（%s）未实现，但缺口表里没有列出它" % (i, rid))

    r.summary = "规则 %d 条：已实现 %d / 结构 %d / 缺口 %d" % (
        declared, counts["implemented"], counts["structural"], counts["deferred"])
    r.status = "fail" if r.errors else "pass"
    return r


# ───────────────────────── Gate 1：方法卡契约 ─────────────────────────

_CARDCHECK = {}


def _cardcheck():
    """跑一次 cardcheck 并缓存（Gate 1 的六项都读同一份结果）。"""
    if "res" not in _CARDCHECK:
        sys.path.insert(0, str(ROOT))
        from tools import cardcheck
        ctx = cardcheck.Ctx(ROOT)
        _CARDCHECK["res"] = (cardcheck, ctx, cardcheck.run(ctx))
    return _CARDCHECK["res"]


# Gate 1 每项负责的规则号；None = 全部规则（用于 method_card_schema）
GATE1_RULE_MAP = {
    "method_card_schema": None,
    "ext_ratio": {27},
    "negative_control_refs": {3, 12, 15},
    "provenance_components": {6, 26, 27, 28, 35},
    "primary_asset_enum": {29, 30, 31, 36},
    "impact_class_coverage": {11},
}


def _gate1(name, desc):
    r = CheckResult(name, 1)
    try:
        _cc, ctx, res = _cardcheck()
    except Exception as e:                                   # pragma: no cover
        r.add("ERROR", "tools/cardcheck.py", 0, "无法运行卡校验器：%s" % e)
        r.status = "fail"
        return r

    want = GATE1_RULE_MAP.get(name)
    errs = [e for e in res["errors"] if want is None or e["rule"] in want]
    warns = [w for w in res["warnings"] if want is None or w["rule"] in want]
    for e in errs[:40]:
        r.add("ERROR", e["path"], e["rule"], "规则%s：%s" % (e["rule"], e["message"]))
    for w in warns[:20]:
        r.add("WARN", w["path"], w["rule"], "规则%s：%s" % (w["rule"], w["message"]))

    if name == "method_card_schema" and ctx.cards:
        # 让「本类 X/30」在门禁输出里可见。
        # 为什么需要：manifest 的 min_mechanisms 是**自声明**的，一个会话把标准定成 7
        # 就能通过——这是设计使然（如实报缺口是正确交付）。但那样缺口就不可见了，
        # 所以这里无条件把「本类去重方法数 / 30」与「本类机制数」并排报出来。
        try:
            from tools import count_identity
            ci = count_identity.compute(ctx)
            for row in ci["by_case"]:
                # D14：规模目标已取消，故**不再报「缺 N」**——只报实测数。
                r.add("INFO", "methods/%s" % row["case_id"], 43,
                      "%s：去重方法数 %d · 机制数 %d · 变体 %d"
                      % (row["case_id"], row["distinct_methods"],
                         row["mechanisms"], row["variants"]))
            r.add("INFO", "methods/", 43,
                  "合计：实例 %d / 去重方法数 N=%d —— 两数必须同报，"
                  "永远不得表述为「%d 种攻击方法」（C8）。"
                  "「每类 30 / 共 %d」的规模目标已由 docs/README.md D14 取消"
                  % (ci["instances"], ci["distinct_methods"],
                     ci["target_instances"], ci["target_instances"]))
        except Exception as e:                               # pragma: no cover
            r.add("WARN", "tools/count_identity.py", 43, "双计数不可用：%s" % e)

    if name == "impact_class_coverage" and ctx.cards:
        have = set()
        for c in ctx.cards:
            have |= set(c.get("impact_class") or [])
        missing = [x for x in "ABCDEF" if x not in have]
        if missing:
            r.add("WARN", "methods/", 11, "impact_class 尚未覆盖：%s" % ", ".join(missing))

    if not ctx.cards:
        r.summary = "无卡片（%s）；规则表 %d 条已映射" % (desc, res["rules_declared"])
        r.status = "pass"
        return r
    r.summary = "%d 张卡 · %d 处 ERROR · %d 处 WARN" % (len(ctx.cards), len(errs), len(warns))
    r.status = "fail" if r.errors else "pass"
    return r


def check_card_fixtures() -> CheckResult:
    """正反用例：19 个违规样本必须全部被拒，1 个合法样本必须通过。

    为什么这是 Gate 1 的必选项：`methods/` 为空时，任何规则都「通过」——
    因为无事可做。**一个从不失败的检查等于没有检查。** fixtures 保证每条约束
    都有东西可咬，且约束一旦被改坏（或 schema 里加了校验器不认识的 keyword）立刻暴露。
    """
    r = CheckResult("card_fixtures", 1)
    sys.path.insert(0, str(ROOT))
    from tools import cardcheck
    res = cardcheck.run_fixtures()
    if not res["ok"]:
        for f in res["failures"]:
            r.add("ERROR", "tests/fixtures/cards", 0, f)
    r.summary = "%d 套用例（%s）" % (res["cases"], "全部符合预期" if res["ok"] else "有 %d 处不符" % len(res["failures"]))
    r.status = "fail" if r.errors else "pass"
    return r


def check_unit_tests() -> CheckResult:
    """`tests/` 全绿。**在进程内跑**，不起子进程。

    为什么不起子进程：本项目的运行环境（含 DSH 沙箱）禁止具名管道，
    `subprocess` 捕获输出会 EPERM。进程内跑 unittest 既避开该限制，
    也让门禁本身不引入新的失败模式。
    """
    r = CheckResult("unit_tests", 2)
    sys.path.insert(0, str(ROOT))
    import io
    import unittest

    try:
        suite = unittest.TestLoader().discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    except Exception as e:                                   # pragma: no cover
        r.add("ERROR", "tests/", 0, "无法发现测试：%s" % e)
        r.status = "fail"
        return r

    total = suite.countTestCases()
    if total == 0:
        r.add("ERROR", "tests/", 0, "tests/ 下未发现任何用例（规范里的断言必须有执行器）")
        r.status = "fail"
        return r

    buf = io.StringIO()
    res = unittest.TextTestRunner(stream=buf, verbosity=0).run(suite)
    for case, tb in list(res.failures) + list(res.errors):
        last = [ln for ln in tb.strip().splitlines() if ln.strip()]
        r.add("ERROR", "tests/", 0, "用例失败：%s" % case, last[-1][:200] if last else "")
    passed = total - len(res.failures) - len(res.errors)
    r.summary = "%d 个用例：通过 %d，失败 %d，错误 %d" % (
        total, passed, len(res.failures), len(res.errors))
    r.status = "fail" if (res.failures or res.errors) else "pass"
    return r


def check_grade_reachable() -> CheckResult:
    """存在可行输入使 `R_m >= 9.0`（设计规格 F3 / R14 档位可达性）。

    这一项是**回归防护**：v1 的乘法式让 Critical 档在数学上不可达
    （真实停用断路器只得 3.71 / Low）。断言不能只做算术，必须真跑出一组输入。
    """
    r = CheckResult("grade_reachable", 2)
    sys.path.insert(0, str(ROOT))
    try:
        from score import core as C
    except Exception as e:                                   # pragma: no cover
        r.add("ERROR", "score/core.py", 0, "无法导入参考实现：%s" % e)
        r.status = "fail"
        return r

    n = C.min_n_for_tier("Critical")
    if n is None:
        r.add("ERROR", "score/core.py", 0, "Critical 档不可达 ⇒ 分数体系失去区分度")
        r.status = "fail"
        return r

    witness = C.ImpactResult(value=10.0, i_infosec=C.i_infosec(6), i_physical=9.0, i_raw=10.0)
    out = C.r_measured(witness, C.exp(1.0, 1.0, 1.0, 1.0, 1.0),
                       C.confidence(n, n, "deterministic"))
    if out["R_m"] < 9.0:
        r.add("ERROR", "score/core.py", 0,
              "构造失败：n=%d 时 R_m=%.4f < 9.0" % (n, out["R_m"]))
        r.status = "fail"
        return r

    # 反向断言：一期 n=3 的上限必须 < 7.0（否则「测 3 次就敢说高危」）
    ceiling3 = 10.0 * C.p_lo(3, 3)
    if ceiling3 >= 7.0:
        r.add("ERROR", "score/core.py", 0,
              "n=3 的上限 %.2f 已达 High 档 ⇒ 小样本保护失效" % ceiling3)

    r.summary = "Critical 可达：n >= %d（构造 R_m=%.4f）；n=3 上限 %.2f（%s）" % (
        n, out["R_m"], ceiling3, C.tier(ceiling3))
    r.status = "fail" if r.errors else "pass"
    return r


def placeholder(name, gate, desc):
    r = CheckResult(name, gate, status="not_implemented")
    r.summary = "未实现（Gate %d）：%s" % (gate, desc)
    return r
GATE1_CHECKS = [
    ("method_card_schema", lambda: _gate1("method_card_schema", "spec/method-card.schema.json 全量校验（26 必填 / 37 属性 / 47 条规则）"),
     "spec/method-card.schema.json 校验全部方法卡（26 必填 / 47 条规则）"),
    ("ext_ratio", lambda: _gate1("ext_ratio", "EXT- 占比上限 20%"), "EXT- 自建方法占比 <= 20%（硬规矩 C）"),
    ("negative_control_refs", lambda: _gate1("negative_control_refs", "负控引用"), "每张卡的 negative_control.method_id 指向真实存在的卡"),
    ("provenance_components", lambda: _gate1("provenance_components", "四分量出处"), "四分量出处齐全；composition_of 可解析（硬规矩 E/F）"),
    ("primary_asset_enum", lambda: _gate1("primary_asset_enum", "主类声明"), "primary_asset 为必填枚举 T01–T08"),
    ("impact_class_coverage", lambda: _gate1("impact_class_coverage", "影响类别覆盖"), "六种 impact_class 全覆盖（设计规格 §4.3.2）"),
    ("card_fixtures", check_card_fixtures, "夹具正反用例：19 个违规样本全部被拒"),
]
GATE2_CHECKS = [
    ("unit_tests", check_unit_tests),
    ("judge_regression", None, "judge_regression 19/19 PASS（设计规格 F2）"),
    ("bit_reproducible", None, "同输入两次运行产物 SHA-256 相同（NF1/C2）"),
    ("offline", None, "断网下 make eval-offline 可完成（NF2）"),
    ("grade_reachable", check_grade_reachable),
]




# ───────────────────────── 调度 ─────────────────────────

GATE0 = [
    ("encoding", check_encoding),
    ("formula_sync", check_formula_sync),
    ("card_contract_sync", check_card_contract_sync),
    ("ci_coverage_sync", check_ci_coverage_sync),
    ("line_endings", check_line_endings),
    ("dod_count", check_dod_count),
    ("negative_assertions", check_negative_assertions),
    ("secrets", check_secrets),
    ("abs_paths", check_abs_paths),
    ("manifest", check_manifest),
    ("hook_health", check_hook_health),
]


def run(gate, only=None):
    results = []
    if gate in ("0", "all"):
        for name, fn in GATE0:
            if only and name != only:
                continue
            results.append(fn())
    if gate in ("1", "all") and not only:
        for item in GATE1_CHECKS:
            name, fn = item[0], item[1]
            desc = item[2] if len(item) > 2 else name
            results.append(fn() if callable(fn) else placeholder(name, 1, desc))
    if gate in ("2", "all") and not only:
        for item in GATE2_CHECKS:
            name, fn = item[0], item[1]
            desc = item[2] if len(item) > 2 else name
            results.append(fn() if callable(fn) else placeholder(name, 2, desc))
    return results


def render(results, as_json):
    failed = [r for r in results if r.status == "fail"]
    if as_json:
        payload = {
            "summary": {
                "total": len(results),
                "pass": sum(1 for r in results if r.status == "pass"),
                "fail": len(failed),
                "not_implemented": sum(1 for r in results if r.status == "not_implemented"),
                "skipped": sum(1 for r in results if r.status == "skipped"),
            },
            "checks": [
                {
                    "name": r.name, "gate": r.gate, "status": r.status, "summary": r.summary,
                    "findings": [vars(f) for f in r.findings],
                }
                for r in results
            ],
        }
        _write_text_lf(ROOT / "gate-report.json",
                       json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(payload["summary"], ensure_ascii=False))
        return

    icon = {"pass": "[PASS]", "fail": "[FAIL]", "skipped": "[SKIP]",
            "not_implemented": "[TODO]"}
    for r in results:
        print("%s %-24s gate=%d  %s" % (icon.get(r.status, "[????]"), r.name, r.gate, r.summary))
        for f in r.findings:
            loc = f.path + ((":%d" % f.line) if f.line else "")
            print("       %-5s %s  %s" % (f.level, loc, f.message))
            if f.snippet:
                print("             | %s" % f.snippet)
    print("-" * 72)
    print("合计 %d 项：通过 %d，失败 %d，未实现 %d，跳过 %d" % (
        len(results),
        sum(1 for r in results if r.status == "pass"),
        len(failed),
        sum(1 for r in results if r.status == "not_implemented"),
        sum(1 for r in results if r.status == "skipped"),
    ))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Git 质量阀门")
    ap.add_argument("--gate", default="0", choices=["0", "1", "2", "all"])
    ap.add_argument("--check", default=None, help="只跑某一项检查")
    ap.add_argument("--json", action="store_true", help="输出 JSON 并写 gate-report.json")
    ap.add_argument("--list", action="store_true", help="列出全部检查")
    args = ap.parse_args(argv)

    if args.list:
        print("Gate 0（当前可跑）:")
        for name, _ in GATE0:
            print("  %-24s" % name)
        print("Gate 1（有方法卡之后）:")
        for item in GATE1_CHECKS:
            name, fn = item[0], item[1]
            desc = item[2] if len(item) > 2 else name
            print("  %-24s %s%s" % (name, desc, "" if callable(fn) else "  [TODO]"))
        print("Gate 2（有实现之后）:")
        for item in GATE2_CHECKS:
            name = item[0]
            fn = item[1]
            desc = item[2] if len(item) > 2 else name
            print("  %-24s %s%s" % (name, desc, "" if callable(fn) else "  [TODO]"))
        return EXIT_OK

    known = [n for n, _ in GATE0] + [i[0] for i in GATE1_CHECKS] + [i[0] for i in GATE2_CHECKS]
    if args.check:
        if args.check not in known:
            print("用法错误：未知检查 %r" % args.check, file=sys.stderr)
            return EXIT_USAGE
        if args.check in [i[0] for i in GATE2_CHECKS]:
            args.gate = "2"
        elif args.check in [i[0] for i in GATE1_CHECKS]:
            args.gate = "1"
            results = [i[1]() for i in GATE1_CHECKS if i[0] == args.check]
            render(results, args.json)
            return EXIT_CHECK_FAILED if any(x.status == "fail" for x in results) else EXIT_OK
        else:
            args.gate = "0"

    results = run(args.gate, only=args.check)
    render(results, args.json)
    return EXIT_CHECK_FAILED if any(r.status == "fail" for r in results) else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())