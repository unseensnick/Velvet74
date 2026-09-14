---
name: ship
description: Scan changes, commit, push, and create a PR, with confirmation at each step. Never merges.
argument-hint: "[optional commit message or PR title]"
disable-model-invocation: true
allowed-tools:
  - Bash(git status)
  - Bash(git status *)
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(git add *)
  - Bash(git commit *)
  - Bash(git push *)
  - Bash(git checkout -b *)
  - Bash(git switch *)
  - Bash(git branch *)
  - Bash(gh pr create *)
  - Bash(gh pr view *)
---

Ship the current changes through commit, push, and PR creation. Confirm with the user before each step using the AskUserQuestion tool.

## Step 1: Scan

- `git status` for changed, staged and untracked files; `git diff --stat` and `git diff` for what changed (a `.kicad_pcb` diff is large: summarize it by footprint references, groups, tracks and zones touched instead of pasting it).
- `git log --oneline -5` for recent commit style.
- Present a summary: modified, added, deleted, untracked.
- If there are no changes, say so and stop.

## Step 2: Stage and commit

- Propose which files to stage. New KiCad backup zips in `*-backups/` are tracked on purpose: list them and stage them when the user agrees. **Never stage**:
  - KiCad local history: `.history/`
  - Local and generated: `Handoff.md`, `*.kicad_prl`, `fp-info-cache`, `ergogen/output/`, `ergogen/node_modules/`, `__pycache__/`
  - Secrets: `.env*`, `*.pem`, `*.key`, `credentials.json`
  - `ergogen/package-lock.json` unless the dependency change is intended
- Draft a commit message per `.claude/rules/workflow.md`: `type(scope): summary`, lower-case, imperative, `<=72` chars, body leading with plain sentences then benefit-first bullets, no bare `#N`, no em dashes.
- **Do NOT include `Co-Authored-By` lines or any AI attribution.**
- **ASK the user to confirm or edit**: show the exact files and the message.
- Only after confirmation: stage and commit. If the `commit-msg` hook rejects it, fix the message and commit again (a new commit, never `--amend` of a pushed one, never `--no-verify`).

## Step 3: Push

- Pushing to `main` is blocked by the command hook; ship from a feature branch. If on `main`, propose a branch name (`feat/...`, `fix/...`) and **ASK** before creating it with `git switch -c`.
- If the branch has no upstream, propose `git push -u origin <branch>`.
- **ASK the user to confirm** before pushing. Never force-push.

## Step 4: Pull request

- Check for an existing PR with `gh pr view`. If one exists, show the URL and stop.
- Analyze ALL commits on the branch vs `main`, not just the latest.
- Draft a title (under 72 chars) and body with `## Summary` (2-4 bullets) plus, when the board changed, the verification run (ERC/DRC counts, routability proof).
- **No `## Test plan` section. No "Generated with Claude Code" footer or any AI attribution.**
- **ASK the user to confirm or edit** the title and body.
- Only after confirmation: `gh pr create --repo unseensnick/my-soffle --base main --title "..." --body "..."`.
- Show the PR URL. **Stop there: merging is the user's call** (`gh pr merge` is blocked by the command hook).

## Rules

- NEVER skip a confirmation step.
- NEVER force-push. NEVER merge.
- NEVER commit `.history/`, `Handoff.md`, secrets or credential files.
- If the user says "skip" at any step, skip it and move to the next.
- If $ARGUMENTS is provided, use it as the commit message / PR title.
