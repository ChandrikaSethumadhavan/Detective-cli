import json
import re
from dataclasses import asdict
from typing import Iterable

CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _clean(s: str) -> str:
    return CONTROL.sub("?", s)


def _lines(f) -> list:
    return [f"{f.file}:{f.line}  {f.confidence}  {f.rule_id}  {f.reason}", f"    {_clean(f.snippet)}", f"    fix: {f.fix}"]


def as_text(findings: Iterable) -> str:
    out = [line for f in findings for line in _lines(f)]
    return "\n".join(out) + "\n" if out else ""


def as_text_range(pairs: Iterable) -> str:
    out, last = [], None
    for commit, f in pairs:
        if commit != last:
            out.append(f"commit {commit[:7]}")
            last = commit
        out.extend(_lines(f))
    return "\n".join(out) + "\n" if out else ""


def as_json_range(pairs: Iterable) -> str:
    return json.dumps([{"commit": c, **asdict(f)} for c, f in pairs], indent=2) + "\n"


def as_json(findings: Iterable) -> str:
    return json.dumps([asdict(f) for f in findings], indent=2) + "\n"
