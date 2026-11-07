import os
import subprocess
import sys

from . import demo
from .cli import main

BANNER = """Secret Finder: finds passwords and keys that were committed to git by mistake.
Everything runs on your machine. Your code is not uploaded, and secrets are masked in the output."""
SKIP = {"node_modules", "venv", "__pycache__"}


class Quit(Exception):
    pass


def find_repos(base: str, depth: int = 3, limit: int = 15) -> list:
    found = []

    def walk(path: str, level: int) -> None:
        if len(found) >= limit:
            return
        if os.path.exists(os.path.join(path, ".git")):
            found.append(path)
            return
        if level == depth:
            return
        try:
            names = sorted(os.listdir(path))
        except OSError:
            return
        for name in names:
            sub = os.path.join(path, name)
            if not name.startswith(".") and name not in SKIP and os.path.isdir(sub) and not os.path.islink(sub):
                walk(sub, level + 1)

    walk(base, 0)
    return found


def _git_ok(path: str, *args: str) -> bool:
    try:
        return subprocess.run(["git", "-C", path, *args], capture_output=True).returncode == 0
    except OSError:
        return False


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise Quit


def _choose(title: str, options: list, extra: dict = None):
    extra = extra or {}
    print(f"\n{title}")
    for i, label in enumerate(options, 1):
        print(f"  {i}) {label}")
    for key, label in extra.items():
        print(f"  {key}) {label}")
    while True:
        answer = _ask(f"Choose 1-{len(options)}: ").lower()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer)
        if answer in extra:
            return answer
        if answer in ("q", "quit", "exit"):
            return len(options)
        print(f"Please type a number from 1 to {len(options)}.")


def _pick_repo():
    base = os.getcwd()
    repos = find_repos(base)
    print(f"\nLooking for git repositories under {base} ...")
    for i, path in enumerate(repos, 1):
        print(f"  {i}) {os.path.relpath(path, base)}")
    if not repos:
        print("  None found. Start the program from the folder that contains your project, or type a path below.")
    while True:
        answer = _ask("Pick a number, type a folder path, or press Enter to go back: ")
        if not answer:
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(repos):
            return repos[int(answer) - 1]
        path = os.path.abspath(os.path.expanduser(answer))
        if not os.path.isdir(path):
            print("I cannot find that folder.")
        elif not _git_ok(path, "rev-parse", "--git-dir"):
            print("That folder is not a git repository.")
        else:
            return path


def _scan(repo: str, argv: list) -> None:
    here = os.getcwd()
    os.chdir(repo)
    try:
        main(argv)
    except Exception as e:
        print(f"Something went wrong: {e}")
    finally:
        os.chdir(here)


def run() -> int:
    print(BANNER)
    repo = None
    try:
        while True:
            if repo is None:
                n = _choose("What would you like to do?", ["Try the demo (no repo needed)", "Try it on your own folder", "Exit"])
                if n == 1:
                    demo.run()
                elif n == 2:
                    repo = _pick_repo()
                else:
                    break
                continue
            n = _choose(
                f"Folder: {repo}\nWhat would you like to see?",
                ["Scan my uncommitted changes (JSON output)", "Scan all commits (history report)", "Try the demo", "Exit"],
                {"f": "Pick a different folder"},
            )
            if n == 1:
                _scan(repo, ["scan", "--json"])
            elif n == 2:
                if _git_ok(repo, "rev-parse", "--verify", "-q", "HEAD"):
                    print("Scanning every commit. This can take a while for a big history ...")
                    _scan(repo, ["scan", "--range", "HEAD", "--max-commits", "5000"])
                else:
                    print("This repository has no commits yet, so there is no history to scan. Try option 1.")
            elif n == 3:
                demo.run()
            elif n == "f":
                repo = _pick_repo() or repo
            else:
                break
    except Quit:
        print()
    print("Goodbye.")
    return 0
