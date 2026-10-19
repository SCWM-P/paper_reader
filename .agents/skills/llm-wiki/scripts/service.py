"""Shared operations over authoritative files."""
import json
import os
from .models import StoreError, basic_structure, questions, evidence, DIRECTORIES
from .codecs import load_record
from .repository import roots, resolve_record, record_paths, safe_path, atomic_write, file_hash
from . import links

def get_item(ref, item_id, workspace, store=None):
    records, errors = links.catalog(workspace, store)
    if ref not in records:
        ref = links.target(ref, records)
    loaded = records[ref]
    return {'status': 'ok', 'record': ref, 'path': str(resolve_record(ref, workspace, store)),
            'sha256': loaded['sha256'], 'item': links.item(loaded['data'], item_id), 'data': loaded['data'],
            'body': loaded['body'], 'content': loaded['raw'].decode('utf-8'), 'errors': errors}

def validate_links(ref, loaded, records):
    for link in links.outgoing(loaded, records):
        identity = link.get('question_id') or link.get('evidence_id')
        if identity:
            links.item(records[link['record']]['data'], identity)
    for question in questions(loaded['data']):
        if 'reader_current' not in question:
            continue
        obj = question['reader_current']
        items = [links.item(records[links.target(x['record'], records)]['data'], x['evidence_id'])
                 for x in obj['evidence_refs']]
        for item in items:
            owner = item.get('question_ref', {})
            if owner.get('record') != ref or owner.get('question_id') != question['id'] or item.get('scope') != obj['scope']:
                raise StoreError('理解证据的归属问题与适用范围必须匹配当前判断', path=ref)
        if obj.get('state') == 'demonstrated_in_scope' and (
                not obj.get('scope') or not any(x.get('kind') == 'demonstration' and
                x.get('scope') == obj['scope'] for x in items)):
            raise StoreError('理解判断需要同一范围内的实际表现依据', path=ref)

def identities(data):
    return [x.get('id', x.get('evidence_id')) for x in [data] + questions(data) + evidence(data)
            if x.get('id', x.get('evidence_id'))]

def check_store(workspace, store=None):
    workspace, store = roots(workspace, store)
    records, errors = links.catalog(workspace, store)
    warnings, owners, results = [], {}, []
    for ref, loaded in records.items():
        before = len(errors)
        try:
            validate_links(ref, loaded, records)
            for identity in identities(loaded['data']):
                if identity in owners:
                    raise StoreError('身份重复：' + identity + '；另一主记录：' + owners[identity])
                owners[identity] = ref
            if loaded['data']['type'] == 'source':
                from paper_reader.scripts.record_check import check_record
                report = check_record(loaded['data'])
                if report['status'] == 'warning':
                    warnings.append({'record': ref, 'reason': '论文存在降级模块或尚无实际问答', 'modules': report['modules']})
        except (StoreError, ValueError, KeyError, TypeError) as error:
            errors.append({'record': ref, 'reason': str(error)})
        results.append({'record': ref, 'status': 'error' if len(errors) > before else
                        'warning' if any(x['record'] == ref for x in warnings) else 'ok'})
    for required in ('README.md', *DIRECTORIES.values()):
        if not safe_path(store / required, workspace).exists():
            errors.append({'record': str(store / required), 'reason': '缺少知识库入口或目录'})
    return {'status': 'error' if errors else 'warning' if warnings else 'ok',
            'results': results, 'errors': errors, 'warnings': warnings,
            'hashes': {ref: loaded['sha256'] for ref, loaded in records.items()}}

def _reindex_store(workspace, store=None):
    workspace, store = roots(workspace, store)
    report = check_store(workspace, store)
    if report['errors']:
        raise StoreError(json.dumps(report['errors'], ensure_ascii=False))
    from .search import title_of
    records, _ = links.catalog(workspace, store)
    lines = ['# 知识索引', '', '由 paper wiki reindex 生成；主记录是事实来源。', '',
             '| 类型 | 标题 | 领域 | 主记录 |', '| --- | --- | --- | --- |']
    for ref, loaded in records.items():
        data = loaded['data']
        url = os.path.relpath(resolve_record(ref, workspace, store), store).replace(os.sep, '/').replace(' ', '%20')
        values = [data['type'], title_of(data), data.get('domain', ''), '[' + ref + '](' + url + ')']
        lines.append('| ' + ' | '.join(str(x).replace('|', '\\|').replace('\n', ' ') for x in values) + ' |')
    if {ref: file_hash(path) for ref, path in record_paths(workspace, store).items()} != report['hashes']:
        raise StoreError('索引期间主记录已改变', 'conflict')
    output = store / 'index.md'
    content = ('\n'.join(lines) + '\n').encode()
    if not output.exists() or output.read_bytes() != content:
        atomic_write(output, content, file_hash(output))
    return {'status': 'ok', 'path': str(output), 'sources': len(records), 'warnings': report['warnings']}

