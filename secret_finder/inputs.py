import subprocess
import sys
from typing import Iterator, List, Optional


class InputError(Exception):
    pass


def _git(*args: str) -> Iterator[str]:
    try:
        proc = subprocess.Popen(
            ["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        raise InputError("git not found")
    with proc:
        yield from proc.stdout
        err = proc.stderr.read()
        if proc.wait():
            raise InputError(err.strip() or "git failed")


def _has_head() -> bool:
    return subprocess.run(
        ["git", "rev-parse", "--verify", "-q", "HEAD"], capture_output=True
    ).returncode == 0


def list_commits(rev_range: str, limit: int) -> List[str]:
    if not rev_range or rev_range.startswith("-"):
        raise InputError(f"invalid range: {rev_range}")
    commits = [line.strip() for line in _git("rev-list", "--no-merges", "--reverse", f"--max-count={limit + 1}", rev_range, "--")]
    if len(commits) > limit:
        raise InputError(f"{rev_range} has more than {limit} commits; narrow the range or raise --max-commits")
    return commits


def read_diff(source: Optional[str] = None, commit: Optional[str] = None) -> Iterator[str]:
    if source and commit:
        raise InputError("give a diff source or --commit, not both")
    if commit:
        if commit.startswith("-"):
            raise InputError(f"invalid commit: {commit}")
        yield from _git("show", "--format=", "-m", "--first-parent", "-U0", commit, "--")
    elif source == "-":
        yield from sys.stdin
    elif source:
        try:
            with open(source, encoding="utf-8", errors="replace") as f:
                yield from f
        except OSError as e:
            raise InputError(f"cannot read {source}: {e.strerror}")
    elif _has_head():
        yield from _git("diff", "HEAD", "-U0")
    else:
        yield from _git("diff", "--cached", "-U0")
