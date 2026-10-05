#!/usr/bin/env python3
"""Collect bibliographic metadata without modifying Zotero (Python stdlib only)."""
from __future__ import annotations
import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import ipaddress
import json
import re
from pathlib import Path
import urllib.error
import urllib.parse as up
import urllib.request as ur
import xml.etree.ElementTree as ET

MAX_BYTES = 2 * 1024 * 1024
DOI = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
ARXIV = re.compile(r"^(?:\d{4}\.\d{4,5}|[a-z.-]+/\d{7})(?:v\d+)?$", re.I)


def public_url(value):
    p = up.urlsplit(value)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        raise ValueError("Resource URL must be http(s), with a host and without credentials")
    if p.hostname.casefold() == "localhost" or p.hostname.casefold().endswith(".local"):
        raise ValueError("Use a public literature resource URL")
    try:
        addr = ipaddress.ip_address(p.hostname)
    except ValueError:
        addr = None
    if addr and not addr.is_global:
        raise ValueError("Use a public literature resource URL")
    return value


class CheckedRedirect(ur.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, timeout=20, data=None, local=False):
    # Remote acquisition respects environment/OS proxy settings. Local translators bypass proxies.
    handlers = [ur.ProxyHandler({})] if local else [CheckedRedirect()]
    if local:
        from zotero_client import _NoRedirect
        handlers.append(_NoRedirect())
    opener = ur.build_opener(*handlers)
    req = ur.Request(url, data=data, headers={"User-Agent": "Zotero-Agent-Skill/1.0 (metadata acquisition)",
                                              "Accept": "application/json, application/atom+xml, text/html",
                                              **({"Content-Type": "text/plain; charset=utf-8"} if data else {})})
    with opener.open(req, timeout=timeout) as response:
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Metadata response exceeds 2 MiB; use a site translator or bounded source")
        return raw, response.geturl(), response.headers.get_content_charset() or "utf-8"


def clean(value):
    return " ".join(html.unescape(re.sub(r"<[^>]*>", "", str(value))).split())


def audit(item):
    if not isinstance(item, dict):
        raise ValueError("Item metadata must be a JSON object")
    kind = item.get("itemType")
    creators = item.get("creators", [])
    if not isinstance(creators, list) or not all(isinstance(c, dict) for c in creators):
        raise ValueError("creators must be an array of creator objects")
    required = ["title", "creators", "date"]
    if kind == "journalArticle":
        required += ["publicationTitle"]
    elif kind == "conferencePaper":
        required += ["proceedingsTitle"]
    elif kind in ("book", "bookSection"):
        required += ["publisher", "place"]
        if kind == "bookSection":
            required += ["bookTitle"]
    elif kind == "webpage":
        required += ["url", "accessDate"]
    missing = [key for key in required if not item.get(key)]
    author_review = [i for i, creator in enumerate(creators)
                     if creator.get("creatorType") == "author" and creator.get("name")]
    check = [key for key in ("volume", "issue", "pages") if kind == "journalArticle" and not item.get(key)]
    if kind == "conferencePaper":
        check += [key for key in ("publisher", "place", "pages") if not item.get(key)]
    return {"missing": missing, "check_if_applicable": check, "unsplit_author_indices": author_review,
            "citation_ready": False, "meaning": "Acquisition checklist only; verify source, publication version and requested style before citation"}


def from_crossref(message, requested_doi):
    if not isinstance(message, dict):
        raise ValueError("Crossref message must be an object")
    if str(message.get("DOI", "")).casefold() != requested_doi.casefold():
        raise ValueError("Crossref returned a different DOI")
    kinds = {"journal-article": "journalArticle", "proceedings-article": "conferencePaper", "book": "book",
             "monograph": "book", "report": "report", "posted-content": "preprint", "book-chapter": "bookSection"}
    kind = kinds.get(message.get("type"))
    if kind is None:
        raise ValueError("Crossref type needs manual/translator mapping: " + str(message.get("type")))
    item = {"itemType": kind, "title": clean((message.get("title") or [""])[0]), "DOI": message["DOI"],
            "url": "https://doi.org/" + up.quote(message["DOI"], safe="/"), "creators": []}
    for role in ("author", "editor"):
        for person in message.get(role, []):
            if not isinstance(person, dict):
                raise ValueError("Crossref creator must be an object")
            if person.get("family"):
                item["creators"].append({"creatorType": role, "firstName": person.get("given", ""), "lastName": person["family"]})
            elif person.get("name"):
                item["creators"].append({"creatorType": role, "name": person["name"]})
    for date_key in ("published-print", "published-online", "published", "issued"):
        date_parts = message.get(date_key, {}).get("date-parts") or [[]]
        parts = date_parts[0]
        if parts:
            item["date"] = "-".join(str(v).zfill(4 if i == 0 else 2) for i, v in enumerate(parts))
            break
    container = clean((message.get("container-title") or [""])[0])
    field = {"journalArticle": "publicationTitle", "conferencePaper": "proceedingsTitle", "bookSection": "bookTitle",
             "preprint": "repository", "report": "institution"}.get(kind)
    if container and field:
        item[field] = container
    for src, target in (("volume", "volume"), ("issue", "issue"), ("page", "pages"), ("abstract", "abstractNote")):
        if message.get(src):
            item[target] = clean(message[src])
    if kind in ("book", "bookSection", "conferencePaper") and message.get("publisher"):
        item["publisher"] = clean(message["publisher"])
    for src, target in (("ISBN", "ISBN"), ("ISSN", "ISSN")):
        if message.get(src) and (target == "ISBN" and kind in ("book", "bookSection", "conferencePaper")
                                  or target == "ISSN" and kind == "journalArticle"):
            item[target] = " ".join(message[src])
    if not item["title"]:
        raise ValueError("Crossref did not supply a title")
    return item


