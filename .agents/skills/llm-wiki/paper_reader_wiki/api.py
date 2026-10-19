"""Local browser API; only the registered paper and knowledge roots are exposed."""
import hmac
import json
from pathlib import Path
import secrets
from . import service
from .models import StoreError, new_id, DIRECTORIES
from .codecs import encode_record, load_record, digest
from .repository import roots, resolve_record, record_paths, safe_path
from .search import query, title_of
from . import links

def create_app(workspace, token=None, shutdown=None):
    from fastapi import FastAPI, Request
    from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    from markdown_it import MarkdownIt
    workspace, store = roots(workspace)
    token = token or secrets.token_urlsafe(32)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost'])
    assets = Path(__file__).parent / 'static'
    markdown = MarkdownIt('commonmark', {'html': False})
    app.state.access_token = token

    @app.middleware('http')
    async def guard(request: Request, call_next):
        if request.url.path.startswith('/api/'):
            if not hmac.compare_digest(request.headers.get('x-wiki-token', ''), token):
                return JSONResponse({'reason': 'Reload the local Paper Reader page to renew API access'}, status_code=403)
            origin = request.headers.get('origin')
            if origin and origin != str(request.base_url).rstrip('/'):
                return JSONResponse({'reason': 'Cross-origin requests are not allowed'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
        if request.url.path.startswith('/archive/'):
            response.headers['Content-Security-Policy'] = 'sandbox allow-scripts; frame-ancestors \'none\''
            # Sandboxed notes have an opaque origin. Their token-protected media
            # must remain embeddable without granting notes API-origin access.
            if not response.headers.get('content-type', '').startswith('text/html'):
                response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        return response

    @app.exception_handler(StoreError)
    async def store_error(request: Request, error: StoreError):
        return JSONResponse({'code': error.code, 'reason': str(error), 'path': error.path},
                            status_code=409 if error.code == 'conflict' else 404 if error.code == 'not_found' else 400)

    @app.exception_handler(ValueError)
    async def value_error(request: Request, error: ValueError):
        return JSONResponse({'reason': str(error)}, status_code=400)

    @app.exception_handler(OSError)
    async def io_error(request: Request, error: OSError):
        return JSONResponse({'reason': str(error)}, status_code=404 if isinstance(error, FileNotFoundError) else 500)

    @app.get('/')
    def index(request: Request):
        # Loopback landing page bootstraps same-origin API access; no URL secret.
        return HTMLResponse((assets / 'index.html').read_text().replace('__TOKEN__', token))

    @app.get('/api/server/status')
    def server_status():
        import os
        return {'status': 'running', 'workspace': str(workspace), 'pid': os.getpid()}

    @app.post('/api/server/stop')
    def server_stop():
        if shutdown is None:
            raise StoreError('This server is not managed by paper wiki serve')
        from starlette.background import BackgroundTask
        return JSONResponse({**server_status(), 'status': 'stopping'}, background=BackgroundTask(shutdown))

    @app.get('/api/records')
    def records():
        return service.list_records(workspace)

    @app.get('/api/record')
    def record(record: str, id: str | None = None):
        result = service.get_item(record, id, workspace)
        result['body_html'] = markdown.render(result['body'])
        if result['data']['type'] == 'source':
            from .paper_adapter import paper_view
            from paper_reader.scripts.record_check import check_record
            result['completeness'] = check_record(result['data'])
            result['view'] = paper_view(result['data'])
            record = result['record']
            key = digest(record.encode())
            result['note_url'] = '/archive/' + token + '/' + key + '/note.html'
            pdf = result['data'].get('paper', {}).get('file')
            if pdf:
                root = resolve_record(record, workspace).parent.parent
                import os
                path = safe_path(Path(os.path.abspath(resolve_record(record, workspace).parent / pdf)), root)
                result['pdf_url'] = '/archive/' + token + '/' + key + '/' + path.relative_to(root).as_posix()
        catalog, errors = links.catalog(workspace)
        result['backlinks'], result['links'], result['link_targets'] = [], [], {}
        for ref, loaded in catalog.items():
            if ref == result['record']:
                continue
            try:
                if any(link['record'] == result['record'] for link in links.outgoing(loaded, catalog)):
                    result['backlinks'].append({'record': ref, 'title': title_of(loaded['data'])})
            except (ValueError, OSError, StoreError) as error:
                errors.append({'record': ref, 'reason': str(error)})
                continue
        try:
            result['links'] = list(links.outgoing(catalog[result['record']], catalog))
            for name in links.body_links(result['body']):
                result['link_targets'][name] = links.target(name.split('#', 1)[0], catalog)
        except StoreError as error:
            errors.append({'record': result['record'], 'reason': str(error)})
        result['errors'] = errors
        return result

    @app.get('/api/query')
    def search(q: str = '', tag: str | None = None, domain: str | None = None,
               type: str | None = None, id: str | None = None,
               record: str | None = None, limit: int = 20):
        return query(workspace, q, tag=tag, domain=domain, kind=type, identity=id, record=record, limit=limit)

    @app.get('/api/graph')
    def graph(focus: str | None = None, kind: str | None = None, limit: int = 200, include_questions: bool = False):
        from .graph import build_graph
        return build_graph(workspace, focus=focus, kind=kind, limit=limit, include_questions=include_questions)

    @app.get('/api/draft')
    def draft(kind: str):
        from datetime import datetime, timezone
        if kind not in (*DIRECTORIES, 'overview'):
            raise StoreError('选择可编辑的知识页面类型')
        now = datetime.now(timezone.utc).isoformat()
        data = {'type': kind, 'id': new_id('c' if kind == 'concept' else 'p'), 'title': '',
                'tags': [], 'related': [], 'domain': '', 'scope': '', 'sources': [],
                'question_refs': [], 'created': now, 'updated': now}
        if kind == 'concept':
            data.update(aliases=[], definition='', relations=[],
                        consensus={'status': 'unverified', 'source_refs': []})
        ref = 'store:overview.md' if kind == 'overview' else 'store:' + DIRECTORIES[kind] + '/' + data['id'] + '.md'
        if resolve_record(ref, workspace).exists():
            raise StoreError('该页面已存在，请编辑现有记录', 'conflict', ref)
        return {'record': ref, 'data': data, 'body': '\n\n', 'sha256': 'missing', 'draft': True}

    @app.post('/api/save')
    def save(payload: dict):
        if not isinstance(payload, dict) or not all(k in payload for k in ('record', 'data', 'expected')):
            raise StoreError('Save requires record, data and expected')
        ref = payload['record']
        path = resolve_record(ref, workspace)
        original = load_record(path) if path.exists() else None
        data = payload['data']
        if not isinstance(data, dict):
            raise StoreError('data must be an object')
        from .models import basic_structure
        basic_structure(data, ref)
        body = payload.get('body') if data.get('type') != 'source' else None
        if body is not None and not isinstance(body, str):
            raise StoreError('Page body must be Markdown text')
        content = encode_record(data, original, body=body)
        return service.save_record(ref, content, payload['expected'], workspace)

    @app.post('/api/reindex')
    def reindex():
        return service.reindex_store(workspace)

    @app.get('/archive/{access}/{key}/{asset:path}')
    def archive(access: str, key: str, asset: str):
        if not hmac.compare_digest(access, token):
            raise StoreError('Invalid archive link', 'not_found')
        refs = {digest(ref.encode()): path for ref, path in record_paths(workspace).items() if ref.startswith('papers/')}
        if key not in refs:
            raise StoreError('Paper not found', 'not_found')
        root = refs[key].parent.parent
        if not asset or any(part in ('', '.', '..', 'tmp') or part.startswith('.') for part in asset.split('/')):
            raise StoreError('Unsupported paper resource', 'invalid_path')
        path = safe_path(root / asset, root)
        allowed = {'.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif',
                   '.pdf', '.mp4', '.webm', '.vtt', '.woff', '.woff2', '.ttf', '.json'}
        if path.suffix.lower() not in allowed or not path.is_file():
            raise StoreError('Resource not found', 'not_found')
        return FileResponse(path)

    import paper_reader
    math = Path(paper_reader.__file__).parent / 'assets' / 'vendor' / 'katex'
    app.mount('/math', StaticFiles(directory=math), name='math')
    app.mount('/static', StaticFiles(directory=assets), name='static')
    return app

def serve(workspace, port, *, json_output=False):
    import socket
    import uvicorn
    from .locking import write_lock
    from . import lifecycle
    workspace, store = roots(workspace)
    if not 1 <= port <= 65535:
        raise StoreError('Port must be between 1 and 65535')
    token = secrets.token_urlsafe(32)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    def shutdown():
        server.should_exit = True
    app = create_app(workspace, token, shutdown)
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, log_level='warning'))
    try:
        with write_lock(workspace):
            if lifecycle.status(workspace)['status'] == 'running':
                raise StoreError('This workspace already has a service. Use paper wiki status or paper wiki stop.')
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('127.0.0.1', port))
            listener.listen(128)
            listener.setblocking(False)
            lifecycle.register(workspace, port, token)
        if json_output:
            import json
            print(json.dumps({'status': 'running', 'url': f'http://127.0.0.1:{port}/',
                              'workspace': str(workspace), 'stop': 'paper wiki stop'}), flush=True)
        else:
            print('Paper Reader: http://127.0.0.1:' + str(port) + '/', flush=True)
            print('关闭：Ctrl+C，或在另一终端执行 paper wiki stop（同一工作区）。', flush=True)
        server.run(sockets=[listener])
    finally:
        listener.close()
        with write_lock(workspace):
            lifecycle.unregister(workspace, token)
