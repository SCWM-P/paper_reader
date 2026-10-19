"""Consistent terminal presentation; JSON is an explicit transport."""
import argparse
import io
import os
import sys
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

def console(file=None):
    return Console(file=file or sys.stdout, no_color='NO_COLOR' in os.environ,
                   width=None if sys.stdout.isatty() else 100, highlight=False)

class Parser(argparse.ArgumentParser):
    def format_help(self):
        buffer = io.StringIO()
        out = console(buffer)
        out.print(self.prog, style='bold cyan')
        if self.description:
            out.print(self.description)
        out.print()
        out.print(self.format_usage().strip(), style='dim', markup=False)
        for group in self._action_groups:
            actions = [a for a in group._group_actions if a.help != argparse.SUPPRESS]
            if not actions:
                continue
            table = Table(box=None, show_header=False, padding=(0, 2))
            table.add_column(style='cyan', no_wrap=True)
            table.add_column()
            for action in actions:
                if isinstance(action, argparse._SubParsersAction):
                    for name, child in action.choices.items():
                        table.add_row(name, child.description or '')
                else:
                    label = ', '.join(action.option_strings) or action.dest
                    if action.option_strings and action.nargs != 0:
                        label += ' ' + (action.metavar or action.dest.upper())
                    table.add_row(label, action.help or '')
            out.print(table)
        if self.epilog:
            out.print()
            out.print(self.epilog, markup=False)
        return buffer.getvalue()

def emit(result, command):
    out = console()
    if 'records' in result and command == 'list':
        last = None
        for row in result['records']:
            group = (row['type'], row['domain'] or '未分类')
            if group != last:
                out.print('\n' + ' · '.join(group), style='bold cyan', markup=False)
                last = group
            out.print('  ' + row['display_title'], markup=False, overflow='fold', no_wrap=False)
        out.print(f"\n已列出 {result['shown']} / {result['total']}；剩余 {result['remaining']}。")
        if result['remaining']:
            out.print('使用 paper wiki list --all 查看全部标题。')
    elif 'item' in result:
        from .search import title_of
        out.print(title_of(result['data']), style='bold', markup=False)
        out.print(result['record'], style='dim', markup=False)
        out.print('ID：' + str(result['item'].get('id', result['item'].get('evidence_id', result['record']))), markup=False)
        out.print('保存基准 SHA256：' + result['sha256'])
        if result['item'] != result['data']:
            render_value(result['item'], out)
        elif result['data']['type'] == 'source':
            for key in ('metadata', 'summary', 'highlights', 'Q & A'):
                out.print('\n' + key, style='bold')
                render_value(result['data'].get(key), out)
        else:
            out.print(Markdown(result['body'] or result['data'].get('definition', '')))
            if result['data'].get('sources'):
                out.print('\n来源', style='bold')
                render_value(result['data']['sources'], out)
    elif 'matches' in result:
        for row in result['matches']:
            out.print('\n' + row['title'] + ' · ' + row['kind'], style='bold', markup=False)
            out.print(row['snippet'].replace('\n', ' '), markup=False)
            out.print(row['record'] + '  ID: ' + row['id'], style='dim', markup=False)
        out.print(f"\n匹配 {result['total']} 项，显示 {len(result['matches'])} 项，剩余 {result['remaining']} 项。")
    elif command == 'check':
        for row in result['results']:
            out.print(row['status'].upper() + '  ' + row['record'], markup=False)
        out.print(f"\n检查 {len(result['results'])} 条记录；错误 {len(result['errors'])}，警告 {len(result['warnings'])}。")
    elif command == 'graph':
        out.print(f"节点 {len(result['nodes'])} / {result['total_nodes']}；关系 {len(result['edges'])}。")
        for edge in result['edges']:
            out.print(edge['source'] + ' → ' + edge['target'] + '  ' + edge['label'], markup=False)
    else:
        render_value({k: v for k, v in result.items() if k not in ('errors', 'warnings', 'hashes')}, out)
    for kind in ('errors', 'warnings'):
        for row in result.get(kind, []):
            out.print(('ERROR' if kind == 'errors' else 'WARNING') + '  ' + str(row.get('record', '')) +
                      '\n  ' + row.get('reason', ''), style='red' if kind == 'errors' else 'yellow', markup=False)

def render_value(value, out, indent=0):
    prefix = '  ' * indent
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                out.print(prefix + str(key) + '：', markup=False)
                render_value(child, out, indent+1)
            else:
                out.print(prefix + str(key) + '：' + str(child if child is not None else '未知'), markup=False)
    elif isinstance(value, list):
        if not value:
            out.print(prefix + '（暂无）')
        for child in value:
            render_value(child, out, indent)
    else:
        out.print(prefix + str(value if value is not None else '未知'), markup=False)

