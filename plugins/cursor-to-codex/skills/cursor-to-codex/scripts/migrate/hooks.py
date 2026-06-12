"""Migrate ``.cursor/hooks.json`` into ``.codex/hooks.json``.

Cursor hook events are mapped to the closest Codex lifecycle events. Cursor's
command-level ``matcher`` (a regex over the shell command) has no Codex
equivalent (Codex matches tool *names*), so it is dropped and surfaced as a
note. Hook scripts under ``.cursor/hooks/`` are copied to ``.codex/hooks/``.
"""

from __future__ import annotations

import json
from typing import Any

from utils.paths import HOOKS_SENTINEL
from utils.report import ADDED, CHECK, NOT_ADDED

from migrate import MigrationContext

# Cursor event -> (Codex event, default matcher or None, note)
_EVENT_MAP: dict[str, tuple[str, str | None, str]] = {
    "beforeShellExecution": ("PreToolUse", "Bash", "shell pre-exec; stdin schema differs."),
    "afterShellExecution": ("PostToolUse", "Bash", "shell post-exec; stdin schema differs."),
    "beforeMCPExecution": ("PreToolUse", "", "Codex matches MCP tool names, not a global MCP hook."),
    "afterMCPExecution": ("PostToolUse", "", "Codex matches MCP tool names, not a global MCP hook."),
    "beforeSubmitPrompt": ("UserPromptSubmit", None, "prompt-submit; stdin schema differs."),
    "afterFileEdit": ("PostToolUse", "Edit|Write", "maps to apply_patch (Edit|Write) post-use."),
    "stop": ("Stop", None, "turn-stop; output contract differs (JSON required)."),
    "subagentStart": ("SubagentStart", "", "subagent start; stdin schema differs."),
    "subagentStop": ("SubagentStop", "", "subagent stop; output contract differs."),
}
_NOT_SUPPORTED = {"beforeReadFile": "Codex has no read-file hook."}
_EVENT_ORDER = list(_EVENT_MAP) + list(_NOT_SUPPORTED)


def run(ctx: MigrationContext) -> None:
    hooks_json = ctx.scope.cursor_dir / "hooks.json"
    if not hooks_json.is_file():
        return
    try:
        data = json.loads(hooks_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        ctx.report.add(ctx.scope.name, NOT_ADDED, "Hook", "hooks.json", f"Unparseable JSON ({exc}).")
        return

    source_hooks = data.get("hooks")
    if not isinstance(source_hooks, dict) or not source_hooks:
        return

    codex_hooks: dict[str, list[dict[str, Any]]] = {}
    for event in _EVENT_ORDER:
        entries = source_hooks.get(event)
        if not isinstance(entries, list) or not entries:
            continue
        if event in _NOT_SUPPORTED:
            ctx.report.add(ctx.scope.name, NOT_ADDED, "Hook", event, _NOT_SUPPORTED[event])
            continue
        codex_event, matcher, note = _EVENT_MAP[event]
        for entry in entries:
            if not isinstance(entry, dict) or "command" not in entry:
                continue
            group = _build_group(entry, matcher)
            codex_hooks.setdefault(codex_event, []).append(group)
            extra = ""
            if entry.get("matcher"):
                extra = f" Cursor matcher '{entry['matcher']}' dropped (Codex matches tool names)."
            ctx.report.add(ctx.scope.name, CHECK, "Hook", f"{event} -> {codex_event}", note + extra)

    if not codex_hooks:
        return

    _copy_hook_scripts(ctx)
    target, status, notes = _resolve_target(ctx)
    payload = {HOOKS_SENTINEL: True, "hooks": codex_hooks}
    ctx.write_text(target, json.dumps(payload, indent=2) + "\n")
    ctx.report.add(ctx.scope.name, status, "Hook", target.name, notes)
    ctx.report.manual("Codex requires reviewing & trusting hooks via /hooks before they run. "
                      "Hooks are enabled by default; no [features] flag is written.")


def _build_group(entry: dict[str, Any], matcher: str | None) -> dict[str, Any]:
    command = str(entry["command"]).replace(".cursor/hooks", ".codex/hooks")
    handler: dict[str, Any] = {"type": "command", "command": command}
    if isinstance(entry.get("timeout"), (int, float)):
        handler["timeout"] = int(entry["timeout"])
    group: dict[str, Any] = {}
    if matcher:
        group["matcher"] = matcher
    group["hooks"] = [handler]
    return group


def _copy_hook_scripts(ctx: MigrationContext) -> None:
    src = ctx.scope.cursor_dir / "hooks"
    if src.is_dir():
        ctx.copy_tree(src, ctx.scope.hooks_dir)


def _resolve_target(ctx: MigrationContext):
    target = ctx.scope.hooks_json
    if target.is_file():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}
        if not (isinstance(existing, dict) and existing.get(HOOKS_SENTINEL)):
            alt = target.with_name("hooks.cursor-to-codex.json")
            return alt, CHECK, "Existing hooks.json preserved; wrote alongside for manual merge."
    return target, ADDED, "Mapped Cursor hooks; review/trust via /hooks."
