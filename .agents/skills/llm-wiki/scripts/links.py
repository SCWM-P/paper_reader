"""One explicit reference resolver shared by validation, UI and graphs."""
import re
from pathlib import PurePosixPath
from .models import StoreError, basic_structure, questions, evidence, references
from .codecs import load_record
from .repository import record_paths

def catalog(workspace, store=None):
    records, errors = {}, []
    for ref, path in record_paths(workspace, store).items():
        try:
            loaded = load_record(path)
            basic_structure(loaded['data'], ref)
            records[ref] = loaded
        except (StoreError, OSError, ValueError, KeyError, TypeError) as error:
            errors.append({'record': ref, 'reason': str(error)})
    return records, errors

def target(value, records):
    if not isinstance(value, str):
        raise StoreError('引用目标必须是字符串')
    value = value.removesuffix('.md')
    matches = []
    for ref, loaded in records.items():
        data = loaded['data']
        if value in (ref.removesuffix('.md'), data.get('id'), PurePosixPath(ref).stem,
                     ref.removeprefix('store:').removesuffix('.md')):
            matches.append(ref)
    if len(matches) != 1:
        raise StoreError(('引用不唯一：' if matches else '引用不存在：') + value, 'invalid_reference')
    return matches[0]

def body_links(body):
    # Code examples are not knowledge references.
    plain = re.sub(r'(?ms)^\s*(`{3,}|~{3,}).*?^\s*\1\s*$', '', body)
    plain = re.sub(r'`[^`]*`', '', plain)
    return re.findall(r'(?<!!)\[\[([^\]|\n]+)(?:\|[^\]\n]*)?\]\]', plain)

def outgoing(loaded, records):
    for link in references(loaded['data']):
        ref = target(link.get('record') or link.get('target_id'), records)
        yield {**link, 'record': ref}
    for name in body_links(loaded['body']):
        name = name.split('#', 1)[0]
        yield {'record': target(name, records), 'kind': 'wikilink'}

def item(data, identity):
    if not identity or identity == data.get('id'):
        return data
    candidates = [x for x in questions(data) + evidence(data) if x.get('id', x.get('evidence_id')) == identity]
    if len(candidates) != 1:
        raise StoreError('条目不存在或身份重复：' + identity, 'not_found')
    return candidates[0]
