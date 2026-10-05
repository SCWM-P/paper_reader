"""Rebuildable, per-instance literature/note index, separate from zotero.sqlite."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from zotero_client import ZoteroError, config_dir


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif tag in ("p", "div", "br", "li", "h1", "h2", "h3", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        elif tag in ("p", "div", "li"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_html(value):
    parser = _Text()
    parser.feed(value or "")
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


def folded(text):
    return unicodedata.normalize("NFKC", text).casefold()


def index_path(server_id, library):
    if not server_id:
        raise ValueError("Persistent indexes require Zotero 10+ Server ID")
    token = hashlib.sha256((server_id + "\0" + library).encode()).hexdigest()[:24]
    return config_dir() / "indexes" / (token + ".sqlite3")


class LiteratureIndex:
    def __init__(self, server_id, library="users/0", create=True):
        self.server_id, self.library = server_id, library
        self.path = index_path(server_id, library)
        if not create and not self.path.is_file():
            raise ValueError("No index for this instance/library; run index sync while Zotero is available")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.path.exists():
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
            except FileExistsError:
                pass
        self.db = sqlite3.connect(self.path, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS objects
              (key TEXT PRIMARY KEY, version INTEGER NOT NULL, parent TEXT,
               kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
               searchable TEXT NOT NULL, data TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS object_parent ON objects(parent);
        """)
        self.fts = True
        try:
            self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(key UNINDEXED, text)")
        except sqlite3.OperationalError:
            self.fts = False
        self.db.commit()

    def close(self):
        self.db.close()

    def metadata(self):
        return dict(self.db.execute("SELECT key, value FROM meta"))

    def _row(self, item):
        d = item["data"]
        body = "\n".join(filter(None, (d.get("abstractNote"), plain_html(d.get("note")),
                                      d.get("annotationText"), d.get("annotationComment"))))
        title = d.get("title", "")
        fields = [title, body, d.get("DOI", ""), d.get("url", ""), d.get("date", ""), d.get("extra", ""),
                  " ".join(t["tag"] for t in d.get("tags", [])),
                  " ".join(c.get("name", "") + " " + c.get("firstName", "") + " " + c.get("lastName", "")
                           for c in d.get("creators", []))]
        return (item["key"], int(item["version"]), d.get("parentItem") or None, d["itemType"], title,
                body, folded("\n".join(fields)), json.dumps(d, ensure_ascii=False))

    def sync(self, z, rebuild=False):
        if z.server_id != self.server_id or z.library != self.library:
            raise ValueError("Index instance/library mismatch")
        if self.metadata().get("schema", "1") != "1":
            raise ValueError("Unsupported cache schema; preserve cache and upgrade this skill")
        # Full lightweight key/version inventory also detects trash/deletions, without
        # assuming that the local /deleted endpoint exists or has cloud semantics.
        for attempt in range(2):
            version, inventory = z.versions()
            known = {} if rebuild else dict(self.db.execute("SELECT key, version FROM objects"))
            changed = sorted(k for k, v in inventory.items() if known.get(k) != v)
            fetched = []
            for start in range(0, len(changed), 50):
                fetched.extend(z.items(keys=changed[start:start + 50]))
            final_version = z.library_version()
            actual = {it["key"]: it["version"] for it in fetched}
            expected = {k: inventory[k] for k in changed}
            if final_version != version or actual != expected:
                if attempt == 0:
                    continue
                raise ZoteroError(409, "library changed", "Library changed during indexing twice; cache remains unchanged. Retry later.")
            deleted = set(known) - set(inventory)
            with self.db:
                if rebuild:
                    self.db.execute("DELETE FROM objects")
                    if self.fts:
                        self.db.execute("DELETE FROM search")
                for key in deleted:
                    self.db.execute("DELETE FROM objects WHERE key=?", (key,))
                    if self.fts:
                        self.db.execute("DELETE FROM search WHERE key=?", (key,))
                for item in fetched:
                    row = self._row(item)
                    self.db.execute("INSERT OR REPLACE INTO objects VALUES (?,?,?,?,?,?,?,?)", row)
                    if self.fts:
                        self.db.execute("DELETE FROM search WHERE key=?", (row[0],))
                        self.db.execute("INSERT INTO search(key,text) VALUES (?,?)", (row[0], row[6]))
                meta = {"schema": "1", "server_id": self.server_id, "library": self.library,
                        "library_version": str(version), "endpoint": z.base,
                        "indexed_at": datetime.now(timezone.utc).isoformat(), "count": str(len(inventory))}
                self.db.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)", meta.items())
            return dict(meta, changed=len(changed), removed=len(deleted), path=str(self.path), fts5=self.fts)

    def _root(self, row):
        visited = set()
        while row["parent"] and row["key"] not in visited:
            visited.add(row["key"])
            parent = self.db.execute("SELECT * FROM objects WHERE key=?", (row["parent"],)).fetchone()
            if parent is None:
                break
            row = parent
        return row

    def recall(self, query, limit=10, notes_only=False):
        terms = [folded(t) for t in query.split() if t.strip()]
        if not terms or limit <= 0:
            raise ValueError("Provide a non-empty query and positive limit")
        # SQL parameters prevent note/query text from being interpreted as SQL/FTS syntax.
        # Substring fallback handles CJK terms inside unsegmented sentences.
        predicates = " AND ".join("searchable LIKE ? ESCAPE '\\'" for _ in terms)
        args = ["%" + t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%" for t in terms]
        kind = " AND kind IN ('note','annotation')" if notes_only else ""
        rows = self.db.execute("SELECT * FROM objects WHERE " + predicates + kind + " ORDER BY key LIMIT ?",
                               args + [limit]).fetchall()
        if self.fts:
            expression = " AND ".join('"' + t.replace('"', '""') + '"' for t in terms)
            ranked = self.db.execute("SELECT o.* FROM search JOIN objects o ON o.key=search.key "
                                     "WHERE search MATCH ?" + (" AND o.kind IN ('note','annotation')" if notes_only else "")
                                     + " ORDER BY bm25(search), o.key LIMIT ?", (expression, limit)).fetchall()
            rows = list({r["key"]: r for r in ranked + rows}.values())[:limit]
        result = []
        for row in rows:
            root = self._root(row)
            data = json.loads(row["data"])
            content = row["body"] or row["title"]
            pos = folded(content).find(terms[0])
            offset = max(0, pos - 100)
            scope = "library" if self.library == "users/0" else self.library
            result.append({"matched_key": row["key"], "paper_key": root["key"], "title": root["title"] or row["title"],
                           "kind": row["kind"], "version": row["version"], "snippet": content[offset:offset + 600],
                           "page_label": data.get("annotationPageLabel"),
                           "select_uri": f"zotero://select/{scope}/items/{root['key']}"})
        return {"cache": self.metadata(), "matches": result,
                "search_scope": "metadata, abstracts, notes, annotation text/comments; excludes PDF full text"}


def index_status():
    result = []
    for path in sorted((config_dir() / "indexes").glob("*.sqlite3")):
        try:
            db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
            try:
                result.append(dict(dict(db.execute("SELECT key,value FROM meta")), path=str(path)))
            finally:
                db.close()
        except sqlite3.Error:
            result.append({"path": str(path), "error": "unreadable cache; rebuild explicitly"})
    return result
