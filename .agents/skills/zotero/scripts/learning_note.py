"""Shared offline teaching presentation for HTML pages and searchable summaries."""
from __future__ import annotations

import html
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from .learning_record import STATES, SOURCE_KINDS, NEXT_ACTIONS


def _text(value):
    return html.escape(str(value), quote=True).replace("\n", "<br>")


def _anchor_link(anchor, paper_url):
    url = paper_url or anchor.get("url")
    if not url:
        return ""
    parsed = urlsplit(url)
    if parsed.scheme:
        if parsed.scheme not in ("http", "https", "zotero") or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Learning source must be an http(s)/zotero URL without credentials")
    elif parsed.netloc or parsed.path.startswith("/") or ".." in parsed.path.split("/"):
        raise ValueError("Learning PDF must use an archive-relative path")
    if anchor.get("page"):
        if parsed.scheme == "zotero":
            query = [(k, v) for k, v in parse_qsl(parsed.query) if k != "page"]
            parsed = parsed._replace(query=urlencode(query + [("page", str(anchor["page"]))]))
        else:
            parsed = parsed._replace(fragment="page=" + str(anchor["page"]))
    return '<a href="' + _text(urlunsplit(parsed)) + '">打开卡点原文</a>'


def learning_content(learning, paper_url=None, compact=False):
    """Render validated learning data. Displaying or opening a page never confirms understanding."""
    anchor, reader = learning["anchor"], learning["reader"]
    location = anchor["locator"] + (f" · PDF 物理页 {anchor['page']}" if anchor.get("page") else "")
    source = _anchor_link(anchor, paper_url)
    basis = "用户自述" if reader["basis"] == "user_report" else "暂定起点，待用户纠正"
    parts = ['<div class="learning-session">', '<div class="learning-anchor"><h4>当前原文卡点</h4>',
             '<p>' + _text(location) + ' ' + source + '</p><blockquote>' + _text(anchor["excerpt"]) + '</blockquote></div>',
             '<p><strong>理解目标：</strong>' + _text(learning["goal"]) + '</p>',
             '<p><strong>已知起点（' + basis + '）：</strong>' + _text(reader["starting_point"]) + '</p>']
    budget = learning["budget"]
    parts.append(f'<p class="learning-budget">本轮最多展开 {budget["max_nodes"]} 个概念，沿先修关系最多追溯 {budget["max_depth"]} 层。</p>')
    unresolved = list(dict.fromkeys(learning["unresolved"] + learning["issues"]))
    if unresolved:
        parts.append('<aside class="learning-unresolved"><h4>待确认与未解决项</h4><ul>' +
                     ''.join('<li>' + _text(x) + '</li>' for x in unresolved[:16]) + '</ul>')
        if len(unresolved) > 16:
            parts.append(f'<p class="learning-budget">另有 {len(unresolved) - 16} 条，完整内容保留在阅读记录 JSON。</p>')
        parts.append('</aside>')
    names = {c["id"]: c["term"] for c in learning["concepts"]}
    for concept in learning["concepts"][:budget["max_nodes"]]:
        state = concept["state"]
        parts.append('<article class="learning-concept"><h4>' + _text(concept["term"]) + '</h4>' +
                     '<p class="learning-state" data-state="' + state + '">' + STATES[state] + '</p>')
        if concept["depends_on"]:
            dependencies = concept["depends_on"][:budget["max_nodes"]]
            parts.append('<p><strong>必要先修：</strong>' + _text('、'.join(names.get(k, k + '（待补）') for k in dependencies)) + '</p>')
            if len(concept["depends_on"]) > len(dependencies):
                parts.append('<p class="learning-budget">其余先修超出本轮节点预算，尚未展开。</p>')
        if concept.get("revision"):
            parts.append('<p><strong>状态修正：</strong>' + _text(concept["revision"]) + '</p>')
        for block in concept["lesson"]:
            label = SOURCE_KINDS[block["kind"]]
            parts.append('<div class="learning-block"><p class="learning-source">' + label + '</p><p><strong>' +
                         _text(block["title"]) + '</strong></p><p>' + _text(block["text"]) + '</p>')
            if block.get("locator"):
                locator = _text(block["locator"])
                if block.get("url"):
                    locator = '<a href="' + _text(block["url"]) + '">' + locator + '</a>'
                parts.append('<p class="learning-locator">' + locator + '</p>')
            parts.append('</div>')
        check = concept.get("check")
        if check:
            parts.append('<div class="learning-check"><p><strong>自测：</strong>' + _text(check["question"]) + '</p>')
            reference = '<p>' + _text(check["reference_answer"]) + '</p>'
            if compact:
                parts.append('<p><strong>自测参考解答：</strong></p>' + reference)
            else:
                parts.append('<details class="learning-reference"><summary>查看参考解答</summary>' + reference + '</details>')
            if check.get("user_answer"):
                parts.append('<p><strong>用户实际作答：</strong>' + _text(check["user_answer"]) + '</p>')
            assessment = {"pending": "待作答 / 待评价", "retry": "需要再试", "pass": "上次作答通过"}[check["assessment"]]
            parts.append('<p><strong>自测记录：</strong>' + assessment + '</p>')
            if check.get("feedback"):
                parts.append('<p><strong>反馈：</strong>' + _text(check["feedback"]) + '</p>')
            parts.append('</div>')
        parts.append('</article>')
    step = learning["next"]
    parts.append('<div class="learning-resume"><p><strong>下一步：</strong>' + NEXT_ACTIONS[step["action"]] +
                 '。' + _text(step["reason"]) + '</p><p>返回位置：' + _text(location) + ' ' + source + '</p></div></div>')
    return ''.join(parts)
