"""Allowed source files and atomic replacement."""
import os
import re
import tempfile
from pathlib import Path
from .models import StoreError, DIRECTORIES
from .codecs import digest

DEFAULT = '.runtime/llm_wiki'

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
    import tomllib
    config = workspace / 'pyproject.toml'
    settings = tomllib.loads(config.read_text()) if config.exists() else {}
    configured = settings.get('tool', {}).get('paper-reader', {}).get('wiki', {}).get('root', DEFAULT)
    if configured not in (DEFAULT, 'wiki'):
        raise StoreError('知识库配置只允许 wiki 或 .runtime/llm_wiki', 'invalid_path')
    store = Path(store or configured)
    store = safe_path(store if store.is_absolute() else workspace / store, workspace)
    if store != workspace / configured:
        raise StoreError('Use the active knowledge store', 'invalid_path', store)
    return workspace, store

def runtime_root(workspace):
    workspace, _ = roots(workspace)
    return safe_path(workspace / '.runtime' / 'llm_wiki', workspace)


def resolve_record(ref, workspace, store=None):
    workspace, store = roots(workspace, store)
    if not isinstance(ref, str) or '\\' in ref:
        raise StoreError('Use a logical POSIX record reference', 'invalid_path')
    relative = ref[6:] if ref.startswith('store:') else ref
    parts = relative.split('/')
    if not relative or any(p in ('', '.', '..') for p in parts):
        raise StoreError('Absolute, empty, and dot path components are forbidden', 'invalid_path', ref)
    if ref.startswith('store:'):
        if relative != 'overview.md' and not (len(parts) == 2 and parts[0] in DIRECTORIES.values() and parts[1].endswith('.md') and not parts[1].startswith('.')):
            raise StoreError('Unsupported learning record', 'invalid_path', ref)
        return safe_path(store / relative, workspace)
    if len(parts) < 4 or parts[0] != 'papers' or parts[-2:] != ['assets', 'reading-record.json']:
        raise StoreError('Only exact papers/**/assets/reading-record.json references are allowed', 'invalid_path', ref)
    return safe_path(workspace / relative, workspace)


def record_paths(workspace, store=None, papers=None):
    workspace, store = roots(workspace, store)
    refs = []
    for directory in DIRECTORIES.values():
        safe_path(store / directory, workspace)
        refs += ['store:' + directory + '/' + p.name for p in sorted((store / directory).glob('*.md'))]
    if (store / 'overview.md').exists():
        refs.append('store:overview.md')
    if papers is not None:
        refs += papers
    else:
        for directory, dirs, files in os.walk(workspace / 'papers', followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in ('ref_repository', 'tmp', 'node_modules') and not (Path(directory) / d).is_symlink())
            if Path(directory).name == 'assets' and 'reading-record.json' in files:
                refs.append((Path(directory) / 'reading-record.json').relative_to(workspace).as_posix())
    return {ref: resolve_record(ref, workspace, store) for ref in sorted(set(refs))}



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
