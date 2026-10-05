#!/usr/bin/env python3
"""Extract caption-located PDF figures (including vector art) as PNG crops.

Optional dependency: PyMuPDF in the selected environment. Pages are 1-based;
crop coordinates are PDF points. Inspect the resulting images before saving notes.
"""
import argparse
import json
import re
from pathlib import Path


def extract(pdf, out, pages=None, crops=None, dpi=180):
    try:
        import pymupdf as fitz
    except ImportError:
        raise SystemExit("Select an environment with PyMuPDF; install it in an isolated environment if needed.")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    with fitz.open(pdf) as doc:
        for number in pages or range(1, len(doc) + 1):
            page = doc[number - 1]
            lines = []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    lines.append(("".join(s["text"] for s in line["spans"]), fitz.Rect(line["bbox"])))
            captions = [(re.match(r"(?:Figure|Fig\.?|图)\s*(\d+)\s*[:.：]?", text, re.I), text, rect)
                        for text, rect in lines]
            captions = [(m.group(1), text, rect) for m, text, rect in captions if m]
            found = {f"figure-{identifier}" for identifier, _, _ in captions}
            for key, coords in (crops or {}).items():
                if coords[0] == number and key not in found:
                    captions.append((key.removeprefix("figure-"), key + " · manual crop", fitz.Rect(coords[1:])))
            drawings = [fitz.Rect(d["rect"]) for d in page.get_drawings()]
            images = [fitz.Rect(info["bbox"]) for info in page.get_image_info()]
            for identifier, caption, cap in captions:
                key = f"figure-{identifier}"
                manual = (crops or {}).get(key)
                if manual:
                    if manual[0] != number:
                        continue
                    rect = fitz.Rect(manual[1:])
                    method = "manual PDF-point crop"
                else:
                    # A caption anchors the diagram above it. Vector bounds include
                    # strokes; text bounds restore labels that extend beyond strokes.
                    candidates = [r for r in drawings + images if r.y1 <= cap.y0 + 2
                                  and r.y1 > cap.y0 - page.rect.height * .65
                                  and r.width > 2 and r.height > 2]
                    if not candidates:
                        continue
                    rect = fitz.Rect(candidates[0])
                    for r in candidates[1:]:
                        rect |= r
                    for _, r in lines:
                        if r.y1 <= cap.y0 and r.y0 >= rect.y0 - 20 and r.intersects(rect + (-20, -20, 20, 20)):
                            rect |= r
                    rect = (rect + (-8, -8, 8, 8)) & fitz.Rect(0, 0, page.rect.width, cap.y0 - 3)
                    method = "caption + vector/image bounds; visually review crop"
                if rect.is_empty or not page.rect.contains(rect):
                    raise ValueError(f"Crop outside PDF page: {key}")
                path = out / f"{key}.png"
                page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), clip=rect, alpha=False).save(path)
                results.append({"id": key, "file": path.name, "caption": caption,
                                "page": number, "bbox": list(rect), "method": method})
    (out / "figures.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pdf")
    p.add_argument("--out", required=True)
    p.add_argument("--pages", type=int, nargs="+")
    p.add_argument("--dpi", type=int, default=180)
    p.add_argument("--crop", action="append", default=[], help="figure-1:3:x0,y0,x1,y1; repeat to correct crops")
    a = p.parse_args()
    if not 36 <= a.dpi <= 600:
        p.error("Choose DPI between 36 and 600")
    crops = {}
    for value in a.crop:
        identifier, page, coords = value.split(":")
        crops[identifier] = [int(page), *map(float, coords.split(","))]
        if not re.fullmatch(r"figure-\d+", identifier) or len(crops[identifier]) != 5:
            p.error("Crop format: figure-1:3:x0,y0,x1,y1")
    print(json.dumps(extract(a.pdf, a.out, a.pages, crops, a.dpi), ensure_ascii=False, indent=2))
