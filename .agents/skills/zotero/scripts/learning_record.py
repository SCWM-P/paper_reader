"""A bounded prerequisite route for one paper passage; no inferred mastery."""
from __future__ import annotations

from copy import deepcopy
import re
from urllib.parse import urlsplit

STATES = {
    "unknown": "需要补习", "uncertain": "不确定", "explained": "已讲解，待确认",
    "confirmed": "作答已确认", "skipped": "已跳过，未确认",
}
SOURCE_KINDS = {
    "paper": "论文原文 / 概述", "background": "外部背景",
    "teaching": "教学示例", "inference": "教学推断",
}
NEXT_ACTIONS = {
    "check": "完成简短自测", "continue_prerequisite": "继续补一个先修",
    "return_to_paper": "返回原文",
}


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonempty text")
    return value


def _choice(value, choices, field):
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{field} must be one of: {', '.join(choices)}")


def _url(value, field):
    _text(value, field)
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https", "zotero") or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{field} must be an http(s)/zotero URL without credentials")


def _texts(value, field):
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list of text")
    for item in value:
        _text(item, field)


def _route_issues(concepts, budget):
    """Inspect each bounded node/edge once; keep representative diagnostics, not all paths."""
    visible = concepts[:budget["max_nodes"]]
    nodes = {c["id"]: c for c in visible}
    edges = {c["id"]: c["depends_on"][:budget["max_nodes"]] for c in visible}
    issues = []
    if len(concepts) > len(visible):
        issues.append(f"节点预算已耗尽：{len(concepts)} 个概念中只展开前 {len(visible)} 个。")
    oversized = [c["id"] for c in visible if len(c["depends_on"]) > budget["max_nodes"]]
    if oversized:
        issues.append("先修列表超过节点预算：" + "、".join(oversized))
    colors, longest, active, missing, cycle = {}, {}, [], [], []

    def visit(key):
        colors[key] = 1
        active.append(key)
        best = [key]
        for dependency in edges[key]:
            if dependency not in nodes:
                missing.append(key + " → " + dependency)
                continue
            if colors.get(dependency) == 1:
                if not cycle:
                    cycle.extend(active[active.index(dependency):] + [dependency])
                continue
            # Memoize one longest route. Back edges stop here; cycles are reported separately.
            tail = longest[dependency] if colors.get(dependency) == 2 else visit(dependency)
            if len(tail) + 1 > len(best):
                best = [key] + tail
        active.pop()
        colors[key] = 2
        longest[key] = best
        return best

    for key in nodes:
        if key not in colors:
            visit(key)
    if missing:
        sample = "；".join(missing[:3])
        suffix = f"（共 {len(missing)} 处，仅列前三处）" if len(missing) > 3 else ""
        issues.append("先修依赖未闭合：" + sample + suffix)
    if cycle:
        issues.append("先修存在循环，例如：" + " → ".join(cycle) + "（停止循环展开）。")
    deepest = max(longest.values(), key=len, default=[])
    if len(deepest) - 1 > budget["max_depth"]:
        issues.append("先修深度预算已耗尽，例如：" + " → ".join(deepest) +
                      f"（最多追溯 {budget['max_depth']} 层）。")
    for concept in visible:
        if concept["state"] != "confirmed":
            issues.append(f"理解尚未确认：{concept['term']}（{STATES[concept['state']]}）。")
    return issues


