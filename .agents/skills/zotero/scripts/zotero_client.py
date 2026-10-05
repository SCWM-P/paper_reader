"""Dependency-free Zotero Local API client (Python 3.10+).

Read-only compatibility with pre-10 local APIs; writes require a Server ID and
a local authorization key. Never accesses the Zotero database directly.
"""
from __future__ import annotations

import configparser
import hashlib
import http.client
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_API_BASE = "http://127.0.0.1:23119"
TIMEOUT = 10
PREFERRED_PORTS = (23119,)
LINK_MODE = {0: "imported_file", 1: "imported_url", 2: "linked_file", 3: "linked_url"}


class ZoteroError(RuntimeError):
    HINTS = {
        0: "Connection failed; Zotero may be starting, API disabled, or port occupied.",
        401: "No valid local key. Request authorization; do not use a zotero.org key.",
        403: "Local API disabled, authorization denied, or library/file not editable.",
        404: "Resource missing, file not downloaded, or endpoint unsupported.",
        409: "Library locked; inspect current state before trying again.",
        412: "Instance, object version, or file hash changed. Re-read before reconciliation.",
        428: "Required Server ID or version/file precondition missing.",
        429: "Throttled. Respect Retry-After; do not repeatedly trigger dialogs.",
    }

    def __init__(self, status, body, hint="", headers=None, details=None):
        self.status, self.body = status, body
        self.hint = hint or self.HINTS.get(status, "")
        self.retry_after = (headers or {}).get("retry-after")
        self.details = details or {}
        # Do not expose server error bodies: they may contain submitted notes or credentials.
        super().__init__(f"HTTP {status}: {self.hint or 'Zotero operation failed; inspect response privately.'}")


def normalize_base(value):
    p = urllib.parse.urlsplit(str(value).rstrip("/"))
    if p.scheme != "http" or p.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("ZOTERO_LOCAL_API must be an HTTP loopback URL")
    if p.username or p.password or p.query or p.fragment or p.path not in ("", "/api"):
        raise ValueError("Use the local origin or origin/api; no credentials/query/path")
    port = p.port if p.port is not None else 23119
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    host = "[::1]" if p.hostname == "::1" else "127.0.0.1"
    return f"http://{host}:{port}"


def config_dir():
    if os.environ.get("ZOTERO_AGENT_HOME"):
        return Path(os.environ["ZOTERO_AGENT_HOME"]).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData/Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "zotero-agent"


def key_path():
    return config_dir() / "local_api_key.json"


