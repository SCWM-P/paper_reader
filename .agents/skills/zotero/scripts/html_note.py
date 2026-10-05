#!/usr/bin/env python3
"""Render portable offline reading HTML using bundled or LLM-authored templates."""
from __future__ import annotations
import argparse
import base64
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import quote
from reading_record import normalize_record, author_names

ASSETS = Path(__file__).resolve().parents[1] / "assets"
THEMES = {"modern": "现代伴读", "tufte": "Tufte 旁注", "latex": "LaTeX 学术", "github": "GitHub 简洁"}


def math_assets():
    """Inline KaTeX and its WOFF2 fonts so exported pages also work offline."""
    vendor = ASSETS / "vendor/katex"
    css = (vendor / "katex.min.css").read_text(encoding="utf-8")
    def font_src(match):
        url = re.search(r'url\(([^)]+\.woff2)\)', match[0])
        if not url:
            raise ValueError("KaTeX font has no WOFF2 source")
        font = vendor / url[1].strip("\"'")
        return 'src:url(data:font/woff2;base64,' + base64.b64encode(font.read_bytes()).decode() + ') format("woff2");'
    # Minified @font-face rules may end without a semicolon; stop at the closing brace.
    css = re.sub(r"src:[^;}]+;?", font_src, css)
    js = (vendor / "katex.min.js").read_text(encoding="utf-8") + "\n" + (vendor / "contrib/auto-render.min.js").read_text(encoding="utf-8")
    return css, js, (vendor / "LICENSE.txt").read_text(encoding="utf-8")


def asset_uri(path, mime, output_base=None):
    """Inline Zotero resources or link to an existing file inside a paper archive."""
    path = Path(path).resolve(strict=True)
    if output_base is None:
        return "data:" + mime + ";base64," + base64.b64encode(path.read_bytes()).decode()
    root = Path(output_base).resolve()
    path.relative_to(root)
    return quote(Path(os.path.relpath(path, root)).as_posix(), safe="/")


def visual_content(record, asset_base, output_base=None):
    figures = []
    for f in record.get("figures", []):
        caption = html.escape(str(f.get("caption", "论文插图")))
        source = ""
        if record.get("paper", {}).get("pdf_url"):
            source = '<a href="' + html.escape(record['paper']['pdf_url'], quote=True) + '#page=' + str(f.get('page', 1)) + '">PDF p.' + str(f.get('page', 1)) + '</a>'
        elif f.get("attachment_key") and record.get("paper", {}).get("library", "users/0") == "users/0":
            key, page = f["attachment_key"], f.get("page", 1)
            if not re.fullmatch("[A-Z0-9]{8}", key) or not isinstance(page, int) or isinstance(page, bool) or page < 1:
                raise ValueError("Figure source requires a valid attachment key and positive PDF page")
            source = f'<a href="{safe_url(f"zotero://open-pdf/library/items/{key}?page={page}")}">PDF p.{page}</a>'
        elif f.get("url"):
            source = f'<a href="{safe_url(f["url"])}">原文出处</a>'
        if f.get("file"):
            path = Path(f["file"]).expanduser()
            path = path if path.is_absolute() else Path(asset_base or ".") / path
            mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(path.suffix.lower())
            if not mime:
                raise ValueError("Figure files support PNG/JPEG/WebP; render PDF vectors as PNG")
            uri = asset_uri(path, mime, output_base)
            image = f'<button class="figure-zoom" type="button" aria-label="放大插图"><img src="{uri}" alt="{html.escape(str(f.get("alt", f.get("caption", "论文插图"))), quote=True)}" loading="lazy"></button>'
        elif source:
            image = '<p>原图可从以下出处打开。</p>'
        else:
            raise ValueError("Figure requires an extracted file or source link")
        figures.append(f'<figure class="paper-figure">{image}<figcaption><strong>{caption}</strong> {source}{paragraph(f.get("explanation", ""))}</figcaption></figure>')
    equations = []
    for equation in record.get("equations", []):
        tex = str(equation["latex"])
        equations.append('<div class="equation-card"><h3>' + html.escape(str(equation.get("title", "公式")))
                         + '</h3><div class="math-block">\\[' + html.escape(tex) + '\\]</div>'
                         + paragraph(equation.get("explanation", "")) + '</div>')
    widgets = []
    for kind in record.get("visualizations", []):
        if kind not in ("attention", "transformer"):
            raise ValueError("Supported visualizations: attention, transformer; authored HTML can add others")
        widgets.append(f'<div class="visual-lab" data-visualization="{kind}"></div>')
    return "".join(figures), "".join(equations), "".join(widgets)


