"""Literature import and evidence-linked reading-note workflows."""
from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import urlsplit

from zotero_client import ZoteroError, equivalent_field
from reading_record import normalize_record, author_names


def normalize_doi(value):
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I).casefold()


def duplicate_candidates(z, payload):
    # Search is a candidate generator; equality below is the actual decision.
    doi = normalize_doi(payload.get("DOI", ""))
    url = payload.get("url", "").rstrip("/")
    title = " ".join(payload.get("title", "").casefold().split())
    queries = [q for q in (doi, payload.get("url"), payload.get("title")) if q]
    result = {}
    for query in queries:
        for it in z.items(top=True, q=query, qmode="everything"):
            d = it["data"]
            reason = None
            if doi and normalize_doi(d.get("DOI", "")) == doi:
                reason = "DOI"
            elif url and d.get("url", "").rstrip("/") == url:
                reason = "URL"
            elif title and " ".join(d.get("title", "").casefold().split()) == title:
                reason = "title (review authors/year before reuse)"
            if reason:
                result[it["key"]] = {"key": it["key"], "title": d.get("title"), "date": d.get("date"), "reason": reason}
    return list(result.values())


def import_item(z, payload, collections=(), tags=(), apply=False):
    payload = dict(payload)
    if not payload.get("title") or payload.get("itemType") in (None, "note", "annotation", "attachment"):
        raise ValueError("Supply verified bibliographic metadata with itemType and title")
    if any(k in payload for k in ("key", "version", "parentItem", "library")):
        raise ValueError("Import editable metadata only; omit keys, versions and library wrappers")
    duplicates = duplicate_candidates(z, payload)
    if duplicates:
        return {"status": "duplicate_candidates", "created": False, "candidates": duplicates}
    cols = list(payload.get("collections", []))
    for name in collections:
        key = z.resolve_collection(name)
        if key not in cols:
            cols.append(key)
    for key in cols:
        z.resolve_collection(key)
    payload["collections"] = cols
    old_tags = list(payload.get("tags", []))
    have = {t["tag"] for t in old_tags}
    for tag in tags:
        if tag not in have:
            old_tags.append({"tag": tag})
            have.add(tag)
    payload["tags"] = old_tags
    # Validate against the running Zotero schema instead of freezing a field list.
    template, creator_types = z.item_template(payload["itemType"])
    unknown = set(payload) - set(template) - {"collections", "relations"}
    if unknown:
        raise ValueError("Fields not supported by this Zotero/item type: " + ", ".join(sorted(unknown)))
    if any(c.get("creatorType") not in creator_types for c in payload.get("creators", [])):
        raise ValueError("Unsupported creatorType for this Zotero item type")
    if not apply:
        return {"status": "preview", "payload": payload}
    key = z._created_key(z.add_items([payload]))
    return {"status": "created", "key": key, "select_uri": z.select_uri(key), "verified": True}


