# Product specification — Detective-cli

> Status: draft, awaiting human approval. Source design: `docs/architecture.html`.

## Problem

Developers sometimes commit passwords or keys by mistake. Detective-cli (`secret-finder`) is a CLI that scans a git change and lists each leaked secret with file, line and a short reason, so it can run by hand, in a pre-commit hook or in CI. Built for the Event Inc Group mini case study (about 30 minutes for the core).

## Users

- Developers checking their own change before commit or push.
- CI jobs and pre-commit hooks that need a deterministic pass/fail exit code.

## Functional requirements

- FR-1: The CLI accepts a unified diff from a file path or from stdin (`-`).
- FR-2: The CLI accepts a commit hash (`--commit H`) and scans that commit's change, including a root commit.
- FR-3: With no input argument the CLI scans the working-directory changes (`git diff HEAD`, staged and unstaged).
- FR-4: Only added lines are scanned. File and new-file line number come from `+++` and `@@` hunk headers. Deleted files and binary files are skipped.
- FR-5: Detection uses a rule list (AWS access key, private key block, GitHub token, Slack token, Google API key, JWT, generic credential assignment) plus a Shannon-entropy rule for random-looking strings.
- FR-6: Placeholders, UUIDs, git hashes, an inline `secret-finder: ignore` comment and a `.secretfinder/allowlist` suppress findings.
- FR-7: Each finding reports file, line, rule id, confidence, a reason and a masked snippet. Output is text by default and JSON with `--json`.
- FR-8: Exit code is 0 with no findings, 1 with findings, 2 on tool error (not a repo, bad commit, unreadable file, bad flags).
- FR-9: `--ai` masks each candidate locally, then asks one configured provider (Google AI Studio or OpenRouter) for a verdict and a one-sentence reason as JSON validated against a schema.
- FR-10: Provider, model id and API key come from environment variables. No model id is hardcoded.
- FR-11: A local verdict cache and allowlist live in `.secretfinder/`, keyed by a fingerprint of rule id, file and masked value, behind a small `Store` interface.
- FR-12: With `--ai`, a medium or low confidence finding marked a false positive is still listed but does not count toward exit 1. High-confidence rule matches are never suppressed by the model.
- FR-13: The repo contains a README (how to install and run), `docs/ai-log.md` with prompts and logs, and the triage prompt in `prompts/triage.txt`. Known limitations are documented in the failure modes table of `docs/architecture.html`.
- FR-14: Each finding carries a rule-specific remediation step (`fix`) naming the action to take, such as revoking or rotating the credential and loading the replacement from the environment. Text output prints it on a `fix:` line under the finding and JSON output includes it as a `fix` key.
- FR-15: The package installs a `secret-finder` console command (`pip install` or `pipx install` from the repository) with the same behaviour as `python3 -m secret_finder`.
- FR-16: A Dockerfile builds an image with Python and git that runs `secret-finder`, so a user with neither can scan a mounted repository or a diff on stdin and pass `SF_AI_*` variables.

## Non-functional requirements

- NFR-1: Security: a raw secret value never appears in any prompt, cache file, log or JSON/text output (only masked snippets).
- NFR-2: Reliability: provider timeout, 429, invalid reply or missing key falls back to rule results and never changes the exit code.
- NFR-3: The core runs offline with Python 3 standard library only. pytest is the only dev dependency.
- NFR-4: Memory stays flat on large diffs (line-by-line parsing).
- NFR-5: API keys are read from the environment only and never written to disk.
- NFR-6: Code carries few comments. Only non-obvious intent gets one.
- NFR-7: Remediation text is static per rule, works offline, is at most 300 characters and never contains any part of the scanned content.

## Constraints

- Language: Python 3, standard library, pytest.
- Do not commit or push to GitHub without asking the human first.
- AI providers are Google AI Studio or OpenRouter, using free models.
- Process: use smaller models for small tasks and reserve expensive models for critical tasks.
- Hosted-model data-use terms must be read before running `--ai` on private code.

## Non-goals

- Scanning git history or untracked files (documented limit; `--include-untracked` later).
- Redis or Tiger Cloud stores (design only in `docs/architecture.html`).
- Detecting split, encoded or low-entropy passwords without a credential-like name.
- A GUI, daemon, or hosted service.

## Acceptance criteria

- AC-1: A two-hunk diff yields the correct new-file line number for a secret on an added line, and removed lines do not move the counter.
- AC-2: Added lines containing an AWS key and a private key header produce exactly two findings. A removed key, a `changeme` placeholder and a UUID produce none.
- AC-3: A diff piped to stdin with a secret exits 1 and prints `file:line`. A clean diff exits 0 with empty output.
- AC-4: `--commit` works on a root commit and on a normal commit. Running with no argument scans `git diff HEAD`.
- AC-5: The prompt built for `--ai` does not contain the raw secret string.
- AC-6: With the provider unreachable or returning invalid JSON, `--ai` output and exit code equal the non-AI run.
- AC-7: A cached verdict is reused on a second run without a provider call.
- AC-8: A medium-confidence finding marked false positive by a stubbed provider is listed and does not set exit 1. A high-confidence one still does.
- AC-9: Every rule has a non-empty `fix` of at most 300 characters, and no finding's `fix` contains the scanned secret value.
- AC-10: `pyproject.toml` declares the `secret-finder` entry point `secret_finder.cli:main`, and the Dockerfile installs git, marks `/repo` as a safe git directory and uses `secret-finder` as its entrypoint.

## Risks

- Free-tier rate limits and model churn: batch candidates, cap calls (`--ai-max-calls`), model id is config.
- Prompt injection through diff content: schema-validated replies, high-confidence rules not suppressible, context treated as data.
- Code context sent to a hosted model: AI is off by default, values are masked, terms to be reviewed.
- Scope exceeds 30 minutes: core ships first, AI and cache are staged behind flags.

## Open questions

- Should AI-marked false positives fail the build by default? Assumed no for medium/low (FR-12).
- Which provider is used first, Google AI Studio or OpenRouter? Assumed Google AI Studio first, OpenRouter after.
