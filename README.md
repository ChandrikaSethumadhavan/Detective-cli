# Detective-cli

Finds passwords, keys and tokens in a git change before they get committed. For each one it shows the file, the line, why it was flagged, and how to fix it.

```
$ secret-finder scan
secret-finder: runs locally on your machine. Your code is not uploaded and secrets are masked in the output.
cfg.py:1  high  aws-access-key  Matches the AWS access key id format.
    "AKIA****"
    fix: Deactivate it: aws iam update-access-key --access-key-id <KEY_ID> --status Inactive. Create a replacement, then load the new one from an environment variable or a secrets manager.
secret-finder: scanned 1 added line in 1 file from working-directory changes: 1 finding (1 high).
```

Secrets are never printed in full. The exit code is `0` when nothing is found and `1` when something is, so it can block a commit or fail a CI job.

## Quick start (Docker, two commands)

You only need Docker. Build it once:

```
docker build -t secret-finder "https://github.com/ChandrikaSethumadhavan/Detective-cli.git#master"
```

Then, from the folder that holds your project (or a folder that contains several projects), run:

```
docker run --rm -it -v "$PWD":/repo -u "$(id -u):$(id -g)" secret-finder
```

A menu opens and guides you:

```
What would you like to do?
  1) Try the demo (no repo needed)
  2) Try it on your own folder
  3) Exit
```

- **Try the demo** builds a throwaway repo with made-up credentials, scans it and shows what it found and why. Nothing real is touched.
- **Try it on your own folder** lists the git repositories found under the folder you started in. Pick one by number or type a path. Then choose a **JSON** scan of your uncommitted changes, a report on **all commits**, the demo again, or exit. After every result you are back at the menu.

The menu can only see the folder you ran the command from, because Docker only shares that folder. Run it from the folder that contains your project.

## Other ways to install

**With Python 3.9+ and git**, no Docker:

```
pipx install "git+https://github.com/ChandrikaSethumadhavan/Detective-cli@master"
secret-finder          # opens the same menu
```

`pip install` works too. **From a clone**, with no install:

```
git clone -b master https://github.com/ChandrikaSethumadhavan/Detective-cli && cd Detective-cli
python3 -m secret_finder
```

## Use it directly

Skip the menu when you know what you want. Run these inside the git repo you want to check. Only lines you added are scanned.

```
secret-finder scan                     # your staged and unstaged changes
secret-finder scan --commit <hash>     # the change made by one commit
secret-finder scan --range origin/main..HEAD   # every commit in a PR or branch
secret-finder scan --range HEAD        # the whole history of the current branch
git diff main | secret-finder scan -   # any diff on stdin
secret-finder scan change.diff         # a saved diff file
secret-finder scan --json              # JSON instead of text
secret-finder scan --quiet             # findings only, no notice or status line
secret-finder demo                     # the demo, without the menu
```

With Docker, add the same prefix as above and the command, for example:

```
docker run --rm -v "$PWD":/repo -u "$(id -u):$(id -g)" secret-finder scan --range HEAD
```

`--range` takes any `git rev-list` range and scans its commits one at a time, so a key that was added and later removed is still found, under the commit that added it:

```
$ secret-finder scan --range origin/main..HEAD
commit 7e9fe02
config.py:1  high  aws-access-key  Matches the AWS access key id format.
    AWS_KEY = "AKIA****"
    fix: Deactivate it: aws iam update-access-key ...
secret-finder: scanned 3 commits (41 added lines in 5 files) from origin/main..HEAD: 1 finding (1 high) in 1 commit.
```

Commit messages are never printed, because they can contain secrets. Merge commits are skipped, since the commits they merge are scanned directly. A range of more than 1000 commits stops with a message instead of scanning part of it. Raise the limit with `--max-commits`. `--json` adds a `commit` field to every finding.

Every scan starts with a privacy notice and ends with a status line saying what was scanned and what was found. Both go to stderr, so the output you pipe or parse (`--json` included) holds only the findings. With `--ai` the notice names the provider that will receive masked findings.

Exit codes: `0` nothing found, `1` findings, `2` could not run (not a git repo, bad commit or range, unreadable file, bad flags).

## Stop secrets before they are committed

A pre-commit hook, in `.git/hooks/pre-commit` (then `chmod +x` it):

```
#!/bin/sh
secret-finder scan
```

A CI step that checks every commit a branch adds:

```
secret-finder scan --range origin/main..HEAD
```

In CI, fetch enough history first (for example `fetch-depth: 0` in GitHub Actions), or the range cannot be resolved.

## Ignore known findings

Put one entry per line in `.secretfinder/allowlist`. Commit this file so the team shares it.

```
aws-access-key tests/*     # a rule id and a file pattern
* docs/*                   # any rule
```

Add `# secret-finder: ignore` to a line to skip just that line. A committed allowlist can silence findings, so review changes to it like code.

`.secretfinder/cache.json` and `.secretfinder/salt` are created for you. Add both to the scanned repo's `.gitignore`.

## Optional: AI triage

`--ai` asks a hosted model to double-check the less certain findings. It is off by default.

```
export SF_AI_PROVIDER=google          # or openrouter
export SF_AI_MODEL=<a model id from the provider's current list>
export SF_AI_API_KEY=<your key>
secret-finder scan --ai
```

- Only medium and low confidence findings are sent. Each is the rule id, confidence, file extension, entropy, and the key name with the masked value. File paths, surrounding code and raw secrets are never sent.
- The model can mark a finding as a likely false positive. It is still listed but no longer sets exit code 1. High confidence findings are never sent and always count.
- If the call fails for any reason, you get the normal results and the same exit code.
- Check the provider's current data-use terms for its free tier before using `--ai` on private code.

## Gaps in this project

- Only added lines are scanned, and untracked files are not covered in working-directory mode. `--range` skips merge commits, so a secret that appears only in a merge conflict resolution is missed, and `--commit` on a merge commit shows its change against the first parent only.
- Split or concatenated secrets, and encoded secrets such as a base64 key, are missed.
- Values must be quoted. `PASSWORD=hunter2hunter2` in an unquoted `.env` or YAML line is missed. The name must contain a credential word such as password, secret, token or key (up to 64 characters around it), and the value must be 8 to 1024 characters without spaces.
- Low-entropy passwords with no credential-like name are missed. The random-string check only covers quoted base64-style strings of 20 or more characters, so random hex keys are missed.
- Long random-looking test strings can be reported as false positives. A 40 or 64 character hex string is treated as a hash and skipped.
- Outside a git repository, `secret-finder scan` with no arguments exits 2 and prints git's usage text instead of a short error.
- The AI step can be wrong. It only sees the key name and the masked token, not the code around it.

## Develop

```
python3 -m unittest tests.test_diffparse tests.test_inputs tests.test_detect tests.test_remediation \
  tests.test_cli tests.test_store tests.test_triage tests.test_providers tests.test_docs \
  tests.test_packaging tests.test_demo tests.test_range tests.test_menu
```

Design, rules and known limitations are in [docs/architecture.html](docs/architecture.html). How AI was used to build this is in [docs/ai-log.md](docs/ai-log.md).
