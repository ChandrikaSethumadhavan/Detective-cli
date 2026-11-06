import argparse
import os
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


LOCAL_NOTICE = "secret-finder: runs locally on your machine. Your code is not uploaded and secrets are masked in the output."


def _notice(ai: bool) -> str:
    if not ai:
        return LOCAL_NOTICE
    provider = os.environ.get("SF_AI_PROVIDER") or "the configured AI provider"
    return (f"secret-finder: --ai is on. Masked findings (rule, key name and masked value, never file paths or raw "
            f"secrets) will be sent to {provider}. Check its data-use terms first.")


def _source(args) -> str:
    if args.commit:
        return f"commit {args.commit}"
    return "stdin" if args.source == "-" else args.source or "working-directory changes"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _status(args, lines: int, files: int, findings) -> str:
    if findings:
        by = {c: sum(f.confidence == c for f in findings) for c in ("high", "medium", "low")}
        result = f"{_plural(len(findings), 'finding')} ({', '.join(f'{n} {c}' for c, n in by.items() if n)})"
    else:
        result = "no secrets found"
    return f"secret-finder: scanned {_plural(lines, 'added line')} in {_plural(files, 'file')} from {_source(args)}: {result}."


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="secret-finder", description="Find secrets in a git change.")
    sub = p.add_subparsers(dest="cmd", required=True)
    scan = sub.add_parser("scan", help="scan a diff, a commit, or the working directory")
    scan.add_argument("source", nargs="?", help="diff file, or - for stdin; omit to scan working-directory changes")
    scan.add_argument("--commit", metavar="HASH", help="scan the change made by this commit")
    scan.add_argument("--json", action="store_true", help="print findings as JSON")
    scan.add_argument("--ai", action="store_true", help="triage medium and low confidence findings with a hosted model")
    scan.add_argument("-q", "--quiet", action="store_true", help="hide the privacy notice and the status line")
    scan.add_argument("--ai-max-calls", type=int, default=5, metavar="N", help="cap on model requests per run")
    sub.add_parser("demo", help="try the tool on a throwaway repo with planted fake secrets")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.cmd == "demo":
        from .demo import run
        return run()
    if not args.quiet:
        print(_notice(args.ai), file=sys.stderr)
    store = LocalStore()
    seen = set()
    lines = 0

    def counted():
        nonlocal lines
        for added in parse(read_diff(args.source, args.commit)):
            lines += 1
            seen.add(added.file)
            yield added

    try:
        found = detect(counted(), allow=store.is_allowed)
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
    sys.stdout.flush()
    if not args.quiet:
        print(_status(args, lines, len(seen), findings), file=sys.stderr)
    return 1 if any(blocks(f) for f in findings) else 0
