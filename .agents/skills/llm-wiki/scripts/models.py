"""Single current contract for knowledge and paper records."""
import re
import uuid
from urllib.parse import urlsplit

UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
DIRECTORIES = {'entity': 'entities', 'concept': 'concepts', 'query': 'queries',
               'comparison': 'comparisons', 'synthesis': 'synthesis'}
TYPES = ('entity', 'concept', 'source', 'query', 'comparison', 'synthesis', 'overview')

class StoreError(Exception):
    def __init__(self, message, code='invalid_record', path=None):
        super().__init__(message)
        self.code, self.path = code, str(path) if path else None

def new_id(prefix):
    return prefix + '_' + str(uuid.uuid4())

def nonempty(value):
    return isinstance(value, str) and bool(value.strip())

def valid_source_url(value):
    if not nonempty(value) or any(c.isspace() for c in value):
        return False
    try:
        url = urlsplit(value)
        return (url.scheme in ('http', 'https') and bool(url.hostname)
                and not url.username and not url.password
                and (url.port is None or 1 <= url.port <= 65535))
    except ValueError:
        return False

def questions(data):
    value = data.get('Q & A', [])
    if not isinstance(value, list) or not all(isinstance(q, dict) for q in value):
        raise StoreError('Q & A 必须是对象数组')
    return value

def evidence(data):
    value = data.get('reader_evidence', [])
    if not isinstance(value, list):
        raise StoreError('reader_evidence 必须是数组')
    for q in questions(data):
        if not isinstance(q.get('reader_evidence', []), list):
            raise StoreError('reader_evidence 必须是数组')
    return value + [entry for q in questions(data) for entry in q.get('reader_evidence', [])]

def walk_objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_objects(child)

def references(data):
    for obj in walk_objects(data):
        if isinstance(obj.get('record'), str):
            yield obj
    for target in data.get('related', []):
        yield {'target_id': target}
    for relation in data.get('relations', []):
        yield {'target_id': relation['target_id']}
    if data.get('redirect_to'):
        yield {'target_id': data['redirect_to']}
    for obj in walk_objects(data):
        for target in obj.get('concept_refs', []):
            yield {'target_id': target}

