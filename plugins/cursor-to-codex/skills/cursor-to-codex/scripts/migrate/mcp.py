"""Migrate ``.cursor/mcp.json`` MCP servers into ``.codex/config.toml``.

Existing, unrelated config.toml content is preserved: only a managed region of
``[mcp_servers.*]`` tables is appended/replaced. Servers already declared
outside the managed region are skipped and reported.
"""

from __future__ import annotations

import json
import math
import re
import tomllib
from typing import Any

from utils import paths
from utils.report import ADDED, CHECK, NOT_ADDED
from utils.toml_writer import render_mcp_server

from migrate import MigrationContext

_VAR_ONLY = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
_BEARER = re.compile(r"^Bearer\s+\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
_VAR_ANY = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def run(ctx: MigrationContext) -> None:
    mcp_json = ctx.scope.cursor_dir / "mcp.json"
    if not mcp_json.is_file():
        return
    try:
        data = json.loads(mcp_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        ctx.report.add(ctx.scope.name, NOT_ADDED, "MCP", "mcp.json", f"Unparseable JSON ({exc}).")
        return

    servers = data.get("mcpServers") or data.get("mcp_servers") or {}
    if not isinstance(servers, dict) or not servers:
        return

    existing = _existing_server_names(ctx)
    blocks: list[str] = []
    for name in sorted(servers):
        cfg = servers[name]
        if not isinstance(cfg, dict):
            continue
        if name in existing:
            ctx.report.add(ctx.scope.name, CHECK, "MCP", name,
                           "Already present in config.toml outside managed block; left untouched.")
            continue
        table, status, notes = _convert_server(ctx, name, cfg)
        if table is None:
            ctx.report.add(ctx.scope.name, status, "MCP", name, notes)
            continue
        blocks.append(render_mcp_server(name, table))
        ctx.report.add(ctx.scope.name, status, "MCP", name, notes)

    if blocks:
        ctx.write_managed(ctx.scope.config_toml, "\n\n".join(blocks))


def _existing_server_names(ctx: MigrationContext) -> set[str]:
    if not ctx.scope.config_toml.is_file():
        return set()
    try:
        text = paths.outside_managed(ctx.scope.config_toml.read_text(encoding="utf-8"))
        parsed = tomllib.loads(text)
    except (tomllib.TOMLDecodeError, OSError):
        return set()
    servers = parsed.get("mcp_servers")
    return set(servers) if isinstance(servers, dict) else set()


def _convert_server(ctx: MigrationContext, name: str, cfg: dict[str, Any]):
    server_type = str(cfg.get("type", "")).lower()
    is_http = server_type in ("http", "streamable-http", "streamable_http") or (
        "url" in cfg and "command" not in cfg and server_type != "sse"
    )
    if server_type == "sse":
        return None, NOT_ADDED, "SSE transport has no Codex equivalent. Re-create as streamable HTTP."

    if is_http:
        return _convert_http(name, cfg)
    if "command" in cfg:
        return _convert_stdio(name, cfg)
    return None, NOT_ADDED, "Unrecognized server shape (no command or url)."


def _convert_stdio(name: str, cfg: dict[str, Any]):
    table: dict[str, Any] = {"command": cfg["command"]}
    notes: list[str] = []
    status = ADDED

    args = cfg.get("args")
    if isinstance(args, list) and args:
        table["args"] = [str(a) for a in args]
    if cfg.get("cwd"):
        table["cwd"] = str(cfg["cwd"])

    env = cfg.get("env")
    literal_env: dict[str, str] = {}
    env_vars: list[str] = []
    if isinstance(env, dict):
        for key, value in env.items():
            value = str(value)
            m = _VAR_ONLY.match(value)
            if m:
                env_vars.append(m.group(1))
            elif _VAR_ANY.search(value):
                literal_env[key] = value
                notes.append(f"env '{key}' contains ${{VAR}} interpolation Codex won't expand.")
                status = CHECK
            else:
                literal_env[key] = value
    if literal_env:
        table["env"] = literal_env
    if env_vars:
        table["env_vars"] = sorted(set(env_vars))

    _apply_timeout(cfg, table, notes)
    if _disabled(cfg):
        table["enabled"] = False
    note = " ".join(notes) if notes else "stdio server."
    if status == CHECK and not notes:
        note = "stdio server (review)."
    return table, status, note


def _convert_http(name: str, cfg: dict[str, Any]):
    table: dict[str, Any] = {"url": cfg["url"]}
    notes: list[str] = []
    status = ADDED

    headers = cfg.get("headers")
    http_headers: dict[str, str] = {}
    env_http_headers: dict[str, str] = {}
    if isinstance(headers, dict):
        for key, value in headers.items():
            value = str(value)
            bearer = _BEARER.match(value)
            var_only = _VAR_ONLY.match(value)
            if key.lower() == "authorization" and bearer:
                table["bearer_token_env_var"] = bearer.group(1)
            elif var_only:
                env_http_headers[key] = var_only.group(1)
            else:
                http_headers[key] = value
    if http_headers:
        table["http_headers"] = http_headers
    if env_http_headers:
        table["env_http_headers"] = env_http_headers

    _apply_timeout(cfg, table, notes)
    if _disabled(cfg):
        table["enabled"] = False
    notes.append("Verify it is a streamable HTTP (not SSE) endpoint.")
    status = CHECK
    return table, status, " ".join(notes)


def _apply_timeout(cfg: dict[str, Any], table: dict[str, Any], notes: list[str]) -> None:
    timeout = cfg.get("timeout")
    if isinstance(timeout, (int, float)) and timeout > 0:
        secs = max(1, math.ceil(timeout / 1000))
        table["startup_timeout_sec"] = secs
        table["tool_timeout_sec"] = secs
        notes.append(f"timeout {int(timeout)}ms -> {secs}s (startup + tool); review split.")


def _disabled(cfg: dict[str, Any]) -> bool:
    if cfg.get("disabled") is True:
        return True
    return cfg.get("enabled") is False
