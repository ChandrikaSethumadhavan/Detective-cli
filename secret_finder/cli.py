import argparse
import sys
from dataclasses import replace
from typing import Optional, Sequence

from .ai import get_provider
from .detect import detect
from .diffparse import parse
from .inputs import InputError, read_diff
from .mask import safe_snippet
from .report import as_json, as_text
from .store import LocalStore
from .triage import blocks, triage


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="secret-finder", description="Find secrets in a git change.")
    sub = p.add_subparsers(dest="cmd", required=True)
    scan = sub.add_parser("scan", help="scan a diff, a commit, or the working directory")
    scan.add_argument("source", nargs="?", help="diff file, or - for stdin; omit to scan working-directory changes")
    scan.add_argument("--commit", metavar="HASH", help="scan the change made by this commit")
    scan.add_argument("--json", action="store_true", help="print findings as JSON")
    scan.add_argument("--ai", action="store_true", help="triage medium and low confidence findings with a hosted model")
    scan.add_argument("--ai-max-calls", type=int, default=5, metavar="N", help="cap on model requests per run")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    store = LocalStore()
    try:
        found = detect(parse(read_diff(args.source, args.commit)), allow=store.is_allowed)
        findings = sorted((replace(f, snippet=safe_snippet(f.snippet)) for f in found), key=lambda f: (f.file, f.line))
    except InputError as e:
        print(f"secret-finder: {e}", file=sys.stderr)
        return 2
    if args.ai:
        try:
            findings = triage(findings, get_provider(), store, args.ai_max_calls)
        except Exception as e:
            print(f"secret-finder: AI triage skipped: {e}", file=sys.stderr)
    sys.stdout.write((as_json if args.json else as_text)(findings))
    return 1 if any(blocks(f) for f in findings) else 0