def basic_structure(data, ref):
    if not isinstance(data, dict) or data.get('type') not in TYPES:
        raise StoreError('记录缺少有效 type', path=ref)
    if 'schema_version' in data:
        raise StoreError('记录不能包含文件级版本号', path=ref)
    kind = data['type']
    if ref.startswith('papers/'):
        if kind != 'source':
            raise StoreError('论文记录必须使用 source 类型', path=ref)
        from paper_reader.scripts.record_check import check_record
        if check_record(data)['status'] == 'error':
            raise StoreError('论文必要模块检查失败', path=ref)
    else:
        expected = 'store:overview.md' if kind == 'overview' else 'store:' + DIRECTORIES.get(kind, '?') + '/'
        if (kind == 'overview' and ref != expected) or (kind != 'overview' and not ref.startswith(expected)):
            raise StoreError('记录类型与目录不一致', path=ref)
        if not re.fullmatch(('c_' if kind == 'concept' else 'p_') + UUID, str(data.get('id', ''))):
            raise StoreError('知识记录需要稳定 UUID4 身份', path=ref)
        if not isinstance(data.get('title'), str) or not data['title'].strip():
            raise StoreError('记录标题不能为空', path=ref)
        for field in ('tags', 'related'):
            if not isinstance(data.get(field), list) or not all(isinstance(x, str) for x in data[field]):
                raise StoreError(field + ' 必须是字符串数组', path=ref)
        for field in ('created', 'updated'):
            if field not in data or (data[field] is not None and not isinstance(data[field], str)):
                raise StoreError(field + ' 必须是时间字符串或 null', path=ref)
        forbidden = {'questions', 'Q & A', 'reader', 'reader_current', 'reader_evidence',
                     'moved_to', 'intended_record', 'name', 'created_at', 'updated_at', 'related_refs'}
        if any(forbidden.intersection(obj) for obj in walk_objects(data)):
            raise StoreError('知识记录只保存当前公共知识字段；个人问答与理解证据属于论文 Q & A', path=ref)
        for field in ('domain', 'scope', 'definition'):
            if field in data and not isinstance(data[field], str):
                raise StoreError(field + ' 必须是字符串', path=ref)
        if kind == 'concept':
            if not all(nonempty(data.get(field)) for field in ('domain', 'scope', 'definition')):
                raise StoreError('概念的 domain、scope、definition 不能为空', path=ref)
            consensus = data.get('consensus', {})
            if not isinstance(consensus, dict) or consensus.get('status') not in ('verified', 'unverified'):
                raise StoreError('概念需要共识核实状态', path=ref)
            if consensus['status'] == 'verified' and not consensus.get('source_refs'):
                raise StoreError('verified 必须引用来源依据', path=ref)
    for field in ('sources', 'question_refs', 'relations'):
        if not isinstance(data.get(field, []), list) or not all(isinstance(x, dict) for x in data.get(field, [])):
            raise StoreError(field + ' 必须是对象数组', path=ref)
    for field in ('tags', 'aliases'):
        if field in data and (not isinstance(data[field], list) or not all(isinstance(x, str) for x in data[field])):
            raise StoreError(field + ' 必须是字符串数组', path=ref)
    source_ids = [s.get('source_id') for s in data.get('sources', [])]
    if any(not nonempty(s) for s in source_ids) or len(source_ids) != len(set(source_ids)):
        raise StoreError('source_id 不能为空或重复', path=ref)
    for source in data.get('sources', []):
        if not (nonempty(source.get('record')) or nonempty(source.get('url'))):
            raise StoreError('来源需要非空 record 或有效的 HTTP(S) url', path=ref)
        if 'record' in source and not nonempty(source['record']):
            raise StoreError('来源 record 不能为空', path=ref)
        if 'url' in source and not valid_source_url(source['url']):
            raise StoreError('来源 url 必须是有效的 HTTP(S) 地址', path=ref)
    for obj in walk_objects(data):
        if 'source_refs' in obj and (not isinstance(obj['source_refs'], list) or any(x not in source_ids for x in obj['source_refs'])):
            raise StoreError('source_refs 引用了未知来源', path=ref)
    for link in data.get('question_refs', []):
        if not str(link.get('record', '')).startswith('papers/') or not re.fullmatch('q_' + UUID, str(link.get('question_id', ''))):
            raise StoreError('question_refs 只能引用论文问答', path=ref)
    for relation in data.get('relations', []):
        if relation.get('type') not in ('requires', 'uses', 'contrasts_with') or not isinstance(relation.get('target_id'), str):
            raise StoreError('无效的关系类型或目标', path=ref)
        if not isinstance(relation.get('scope'), str) or not isinstance(relation.get('source_refs'), list):
            raise StoreError('概念关系需要适用范围和来源', path=ref)
    qids = []
    if 'reader_current' in data:
        raise StoreError('reader_current 必须放在所属问答中', path=ref)
    for q in questions(data):
        if not re.fullmatch('q_' + UUID, str(q.get('id', ''))):
            raise StoreError('实际问题需要 q_UUID4', path=ref)
        qids.append(q['id'])
        if q.get('question_form') not in ('exact', 'legacy_recorded') or not isinstance(q.get('question'), str) or not q['question'].strip():
            raise StoreError('实际问题需要原问与来源形式', path=ref)
        if not isinstance(q.get('answer'), str) or q.get('resolution', 'answered') not in ('answered', 'partial', 'unanswered'):
            raise StoreError('无效的答复或状态', path=ref)
        if 'reader_current' in q:
            current = q['reader_current']
            if not isinstance(current, dict) or current.get('state') not in ('unknown', 'uncertain', 'demonstrated_in_scope', 'forgotten'):
                raise StoreError('reader_current 需要有效的 state', path=ref)
            if not nonempty(current.get('scope')) or not isinstance(current.get('evidence_refs'), list):
                raise StoreError('reader_current 需要非空 scope 和 evidence_refs 数组', path=ref)
            if current['state'] != 'unknown' and not current['evidence_refs']:
                raise StoreError('理解判断必须引用实际证据', path=ref)
            for link in current['evidence_refs']:
                if not isinstance(link, dict) or link.get('record') != ref or not re.fullmatch('e_' + UUID, str(link.get('evidence_id', ''))):
                    raise StoreError('理解判断必须引用同一论文中的 e_UUID4', path=ref)
        if not isinstance(q.get('reader_evidence', []), list):
            raise StoreError('reader_evidence 必须是数组', path=ref)
        for entry in q.get('reader_evidence', []):
            if (not isinstance(entry, dict) or not isinstance(entry.get('question_ref'), dict)
                    or entry['question_ref'].get('question_id') != q['id']):
                raise StoreError('问答中的证据必须归属当前问题', path=ref)
    if len(qids) != len(set(qids)):
        raise StoreError('问题 ID 重复', path=ref)
    for entry in evidence(data):
        if not isinstance(entry, dict) or not re.fullmatch('e_' + UUID, str(entry.get('evidence_id', ''))):
            raise StoreError('理解证据需要 e_UUID4', path=ref)
        if entry.get('kind') not in ('self_report', 'demonstration', 'inference', 'forgotten', 'correction'):
            raise StoreError('无效的证据类型', path=ref)
        if not nonempty(entry.get('actual')) or not nonempty(entry.get('scope')):
            raise StoreError('证据需要实际表现和适用范围', path=ref)
        owner = entry.get('question_ref', {})
        if not isinstance(owner, dict) or owner.get('record') != ref or owner.get('question_id') not in qids:
            raise StoreError('理解证据必须引用同一论文中的实际问题', path=ref)
