import re
from typing import Iterable, Iterator, NamedTuple

HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class Added(NamedTuple):
    file: str
    line: int
    text: str


def _target(header: str):
    name = header[4:].split("\t")[0].strip().strip('"')
    if name == "/dev/null":
        return None
    return name[2:] if name.startswith("b/") else name


def parse(lines: Iterable[str]) -> Iterator[Added]:
    path = None
    old_left = new_left = new_line = 0
    for raw in lines:
        raw = raw.rstrip("\r\n")
        if old_left or new_left:
            tag = raw[:1]
            if tag == "+":
                new_left -= 1
                if path:
                    yield Added(path, new_line, raw[1:])
                new_line += 1
            elif tag == "-":
                old_left -= 1
            elif tag == " " or raw == "":
                old_left -= 1
                new_left -= 1
                new_line += 1
            continue
        if raw.startswith("diff --git ") or raw.startswith("Binary files "):
            path = None
        elif raw.startswith("+++ "):
            path = _target(raw)
        elif m := HUNK.match(raw):
            old_left = int(m.group(1) if m.group(1) is not None else 1)
            new_line = int(m.group(2))
            new_left = int(m.group(3) if m.group(3) is not None else 1)
