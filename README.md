# Detective-cli

A command-line tool that finds passwords, keys and tokens committed by mistake. Give it a git diff (file or stdin), a commit, a range of commits, or your current changes. It lists each finding with the file, the line, a short reason and how to fix it.

```
$ secret-finder scan
secret-finder: runs locally on your machine. Your code is not uploaded and secrets are masked in the output.
cfg.py:1  high  aws-access-key  Matches the AWS access key id format.
    "AKIA****"
    fix: Deactivate it: aws iam update-access-key --access-key-id <KEY_ID> --status Inactive. Create a replacement, then load the new one from an environment variable or a secrets manager.
secret-finder: scanned 1 added line in 1 file from working-directory changes: 1 finding (1 high).
```

Secrets are never printed in full. Exit code `0` means nothing found, `1` means findings, `2` means it could not run.

## How to run

You only need Docker. Build once, then run from the folder that holds your project:

```
docker build -t secret-finder "https://github.com/ChandrikaSethumadhavan/Detective-cli.git#master"
docker run --rm -it -v "$PWD":/repo -u "$(id -u):$(id -g)" secret-finder
```

A menu opens: **1) Try the demo** (a throwaway repo with made-up secrets, nothing real is touched) or **2) Try it on your own folder** (pick a repo it finds, or type a path). For a repo you then choose a JSON scan of your uncommitted changes, a report on all commits, the demo, or exit, and you return to the menu after every result. Docker only shares the folder you start from, so start in the folder that contains your project.

Without Docker, with Python 3.9+ and git:

```
pipx install "git+https://github.com/ChandrikaSethumadhavan/Detective-cli@master"
secret-finder                          # the menu
secret-finder scan                     # your uncommitted changes
secret-finder scan --commit <hash>     # one commit
secret-finder scan --range HEAD        # every commit in the history
git diff main | secret-finder scan -   # a diff on stdin
```

Hooks, CI, the allowlist, `--json`, `--quiet` and optional AI triage are in [docs/usage.md](docs/usage.md).

## Shortcomings/ Place for further improvements

- Only added lines are scanned, and untracked files are not covered in working-directory mode. `--range` skips merge commits, so a secret that appears only in a merge conflict resolution is missed.
- Split or concatenated secrets, and encoded secrets such as a base64 key, are missed.
- Values must be quoted. `PASSWORD=hunter2hunter2` in an unquoted `.env` or YAML line is missed. The name must contain a credential word such as password, secret, token or key, and the value must be 8 to 1024 characters without spaces.
- Low-entropy passwords with no credential-like name are missed. The random-string check only covers quoted base64-style strings of 20 or more characters, so random hex keys are missed.
- Long random-looking test strings can be reported as false positives. A 40 or 64 character hex string is treated as a hash and skipped.
- Outside a git repository, `secret-finder scan` exits 2 and prints git's usage text instead of a short error.
- The optional AI step can be wrong. It only sees the key name and the masked token, not the code around it.

## Tests

The three core ones: `tests/test_diffparse.py` (line numbers from a diff), `tests/test_detect.py` (what is and is not a secret) and `tests/test_cli.py` (input modes and exit codes). The full set, 75 tests:

```
python3 -m unittest tests.test_diffparse tests.test_inputs tests.test_detect tests.test_remediation \
  tests.test_cli tests.test_store tests.test_triage tests.test_providers tests.test_docs \
  tests.test_packaging tests.test_demo tests.test_range tests.test_menu
```

## More

- [docs/architecture.html](docs/architecture.html): design, rules, data model and failure modes.
- [docs/ai-log.md](docs/ai-log.md) and [docs/prompts.md](docs/prompts.md): how AI was used, the security reviews, and the prompts as typed.
