"""Paper Reader command line tools."""
from __future__ import annotations

import argparse
import importlib
import sys

COMMANDS = {
    "check": ("record_check", "检查阅读记录完整性"),
    "zotero": ("zotero_ops", "检索、读取及整理 Zotero 文库"),
    "authorize": ("zotero_authorize", "申请或查看本机 Zotero 授权"),
    "render": ("html_note", "导出阅读 HTML"),
    "metadata": ("zotero_metadata", "采集论文元数据"),
    "figures": ("pdf_figures", "从 PDF 提取原图"),
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="paper", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(f"  {name:12} {description}" for name, (_, description) in COMMANDS.items()) +
               "\n\n使用 paper COMMAND --help 查看子命令参数。")
    parser.add_argument("command", choices=COMMANDS)
    if not argv or argv[0] in ("-h", "--help"):
        parser.print_help()
        return 0
    selected = parser.parse_args(argv[:1]).command
    module = importlib.import_module("." + COMMANDS[selected][0], __package__)
    return module.main(argv[1:], prog=f"paper {selected}")
