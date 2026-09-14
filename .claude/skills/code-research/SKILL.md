---
name: code-research
description: Deep, fan-out research over the repo to answer a big question ("how does placement flow from Ergogen to the board end to end", "which scripts can overwrite hand work", "audit the template against the keyboard schematic", "where do the KiCad 8 assumptions still live"). Parallel explorer agents gather file:line-cited findings, high-stakes claims are adversarially verified against current files, and the result is a single prioritized report. Use for questions that span many files, NOT a one-file lookup and NOT a single-task pre-plan (use /scout for that).
argument-hint: "<research question>"
disable-model-invocation: false
allowed-tools:
  - Bash(git *)
  - Glob
  - Grep
  - Read
  - Agent
---

# code-research

Fans out exploration, reads files, verifies claims against **current files**, and synthesizes a report cited by **`file:line`**.

**This skill never edits files and never runs anything that writes a design file.** It produces a findings report; acting on it is a separate step the user approves.

## When to use

- Broad questions spanning scripts, the Ergogen config, the schematic, the board and the template.
- Audits where you want coverage and confidence, not a quick pointer.

## When NOT to use

- A single fact or one-file lookup. Just read it.
- Pre-planning one concrete task. Use `/scout`.

If invoked for something trivial, push back once.

## Standing defaults

- **Depth.** Open the files and verify each claim. Never infer from a name. A plausible mechanism that was not read is not a finding.
- **Completeness.** Research until every unknown is resolved or surfaced as an open question.
- **Open questions get asked, not guessed.**
- **Adversarial verification is mandatory**, including claims from memories, `Handoff.md`, READMEs and subagent findings.
- **Output format** follows [.claude/rules/plan-output.md](../../rules/plan-output.md).

## Method

### 1. Scope and clarify

Echo the question in one sentence. If vague, narrow it with `AskUserQuestion`. Decide the angle of decomposition (by script, by data flow Ergogen to schematic to board, by concern) and the inclusion bar.

### 2. Map the terrain (main thread)

- The relevant files (`Glob`, `Grep`); `git log --oneline -20`; `Handoff.md` and `.claude/rules/kicad.md` for known constraints and deliberate descopes.
- Note what is already covered or out of scope, verbatim, for every agent.
- Large KiCad files (the board is several MB): brief agents to `Grep` for references, nets or groups rather than reading the whole file.

### 3. Fan out parallel explorers

Split into 3-6 independent areas; one `Agent` (`subagent_type: Explore`) per area, all in one message. Brief each: goal and inclusion bar, exact paths, the out-of-scope list, `file:line` for every claim, High/Med/Low with a one-line why, ~500-700 words, an "uncertain" section.

### 4. Adversarially verify

Re-read current files for the highest-stakes or most surprising claims. Typical kills: "X doesn't exist" when it moved; a flagged bug the script already handles; deferred work; a value from memory the current board contradicts. Label findings **verified** or **reported**; anything that would change the plan must be verified.

### 5. Synthesize the report

One report into the conversation, per plan-output.md. Dedupe across agents; separate real gaps from deferred work; report the plan section as a plan when the research feeds implementation.

### 6. Hand off

End with "Ready to act" and the recommended first batch, or "Open questions block this". Do not start the fix.

## Scale knob

Verification is never the knob. Breadth scales: one fan-out for a focused audit, repeated rounds plus a completeness critic for "be exhaustive". Keep machine load gentle: parallel agents are fine, but never launch heavy local jobs (autorouting, rendering) from this skill.

## Rules

- Read-only.
- Every concrete claim cites `file:line`.
- Surface stale memories and docs instead of acting on them.
- Never fill a gap with an assumption.
- No interim narration: one sentence when the fan-out starts, then nothing until the report.
- No em dashes.
