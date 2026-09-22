---
alwaysApply: true
---

# Commit workflow

After a change, create a git commit when the user asks for one. Do not push unless asked; pushing and PRs go through `/ship`, which confirms each step.

Never commit `*-backups/` folders (KiCad's project zips, including `templates/rp2040-inner-column/RP2040InnerColumn-backups/`), untracked backup zips, `Handoff.md`, or anything `.gitignore` covers.

## Commit message standard

Write commits the user could skim later and understand. Scale the structure to the change: a typo is one line; a feature gets a body.

**Subject (always):** `type(scope): summary`

- Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `build`, `ci`, `style`, `revert`. Scope optional, lower-case (`pcb`, `sch`, `lib`, `ergogen`, `scripts`, `templates`, `kicad`, `claude`).
- Imperative mood, lower-case, no trailing period, `<=72` chars.
- Never a bare `#N`: GitHub auto-links it to an issue or PR of this repo. Link a real one as `owner/repo#N` (`unseensnick/Velvet74#N`).

**Body (omit only for trivial commits; wrap ~72 cols):**

1. **Lead** with 1-2 plain-language sentences: what changed and why it matters. Never open with implementation detail.
2. **Bullets** for the notable changes, benefit-first and scannable. For a large commit, group them under short headers (the board-facing effect first, then `Under the hood:`).
3. **Footer (optional):** verification (ERC/DRC result, Freerouting proof), deferred items, tradeoffs.

**Rules:** blank line after the subject; no em dashes; no AI watermarks (no `Co-Authored-By` naming Claude or Anthropic, no "Generated with" footer, no robot emoji).

**Checklist, on every commit** (including `docs`, `chore` and one-line fixes):

1. Subject is `type(scope): summary`: a real type, imperative, lower-case, no trailing period, `<=72` chars.
2. No bare `#N` anywhere in the message.
3. No em dashes; no AI watermark.
4. Non-trivial commit: body leads with plain sentences, then benefit-first bullets.

## Enforcement

`.githooks/commit-msg` rejects a message that breaks checks 1 to 3 (merge, revert, `fixup!` and `squash!` subjects are let through). Activate it once per clone with `git config core.hooksPath .githooks`. A rejected commit is reworded and committed again; never `--no-verify`.

`.github/workflows/commit-standards.yml` runs the same hook over every commit a PR adds, plus the Claude Code hook fixtures, so a clone without the hook still gets checked.