def safe_url(value):
    from urllib.parse import urlsplit
    p = urlsplit(value)
    if p.scheme not in ("https", "http", "zotero") or not p.netloc or p.username or p.password:
        raise ValueError("Links must be http(s)/zotero without credentials")
    return html.escape(value, quote=True)


def paragraph(value):
    return "".join("<p>" + html.escape(part).replace("\n", "<br>") + "</p>"
                   for part in str(value).split("\n\n") if part.strip())


def section(name, title, number, content):
    return f'<section id="{name}"><h2><span class="section-number">{number:02d}</span>{title}</h2>{content}</section>'


def evidence_content(record, entries, theme, compact=False):
    evidence = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("claim") or not entry.get("locator"):
            raise ValueError("Evidence requires claim and locator")
        locator = html.escape(str(entry["locator"]))
        if entry.get("url"):
            locator = f'<a href="{safe_url(entry["url"])}">{locator}</a>'
        if record.get('paper', {}).get('pdf_url') and entry.get('attachment_key') == record['paper'].get('pdf_key'):
            url = record['paper']['pdf_url'] + (f"#page={entry['page']}" if entry.get('page') else '')
            locator = '<a href="' + html.escape(url, quote=True) + '">' + locator + '</a>'
        elif entry.get("attachment_key") and record.get("paper", {}).get("library", "users/0") == "users/0":
            key, page = entry["attachment_key"], entry.get("page")
            if not re.fullmatch("[A-Z0-9]{8}", key):
                raise ValueError("Invalid evidence attachment key")
            if page is not None and (not isinstance(page, int) or isinstance(page, bool) or page < 1):
                raise ValueError("page must be a positive 1-based integer")
            url = f"zotero://open-pdf/library/items/{key}" + (f"?page={page}" if page else "")
            locator = f'<a href="{safe_url(url)}">{locator}</a>'
        location_class = "sidenote evidence-label" if theme == "tufte" else "evidence-label"
        evidence.append('<div class="evidence-item">' + ('' if compact else paragraph(entry["claim"]))
                        + f'<span class="{location_class}">{locator}</span></div>')
    return "".join(evidence)


def text_content(value):
    if isinstance(value, list):
        return '<ul>' + ''.join('<li>' + html.escape(str(x)) + '</li>' for x in value) + '</ul>'
    if isinstance(value, dict):
        return '<dl class="extra-fields">' + ''.join('<dt>'+html.escape(str(k))+'</dt><dd>'+paragraph(v)+'</dd>' for k,v in value.items()) + '</dl>'
    return paragraph(value)


def metadata_content(metadata):
    names = author_names(metadata)
    rows = []
    labels = {"date":"发表时间","publicationTitle":"期刊","proceedingsTitle":"论文集","conferenceName":"会议",
              "volume":"卷","issue":"期","pages":"页码","publisher":"出版社","place":"出版地",
              "DOI":"DOI","ISBN":"ISBN","repository":"预印本平台","archiveID":"文献标识","itemType":"文献类型","url":"来源"}
    for key,label in labels.items():
        if not metadata.get(key):
            continue
        value = html.escape(str(metadata[key]))
        if key == "url":
            value = f'<a href="{safe_url(str(metadata[key]))}">打开论文来源</a>'
        elif key == "DOI":
            from urllib.parse import quote
            value = f'<a href="{safe_url("https://doi.org/"+quote(str(metadata[key]),safe="/"))}">{value}</a>'
        rows.append(f'<div><dt>{label}</dt><dd>{value}</dd></div>')
    raw = html.escape(json.dumps(metadata,ensure_ascii=False,indent=2))
    return '<div class="paper-metadata"><p class="lab-badge">PUBLICATION RECORD</p><h3>'+html.escape(str(metadata['title']))+'</h3><div class="author-list">'+''.join('<span>'+html.escape(n)+'</span>' for n in names)+'</div><dl class="metadata-grid">'+''.join(rows)+'</dl><details><summary>查看完整采集元数据</summary><pre>'+raw+'</pre></details></div>'


