# Cursor -> Codex: mapping reference

> **Docs last checked: 2026-06-12** against the official Codex docs:
> [config reference](https://developers.openai.com/codex/config),
> [MCP](https://developers.openai.com/codex/mcp),
> [skills](https://developers.openai.com/codex/skills),
> [hooks](https://developers.openai.com/codex/hooks),
> [AGENTS.md](https://developers.openai.com/codex/agents),
> [build plugins](https://developers.openai.com/codex/plugins/build).
> Codex schemas evolve; re-verify these before relying on a `Check before using`
> mapping. Target paths are centralized in `scripts/utils/paths.py`.

## Target locations (where things go)

| Surface | Project scope | Global scope |
| --- | --- | --- |
| Instructions | `./AGENTS.md` (+ nested `AGENTS.md`) | `~/.codex/AGENTS.md` |
| Skills | `./.agents/skills/<name>/` | `~/.agents/skills/<name>/` |
| MCP + config | `./.codex/config.toml` | `~/.codex/config.toml` |
| Hooks | `./.codex/hooks.json` (+ `./.codex/hooks/`) | `~/.codex/hooks.json` |

Skills live under **`.agents/skills`** (the agent-skills standard), not
`.codex/skills`. Codex has no separate "prompts" directory — reusable prompts
are skills, so Cursor commands become one-file skills.

## Instructions

| Cursor source | Codex target | Status | Notes |
| --- | --- | --- | --- |
| `.cursorrules` (legacy) | root `AGENTS.md` managed block | `Added` | Appended; user content outside the block is preserved. |
| root `AGENTS.md` | root `AGENTS.md` | `Check before using` | Shared by Cursor and Codex; only the managed block is updated, never overwritten. |
| `.mdc` `alwaysApply: true` | root `AGENTS.md` managed block | `Added` | Frontmatter stripped; one `## Rule: <name>` section per rule. |
| `.mdc` `globs` (dir-scoped) | nested `AGENTS.md` in that dir | `Check before using` | Codex scopes by directory, not arbitrary globs. Verify the directory matches intent. |
| `.mdc` `globs` (not dir-scoped, e.g. `**/*.md`) | root `AGENTS.md` (inlined) | `Check before using` | Inlined with an "Applies to files matching: …" preamble; Codex won't auto-scope by extension. |
| `.mdc` agent-requested (`description`, no globs/always) | `.agents/skills/<name>/SKILL.md` | `Check before using` | `description` drives implicit invocation. |
| `.mdc` manual (`@`-referenced) | `.agents/skills/<name>/SKILL.md` | `Check before using` | Invoke explicitly with `$name`. |

A glob is "directory-scoped" when it has a leading path with no wildcards before
the first `*`/`?`/`[`/`{` (e.g. `src/**/*.ts` -> `src/`). `*.ts` and `**/*.ts`
are not directory-scoped.

## Skills

| Cursor source | Codex target | Status | Notes |
| --- | --- | --- | --- |
| `.cursor/skills/<name>/SKILL.md` (+ `scripts/`, `references/`, `assets/`) | `.agents/skills/<name>/` | `Added` | Whole directory copied; binary support files preserved. |
| `disable-model-invocation: true` | `.agents/skills/<name>/agents/openai.yaml` | `Check before using` | Mapped to `policy.allow_implicit_invocation: false`; `$name` still works. |

Symlinked `.cursor/skills` / `.cursor/rules` are resolved so rules are not
double-migrated as skills.

## Commands

| Cursor source | Codex target | Status | Notes |
| --- | --- | --- | --- |
| `.cursor/commands/*.md` | `.agents/skills/<name>/SKILL.md` (one-file) | `Added` | `description` derived from the first heading/line; invoke with `$name`. |

## MCP servers (`.cursor/mcp.json` -> `.codex/config.toml`)

Only a managed region of `[mcp_servers.*]` tables is written; unrelated
`config.toml` content (other servers, `notify`, `projects`, …) is parsed with
`tomllib` and preserved. Servers already declared outside the managed region are
skipped and reported.

| Cursor field | Codex field | Status | Notes |
| --- | --- | --- | --- |
| stdio `command` / `args` | `command` / `args` | `Added` | |
| stdio `cwd` | `cwd` | `Added` | |
| `env` literal value | `[mcp_servers.X.env]` | `Added` | |
| `env` value `${VAR}` (whole value) | `env_vars = ["VAR"]` | `Added` | Forwarded from the environment. |
| `env` value with embedded `${VAR}` | kept literal in `env` | `Check before using` | Codex does not expand `${VAR}` inside `env` values. |
| `type: "http"` + `url` | `url` (streamable HTTP) | `Check before using` | Confirm the endpoint is streamable HTTP, not SSE. |
| header `Authorization: "Bearer ${VAR}"` | `bearer_token_env_var = "VAR"` | `Added` | |
| header value `${VAR}` | `[mcp_servers.X.env_http_headers]` | `Added` | Value pulled from the environment. |
| header static value | `[mcp_servers.X.http_headers]` | `Added` | |
| `type: "sse"` | — | `Not Added` | Codex has no SSE transport; re-create as streamable HTTP. |
| `timeout` (ms) | `startup_timeout_sec` + `tool_timeout_sec` (s) | `Check before using` | ms→s (ceil), applied to both; review the split. |
| `disabled: true` / `enabled: false` | `enabled = false` | `Added` | |

## Hooks (`.cursor/hooks.json` -> `.codex/hooks.json`)

Hooks are **enabled by default** in Codex, so no `[features]` flag is written
(`hooks` is the canonical key; `codex_hooks` is a deprecated alias). Hook scripts
under `.cursor/hooks/` are copied to `.codex/hooks/` and command paths rewritten.
Codex requires reviewing and trusting hooks via `/hooks` before they run.

| Cursor event | Codex event | Matcher | Status | Notes |
| --- | --- | --- | --- | --- |
| `beforeShellExecution` | `PreToolUse` | `Bash` | `Check before using` | stdin/stdout schema differs. |
| `afterShellExecution` | `PostToolUse` | `Bash` | `Check before using` | Cursor's command-regex matcher is dropped (Codex matches tool names). |
| `beforeMCPExecution` | `PreToolUse` | (none) | `Check before using` | Codex matches MCP tool names, not a global MCP hook. |
| `afterMCPExecution` | `PostToolUse` | (none) | `Check before using` | As above. |
| `beforeSubmitPrompt` | `UserPromptSubmit` | — | `Check before using` | schema differs. |
| `afterFileEdit` | `PostToolUse` | `Edit\|Write` | `Check before using` | Maps to `apply_patch` post-use. |
| `stop` | `Stop` | — | `Check before using` | Output contract differs (JSON required to continue). |
| `subagentStart` | `SubagentStart` | (none) | `Check before using` | schema differs. |
| `subagentStop` | `SubagentStop` | (none) | `Check before using` | Output contract differs. |
| `beforeReadFile` | — | — | `Not Added` | Codex has no read-file hook. |

If a non-managed `.codex/hooks.json` already exists, the migration writes
`.codex/hooks.cursor-to-codex.json` instead (so your existing hooks are not
clobbered) and flags it for manual merge. Re-runs detect the
`_cursor_to_codex` sentinel and regenerate in place.

## Settings & ignore files

Cursor is a VS Code fork, so most of its "settings" configure the *editor*, not
an agent. Codex is an agent (CLI + IDE extension) and has no consumer for them,
so they are intentionally not migrated. Ignore files and cloud-agent setup have
no Codex equivalent either, but the tool detects them and surfaces a manual note
(report-only — no Codex file is written, and no unsupported `.codexignore` is
fabricated).

| Cursor source | Codex target | Status | Notes |
| --- | --- | --- | --- |
| `.cursorignore` | — | `Not Added` | Codex has no `.codexignore` ([openai/codex#1397](https://github.com/openai/codex/issues/1397)); restrict context via `.gitignore` + sandbox/`shell_environment_policy`. Reported for manual review. |
| `.cursorindexingignore` | — | `Not Added` | As above; Codex does not index from a per-repo ignore file. Reported for manual review. |
| `.cursor/environment.json` | — | `Not Added` | Cursor background/cloud-agent setup; Codex cloud uses its own environment config. Reported for manual review. |
| editor `settings.json` / `keybindings.json` / themes | — | `Not Added` | Editor settings; Codex has no consumer. Not detected (intentional). |
| Cursor model picker / rules toggles / privacy / memories | — | `Not Added` | App state, not portable repo files. Not migratable. |

## Not migrated

- **Subagents** — Cursor has no subagent definition files to convert.
- **Cursor matcher regexes** on shell hooks — Codex matchers filter tool names,
  not command text; carried into the report as a note, not silently dropped.
- **Cursor editor/app settings** — `settings.json`, keybindings, themes, model
  picker, privacy mode, and memories have no Codex equivalent (Codex is an agent,
  not an editor). Not migrated by design.
- **Ignore files & `environment.json`** — Codex cannot consume `.cursorignore`,
  `.cursorindexingignore`, or `.cursor/environment.json`; they are detected and
  reported under "MANUAL MIGRATION REQUIRED" rather than converted.
