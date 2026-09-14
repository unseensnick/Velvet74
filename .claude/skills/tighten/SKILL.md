---
name: tighten
description: Trim verbose prose, walls of text, journey narration, and WHAT comments from docs and code without losing vital info. Targets markdown files (README, template README, CLAUDE.md, rules, skills) and, when asked, script comments and docstrings. Applies the "WHY not WHAT" and "describe current behavior, not the journey" rules from `.claude/rules/code-quality.md` and `.claude/rules/prose-style.md`. Use after a change lands and the docs around it have accumulated cruft, or when a file feels heavier than it earns. Always plans before editing.
argument-hint: "<file or directory path>"
disable-model-invocation: true
allowed-tools:
  - Bash(git *)
---

Tighten the file(s) at `$ARGUMENTS` so a reader learns the same things in less time, with no vital info lost. **This skill always enters plan mode before editing.** It never deletes content silently.

## When to use this

- A `.md` file (README, `templates/*/README.md`, CLAUDE.md, `.claude/rules/*.md`, `.claude/skills/*.md`) has grown a wall of text or a journey paragraph.
- Comments or docstrings in a recently touched script restate the code instead of explaining the WHY.
- A handoff or planning doc accumulated mid-development churn and needs a "what actually shipped" pass.

Do NOT use this for:

- Code refactoring (prose only).
- A whole-repo sweep without a motivating change.
- KiCad design files, generated output (`ergogen/output/`), backups, or `.history/`.
- Files you have never read this session, on a hunch.

## Step 1: Scope and read

Parse `$ARGUMENTS`. For a directory, list the files with `git ls-files` so the user sees the scope. For a single file, read it in full.

Reject early if the path is a code file and the user did not ask for comment tightening (ask first), or if it is a generated, vendored or KiCad file.

`git log -10 -- <path>` for each target. If a file was just rewritten, ask whether it is really stale.

## Step 2: Classify every paragraph

| Class | Action |
|---|---|
| **Vital, well-written** | Keep verbatim. |
| **Vital, verbose** | Tighten. Keep every fact (measurements, clearances, part references, commands); cut filler. |
| **Vital, mis-located** | Suggest moving it (rationale into a commit message, module facts into the template README). |
| **Journey** ("we tried X then Y", "originally") | Cut, unless it is a "what failed, do not repeat" fact a future session needs. Then keep it, stated as a fact. |
| **WHAT comment** above self-describing code | Cut. |
| **WHY comment** | Keep. |
| **Redundant** (same info in another file in scope) | One canonical home; replace the duplicate with a link. |
| **Dead** (TODO with no substance, resolved work) | Cut. |
| **Stale** (names a function, file, part or value that no longer matches) | Verify with Grep/Read; surface for confirmation before cutting. |

Keep a tally per class.

## Step 3: Plan before editing

Use `EnterPlanMode`:

1. **Scope**: files, size, the motivating reason.
2. **Tally** per class.
3. **Before / after** for non-trivial edits.
4. **Open questions** via `AskUserQuestion` before exiting plan mode.
5. **Out of scope**: what you noticed but won't touch.

Call `ExitPlanMode` after approval.

## Step 4: Apply

- `Edit` for partial changes, one logical change per edit.
- Re-read the file when done. Revert any edit that reads worse.
- Grep for links or anchors other files relied on.

## Step 5: Check your own output

Grep the changed files for em dashes and AI watermarks, and fix them while you are in the file.

## Step 6: Verify and hand off

Read markdown back to confirm headings, lists, code fences and links are intact. Summarize per file: cut, tightened, moved (and where).

Do NOT commit. The user reviews and runs `/ship`.

## Rules

- Never silently delete. Every cut shows up in the plan, classified.
- Never widen scope mid-run.
- Vital info is sacred. If you can't tell whether a sentence is vital, ask.
- A number measured on the real board (caliper values, clearances, DRC counts) is always vital.
- No em dashes, no AI watermarks.
- If the file is shorter than ~50 lines, push back once.
