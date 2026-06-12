---
name: cursor-to-codex
description: Use when migrating a repository or a user's global configuration from Cursor to Codex. Converts .cursor/rules/*.mdc, .cursorrules, .cursor/skills, .cursor/commands, .cursor/mcp.json, and .cursor/hooks.json into Codex artifacts (AGENTS.md, .agents/skills, .codex/config.toml, .codex/hooks.json). Trigger on "migrate Cursor to Codex", "move my Cursor config", "convert .cursor to Codex".
---

# Cursor to Codex migration

Migrate a repo's (and optionally the user's global) Cursor configuration into the
equivalent Codex artifacts. This is a **one-time** migration per repository: once
you cut over, `.codex/` + `AGENTS.md` + `.agents/skills/` become the source of
truth and `.cursor/` can be retired.

Deep mapping details, edge cases, and the docs-checked date live in
[references/differences.md](references/differences.md). Read it before resolving
any `Check before using` item.

## Autonomy

- Run the migration **without** asking for confirmation on each file; it never
  deletes `.cursor/` and only appends/replaces clearly marked managed regions.
- Never overwrite user content outside the managed markers in `AGENTS.md` or
  `.codex/config.toml`. Never delete the original Cursor files.
- Do the work, then report what landed and what needs human review.

## Migration order

Run the bundled CLI; it performs these conversions in order, for the project
scope (`./`) and the global scope (`~/`) when each has Cursor config:

1. **Instructions** — `.cursorrules` + `alwaysApply` rules -> root `AGENTS.md`
   managed region. Directory-scoped `globs` rules -> nested `AGENTS.md`.
2. **Rules** — agent-requested / manual rules -> Codex skills under
   `.agents/skills/<name>/`.
3. **Skills** — `.cursor/skills/<name>/` -> `.agents/skills/<name>/` (support
   files copied; `disable-model-invocation` -> `allow_implicit_invocation: false`).
4. **Commands** — `.cursor/commands/*.md` -> one-file skills (`$name`).
5. **MCP** — `.cursor/mcp.json` -> `.codex/config.toml` `[mcp_servers.*]`.
6. **Hooks** — `.cursor/hooks.json` -> `.codex/hooks.json` (scripts copied).

## Commands

Resolve the bundled script path (relative to this SKILL.md):

```bash
SCRIPT="$(dirname "$0")/scripts/cursor-to-codex.py"   # or pass the full path
```

In-session fix loop (run from the repo root):

```bash
# 1. Inventory what exists (writes nothing)
python3 scripts/cursor-to-codex.py --scan-only

# 2. Preview the conversion (writes nothing)
python3 scripts/cursor-to-codex.py --dry-run

# 3. Migrate for real (project + global where present)
python3 scripts/cursor-to-codex.py

# 4. Fix any "## MANUAL MIGRATION REQUIRED" notes, then re-run safely
python3 scripts/cursor-to-codex.py        # idempotent: no-op if nothing changed

# 5. Confirm the output is well-formed
python3 scripts/cursor-to-codex.py --validate-target
```

Useful flags: `--scope project|global|both` (default `both`), `--root <dir>`
(project root), and the advanced `--source <.cursor> --target <.codex>` pair.

## Report contract

After a run, present the per-scope status table exactly as the CLI prints it:

| Status | Item | Notes |
| --- | --- | --- |
| `Added` | `<Type>` name | What landed |
| `Check before using` | `<Type>` name | Lossy mapping to review |
| `Not Added` | `<Type>` name | No Codex equivalent |

- `Added` — migrated cleanly; usable as-is.
- `Check before using` — migrated but semantics differ (globs, hooks, HTTP MCP,
  disabled implicit invocation); a human must verify.
- `Not Added` — no Codex equivalent (SSE MCP, `beforeReadFile` hooks); re-create
  manually if needed.

The same content is written to `.codex/cursor-to-codex-report.txt`.

## After migrating

1. Resolve every `Check before using` row using `references/differences.md`.
2. Review and trust hooks with `/hooks` (hooks are enabled by default in Codex).
3. Restart Codex so it picks up new skills, config, and hooks.
4. Once verified, you may retire `.cursor/` (this tool never deletes it).
