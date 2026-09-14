---
name: session-handoff
description: Write my-soffle's Handoff.md so a fresh session resumes cleanly, and update memory when this session produced durable facts. Use when the session is wrapping up ("I'm stepping away", "continue tomorrow", "wrap up"), before a `/clear`, when a long session has accumulated state that would be lost, or when the session is looping on a broken approach and a fresh agent would do better. Offer it proactively on those signals; do not wait to be asked.
argument-hint: "[optional: a narrower scope, e.g. 'handoff only']"
disable-model-invocation: false
allowed-tools:
  - Bash(git *)
  - Read
  - Glob
  - Grep
---

Write the handoff and bring memory in line with it, so the next session starts from an accurate picture instead of re-deriving one. The repo-specific twin of the global `session-handoff` skill: same spine, this repo's file set and conventions.

## Default behavior (no arguments)

Invoked with no arguments, do both, without further prompting:

1. **Rewrite `Handoff.md`** at the repo root to the structure below.
2. **Update memory** when this session produced a durable fact (a trap, a user decision, a measurement, a proven placement), and fix or flag any memory this session proved stale.

`$ARGUMENTS` narrows that scope ("handoff only"). It never widens it.

## Step 1: Establish the real state before writing

Never write the handoff from conversation memory alone:

- `git status --short` for a dirty tree, and `git log origin/<branch>..HEAD --oneline` for what is unpushed. State both in the header, including "pushed and clean" when true. Call out uncommitted design files (`*.kicad_pcb`, `*.kicad_sch`, `*.kicad_pro`) by name: they are the work most easily lost.
- `git log --oneline -20` for the session's actual commits.
- Read the existing `Handoff.md`. If it still describes a previous session as "this session", **rewrite it rather than appending**.
- Note any scratchpad files the next session needs (search pipelines, test boards). Scratchpad directories are per session, so copy anything essential somewhere durable or say plainly that it will be gone.

## Step 2: The handoff structure

Omit a section only when it genuinely has nothing.

- **Header**: branch, HEAD short-SHA, pushed/unpushed count, tree state, whether KiCad has files open that a script must not touch, and any standing instruction from the user.
- **Read first**: the two or three files that frame the work (`CLAUDE.md`, `.claude/rules/kicad.md`, the template README).
- **Goal**: the board-level outcome, not the next tactical step.
- **Current state**: what works, what is half-done, what is deliberately not done. Give measured numbers where they exist (DRC counts, unrouted nets, clearances, Freerouting pass rate).
- **Files**: only those central to the in-progress work, each with its role and status.
- **Changes made**: the commit range, one line per commit.
- **What failed / do not repeat**: the highest-value section. The approach, what was expected, what happened. Group variations of one idea. Include process failures (wrong KiCad Python, a script run while KiCad had the file open, too many parallel jobs).
- **Next steps**: ordered and concrete, with which step gates which.
- **Parked**: items waiting on the user. Say not to raise them unprompted.
- **Durable gotchas**: facts that outlive the session.
- **Verify**: the ERC/DRC/Ergogen commands and expected results.

## Step 3: Where things go

| File | Holds | Convention |
|---|---|---|
| `Handoff.md` (root) | Session state | **Gitignored. Edit on disk, never `git add` it.** |
| Memory (`MEMORY.md` index plus one file per fact) | Durable cross-session facts | Update the existing file for a topic rather than adding a near-duplicate; keep the index line current |
| `templates/rp2040-inner-column/README.md` | Module facts (placement, checks, routability) | Only when the user asked for doc changes; it is outside the handoff's scope otherwise |

Observations blocked on the user go to memory or the Parked section, never into a README.

## Step 4: Hand back

Report the final branch state so the user knows whether anything is left to commit or push. Then give the next-session prompt verbatim:

> Read `Handoff.md` and continue from where the previous session left off. Before you start working, summarize back to me your understanding of the goal, current state, and what you plan to do next so I can confirm before you proceed.

## Rules

- Verify state with git before writing it down. A handoff asserting "pushed and clean" that is neither is worse than none.
- Do not hide failures.
- Label hypotheses as hypotheses.
- Do not pad. No progress narration: it is a briefing, not a journal.
- No em dashes, no AI watermarks.
- This skill does not commit or push anything.
