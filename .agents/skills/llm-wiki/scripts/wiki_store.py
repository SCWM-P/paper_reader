#!/usr/bin/env python3
"""Small offline store for editable knowledge and actual reading conversations."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata
import uuid

START = '<!-- llm-wiki:data:v1 -->'
END = '<!-- /llm-wiki:data -->'
INDEX_START = '<!-- llm-wiki:index:start -->'
INDEX_END = '<!-- llm-wiki:index:end -->'
UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
DEFAULT = '.runtime/llm_wiki'


class StoreError(Exception):
    def __init__(self, message, code='invalid_record', path=None):
        super().__init__(message)
        self.code, self.path = code, str(path) if path else None


def new_id(prefix):
    return prefix + '_' + str(uuid.uuid4())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_hash(path):
    return digest(Path(path).read_bytes()) if Path(path).exists() else 'missing'


def safe_path(path, root):
    path, root = Path(path).absolute(), Path(root).resolve()
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        raise StoreError('Path is outside the allowed root', 'invalid_path', path)
    current = root
    for part in parts:
        if part in ('.', '..'):
            raise StoreError('Dot path components are forbidden', 'invalid_path', path)
        current = current / part
        if current.is_symlink():
            raise StoreError('Learning paths must not be symbolic links', 'invalid_path', current)
    return path


def roots(workspace, store=None):
    workspace = Path(workspace).resolve()
    if not (workspace / 'AGENTS.md').is_file() or not (workspace / 'papers').is_dir():
        raise StoreError('Workspace must contain AGENTS.md and papers/', 'invalid_path', workspace)
    safe_path(workspace / 'papers', workspace)
    store = Path(store or DEFAULT)
    store = safe_path(store if store.is_absolute() else workspace / store, workspace)
    relative = store.relative_to(workspace).as_posix()
    if relative != DEFAULT and not re.fullmatch(r'\.runtime/llm_wiki-migrations/m_' + UUID + '/candidate', relative):
        raise StoreError('Use the active store or an explicit migration candidate', 'invalid_path', store)
    return workspace, store


def resolve_record(ref, workspace, store=None):
    workspace, store = roots(workspace, store)
    if not isinstance(ref, str) or '\\' in ref:
        raise StoreError('Use a logical POSIX record reference', 'invalid_path')
    relative = ref[6:] if ref.startswith('store:') else ref
    parts = relative.split('/')
    if not relative or any(p in ('', '.', '..') for p in parts):
        raise StoreError('Absolute, empty, and dot path components are forbidden', 'invalid_path', ref)
    if ref.startswith('store:'):
        if relative != 'unassigned.md' and not re.fullmatch('concepts/c_' + UUID + r'\.md', relative):
            raise StoreError('Unsupported learning record', 'invalid_path', ref)
        return safe_path(store / relative, workspace)
    if len(parts) < 4 or parts[0] != 'papers' or parts[-2:] != ['assets', 'reading-record.json']:
        raise StoreError('Only exact papers/**/assets/reading-record.json references are allowed', 'invalid_path', ref)
    return safe_path(workspace / relative, workspace)


def record_paths(workspace, store=None, papers=None):
    workspace, store = roots(workspace, store)
    refs = ['store:unassigned.md'] if (store / 'unassigned.md').exists() else []
    safe_path(store / 'concepts', workspace)
    refs += ['store:concepts/' + p.name for p in sorted((store / 'concepts').glob('*.md'))]
    if papers is not None:
        refs += papers
    else:
        for directory, dirs, files in os.walk(workspace / 'papers', followlinks=False):
            dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
            if Path(directory).name == 'assets' and 'reading-record.json' in files:
                refs.append((Path(directory) / 'reading-record.json').relative_to(workspace).as_posix())
    return {ref: resolve_record(ref, workspace, store) for ref in sorted(set(refs))}


def load_record(path):
    path = Path(path)
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig' if path.suffix == '.json' else 'utf-8')
    before = after = None
    if path.suffix == '.json':
        data = json.loads(text)
    else:
        if text.count(START) != 1 or text.count(END) != 1:
            raise StoreError('Expected one v1 data block', path=path)
        begin, finish = text.index(START) + len(START), text.index(END)
        match = re.fullmatch(r'\s*```json\s*\n(.*?)\n```\s*', text[begin:finish], re.S)
        if not match:
            raise StoreError('Expected one JSON fence inside the data block', path=path)
        data = json.loads(match[1])
        before, after = text[:begin + match.start(1)], text[begin + match.end(1):]
    if not isinstance(data, dict):
        raise StoreError('Record must be an object', path=path)
    if path.suffix != '.json' and data.get('schema_version') != 1:
        raise StoreError('Unsupported schema_version; preserve the original', path=path)
    return {'data': data, 'raw': raw, 'sha256': digest(raw), 'before': before, 'after': after}


def encode_record(data, original=None, title='学习记录'):
    body = json.dumps(data, ensure_ascii=False, indent=2)
    if original and original['before'] is not None:
        return (original['before'] + body + original['after']).encode()
    if original:
        return (body + '\n').encode()
    return ('# ' + title + '\n\n' + START + '\n```json\n' + body + '\n```\n' + END + '\n\n## 用户自由笔记\n\n').encode()


def questions(data):
    value = data.get('Q & A', data.get('questions', []))
    if not isinstance(value, list) or not all(isinstance(q, dict) for q in value):
        raise StoreError('Questions must be an array of objects')
    return value


def evidence(data):
    return data.get('reader_evidence', []) + [e for q in questions(data) for e in q.get('reader_evidence', [])]


def basic_structure(data, ref):
    """Only invariants needed to locate and save records; semantics remain with the AI."""
    if ref.startswith('store:concepts/') and data.get('id') != Path(ref[6:]).stem:
        raise StoreError('Concept ID must match its filename', path=ref)
    for q in questions(data):
        if 'moved_to' in q:
            moved = q['moved_to']
            if ref != 'store:unassigned.md' or not isinstance(moved, dict) or moved.get('question_id') != q.get('id') or 'question' in q or 'answer' in q:
                raise StoreError('Invalid unassigned redirect', path=ref)
        elif not isinstance(q.get('question'), str) or not q['question'].strip() or not isinstance(q.get('answer', ''), str):
            raise StoreError('Questions need original text and a string answer; use an empty string before answering', path=ref)
        if 'id' in q and not re.fullmatch('q_' + UUID, str(q['id'])):
            raise StoreError('Question ID must be q_UUID4', path=ref)
    for e in evidence(data):
        if not isinstance(e, dict) or not re.fullmatch('e_' + UUID, str(e.get('evidence_id', ''))):
            raise StoreError('Evidence ID must be e_UUID4', path=ref)


def get_item(ref, item_id, workspace, store=None, seen=None):
    seen = set(seen or ())
    if (ref, item_id) in seen:
        raise StoreError('Redirect cycle', path=ref)
    seen.add((ref, item_id))
    path = resolve_record(ref, workspace, store)
    loaded = load_record(path)
    data = loaded['data']
    basic_structure(data, ref)
    item = data
    if item_id:
        if item_id == data.get('id'):
            if data.get('record_status') == 'merged':
                target = data['redirect_to']
                return get_item('store:concepts/' + target + '.md', target, workspace, store, seen)
        else:
            matches = [x for x in questions(data) + evidence(data) if x.get('id', x.get('evidence_id')) == item_id]
            if len(matches) > 1:
                raise StoreError('Duplicate ID within the record', path=ref)
            if not matches:
                redirects = [q['moved_to'] for q in questions(data) if item_id in q.get('moved_to', {}).get('evidence_ids', [])]
                if len(redirects) == 1:
                    return get_item(redirects[0]['record'], item_id, workspace, store, seen)
                raise StoreError('Item not found', 'not_found', ref)
            item = matches[0]
            if 'moved_to' in item:
                return get_item(item['moved_to']['record'], item['moved_to']['question_id'], workspace, store, seen)
    return {'status': 'ok', 'record': ref, 'path': str(path), 'sha256': loaded['sha256'], 'item': item}


def _fold(value):
    return unicodedata.normalize('NFKC', value).casefold()


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def find(query, workspace, store=None, papers=None):
    matches, errors = [], []
    for ref, path in record_paths(workspace, store, papers).items():
        try:
            data = load_record(path)['data']
            basic_structure(data, ref)
            context = {k: data[k] for k in ('id', 'name', 'aliases', 'domain', 'scope') if k in data}
            rows = [('concept', data)] if context else []
            rows += [('question', q) for q in questions(data) if 'moved_to' not in q]
            rows += [('evidence', e) for e in evidence(data)]
            for kind, row in rows:
                haystack = context if kind == 'concept' else row
                if any(_fold(query) in _fold(s) for s in _strings(haystack)):
                    matches.append({'record': ref, 'kind': kind, 'context': context, 'item': row,
                                    'status': 'legacy_unanchored' if kind == 'question' and not row.get('id') else 'current'})
        except (StoreError, OSError, ValueError) as error:
            errors.append({'record': ref, 'reason': str(error)})
    return {'status': 'error' if errors else 'ok', 'matches': matches, 'errors': errors}


def _references(value):
    if isinstance(value, dict):
        if isinstance(value.get('record'), str):
            yield value
        for child in value.values():
            yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


def check_store(workspace, store=None):
    workspace, store = roots(workspace, store)
    errors, warnings, hashes, owners = [], [], {}, {}
    for ref, path in record_paths(workspace, store).items():
        try:
            loaded = load_record(path)
            data = loaded['data']
            basic_structure(data, ref)
            hashes[ref] = loaded['sha256']
            for item in questions(data) + evidence(data):
                key = item.get('id', item.get('evidence_id'))
                if key and 'moved_to' not in item:
                    if key in owners:
                        errors.append({'record': ref, 'reason': 'Duplicate full owner: ' + key, 'other': owners[key]})
                    owners[key] = ref
            for reference in _references(data):
                target = resolve_record(reference['record'], workspace, store)
                key = reference.get('question_id', reference.get('evidence_id'))
                if key:
                    get_item(reference['record'], key, workspace, store)
                elif not target.exists():
                    warnings.append({'record': ref, 'reason': 'Missing source: ' + reference['record']})
            if data.get('record_status') == 'merged':
                get_item(ref, data['id'], workspace, store)
        except (StoreError, OSError, ValueError, KeyError, TypeError) as error:
            errors.append({'record': ref, 'reason': str(error)})
    for required in ('README.md', 'unassigned.md', 'concepts'):
        if not safe_path(store / required, workspace).exists():
            errors.append({'record': required, 'reason': 'Missing store entry'})
    return {'status': 'error' if errors else ('warning' if warnings else 'ok'), 'errors': errors, 'warnings': warnings, 'hashes': hashes}


def atomic_write(path, raw, expected=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if expected is not None and file_hash(path) != expected:
            raise StoreError('Target changed; reread and merge user edits', 'conflict', path)
        os.replace(temporary, path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def init_store(workspace, store=None):
    workspace, store = roots(workspace, store)
    if store.exists():
        return check_store(workspace, store)
    if store == workspace / DEFAULT and (workspace / '.runtime/paper_tutor').exists():
        raise StoreError('Back up and migrate the legacy store first', 'migration_required', store)
    runtime = safe_path(workspace / '.runtime', workspace)
    runtime.mkdir(exist_ok=True)
    ignore = safe_path(runtime / '.gitignore', workspace)
    raw = ignore.read_bytes() if ignore.exists() else b''
    if b'*' not in raw.splitlines():
        atomic_write(ignore, raw + (b'\n' if raw and not raw.endswith(b'\n') else b'') + b'*\n', file_hash(ignore))
    store.mkdir(parents=True)
    (store / 'concepts').mkdir()
    atomic_write(store / 'unassigned.md', encode_record({'schema_version': 1, 'questions': [], 'reader_evidence': [], 'revisions': []}, title='待归属实际问题'))
    atomic_write(store / 'README.md', ('# llm-wiki 本地知识与学习记录\n\n个人记录不进入 Git。没有记录不表示用户已经掌握。\n\n## 用户备注\n\n' + INDEX_START + '\n' + INDEX_END + '\n').encode())
    return reindex_store(workspace, store)


def reindex_store(workspace, store=None):
    workspace, store = roots(workspace, store)
    readme = safe_path(store / 'README.md', workspace)
    expected = file_hash(readme)
    original = readme.read_text() if readme.exists() else '# llm-wiki 本地知识与学习记录\n\n'
    report = check_store(workspace, store)
    errors = [e for e in report['errors'] if e['record'] != 'README.md']
    if errors:
        raise StoreError(json.dumps(errors, ensure_ascii=False), path=readme)
    lines = [INDEX_START, '<!-- llm-wiki:hashes ' + json.dumps(report['hashes'], ensure_ascii=False, sort_keys=True) + ' -->',
             '', '| ID | 名称或原问题 | 领域与范围 | 状态 | 主记录 |', '| --- | --- | --- | --- | --- |']
    def row(values):
        return '| ' + ' | '.join(str(v).replace('|', '\\|').replace('\n', ' ') for v in values) + ' |'
    paths = record_paths(workspace, store)
    for ref, path in paths.items():
        data = load_record(path)['data']
        link = '[' + ref + '](' + os.path.relpath(path, store).replace(os.sep, '/').replace(' ', '%20') + ')'
        if 'name' in data:
            lines.append(row([data['id'], data['name'] + ' / ' + '、'.join(data.get('aliases', [])), data.get('domain', '') + ' / ' + data.get('scope', ''), data.get('record_status', 'active') + '; ' + data.get('reader', {}).get('current', {}).get('state', 'unknown'), link]))
        for q in questions(data):
            lines.append(row([q.get('id', 'legacy_unanchored'), q.get('question', '转存入口')[:100], data.get('scope', ''), 'moved' if 'moved_to' in q else q.get('resolution', 'legacy_recorded'), link]))
    lines.append(INDEX_END)
    block = '\n'.join(lines)
    if original.count(INDEX_START) == original.count(INDEX_END) == 1 and original.index(INDEX_START) < original.index(INDEX_END):
        result = original[:original.index(INDEX_START)] + block + original[original.index(INDEX_END) + len(INDEX_END):]
    elif INDEX_START not in original and INDEX_END not in original:
        result = original + '\n' + block + '\n'
    else:
        raise StoreError('Ambiguous index markers; preserve notes and repair explicitly', path=readme)
    if {ref: file_hash(path) for ref, path in record_paths(workspace, store).items()} != report['hashes']:
        raise StoreError('Sources changed during index generation', 'conflict', readme)
    if result.encode() != (readme.read_bytes() if readme.exists() else b''):
        atomic_write(readme, result.encode(), expected)
    return {'status': 'ok', 'path': str(readme), 'sha256': file_hash(readme), 'sources': len(paths), 'warnings': report['warnings']}


def save_candidate(target_ref, candidate_path, expected, op_id, workspace, store=None):
    workspace, store = roots(workspace, store)
    target = resolve_record(target_ref, workspace, store)
    if not re.fullmatch('op_' + UUID, op_id):
        raise StoreError('Operation ID must be op_UUID4', 'invalid_path')
    if expected != 'missing' and not re.fullmatch('[0-9a-f]{64}', expected):
        raise StoreError('Expected baseline must be SHA256 or missing')
    supplied = Path(candidate_path)
    supplied = safe_path(supplied if supplied.is_absolute() else workspace / supplied, workspace)
    directory = safe_path(store / '.pending' / op_id, workspace)
    candidate = safe_path(directory / ('candidate' + target.suffix), workspace)
    if supplied != candidate:
        raise StoreError('Candidate must be this store .pending/op_UUID4/candidate.md or candidate.json', 'invalid_path', supplied)
    loaded = load_record(candidate)
    basic_structure(loaded['data'], target_ref)
    metadata = safe_path(directory / 'operation.json', workspace)
    operation = {'op_id': op_id, 'target': target_ref, 'expected_sha256': expected, 'candidate_sha256': loaded['sha256'], 'phase': 'prepared'}
    if metadata.exists():
        previous = json.loads(metadata.read_text())
        if any(previous.get(k) != operation[k] for k in ('op_id', 'target', 'expected_sha256', 'candidate_sha256')):
            raise StoreError('Operation ID already belongs to a different save; preserve both candidates', 'conflict', metadata)
    else:
        with metadata.open('x', encoding='utf-8') as stream:
            json.dump(operation, stream, ensure_ascii=False, indent=2)
            stream.flush(); os.fsync(stream.fileno())
    current_hash = file_hash(target)
    if current_hash == loaded['sha256']:
        status = 'unchanged'
    else:
        if current_hash != expected:
            raise StoreError('Target changed; reread and merge user edits', 'conflict', target)
        if target_ref.startswith('papers/') and current_hash == 'missing':
            raise StoreError('Create the ordinary paper record first; temporarily keep the question in unassigned.md', path=target_ref)
        if target.exists():
            base = load_record(target)
            old, new = base['data'], loaded['data']
            if target_ref.startswith('papers/'):
                if {k: v for k, v in old.items() if k != 'Q & A'} != {k: v for k, v in new.items() if k != 'Q & A'}:
                    raise StoreError('Wiki save may change only Q & A in a paper record', 'conflict', target)
            elif (base['before'], base['after']) != (loaded['before'], loaded['after']):
                raise StoreError('Candidate changes free notes; preserve the current notes and merge only the data block', 'conflict', target)
            for q in questions(old):
                same = [n for n in questions(new) if (n.get('id') == q['id'] if q.get('id') else n.get('question') == q.get('question'))]
                if not same or (q.get('id') and len(same) != 1) or ('moved_to' not in same[0] and q.get('question') != same[0].get('question')):
                    raise StoreError('Preserve each existing original question and stable ID', 'conflict', target)
            moved = {e for q in questions(new) for e in q.get('moved_to', {}).get('evidence_ids', [])}
            for entry in evidence(old):
                if entry not in evidence(new) and not (target_ref == 'store:unassigned.md' and entry['evidence_id'] in moved):
                    raise StoreError('Preserve actual evidence; add corrections as new entries', 'conflict', target)
            backup = safe_path(store / '.backups' / op_id / ('base' + target.suffix), workspace)
            if backup.exists() and file_hash(backup) != base['sha256']:
                raise StoreError('Backup belongs to a different baseline', 'conflict', backup)
            if not backup.exists():
                atomic_write(backup, base['raw'])
        atomic_write(target, loaded['raw'], expected)
        if file_hash(target) != loaded['sha256']:
            raise StoreError('Target changed after replacement; preserve later edits', 'conflict', target)
        status = 'committed'
    operation['phase'] = 'committed'
    atomic_write(metadata, (json.dumps(operation, ensure_ascii=False, indent=2) + '\n').encode())
    return {'status': status, 'record': target_ref, 'path': str(target), 'sha256': loaded['sha256'], 'recoverable_path': str(candidate)}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise StoreError(message, 'invalid_argument')


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--workspace', default='.')
    parser.add_argument('--store')
    commands = parser.add_subparsers(dest='command', required=True, parser_class=Parser)
    for command in ('init', 'get', 'find', 'save', 'check', 'reindex'):
        child = commands.add_parser(command)
        child.add_argument('--workspace', default=argparse.SUPPRESS)
        child.add_argument('--store', default=argparse.SUPPRESS)
        if command == 'get':
            child.add_argument('--record', required=True); child.add_argument('--id')
        if command == 'find':
            child.add_argument('--query', required=True); child.add_argument('--paper', action='append')
        if command == 'save':
            child.add_argument('--target', required=True); child.add_argument('--candidate', required=True)
            child.add_argument('--expect', required=True); child.add_argument('--op-id', required=True)
    args = None
    try:
        args = parser.parse_args(argv)
        workspace, store = roots(args.workspace, args.store)
        if args.command == 'init': result = init_store(workspace, store)
        elif args.command == 'get': result = get_item(args.record, args.id, workspace, store)
        elif args.command == 'find': result = find(args.query, workspace, store, args.paper)
        elif args.command == 'save': result = save_candidate(args.target, args.candidate, args.expect, args.op_id, workspace, store)
        elif args.command == 'check': result = check_store(workspace, store)
        else: result = reindex_store(workspace, store)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('errors') else 0
    except (StoreError, OSError, ValueError, KeyError, TypeError) as error:
        recoverable = None
        if args and args.command == 'save':
            try:
                workspace, store = roots(args.workspace, args.store)
                target = resolve_record(args.target, workspace, store)
                candidate = safe_path(store / '.pending' / args.op_id / ('candidate' + target.suffix), workspace)
                load_record(candidate)
                recoverable = str(candidate)
            except (StoreError, OSError, ValueError):
                pass
        code = getattr(error, 'code', 'io_error' if isinstance(error, OSError) else 'invalid_record')
        print(json.dumps({'status': 'error', 'code': code, 'reason': str(error), 'path': getattr(error, 'path', None), 'recoverable_path': recoverable}, ensure_ascii=False, indent=2))
        return {'invalid_path': 2, 'invalid_argument': 2, 'conflict': 3, 'migration_required': 3, 'io_error': 4}.get(code, 1)


if __name__ == '__main__':
    raise SystemExit(main())
