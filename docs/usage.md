# Usage guide

Everything beyond the quick start in the [README](../README.md).

## Other ways to install

**With Python 3.9+ and git**, no Docker:

```
pipx install "git+https://github.com/ChandrikaSethumadhavan/Detective-cli@master"
secret-finder          # opens the interactive menu
```

`pip install` works too. **From a clone**, with no install:

```
git clone -b master https://github.com/ChandrikaSethumadhavan/Detective-cli && cd Detective-cli
python3 -m secret_finder
```

## Commands

Run these inside the git repo you want to check. Only lines you added are scanned.

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
secret-finder                          # the interactive menu (needs a terminal)
```

With Docker, add the same prefix as in the README and the command, for example:

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
