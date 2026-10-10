"""Shared current-format reading content for HTML pages and searchable Zotero notes."""
from __future__ import annotations
from .learning_record import normalize_learning
from .record_check import check_record


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
    report = check_record(record)
    errors = [name + ": " + row["message"] for name, row in report["modules"].items() if row["status"] == "error"]
    if errors:
        raise ValueError("；".join(errors))
    result = dict(record)
    metadata = record["metadata"]
    # Collected reports and editable Zotero metadata are both current pipeline inputs.
    if isinstance(metadata.get("item"), dict):
        metadata = dict(metadata["item"], provenance={k: v for k, v in metadata.items() if k != "item"})
    metadata = dict(metadata)
    if parent_metadata:
        for key, value in parent_metadata.items():
            if key not in {"key", "version", "collections", "tags", "relations", "dateAdded", "dateModified"} and value:
                metadata.setdefault(key, value)
    if not metadata.get("title"):
        raise ValueError("metadata.title is required")
    authors = [a for a in author_names(metadata) if a.strip()]
    if not authors:
        raise ValueError("Supply metadata.author or the pipeline's verified creators")
    metadata["author"] = authors
    result["metadata"] = metadata
    highlights = record["highlights"]
    result["highlights"] = [highlights] if isinstance(highlights, str) else highlights
    qa = record["Q & A"]
    if not isinstance(qa, list):
        raise ValueError("Q & A must be a list; use [] until discussion is recorded")
    for entry in qa:
        if not isinstance(entry, dict) or not isinstance(entry.get("question"), str) or not entry["question"].strip():
            raise ValueError("Each Q & A entry requires question text")
        if not isinstance(entry.get("answer", ""), str):
            raise ValueError("Q & A answer must be text")
    others = record.get("others", [])
    if isinstance(others, str):
        others = [{"title": "补充阅读", "content": others}]
    elif isinstance(others, dict):
        others = [dict(value, title=value.get("title", key)) if isinstance(value, dict)
                  else {"title": key, "content": value} for key, value in others.items()]
    if not isinstance(others, list) or not all(isinstance(entry, dict) for entry in others):
        raise ValueError("others must be optional text, named sections, or a list of section objects for rendering")
    result["others"] = [dict(entry) for entry in others]
    for entry in result["others"]:
        if "learning" in entry:
            entry["learning"] = normalize_learning(entry["learning"])
    result.setdefault("title", str(metadata["title"]) + " · 阅读笔记")
    return result
