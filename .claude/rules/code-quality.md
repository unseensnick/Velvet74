---
alwaysApply: true
---

# Code quality

## Coding principles

- **DRY**: before adding a helper, search the repo for an existing equivalent. `scripts/` already has board-to-local transforms, library-table readers and pcbnew save helpers; reuse them.
- **YAGNI**: only add what the current task requires. No speculative CLI flags, optional parameters, or abstractions for hypothetical callers.
- **KISS**: prefer the simplest correct solution. Complexity must be justified by a concrete requirement, not elegance or anticipated scale.
- **Minimal blast radius, measured against the defect and not the diff**: a bug fix changes only what is broken, and changes it everywhere it is broken, not only at the site that reproduced. Grep for sibling sites (the same trap usually sits in more than one script) before calling a fix done, and name any you deliberately left. Leave working surrounding code untouched.
- **No standalone refactor sprints**: refactor alongside the feature or fix that motivated it. Never propose a separate cleanup pass unless the user asks.

## Anti-defaults

- No premature abstractions. Three similar lines beat a helper used once.
- Don't add features or improvements beyond what was asked.
- Don't refactor adjacent code while fixing a bug.
- No dead code or commented-out blocks. Git has history.
- No em dashes in prose, comments, commit messages, or PR bodies. Use commas, parentheses, periods, or colons.
- No AI watermarks. No "Co-Authored-By: Claude", "Generated with Claude Code", robot emoji footers, or similar tags in commits, PRs, code, or docs.

## Comments and docstrings

Short and useful: as brief as possible without losing vital info. Vital info is whatever saves the next reader from a bug or a wrong "fix": an invariant the code can't express, a coupling to another file or to KiCad's own behaviour, a measurement that fixed a number, a trap that already bit once.

- **The ban is restating the adjacent code.** Rename the symbol instead if it needed explaining.
- **WHY is the highest-value content**: why this approach, why not the obvious alternative, what breaks otherwise.
- **WHAT is allowed when it is not visible in the code**: the frame a coordinate is in (Ergogen y-up vs KiCad y-down), what a magic number was measured against, which KiCad version's API a call depends on.
- **Never a wall of text.** An explanation that needs paragraphs belongs in a README (the template's `README.md` for the RP2040 module); the comment states the rule and points there.
- A module docstring at the top of each script says what it does, how to run it (inside pcbnew and from a shell), and **what it overwrites**. Keep that current when behaviour changes.
- No calendar dates in code comments. Git records when a line was written.

## Naming (Python scripts)

- Files and functions: `snake_case`. Constants: `UPPER_SNAKE` (`ORIGIN`, `LED`, `GROUPS`). Private helpers: leading underscore.
- Units in names or comments when ambiguous: KiCad internal units vs millimetres (`pcbnew.FromMM` / `ToMM` at the boundary, millimetres everywhere else).
- Refer to parts by their schematic reference (`SW16`, `LED16`, `C116`, `U1`), matching the schematic. Never invent a second naming scheme.

## Code markers

`TODO: desc` for planned work, `FIXME: desc` for known bugs, `HACK: desc` for ugly workarounds (explain the proper fix), `NOTE: desc` for non-obvious context. Never `XXX`, `TEMP`, `REMOVEME`.

## File organization

- Imports: stdlib, then third-party (`pcbnew`), blank line between groups. No star imports.
- Scripts run under KiCad's bundled Python (`%LOCALAPPDATA%\Programs\KiCad\10.0\bin\python.exe`) unless the docstring says stdlib only; don't add third-party dependencies it lacks.
- Constants at the top, helpers in call order, entry point last.