def build_body(record, theme, asset_base=None, output_base=None):
    metadata = metadata_content(record['metadata'])
    contributions = []
    for i, entry in enumerate(record['highlights']):
        if isinstance(entry, str):
            title, content = f'贡献 {i+1}', entry
        elif isinstance(entry, dict):
            title, content = entry.get('title',f'贡献 {i+1}'), entry.get('content', '')
        else:
            raise ValueError('highlights entries must be text or title/content objects')
        contributions.append('<article class="highlight-card"><span class="highlight-index">'+f'{i+1:02d}'+'</span><h3>'+html.escape(str(title))+'</h3>'+paragraph(content)+(evidence_content(record,entry.get('evidence',[]),theme,compact=True) if isinstance(entry,dict) else '')+'</article>')
    highlights = '<div class="highlight-grid">'+''.join(contributions)+'</div>' if contributions else '<p class="module-empty">主要贡献待本次阅读补充。</p>'
    qa = []
    for i, entry in enumerate(record['Q & A']):
        origin = str(entry.get('origin', '伴读讨论'))
        qa.append('<details class="qa-card" open><summary><span class="qa-index">Q'+str(i+1)+'</span><span>'+html.escape(entry['question'])+'</span></summary><div class="qa-answer"><span class="qa-origin">'+html.escape(origin)+'</span>'+paragraph(entry.get('answer') or '待下一次讨论继续解答。')+evidence_content(record,entry.get('evidence',[]),theme,compact=True)+'</div></details>')
    questions = '<div class="qa-tools"><label>查找讨论 <input type="search" class="qa-search" placeholder="问题或解答中的关键词"></label><button type="button" class="qa-expand">展开全部</button><button type="button" class="qa-collapse">收起全部</button><span class="qa-count" aria-live="polite"></span></div><div class="qa-list">'+''.join(qa)+'</div>' if qa else '<p class="module-empty">本次交流尚未登记问答；后续讨论可持续追加。</p>'
    blocks=[('metadata','文献元数据',metadata),('summary','阅读结论','<div class="summary-callout">'+paragraph(record['summary'])+'</div>'),('highlights','学术价值与贡献',highlights),('qa','伴读 Q & A',questions)]
    extensions=[];anchors=[];used={'metadata','summary','highlights','qa','others'}
    for i, entry in enumerate(record.get('others', [])):
        key = str(entry.get('id',f'extension-{i+1}'))
        if not re.fullmatch('[a-z][a-z0-9-]*',key) or key in used:
            key=f'extension-{i+1}'
            while key in used: key+='-extra'
        used.add(key)
        title = str(entry.get('title','扩展阅读'))
        content = text_content(entry.get('content',''))
        figures, equations, visuals = visual_content(dict(entry,paper=record.get('paper',{})),asset_base,output_base)
        content += figures+equations+visuals+evidence_content(record,entry.get('evidence',[]),theme)
        if entry.get('code'):
            content += '<div class="code-panel"><div class="code-toolbar"><span>'+html.escape(str(entry.get('language','code')))+'</span><button class="copy-code" type="button">复制代码</button><span class="copy-status" aria-live="polite"></span></div><pre><code>'+html.escape(str(entry['code']))+'</code></pre></div>'
        for video in entry.get('videos',[]):
            if video.get('file'):
                path = Path(video['file']).expanduser()
                path = path if path.is_absolute() else Path(asset_base or '.') / path
                mime = {'.mp4':'video/mp4','.webm':'video/webm','.ogv':'video/ogg'}.get(path.suffix.lower())
                if not mime: raise ValueError('Video files support MP4/WebM/OGV')
                uri=asset_uri(path,mime,output_base)
                content += '<figure class="video-panel"><video controls preload="none" playsinline src="'+uri+'"></video><figcaption>'+html.escape(str(video.get('caption','教学视频')))+'</figcaption></figure>'
            elif video.get('url'):
                content += '<p><a href="'+safe_url(video['url'])+'">'+html.escape(str(video.get('caption','观看视频')))+'</a></p>'
        for link in entry.get('links',[]):
            content += '<p class="extension-link"><a href="'+safe_url(link['url'])+'">'+html.escape(str(link.get('label',link['url'])))+'</a></p>'
        if entry.get('html_file'):
            path=Path(entry['html_file']).expanduser()
            path=path if path.is_absolute() else Path(asset_base or '.')/path
            content += path.read_text(encoding='utf-8-sig')
        content += str(entry.get('html',''))
        # Preserve new, named extension data even without a predefined renderer.
        extra={k:v for k,v in entry.items() if k not in {'id','title','content','figures','equations','visualizations','evidence','code','language','videos','links','html_file','html'}}
        if extra: content += text_content(extra)
        extensions.append('<section class="extension-panel" id="'+key+'"><h3>'+html.escape(title)+'</h3>'+content+'</section>')
        anchors.append(f'<a class="extension-nav" href="#{key}">{html.escape(title)}</a>')
    if extensions: blocks.append(('others','扩展阅读',''.join(extensions)))
    body='\n'.join(section(key,title,i+1,content) for i,(key,title,content) in enumerate(blocks))
    toc=''.join(f'<a href="#{key}">{title}</a>' for key,title,_ in blocks)+''.join(anchors)
    return body,toc


