import os
import subprocess
import sys
import tempfile

from .cli import main

TOKEN = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
FILES = {
    "config.py": 'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"\nREGION = "eu-west-1"\n',
    "settings.json": '{\n  "db_password": "hunter2hunter2"\n}\n',
    "deploy.sh": f'#!/bin/sh\nexport GITHUB_TOKEN="{TOKEN}"\n',
    "notes.py": 'API_KEY = os.environ["API_KEY"]\nPASSWORD = "changeme"\n',
}


def _git(cwd: str, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=demo", "-c", "user.email=demo@example.com", "-c", "commit.gpgsign=false", *args],
        cwd=cwd, check=True, capture_output=True,
    )


def run() -> int:
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        print("secret-finder: the demo needs git installed", file=sys.stderr)
        return 2
    here = os.getcwd()
    with tempfile.TemporaryDirectory(prefix="secret-finder-demo-") as tmp:
        _git(tmp, "init", "-q")
        with open(os.path.join(tmp, "README.md"), "w") as f:
            f.write("# Demo repo\n")
        _git(tmp, "add", "README.md")
        _git(tmp, "commit", "-q", "-m", "first commit")
        for name, text in FILES.items():
            with open(os.path.join(tmp, name), "w") as f:
                f.write(text)
        _git(tmp, "add", "-A")
        print("Demo: a throwaway git repo with four new files, using made-up credentials. Nothing here is real.")
        print("Running: secret-finder scan\n")
        os.chdir(tmp)
        try:
            main(["scan"])
        finally:
            os.chdir(here)
        print("\nWhat to notice:")
        print("  - config.py, settings.json and deploy.sh each hold a secret, so each is reported with file:line,")
        print("    a short reason, a masked value and a fix. Real secrets are never printed in full.")
        print("  - notes.py is not reported: a placeholder (changeme) and an environment lookup are not secrets.")
        print("  - The status line shows what was scanned. The exit code of a real scan is 1 when anything is found.")
        print("\nThe demo repo has been deleted. To check your own repo, run: secret-finder scan")
    return 0
