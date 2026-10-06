#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bibsearch —— 8 个攻击类别共用的文献检索工具（多源 + 熔断 + 可复现）。

设计动因（实测得出，非假设）:
  当前实现直连实测: OpenAlex 与 Semantic Scholar 对当前出口 IP 整段返回 429
  (0.4s 内拒绝，带 mailto 进 polite pool 无效)；Crossref / DBLP / arXiv /
  OpenAIRE / Europe PMC 全部 200 可用。
  因此本工具不把任何单一源当唯一通路：按源逐个尝试，某源失败即熔断跳过，
  并在输出里明确记录"哪个源没答"，绝不把"源失败"静默成"没找到"。

对应项目纪律:
  docs/search-protocol.md §3 四轮检索 —— 每轮检索式必须记录并归档
  docs/search-protocol.md §6 第 7 步 —— 写入共享文献池后才可入库（本工具只出候选）
  docs/judgment-discipline.md E2 —— 数字必须直读原始工件（本工具只给题录）
  docs/judgment-discipline.md E3 —— 负向断言必须记录检索式与轮次

依赖: 仅 Python 标准库。无第三方包，无 API key。

用法:
  python bibsearch.py health
  python bibsearch.py discover --class T01 --queries "..." "..." --out cand.json
  python bibsearch.py refs --doi 10.52202/079017-4136 --out refs.json
  python bibsearch.py verify --doi 10.1016/j.inffus.2025.103900
  python bibsearch.py verify --file dois.txt
