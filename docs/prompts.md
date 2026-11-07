# Prompts as typed

Selected prompts that shaped this project, quoted exactly as I typed them, typos included. Short approval messages such as "I reviewed it, approve T-5" and pasted terminal output are left out. What each prompt produced is in [ai-log.md](ai-log.md).

## 1. Plan and architecture

nstall and use Genesis for this repository.
My project goal is: "Refer to docs/*.html for the detailed plan that was crafted by me about what to build in this repo. Do not push or commit changes to GitHub without asking me. Do not write excessive comments, route to smaller models for smaller tasks and use opus or expensive models only when the task is critical. AI agents i would use google ai studio's free models or openrouter models and redis/tigercloud for storage if needed (refer to the document). Use the genesis tool to go in detail about planning the functional and non-functional requiremnets."

1. Check for Git, Node.js 18+, and the `genesis` CLI. If Genesis is already
   installed, use that installation and inspect its help and installed skill.
   Do not overwrite an existing installation or unrelated local changes.

2. If Genesis is missing, install the official kit:
   - Clone https://github.com/ayush488-glitch/genesis-kit.git into
     ~/.local/share/genesis-kit if that directory is absent.
   - If it already contains the official repository, inspect its status and
     update with a fast-forward-only pull when clean. Preserve local changes.
   - Run bash ~/.local/share/genesis-kit/install.sh.
   - Verify with ~/.local/bin/genesis help. Use that absolute CLI path if
     ~/.local/bin is not on PATH; do not edit shell startup files.
   - If prerequisites are missing or the existing directory belongs to
     something else, explain the specific issue instead of replacing it.

3. Load the installed Genesis skill and the bundled official Ponytail skill
   at full. If this coding host cannot discover skills, read their SKILL.md
   files directly from the kit's skills/genesis and skills/ponytail folders.

4. Inspect this project. If it already has Genesis state, read
   .genesis/KICKOFF.md and run `genesis status .` and `genesis brief .`.
   Resume the existing workflow; do not initialize over it.
   If it has implementation code but no Genesis state, run `genesis adopt .`
   read-only, show the discovery report, and obtain approval for adoption
   before using `genesis adopt . --write --objective "<my actual goal>"`.
   If it is a new project, run
   `genesis init . --workflow new-product --objective "<my actual goal>"`.
   Use my actual goal above, not a placeholder.

5. Run `genesis agent connect . --write` to connect repository instructions.
   Report the current state, evidence, blocker and exact next action.

6. For a new product, clarify users, outcomes, constraints, non-goals,
   acceptance criteria and unresolved assumptions. Record durable decisions
   and knowledge through Genesis. Fill SPEC.md with FR-*, NFR-* and AC-*
   identifiers. Run `genesis spec check .`, then obtain my specification
   approval before implementation. Record only approval I actually gave.

7. Define bounded tasks linked to the approved requirements, with file scope,
   dependencies and mandatory executable gates. Run `genesis plan check .`
   and obtain my plan approval before activating implementation. Declare
   observable actor/scope/environment/duration scenarios for autonomous work.

8. Continue only authorized active work. Run current gates; obtain independent
   review for non-low-risk tasks. Use `genesis task complete`, never a state
   edit, to complete work. If I authorize a bounded host command, record a
   task-scoped, expiring grant and use `genesis run`. Reuse valid authorization
   and proof across sessions. Never invent a reviewer or approval.

9. After interruption, inspect attempts and uncertain side effects before
   recovery or retry. Record durable discoveries and checkpoint before stopping.
   Treat learned rules as proposals until evaluation, review and promotion pass.







## 2. The interactive menu

> for the user we dont know what repo or folder he's gonna try it on right? so shouldnt it be easier? i feel like these are way too many steps, so when the docker image is built and then run, there should be 2 options popping up, 1. try demo 2.try it on your own folder and under this option 2 when selected, it should ask for the folder to try it on and then show 1.json 2.range of all commits 3.exit, when selected it shoud show the result and then go back to selecting 1 or 2 (json or range ) and 3.try demo 4.exit.. when demo is tried, it must land on these optiopns back again. all on command line. make these chnages, then tell me to commit and push and then try the steps. It must be really user friendly