def normalize_learning(value):
    if not isinstance(value, dict):
        raise ValueError("learning must be an object")
    result = deepcopy(value)
    version = result.setdefault("version", 1)
    if type(version) is not int or version != 1:
        raise ValueError("learning.version must be 1")
    anchor = result.get("anchor")
    if not isinstance(anchor, dict):
        raise ValueError("learning.anchor must preserve the original passage")
    for field in ("locator", "excerpt"):
        _text(anchor.get(field), "learning.anchor." + field)
    if "page" in anchor and (type(anchor["page"]) is not int or anchor["page"] < 1):
        raise ValueError("learning.anchor.page must be a positive physical PDF page")
    if "url" in anchor:
        _url(anchor["url"], "learning.anchor.url")
    reader = result.get("reader")
    if not isinstance(reader, dict):
        raise ValueError("learning.reader must contain the starting point and its basis")
    _text(reader.get("starting_point"), "learning.reader.starting_point")
    _choice(reader.get("basis"), ("assumed", "user_report"), "learning.reader.basis")
    _text(result.get("goal"), "learning.goal")
    budget = result.setdefault("budget", {"max_depth": 2, "max_nodes": 5})
    if not isinstance(budget, dict):
        raise ValueError("learning.budget must be an object")
    for field, upper in (("max_depth", 3), ("max_nodes", 8)):
        if type(budget.get(field)) is not int or not 1 <= budget[field] <= upper:
            raise ValueError(f"learning.budget.{field} must be an integer from 1 to {upper}")
    concepts = result.get("concepts")
    if not isinstance(concepts, list):
        raise ValueError("learning.concepts must be a list")
    ids = set()
    for concept in concepts:
        if not isinstance(concept, dict):
            raise ValueError("Each learning concept must be an object")
        key = _text(concept.get("id"), "concept.id")
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", key) or key in ids:
            raise ValueError("Concept ids must be unique lowercase slugs (max 64 characters)")
        ids.add(key)
        _text(concept.get("term"), "concept.term")
        _choice(concept.get("state"), STATES, "concept.state")
        dependencies = concept.setdefault("depends_on", [])
        _texts(dependencies, "concept.depends_on")
        if len(set(dependencies)) != len(dependencies):
            raise ValueError("concept.depends_on must not contain duplicates")
        for key in dependencies:
            if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", key):
                raise ValueError("concept.depends_on must use concept ids")
        if "revision" in concept:
            _text(concept["revision"], "concept.revision")
        lesson = concept.setdefault("lesson", [])
        if not isinstance(lesson, list):
            raise ValueError("concept.lesson must be a list of attributed blocks")
        for block in lesson:
            if not isinstance(block, dict):
                raise ValueError("Each lesson block must be an object")
            _choice(block.get("kind"), SOURCE_KINDS, "lesson.kind")
            for field in ("title", "text"):
                _text(block.get(field), "lesson." + field)
            if block["kind"] in ("paper", "background"):
                _text(block.get("locator"), "lesson.locator")
            if "url" in block:
                _url(block["url"], "lesson.url")
        if concept["state"] == "explained" and not lesson:
            raise ValueError("An explained concept requires lesson content")
        check = concept.get("check")
        if "check" in concept:
            if not isinstance(check, dict):
                raise ValueError("concept.check must be an object")
            for field in ("question", "reference_answer"):
                _text(check.get(field), "check." + field)
            _choice(check.setdefault("assessment", "pending"), ("pending", "retry", "pass"), "check.assessment")
            for field in ("user_answer", "feedback"):
                if field in check:
                    _text(check[field], "check." + field)
            if check["assessment"] != "pending":
                for field in ("user_answer", "feedback"):
                    _text(check.get(field), "check." + field)
        if concept["state"] == "confirmed" and (not check or check["assessment"] != "pass"):
            raise ValueError("Confirmation requires a recorded user answer and passing feedback")
    unresolved = result.setdefault("unresolved", [])
    _texts(unresolved, "learning.unresolved")
    # Derived issues are recomputed after correction; never persist a stale mastery warning.
    result["unresolved"] = list(dict.fromkeys(unresolved))
    result["issues"] = _route_issues(concepts, budget)
    next_step = result.get("next")
    if not isinstance(next_step, dict):
        raise ValueError("learning.next must record how to resume")
    _choice(next_step.get("action"), NEXT_ACTIONS, "learning.next.action")
    _text(next_step.get("reason"), "learning.next.reason")
    return result