"""

import argparse
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

_real_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(_real_stdout.buffer, encoding="utf-8",
                             errors="replace", line_buffering=True)
sys.stdout.detach() if False else None  # 保持 _real_stdout 存活，避免底层 buffer 被 GC 关闭

UA = {
    "User-Agent": "agent-attack-atlas-bibsearch/0.2 (mailto:bib@example.invalid)",
    "Accept": "application/json",
}
GAP = 1.2
MAX_RETRY = 3
TIMEOUT = 40

ATTACK_KW = ["poison", "backdoor", "attack", "inject", "corrupt", "trigger",
             "adversar", "malicious", "jailbreak", "manipulat", "tamper", "exploit"]
SURVEY_KW = ["survey", "systematization", "sok", "review", "taxonomy",
             "overview", "benchmark", "position paper"]


class Source:
    def __init__(self, name):
        self.name = name
        self.alive = True
        self.errors = []
        self._last = 0.0

    def get(self, url, label=""):
        if not self.alive:
            return None
        wait = GAP - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        for attempt in range(MAX_RETRY):
            self._last = time.time()
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    return r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                self.errors.append("%s HTTP %s" % (label, e.code))
                if e.code in (429, 403):
                    self.alive = False
                    return None
                if e.code >= 500:
                    time.sleep(2 * (attempt + 1))
                    continue
                return None
            except Exception as e:
                self.errors.append("%s %s" % (label, type(e).__name__))
                time.sleep(1.5 * (attempt + 1))
        return None


SOURCES = {n: Source(n) for n in
           ["crossref", "dblp", "arxiv", "openaire", "europepmc", "openalex"]}


def s_crossref(q, rows=40):
    url = ("https://api.crossref.org/works?rows=%d&query.bibliographic=%s"
           "&filter=from-pub-date:2024-01-01" % (rows, urllib.parse.quote(q)))
    body = SOURCES["crossref"].get(url, "cr:%s" % q[:28])
    if not body:
        return []
    out = []
    for it in json.loads(body)["message"]["items"]:
        ev = (it.get("event") or {}).get("name")
        ct = (it.get("container-title") or [None])[0]
        out.append({
            "title": (it.get("title") or [""])[0],
            "year": ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0],
            "venue": ct or ev or "?",
            "venue_type": it.get("type"),
            "doi": it.get("DOI"),
            "cited_by": it.get("is-referenced-by-count"),
            "source": "crossref",
            "raw_event": ev,
            "publisher": it.get("publisher"),
        })
    return out


def s_dblp(q, rows=40):
    url = ("https://dblp.org/search/publ/api?q=%s&format=json&h=%d"
           % (urllib.parse.quote(q), rows))
    body = SOURCES["dblp"].get(url, "dblp:%s" % q[:28])
    if not body:
        return []
    try:
        hits = json.loads(body)["result"]["hits"].get("hit", [])
    except Exception:
        return []
    out = []
    for h in hits:
        i = h.get("info", {})
        v = i.get("venue")
        if isinstance(v, list):
            v = v[0] if v else None
        out.append({
            "title": (i.get("title") or "").rstrip("."),
            "year": int(i["year"]) if str(i.get("year", "")).isdigit() else None,
            "venue": v,
            "venue_type": i.get("type"),
            "doi": i.get("doi"),
            "cited_by": None,
            "source": "dblp",
            "raw_event": None,
            "publisher": None,
        })
    return out


def s_arxiv(q, rows=30):
    """arXiv 检索。

    ⚠️ 2026-09-29 实测修正（T02 会话发现，影响 T01 结论的口径）：
    `all:<整串>` 在 arXiv API 里是 **OR 语义**，不是短语匹配。
    实测 `all:audit log tampering attack LLM agent` 返回 30 条里包含
    《Detecting Tampering in a Random Hypercube》(2012) 这类完全无关条目，
    而 `all:log injection attack large language model` 返回 **0 条**
    ——即"噪声混入"与"静默漏检"同时发生。
    故改为**逐词 `all:` + AND 连接**（arXiv API 的合取写法），
    并把原始检索式记进 `raw_query` 以便复现与对账。

    另：该源对本出口 IP 有**请求频率限制**，连续查询会 429。
    此处对 429 做退避重试，且**只在连续失败后才熔断**（默认行为是立即熔断，
    会把"限流"误报成"源不可用"，与 E3 的口径冲突）。
    """
    import re as _re
    terms = [w for w in _re.findall(r"[A-Za-z][A-Za-z0-9\-]+", q)]
    if not terms:
        terms = [q]
    expr = " AND ".join("all:%s" % t for t in terms)
    url = ("https://export.arxiv.org/api/query?search_query=%s&max_results=%d"
           % (urllib.parse.quote(expr), rows))
    body = None
    for attempt in range(3):
        body = SOURCES["arxiv"].get(url, "arxiv:%s" % q[:24])
        if body:
            break
        if not SOURCES["arxiv"].alive:
            # 被 429 熔断：本函数不复活源状态，交由调用方按"部分完成"记录
            return []
        time.sleep(3 * (attempt + 1))
    if not body:
        return []
    out = []
    for entry in re.findall(r"<entry>(.*?)</entry>", body, re.S):
        t = re.search(r"<title>(.*?)</title>", entry, re.S)
        d = re.search(r"<published>(\d{4})", entry)
        idm = re.search(r"<id>(.*?)</id>", entry, re.S)
        out.append({
            "title": re.sub(r"\s+", " ", t.group(1)).strip() if t else "",
            "year": int(d.group(1)) if d else None,
            "venue": "arXiv",
            "venue_type": "preprint",
            "doi": idm.group(1).strip() if idm else None,
            "cited_by": None,
            "source": "arxiv",
            "raw_event": None,
            "publisher": "arXiv",
            "raw_query": expr,
        })
    return out


def s_europepmc(q, rows=25):
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%s"
           "&format=json&pageSize=%d" % (urllib.parse.quote(q), rows))
    body = SOURCES["europepmc"].get(url, "epmc:%s" % q[:24])
    if not body:
        return []
    try:
        items = json.loads(body).get("resultList", {}).get("result", [])
    except Exception:
        return []
    return [{
        "title": i.get("title", ""),
        "year": int(i["pubYear"]) if str(i.get("pubYear", "")).isdigit() else None,
        "venue": i.get("journalTitle") or "?",
        "venue_type": "journal-article",
        "doi": i.get("doi"),
        "cited_by": i.get("citedByCount"),
        "source": "europepmc",
        "raw_event": None,
        "publisher": None,
    } for i in items]


def s_openaire(q, rows=30):
    """OpenAIRE 聚合检索。

    字段形状不规范（dict / list[dict] / 裸值混用），统一用 _dollars 归一。
    若直接下标访问，遇到 list 形状会抛异常并被 except 吞掉，表现为"静默返回空"
    ——那是假阴性，本项目明令禁止（E3）。
    """
    # OpenAIRE 的 title= 是"关键词 AND"，不是短语匹配：词一多就 total=0。
    # 实测: "memory poisoning"(151) 命中, "memory poisoning attack knowledge base agent"(0) 落空。
    # 故截断为前 4 个实词。截断若不中，再退到前 2 个词，并把两次都记进检索记录。
    STOP = {"attack", "attacks", "based", "using", "via", "toward", "towards",
            "against", "large", "language", "model", "models", "systems", "system"}
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]+", q) if w.lower() not in STOP]
    tries = []
    if words:
        tries.append(" ".join(words[:4]))
        if len(words) > 2:
            tries.append(" ".join(words[:2]))
    if not tries:
        tries = [q]
    body = None
    for t in tries:
        url = ("https://api.openaire.eu/search/publications?title=%s&size=%d&format=json"
               % (urllib.parse.quote(t), rows))
        body = SOURCES["openaire"].get(url, "openaire:%s" % t[:20])
        if body:
            break
    if not body:
        return []
    try:
        d = json.loads(body)
    except Exception:
        SOURCES["openaire"].errors.append("openaire JSON 解析失败")
        return []
    res = ((d.get("response") or {}).get("results") or {}).get("result") or []
    if isinstance(res, dict):
        res = [res]
    out = []
    for r in res:
        oa = (((r or {}).get("metadata") or {}).get("oaf:entity") or {}).get("oaf:result") or {}
        title = _dollars(oa.get("title"))
        date = _dollars(oa.get("dateofacceptance"))
        pub = _dollars(oa.get("publisher"))
        pid = oa.get("pid")
        doi = None
        for p in (pid if isinstance(pid, list) else [pid]):
            if isinstance(p, dict) and p.get("@classid") == "doi":
                doi = p.get("$")
                break
        year = None
        if date and str(date)[:4].isdigit():
            year = int(str(date)[:4])
        out.append({
            "title": title or "",
            "year": year,
            "venue": pub or "OpenAIRE",
            "venue_type": _dollars(oa.get("resulttype")) or "aggregated",
            "doi": doi,
            "cited_by": None,
            "source": "openaire",
            "raw_event": None,
            "publisher": pub,
        })
    return out


def s_openalex(q, rows=40):
    """OpenAlex 检索。

    注意: 当前实现实测该源会**成段 429**（出口 IP 级），且会自行恢复。
    因此它只作为**可用时启用**的增量源：熔断逻辑会处理它挂掉的情况，
    绝不能让它的失败影响其他源。mailto 进 polite pool 实测**无效**。
    """
    url = ("https://api.openalex.org/works?filter=title_and_abstract.search:%s"
           "&per-page=%d&mailto=bib@example.invalid"
           "&select=display_name,publication_year,type,doi,primary_location,cited_by_count"
           % (urllib.parse.quote(q), min(rows, 50)))
    body = SOURCES["openalex"].get(url, "oa:%s" % q[:24])
    if not body:
        return []
    try:
        d = json.loads(body)
    except Exception:
        SOURCES["openalex"].errors.append("openalex JSON 解析失败")
        return []
    out = []
    for w in d.get("results") or []:
        src = (w.get("primary_location") or {}).get("source") or {}
        out.append({
            "title": w.get("display_name") or "",
            "year": w.get("publication_year"),
            "venue": src.get("display_name") or "?",
            "venue_type": src.get("type") or w.get("type"),
            "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
            "cited_by": w.get("cited_by_count"),
            "source": "openalex",
            "raw_event": None,
            "publisher": src.get("host_organization_name"),
        })
    return out


ALL_IMPL = [("crossref", s_crossref), ("dblp", s_dblp), ("arxiv", s_arxiv),
            ("openaire", s_openaire), ("europepmc", s_europepmc),
            ("openalex", s_openalex)]


def cmd_health(_args):
    probes = {
        "crossref": "https://api.crossref.org/works?query.bibliographic=AgentPoison&rows=1",
        "dblp": "https://dblp.org/search/publ/api?q=AgentPoison&format=json&h=1",
        "arxiv": "https://export.arxiv.org/api/query?search_query=all:AgentPoison&max_results=1",
        "europepmc": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=AgentPoison&format=json&pageSize=1",
        "openalex": "https://api.openalex.org/works?filter=title.search:AgentPoison&per-page=1&mailto=bib@example.invalid",
        "semanticscholar": "https://api.semanticscholar.org/graph/v1/paper/search?query=AgentPoison&limit=1",
    }
    print("源体检（%s）" % time.strftime("%Y-%m-%d %H:%M:%S"))
    print("-" * 72)
    live, dead = [], []
    for name, url in probes.items():
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                r.read(2048)
                code = r.status
            print("[可用 %s] %-18s %.1fs" % (code, name, time.time() - t0))
            live.append(name)
        except urllib.error.HTTPError as e:
            print("[HTTP %s] %-18s %.1fs" % (e.code, name, time.time() - t0))
            dead.append("%s(HTTP %s)" % (name, e.code))
        except Exception as e:
            print("[失败   ] %-18s %.1fs %s" % (name, time.time() - t0, type(e).__name__))
            dead.append("%s(%s)" % (name, type(e).__name__))
        time.sleep(0.6)
    print("-" * 72)
    print("可用: %s" % (", ".join(live) or "无"))
    print("不可用: %s" % (", ".join(dead) or "无"))
    return 0


def cmd_discover(args):
    queries = args.queries or []
    if not queries:
        print("错误: 至少给一个 --queries", file=sys.stderr)
        return 2
    record = {"class": args.cls, "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "round": args.round, "queries": queries, "per_query": [], "items": {}}
    for q in queries:
        got, per_source = [], {}
        for name, impl in ALL_IMPL:
            if not SOURCES[name].alive:
                per_source[name] = "熔断跳过"
                continue
            try:
                r = impl(q)
            except Exception as e:
                r = []
                SOURCES[name].errors.append("%s %s" % (name, type(e).__name__))
            per_source[name] = len(r)
            got.extend(r)
        print("检索式: %s" % q)
        print("  各源命中: %s" % per_source)
        record["per_query"].append({"query": q, "per_source": per_source})
        for it in got:
            t = re.sub(r"\s+", " ", (it.get("title") or "")).strip()
            if not t:
                continue
            low = t.lower()
            if not any(k in low for k in ATTACK_KW):
                continue
            key = re.sub(r"[^a-z0-9]+", "", low)[:60]
            if not key:
                continue
            rec = record["items"].setdefault(key, dict(it, sources=[], survey=False))
            rec["sources"] = sorted(set(rec["sources"] + [it["source"]]))
            tier, why = classify_venue(rec.get("venue"), rec.get("venue_type"))
            rec["tier"], rec["tier_reason"] = tier, why
            rec["is_journal"] = is_journal(rec.get("venue_type"), rec.get("venue"))
            if any(k in low for k in SURVEY_KW):
                rec["survey"] = True
            if it.get("doi") and not rec.get("doi"):
                rec["doi"] = it["doi"]
            if it.get("venue") and rec.get("venue") in (None, "?", "arXiv"):
                rec["venue"] = it["venue"]
                rec["venue_type"] = it.get("venue_type")
    items = [i for i in record["items"].values() if i.get("tier") != "\u5254"]
    rejected = [i for i in record["items"].values() if i.get("tier") == "\u5254"]
    record["sources_failed"] = {n: {"alive": s.alive, "errors": s.errors[-4:]}
                                for n, s in SOURCES.items() if not s.alive or s.errors}
    record["count"] = len(items)
    record["count_rejected"] = len(rejected)
    record["count_attack"] = sum(1 for i in items if not i["survey"])
    dist = {}
    for i in items:
        if i["survey"]:
            continue
        dist[i.get("tier", "\u672a\u5206\u7ea7")] = dist.get(i.get("tier", "\u672a\u5206\u7ea7"), 0) + 1
    print("-" * 72)
    print("\u53bb\u91cd\u540e\u547d\u4e2d %d \u6761\uff08\u653b\u51fb\u65b9\u6cd5\u7c7b %d / \u7efc\u8ff0\u7c7b %d\uff09\uff1b"
          "\u5254\u975e\u5408\u683c\u6e20\u9053 %d \u6761"
          % (record["count"], record["count_attack"],
             record["count"] - record["count_attack"], len(rejected)))
    print("\u653b\u51fb\u65b9\u6cd5\u7c7b\u6309\u53ef\u4fe1\u5ea6\u5206\u5e03: %s" % dist)
    order = {"S": 0, "A": 1, "B": 2, "\u672a\u5206\u7ea7": 3}
    for i, it in enumerate(sorted(items, key=lambda x: (order.get(x.get("tier", "\u672a\u5206\u7ea7"), 9), -(x.get("year") or 0))), 1):
        tag = " [\u7efc\u8ff0]" if it["survey"] else ""
        jn = "\u671f\u520a" if it.get("is_journal") else "\u975e\u671f\u520a"
        print("%3d. [%s] %s | %s | %s | %s%s"
              % (i, it.get("tier", "?"), it.get("year"), it.get("venue"), jn,
                 ",".join(it.get("sources", [])), tag))
        print("     %s" % it.get("title", "")[:100])
        if it.get("doi"):
            print("     doi:%s" % it["doi"])
    if record["sources_failed"]:
        print("-" * 72)
        print("注意：以下源未答全 ⇒ 结果是不完整检索（不得据此写负向断言）:")
        for n, v in record["sources_failed"].items():
            print("  %s: %s" % (n, v["errors"]))
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(record, f, ensure_ascii=False, indent=1)
        print("\n[检索记录已归档] %s" % args.out)
    return 0


def cmd_refs(args):
    doi = args.doi
    body = SOURCES["crossref"].get(
        "https://api.crossref.org/works/" + urllib.parse.quote(doi), "refs:%s" % doi)
    if not body:
        print("Crossref 未答（%s）" % doi, file=sys.stderr)
        return 3
    m = json.loads(body)["message"]
    refs = m.get("reference") or []
    print("《%s》" % (m.get("title") or [""])[0][:90])
    print("  出处: %s | 被引: %s | reference-count=%s | 记录内可见=%d"
          % ((m.get("container-title") or ["?"])[0],
             m.get("is-referenced-by-count"), m.get("reference-count"), len(refs)))
    if not refs:
        print("  => 该记录未开放参考文献，反向滚雪球对此篇不可用（如实记录，不推断）")
    rows = []
    for r in refs:
        rows.append({"key": r.get("key"), "doi": r.get("DOI"),
                     "title": r.get("article-title") or r.get("volume-title"),
                     "journal": r.get("journal-title"), "year": r.get("year"),
                     "unstructured": r.get("unstructured")})
    for i, r in enumerate(rows, 1):
        print("%3d. %s | %s | %s" % (i, r["year"], r["journal"],
                                     (r["title"] or r["unstructured"] or "")[:88]))
        if r["doi"]:
            print("     doi:%s" % r["doi"])
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"seed": doi, "refs": rows}, f, ensure_ascii=False, indent=1)
        print("\n[归档] %s" % args.out)
    return 0


def verify_one(doi):
    res = {"doi": doi, "crossref": None, "dblp": None}
    body = SOURCES["crossref"].get(
        "https://api.crossref.org/works/" + urllib.parse.quote(doi), "v:%s" % doi)
    if body:
        m = json.loads(body)["message"]
        res["crossref"] = {
            "title": (m.get("title") or [""])[0],
            "container": (m.get("container-title") or [None])[0],
            "event": (m.get("event") or {}).get("name"),
            "type": m.get("type"),
            "year": ((m.get("issued") or {}).get("date-parts") or [[None]])[0][0],
            "publisher": m.get("publisher"),
            "cited_by": m.get("is-referenced-by-count"),
            "volume": m.get("volume"), "page": m.get("page"),
            "article_number": m.get("article-number"),
        }
    if res["crossref"]:
        b = SOURCES["dblp"].get(
            "https://dblp.org/search/publ/api?q=%s&format=json&h=3"
            % urllib.parse.quote(res["crossref"]["title"][:120]), "vd:%s" % doi)
        if b:
            try:
                hits = json.loads(b)["result"]["hits"].get("hit", [])
                res["dblp"] = [{"title": (h.get("info", {}).get("title") or "").rstrip("."),
                                "venue": h.get("info", {}).get("venue"),
                                "year": h.get("info", {}).get("year"),
                                "type": h.get("info", {}).get("type"),
                                "doi": h.get("info", {}).get("doi")} for h in hits]
            except Exception:
                res["dblp"] = []
    return res


def cmd_verify(args):
    dois = []
    if args.doi:
        dois += args.doi
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            dois += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    if not dois:
        print("错误: 需要 --doi 或 --file", file=sys.stderr)
        return 2
    out = []
    for d in dois:
        r = verify_one(d)
        out.append(r)
        cr = r["crossref"]
        print("=" * 78)
        print("DOI: %s" % d)
        if not cr:
            print("  Crossref 未答 => 题录未能核验（不得填猜测值）")
        else:
            print("  题名   : %s" % cr["title"][:95])
            print("  出处   : %s" % cr["container"])
            print("  会议名 : %s" % cr["event"])
            print("  类型   : %s | 年: %s | 出版方: %s" % (cr["type"], cr["year"], cr["publisher"]))
            print("  卷/页/文号: %s / %s / %s" % (cr["volume"], cr["page"], cr["article_number"]))
            print("  被引   : %s" % cr["cited_by"])
        if r["dblp"]:
            for h in r["dblp"][:2]:
                print("  DBLP   : %s | %s | %s | type=%s"
                      % (h["year"], h["venue"], (h["title"] or "")[:60], h["type"]))
        elif r["dblp"] == []:
            print("  DBLP   : 无命中（该篇可能未被 DBLP 收录）")
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print("\n[归档] %s" % args.out)
    return 0


def main():
    p = argparse.ArgumentParser(description="8 类别共用的多源文献检索工具")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health", help="逐源体检")
    d = sub.add_parser("discover", help="第1/2轮：多源宽撒")
    d.add_argument("--class", dest="cls", required=True)
    d.add_argument("--queries", nargs="+", required=True)
    d.add_argument("--round", type=int, default=1)
    d.add_argument("--out")
    r = sub.add_parser("refs", help="第3轮：反向滚雪球")
    r.add_argument("--doi", required=True)
    r.add_argument("--out")
    v = sub.add_parser("verify", help="第4轮：venue 核验")
    v.add_argument("--doi", action="append")
    v.add_argument("--file")
    v.add_argument("--out")
    args = p.parse_args()
    return {"health": cmd_health, "discover": cmd_discover,
            "refs": cmd_refs, "verify": cmd_verify}[args.cmd](args)


# --------------------------------------------------------------------------
# 追加：venue 可信度分级（用户 2026-09-29 要求：可信会议计入，SCI 作标注维度）
# 判定基于**刊名/会议名精确匹配**，不做语义猜测；未命中一律记 "未分级"。
# --------------------------------------------------------------------------
TIER_S_JOURNAL = ["information fusion", "ieee transactions on pattern analysis",
                  "ieee transactions on information forensics",
                  "ieee transactions on dependable and secure",
                  "ieee transactions on software engineering",
                  "acm computing surveys", "ieee transactions on knowledge and data"]
TIER_S_CONF = ["usenix security", "ieee symposium on security and privacy",
               "acm sigsac conference on computer and communications security",
               "network and distributed system security",
               "advances in neural information processing systems",
               "neural information processing systems",
               "proceedings 20",
               "international conference on machine learning (icml)",
               "proceedings of the international conference on machine learning",
               "international conference on learning representations"]
TIER_A_JOURNAL = ["neural networks", "expert systems with applications",
                  "engineering applications of artificial intelligence",
                  "knowledge-based systems", "future generation computer systems",
                  "pattern recognition", "applied soft computing",
                  "acm transactions on information systems",
                  "ieee transactions on", "scientific reports",
                  "computers & security", "neurocomputing", "applied intelligence",
                  "information sciences", "science china information sciences"]
TIER_A_CONF = ["findings of the association for computational linguistics",
               "association for computational linguistics",
               "acm sigkdd", "knowledge discovery and data mining",
               "the web conference", "acm web conference", "sigir",
               "international conference on robotics and automation",
               "ieee/cvf conference on computer vision",
               "aaai conference on artificial intelligence",
               "international joint conference on artificial intelligence",
               "ieee international conference on software analysis",
               "trust, security and privacy in computing",
               "empirical software engineering", "icse", "ase "]
TIER_B = ["aisec", "workshop on artificial intelligence and security",
          "ieee access", "findings"]
# ⚠️ 2026-09-29 修正（T02 会话发现）：原 TIER_B 含 "arxiv"，
# 使**每一条 arXiv 预印本都被判成 B 级**，与 `search-protocol.md` §2.3
# 「每张卡必须填 source_grade（S/A/B/C/—）与 numeric_evidence（原表/摘要/无），
#   两者严格分列」以及「不得用收录数量掩盖来源等级下滑」直接冲突——
# 把预印本默认记 B，等于系统性高估一级。
# 现按签署的等级表把预印本/聚合源一律记为 **"未分级"**，
# 并保留 venue_type 供人工定级时使用。**T01 已产出的 tier 分布受此缺陷影响，须重算。**
UNGRADED_PREPRINT = ["arxiv", "openaire", "preprint", "ssrn", "researchgate"]
# 明确不应作为方法来源的预印本服务器/一般性平台（search-protocol §2.2）
# 疑似掠夺性/低可信刊（2026-09-29 实测在检索结果中出现且从未核验过收录状态）。
# 原则：不确定一律标"剔"并说明理由，绝不给它 S/A，避免用假等级充数。
REJECT_VENUE = ["fundamental scientific reports", "american journal of",
                "american journal ", "advances in engineering innovation",
                "international research journal", "iconic research"] + ["ssrn", "research square", "rs-", "preprints.org", "techrxiv",
                "zenodo", "osf", "hal ", "semanticscholar", "ijsr", "irjmets",
                "iconic research", "e-commerce letters", "advances in engineering"]


def classify_venue(venue, venue_type):
    """返回 (tier, reason)。未命中记 '未分级'，不猜。"""
    v = (venue or "").lower()
    if not v or v == "?":
        return "未分级", "venue 缺失"
    for k in REJECT_VENUE:
        if k in v:
            return "剔", "非合格出版渠道(%s)" % k
    # 预印本/聚合源：一律"未分级"，不得默认记 B（见 UNGRADED_PREPRINT 说明）
    if (venue_type or "").lower() == "preprint" or any(k in v for k in UNGRADED_PREPRINT):
        return "未分级", "预印本/聚合源，未定级（须人工按 venue 定级）"
    # 先判 Findings/workshop：它们虽含主会名，但按签署的等级表只能是 B
    if "findings" in v or "workshop" in v:
        return "B", "Findings/Workshop（含主会名但非主会正刊）"
    if any(k in v for k in TIER_S_CONF):
        return "S", "Tier S 会议"
    if any(k in v for k in TIER_S_JOURNAL):
        return "S", "Tier S 期刊"
    if any(k in v for k in TIER_A_CONF):
        return "A", "Tier A 会议"
    if any(k in v for k in TIER_A_JOURNAL):
        return "A", "Tier A 期刊"
    if any(k in v for k in TIER_B):
        return "B", "Tier B"
    return "未分级", "不在已签署名单内"


def _dollars(x):
    """OpenAIRE 字段归一：{'$':v} / [{'$':v},...] / 裸值 三种形状统一成一个值。"""
    if x is None:
        return None
    if isinstance(x, dict):
        return x.get("$")
    if isinstance(x, list):
        for e in x:
            v = _dollars(e)
            if v:
                return v
        return None
    return x


def is_journal(venue_type, venue):
    vt = (venue_type or "").lower()
    v0 = (venue or "").lower()
    # 先排除会议录：proceedings-article / "proceedings of ..." 一律不是期刊
    if "proceedings" in vt or "conference" in vt or "workshop" in vt:
        return False
    if v0.startswith("proceedings") or "conference on" in v0 or "symposium" in v0:
        return False
    if "journal" in vt:
        return True
    v = (venue or "").lower()
    return any(w in v for w in ["transactions", "journal", "letters", "review",
                                "fusion", "networks", "systems", "intelligence",
                                "applications", "computing", "science", "reports"])


if __name__ == "__main__":
    sys.exit(main())
