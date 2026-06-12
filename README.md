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
        migrate/{instructions,rules,skills,commands,mcp,hooks}.py
        utils/{frontmatter,toml_writer,paths,report,validate}.py
  tests/test_cursor_to_codex.py
```

## Contributing the skill to openai/skills

The bundled skill is self-contained (pure stdlib, references one level deep), so
it can also be contributed to the community [`openai/skills`](https://github.com/openai/skills)
repo for discoverability — independent of this plugin, which is the source of
truth:

1. Fork `openai/skills`.
2. Copy `plugins/cursor-to-codex/skills/cursor-to-codex/` into the fork at
   `.experimental/cursor-to-codex/` (the community area; `.curated/` is
   OpenAI-owned, do not target it).
3. Open a PR. No code changes are required.

## Development

```bash
python3 -m pytest tests/      # run the test suite (stdlib unittest-compatible)
ruff check .                  # optional lint (dev only; not needed by users)
```

## License

MIT — see [LICENSE](LICENSE).
