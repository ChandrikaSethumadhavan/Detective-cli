import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, Optional

from .diffparse import Added
from .entropy import shannon
from .mask import own_snippet
from .rules import ENTROPY_MIN, RULES
from .store import LocalStore

IGNORE = "secret-finder: ignore"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
HASH = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$", re.I)
PLACEHOLDER = re.compile(
    r"^(?:change_?me|your[_-][a-z]+(?:[_-][a-z]+)*|<[a-z_ -]+>|\$\{[^}]*\}|\{\{[^}]*\}\}|%\([^)]*\)s?|x{4,}|example|placeholder|dummy|todo)$", re.I)
ENV_ARG = re.compile(r"""(?:\benviron\s*\[|\benviron\.get\(|\bgetenv\(|\bprocess\.env\[|\bENV\[|\bENV\.fetch\()\s*['"]$""")


@dataclass
class Finding:
    file: str
    line: int
    rule_id: str
    confidence: str
    reason: str
    fix: str
    snippet: str
    entropy: Optional[float]
    fingerprint: str
    verdict: Optional[str] = None
    source: str = "rule"


def _is_noise(value: str) -> bool:
    low = value.lower()
    return (
        UUID.match(value) is not None
        or HASH.match(value) is not None
        or len(set(value)) < 3
        or value.endswith("****")
        or PLACEHOLDER.match(value) is not None
    )


def _scan_line(text: str):
    covered = bytearray(len(text))
    for rule in RULES:
        for m in rule.pattern.finditer(text):
            start, end = m.span(1) if rule.pattern.groups else m.span()
            if covered.find(1, start, end) != -1:
                continue
            value = text[start:end]
            ent = None
            if rule.confidence != "high":
                if _is_noise(value) or ENV_ARG.search(text[max(0, start - 64):start]):
                    continue
                if rule.id == "high-entropy-string":
                    ent = shannon(value)
                    if ent < ENTROPY_MIN:
                        continue
            covered[start:end] = b"\x01" * (end - start)
            yield rule, start, end, ent


def detect(added: Iterable[Added], allow: Optional[Callable[[Finding], bool]] = None,
           salt: Optional[bytes] = None) -> Iterator[Finding]:
    store = LocalStore() if allow is None or salt is None else None
    allow = allow or store.is_allowed
    salt = store.salt if salt is None else salt
    for item in added:
        if IGNORE in item.text:
            continue
        for rule, start, end, ent in _scan_line(item.text):
            snippet = own_snippet(item.text, start, end, rule)
            msg = f"{rule.id}|{item.file}|{snippet}|{item.text[start:end]}".encode("utf-8", "replace")
            finding = Finding(item.file, item.line, rule.id, rule.confidence, rule.reason, rule.fix, snippet,
                              None if ent is None else round(ent, 2), hmac.new(salt, msg, hashlib.sha256).hexdigest())
            if not allow(finding):
                yield finding
