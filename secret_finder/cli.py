import argparse
import os
import sys
from dataclasses import replace
from typing import Optional, Sequence

from .ai import get_provider
from .detect import detect
from .diffparse import parse
from .inputs import InputError, list_commits, read_diff
from .mask import safe_snippet
from .report import as_json, as_json_range, as_text, as_text_range
from .store import LocalStore
from .triage import blocks, triage


DOCKER_MENU = 'docker run --rm -it -v "$PWD":/repo -u "$(id -u):$(id -g)" secret-finder'
LOCAL_NOTICE = "secret-finder: runs locally on your machine. Your code is not uploaded and secrets are masked in the output."


def _notice(ai: bool) -> str:
    if not ai:
        return LOCAL_NOTICE
    provider = os.environ.get("SF_AI_PROVIDER") or "the configured AI provider"
    return (f"secret-finder: --ai is on. Masked findings (rule, key name and masked value, never file paths or raw "
            f"secrets) will be sent to {provider}. Check its data-use terms first.")


def _source(args) -> str:
    if args.range:
        return args.range
    if args.commit:
        return f"commit {args.commit}"
    return "stdin" if args.source == "-" else args.source or "working-directory changes"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _counts(findings) -> str:
    by = {c: sum(f.confidence == c for f in findings) for c in ("high", "medium", "low")}
    return f"{_plural(len(findings), 'finding')} ({', '.join(f'{n} {c}' for c, n in by.items() if n)})"


def _status(args, count, pairs) -> str:
    findings = [f for _, f in pairs]
    if args.range and not count.commits:
        return f"secret-finder: no commits matched {args.range}; nothing was scanned."
    what = f"{_plural(count.lines, 'added line')} in {_plural(len(count.files), 'file')}"
    if args.range:
        what = f"{_plural(count.commits, 'commit')} ({what})"
    result = "no secrets found"
    if findings:
        result = _counts(findings)
        if args.range:
            result += f" in {_plural(len({c for c, _ in pairs}), 'commit')}"
    return f"secret-finder: scanned {what} from {_source(args)}: {result}."


class _Count:
    def __init__(self):
        self.lines, self.files, self.commits = 0, set(), 0

    def added(self, diff):
        for item in parse(diff):
            self.lines += 1
            self.files.add(item.file)
            yield item


def _scan(args, store, count):
    def masked(found, commit):
        return [(commit, replace(f, snippet=safe_snippet(f.snippet))) for f in found]

    if args.range:
        if args.source or args.commit:
            raise InputError("--range cannot be combined with a diff file, stdin or --commit")
        pairs = []
        commits = list_commits(args.range, args.max_commits)
        count.commits = len(commits)
        for c in commits:
            pairs += sorted(masked(detect(count.added(read_diff(commit=c)), allow=store.is_allowed), c),
                            key=lambda p: (p[1].file, p[1].line))
        return pairs
    found = detect(count.added(read_diff(args.source, args.commit)), allow=store.is_allowed)
    return sorted(masked(found, None), key=lambda p: (p[1].file, p[1].line))


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="secret-finder", description="Find secrets in a git change.")
    sub = p.add_subparsers(dest="cmd")
    scan = sub.add_parser("scan", help="scan a diff, a commit, or the working directory")
    scan.add_argument("source", nargs="?", help="diff file, or - for stdin; omit to scan working-directory changes")
    scan.add_argument("--commit", metavar="HASH", help="scan the change made by this commit")
    scan.add_argument("--json", action="store_true", help="print findings as JSON")
    scan.add_argument("--range", metavar="REVS", help="scan every non-merge commit in a git range, e.g. origin/main..HEAD, or HEAD for all history")
    scan.add_argument("--max-commits", type=int, default=1000, metavar="N", help="largest range to scan (default 1000)")
    scan.add_argument("--ai", action="store_true", help="triage medium and low confidence findings with a hosted model")
    scan.add_argument("-q", "--quiet", action="store_true", help="hide the privacy notice and the status line")
    scan.add_argument("--ai-max-calls", type=int, default=5, metavar="N", help="cap on model requests per run")
    sub.add_parser("menu", help="open the interactive menu")
    sub.add_parser("demo", help="try the tool on a throwaway repo with planted fake secrets")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.cmd is None and not sys.stdin.isatty():
        parser.print_usage(sys.stderr)
        print("Run it in a terminal to open the interactive menu. With Docker, add -it:\n"
              f"  {DOCKER_MENU}", file=sys.stderr)
        return 2
    if args.cmd in (None, "menu"):
        from .menu import run
        return run()
    if args.cmd == "demo":
        from .demo import run
        return run()
    if not args.quiet:
        print(_notice(args.ai), file=sys.stderr)
    store = LocalStore()
    count = _Count()
    try:
        pairs = _scan(args, store, count)
    except InputError as e:
        print(f"secret-finder: {e}", file=sys.stderr)
        return 2
    if args.ai:
        try:
            triaged = triage([f for _, f in pairs], get_provider(), store, args.ai_max_calls)
            pairs = [(c, f) for (c, _), f in zip(pairs, triaged)]
        except Exception as e:
            print(f"secret-finder: AI triage skipped: {e}", file=sys.stderr)
    findings = [f for _, f in pairs]
    if args.range:
        sys.stdout.write((as_json_range if args.json else as_text_range)(pairs))
    else:
        sys.stdout.write((as_json if args.json else as_text)(findings))
    sys.stdout.flush()
    if not args.quiet:
        print(_status(args, count, pairs), file=sys.stderr)
    return 1 if any(blocks(f) for f in findings) else 0
