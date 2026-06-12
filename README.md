# cursor-to-codex

A standalone, MIT-licensed **Codex plugin** that migrates a repository's (and
optionally your global) **Cursor** configuration into the equivalent **Codex**
artifacts — in one shot, idempotently, with zero third-party dependencies.

| Cursor source | Codex target |
| --- | --- |
| `.cursorrules`, `.cursor/rules/*.mdc` (`alwaysApply`) | `AGENTS.md` (root + nested) |
| `.cursor/rules/*.mdc` (agent/manual) | `.agents/skills/<name>/` |
| `.cursor/skills/<name>/` | `.agents/skills/<name>/` |
| `.cursor/commands/*.md` | `.agents/skills/<name>/` (one-file, `$name`) |
| `.cursor/mcp.json` | `.codex/config.toml` `[mcp_servers.*]` |
| `.cursor/hooks.json` (+ `hooks/`) | `.codex/hooks.json` (+ `.codex/hooks/`) |

Full mapping with statuses and edge cases:
[`plugins/cursor-to-codex/skills/cursor-to-codex/references/differences.md`](plugins/cursor-to-codex/skills/cursor-to-codex/references/differences.md).

### What is not migrated (and why)

- **Cursor editor/app settings** — `settings.json`, keybindings, themes, the
  model picker, privacy mode, and memories configure the editor or live in app
  state. Codex is an agent, not an editor, so it has no consumer for them. These
  are intentionally left alone.
- **Ignore files & cloud setup** — `.cursorignore`, `.cursorindexingignore`, and
  `.cursor/environment.json` have no Codex equivalent (Codex has no
  `.codexignore`; it restricts context via `.gitignore` + the sandbox). The tool
  detects them and reports them under `## MANUAL MIGRATION REQUIRED` instead of
  converting them — it never writes an unsupported target.

## Why it's safe

- **One-time, but re-runnable.** Designed as a one-time cutover, yet every write
  is idempotent: managed-region markers in `AGENTS.md` / `config.toml` and
  content comparison mean re-running changes nothing if nothing changed.
- **Never destructive.** It never deletes `.cursor/` and never overwrites your
  content outside clearly marked managed regions. Unrelated `config.toml` keys
  are preserved.
- **No dependencies.** Pure Python standard library, `>= 3.11`.

## Install

```bash
codex plugin marketplace add sumitpatil04/cursor-to-codex
# restart Codex
```

Then open `/plugins` and install **cursor-to-codex** (or run
`codex plugin add cursor-to-codex@cursor-to-codex`). To pull later updates:
`codex plugin marketplace upgrade`.

## Use it in Codex

Once installed, open Codex in a repository that still has a `.cursor/`
directory and ask in plain language — the skill triggers automatically:

- **"Migrate my Cursor configuration to Codex."**
- **"Preview the Cursor → Codex migration for this repo."** (dry run, writes nothing)

Codex performs the migration and prints a per-scope status table
(`Added` / `Check before using` / `Not Added`) plus any
`## MANUAL MIGRATION REQUIRED` notes. The same report is saved to
`.codex/cursor-to-codex-report.txt`. The flow Codex follows:

1. Inventory what exists (writes nothing).
2. Preview the conversion (writes nothing).
3. Migrate — project (`./`) and global (`~/`) scopes where present.
4. Surface anything that needs review, then validate the output.

After migrating: resolve any `Check before using` items (see
[`differences.md`](plugins/cursor-to-codex/skills/cursor-to-codex/references/differences.md)),
review and trust hooks with `/hooks`, restart Codex, and you can retire
`.cursor/` (the tool never deletes it).

## Repo layout

```
cursor-to-codex/
  .agents/plugins/marketplace.json          # marketplace catalog
  plugins/cursor-to-codex/
    .codex-plugin/plugin.json               # plugin manifest
    assets/icon.svg
    skills/cursor-to-codex/
      SKILL.md
      references/differences.md
      scripts/
        cursor-to-codex.py                  # entry shim
        cli.py                              # argparse + orchestration
        migrate/{instructions,rules,skills,commands,mcp,hooks,notices}.py
        utils/{frontmatter,toml_writer,paths,report,validate}.py
  tests/test_cursor_to_codex.py
```

## Development

```bash
python3 -m pytest tests/      # run the test suite (stdlib unittest-compatible)
ruff check .                  # optional lint (dev only; not needed by users)
```

## License

MIT — see [LICENSE](LICENSE).
