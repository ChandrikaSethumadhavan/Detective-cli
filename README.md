# Detective-cli

Finds passwords, keys and tokens in a git change. Each finding has the file, the line, a short reason and a step to fix it. Python 3.9+, standard library only (tested on 3.12).

## Run

```
python3 -m secret_finder scan                    # staged and unstaged changes (git diff HEAD)
python3 -m secret_finder scan --commit <hash>    # one commit; root and merge commits work
git diff main | python3 -m secret_finder scan -  # a diff on stdin
python3 -m secret_finder scan change.diff        # a diff file
```

Add `--json` for JSON. Example output:

```
cfg.py:1  high  aws-access-key  Matches the AWS access key id format.
    "AKIA****"
    fix: Deactivate it: aws iam update-access-key --access-key-id <KEY_ID> --status Inactive. Create a replacement, then load the new one from an environment variable or a secrets manager.
```

Values are always masked in the output. Exit code: `0` no findings, `1` findings, `2` tool error (not a repo, bad commit, unreadable file, bad flags). That makes it usable in a pre-commit hook or CI step.

## Optional AI triage

`--ai` asks a hosted model to judge medium and low confidence findings. Off by default.

```
export SF_AI_PROVIDER=google          # or openrouter
export SF_AI_MODEL=<a model id from the provider's current list>
export SF_AI_API_KEY=<your key>
python3 -m secret_finder scan --ai [--ai-max-calls 5]
```

- Only medium and low confidence findings are sent. Each record is the rule id, confidence, file extension, entropy, and the key name with the masked value. No file paths, no surrounding code, no raw secrets.
- The model can mark a finding as a likely false positive. That finding is still listed but no longer sets exit code 1. High confidence findings are never sent and always count.
- Any failure (timeout, 429, bad reply, missing key) falls back to the rule results with the same exit code.
- Text inside a diff can try to steer the model toward "false positive" for medium and low findings. That is why high confidence findings are excluded.
- Read each provider's current data-use terms for the free tier before using `--ai` on private code. Masking reduces what is sent. It does not make the call private.

## Allowlist and local state

`.secretfinder/allowlist`, one entry per line, `#` for comments:

```
aws-access-key tests/*      # rule id and file glob
* docs/*                    # any rule
<64-hex fingerprint>        # one finding, valid only in the clone that produced it
```

`# secret-finder: ignore` on a line skips that line. `.secretfinder/cache.json` (AI verdicts) and `.secretfinder/salt` (per-clone key for fingerprints) are gitignored. Treat a committed allowlist as trusted configuration that needs review, because it can silence findings.

## Tests

```
python3 -m unittest tests.test_diffparse tests.test_inputs tests.test_detect tests.test_remediation \
  tests.test_cli tests.test_store tests.test_triage tests.test_providers tests.test_docs
```

## Where it fails

- Only added lines are scanned. Secrets already in history, or in untracked files in working-directory mode, are not found. A merge commit is scanned against its first parent only.
- Split or concatenated secrets, and encoded secrets (for example base64 of a key), are missed.
- The generic rule needs a quoted value, so `PASSWORD=hunter2hunter2` in an unquoted `.env` or YAML line is missed. It also needs a credential word in the name (up to 64 characters around it) and a value of 8 to 1024 characters without spaces.
- Low-entropy passwords with no credential-like name are missed. The random-string rule only checks quoted base64-style strings of 20 or more characters with entropy of at least 4.2, so random hex keys are missed.
- Long random-looking test fixtures can be reported as false positives. A 40 or 64 character hex string is treated as a hash and skipped.
- Outside a git repository, working-directory mode exits 2 and prints git's usage text.
- The AI step can be wrong, and it only sees the masked token and key name, not the code around it.
