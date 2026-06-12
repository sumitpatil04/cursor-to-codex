"""Minimal, deterministic TOML rendering for the shapes this migrator emits.

Only ``[mcp_servers.<name>]`` tables are produced, so this is intentionally
limited to strings, booleans, integers, inline string/scalar arrays, and a
single level of subtables (``env``, ``http_headers``, ``env_http_headers``).
"""

from __future__ import annotations

from typing import Any

# Scalar keys rendered (in this order) directly under [mcp_servers.<name>].
_SCALAR_ORDER = [
    "command",
    "url",
    "args",
    "bearer_token_env_var",
    "cwd",
    "env_vars",
    "startup_timeout_sec",
    "tool_timeout_sec",
    "enabled",
]
# Subtable keys rendered (in this order) as [mcp_servers.<name>.<key>].
_SUBTABLE_ORDER = ["env", "http_headers", "env_http_headers"]


def escape_basic_string(value: str) -> str:
    out = value.replace("\\", "\\\\").replace('"', '\\"')
    out = out.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
    return f'"{out}"'


def render_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(render_value(v) for v in value) + "]"
    return escape_basic_string(str(value))


def _render_key_table(quoted_header: str, table: dict[str, Any]) -> list[str]:
    lines = [f"[{quoted_header}]"]
    for key in sorted(table):
        lines.append(f"{key} = {render_value(table[key])}")
    return lines


def render_mcp_server(name: str, table: dict[str, Any]) -> str:
    """Render one ``[mcp_servers.<name>]`` block (with ordered subtables)."""
    header = f"mcp_servers.{_quote_key(name)}"
    lines: list[str] = [f"[{header}]"]
    for key in _SCALAR_ORDER:
        if key in table and table[key] not in (None, "", []):
            lines.append(f"{key} = {render_value(table[key])}")
    for key in _SUBTABLE_ORDER:
        sub = table.get(key)
        if isinstance(sub, dict) and sub:
            lines.append("")
            lines.extend(_render_key_table(f"{header}.{key}", sub))
    return "\n".join(lines)


def _quote_key(key: str) -> str:
    """Bare key when safe; otherwise a quoted key."""
    if key and all(c.isalnum() or c in "-_" for c in key):
        return key
    return escape_basic_string(key)
