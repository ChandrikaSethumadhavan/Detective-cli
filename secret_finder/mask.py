import re

from .rules import RULES, mask

NAME = r"""(?i:(?<![a-z0-9_-])(?:[a-z]{1,16}[_-]){0,3}[a-z]{0,16}(?:pass|pwd|secret|token|key|auth|cred)[a-z]{0,16}(?:[_-][a-z]{1,16}){0,3}\d{0,2}\s*[:=]\s*)?"""
WINDOW = re.compile(NAME + r"""['"]?[^\s'";,:/@?&=#]{0,4}\*\*\*\*['"]?""")
BEFORE = re.compile(NAME + r"""['"]?$""")
KEY_HEADER = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----(?:\[redacted\])?")


def own_snippet(text: str, start: int, end: int, rule) -> str:
    if not rule.mask:
        return text[start:end]
    before = BEFORE.search(text[max(0, start - 80):start]).group(0)
    close = text[end] if text[end:end + 1] in ("'", '"') else ""
    return before + mask(text[start:end]) + close


def redact(text: str) -> str:
    cut = min((m.end() for r in RULES if not r.mask for m in r.pattern.finditer(text)), default=None)
    if cut is not None and cut < len(text):
        text = text[:cut] + "[redacted]"
    spans = sorted(
        m.span(1) if r.pattern.groups else m.span()
        for r in RULES if r.mask for m in r.pattern.finditer(text)
    )
    merged = []
    for start, end in spans:
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    for start, end in reversed(merged):
        text = text[:start] + mask(text[start:end]) + text[end:]
    return text


def safe_snippet(text: str) -> str:
    text = redact(text)
    m = WINDOW.search(text[:4000]) or KEY_HEADER.search(text)
    return m.group(0) if m else ""