def render(record, theme="modern", template_file=None, css_file=None, body_file=None, asset_base=None, output_base=None):
    if not isinstance(record, dict) or not isinstance(record.get("paper", {}), dict):
        raise ValueError("Reading record and optional paper must be JSON objects")
    if theme not in THEMES:
        raise ValueError("Unknown theme")
    record = normalize_record(record)
    if output_base is not None and record.get('paper', {}).get('file'):
        record['paper']['pdf_url'] = asset_uri(Path(asset_base or '.') / record['paper']['file'], 'application/pdf', output_base)
    body, toc = build_body(record, theme, asset_base, output_base)
    modules={}
    for key in ('metadata','summary','highlights','qa','others'):
        found=re.search(r'<section id="'+key+r'">(.*?)(?=\n<section id=|\Z)',body,re.S)
        modules[key.upper()+'_HTML']=found[0] if found else ''
    figures=equations=visuals=''
    for entry in record['others']:
        f,e,v=visual_content(dict(entry,paper=record.get('paper',{})),asset_base,output_base)
        figures+=f;equations+=e;visuals+=v
    if body_file:
        # Explicit authored HTML, not untrusted text copied out of a PDF.
        body = Path(body_file).read_text(encoding="utf-8-sig")
        for name, content in (("FIGURES_HTML", figures), ("EQUATIONS_HTML", equations), ("VISUALS_HTML", visuals)):
            body = body.replace("{{" + name + "}}", content)
        # Core modules can be retained when the LLM authors an extended layout.
        for key in ('metadata','summary','highlights','qa','others'):
            body=body.replace('{{'+key.upper()+'_HTML}}',modules[key.upper()+'_HTML'])
        if re.search(r'<(?:html|head|body)\b', body, re.I):
            raise ValueError("--body-file must contain an HTML fragment; use --template-file for full document")
        toc = "".join(f'<a href="#{html.escape(key, quote=True)}">{html.escape(re.sub("<[^>]+>", "", title))}</a>'
                      for key, title in re.findall(r'<section\b[^>]*id=[\"\x27]([^\"\x27]+)[\"\x27][^>]*>\s*<h2[^>]*>(.*?)</h2>', body, re.S | re.I))
    math_css, math_js, math_license = math_assets()
    css, notices = math_css, [math_license]
    if theme != "modern":
        vendor = ASSETS / "vendor" / theme
        css += "\n" + (vendor / "style.css").read_text(encoding="utf-8")
        # Keep embedded KaTeX fonts; remove external theme fonts.
        css = re.sub(r"@font-face\s*\{(?![^}]*data:)[^}]*\}", "", css, flags=re.S | re.I)
        css = re.sub(r"@import[^;]+;", "", css, flags=re.I)
        notices.append((vendor / "LICENSE.txt").read_text(encoding="utf-8"))
    css += "\n" + (ASSETS / "templates/reading-note.css").read_text(encoding="utf-8")
    if css_file:
        css += "\n" + Path(css_file).read_text(encoding="utf-8-sig")
    if re.search(r"</style", css, re.I):
        raise ValueError("CSS cannot contain a closing style tag")
    template = Path(template_file) if template_file else ASSETS / "templates/reading-note.html"
    template = template.read_text(encoding="utf-8-sig")
    if "{{BODY_HTML}}" not in template or "{{TITLE}}" not in template:
        raise ValueError("Custom template must include {{TITLE}} and {{BODY_HTML}}")
    title = str(record.get("title", "文献阅读笔记"))
    paper = record.get("paper", {})
    source = ""
    if paper.get("select_uri"):
        source = f'<a href="{safe_url(paper["select_uri"])}">返回 Zotero 文献</a>'
    elif paper.get("url"):
        source = f'<a href="{safe_url(paper["url"])}">论文来源</a>'
    if paper.get('pdf_url'):
        source = '<a href="' + html.escape(paper['pdf_url'], quote=True) + '">打开原文 PDF</a> · ' + source
    meta = [record.get("recorded_at", "未记录时间"), record.get("note_author", record.get("author", "AI 伴读")), record['metadata'].get("date", "")]
    data_json = json.dumps(record, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    values = {"TITLE": html.escape(title), "LANG": html.escape(str(record.get("lang", "zh-CN")), quote=True),
              "DESCRIPTION": html.escape(record["summary"][:160], quote=True), "THEME": theme, "THEME_LABEL": THEMES[theme],
              "KICKER": "Reading note / 文献伴读", "SUBTITLE": html.escape(str(record.get("subtitle", record['metadata']['title']))),
              "META_HTML": "".join("<span>" + html.escape(str(m)) + "</span>" for m in meta if m),
              "BODY_HTML": body, "TOC_HTML": toc, "STYLE_CSS": css, "SOURCE_LINK_HTML": source,
              "DATA_JSON": data_json, "MATH_JS": math_js,
              "FIGURES_HTML": figures, "EQUATIONS_HTML": equations, "VISUALS_HTML": visuals,
              "BEHAVIOR_JS": math_js + "\n" + (ASSETS / "templates/reading-visuals.js").read_text(encoding="utf-8") + "\n" + (ASSETS / "templates/reading-note.js").read_text(encoding="utf-8"),
              "LICENSE_NOTICE": "\n".join("<!-- Third-party style license:\n" + n.replace("--", "—") + "\n-->" for n in notices)}
    values.update(modules)
    tokens = set(re.findall(r"\{\{([A-Z_]+)\}\}", template))
    unknown = tokens - set(values)
    if unknown:
        raise ValueError("Unknown template slots: " + ", ".join(sorted(unknown)))
    # One substitution pass: placeholders inside user-authored text remain literal.
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda match: values[match[1]], template)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--file", required=True, help="structured reading-note JSON")
    p.add_argument("--out", required=True, help="standalone .html file")
    p.add_argument("--theme", choices=THEMES, default="modern")
    p.add_argument("--asset-mode", choices=("inline", "relative"), default="inline", help="inline resources for Zotero, or relative links inside the output paper directory")
    p.add_argument("--template-file", help="replaceable full-document template")
    p.add_argument("--css-file", help="append authored CSS")
    p.add_argument("--body-file", help="explicit authored HTML fragment (not a Markdown converter)")
    p.add_argument("--force", action="store_true", help="replace an existing local export")
    a = p.parse_args()
    try:
        out = Path(a.out).expanduser().resolve()
        if out.suffix.casefold() != ".html":
            raise ValueError("Output must end in .html")
        if out.exists() and not a.force:
            raise ValueError("Output exists; use another filename or --force for an authorized replacement")
        record = json.loads(Path(a.file).expanduser().read_text(encoding="utf-8-sig"))
        rendered = render(record, a.theme, a.template_file, a.css_file, a.body_file, Path(a.file).expanduser().resolve().parent, out.parent if a.asset_mode == 'relative' else None)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        print(json.dumps({"html": str(out), "theme": a.theme, "bytes": out.stat().st_size, "zotero_registered": False}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
