"""Graph derived from the same reference resolver used by validation."""
from .models import StoreError, questions
from . import links
from .search import title_of

def build_graph(workspace, store=None, focus=None, kind=None, limit=200, include_questions=False):
    if not 1 <= limit <= 1000:
        raise StoreError('图谱数量范围为 1–1000')
    records, errors = links.catalog(workspace, store)
    nodes, edges = {}, []
    for ref, loaded in records.items():
        data = loaded['data']
        nodes[ref] = {'id': data.get('id', ref), 'record': ref, 'type': data['type'],
                      'title': title_of(data), 'domain': data.get('domain', '')}
        if include_questions:
            for q in questions(data):
                nodes[q['id']] = {'id': q['id'], 'record': ref, 'item_id': q['id'],
                                  'type': 'question', 'title': q['question']}
    def edge(source, target, category, label):
        value = {'source': nodes[source]['id'], 'target': nodes[target]['id'], 'kind': category, 'label': label}
        if value not in edges:
            edges.append(value)
    for ref, loaded in records.items():
        data = loaded['data']
        try:
            for link in links.outgoing(loaded, records):
                target = link['record']
                if target == ref:
                    continue
                category = 'source' if nodes[target]['type'] == 'source' else 'concept'
                edge(ref, target, category, link.get('kind') or link.get('locator') or '关联')
            for relation in data.get('relations', []):
                edge(ref, links.target(relation['target_id'], records), 'concept', relation['type'])
            if include_questions:
                for q in questions(data):
                    edge(ref, q['id'], 'question', '实际问答')
                for link in data.get('question_refs', []):
                    edge(ref, link['question_id'], 'question', '问答引用')
        except (StoreError, KeyError) as error:
            errors.append({'record': ref, 'reason': str(error)})
    by_id = {n['id']: n for n in nodes.values()}
    if kind:
        edges = [e for e in edges if e['kind'] == kind]
    chosen = set(by_id)
    if focus:
        focus = nodes[focus]['id'] if focus in nodes else focus
        if focus not in by_id:
            raise StoreError('图谱节点不存在', 'not_found')
        chosen = {focus}
        for e in edges:
            if focus in (e['source'], e['target']):
                chosen.update((e['source'], e['target']))
    ordered = sorted(chosen, key=lambda key: (key != focus, by_id[key]['title']))
    visible = set(ordered[:limit])
    return {'nodes': [by_id[k] for k in ordered[:limit]],
            'edges': [e for e in edges if e['source'] in visible and e['target'] in visible],
            'total_nodes': len(chosen), 'truncated': len(chosen) > limit, 'errors': errors}