def init_store(workspace, store=None):
    from .locking import write_lock
    workspace, store = roots(workspace, store)
    with write_lock(workspace):
        store.mkdir(parents=True, exist_ok=True)
        for folder in DIRECTORIES.values():
            safe_path(store / folder, workspace).mkdir(exist_ok=True)
        if not (store / 'README.md').exists():
            atomic_write(store / 'README.md', ('# 公共知识库\n\n先用 paper wiki list 浏览，再用 paper wiki query 定向读取。\n\n'
                '概念与实体有来源不等于用户已经掌握；实际问答与理解证据只存于论文记录。\n\n'
                '[派生索引](index.md) 可用 paper wiki reindex 重建。\n').encode(), 'missing')
        return _reindex_store(workspace, store)

def list_records(workspace, store=None):
    from .search import title_of
    records, errors = links.catalog(workspace, store)
    rows = [{'record': ref, 'id': x['data'].get('id', ref), 'type': x['data']['type'],
             'title': title_of(x['data']), 'domain': x['data'].get('domain', ''),
             'tags': x['data'].get('tags', []), 'sha256': x['sha256'],
             'sources': len(x['data'].get('sources', []))} for ref, x in records.items()]
    return {'status': 'error' if errors else 'ok', 'records': rows, 'errors': errors}

def validate_candidate(candidate, ref, workspace, store):
    basic_structure(candidate['data'], ref)
    records, _ = links.catalog(workspace, store)
    records[ref] = candidate
    ids = identities(candidate['data'])
    if len(ids) != len(set(ids)):
        raise StoreError('记录中的身份重复', path=ref)
    for other, loaded in records.items():
        if other != ref and set(ids).intersection(identities(loaded['data'])):
            raise StoreError('身份已经属于另一主记录：' + other, path=ref)
        validate_links(other, loaded, records)

def preserve_fields(old, new):
    if isinstance(old, dict) and isinstance(new, dict):
        if not set(old).issubset(new):
            raise StoreError('保留现有字段：' + ', '.join(sorted(set(old) - set(new))))
        for key in old:
            preserve_fields(old[key], new[key])
    elif isinstance(old, list) and isinstance(new, list):
        for entry in old:
            if not isinstance(entry, dict):
                continue
            identity = next((k for k in ('id', 'source_id', 'evidence_id', 'target_id') if k in entry), None)
            if identity:
                match = next((x for x in new if isinstance(x, dict) and x.get(identity) == entry[identity]), None)
                if match is not None:
                    preserve_fields(entry, match)

def save_record(ref, content, expected, workspace, store=None):
    import re
    from .codecs import decode_record, digest
    from .locking import write_lock
    workspace, store = roots(workspace, store)
    if expected != 'missing' and not re.fullmatch('[0-9a-f]{64}', expected):
        raise StoreError('保存基准应为 SHA256 或 missing', 'invalid_path', ref)
    target = resolve_record(ref, workspace, store)
    candidate = decode_record(content, ref.startswith('papers/'))
    data = candidate['data']
    with write_lock(workspace):
        baseline = file_hash(target)
        if baseline != expected:
            raise StoreError('主记录已改变；请重新读取并合并修改', 'conflict', ref)
        if baseline != 'missing':
            old = load_record(target)['data']
            preserve_fields(old, data)
            if old['type'] != data['type'] or old.get('id') != data.get('id'):
                raise StoreError('不能改变记录身份', path=ref)
            if ref.startswith('papers/') and (
                {k: v for k, v in old.items() if k != 'Q & A'} != {k: v for k, v in data.items() if k != 'Q & A'}):
                raise StoreError('Wiki 编辑仅修改论文 Q & A；论文采集使用论文工作流', path=ref)
            for question in questions(old):
                same = [q for q in questions(data) if q.get('id') == question.get('id')]
                if len(same) != 1 or same[0].get('question') != question.get('question'):
                    raise StoreError('保留实际原问及稳定身份', path=ref)
            if any(entry not in evidence(data) for entry in evidence(old)):
                raise StoreError('保留已有证据；纠正应追加', path=ref)
        elif ref.startswith('papers/'):
            raise StoreError('先通过论文工作流建立完整论文记录', path=ref)
        validate_candidate(candidate, ref, workspace, store)
        if baseline != digest(content):
            atomic_write(target, content, expected)
        committed = file_hash(target)
        if committed != digest(content):
            raise StoreError('外部编辑器在保存后改变了记录', 'conflict', ref)
        result = {'status': 'ok', 'record': ref, 'sha256': committed,
                  'source': {'status': 'unchanged' if baseline == committed else 'saved'},
                  'html': {'status': 'not_applicable'}}
        try:
            result['index'] = _reindex_store(workspace, store)
        except (OSError, ValueError, KeyError, TypeError, StoreError) as error:
            result['index'] = {'status': 'error', 'reason': str(error)}
        if data['type'] == 'source':
            try:
                from .paper_adapter import render_paper
                result['html'] = render_paper(ref, workspace, committed)
            except (OSError, ValueError, KeyError, TypeError, ImportError, StoreError) as error:
                result['html'] = {'status': 'error', 'reason': str(error)}
        return result

def reindex_store(workspace, store=None):
    from .locking import write_lock
    with write_lock(workspace):
        return _reindex_store(workspace, store)

