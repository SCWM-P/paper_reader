"""Intentional queries and bounded, unfiltered knowledge browsing."""
import unicodedata
from .models import questions, evidence, StoreError
from . import links

def fold(value):
    return unicodedata.normalize('NFKC', value).casefold()

def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)

def title_of(data):
    metadata = data.get('metadata', {})
    metadata = metadata.get('item', metadata)
    return data.get('title') or metadata.get('title') or '无标题记录'

def excerpt(row, body, terms):
    fields = ('question', 'answer', 'definition', 'summary', 'highlights',
              'observation', 'basis', 'content', 'scope')
    candidates = [text for field in fields for text in strings(row.get(field))]
    candidates += [line for line in body.splitlines() if line.strip() and not line.startswith('#')]
    matching = [text for text in candidates if terms and any(t in fold(text) for t in terms)]
    if not matching and terms:
        matching = [text for text in strings(row) if any(t in fold(text) for t in terms)]
    text = (matching or candidates or [title_of(row)])[0]
    offset = min((fold(text).find(t) for t in terms if t in fold(text)), default=0)
    start = max(0, offset-35)
    return ('…' if start else '') + text[start:start+240] + ('…' if len(text)>start+240 else '')

def browse(workspace, store=None, all=False):
    from .service import list_records
    catalog = list_records(workspace, store)
    rows = sorted((r for r in catalog['records'] if r['type'] in ('concept', 'entity')),
                  key=lambda r: (r['type'], r['domain'], fold(r['title']), r['id']))
    shown, length = [], 0
    for row in rows:
        title = row['title']
        if not all:
            title = title[:117] + '…' if len(title) > 120 else title
            if len(shown) == 50 or length + len(title) + len(row['domain']) + 20 > 7800:
                break
        shown.append({**row, 'display_title': title})
        length += len(title) + len(row['domain']) + 20
    return {'status': catalog['status'], 'records': shown, 'total': len(rows),
            'shown': len(shown), 'remaining': len(rows) - len(shown), 'errors': catalog['errors']}

def query(workspace, text='', *, tag=None, domain=None, kind=None, identity=None, record=None, limit=20, store=None):
    if not any((text.strip(), tag, domain, kind, identity, record)):
        raise StoreError('请提供关键词或筛选条件；无预期浏览使用 paper wiki list', 'usage')
    if limit < 1:
        raise StoreError('limit 必须大于零', 'usage')
    records, errors = links.catalog(workspace, store)
    terms = fold(text).split()
    exact = identity is not None or record is not None
    matches = []
    selected = links.target(record, records) if record else None
    for ref, loaded in records.items():
        data = loaded['data']
        if selected and ref != selected:
            continue
        if kind and data['type'] != kind:
            continue
        if tag and fold(tag) not in [fold(t) for t in data.get('tags', [])]:
            continue
        if domain and fold(domain) != fold(data.get('domain', '')):
            continue
        rows = [(data['type'], data, loaded['body'])]
        rows += [('question', q, '') for q in questions(data)]
        rows += [('evidence', e, '') for e in evidence(data)]
        if record and not identity:
            rows = rows[:1]
        for row_kind, row, body in rows:
            key = row.get('id', row.get('evidence_id', ref))
            if identity and identity != key:
                continue
            plain = '\n'.join(strings(row)) + '\n' + body
            normalized = fold(plain)
            if any(term not in normalized for term in terms):
                continue
            score = sum(5 if t in fold(title_of(data)) else 1 for t in terms)
            matches.append({'record': ref, 'type': data['type'], 'kind': row_kind, 'title': title_of(data),
                            'id': key, 'snippet': excerpt(row, body, terms),
                            'score': score, 'tags': data.get('tags', []), 'domain': data.get('domain', '')})
    matches.sort(key=lambda x: (-x['score'], x['record'], x['id']))
    if exact:
        if len(matches) != 1:
            raise StoreError('精确读取没有唯一匹配结果', 'not_found')
        from .service import get_item
        hit = matches[0]
        return get_item(hit['record'], hit['id'] if hit['kind'] in ('question', 'evidence') else None, workspace, store)
    return {'status': 'error' if errors else 'ok', 'matches': matches[:limit],
            'total': len(matches), 'remaining': max(0, len(matches)-limit), 'errors': errors}

