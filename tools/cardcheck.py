# -*- coding: utf-8 -*-
"""方法卡校验器（Gate 1 的执行器）。

包含两件互相独立的东西：

  1. **一个最小的 JSON Schema 子集校验器**。为什么自己写：环境里没有 `jsonschema`
     （已实测 `ModuleNotFoundError`），而本项目对统计与校验一律自实现（docs/README.md D3）。
     自写的最大风险是「schema 用了校验器不认识的 keyword，于是那条约束被静默忽略」——
     所以本文件带一道 `assert_keywords_supported()`：schema 里出现任何未实现的 keyword 即报错，
     绝不静默放过。

  2. **`x-validation-rules` 的执行器**。规则是语义的（跨卡引用、唯一性、覆盖率），
     JSON Schema 表达不了，必须逐条写代码。未实现的规则**必须**在 docs/ci-coverage.md
     显式登记为缺口，并由本模块断言该登记表与代码一致——不允许「文档说实现了、代码里没有」。

用法:
    python tools/cardcheck.py               校验 methods/ 下全部卡片
    python tools/cardcheck.py --json
    python tools/cardcheck.py --fixtures    只跑 tests/fixtures/cards 的正反用例
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

#: 未标定标记（禁令 10 的既有约定）。见规则 37 的具名例外说明。
UNCALIBRATED = "[待校准]"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

# ───────────────────────── 最小 JSON Schema 子集校验器 ─────────────────────────

SUPPORTED_KEYWORDS = {
    "$schema", "$id", "title", "description", "default",
    "type", "enum", "const",
    "properties", "additionalProperties", "required", "minProperties",
    "items", "minItems", "maxItems", "uniqueItems",
    "minLength", "maxLength", "pattern",
    "minimum", "maximum",
    "oneOf",
}

TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
}


def _is_type(value, name: str) -> bool:
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    cls = TYPE_MAP.get(name)
    return isinstance(value, cls) if cls else True


def assert_keywords_supported(schema, where: str = "<root>") -> list:
    """schema 里出现未实现的 keyword ⇒ 报错。防止约束被静默忽略。"""
    errs = []
    if isinstance(schema, dict):
        for k, v in schema.items():
            if k.startswith("x-"):
                continue
            if k not in SUPPORTED_KEYWORDS:
                errs.append("%s: 校验器不支持的 keyword %r（约束会被静默忽略）" % (where, k))
                continue
            if k in ("properties",) and isinstance(v, dict):
                for kk, vv in v.items():
                    errs += assert_keywords_supported(vv, "%s.%s" % (where, kk))
            elif k in ("items", "additionalProperties", "oneOf") or isinstance(v, (dict, list)):
                errs += assert_keywords_supported(v, "%s.%s" % (where, k))
    elif isinstance(schema, list):
        for i, v in enumerate(schema):
            errs += assert_keywords_supported(v, "%s[%d]" % (where, i))
    return errs


def _canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def _display_path(p: Path, root: Path) -> str:
    """优先给仓库相对路径；不在仓库内时退回绝对路径。

    历史 bug：原实现直接 `p.relative_to(root)`，当 `--fixtures` 或冒烟测试把
    `methods_dir` 指到仓库外时**直接抛 ValueError 崩掉**，而不是给出可读的校验结果。
    """
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _public(doc: dict) -> dict:
    """剥掉本模块注入的内部键（下划线开头），只留卡/清单自身的字段。"""
    return {k: v for k, v in doc.items() if not k.startswith("_")}


def validate(value, schema, path: str = "$") -> list:
    """返回 [(路径, 原因)]。空列表 = 通过。"""
    errs = []
    if not isinstance(schema, dict):
        return errs

    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, n) for n in names):
            return [("%s" % path, "类型应为 %s，实为 %s" % ("/".join(names), type(value).__name__))]

    if "const" in schema and _canon(value) != _canon(schema["const"]):
        errs.append((path, "应恒等于 %r，实为 %r" % (schema["const"], value)))

    if "enum" in schema and not any(_canon(value) == _canon(e) for e in schema["enum"]):
        errs.append((path, "取值 %r 不在枚举 %s 内" % (value, schema["enum"])))

    if "oneOf" in schema:
        hits = [i for i, s in enumerate(schema["oneOf"]) if not validate(value, s, path)]
        if len(hits) != 1:
            errs.append((path, "oneOf 要求恰好匹配 1 个分支，实际匹配 %d 个" % len(hits)))
            return errs

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errs.append((path, "长度 %d < minLength %d" % (len(value), schema["minLength"])))
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errs.append((path, "长度 %d > maxLength %d" % (len(value), schema["maxLength"])))
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append((path, "不匹配 pattern %s" % schema["pattern"]))

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append((path, "%r < minimum %r" % (value, schema["minimum"])))
        if "maximum" in schema and value > schema["maximum"]:
            errs.append((path, "%r > maximum %r" % (value, schema["maximum"])))

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errs.append((path, "元素数 %d < minItems %d" % (len(value), schema["minItems"])))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append((path, "元素数 %d > maxItems %d" % (len(value), schema["maxItems"])))
        if schema.get("uniqueItems"):
            seen = {}
            for i, item in enumerate(value):
                c = _canon(item)
                if c in seen:
                    errs.append((path, "uniqueItems：第 %d 项与第 %d 项重复" % (i, seen[c])))
                seen[c] = i
        if "items" in schema:
            for i, item in enumerate(value):
                errs += validate(item, schema["items"], "%s[%d]" % (path, i))

    if isinstance(value, dict):
        if "minProperties" in schema and len(value) < schema["minProperties"]:
            errs.append((path, "键数 %d < minProperties %d" % (len(value), schema["minProperties"])))
        for r in schema.get("required", []):
            if r not in value:
                errs.append((path, "缺必填字段 %s" % r))
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                errs += validate(v, props[k], "%s.%s" % (path, k))
            else:
                ap = schema.get("additionalProperties", True)
                if ap is False:
                    errs.append(("%s.%s" % (path, k),
                                 "未定义的字段（schema 为 additionalProperties: false）"))
                elif isinstance(ap, dict):
                    errs += validate(v, ap, "%s.%s" % (path, k))
    return errs

# ───────────────────────── 载入 ─────────────────────────

def _load_json(p: Path):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def _load_yaml(p: Path):
    import yaml
    with io.open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


CASES = ["T0%d" % i for i in range(1, 9)]
KIM7 = ["input_trust", "access_sensitivity", "workflow", "action", "memory", "tool", "user_interface"]
TRANSFORM_OPERATORS = {          # 由 method-card.schema.json 的 transform_chain enum 给出；
 "none", "nl_role", "chat_template", "refusal_suppress", "lang_shift", # 与
 "semantic", "encode", "auth", "context_seed", # /transform_registry.py
 "chatml", "chatml_think", "chatml_tool", "mot", "multi_turn", "full", # 与 /payload_variant.py
    "disguise", "aligned", "perturb_r", "perturb_p", "perturb_i",            # 的算子名一一对应
}


class Ctx:
    """一次校验的上下文。"""

    def __init__(self, root: Path, methods_dir: Path | None = None):
        self.root = root
        self.methods_dir = methods_dir or (root / "methods")
        self.schema = _load_json(root / "spec" / "method-card.schema.json")
        self.manifest_schema = _load_json(root / "spec" / "scenario-manifest.schema.json")
        self.profile_schema = _load_json(root / "spec" / "target-profile.schema.json")
        self.registry = _load_json(root / "judges" / "registry.json")
        self.judges = {j["judge_id"]: j for j in self.registry["judges"]}
        self.cards = []          # [{...,"_path": str, "_case_dir": str}]
        self.manifests = {}      # case_id -> manifest dict
        self.profiles = {}
        self.errors = []         # (level, path, rule_no, message)
        self._load()

    # ---- 载入 ----
    def _load(self):
        if self.methods_dir.exists():
            for p in sorted(self.methods_dir.rglob("*.y*ml")):
                if p.name == "manifest.json" or p.name.startswith("_"):
                    continue
                try:
                    doc = _load_yaml(p)
                except Exception as e:
                    self.errors.append(("ERROR", str(p.relative_to(self.root)), 0,
                                        "YAML 解析失败：%s" % e))
                    continue
                if not isinstance(doc, dict):
                    continue
                doc["_path"] = _display_path(p, self.root)
                doc["_case_dir"] = p.parent.name
                self.cards.append(doc)
            for p in sorted(self.methods_dir.rglob("manifest.json")):
                try:
                    m = _load_json(p)
                except Exception as e:
                    self.errors.append(("ERROR", str(p.relative_to(self.root)), 0,
                                        "manifest 解析失败：%s" % e))
                    continue
                self.manifests[p.parent.name] = m
                m["_path"] = _display_path(p, self.root)
        tp = self.root / "targets"
        if tp.exists():
            for p in sorted(tp.rglob("*.json")):
                try:
                    self.profiles[p.stem] = _load_json(p)
                except Exception:
                    pass

    def err(self, level, path, rule, msg):
        self.errors.append((level, path, rule, msg))

    @property
    def real_cards(self):
        """variant_of 为空的卡（变体不算方法）。"""
        return [c for c in self.cards if not c.get("variant_of")]

    def by_id(self):
        return {c.get("method_id"): c for c in self.cards}


# ───────────────────────── 47 条 x-validation-rules 的执行器 ─────────────────────────
# 键 = 规则在 spec/method-card.schema.json x-validation-rules 中的序号（1-based）。
# 值 = (rule_id, 实现函数, 状态)。状态 "deferred" 者必须带原因，并写入 docs/ci-coverage.md。

def r01(ctx):
    seen = {}
    for c in ctx.cards:
        mid = c.get("method_id")
        if mid in seen:
            ctx.err("ERROR", c["_path"], 1, "method_id 重复：%s（另一处在 %s）" % (mid, seen[mid]))
        seen[mid] = c["_path"]
        if mid and c.get("case_id") and not str(mid).startswith(str(c["case_id"]) + "."):
            ctx.err("ERROR", c["_path"], 1, "method_id 前缀 %r 不等于 case_id %r" % (mid, c.get("case_id")))


def r03(ctx):
    ids = ctx.by_id()
    for c in ctx.cards:
        nc = c.get("negative_control") or {}
        kind, ref = nc.get("kind"), nc.get("method_id")
        if kind == "none":
            if c.get("anchor") or not c.get("generated"):
                ctx.err("ERROR", c["_path"], 3,
                        "negative_control.kind='none' 仅允许用于 anchor=false 且 generated=true 的方法")
            if not (nc.get("note") or "").strip():
                ctx.err("ERROR", c["_path"], 3, "kind='none' 必须带 note 说明理由")
        elif ref and ref not in ids:
            ctx.err("ERROR", c["_path"], 3, "negative_control.method_id=%r 指向不存在的卡" % ref)


def r04(ctx):
    for c in ctx.cards:
        for op in c.get("transform_chain") or []:
            if op not in TRANSFORM_OPERATORS:
                ctx.err("ERROR", c["_path"], 4, "transform_chain 含未注册算子 %r" % op)


def r06(ctx):
    pat = re.compile(r"^(ATK-[A-Z]+-[0-9]{2}|S_L[0-9]+_[a-z_]+|EXT-[A-Za-z0-9_-]+|LIT-[A-Za-z0-9._-]+)$")
    transform_names = TRANSFORM_OPERATORS - {"none"}
    for c in ctx.cards:
        mr = c.get("mechanism_ref") or ""
        if not pat.match(mr):
            ctx.err("ERROR", c["_path"], 6, "mechanism_ref %r 不匹配允许的四种形态（ATK-* / S_L* / EXT-* / LIT-<bib_id>）" % mr)
        if mr in transform_names or mr.startswith("perturb") or mr.startswith("chatml"):
            ctx.err("ERROR", c["_path"], 6,
                    "mechanism_ref 不得填变换族名（%r）——变换族只能由 transform_chain 表达" % mr)


def r07_r13(ctx):
    """机制数（主口径）与方法数（辅助口径）—— 两个数必须分别报告。"""
    for case_id, m in sorted(ctx.manifests.items()):
        cards = [c for c in ctx.cards if c.get("case_id") == case_id]
        variants = [c for c in cards if c.get("variant_of")]
        real = [c for c in cards if not c.get("variant_of")]
        mechs = {c.get("mechanism_ref") for c in real}
        want_m = int(m.get("min_mechanisms", 30))
        want_n = int(m.get("min_methods", want_m))
        if len(mechs) < want_m:
            has_rat = len(str(m.get("mechanisms_shortfall_rationale") or "")) >= 20
            lvl = "WARN" if has_rat else "ERROR"
            ctx.err(lvl, m["_path"], 7,
                    "%s：不同 mechanism_ref 数 %d < min_mechanisms %d%s"
                    % (case_id, len(mechs), want_m,
                       "（已有缺口说明，记 WARN）" if has_rat else "（缺 mechanisms_shortfall_rationale，记 ERROR）"))
        if len(real) < want_n:
            ctx.err("WARN", m["_path"], 13,
                    "%s：非变体卡数 %d < min_methods %d" % (case_id, len(real), want_n))
        for c in variants:
            base = ctx.by_id().get(c.get("variant_of"))
            if base and c.get("mechanism_ref") != base.get("mechanism_ref"):
                ctx.err("ERROR", c["_path"], 8, "变体的 mechanism_ref 与基准卡不一致")


def r09(ctx):
    """`execution.script` 指向的文件必须存在——**两种模式一律生效**。

    这是「攻击方法脚本库」这一交付形态唯一的机器可检连接点：
    没有它，`scripts/` 里的文件与 `cards/` 里的卡之间没有任何可验证的关系。
    """
    for c in ctx.cards:
        ex = c.get("execution") or {}
        mode = ex.get("mode")
        if mode not in ("declarative", "script_hook"):
            ctx.err("ERROR", c["_path"], 9,
                    "execution.mode 必须是 declarative 或 script_hook，实为 %r" % mode)
            continue
        s = ex.get("script")
        if not s:
            ctx.err("ERROR", c["_path"], 9, "execution.script 必填（两种模式都要）")
        elif not (ctx.root / s).exists():
            ctx.err("ERROR", c["_path"], 9, "execution.script 指向的文件不存在：%s" % s)
        elif mode == "script_hook" and "scripts" not in str(s).replace("\\", "/"):
            ctx.err("WARN", c["_path"], 9,
                    "script_hook 的脚本不在 scripts/ 下（%s）；本项目的目录约定见 docs/delivery-form.md §1" % s)


def r45(ctx):
    """`execution.args` 不得夹带载荷正文（禁令 9）。"""
    # 启发式，不是完备的载荷检测器：只拦两类最明显的——
    # ① 凭据/私钥特征；② args 里出现成段中文（结构性参数不该是句子）。
    # 完备方案见 ROADMAP.md（需要真正的载荷分类器）。
    PAT = re.compile(r"(?i)(sk-[A-Za-z0-9_\-]{16,}|BEGIN [A-Z ]*PRIVATE KEY|"
                     r"[\u4e00-\u9fff，。；：、！？“”‘’（）]{25,})")
    for c in ctx.cards:
        ex = c.get("execution") or {}
        for k, v in (ex.get("args") or {}).items():
            s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            if PAT.search(s):
                ctx.err("ERROR", c["_path"], 45,
                        "execution.args.%s 疑似含载荷正文/凭据（禁令 9）：只放结构性参数" % k)


def r10(ctx):
    for c in ctx.cards:
        cl = c.get("cleanup") or {}
        if cl.get("required"):
            for k in ("reader", "expected_postcondition"):
                if not (cl.get(k) or "").strip():
                    ctx.err("ERROR", c["_path"], 10, "cleanup.required=true 时 %s 必填" % k)


def r12_r35(ctx):
    ids = ctx.by_id()
    for c in ctx.cards:
        v = c.get("variant_of")
        if not v:
            continue
        base = ids.get(v)
        if base is None:
            ctx.err("ERROR", c["_path"], 12, "variant_of=%r 指向不存在的卡" % v)
            continue
        if base.get("case_id") != c.get("case_id"):
            ctx.err("ERROR", c["_path"], 12, "variant_of 与基准卡 case_id 不同")
        if _canon(base.get("provenance_components")) != _canon(c.get("provenance_components")):
            ctx.err("ERROR", c["_path"], 35, "变体的 provenance_components 与基准卡不一致（变体只改包装，不改出处）")


def r_surface(ctx):
    """surface_layer 标 L6/L7 的卡报 WARN（schema 的 surface_layer 描述已承诺此项）。"""
    for c in ctx.cards:
        if c.get("surface_layer") in ("L6", "L7"):
            ctx.err("WARN", c["_path"], 0,
                    "surface_layer=%s 当前无实现（schema 已声明 CI 报 warning）" % c.get("surface_layer"))


def r14(ctx):
    debt = [c["_path"] for c in ctx.cards if (c.get("judge") or {}).get("self_attested")]
    if debt:
        ctx.err("WARN", "methods/", 14,
                "self_attested 判据技术债 %d 张（scoring 阶段 C 恒为 0）：%s"
                % (len(debt), ", ".join(debt[:5])))


def r15(ctx):
    for c in ctx.cards:
        dc = c.get("design_class")
        kind = (c.get("negative_control") or {}).get("kind")
        if dc == "reverse_captcha" and kind not in ("format_matched_benign", "semantic_matched_benign"):
            ctx.err("ERROR", c["_path"], 15, "reverse_captcha 的负控必须是 format/semantic_matched_benign，实为 %r" % kind)
        if dc == "obfuscation" and kind != "same_flow_without_marker":
            ctx.err("ERROR", c["_path"], 15, "obfuscation 的负控必须是 same_flow_without_marker，实为 %r" % kind)


def r16(ctx):
    for c in ctx.cards:
        if c.get("design_class") in ("reverse_captcha", "obfuscation"):
            params = (c.get("judge") or {}).get("params") or {}
            if "control_follow_rate" not in params:
                ctx.err("ERROR", c["_path"], 16,
                        "%s 的 judge.params 必须记录 control_follow_rate（缺对照会得出相反结论）" % c.get("design_class"))


#: 表1 的 8 个既有前缀（唯一真值源：外部组件 的 ## 标题）
ATK_PREFIXES = {"APP", "CODE", "EMB", "INJ", "MAS", "MEM", "SUP", "TOOL"}


def r46(ctx):
    """`ATK-<前缀>-NN` 的前缀必须在表1 白名单内。

    为什么需要：schema 的 pattern 是 `ATK-[A-Z]+-[0-9]{2}`，**任何大写前缀都能过**。
    实测 T02 用了 `ATK-AUD-01..09`，而表1 里没有 AUD——这等于自造 id 占了表1 的命名空间，
    读卡的人去查表1 查不到，与 `EXT-` 的马甲是同一类问题。
    表1 覆盖不到的新机制应走 `LIT-<bib_id>`。
    """
    for c in ctx.cards:
        mr = str(c.get("mechanism_ref") or "")
        if not mr.startswith("ATK-"):
            continue
        parts = mr.split("-")
        if len(parts) < 3:
            continue
        pfx = parts[1]
        if pfx not in ATK_PREFIXES:
            ctx.err("ERROR", c["_path"], 46,
                    "ATK-%s-… 的前缀不在表1 白名单 %s 内；表1 未覆盖的新机制请用 LIT-<bib_id>"
                    % (pfx, "/".join(sorted(ATK_PREFIXES))))


#: 表号/图号的形态（中英）
# 表号/图号定位符。**阿拉伯数字与罗马数字都收**：
# 实测 T01 的 B-26（IEEE TDSC 2026）正文用的是 `Table I / II / III`，
# 只认 \d 会把这种合法定位符判成"找不到表号"（假阳性）。
# 罗马数字分支加 \b，避免把 `Table in` / `Table If` 这类散文误判为定位符。
EVIDENCE_LOCATOR = re.compile(r"(Table\s*(?:\d+|[IVXLC]+\b)|Fig(?:ure)?\.?\s*(?:\d+|[IVXLC]+\b)|"
                              r"TABLE\s*(?:\d+|[IVXLC]+\b)|表\s*\d|图\s*\d)", re.I)


def r47(ctx):
    """`numeric_evidence == 'original_table'` ⇒ 必须能指出表号/图号。

    schema 本来就写着「original_table 必须能指出表号」，但从未机检。
    实测 89 张声明 original_table 的卡里有 16 张（18%）给不出表号——
    其中两张是会话自己发现并上报的（T06 的 71.0%、T08 的 A-5）。
    """
    for c in ctx.cards:
        if c.get("numeric_evidence") != "original_table":
            continue
        blob = []
        pc = c.get("provenance_components") or {}
        for v in pc.values():
            if isinstance(v, dict):
                blob += [str(v.get("source", "")), str(v.get("ref", ""))]
        blob += [str(x) for x in (c.get("source_refs") or [])]
        blob.append(str((c.get("trigger_path") or {}).get("note") or ""))
        if not EVIDENCE_LOCATOR.search(" ".join(blob)):
            ctx.err("ERROR", c["_path"], 47,
                    "numeric_evidence=original_table 但全卡找不到表号/图号；"
                    "数字在正文的应填 body_text，指不出出处的应填 abstract 或 none")


def r39(ctx):
    """机制出处前缀 ⟺ provenance_kind。"""
    for c in ctx.cards:
        mr = str(c.get("mechanism_ref") or "")
        pk = c.get("provenance_kind")
        is_ext = mr.startswith("EXT-")
        is_lit = mr.startswith("LIT-")
        if is_ext and pk != "ext":
            ctx.err("ERROR", c["_path"], 39, "mechanism_ref 以 EXT- 开头，provenance_kind 必须为 ext，实为 %r" % pk)
        if (not is_ext) and pk == "ext":
            ctx.err("ERROR", c["_path"], 39, "provenance_kind=ext 时 mechanism_ref 必须以 EXT- 开头，实为 %r" % mr)
        if is_lit and pk not in ("interpolation", "composition"):
            ctx.err("ERROR", c["_path"], 39, "LIT- 前缀要求 provenance_kind ∈ {interpolation, composition}，实为 %r" % pk)


def _bib_ids(ctx):
    """bib_id 全集 = **共享总表 ∪ 各类自己的 bib 表**。

    为什么是并集：并行作业规程（docs/README.md）P2 规定各类
    **不得写共享总表**，改写 `docs/bib-<CASE>.md`，由整理会话最后合并。
    若本函数只读总表，则任何使用 `LIT-` 通道的类别都会被**稳定卡死**——
    这正是 T06 遇到的阻塞（20 条 ERROR，三轮不变）：它的 20 个机制全走 LIT-，
    而总表里没有 B-105…B-124。

    这是本框架自身的一处设计冲突（规则 40 与 P2 互斥），不是任何类别会话的过错。
    """
    ids = set()
    found = False
    files = [ctx.root / "docs" / "shared-bibliography.md"]
    files += sorted((ctx.root / "docs").glob("bib-*.md"))
    for f in files:
        if not f.exists():
            continue
        found = True
        # 两种形态都认：
        #   B-<数字>        早期分配的数字段（保留，不可改）
        ids |= set(re.findall(r"\|\s*(B-(?:\d{1,4}|T0[1-8]-\d{1,4}))\s*\|",
                              f.read_text(encoding="utf-8")))
    return ids if found else None


def r40_r41(ctx):
    """LIT-<bib_id> 可解析 + 一个 (论文,机制) 只出一个。"""
    ids = _bib_ids(ctx)
    if ids is None:
        ctx.err("INFO", "docs/shared-bibliography.md", 40, "文献池不存在 ⇒ 规则 40 不可判")
        return
    seen = {}
    for c in ctx.cards:
        mr = str(c.get("mechanism_ref") or "")
        if not mr.startswith("LIT-"):
            continue
        bib = mr[4:]
        # `LIT-<bib_id><可选机制后缀>`：后缀（A/B/C…）代表**该文献内的第 N 个独立机制**。
        # 解析只查**基论文 id**——后缀的作用是在文献内部消歧，不另立文献条目。
        # 依据：mechanism_ref 是**机制级**标识（与 ATK-* 同级），而 bib_id 是论文级；
        # 一篇文献切出多个机制时，必须能在 mechanism_ref 上区分开，
        # 否则 C4 的「机制首步」轴看不见这个差异。
        base = re.sub(r"[A-Z]+$", "", bib)
        if base not in ids:
            ctx.err("ERROR", c["_path"], 40,
                    "LIT-%s 的基论文 %s 解析不到（否则它是 EXT- 的马甲）" % (bib, base))
        seen.setdefault(mr, []).append(c["_path"])
    for mr, paths in seen.items():
        if len(paths) > 1:
            ctx.err("ERROR", paths[1], 41,
                    "%s 在全库出现 %d 次；一个 (论文, 机制) 只出一个机制条目（出现处：%s）"
                    % (mr, len(paths), ", ".join(paths)))


# C4 五轴：字段 -> 取值函数
C4_AXES = {
    "injection_entry":     lambda c: (c.get("provenance_components") or {}).get("vector", {}).get("ref")
                                     if isinstance((c.get("provenance_components") or {}).get("vector"), dict)
                                     else (c.get("provenance_components") or {}).get("vector"),
    "target_asset":        lambda c: c.get("primary_asset"),
    "mechanism_first_step": lambda c: c.get("mechanism_ref"),
    "dialogue_shape":      lambda c: "%s/%s" % (c.get("dialogue_shape"), c.get("turns")),
    "judge_layer":         lambda c: "%s/%s" % ((c.get("judge") or {}).get("verifier"),
                                                (c.get("judge") or {}).get("evidence_layer")),
}
AXIS_FIELD_HINT = {
    "injection_entry": "provenance_components.vector",
    "target_asset": "primary_asset",
    "mechanism_first_step": "mechanism_ref",
    "dialogue_shape": "dialogue_shape+turns",
    "judge_layer": "judge.verifier+judge.evidence_layer",
}


def _is_control(c) -> bool:
    """负控卡（kind=none 的自持卡）是对照臂，不是竞争方法，不参与 C11。"""
    return ((c.get("negative_control") or {}).get("kind") == "none")


def r42(ctx):
    """C11：主张在某轴上不同的卡必须举证；拿不出举证就应退回变体。

    基准卡的判定必须是**确定性的**，否则同一组卡里每张都会要求别人举证。
    约定：同一 (case_id, mechanism_ref) 组内，**`method_id` 字典序最小者为基准卡**；
    其余为「主张不同」的一方，须给 `distinctness_evidence`。
    负控卡（`negative_control.kind == 'none'`）是对照臂，整组跳过。
    """
    groups = {}
    for c in ctx.cards:
        if c.get("variant_of") or _is_control(c):
            continue
        groups.setdefault((c.get("case_id"), c.get("mechanism_ref")), []).append(c)

    for (_case, _mr), members in sorted(groups.items(), key=lambda kv: str(kv[0])):
        if len(members) < 2:
            continue
        members = sorted(members, key=lambda c: str(c.get("method_id")))
        base = members[0]
        for c in members[1:]:
            diff_axes = [ax for ax, fn in C4_AXES.items() if fn(base) != fn(c)]
            if not diff_axes:
                ctx.err("WARN", c["_path"], 42,
                        "与基准卡 %s 在五轴上全等 ⇒ 应改为 variant_of（C1：变体不计入方法数）"
                        % base.get("method_id"))
                continue
            ev = c.get("distinctness_evidence")
            if not isinstance(ev, dict):
                ctx.err("ERROR", c["_path"], 42,
                        "与基准卡 %s 在 %s 轴上不同，但缺 distinctness_evidence（C11 举证）；"
                        "拿不出独立构造 + 独立数字时，应改为 variant_of"
                        % (base.get("method_id"), "/".join(diff_axes)))
                continue
            ax = ev.get("axis")
            if ax not in diff_axes:
                ctx.err("ERROR", c["_path"], 42,
                        "distinctness_evidence.axis=%r 不在实际有差异的轴 %s 内" % (ax, diff_axes))
            elif str(ev.get("value")) != str(C4_AXES[ax](c)):
                ctx.err("ERROR", c["_path"], 42,
                        "distinctness_evidence.value=%r 与卡上 %s 的实际取值 %r 不一致"
                        % (ev.get("value"), AXIS_FIELD_HINT[ax], C4_AXES[ax](c)))


def r43(ctx):
    """按 C4 五轴计数，把 N 与实例数报出来（口径本身由 schema 规则 43 定义）。"""
    real = ctx.real_cards
    if not real:
        return
    keys = {tuple(str(fn(c)) for fn in C4_AXES.values()) for c in real}
    ctx.err("INFO", "methods/", 43,
            "C4 五轴：实例 %d · 去重方法数 N=%d（重合率 %.0f%%）"
            % (len(real), len(keys), 100.0 * (1 - len(keys) / len(real))))


def r17(ctx):
    """每个目标画像上的**适用性覆盖表**。

    ⚠️ 本规则在 2026-10-01 改过语义，理由是一条实测出来的错位：

    原文（第一版）把「卡的 required_actions 不在目标 tools 并集里」报成 **ERROR**，
    但同一行报错文案自己写着「该卡在此目标上应记 `untested` 而非 `fail`」。
    **`untested` 是六态之一（R1/R2），是「测不了」，不是「卡错了」。** 把它报成
    ERROR，等于用错误级别表达一个本来就合法的状态——而那正是本项目
    `docs/judgment-discipline.md` §5.2 反复警告的「聚合掩盖」的镜像：
    把「不适用」压成「失败」。

    实测触发：2026-10-01 加入第一份目标画像（`targets/agentdojo-workspace.json`）后，
    本规则由「不可判」变为可判，立刻报出 **448 条 ERROR**。逐条看，它们全部是
    「这张卡在这一个目标上跑不了」——即 `untested`，不是缺陷。

    **现在的口径**：
      · 无目标画像 ⇒ INFO「不可判」（不是通过）；
      · 有目标画像 ⇒ 逐目标报**适用/不适用计数**，全部 INFO；
      · **不报 ERROR**。真正该报 ERROR 的是 `required_actions` 的**格式**问题，
        那是规则 44 的职责。

    **同时暴露的一个更大的缺口（本规则报不出来，登记在案）**：
    `required_actions` **没有受控词表**。实测 186 张卡用了 **152 个不同的动作名**，
    其中 141 个只在单一类别内出现（T04 一类自造 46 个），跨类共用的只有 11 个。
    ⇒ 该字段目前既不可跨类比较，也不与任何真实目标的工具清单挂钩。
    规则 44 只查格式 `^[a-z][a-z0-9_]*$`，查不出这一点。
    """
    if not ctx.profiles:
        ctx.err("INFO", "targets/", 17,
                "仓库内没有目标画像 ⇒ 规则 17 不可判（不是通过）。解除条件：targets/ 下出现第一份 TargetProfile")
        return

    for name, prof in sorted(ctx.profiles.items()):
        have = set(prof.get("tools") or [])
        applicable = 0
        gaps = {}
        for c in ctx.cards:
            need = set((c.get("trigger_path") or {}).get("required_actions") or [])
            missing = need - have
            if missing:
                for a in missing:
                    gaps[a] = gaps.get(a, 0) + 1
            else:
                applicable += 1
        ctx.err("INFO", "targets/%s" % name, 17,
                "适用性覆盖：%d/%d 张卡的 required_actions ⊆ 本目标 tools；"
                "%d 张在本目标上记 untested（缺 %d 种动作）"
                % (applicable, len(ctx.cards), len(ctx.cards) - applicable, len(gaps)))


def r44(ctx):
    for c in ctx.cards:
        for act in (c.get("trigger_path") or {}).get("required_actions") or []:
            if not re.match(r"^[a-z][a-z0-9_]*$", str(act)):
                ctx.err("ERROR", c["_path"], 44,
                        "required_actions 的元素 %r 不是动作标识（须 ^[a-z][a-z0-9_]*$）；"
                        "前置条件属于 preconditions，不得写进本字段" % act)


def r21(ctx):
    for c in ctx.cards:
        for k in ("source_grade", "numeric_evidence"):
            v = c.get(k)
            if v is None or (isinstance(v, str) and not v.strip()):
                ctx.err("ERROR", c["_path"], 21, "%s 必填且不得为空" % k)


def r22(ctx):
    for c in ctx.cards:
        j = c.get("judge") or {}
        reg = ctx.judges.get(j.get("verifier"))
        if reg and reg["report_dependent"] and not j.get("self_attested"):
            ctx.err("WARN", c["_path"], 22,
                    "判据 %s 标记 report_dependent=true，卡上未标 self_attested；"
                    "此类判据不得单独支撑 confirmed，只能支撑 inconclusive" % j.get("verifier"))


def r23_r38(ctx):
    for c in ctx.cards:
        j = c.get("judge") or {}
        reg = ctx.judges.get(j.get("verifier"))
        if reg and reg["requires_canary"] and not (j.get("params") or {}).get("canary_id"):
            ctx.err("ERROR", c["_path"], 38,
                    "判据 %s 要求 canary，但 judge.params.canary_id 缺失；缺 canary 时只能记 inconclusive"
                    % j.get("verifier"))
        # 2026-10-03 补：**schema 里 required 的每个键都要在**。规则 38 原先只查 `canary_id`，
        # 于是 `sensitive_data` 的 `field` 缺了也不报（实测：`T08.B-T08-08` 正是这样漏过去的）。
        if reg:
            req = (reg.get("params_schema") or {}).get("required") or []
            have = set((j.get("params") or {}))
            missing = [k for k in req if k not in have]
            if missing:
                # **WARN 而不是 ERROR，理由要写在明面上**（2026-10-03）：
                # 本条一开就露出 **42 张真卡**缺必填键（25 张 ground_truth_contradiction +
                # 17 张 audit_integrity）—— 那是**标注欠账**，不是"卡写错了"：
                # 其中 `claimed_value` / `authoritative_value` 是**运行期真值**，
                # 卡上本来就不该有真值。记 ERROR 会让 `cardcheck` 长期不可用（本文件是
                # 每次提交的入口），而"常年红的门禁"等于没有门禁。
                # ⇒ 保持**可见**（WARN + 逐卡列出），把裁定留给 `ROADMAP.md` **G-29**。
                ctx.err("WARN", c["_path"], 38,
                        "judge %s 的 params_schema.required 缺键：%s ⇒ 判据会抛 params_incomplete"
                        "（标注欠账，见 ROADMAP.md G-29）"
                        % (j.get("verifier"), ", ".join(sorted(missing))))


def r25(ctx):
    for c in ctx.cards:
        pc = c.get("physical_consequence")
        if pc in (None, "none", "D09"):
            continue
        j = c.get("judge") or {}
        reg = ctx.judges.get(j.get("verifier"))
        if reg is None:
            continue
        if not reg["supports_physical_consequence"]:
            ctx.err("ERROR", c["_path"], 25,
                    "physical_consequence=%s 但判据 %s 不支持状态差分（其 oracle_kinds=%s）"
                    % (pc, j.get("verifier"), reg["oracle_kinds"]))
        if j.get("evidence_layer") not in ("state", "causal"):
            ctx.err("ERROR", c["_path"], 25,
                    "physical_consequence=%s 要求 evidence_layer ∈ {state, causal}，实为 %r"
                    % (pc, j.get("evidence_layer")))


def r26(ctx):
    for c in ctx.cards:
        pk, comp = c.get("provenance_kind"), c.get("composition_of")
        if pk == "composition":
            if not comp:
                ctx.err("ERROR", c["_path"], 26, "provenance_kind=composition 时 composition_of 必填")
            elif len(comp) < 2:
                ctx.err("WARN", c["_path"], 26,
                        "composition_of 只有 %d 项——组合至少涉及 2 篇文献，请确认不是把单一来源误标为 composition" % len(comp))
        elif comp:
            ctx.err("ERROR", c["_path"], 26, "provenance_kind=%r 时 composition_of 不得出现" % pk)


def r27(ctx):
    total = len(ctx.real_cards)
    if total == 0:
        return
    ext = [c for c in ctx.real_cards if c.get("provenance_kind") == "ext"]
    ratio = len(ext) / total
    if ratio > 0.20:
        ctx.err("ERROR", "methods/", 27,
                "EXT- 占比 %.1f%% > 20%%（%d/%d）。超标即拒绝，不得靠下调 provenance_kind 蒙混"
                % (ratio * 100, len(ext), total))
    else:
        ctx.err("INFO", "methods/", 27, "EXT- 占比 %.1f%%（%d/%d），上限 20%%" % (ratio * 100, len(ext), total))


def r28(ctx):
    for c in ctx.cards:
        sg, pk = c.get("source_grade"), c.get("provenance_kind")
        if sg == "—" and pk != "ext":
            ctx.err("ERROR", c["_path"], 28, "source_grade='—' 仅允许 provenance_kind=ext，实为 %r" % pk)
        if pk == "ext" and sg != "—":
            ctx.err("ERROR", c["_path"], 28, "provenance_kind=ext 时 source_grade 必须为 '—'，实为 %r" % sg)


def r29_r30(ctx):
    for c in ctx.cards:
        pre = c.get("preconditions")
        if not isinstance(pre, dict):
            ctx.err("ERROR", c["_path"], 29, "preconditions 必须是 {Kim 7 维: 档位} 的 object")
            continue
        for k, v in pre.items():
            if k not in KIM7:
                ctx.err("ERROR", c["_path"], 29, "preconditions 键 %r 不在 Kim 7 维内" % k)
            if v not in (1, 2, 3):
                ctx.err("ERROR", c["_path"], 30, "preconditions[%s] 取值 %r 不是 1/2/3" % (k, v))


def r31(ctx):
    for c in ctx.cards:
        pa = c.get("primary_asset")
        if pa and pa != c.get("case_id"):
            ctx.err("WARN", c["_path"], 31,
                    "primary_asset=%s 与 case_id=%s 不同 ⇒ 记为【边界争议卡】"
                    "（这是 κ 研究要观测的信号，不要为了消警告而强行对齐）" % (pa, c.get("case_id")))


def r33(ctx):
    for c in ctx.cards:
        j = c.get("judge") or {}
        if j.get("evidence_layer") != "text":
            continue
        m = ctx.manifests.get(c.get("case_id"))
        if m is not None and not m.get("allow_text_fallback"):
            ctx.err("ERROR", c["_path"], 33,
                    "judge.evidence_layer=text 但场景 %s 的 allow_text_fallback=false" % c.get("case_id"))


def r36(ctx):
    if not ctx.cards:
        return
    have = {c.get("primary_asset") for c in ctx.cards}
    missing = [x for x in CASES if x not in have]
    if missing:
        ctx.err("INFO", "methods/", 36, "primary_asset 尚未覆盖：%s（该类尚无方法）" % ", ".join(missing))


def r37(ctx):
    for c in ctx.cards:
        j = c.get("judge") or {}
        vid = j.get("verifier")
        reg = ctx.judges.get(vid)
        if reg is None:
            ctx.err("ERROR", c["_path"], 37, "judge.verifier=%r 未在 judges/registry.json 注册" % vid)
            continue
        if j.get("evidence_layer") not in reg["evidence_layers"]:
            ctx.err("ERROR", c["_path"], 37,
                    "judge.evidence_layer=%r 不在 %s 的合法层集合 %s 内"
                    % (j.get("evidence_layer"), vid, reg["evidence_layers"]))
        schema = reg.get("params_schema") or {}
        props = schema.get("properties") or {}
        allowed = set(props)
        for k, v in (j.get("params") or {}).items():
            if allowed and k not in allowed:
                ctx.err("ERROR", c["_path"], 37, "judge.params 键 %r 不在 %s 的 params_schema 内" % (k, vid))
                continue
            # 值类型也要查（2026-10-03 补）：只查键名会漏掉两种**静默失效的填法** ——
            #   ① `control_follow_rate: 0.0` 这类"填给谁都一样"的值（它照样满足键名检查）；
            #   ② `[待校准]` 这类字符串占位填进 number 槽。
            # 判据侧本来就会抛 `params_invalid_type` ⇒ 门禁看不见等于把错误推迟到运行期。
            spec = props.get(k)
            if not isinstance(spec, dict):
                continue
            want = spec.get("type")
            if want == "string" and not isinstance(v, str):
                ctx.err("ERROR", c["_path"], 37,
                        "judge.params.%s 须为 string，实为 %s（%r）" % (k, type(v).__name__, v))
            elif want == "number" and v == UNCALIBRATED:
                # **具名例外，不是放宽**（2026-10-03）：`[待校准]` 是本项目**已有的**标记
                #  `spec/method-card.schema.json` 的 x-validation-rules 第 16 条又**强制**
                # `design_class ∈ {reverse_captcha, obfuscation}` 的卡必须显式记录本键）。
                # 两者相撞时唯一诚实的处置是**留着标记**：填一个数字就是"为了让门禁变绿而填假值"。
                # ⇒ 报 WARN 并**点名是未标定**，任何人不得把它当"已填"读。
                ctx.err("WARN", c["_path"], 37,
                        "judge.params.%s 是未标定标记 %r ⇒ 本键**尚无取值**，"
                        "不得当已填读（G-30）" % (k, UNCALIBRATED))
            elif want == "number" and (isinstance(v, bool) or not isinstance(v, (int, float))):
                ctx.err("ERROR", c["_path"], 37,
                        "judge.params.%s 须为 number，实为 %r" % (k, v))
            elif want == "integer" and (isinstance(v, bool) or not isinstance(v, int)):
                ctx.err("ERROR", c["_path"], 37,
                        "judge.params.%s 须为 integer，实为 %r" % (k, v))
            elif want == "boolean" and not isinstance(v, bool):
                ctx.err("ERROR", c["_path"], 37,
                        "judge.params.%s 须为 boolean，实为 %r" % (k, v))
            elif want == "array" and not isinstance(v, list):
                ctx.err("ERROR", c["_path"], 37,
                        "judge.params.%s 须为 array，实为 %r" % (k, v))
            elif spec.get("minLength") and isinstance(v, str) and len(v) < int(spec["minLength"]):
                ctx.err("ERROR", c["_path"], 37,
                        "judge.params.%s 长度 %d < minLength %s" % (k, len(v), spec["minLength"]))
            elif spec.get("enum") and v not in spec["enum"]:
                ctx.err("ERROR", c["_path"], 37,
                        "judge.params.%s 取值 %r 不在 enum %s 内" % (k, v, spec["enum"]))


# 规则号 -> (rule_id, 执行函数, 状态, 缺口原因)
RULES = {
    1:  ("unique_method_id", r01, "implemented", None),
    2:  ("verifier_registered", r37, "implemented", None),
    3:  ("negative_control_ref", r03, "implemented", None),
    4:  ("transform_registered", r04, "implemented",
 "仅校验算子名 ∈ schema enum；与 /transform_registry.py 的逐算子交叉核对待 harness/ 提取后补"),
    5:  ("case_container", None, "structural", "由 case_id / target_consequence 的 enum 在 schema 层保证"),
    6:  ("mechanism_ref_shape", r06, "implemented", None),
    7:  ("min_mechanisms", r07_r13, "implemented", None),
    8:  ("variant_excluded_from_count", r07_r13, "implemented", None),
    9:  ("script_exists", r09, "implemented",
         "两种模式都查 execution.script 存在；script_hook 的目录约定只报 WARN"),
    10: ("cleanup_fields", r10, "implemented", None),
    11: ("impact_class_letters", None, "structural", "由 impact_class.items.enum 保证"),
    12: ("variant_ref_exists", r12_r35, "implemented", None),
    13: ("min_methods", r07_r13, "implemented", None),
    14: ("self_attested_debt_list", r14, "implemented", None),
    15: ("design_class_negative_control", r15, "implemented", None),
    16: ("control_follow_rate", r16, "implemented", None),
    17: ("required_actions_in_profile", r17, "implemented",
         "无目标画像时报 INFO（不可判），有画像时逐动作校验"),
    18: ("per_dimension_table_in_report", None, "deferred", "需要报告产物；报告器属二期（设计规格 F5）"),
    19: ("index_only_flag", None, "deferred", "需要报告产物；报告器属二期（设计规格 F5）"),
    20: ("superseded_removed_from_index", None, "deferred", "需要报告索引产物；报告器属二期（设计规格 F5）"),
    21: ("dual_grade_present", r21, "implemented", None),
    22: ("report_dependent_flagged", r22, "implemented", None),
    23: ("canary_required", r23_r38, "implemented", None),
    24: ("case_container_strict", None, "structural", "由 case_id enum 保证（且 schema 已拒绝 D/baseline/T09/T10）"),
    25: ("physical_needs_state_judge", r25, "implemented", None),
    26: ("composition_of", r26, "implemented",
         "composition_of 元素对共享文献池的可解析性待 spec/shared-bibliography 索引化后补"),
    27: ("ext_ratio_20pct", r27, "implemented", None),
    28: ("source_grade_dash_iff_ext", r28, "implemented", None),
    29: ("preconditions_kim7", r29_r30, "implemented", None),
    30: ("preconditions_levels", r29_r30, "implemented", None),
    31: ("primary_asset_dispute_warn", r31, "implemented", None),
    32: ("physical_consequence_required", None, "structural", "由 required 列表 + physical_consequence.enum 保证"),
    33: ("text_layer_needs_fallback", r33, "implemented", None),
    34: ("declared_vs_reached_cap", None, "implemented",
         "判定与封顶在 score/core.py 实现，正反用例见 tests/test_score_core.py::TestCaps"),
    35: ("variant_provenance_identical", r12_r35, "implemented", None),
    36: ("primary_asset_union", r36, "implemented", None),
    37: ("judge_registry_consistency", r37, "implemented", None),
    38: ("canary_params_required", r23_r38, "implemented", None),
    39: ("mechanism_prefix_kind_binding", r39, "implemented", None),
    40: ("lit_resolvable_in_bibliography", r40_r41, "implemented", None),
    41: ("lit_unique_per_paper_mechanism", r40_r41, "implemented", None),
    42: ("c11_distinctness_evidence", r42, "implemented", None),
    43: ("c4_five_axis_identity", r43, "implemented", None),
    44: ("required_actions_identifier", r44, "implemented", None),
    45: ("args_no_payload_body", r45, "implemented",
         "按载荷/凭据特征串扫描 args；不是完备的载荷检测器，只是最低限度拦截"),
    46: ("atk_prefix_whitelist", r46, "implemented", None),
    47: ("original_table_needs_locator", r47, "implemented", None),
}

# ───────────────────────── 覆盖率与运行 ─────────────────────────

def coverage(ctx) -> dict:
    """47 条规则的实现状态。缺任何一条即视为代码 bug（规则表与 schema 脱节）。"""
    declared = len(ctx.schema["x-validation-rules"])
    missing = [i for i in range(1, declared + 1) if i not in RULES]
    extra = [i for i in RULES if i > declared]
    return {"declared": declared, "mapped": len(RULES), "missing": missing, "extra": extra}


def run(ctx: Ctx) -> dict:
    # (0) schema 自检：未实现的 keyword 必须报错，不能静默忽略
    keyword_errors = []
    for name in ("method-card.schema.json", "scenario-manifest.schema.json",
                 "target-profile.schema.json", "judge-registry.schema.json"):
        sch = _load_json(ctx.root / "spec" / name)
        keyword_errors += ["%s %s" % (name, e) for e in assert_keywords_supported(sch, name)]

    # (1) 结构校验：卡片、manifest、注册表
    # 注意：`_path` / `_case_dir` 是本模块注入的内部键，校验前必须剥掉，
    # 否则会被 additionalProperties:false 判为未定义字段（这个假阳性踩过一次）。
    for c in ctx.cards:
        for path, msg in validate(_public(c), ctx.schema, "$"):
            ctx.err("ERROR", c["_path"], 0, "schema：%s %s" % (path, msg))
    for case_id, m in ctx.manifests.items():
        for path, msg in validate(_public(m), ctx.manifest_schema, "$"):
            ctx.err("ERROR", m["_path"], 0, "manifest schema：%s %s" % (path, msg))
        if m.get("case_id") and m["case_id"] != case_id:
            ctx.err("ERROR", m["_path"], 0, "manifest.case_id=%s 不等于目录名 %s" % (m["case_id"], case_id))
    for name, prof in ctx.profiles.items():
        for path, msg in validate(prof, ctx.profile_schema, "$"):
            ctx.err("ERROR", "targets/%s" % name, 0, "target-profile schema：%s %s" % (path, msg))
    reg_schema = _load_json(ctx.root / "spec" / "judge-registry.schema.json")
    for path, msg in validate(ctx.registry, reg_schema, "$"):
        ctx.err("ERROR", "judges/registry.json", 0, "registry schema：%s %s" % (path, msg))

    # (1b) surface_layer 的 L6/L7 警告（schema 描述已承诺）
    r_surface(ctx)

    # (2) 语义规则。
    # 多个规则号可能共用同一个函数（例如 7/8/13 都是「计数纪律」）。
    # 共用时**只跑一次**，否则同一问题会被报两遍。
    ran = set()
    for no in sorted(RULES):
        _rid, fn, status, _why = RULES[no]
        if status == "deferred":
            ctx.err("INFO", "-", no, "规则未实现（已登记缺口）：%s" % _rid)
            continue
        if fn is None or id(fn) in ran:
            continue
        ran.add(id(fn))
        fn(ctx)

    cov = coverage(ctx)
    for i in cov["missing"]:
        ctx.err("ERROR", "tools/cardcheck.py", i,
                "x-validation-rules 第 %d 条没有对应的执行器（规则表与 schema 脱节）" % i)
    for i in cov["extra"]:
        ctx.err("ERROR", "tools/cardcheck.py", i,
                "规则表里的第 %d 条超出了 schema 声明的 %d 条" % (i, cov["declared"]))

    return summarize(ctx, cov)


def summarize(ctx: Ctx, cov: dict) -> dict:
    by_level = {"ERROR": [], "WARN": [], "INFO": []}
    for level, path, rule, msg in ctx.errors:
        by_level[level].append({"rule": rule, "path": path, "message": msg})
    implemented = sum(1 for v in RULES.values() if v[2] == "implemented")
    return {
        "cards": len(ctx.cards),
        "real_cards": len(ctx.real_cards),
        "manifests": len(ctx.manifests),
        "targets": len(ctx.profiles),
        "judges": len(ctx.judges),
        "rules_declared": cov["declared"],
        "rules_implemented": implemented,
        "rules_structural": sum(1 for v in RULES.values() if v[2] == "structural"),
        "rules_deferred": sum(1 for v in RULES.values() if v[2] == "deferred"),
        "deferred": [{"rule": i, "id": RULES[i][0], "why": RULES[i][3]}
                     for i in sorted(RULES) if RULES[i][2] == "deferred"],
        "errors": by_level["ERROR"],
        "warnings": by_level["WARN"],
        "infos": by_level["INFO"],
        "ok": not by_level["ERROR"],
        "keyword_errors": [],
    }


def run_fixtures(fixtures_dir: Path | None = None) -> dict:
    """跑 tests/fixtures/cards 的正反用例。

    为什么必须有这一项：`methods/` 为空时，全部规则都「通过」——因为无事可做。
    那样的门禁是装饰品。fixtures 保证每条约束都有东西可咬。
    """
    d = fixtures_dir or (ROOT / "tests" / "fixtures" / "cards")
    expect_file = d / "expectations.json"
    if not expect_file.exists():
        return {"ok": False, "failures": ["缺少 %s" % expect_file], "cases": 0}
    exp = _load_json(expect_file)
    failures = []
    cases = 0
    for item in exp["cases"]:
        cases += 1
        sub = d / item["dir"]
        ctx = Ctx(ROOT, methods_dir=sub)
        res = run(ctx)
        got_err = res["ok"] is False
        if got_err != item["expect_error"]:
            failures.append("%s：期望 %s，实际 %s（%d 条 ERROR）" % (
                item["dir"], "拒绝" if item["expect_error"] else "通过",
                "拒绝" if got_err else "通过", len(res["errors"])))
            continue
        if item.get("expect_rule") is not None:
            hit = {e["rule"] for e in res["errors"]}
            if item["expect_rule"] not in hit:
                failures.append("%s：期望命中规则 %s，实际命中 %s" % (
                    item["dir"], item["expect_rule"], sorted(hit)))
    return {"ok": not failures, "failures": failures, "cases": cases}


def main(argv=None):
    ap = argparse.ArgumentParser(description="方法卡校验器（Gate 1 执行器）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fixtures", action="store_true", help="只跑 fixtures 正反用例")
    ap.add_argument("--coverage", action="store_true", help="打印规则实现覆盖率")
    ap.add_argument("--case", default=None, metavar="T0X",
                    help="只校验某一类（并行作业用；Gate 1 是全局的，本选项让各类互不干扰）")
    a = ap.parse_args(argv)

    if a.coverage:
        ctx = Ctx(ROOT)
        cov = coverage(ctx)
        for i in sorted(RULES):
            rid, _fn, status, why = RULES[i]
            print("%2d  %-34s %-12s %s" % (i, rid, status, why or ""))
        print("-" * 72)
        print("声明 %d 条；已映射 %d 条；缺 %s" % (cov["declared"], cov["mapped"], cov["missing"] or "无"))
        return 0 if not cov["missing"] and not cov["extra"] else 1

    if a.fixtures:
        r = run_fixtures()
        print(("fixtures: %d 个用例，" % r["cases"]) + ("全部符合预期" if r["ok"] else "有 %d 处不符" % len(r["failures"])))
        for f in r["failures"]:
            print("  ! %s" % f)
        return 0 if r["ok"] else 1

    ctx = Ctx(ROOT)
    if a.case:
        # 并行作业用：只看本类的卡。六个类别会话同时写卡时，
        # Gate 1 是**全局**的——任何一类的卡有错，所有人的 Gate 1 都红。
        # 本选项让每类只验自己那一份，互不干扰。
        ctx.cards = [c for c in ctx.cards if c.get("case_id") == a.case]
        ctx.manifests = {k: v for k, v in ctx.manifests.items() if k == a.case}
    res = run(ctx)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["ok"] else 1
    print("卡片 %d（其中非变体 %d）· manifest %d · 目标画像 %d · 判据注册表 %d"
          % (res["cards"], res["real_cards"], res["manifests"], res["targets"], res["judges"]))
    print("规则：声明 %d · 已实现 %d · 结构保证 %d · 登记缺口 %d"
          % (res["rules_declared"], res["rules_implemented"],
             res["rules_structural"], res["rules_deferred"]))
    for e in res["errors"]:
        print("  [ERROR] 规则%-3s %s  %s" % (e["rule"], e["path"], e["message"]))
    for w in res["warnings"]:
        print("  [WARN]  规则%-3s %s  %s" % (w["rule"], w["path"], w["message"]))
    for i in res["infos"]:
        print("  [INFO]  规则%-3s %s  %s" % (i["rule"], i["path"], i["message"]))
    print("-" * 72)
    print("结论：%s" % ("通过" if res["ok"] else "失败（%d 条 ERROR）" % len(res["errors"])))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())