def from_arxiv(raw, requested_id):
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(raw)
    entries = root.findall("a:entry", ns)
    if len(entries) != 1:
        raise ValueError("arXiv returned zero or multiple entries")
    entry = entries[0]
    identity = entry.findtext("a:id", "", ns)
    actual = identity.split("/abs/")[-1]
    if re.sub(r"v\d+$", "", actual) != re.sub(r"v\d+$", "", requested_id):
        raise ValueError("arXiv returned a different identifier")
    if re.search(r"v\d+$", requested_id) and actual != requested_id:
        raise ValueError("arXiv returned a different version")
    item = {"itemType": "preprint", "title": clean(entry.findtext("a:title", "", ns)),
            "repository": "arXiv", "archiveID": actual, "url": "https://arxiv.org/abs/" + actual,
            "date": entry.findtext("a:published", "", ns)[:10],
            "abstractNote": clean(entry.findtext("a:summary", "", ns)),
            # Atom provides unsplit names: preserve Unicode/name order for human review.
            "creators": [{"creatorType": "author", "name": clean(a.findtext("a:name", "", ns))}
                         for a in entry.findall("a:author", ns)]}
    if entry.findtext("x:doi", "", ns):
        item["DOI"] = entry.findtext("x:doi", "", ns)
    # A journal-ref string is provenance, not reliable structured volume/issue/pages.
    ref = entry.findtext("x:journal_ref", "", ns)
    if ref:
        item["extra"] = "arXiv journal reference (verify publication separately): " + clean(ref)
    if not item["title"]:
        raise ValueError("arXiv did not supply a title")
    return item


class EmbeddedMetadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta, self.title, self.in_title = {}, [], False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = (attrs.get("name") or attrs.get("property") or "").casefold()
            value = attrs.get("content", "").strip()
            if key and value:
                self.meta.setdefault(key, []).append(value)
        elif tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)

    def item(self, url):
        m = self.meta
        get = lambda *keys: next((clean(m[k][0]) for k in keys if m.get(k)), "")
        scholarly = bool(get("citation_title"))
        journal = get("citation_journal_title")
        conference = get("citation_conference_title")
        kind = "journalArticle" if scholarly and journal else "conferencePaper" if scholarly and conference else "webpage"
        item = {"itemType": kind, "title": get("citation_title", "dc.title", "og:title") or clean("".join(self.title)) or url,
                "url": url, "accessDate": dt.datetime.now(dt.timezone.utc).date().isoformat(), "creators": []}
        for name in m.get("citation_author", []) or m.get("dc.creator", []):
            # No heuristic splitting of family/given names, particularly for Chinese names.
            item["creators"].append({"creatorType": "author", "name": clean(name)})
        for field, keys in {"date": ("citation_publication_date", "citation_date", "dc.date"),
                            "DOI": ("citation_doi",), "volume": ("citation_volume",), "issue": ("citation_issue",)}.items():
            value = get(*keys)
            if value:
                item[field] = value
        if journal and kind == "journalArticle":
            item["publicationTitle"] = journal
        if conference and kind == "conferencePaper":
            item["proceedingsTitle"] = conference
        first, last = get("citation_firstpage"), get("citation_lastpage")
        if first:
            item["pages"] = first + ("-" + last if last and last != first else "")
        # Avoid injecting journal-only fields into a generic webpage schema.
        if kind == "webpage":
            for field in ("DOI", "volume", "issue", "pages"):
                item.pop(field, None)
        return item