def reading_note_html(z, parent_key, record):
    item = z.item(parent_key)
    if item['data'].get('deleted'):
        raise ValueError('Paper is in Zotero Trash; select an active item or explicitly restore it first')
    record = normalize_record(record, item['data'])
    if item["data"]["itemType"] in ("attachment", "note", "annotation"):
        raise ValueError("Choose the bibliographic parent for reading notes")
    esc = lambda x: html.escape(str(x), quote=True)
    body = [f'<h1>{esc(record.get("title", "AI Reading Summary"))}</h1>',
            f'<p>文献：<a href="{esc(z.select_uri(parent_key))}">{esc(item["data"].get("title", parent_key))}</a></p>',
            '<h2>文献元数据</h2><p>'+esc(record['metadata']['title'])+'</p><p>'+esc('; '.join(author_names(record['metadata'])))+'</p>',
            f'<p>记录时间：{esc(record.get("recorded_at", "待补充"))}；记录者：{esc(record.get("note_author", record.get("author", "AI 伴读")))}</p>',
            f'<h2>阅读结论</h2><p>{esc(record["summary"])}</p>']
    for key in ('date','publicationTitle','proceedingsTitle','conferenceName','volume','issue','pages','publisher','DOI','url'):
        if record['metadata'].get(key): body.insert(4,'<p>'+esc(key)+': '+esc(record['metadata'][key])+'</p>')
    if record.get("html_attachment_key"):
        key = record["html_attachment_key"]
        attachment = z.item(key)["data"]
        if attachment.get("parentItem") != parent_key or attachment.get("contentType") != "text/html":
            raise ValueError("Choose this paper's HTML reading attachment")
        scope = "library" if z.library == "users/0" else z.library
        body.insert(2, f'<p><a href="zotero://open/{scope}/items/{esc(key)}">打开 HTML 阅读笔记</a></p>')
    body.append('<h2>学术价值与贡献</h2>')
    for entry in record['highlights']:
        if isinstance(entry,str): body.append('<p>'+esc(entry)+'</p>')
        else: body.append('<h3>'+esc(entry.get('title','主要贡献'))+'</h3><p>'+esc(entry.get('content',''))+'</p>')
    body.append('<h2>伴读 Q &amp; A</h2>')
    for entry in record['Q & A']:
        body.append('<h3>'+esc(entry['question'])+'</h3><p>'+esc(entry.get('answer') or '待继续讨论')+'</p>')
    evidence=[]
    for entry in record['others']:
        body.append('<h2>'+esc(entry.get('title','扩展阅读'))+'</h2>')
        content=entry.get('content','')
        if isinstance(content,list): body.append('<ul>'+''.join('<li>'+esc(x)+'</li>' for x in content)+'</ul>')
        elif content: body.append('<p>'+esc(content)+'</p>')
        if entry.get('code'): body.append('<pre>'+esc(entry['code'])+'</pre>')
        for figure in entry.get('figures',[]): body.append('<p>'+esc(figure.get('caption',''))+' '+esc(figure.get('explanation',''))+'</p>')
        for equation in entry.get('equations',[]): body.append('<p>'+esc(equation.get('title',''))+' '+esc(equation.get('latex',''))+' '+esc(equation.get('explanation',''))+'</p>')
        for video in entry.get('videos',[]): body.append('<p>'+esc(video.get('caption','教学视频'))+' · 在 HTML 阅读页中观看</p>')
        for link in entry.get('links',[]):
            parsed=urlsplit(link['url'])
            if parsed.scheme not in ('http','https','zotero') or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError('Use a public source URL or Zotero link')
            body.append('<p><a href="'+esc(link['url'])+'">'+esc(link.get('label',link['url']))+'</a></p>')
        evidence.extend(entry.get('evidence',[]))
    for entry in record['highlights']+record['Q & A']:
        if isinstance(entry,dict): evidence.extend(entry.get('evidence',[]))
    if evidence: body.append('<h2>证据与出处</h2><ul>')
    seen_evidence=set()
    for entry in evidence:
        if not isinstance(entry, dict) or not entry.get("claim") or not entry.get("locator"):
            raise ValueError("Each evidence entry requires claim and locator (section/page/table)")
        identity=tuple(str(entry.get(k,'')) for k in ('claim','locator','attachment_key','page','url'))
        if identity in seen_evidence: continue
        seen_evidence.add(identity)
        link = z.select_uri(parent_key)
        if entry.get("url"):
            link = entry["url"]
            parsed = urlsplit(link)
            if parsed.scheme not in ("https", "http", "zotero") or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError("Use a public source URL or Zotero evidence link")
        if entry.get("attachment_key"):
            attachment = z.item(entry["attachment_key"])
            if attachment["data"].get("parentItem") != parent_key or attachment["data"]["itemType"] != "attachment":
                raise ValueError("Evidence attachment must belong to this paper")
            if z.library == "users/0" and entry.get("page") is not None:
                page = entry["page"]
                if not isinstance(page, int) or isinstance(page, bool) or page < 1:
                    raise ValueError("PDF page is a positive 1-based integer")
                link = f'zotero://open-pdf/library/items/{entry["attachment_key"]}?page={page}'
        body.append(f'<li>{esc(entry["claim"])} — <a href="{esc(link)}">{esc(entry["locator"])}</a></li>')
    if evidence: body.append("</ul>")
    return "\n".join(body)


def upsert_reading_note(z, parent, record, slot="reading-summary", expected_version=None, apply=False):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", slot):
        raise ValueError("slot must use lowercase letters, digits and hyphens")
    body = reading_note_html(z, parent, record)
    marker = "agent:slot:" + slot
    candidates = [ch for ch in z.children(parent) if ch["data"]["itemType"] == "note"
                  and marker in {t["tag"] for t in ch["data"].get("tags", [])}]
    if len(candidates) > 1:
        raise ValueError("Multiple notes own this slot; resolve explicitly before updating")
    cur = candidates[0] if candidates else None
    preview = {"status": "preview", "parent": parent, "slot": slot, "html": body,
               "existing_key": cur["key"] if cur else None, "existing_version": cur["version"] if cur else None}
    if not apply:
        return preview
    if cur and equivalent_field("note", cur["data"].get("note"), body):
        return {"status": "unchanged", "key": cur["key"], "verified": True}
    if cur:
        if expected_version is None:
            raise ValueError("Read and integrate existing note; supply --expected-version to replace this slot")
        updated = z.update_item(cur["key"], {"note": body}, expected_version=expected_version, current=cur)
        return {"status": "updated", "key": updated["key"], "verified": True}
    key = z.add_note(parent, body, ["agent:reading-note", marker])
    return {"status": "created", "key": key, "verified": True}


