"""Paper views and HTML rendering reuse the existing paper implementation."""
from .repository import resolve_record, safe_path, atomic_write, file_hash
from .codecs import load_record
from .models import StoreError

def paper_view(data):
    from paper_reader.scripts.reading_record import normalize_record
    return normalize_record(data)

def render_paper(ref, workspace, expected):
    from paper_reader.scripts.html_note import render
    path = resolve_record(ref, workspace)
    record = load_record(path)
    if record['sha256'] != expected:
        raise StoreError('Paper changed before rendering', 'conflict', path)
    output = safe_path(path.parent.parent / 'note.html', workspace)
    baseline = file_hash(output)
    html = render(record['data'], asset_base=path.parent, output_base=output.parent)
    if file_hash(path) != expected:
        raise StoreError('Paper changed during rendering', 'conflict', path)
    atomic_write(output, html.encode(), baseline)
    return {'status': 'ok', 'path': str(output)}
