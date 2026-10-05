#!/usr/bin/env python3
"""Request a local write key without revealing it; authorization is a human decision."""
import argparse
import json
import sys
from zotero_client import Zotero, ZoteroError


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("app_name", nargs="?", default="Literature Reading Agent")
    p.add_argument("--status", action="store_true", help="cached key status; no dialog/write test")
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--force", action="store_true")
    p.add_argument("--base")
    a = p.parse_args()
    if a.timeout <= 0:
        p.error("timeout must be positive")
    try:
        z = Zotero(base=a.base)
        if a.status or (z.can_write and not a.force):
            print(json.dumps(z.info(), ensure_ascii=False, indent=2))
            return 0 if z.can_write else 1
        print('Zotero will ask you to Allow (one write), Always Allow (reuse), or Deny.', flush=True)
        print(json.dumps(z.authorize(a.app_name, a.timeout), ensure_ascii=False, indent=2))
        return 0
    except (ZoteroError, ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
