"""Check the four required reading modules; optional extensions are outside this check."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

MODULES = ("metadata", "summary", "highlights", "Q & A")


def has_content(value):
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(has_content(item) for item in value.values())
    if isinstance(value, list):
        return any(has_content(item) for item in value)
    return value is not None and not isinstance(value, bool) and bool(value)


def check_record(record):
    if not isinstance(record, dict):
        raise ValueError("阅读记录必须是 JSON 对象")
    completeness = record.get("completeness", {})
    if not isinstance(completeness, dict):
        raise ValueError("completeness 必须是按模块保存 status 的对象")
    unknown = set(completeness) - set(MODULES) - {"others"}
    if unknown:
        raise ValueError("completeness 中有未知模块：" + "、".join(sorted(unknown)))
    expected = {"metadata": dict, "summary": str, "highlights": (str, list), "Q & A": list}
    modules = {}
    for name in MODULES:
        errors, warnings = [], []
        if name == "metadata" and record.get("type") != "source":
            errors.append("阅读记录必须包含 type: source")
        if name == "Q & A" and isinstance(record.get(name), list):
            ids = []
            for item in record[name]:
                if not isinstance(item, dict) or not re.fullmatch(r"q_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", str(item.get("id", ""))):
                    errors.append("每条实际问答必须有 q_UUID4")
                    break
                ids.append(item["id"])
                if item.get("question_form") not in ("exact", "legacy_recorded"):
                    errors.append("每条实际问答必须标明 question_form")
                if not isinstance(item.get("question"), str) or not item["question"].strip() or not isinstance(item.get("answer"), str):
                    errors.append("每条实际问答必须有原问和字符串答复")
            if len(ids) != len(set(ids)):
                errors.append("问答 ID 重复")
        if name not in record:
            errors.append("缺少必要模块")
        else:
            value = record[name]
            if not has_content(value):
                (warnings if name == "Q & A" else errors).append("内容为空")
            elif not isinstance(value, expected[name]):
                errors.append("内容格式错误")
        if name in completeness:
            state = completeness[name]
            if not isinstance(state, dict) or set(state) != {"status"} or state["status"] not in ("complete", "degraded"):
                errors.append("仅允许 status 为 complete 或 degraded")
            elif state["status"] == "degraded":
                warnings.append("已标记降级")
        status = "error" if errors else "warning" if warnings else "ok"
        modules[name] = {"status": status}
        if errors or warnings:
            modules[name]["message"] = "；".join(errors + warnings)
    statuses = {item["status"] for item in modules.values()}
    return {"status": "error" if "error" in statuses else "warning" if "warning" in statuses else "ok",
            "modules": modules}


def main(argv=None, *, prog=None):
    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
    parser.add_argument("path", help="论文实例目录，或 reading-record.json")
    parser.add_argument("--json", action="store_true", help="输出简洁 JSON 报告")
    args = parser.parse_args(argv)
    try:
        path = Path(args.path).expanduser()
        if path.is_dir():
            path = path / "assets/reading-record.json"
        report = check_record(json.loads(path.read_text(encoding="utf-8-sig")))
    except (OSError, UnicodeError, ValueError) as error:
        message = f"无法检查记录：{error}"
        print(json.dumps({"status": "error", "message": message}, ensure_ascii=False) if args.json else "ERROR " + message)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for name, item in report["modules"].items():
            suffix = ": " + item["message"] if item.get("message") else ""
            print(f"{item['status'].upper()} {name}{suffix}")
    return 1 if report["status"] == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
