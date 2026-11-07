# AI log

How AI was used to build Detective-cli, what it produced, and what was checked. The prompts as typed are in [prompts.md](prompts.md). The runtime prompt the tool sends to a model is in `prompts/triage.txt`.

## Tools and roles

- Claude Code with Sonnet 5.5 wrote the plan, the code and the tests.
- Opus reviewed the security-critical parts read-only (masker, provider adapters, detection regexes). It did not write product code.
- Genesis (a spec, plan, task and gate workflow) held the specification, the task list, the proof for each gate and every approval. Approvals were given by the author in chat and recorded under the author's name.
- Standing instruction from the author: do not commit or push without asking, keep code comments sparse, use smaller models for small tasks and Opus only for critical ones.

## Prompts, in order

| # | Prompt (summarized) | Result |
|---|---|---|
| 1 | Read the case study PDF. Plan the architecture, write a detailed HTML document with flow diagrams, consider Redis or Tiger Cloud for storage, use Google AI Studio or OpenRouter free models for the AI part. | `docs/architecture.html`: component diagram, event flow, input modes, detection rules, AI trust boundary, data model, storage decision table, failure modes, test plan. Storage conclusion: local files for the build, Redis and Tiger Cloud as optional extensions. |
| 2 | Install and use Genesis for this repo, with the goal: follow `docs/*.html`, no commit or push without asking, few comments, route small tasks to smaller models. | Genesis initialized, `SPEC.md` drafted from the architecture document. |
| 3 | Scope answer: MVP plus local cache and AI triage. | Spec fixed at 30 requirements (FR, NFR, AC identifiers). |
| 4 | Approve the spec, then the plan. | Seven tasks, later extended to 15 task records (see below). |
| 5 | Add a remediation step to each finding as a natural part of the tool. | FR-14, NFR-7, AC-9 and task T-2a: a fixed fix string per rule with exact revoke or rotate commands. |
| 6 | Approve each task after review, one at a time. | Each medium-risk task needed the author's independent-review approval. |
| 11 | Asked whether the project meets the brief and the recruiter email: README must be short with a where-it-fails section, the company PDF must not be published, and prompts should be quoted. | A short README, `docs/usage.md` for the rest, `docs/prompts.md` with verbatim prompts, and `info/` (the PDF) removed from the working tree and gitignored. |
| 10 | Said the steps were too many for a stranger: wanted a single command that opens a menu (try the demo, or try it on your own folder with JSON, all commits, demo, exit), returning to the menu after every result. | An interactive menu (`secret-finder` with no arguments, or `secret-finder menu`), repository discovery under the current folder, and a Docker image whose default is the menu (spec FR-24 to FR-26, AC-17 to AC-19). |
| 9 | Asked to scan the commits of a repo or PR and report them, not just uncommitted changes. | `scan --range` (spec FR-20 to FR-23, AC-14 to AC-16): per-commit scanning, grouped output, JSON `commit` key, commit-count status line, a size limit. The demo output order was fixed in the same task. |
| 8 | Feedback after trying the Docker image: print a privacy message first, add a way to try the tool without a real repo, and print clearer status so a clean scan does not look empty. | A stderr privacy notice, a stderr status line, `--quiet`, and `secret-finder demo` (spec FR-17 to FR-19, AC-11 to AC-13). |
| 7 | Make it easy for others to run, including people without Python. Simplify the README and drop its where-it-fails section. | `pyproject.toml` console command, `Dockerfile`, a rewritten README, and a spec amendment (FR-13, FR-15, FR-16, AC-10). Known limitations now live in the failure modes table of `docs/architecture.html`. The development machine has neither Docker nor pip, so the image build and a real install were checked statically only. |

## Tasks

| Task | Delivered |
|---|---|
| T-1 | Diff parser and the four input modes |
| T-2, T-2a | Rules, entropy, filters, fix steps |
| T-3 | CLI, text and JSON output, exit codes |
| T-4 | Local allowlist and verdict cache |
| T-5, T-5a, T-5c | Masker, triage policy, salted fingerprints, parser and store hardening |
| T-6, T-6a, T-6b | Google AI Studio and OpenRouter adapters, snippet masking, linear-time regexes |
| T-7c | README, this log, runtime prompt, documentation update |
| T-8 | pyproject.toml, Dockerfile, README rewrite, documentation update |
| T-9 | README section "Gaps in this project" restored at the author's request, listing known limitations |
| T-14 | Submission fixes: short README, usage guide, verbatim prompts, challenge PDF folder removed |
| T-13 | Interactive menu, Docker default entrypoint, README quick start |
| T-12 | History scanning with --range, and the demo output order |
| T-11 | Privacy notice, status line and the demo command |
| T-10 | The tool flagged its own `pyproject.toml` entry point. The generic rule now skips a lowercase `module.path:function` value in `pyproject.toml` and `setup.cfg` only. A shape-only rule would have hidden pairs such as `john.smith:letmein`, so it is limited to those files. |

T-5b and T-7 and T-7b were rejected and re-created as T-5c, T-7b and T-7c without code changes. Genesis fixes a task's file baseline when the task is first activated, so adding tasks to an approved plan made baselines stale. Re-creating the task was the supported way to refresh it.

## Security reviews and what changed

| Review | Findings | Resolution |
|---|---|---|
| Masker, first pass | A one-line JSON private key was printed in full. Unmatched secrets on the same line reached the prompt and the output. A committed cache could inject terminal escapes. Fingerprints ignored the secret, so different secrets collided. | Cut everything after a private key header. Snippets and prompts reduced to key name plus masked token. Replies and cached reasons cleaned and capped. Fingerprints became an HMAC of the value with a per-clone salt. |
| Fingerprint and salt | The environment-read skip hid real secrets. Other secrets on a line were unmasked in snippets. Bad bytes crashed fingerprinting. The salt file accepted bad values and was not written atomically. | Skip only when the value is the first argument of an environment read. Mask every match. Replace invalid bytes. Validate the salt and publish it atomically. |
| Provider adapters | Provider exceptions could escape or print server text. No total time limit on a response. Model ids needed stricter validation. | Every failure becomes one fixed-message error. 30 second read deadline, 1 MB cap, exact model id check. Redirects refused and checked against a loopback server. |
| Masker window | URL credentials on the same line as a JWT reached the prompt. | Snippet reduced to the masked token and a credential-looking key name. |
| Regexes and snippets | The generic rule was cubic on long lines. The JWT rule and the per-line overlap check were quadratic. Hostnames could appear as key names. | Bounded repeats, a covered-bytes array, and key names limited to plain letter segments. 1 MB lines now scan in under a second. |

Some auditor claims did not hold and were corrected after reproducing them. For example, `os.environ.get("X", "R3alS3cret99")` was reported as a hidden finding, but no rule matches that line, so it is a plain detection gap and is listed in the README.

## Checks the author can repeat

- `python3 -m unittest` on the test modules listed in the README.
- `genesis status .` and `.genesis/PLAN.md` show every task, gate and approval.
