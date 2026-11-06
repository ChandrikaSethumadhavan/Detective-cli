import json
import re
from dataclasses import asdict
from typing import Iterable

CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _clean(s: str) -> str:
    return CONTROL.sub("?", s)


def as_text(findings: Iterable) -> str:
    out = []
    for f in findings:
        out.append(f"{f.file}:{f.line}  {f.confidence}  {f.rule_id}  {f.reason}")
        out.append(f"    {_clean(f.snippet)}")
        out.append(f"    fix: {f.fix}")
    return "\n".join(out) + "\n" if out else ""


def as_json(findings: Iterable) -> str:
    return json.dumps([asdict(f) for f in findings], indent=2) + "\n"