def private_json(path, data):
    """Atomic credential/cache metadata write; owner-only creation on POSIX."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".zotero-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _candidate_profile_dirs():
    override = os.environ.get("ZOTERO_PROFILE_DIR")
    if override:
        return [Path(override).expanduser()]
    home = Path.home()
    if sys.platform == "win32":
        roots = [Path(os.environ.get("APPDATA") or home / "AppData/Roaming") / "Zotero/Zotero"]
    elif sys.platform == "darwin":
        roots = [home / "Library/Application Support/Zotero"]
    else:
        roots = [home / ".zotero/zotero", home / ".var/app/org.zotero.Zotero/config/zotero/zotero",
                 home / "snap/zotero-snap/common/.zotero/zotero",
                 home / "snap/zotero/common/.zotero/zotero"]
    out = []
    for root in roots:
        ini = configparser.ConfigParser(interpolation=None)
        try:
            ini.read(root / "profiles.ini", encoding="utf-8-sig")
            for section in ini.sections():
                if section.startswith("Profile") and ini.has_option(section, "Path"):
                    path = Path(ini[section]["Path"])
                    if ini[section].get("IsRelative", "1") == "1":
                        path = root / path
                    out.append((ini[section].get("Default") == "1", path))
        except (OSError, configparser.Error):
            pass
        for parent in (root / "Profiles", root):
            if parent.is_dir():
                out.extend((False, p) for p in sorted(parent.iterdir()) if (p / "prefs.js").is_file())
        if (root / "prefs.js").is_file():
            out.append((False, root))
    return list(dict.fromkeys(p for _, p in sorted(out, key=lambda x: not x[0])))


def _profile():
    profiles = _candidate_profile_dirs()
    return profiles[0] if profiles else None


def _read_pref(key):
    if key not in {"dataDir", "useDataDir", "httpServer.port", "httpServer.localAPI.enabled"}:
        raise ValueError("Preference is not allowlisted")
    profile = _profile()
    if not profile or not (profile / "prefs.js").is_file():
        return None
    pattern = re.compile(r'user_pref\(\s*"extensions\.zotero\.' + re.escape(key)
                         + r'"\s*,\s*("(?:[^"\\]|\\.)*"|true|false|\d+)\s*\)')
    try:
        # Extract only allowlisted preferences, never print the file or plugin settings.
        match = pattern.search((profile / "prefs.js").read_text(encoding="utf-8", errors="replace"))
        return json.loads(match[1]) if match else None
    except (OSError, ValueError):
        return None


def zotero_paths():
    profile = _profile()
    custom = os.environ.get("ZOTERO_DATA_DIR")
    source = "ZOTERO_DATA_DIR" if custom else "expected default (not verified against active API)"
    if not custom and _read_pref("useDataDir") is True:
        custom = _read_pref("dataDir")
        source = "selected profile preference (not verified against active API)"
    data_dir = Path(custom).expanduser() if custom else Path.home() / "Zotero"
    return {"profile_dir": str(profile) if profile else None,
            "data_dir": str(data_dir), "data_dir_source": source,
            "data_dir_exists": data_dir.is_dir(), "profile_candidates": len(_candidate_profile_dirs()),
            "database": str(data_dir / "zotero.sqlite"), "storage_dir": str(data_dir / "storage"),
            "config_dir": str(config_dir()), "note": "Paths are hints only; /file/view/url is authoritative."}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# Loopback traffic must bypass HTTP(S)/system proxies. Never redirect keys to another host.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def _call_once(method, path, headers=None, data=None, timeout=TIMEOUT, base=DEFAULT_API_BASE):
    base = normalize_base(base)
    if not path.startswith("/api/") or path.startswith("//"):
        raise ValueError("Expected a local /api/ path")
    body = data if isinstance(data, bytes) else (json.dumps(data).encode("utf-8") if data is not None else None)
    hdrs = dict(headers or {})
    if body is not None:
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(base + path, data=body, headers=hdrs, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
    except (urllib.error.URLError, OSError, TimeoutError, http.client.HTTPException) as e:
        return None, {}, str(e).encode("utf-8", "replace")


def api_base():
    if os.environ.get("ZOTERO_LOCAL_API"):
        return normalize_base(os.environ["ZOTERO_LOCAL_API"])
    return normalize_base(f"http://127.0.0.1:{os.environ.get('ZOTERO_PORT', '23119')}")


def resolve_base(probe=True, timeout=1.0, discovery_timeout=None):
    if os.environ.get("ZOTERO_LOCAL_API") or os.environ.get("ZOTERO_PORT"):
        return api_base()
    candidates = []
    pinned = _read_pref("httpServer.port")
    if isinstance(pinned, int) and 0 < pinned < 65536:
        candidates.append(f"http://127.0.0.1:{pinned}")
    candidates.append(DEFAULT_API_BASE)
    if not probe:
        return candidates[0]
    budget = float(os.environ.get("ZOTERO_DISCOVERY_TIMEOUT", "3")) if discovery_timeout is None else discovery_timeout
    deadline = time.monotonic() + max(0, budget)
    while True:
        for base in dict.fromkeys(candidates):
            status, hdrs, _ = _call_once("GET", "/api/", timeout=timeout, base=base)
            if status in (200, 403) and (hdrs.get("zotero-api-version") or hdrs.get("zotero-version")):
                return base
        if time.monotonic() >= deadline:
            return candidates[0]
        time.sleep(min(.3, max(0, deadline - time.monotonic())))


def request_with_retry(method, path, headers=None, data=None, timeout=TIMEOUT,
                       attempts=2, pause=.3, base=None, on_retry=None):
    # Mutations, authorization, and uploads are NEVER replayed after an ambiguous failure.
    count = max(1, attempts) if method in ("GET", "HEAD") else 1
    resolved = normalize_base(base) if base else resolve_base()
    for i in range(count):
        result = _call_once(method, path, headers, data, timeout, resolved)
        if result[0] is not None or i == count - 1:
            return result
        if on_retry:
            on_retry(i + 1, "read transport retry")
        time.sleep(pause)


def validate_key(key):
    if not re.fullmatch(r"[A-Z0-9]{8}", str(key)):
        raise ValueError("Zotero item/collection keys must be 8 uppercase letters/digits")
    return key


def canonical_note(value):
    """Ignore only Zotero's note container and whitespace between block tags."""
    value = value.strip()
    match = re.fullmatch(r'<div\s+data-schema-version=[\"\x27]\d+[\"\x27]\s*>(.*)</div>', value, re.S)
    if match:
        value = match[1].strip()
    return re.sub(r">\s+<", "><", value)


