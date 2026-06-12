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

## Install (public)

Once this repo is pushed to GitHub:

```bash
codex plugin marketplace add sumitpatil04/cursor-to-codex
# restart Codex, then:
/plugins            # install "cursor-to-codex"
```

Then ask Codex: **"Migrate my Cursor configuration to Codex."**

## Try it locally now

```bash
./scripts/install-local.sh             # register this repo as a local marketplace
./scripts/install-local.sh --personal  # also copy into ~/.codex/plugins
```

Restart Codex, open `/plugins`, install `cursor-to-codex`.

If your marketplace is a *different* repo that references this one, use a
git-subdir source instead of `local` in its `marketplace.json`:

```json
{ "source": { "source": "git", "repository": "sumitpatil04/cursor-to-codex", "path": "plugins/cursor-to-codex" } }
```

## Manual CLI (no install)

```bash
cd /path/to/your/repo
PY=plugins/cursor-to-codex/skills/cursor-to-codex/scripts/cursor-to-codex.py
python3 $PY --scan-only        # inventory, writes nothing
python3 $PY --dry-run          # preview, writes nothing
python3 $PY                    # migrate (project + global where present)
python3 $PY --validate-target  # verify output is well-formed
```

Flags: `--scope project|global|both` (default `both`), `--root <dir>`, and the
advanced `--source <.cursor> --target <.codex>` pair.

## Repo layout

```
cursor-to-codex/
  .agents/plugins/marketplace.json          # local marketplace catalog
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
  scripts/install-local.sh
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