def collect(source, translator=None, timeout=20):
    source = source.strip()
    normalized = re.sub(r"^(?:doi:\s*|https?://(?:dx\.)?doi\.org/)", "", source, flags=re.I)
    doi = normalized if DOI.fullmatch(normalized) else None
    aid = re.sub(r"^(?:arxiv:\s*|https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/)", "", source, flags=re.I)
    aid = re.sub(r"\.pdf$", "", aid)
    aid = aid if ARXIV.fullmatch(aid) else None
    resource = "https://doi.org/" + up.quote(doi, safe="/") if doi else "https://arxiv.org/abs/" + aid if aid else public_url(source)
    attempts, item, method, retrieval = [], None, "link-only", resource
    if translator:
        from zotero_client import normalize_base
        if up.urlsplit(translator).port is None:
            raise ValueError("Specify the translation-server port explicitly (usually 1969)")
        origin = normalize_base(translator)
        # Separate optional service, not a Zotero Local API endpoint.
        origin = origin.removesuffix("/api")
        endpoint = origin + ("/search" if doi or aid else "/web")
        try:
            raw, retrieval, _ = fetch(endpoint, timeout, (doi or ("arXiv:" + aid if aid else source)).encode(), local=True)
            result = json.loads(raw)
            if not isinstance(result, list) or len(result) != 1 or not isinstance(result[0], dict):
                raise ValueError("Translator requires an explicit single-item selection")
            original = result[0].get("data", result[0])
            if not isinstance(original, dict):
                raise ValueError("Translator item must be an object")
            item = {k: v for k, v in original.items() if k not in {"key", "version", "library", "attachments", "notes", "collections", "relations"}}
            if not item.get("title") or not item.get("itemType"):
                raise ValueError("Translator did not return bibliographic metadata")
            method = "zotero-translator"
        except (OSError, ValueError, TypeError, KeyError) as e:
            attempts.append({"provider": "translator", "error": type(e).__name__, "status": getattr(e, "code", None)})
            item = None
    if item is not None:
        try:
            audit(item)
        except ValueError:
            attempts.append({"provider": method, "error": "invalid_creator_shape", "status": None})
            item, method = None, "link-only"
    if item is None:
        try:
            if doi:
                endpoint = "https://api.crossref.org/works/" + up.quote(doi, safe="")
                raw, retrieval, _ = fetch(endpoint, timeout)
                item, method = from_crossref(json.loads(raw)["message"], doi), "crossref-doi"
            elif aid:
                endpoint = "https://export.arxiv.org/api/query?id_list=" + up.quote(aid, safe="")
                raw, retrieval, _ = fetch(endpoint, timeout)
                item, method = from_arxiv(raw, aid), "arxiv-atom"
            else:
                raw, retrieval, encoding = fetch(resource, timeout)
                parser = EmbeddedMetadata()
                parser.feed(raw.decode(encoding, errors="replace"))
                item, method = parser.item(resource), "embedded-html"
        except (OSError, ValueError, KeyError, TypeError, LookupError, ET.ParseError) as e:
            attempts.append({"provider": "identifier/page", "error": type(e).__name__, "status": getattr(e, "code", None)})
    if item is None:
        item = {"itemType": "webpage", "title": resource, "url": resource,
                "accessDate": dt.datetime.now(dt.timezone.utc).date().isoformat()}
    report = audit(item)
    degraded = method == "link-only" or item["itemType"] == "webpage" or bool(report["missing"])
    if degraded:
        tags = item.setdefault("tags", [])
        if not any(t.get("tag") == "agent:metadata-incomplete" for t in tags):
            tags.append({"tag": "agent:metadata-incomplete"})
    return {"status": "needs_review" if degraded else "collected_needs_verification", "item": item,
            "provenance": {"source_url": resource, "retrieval_url": retrieval, "method": method,
                           "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                           "field_sources": {k: "local UTC access date" if k == "accessDate" else method
                                             for k in item if k not in ("tags", "collections")}},
            "audit": report, "attempts": attempts,
            "warnings": ["No Zotero write performed", "Check authors, dates, venue and publication/preprint version against the source",
                         "Unsplit author names require review; GB/T and BibTeX both depend on correct metadata"]}


def write_json(path, value, force):
    dest = Path(path).expanduser().resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w" if force else "x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    acquire = sub.add_parser("collect")
    acquire.add_argument("source", help="DOI, arXiv ID or public literature webpage URL")
    acquire.add_argument("--translator", help="optional already-running loopback Zotero translation-server origin")
    acquire.add_argument("--timeout", type=float, default=20)
    acquire.add_argument("--out", help="report JSON with provenance and acquisition checklist")
    acquire.add_argument("--item-out", help="editable item JSON for zotero_ops import (after verification)")
    acquire.add_argument("--force", action="store_true")
    check = sub.add_parser("audit")
    check.add_argument("--file", required=True)
    a = parser.parse_args()
    try:
        if a.command == "audit":
            item = json.loads(Path(a.file).read_text(encoding="utf-8-sig"))
            result = audit(item.get("data", item)) if isinstance(item, dict) else audit(item)
        else:
            if not 0 < a.timeout <= 120:
                raise ValueError("timeout must be >0 and <=120 seconds per provider")
            result = collect(a.source, a.translator, a.timeout)
            for path in (a.out, a.item_out):
                if path and Path(path).expanduser().exists() and not a.force:
                    raise ValueError("Output exists; choose another filename or explicitly use --force")
            if a.out and a.item_out and Path(a.out).resolve() == Path(a.item_out).resolve():
                raise ValueError("Report and editable item must use different output paths")
            if a.out:
                write_json(a.out, result, a.force)
            if a.item_out:
                write_json(a.item_out, result["item"], a.force)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
