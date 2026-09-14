---
name: debug-fix
description: Find and fix a bug in the scripts, Ergogen config or KiCad design. Default is careful (reproduce, investigate, verify). Add `--fast` for an urgent minimal fix on a short-lived branch.
argument-hint: "[issue, error, or description] [optional: --fast]"
disable-model-invocation: true
allowed-tools:
  - Bash(git *)
  - Read
  - Glob
  - Grep
  - Edit
  - Write
---

Find and fix the following issue:

**Problem**: $ARGUMENTS

## Mode

Check $ARGUMENTS for `--fast`. Strip it before parsing the problem description.

- **Default**: careful debug-fix.
- **--fast**: urgent fix. A `fix/*` branch from `main`, minimal-change discipline, only the checks that touch the changed code. Before committing to fast mode, briefly confirm with the user that speed really matters more than thoroughness.

## Step 1: Understand

- Error or traceback: parse it for file, line, error type, and call chain (pcbnew tracebacks often point into KiCad's bindings; find the script line that called in).
- ERC/DRC report: note the violation type, the references and coordinates.
- Description: identify expected vs actual.

If unclear, ask before proceeding.

## Step 2: Branch (--fast only)

Create `fix/<short-description>` from `main`. **ASK** the user to confirm the branch name first. In default mode, branch handling happens in Step 7.

## Step 3: Reproduce (default only)

- Find the simplest trigger: a read-only `kicad-cli` check, a script run against a **copy** of the board in the scratchpad, or `npm run build` in `ergogen/`.
- Never reproduce by running a script over the real board or template when it would overwrite hand edits or routing (see `.claude/rules/kicad.md`).
- Can't reproduce? Check the KiCad version in use (10.0.3 vs 8.0.9 Python), whether KiCad had the file open, and `git log` for a recent fix.

## Step 4: Investigate (default only)

1. Locate the symptom: which file and line produces the wrong output.
2. Read the code path backwards: what called this, what data was passed.
3. `git log --oneline -20 -- <file>`, `git log --all --grep="<keyword>"`.
4. Form a hypothesis: "X is wrong because Y." Verify it with a targeted print or a read-only probe.
5. If wrong, trace a different path. Don't keep guessing the same hypothesis.

## Step 5: Fix

- Make the smallest correct change, at the place bad data originates.
- Grep for the same defect at sibling sites (the other scripts share transforms, table readers and save logic) and fix each or name why it was left.
- Don't refactor surrounding code; don't add defensive checks that mask the problem.
- A fix that must edit a `.kicad_*` file as text asks first (the protect-files hook will prompt too). Prefer changing the schematic in KiCad, or a pcbnew script, over hand-editing S-expressions.

In `--fast` mode: warn the user if the fix needs more than ~50 lines. No features, formatting, or unrelated cleanups.

## Step 6: Verify

**Default**:
- Re-run the reproduction and confirm it is fixed. Temporarily revert the fix and confirm the reproduction fails again.
- Run the checks for what changed: `kicad-cli sch erc --severity-error <sch>`, `kicad-cli pcb drc --schematic-parity --severity-error <pcb>` (the template's expected items are in its README), `npm run build` in `ergogen/`.
- Compare violation counts before and after, not just "it passes".

**--fast**: only the checks that touch the changed code. **ASK** whether to run more before shipping.

## Step 7: Wrap up

- Create a branch if not already on one and the user wants one.
- Stage only the fix (never backups zips, `Handoff.md`, generated output).
- Commit: `fix(scope): <what was wrong>` per `.claude/rules/workflow.md` (the `commit-msg` hook enforces it). **ASK** the user to confirm the message.
- Push and PR only through `/ship`, which confirms each step. Never merge.

## Rules

- NEVER skip confirmation steps in `--fast` mode.
- NEVER force-push. NEVER merge a PR.
- NEVER commit secrets or unrelated changes.
- NEVER run a board-writing script over uncommitted hand edits without the user's go-ahead.
- If the user says "skip" at any step, skip it.
