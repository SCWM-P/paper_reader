"""YAML frontmatter for knowledge; paper JSON remains authoritative."""
from pathlib import Path
import hashlib
import json
import re
import yaml
from .models import StoreError

INDEX_START = '<!-- llm-wiki:index:start -->'
INDEX_END = '<!-- llm-wiki:index:end -->'

class MetadataLoader(yaml.SafeLoader):
    pass

# Keep dates as source strings; do not silently manufacture times.
MetadataLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in values if tag != 'tag:yaml.org,2002:timestamp']
    for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
}

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def decode_record(raw, paper=False):
    text = raw.decode('utf-8-sig')
    body = ''
    if paper:
        data = json.loads(text)
    else:
        match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
        if not match:
            raise StoreError('知识记录必须以 YAML frontmatter 开始')
        try:
            data = yaml.load(match[1], Loader=MetadataLoader)
        except yaml.YAMLError as error:
            raise StoreError('YAML 解析失败：' + str(error)) from error
        body = text[match.end():]
    if not isinstance(data, dict):
        raise StoreError('记录必须是对象')
    return {'data': data, 'raw': raw, 'sha256': digest(raw), 'body': body}

def load_record(path):
    path = Path(path)
    return decode_record(path.read_bytes(), path.suffix == '.json')

def encode_record(data, original=None, body=None):
    if data.get('type') == 'source':
        return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()
    if body is None:
        body = original['body'] if original else ''
    metadata = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000)
    return ('---\n' + metadata + '---\n' + body).encode()
