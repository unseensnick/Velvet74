---
name: scout
description: Investigate a non-trivial task, then produce the plan for it. Emits a file:line-cited findings report covering current behavior, the schematic/board/script state it depends on, helpers to reuse and stale docs, followed by a sequenced plan and any blocking open questions. Use before changing a placement or build script, moving parts between the template and the keyboard board, changing Ergogen geometry, or any change that touches several files. The point is to ground the plan in evidence, not memory. Investigates deeply and verifies adversarially by default; never edits files.
argument-hint: "<task description> (e.g., 'bring the rp2040 module into the inner column', 'move encoder 2 up 1 mm')"
disable-model-invocation: false
allowed-tools:
  - Bash(git *)
---

Investigate the task described by `$ARGUMENTS` deeply enough that the resulting plan cannot contain hallucinated functions, stale memories, or assumed KiCad behavior. Output is a findings report **and the plan that follows from it**. **This skill never edits files and never runs a script that writes a design file**: it proposes, the user approves, implementation is a separate step.

## Standing defaults

- **Depth.** Open the files and verify each claim against current code or the current board/schematic text. Never infer from a file or symbol name. A plausible mechanism that was not read is not a finding.
- **Completeness.** Keep investigating until every unknown is resolved. Do not fill a gap with an assumption to finish the report.
- **Open questions get asked, not guessed.** Anything that cannot be settled from the files becomes an explicit numbered question, answered before implementation starts.
- **Adversarial verification is mandatory.** Re-read the claims that would most distort the plan if wrong, including claims from `Handoff.md`, memories, READMEs and subagent findings.
- **Output format** follows [.claude/rules/plan-output.md](../../rules/plan-output.md).

## When to use this

- Changing a script in `scripts/`, especially one that saves boards (it may overwrite routing or hand placement).
- Moving parts or groups between `templates/rp2040-inner-column/` and `velvet74.kicad_pcb`.
- Changing Ergogen geometry that feeds the placement script.
- Acting on a claim from memory or a Handoff that names specific files, parts, coordinates or functions.

Do NOT use it for one-line tweaks, work entirely inside a file you just edited, or the happy-path continuation of an active task. If invoked for trivial work, push back once.

## Step 1: Parse and scope

Echo the task in one sentence so the user can correct a misreading. If it is vague ("board stuff"), use `AskUserQuestion` to narrow: which board or script, which parts, is there a Handoff or recent commit range framing it. Do not proceed with a vague scope.

## Step 2: Cheap reads before delegating

On the main thread:

1. `Handoff.md` in the repo root if present. Note what shipped, what was deferred, what is off-limits.
2. `git log --oneline -20` and `git status --short` (uncommitted hand edits in a design file change what a plan may do).
3. [.claude/rules/kicad.md](../../rules/kicad.md) for ownership rules and the traps a plan must respect.
4. The docstring of every script the task touches: what it overwrites.

Write down for Step 3: the task as scoped, branch and recent commit shape, uncommitted design files, and the deferred list verbatim. **The most common audit failure is flagging deferred work as missing.**

## Step 3: Identify investigation areas

Brief one `Explore` agent per area that applies, all in one message:

| Area | When relevant | What to brief |
|---|---|---|
| Scripts | Always when a script is involved | Target script, what it reads and writes, helpers already in `scripts/`. |
| Board / schematic state | Placement, nets, groups | The relevant `.kicad_pcb` / `.kicad_sch` sections (footprints by reference, groups, net classes in `.kicad_pro`). |
| Ergogen | Geometry | `ergogen/config.yaml` zones and the points feeding the refs involved. |
| KiCad API | New pcbnew calls | KiCad 10 behaviour of the call, from KiCad's own Python bindings or a quick read-only probe. |

Brief each as a colleague who has not seen this conversation: the goal, exact paths, a `file:line` for every claim, ~500 words, and an "uncertain" section.

## Step 4: Adversarially verify

Re-read the claims that would most distort the plan if wrong. Typical kills: something "doesn't exist" when it moved; a problem the script already handles; deferred work; a coordinate or clearance quoted from memory that the current board contradicts. Label findings **verified** or **reported**; anything load-bearing must be verified.

## Step 5: Synthesize the report and the plan

Into the conversation, in the structure from plan-output.md. Additions:

- A claim without a `file:line` from something actually read goes in Open questions.
- A contradiction between memory, `Handoff.md` or a README and current files is itself a finding under Stale docs.
- The plan names the helper it reuses, and names every file a step will overwrite and how that work is protected (commit first, KiCad closed, `.kicad_pro` restored).
- A placement step names how routability will be proven, not just DRC.

## Step 6: Hand off

End with **"Ready to implement."**, **"Open questions block implementation."**, or **"Investigation incomplete."** (name what is unchecked). Then stop. Do not start editing and do not call `EnterPlanMode`.

## Rules

- Never edits files, never runs a script that saves a board, schematic or project file.
- Every claim cites `file:line`. Memory and Handoff claims are hypotheses until cited.
- Cap each subagent at ~500 words; the report follows plan-output.md's word cap.
- No interim narration: one sentence when agents are spawned, then nothing until the report.
- No em dashes.