def attach_pdf(z, parent, file_path, apply=False):
    path = Path(file_path).expanduser().resolve(strict=True)
    if not path.is_file() or path.stat().st_size >= 4 * 1024 ** 3:
        raise ValueError("PDF must be a regular file smaller than 4 GiB")
    with path.open("rb") as f:
        if b"%PDF-" not in f.read(1024):
            raise ValueError("File does not have a PDF signature")
    item = z.item(parent)
    if apply and item['data'].get('deleted'):
        raise ValueError('Paper is in Zotero Trash; select an active item or explicitly restore it first')
    if item["data"]["itemType"] in ("note", "annotation", "attachment"):
        raise ValueError("Choose the bibliographic parent")
    import hashlib
    md5 = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 ** 2), b""):
            md5.update(chunk)
    existing = [ch for ch in z.pdf_attachments(parent) if ch["data"].get("md5") == md5.hexdigest()]
    if existing:
        return {"status": "existing", "key": existing[0]["key"], "verified": True}
    if not apply:
        return {"status": "preview", "parent": parent, "filename": path.name, "bytes": path.stat().st_size}
    if not z.info()["key_remembered"]:
        raise ValueError("Multi-step PDF saving requires a remembered key; authorize with Always Allow")
    key = z._created_key(z.add_items([{"itemType": "attachment", "parentItem": parent,
                                     "linkMode": "imported_file", "filename": path.name,
                                     "title": path.stem, "contentType": "application/pdf"}]))
    try:
        return dict(z.upload_file(key, path), status="saved")
    except Exception as e:
        # Do not delete the attachment or retry creation; report the resumable identity.
        raise ZoteroError(getattr(e, "status", 0), "partial PDF import",
                          f"Attachment metadata created: {key}; PDF save incomplete/unknown. Inspect it, then use upload {key} --file FILE.") from e


def save_html_note(z, parent, record, out, theme="modern", slot="reading-summary",
                   expected_version=None, apply=False, template_file=None, css_file=None, body_file=None, asset_base=None):
    """Export a reading page and keep its stored attachment and native summary together."""
    from html_note import render
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", slot):
        raise ValueError("Use lowercase letters, digits and hyphens for slot")
    paper = z.item(parent)["data"]
    if apply and paper.get('deleted'):
        raise ValueError('Paper is in Zotero Trash; export locally or explicitly restore the paper before saving')
    if paper["itemType"] in ("note", "annotation", "attachment"):
        raise ValueError("Choose the bibliographic paper")
    record = normalize_record(record, paper)
    identity = record.get("paper", {})
    if identity.get("key", parent) != parent or identity.get("library", z.library) != z.library:
        raise ValueError("Reading record belongs to another paper/library")
    record["paper"] = dict(identity, key=parent, library=z.library, title=paper.get("title", ""),
                           select_uri=z.select_uri(parent))
    # Resolve an existing note before saving the file, so human edits can be integrated first.
    notes = [ch for ch in z.children(parent) if ch["data"]["itemType"] == "note"
             and "agent:slot:" + slot in {t["tag"] for t in ch["data"].get("tags", [])}]
    if len(notes) > 1:
        raise ValueError("Multiple notes own this slot; choose a single reading summary")
    if apply and notes and expected_version != notes[0]["version"]:
        raise ValueError("Integrate the existing note and pass its --expected-version")
    path = Path(out).expanduser().resolve()
    if path.suffix.casefold() != ".html":
        raise ValueError("Output filename must end in .html")
    rendered = render(record, theme, template_file, css_file, body_file, asset_base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    if not apply:
        return {"status": "exported", "html": str(path), "zotero_registered": False}
    if not z.info()["key_remembered"]:
        raise ValueError("HTML attachment saving uses multiple requests; authorize with Always Allow")
    marker = "agent:html:" + slot
    candidates = [ch for ch in z.children(parent) if ch["data"]["itemType"] == "attachment"
                  and marker in {t["tag"] for t in ch["data"].get("tags", [])}]
    if len(candidates) > 1:
        raise ValueError("Multiple HTML files own this slot; choose the existing attachment")
    key = candidates[0]["key"] if candidates else None
    if key and candidates[0]["data"].get("contentType") != "text/html":
        raise ValueError("Existing slot attachment should be text/html")
    if not key:
        key = z._created_key(z.add_items([{"itemType": "attachment", "parentItem": parent,
                                         "linkMode": "imported_file", "filename": path.name,
                                         "title": record.get("title", "HTML 阅读笔记"), "contentType": "text/html",
                                         "charset": "utf-8", "tags": [{"tag": marker}]}]))
    try:
        uploaded = z.upload_file(key, path)
        record["html_attachment_key"] = key
        summary = upsert_reading_note(z, parent, record, slot, expected_version, apply=True)
    except Exception as e:
        raise ZoteroError(getattr(e, "status", 0), "partial HTML note save",
                          f"HTML attachment key: {key}; inspect it before resuming html-note. "
                          "The native summary may still need saving.", details={"attachment_key": key, "html": str(path)}) from e
    return {"status": "saved", "paper_key": parent, "html": str(path), "attachment_key": key,
            "attachment_path": uploaded.get("path") or z.attachment_path(key), "note_key": summary["key"],
            "open_uri": f'zotero://open/{"library" if z.library == "users/0" else z.library}/items/{key}',
            "zotero_registered": True, "verified": True}
