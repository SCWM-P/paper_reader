"""Shared reading content for HTML pages and searchable Zotero notes."""
from __future__ import annotations


def author_names(metadata):
    authors = metadata.get("author")
    if authors:
        if isinstance(authors, str):
            return [authors]
        if isinstance(authors, list):
            return [str(a) if not isinstance(a, dict) else a.get("name") or
                    " ".join(filter(None, (a.get("firstName"), a.get("lastName")))) for a in authors]
        raise ValueError("metadata.author must be a string or list")
    creators = metadata.get("creators", [])
    return [c.get("name") or " ".join(filter(None, (c.get("firstName"), c.get("lastName"))))
            for c in creators if c.get("creatorType", "author") == "author"]


def normalize_record(record, parent_metadata=None):
    if not isinstance(record, dict):
        raise ValueError("Reading record must be an object")
    result = dict(record)
    legacy = "metadata" not in record
    metadata = record.get("metadata", parent_metadata or record.get("paper", {}))
    if not isinstance(metadata, dict):
        raise ValueError("metadata must contain the collected metadata object")
    # Both editable Zotero items and collect reports can be reused directly.
    if isinstance(metadata.get("item"), dict):
        metadata = dict(metadata["item"], provenance={k:v for k,v in metadata.items() if k != "item"})
    metadata = dict(metadata)
    if legacy and not metadata.get('title'):
        metadata['title']=record.get('title','')
    if parent_metadata:
        for key, value in parent_metadata.items():
            if key not in {"key", "version", "collections", "tags", "relations", "dateAdded", "dateModified"} and value:
                metadata.setdefault(key, value)
    if not metadata.get("title"):
        raise ValueError("metadata.title is required")
    authors = [a for a in author_names(metadata) if a.strip()]
    if not authors and not legacy:
        raise ValueError("Supply metadata.author or the pipeline's verified creators")
    metadata["author"] = authors or ["作者待补全"]
    result["metadata"] = metadata
    if not isinstance(result.get("summary"), str) or not result["summary"].strip():
        raise ValueError("summary must contain the concise reading conclusion")
    highlights = result.get("highlights", [] if legacy else None)
    if isinstance(highlights, str):
        highlights = [highlights]
    if not isinstance(highlights, list):
        raise ValueError("highlights must be text or a list of contributions")
    result["highlights"] = highlights
    qa = result.get("Q & A", result.get("qa", [] if legacy else None))
    if not isinstance(qa, list):
        raise ValueError("Q & A must be a list of question/answer objects; use [] until discussion is recorded")
    for entry in qa:
        if not isinstance(entry, dict) or not isinstance(entry.get("question"), str) or not entry["question"].strip():
            raise ValueError("Each Q & A entry requires question text")
        if not isinstance(entry.get("answer", ""), str):
            raise ValueError("Q & A answer must be text")
    result["Q & A"] = qa
    others = result.get("others", [])
    if isinstance(others, str):
        others = [{"title":"补充阅读", "content":others}]
    elif isinstance(others, dict):
        others = [dict(value, title=value.get("title",key)) if isinstance(value,dict)
                  else {"title":key,"content":value} for key,value in others.items()]
    if not isinstance(others, list) or not all(isinstance(x, dict) for x in others):
        raise ValueError("others must be optional text, named sections, or a list of section objects")
    others = list(others)
    # Existing records remain readable while new sessions use the four core fields.
    for key, title in (("figures","论文原图"),("equations","公式与张量"),("visualizations","交互计算与架构"),
                       ("evidence","证据与出处")):
        if result.get(key):
            others.append({"id":"visual-lab" if key == "visualizations" else key,"title":title,key:result[key]})
    if legacy:
        for key, title in (("read_scope","阅读范围"),("limitations","适用范围"),("questions","后续问题"),("next_steps","下一次继续")):
            if result.get(key):
                others.append({"id":key.replace("_","-"),"title":title,"content":result[key]})
    result["others"] = others
    for key in ("figures","equations","visualizations","evidence","read_scope","limitations","questions","next_steps","qa"):
        result.pop(key, None)
    result.setdefault("title", str(metadata["title"]) + " · 阅读笔记")
    return result
