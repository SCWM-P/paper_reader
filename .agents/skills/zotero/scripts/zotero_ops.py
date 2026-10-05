#!/usr/bin/env python3
"""JSON CLI for natural-language Zotero workflows; Python 3.10+, stdlib only."""
from __future__ import annotations
import argparse
import html
import json
import sqlite3
import sys
from pathlib import Path
from zotero_client import Zotero, ZoteroError, zotero_paths
from zotero_index import LiteratureIndex, index_status
from zotero_workflow import attach_pdf, import_item, upsert_reading_note, save_html_note


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def read_json(path):
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8-sig"))


def packet(z, key):
    item, children = z.item(key), z.children(key)
    annotations = []
    for ch in children:
        if ch["data"]["itemType"] == "attachment":
            annotations.extend(z.children(ch["key"]))
    return {"item": item, "children": children, "attachment_children": annotations,
            "select_uri": z.select_uri(key), "server_id": z.server_id, "library": z.library}


def positive(value):
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return n


def write_flags(p):
    p.add_argument("--apply", action="store_true", help="perform write; otherwise preview")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--library", default="users/0", help="users/0 or groups/GROUP_ID")
    ap.add_argument("--base", help="HTTP loopback origin, optionally ending in /api")
    ap.add_argument("--timeout", type=positive, default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="read-only capability/path diagnosis")
    sub.add_parser("groups", help="list available group libraries")
    p = sub.add_parser("items", help="paged search; default first 20")
    p.add_argument("--top", action="store_true")
    p.add_argument("--include-children", action="store_true")
    for name in ("item-type", "collection", "tag", "q"):
        p.add_argument("--" + name)
    p.add_argument("--qmode", choices=["titleCreatorYear", "everything"])
    p.add_argument("--limit", type=positive, default=20)
    p.add_argument("--all", action="store_true", help="fetch every page")
    p.add_argument("--sort", default="dateAdded")
    p.add_argument("--direction", choices=["asc", "desc"], default="desc")
    p.add_argument("--since", type=int)
    for name in ("collections", "tags", "json", "verbose"):
        p.add_argument("--" + name, action="store_true")
    p = sub.add_parser("show", help="item, child notes/files and nested annotations")
    p.add_argument("key")
    p = sub.add_parser("fulltext", help="indexed text with coverage metadata")
    p.add_argument("key")
    p.add_argument("--by-item", action="store_true")
    p.add_argument("--out")
    p.add_argument("--chars", type=positive, default=6000)
    p.add_argument("--all", action="store_true")
    p = sub.add_parser("path", help="authoritative file path")
    p.add_argument("key")
    p = sub.add_parser("note", help="add note; reading-note supports resumable conclusions")
    p.add_argument("key", help="bibliographic parent, or none")
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--body")
    source.add_argument("--body-file")
    p.add_argument("--html", action="store_true", help="treat body as HTML; default escapes text")
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("reading-note", help="upsert structured conclusions/evidence by slot")
    p.add_argument("key")
    p.add_argument("--file", required=True)
    p.add_argument("--slot", default="reading-summary")
    p.add_argument("--expected-version", type=int)
    write_flags(p)
    p = sub.add_parser("html-note", help="export and save a stored HTML reading page with searchable native summary")
    p.add_argument("key")
    p.add_argument("--file", required=True, help="reading record JSON")
    p.add_argument("--out", required=True, help="local HTML output")
    p.add_argument("--theme", choices=["modern", "tufte", "latex", "github"], default="modern")
    p.add_argument("--slot", default="reading-summary")
    p.add_argument("--expected-version", type=int)
    p.add_argument("--template-file")
    p.add_argument("--css-file")
    p.add_argument("--body-file")
    write_flags(p)
    p = sub.add_parser("tag", help="append tags preserving tag types")
    p.add_argument("key")
    p.add_argument("--tag", action="append", required=True)
    p = sub.add_parser("organize", help="add memberships/tags, optionally remove one membership")
    p.add_argument("key")
    p.add_argument("--collection", action="append", default=[])
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--remove-collection")
    write_flags(p)
    p = sub.add_parser("collection", help="ensure collection exists under a parent")
    p.add_argument("name")
    p.add_argument("--parent")
    write_flags(p)
    p = sub.add_parser("import", help="deduplicate verified bibliographic metadata")
    p.add_argument("--file", required=True)
    p.add_argument("--collection", action="append", default=[])
    p.add_argument("--tag", action="append", default=[])
    write_flags(p)
    for name, help_text in (("attach", "save local PDF as a stored child attachment"),
                            ("upload", "resume file upload to an existing attachment")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("key")
        p.add_argument("--file", required=True)
        write_flags(p)
    p = sub.add_parser("update", help="version-checked metadata/note edit")
    p.add_argument("key")
    p.add_argument("--file", required=True, help="JSON object with changed fields")
    p.add_argument("--expected-version", type=int, required=True)
    write_flags(p)
    p = sub.add_parser("trash", help="move to trash; prefer over permanent delete")
    p.add_argument("key")
    p.add_argument("--expected-version", type=int, required=True)
    write_flags(p)
    p = sub.add_parser("delete", help="permanently delete one item")
    p.add_argument("key")
    p.add_argument("--yes", action="store_true", required=True)
    p = sub.add_parser("index", help="cross-session metadata/note/annotation cache")
    p.add_argument("action", choices=["sync", "status"])
    p.add_argument("--rebuild", action="store_true")
    p = sub.add_parser("recall", help="retrieve papers and conclusions across sessions")
    p.add_argument("query")
    p.add_argument("--limit", type=positive, default=10)
    p.add_argument("--notes-only", action="store_true")
    p.add_argument("--offline", action="store_true", help="explicit use of potentially stale cache")
    p.add_argument("--server-id", help="required offline; find using index status")
    return ap


def dispatch(z, a):
    if a.cmd == "doctor":
        return z.doctor()
    if a.cmd == "groups":
        return z.groups()
    if a.cmd == "items":
        if a.collections:
            return z.collections()
        if a.tags:
            return z.tags()
        objects = z.items(top=a.top, item_type=a.item_type, collection=a.collection, tag=a.tag,
                          q=a.q, qmode=a.qmode, limit=None if a.all else a.limit, sort=a.sort,
                          direction=a.direction, since=a.since, include_children=a.include_children)
        return {"items": objects, "count": len(objects), "limit": None if a.all else a.limit,
                "scope": z.library, "server_id": z.server_id}
    if a.cmd == "show":
        return packet(z, a.key)
    if a.cmd == "path":
        path = z.attachment_path(a.key)
        return {"path": path, "exists": Path(path).is_file() if path else False}
    if a.cmd == "fulltext":
        key = a.key
        if a.by_item:
            pdfs = z.pdf_attachments(key)
            if len(pdfs) != 1:
                raise ValueError("Select an explicit PDF attachment key: " + ", ".join(p["key"] for p in pdfs))
            key = pdfs[0]["key"]
        record = z.fulltext_record(key)
        if record is None:
            raise ZoteroError(404, "no indexed text", "No cached full text: check download, indexing, PDF scans/OCR. Do not infer conclusions.")
        content = record.get("content", "")
        result = {"attachment_key": key, "coverage": {k: v for k, v in record.items() if k != "content"},
                  "characters": len(content), "page_mapping": "unavailable in plain text"}
        if a.out:
            Path(a.out).expanduser().write_text(content, encoding="utf-8")
            result["saved_to"] = str(Path(a.out).expanduser().resolve())
        else:
            result.update(content=content if a.all else content[:a.chars], truncated=not a.all and len(content) > a.chars)
        return result
    if a.cmd == "note":
        body = Path(a.body_file).read_text(encoding="utf-8-sig") if a.body_file else a.body
        if not body.strip():
            raise ValueError("Empty note")
        body = body if a.html else "<p>" + html.escape(body).replace("\n", "<br>") + "</p>"
        parent = None if a.key.lower() in ("none", "-") else a.key
        if a.dry_run:
            return {"status": "preview", "parent": parent, "html": body, "tags": a.tag}
        return {"key": z.add_note(parent, body, a.tag), "verified": True}
    if a.cmd == "reading-note":
        return upsert_reading_note(z, a.key, read_json(a.file), a.slot, a.expected_version, a.apply)
    if a.cmd == "html-note":
        return save_html_note(z, a.key, read_json(a.file), a.out, a.theme, a.slot, a.expected_version,
                              a.apply, a.template_file, a.css_file, a.body_file, Path(a.file).expanduser().resolve().parent)
    if a.cmd == "tag":
        return z.add_tags(a.key, a.tag)
    if a.cmd == "organize":
        if not a.apply:
            return {"status": "preview", "current": z.item(a.key), "add_collections": a.collection,
                    "add_tags": a.tag, "remove_collection": a.remove_collection}
        return z.organize(a.key, a.collection, a.tag, a.remove_collection)
    if a.cmd == "collection":
        return {"key": z.add_collection(a.name, a.parent), "verified": True} if a.apply else {"status": "preview", "name": a.name, "parent": a.parent}
    if a.cmd == "import":
        return import_item(z, read_json(a.file), a.collection, a.tag, a.apply)
    if a.cmd == "attach":
        return attach_pdf(z, a.key, a.file, a.apply)
    if a.cmd == "upload":
        return z.upload_file(a.key, a.file) if a.apply else {"status": "preview", "attachment": z.item(a.key), "file": a.file}
    if a.cmd in ("update", "trash"):
        changes = {"deleted": 1} if a.cmd == "trash" else read_json(a.file)
        if not isinstance(changes, dict):
            raise ValueError("Changes must be a JSON object")
        if not a.apply:
            return {"status": "preview", "current": z.item(a.key), "changes": changes, "expected_version": a.expected_version}
        return z.update_item(a.key, changes, a.expected_version)
    if a.cmd == "delete":
        return z.delete_item(a.key)
    if a.cmd in ("index", "recall"):
        idx = LiteratureIndex(z.server_id, z.library)
        try:
            state = idx.sync(z, rebuild=getattr(a, "rebuild", False))
            if a.cmd == "index":
                return state
            return dict(idx.recall(a.query, a.limit, a.notes_only), offline=False, live_refresh="verified")
        finally:
            idx.close()
    raise ValueError("Unknown command")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    a = build_parser().parse_args()
    try:
        if a.cmd == "index" and a.action == "status":
            emit(index_status())
            return 0
        if a.cmd == "recall" and a.offline:
            if not a.server_id:
                raise ValueError("--offline requires --server-id; list caches using index status")
            idx = LiteratureIndex(a.server_id, a.library, create=False)
            try:
                emit(dict(idx.recall(a.query, a.limit, a.notes_only), offline=True, live_refresh="not performed; cache may be stale"))
            finally:
                idx.close()
            return 0
        emit(dispatch(Zotero(base=a.base, timeout=a.timeout, library=a.library), a))
        return 0
    except ZoteroError as e:
        payload = {"error": {"status": e.status, "message": str(e), "hint": e.hint,
                             "retry_after": e.retry_after, "details": e.details}}
        if a.cmd == "doctor":
            payload["paths"] = zotero_paths()
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 1
    except (ValueError, KeyError, OSError, sqlite3.Error) as e:
        print(json.dumps({"error": {"type": type(e).__name__, "message": str(e)}}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
