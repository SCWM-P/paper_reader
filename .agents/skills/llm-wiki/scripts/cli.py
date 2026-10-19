"""浏览公共知识、定向查询、保存记录和运行本地界面。"""
import argparse
import json
import sys
from pathlib import Path
from .models import StoreError, TYPES
from . import service
from .search import query, browse
from .presentation import Parser, emit

COMMANDS = {
    'list': '浏览概念与实体标题；不接受检索筛选',
    'query': '按关键词、标签、领域、类型或身份定向查询',
    'save': '按保存基准写入候选记录',
    'check': '检查记录、身份和引用',
    'init': '初始化配置选择的知识目录',
    'reindex': '从主记录重建索引',
    'graph': '查看明确引用构成的关系图',
    'serve': '启动本地浏览器界面',
    'status': '查看本工作区服务状态',
    'stop': '正常关闭服务并释放端口',
}
def main(argv=None, *, prog=None):
    parser = Parser(prog=prog or 'paper wiki', description=__doc__,
        epilog="常用示例\n  paper wiki list --all\n  paper wiki query 'attention'\n  paper wiki query --type source\n  paper wiki serve\n  paper wiki stop")
    parser.add_argument('--workspace', default='.', help='工作区目录（默认当前目录）')
    parser.add_argument('--json', action='store_true', help='输出完整结构化结果')
    commands = parser.add_subparsers(dest='command', required=True, metavar='COMMAND')
    children = {}
    for command, description in COMMANDS.items():
        child = commands.add_parser(command, description=description)
        children[command] = child
        child.add_argument('--workspace', default=argparse.SUPPRESS, help='工作区目录')
        child.add_argument('--json', action='store_true', default=argparse.SUPPRESS, help='输出完整结构化结果')
        if command == 'list':
            child.add_argument('--all', action='store_true', help='不截断数量或标题长度')
        elif command == 'query':
            child.add_argument('keyword', nargs='?', default='', help='全文关键词')
            for field in ('tag', 'domain', 'id', 'record'):
                child.add_argument('--'+field, help={'tag':'标签', 'domain':'领域', 'id':'稳定身份（精确读取）', 'record':'逻辑记录路径（精确读取）'}[field])
            child.add_argument('--type', choices=TYPES, help='记录类型')
            child.add_argument('--limit', type=int, default=20, help='普通查询最多返回条数（默认20）')
        elif command == 'save':
            child.add_argument('--target', required=True, help='目标逻辑路径')
            child.add_argument('--candidate', required=True, help='候选文件；- 表示标准输入')
            child.add_argument('--expect', required=True, help='基准 SHA256；新记录用 missing')
        elif command == 'graph':
            child.add_argument('--focus', help='节点稳定身份或记录路径')
            child.add_argument('--kind', choices=('concept', 'source', 'question'), help='关系类别')
            child.add_argument('--limit', type=int, default=200, help='节点数量上限')
            child.add_argument('--include-questions', action='store_true', help='附带论文实际问答节点')
        elif command == 'serve':
            child.add_argument('--port', type=int, default=8765, help='本机端口（默认8765）')
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        parser.print_help()
        return 0
    args = parser.parse_args(argv)
    try:
        if args.command == 'list':
            result = browse(args.workspace, all=args.all)
        elif args.command == 'query':
            if not any((args.keyword, args.tag, args.domain, args.type, args.id, args.record)):
                children['query'].print_help()
                return 0
            result = query(args.workspace, args.keyword, tag=args.tag, domain=args.domain,
                           kind=args.type, identity=args.id, record=args.record, limit=args.limit)
        elif args.command == 'save':
            content = sys.stdin.buffer.read() if args.candidate == '-' else Path(args.candidate).read_bytes()
            result = service.save_record(args.target, content, args.expect, args.workspace)
        elif args.command in ('init', 'check', 'reindex'):
            result = getattr(service, args.command+'_store')(args.workspace)
        elif args.command == 'graph':
            from .graph import build_graph
            result = build_graph(args.workspace, focus=args.focus, kind=args.kind, limit=args.limit, include_questions=args.include_questions)
        elif args.command in ('status', 'stop'):
            from . import lifecycle
            result = getattr(lifecycle, args.command)(args.workspace)
        else:
            from .api import serve
            serve(args.workspace, args.port, json_output=args.json)
            return 0
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            emit(result, args.command)
        return 1 if result.get('errors') or result.get('status') in ('error', 'unreachable') else 0
    except (StoreError, OSError, ValueError, KeyError, TypeError, ImportError) as error:
        code = getattr(error, 'code', 'dependency_missing' if isinstance(error, ImportError) else 'io_error' if isinstance(error, OSError) else 'invalid_record')
        result = {'status':'error', 'code':code, 'reason':str(error), 'path':getattr(error,'path',None)}
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            emit(result, args.command if args.command not in ('check','graph','list') else 'error')
        return {'usage':2, 'invalid_path':2, 'conflict':3, 'io_error':4}.get(code, 1)