def equivalent_field(field, a, b):
    if field == "tags":
        return sorted((t["tag"], int(t.get("type", 0))) for t in a or []) == sorted((t["tag"], int(t.get("type", 0))) for t in b or [])
    if field == "collections":
        return set(a or []) == set(b or [])
    if field == "note":
        return canonical_note(a or "") == canonical_note(b or "")
    return a == b


def file_url_to_path(url, platform=None):
    p = urllib.parse.urlsplit(url)
    if p.scheme != "file":
        raise ValueError("Zotero did not return a file URL")
    path = urllib.parse.unquote(p.path)
    if (platform or sys.platform) == "win32":
        if p.netloc and p.netloc != "localhost":
            return "\\\\" + p.netloc + path.replace("/", "\\")
        if re.match(r"^/[A-Za-z]:", path):
            path = path[1:]
        return path.replace("/", "\\")
    if p.netloc not in ("", "localhost"):
        raise ValueError("Remote file authority cannot be resolved on this platform")
    return path


class Zotero:
    def __init__(self, key=None, keyfile=None, base=None, timeout=None, verify=True,
                 autodetect=True, library="users/0"):
        if not re.fullmatch(r"(?:users/0|groups/[1-9]\d*)", library):
            raise ValueError("Library must be users/0 or groups/GROUP_ID")
        self.library = library
        self.prefix = "/api/" + library
        self.base = normalize_base(base) if base else (resolve_base() if autodetect else api_base())
        self.timeout = float(timeout if timeout is not None else os.environ.get("ZOTERO_TIMEOUT", TIMEOUT))
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        self.retries, self.last_retry_message = 0, ""
        status, headers, _ = self._raw("GET", "/api/")
        if status != 200:
            raise ZoteroError(status or 0, "discovery failed")
        self.server_id = headers.get("zotero-server-id")
        self.api_version = headers.get("zotero-api-version")
        self.schema_version = headers.get("zotero-schema-version")
        self.zotero_version = headers.get("zotero-version")
        if self.api_version != "3":
            raise ZoteroError(501, "unsupported API", "This client supports local API version 3; update it for a newer API.")
        self._keyfile = Path(keyfile).expanduser() if keyfile else key_path()
        self._key = key or os.environ.get("ZOTERO_LOCAL_API_KEY")
        self._remember = False
        self._load_key()
        # A GET cannot prove write permission. It must not advertise 'write verified'.

    def _raw(self, method, path, headers=None, data=None, timeout=None):
        return request_with_retry(method, path, headers, data,
                                  timeout=timeout or self.timeout, base=self.base,
                                  on_retry=self._note_retry)

    def _note_retry(self, attempt, message):
        self.retries += 1
        self.last_retry_message = message

    def _load_key(self):
        if self._key or not self.server_id:
            return
        try:
            cfg = json.loads(self._keyfile.read_text(encoding="utf-8-sig"))
            records = cfg.get("servers", {})
            entry = records.get(self.server_id)
            if entry is None and cfg.get("serverID") == self.server_id:
                entry = cfg  # migrate existing per-user v1 credentials on the next save
            if entry and entry.get("key"):
                self._key, self._remember = entry["key"], bool(entry.get("remember"))
        except (OSError, ValueError, AttributeError):
            pass

    def save_key(self, key, remember):
        self._key, self._remember = key, remember
        try:
            cfg = json.loads(self._keyfile.read_text(encoding="utf-8-sig"))
            records = cfg.get("servers", {})
            if cfg.get("serverID") and cfg.get("key"):
                records.setdefault(cfg["serverID"], {"key": cfg["key"], "remember": cfg.get("remember", False)})
        except (OSError, ValueError):
            records = {}
        records[self.server_id] = {"key": key, "remember": remember}
        private_json(self._keyfile, {"format": 2, "servers": records})
        return self._keyfile

    @property
    def can_write(self):
        return bool(self.server_id and self._key)

    def _headers(self, write=False, extra=None):
        h = {"Zotero-API-Version": "3", "Accept": "application/json"}
        if self.server_id:
            h["Zotero-Server-ID"] = self.server_id
        if write:
            if not self.server_id:
                raise ZoteroError(501, "read-only legacy API", "Local writes require Zotero 10+; reads remain available.")
            if not self._key:
                raise ZoteroError(401, "no key")
            h["Zotero-API-Key"] = self._key
        if extra:
            h.update({k: str(v) for k, v in extra.items()})
        return h

    def _call(self, method, path, *, write=False, data=None, headers=None, parse=True, timeout=None):
        status, hdrs, raw = self._raw(method, path, self._headers(write, headers), data, timeout)
        if status is None:
            hint = "Write outcome unknown: do not repeat; reconcile with a fresh read." if write or method != "GET" else ""
            raise ZoteroError(0, raw.decode("utf-8", "replace"), hint)
        if not 200 <= status < 300:
            if status == 401 and write:
                self._key = None
            raise ZoteroError(status, raw.decode("utf-8", "replace"), headers=hdrs)
        actual_id = hdrs.get("zotero-server-id")
        if self.server_id and actual_id and actual_id != self.server_id:
            raise ZoteroError(412, "Server ID changed")
        if write and not self._remember:
            self._key = None  # a single-use key is consumed on validated writes
        if not parse or not raw:
            return status, hdrs, raw if not parse else None
        try:
            return status, hdrs, json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError):
            raise ZoteroError(502, "invalid JSON", "Unexpected API response; check endpoint/version.") from None

    def authorize(self, app_name="Literature Reading Agent", timeout=60):
        if not self.server_id:
            raise ZoteroError(501, "legacy API", "Upgrade to Zotero 10+ for local writes.")
        headers = {"Zotero-API-Version": "3", "Zotero-Server-ID": self.server_id}
        status, hdrs, raw = self._raw("POST", "/api/local/authorize", headers, {"appName": app_name}, timeout)
        if status != 200:
            raise ZoteroError(status or 0, "authorization failed", headers=hdrs)
        data = json.loads(raw)
        self.save_key(data["key"], bool(data.get("remember")))
        return {"remember": self._remember, "keyfile": str(self._keyfile)}

    def _list(self, path, params=None, limit=None):
        if limit is not None and limit < 0:
            raise ValueError("limit cannot be negative")
        if limit == 0:
            return []
        result, start, seen = [], 0, set()
        while True:
            size = min(100, limit - len(result)) if limit is not None else 100
            query = dict(params or {}, format="json", limit=size, start=start)
            _, hdrs, page = self._call("GET", path + "?" + urllib.parse.urlencode(query))
            if not isinstance(page, list):
                raise ZoteroError(502, "expected list")
            if not page:
                break
            for obj in page:
                identity = obj.get("key") or obj.get("tag") or obj.get("id") or json.dumps(obj, sort_keys=True)
                if identity in seen:
                    raise ZoteroError(409, "pagination changed", "Result set changed during paging; retry the read.")
                seen.add(identity)
            result.extend(page)
            start += len(page)
            total = int(hdrs["total-results"]) if hdrs.get("total-results", "").isdigit() else None
            if (limit is not None and len(result) >= limit) or (total is not None and start >= total) or (total is None and len(page) < size):
                break
        return result

    def items(self, top=False, item_type=None, collection=None, tag=None, q=None, qmode=None,
              limit=None, sort=None, direction=None, since=None, include_children=False, keys=None):
        params = {k: v for k, v in {"itemType": item_type, "tag": tag, "q": q, "qmode": qmode,
                  "sort": sort, "direction": direction, "since": since}.items() if v is not None}
        if keys is not None:
            if not keys:
                return []
            params["itemKey"] = ",".join(validate_key(k) for k in keys)
        path = self.prefix + (f"/collections/{self.resolve_collection(collection)}/items" if collection else "/items")
        if (collection and not include_children) or (not collection and top):
            path += "/top"
        return self._list(path, params, limit)

    def item(self, key):
        return self._call("GET", self.prefix + "/items/" + validate_key(key))[2]

    def children(self, key):
        return self._list(self.prefix + "/items/" + validate_key(key) + "/children")

    def collections(self):
        return self._list(self.prefix + "/collections")

    def tags(self):
        return self._list(self.prefix + "/tags")

    def groups(self):
        return self._list("/api/users/0/groups")

    def item_template(self, item_type):
        """Build allowed editable fields locally; /api/items/new is not implemented."""
        query = urllib.parse.urlencode({"itemType": item_type})
        fields = self._call("GET", "/api/itemTypeFields?" + query)[2]
        creators = self._call("GET", "/api/itemTypeCreatorTypes?" + query)[2]
        template = {f["field"]: "" for f in fields}
        template.update(itemType=item_type, tags=[], collections=[], relations={}, creators=[])
        return template, {c["creatorType"] for c in creators}

    def library_version(self):
        _, h, _ = self._call("GET", self.prefix + "/items?limit=1")
        if "last-modified-version" not in h:
            raise ZoteroError(502, "missing library version")
        return int(h["last-modified-version"])

    def versions(self):
        _, hdrs, data = self._call("GET", self.prefix + "/items?format=versions")
        return int(hdrs["last-modified-version"]), data

    def resolve_collection(self, name_or_key):
        cols = self.collections()
        keyed = [c for c in cols if c["key"] == name_or_key]
        if keyed:
            return keyed[0]["key"]
        named = [c for c in cols if c["data"]["name"] == name_or_key]
        if len(named) == 1:
            return named[0]["key"]
        if len(named) > 1:
            raise ValueError("Ambiguous collection name; use a key: " + ", ".join(c["key"] for c in named))
        raise ValueError(f"Collection not found: {name_or_key}")

    def fulltext_record(self, key):
        try:
            return self._call("GET", self.prefix + "/items/" + validate_key(key) + "/fulltext")[2]
        except ZoteroError as e:
            if e.status == 404:
                return None
            raise

    def fulltext(self, key):
        record = self.fulltext_record(key)
        return record.get("content") if record else None

    def pdf_attachments(self, key):
        item = self.item(key)
        candidates = [item] if item["data"]["itemType"] == "attachment" else self.children(key)
        return [ch for ch in candidates if ch["data"]["itemType"] == "attachment"
                and ch["data"].get("contentType") == "application/pdf"]

    def attachment_path(self, key, index=0):
        item = self.item(key)
        if item["data"]["itemType"] != "attachment":
            pdfs = self.pdf_attachments(key)
            if not pdfs:
                return None
            if len(pdfs) > 1:
                raise ValueError("Multiple PDFs; pass an explicit attachment key from show")
            key = pdfs[0]["key"]
        _, _, raw = self._call("GET", self.prefix + "/items/" + validate_key(key) + "/file/view/url", parse=False)
        return file_url_to_path(raw.decode("utf-8").strip())

    def fulltext_of_item(self, key, index=0):
        pdfs = self.pdf_attachments(key)
        if len(pdfs) > 1:
            raise ValueError("Multiple PDFs; select an attachment key explicitly")
        return self.fulltext(pdfs[0]["key"]) if pdfs else None

    def select_uri(self, key):
        validate_key(key)
        scope = "library" if self.library == "users/0" else self.library
        return f"zotero://select/{scope}/items/{key}"

    def add_items(self, payload):
        if not 1 <= len(payload) <= 50:
            raise ValueError("Create between 1 and 50 items per batch")
        _, _, result = self._call("POST", self.prefix + "/items", write=True, data=payload)
        if result.get("failed"):
            details = {"successful_keys": [v["key"] for v in result.get("successful", {}).values()],
                       "failed_indices": list(result["failed"]), "unchanged": result.get("unchanged", {})}
            raise ZoteroError(400, json.dumps(result), "Batch partially failed; successful keys remain. Reconcile before retrying.", details=details)
        return result

    def _created_key(self, result):
        ok = result.get("successful", {})
        if len(ok) != 1:
            raise ZoteroError(502, "unexpected create response", "Creation uncertain; inspect library before retrying.")
        created = next(iter(ok.values()))
        key = created["key"]
        fresh = self.item(key)  # observable verification; no SQLite access
        if created.get("data") and fresh["data"] != created["data"]:
            raise ZoteroError(409, "create read-back changed", f"Created item {key} changed before verification; inspect before retrying.")
        return key

    def add_note(self, parent_key, note_html, tags=None):
        payload = {"itemType": "note", "note": note_html, "tags": [{"tag": t} for t in tags or []]}
        if parent_key:
            parent = self.item(parent_key)
            if parent["data"]["itemType"] in ("note", "annotation", "attachment"):
                raise ValueError("Attach reading notes to the bibliographic parent")
            payload["parentItem"] = parent_key
            for ch in self.children(parent_key):
                d = ch["data"]
                if d["itemType"] == "note" and equivalent_field("note", d.get("note"), note_html) and equivalent_field("tags", d.get("tags"), payload["tags"]):
                    return ch["key"]  # safe repeat after a previous completed request
        return self._created_key(self.add_items([payload]))

    def add_collection(self, name, parent=None):
        parent_key = self.resolve_collection(parent) if parent else False
        cols = [c for c in self.collections() if c["data"]["name"] == name
                and c["data"].get("parentCollection", False) == parent_key]
        if len(cols) == 1:
            return cols[0]["key"]
        if len(cols) > 1:
            raise ValueError("Duplicate sibling collections; resolve in Zotero first")
        payload = {"name": name, "parentCollection": parent_key}
        result = self._call("POST", self.prefix + "/collections", write=True, data=[payload])[2]
        if result.get("failed") or len(result.get("successful", {})) != 1:
            raise ZoteroError(400, json.dumps(result), "Collection creation failed; reconcile before retrying.")
        key = next(iter(result["successful"].values()))["key"]
        self._call("GET", self.prefix + "/collections/" + validate_key(key))
        return key

    def update_item(self, key, data, expected_version=None, current=None):
        cur = current or self.item(key)
        version = cur["version"] if expected_version is None else expected_version
        if cur["version"] != version:
            raise ZoteroError(412, "object changed")
        if any(k in data for k in ("key", "version")):
            raise ValueError("Do not supply key/version in changes")
        self._call("PATCH", self.prefix + "/items/" + validate_key(key), write=True, data=data,
                   headers={"If-Unmodified-Since-Version": version})
        fresh = self.item(key)
        for field, value in data.items():
            if not equivalent_field(field, fresh["data"].get(field), value):
                raise ZoteroError(409, "read-back mismatch", "Write/read-back differ; inspect normalization or concurrent edits.")
        return fresh

    def add_tags(self, key, tags):
        cur = self.item(key)
        merged = list(cur["data"].get("tags", []))  # preserve type and other fields
        have = {t["tag"] for t in merged}
        for tag in tags:
            if tag not in have:
                merged.append({"tag": tag})
                have.add(tag)
        return cur if merged == cur["data"].get("tags", []) else self.update_item(key, {"tags": merged}, current=cur)

    def organize(self, key, collections=(), tags=(), remove_collection=None):
        cur = self.item(key)
        if cur["data"].get("parentItem"):
            raise ValueError("Organize the top-level bibliographic item")
        merged = list(cur["data"].get("collections", []))
        for name in collections:
            col = self.resolve_collection(name)
            if col not in merged:
                merged.append(col)
        if remove_collection:
            col = self.resolve_collection(remove_collection)
            merged = [k for k in merged if k != col]
        old_tags = list(cur["data"].get("tags", []))
        have = {t["tag"] for t in old_tags}
        for tag in tags:
            if tag not in have:
                old_tags.append({"tag": tag})
                have.add(tag)
        return self.update_item(key, {"collections": merged, "tags": old_tags}, current=cur)

    def delete_item(self, key):
        cur = self.item(key)
        self._call("DELETE", self.prefix + "/items/" + validate_key(key), write=True,
                   headers={"If-Unmodified-Since-Version": cur["version"]})
        try:
            self.item(key)
        except ZoteroError as e:
            if e.status == 404:
                return {"deleted": key}
            raise
        raise ZoteroError(409, "delete not confirmed")

    def info(self):
        return {"api_base": self.base, "library": self.library, "server_id": self.server_id,
                "api_version": self.api_version, "schema_version": self.schema_version,
                "reported_zotero_version": self.zotero_version, "read": "verified",
                "local_write_supported": bool(self.server_id),
                "authorization": "key present; not write-tested" if self.can_write else "not authorized",
                "key_remembered": self._remember, "keyfile": str(self._keyfile), "read_retries": self.retries}

    def doctor(self):
        _, h, _ = self._call("GET", self.prefix + "/items/top?limit=1")
        return {"api": self.info(), "top_items": h.get("total-results"),
                "paths": zotero_paths(), "write_test": "skipped (read-only diagnostic)"}

    def upload_file(self, attachment_key, file_path):
        """Three-phase local upload to an existing stored attachment; resumable by key."""
        path = Path(file_path).expanduser().resolve(strict=True)
        size = path.stat().st_size
        if not path.is_file() or size >= 4 * 1024 ** 3:
            raise ValueError("File must be a regular file smaller than 4 GiB")
        current = self.item(attachment_key)["data"]
        if current.get("itemType") != "attachment" or current.get("linkMode") not in (0, 1, "imported_file", "imported_url"):
            raise ValueError("Upload target must be a stored-file attachment")
        digest = hashlib.md5(usedforsecurity=False)
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 ** 2), b""):
                digest.update(chunk)
        md5 = digest.hexdigest()
        condition = {"If-Match": current["md5"]} if current.get("md5") else {"If-None-Match": "*"}
        endpoint = self.prefix + "/items/" + validate_key(attachment_key) + "/file"
        params = {"md5": md5, "filename": path.name, "filesize": size, "mtime": path.stat().st_mtime_ns // 1000000}
        hdrs = dict(condition, **{"Content-Type": "application/x-www-form-urlencoded"})
        data = urllib.parse.urlencode(params).encode()
        auth = self._call("POST", endpoint, write=True, data=data, headers=hdrs)[2]
        if not auth.get("exists"):
            target = urllib.parse.urlsplit(auth["url"])
            if normalize_base(f"{target.scheme}://{target.netloc}") != self.base:
                raise ValueError("Upload URL does not point to the selected local Zotero")
            if not target.path.startswith("/api/local/uploads/") or target.query or target.fragment:
                raise ValueError("Unexpected upload URL")
            if auth.get("prefix") or auth.get("suffix"):
                raise ValueError("Unexpected local upload framing")
            # http.client streams the file; urllib otherwise loads multi-GB bytes in memory.
            import http.client
            conn = http.client.HTTPConnection(target.hostname, target.port, timeout=self.timeout)
            try:
                conn.putrequest("POST", target.path)
                conn.putheader("Content-Type", auth["contentType"])
                conn.putheader("Content-Length", str(size))
                conn.endheaders()
                with path.open("rb") as f:
                    for chunk in iter(lambda: f.read(1024 ** 2), b""):
                        conn.send(chunk)
                response = conn.getresponse()
                response.read()
                if response.status != 201:
                    raise ZoteroError(response.status, "file byte upload failed")
            except (OSError, http.client.HTTPException):
                raise ZoteroError(0, "upload interrupted", f"Upload outcome unknown; inspect attachment {attachment_key} before resuming.") from None
            finally:
                conn.close()
            self._call("POST", endpoint, write=True,
                       data=urllib.parse.urlencode({"upload": auth["uploadKey"]}).encode(), headers=hdrs)
        fresh = self.item(attachment_key)
        if fresh["data"].get("md5") != md5:
            raise ZoteroError(409, "hash read-back mismatch")
        return {"key": attachment_key, "md5": md5, "bytes": size, "verified": True}
