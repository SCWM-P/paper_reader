"""Workspace service discovery and authenticated graceful shutdown."""
import json
import os
import time
from urllib.error import URLError
from urllib.request import Request, build_opener, ProxyHandler
from .models import StoreError
from .repository import roots, safe_path, atomic_write, file_hash, runtime_root

def registry_path(workspace):
    workspace, _ = roots(workspace)
    store = runtime_root(workspace)
    return safe_path(store / 'server.json', workspace)

def read_registry(workspace):
    path = registry_path(workspace)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if data.get('workspace') != str(roots(workspace)[0]) or not isinstance(data.get('port'), int) or not 1 <= data['port'] <= 65535:
        raise StoreError('Invalid service registry', path=path)
    if not isinstance(data.get('token'), str) or not data['token']:
        raise StoreError('Missing service identity', path=path)
    return data

def request(data, action, method='GET'):
    url = 'http://127.0.0.1:' + str(data['port']) + '/api/server/' + action
    req = Request(url, headers={'x-wiki-token': data['token']}, method=method)
    with build_opener(ProxyHandler({})).open(req, timeout=2) as response:
        value = json.load(response)
    if value.get('workspace') != data['workspace'] or value.get('pid') != data['pid']:
        raise StoreError('The responding service does not match this workspace')
    return value

def status(workspace):
    data = read_registry(workspace)
    if data is None:
        return {'status': 'stopped', 'reason': 'No service registered for this workspace'}
    try:
        value = request(data, 'status')
    except (URLError, TimeoutError, OSError, ValueError) as error:
        return {'status': 'unreachable', 'pid': data['pid'], 'port': data['port'], 'reason': str(error)}
    return {**value, 'url': 'http://127.0.0.1:' + str(data['port']) + '/'}

def stop(workspace):
    data = read_registry(workspace)
    if data is None:
        return {'status': 'stopped', 'reason': 'No service registered for this workspace'}
    request(data, 'stop', 'POST')
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        current = read_registry(workspace)
        if current is None or current['token'] != data['token']:
            return {'status': 'stopped', 'pid': data['pid'], 'port': data['port'], 'listener': 'closed'}
        time.sleep(0.1)
    raise StoreError('Shutdown requested; service is still finishing requests. Run paper wiki status again.')

def register(workspace, port, token):
    path = registry_path(workspace)
    data = {'workspace': str(roots(workspace)[0]), 'pid': os.getpid(), 'port': port, 'token': token}
    atomic_write(path, json.dumps(data).encode(), file_hash(path))
    path.chmod(0o600)

def unregister(workspace, token):
    data = read_registry(workspace)
    if data and data['token'] == token:
        registry_path(workspace).unlink()
