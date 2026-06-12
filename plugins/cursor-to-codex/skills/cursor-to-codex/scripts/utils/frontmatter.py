"""Minimal frontmatter parser for Cursor ``.mdc`` and ``SKILL.md`` files.

Pure stdlib: supports the small YAML subset Cursor actually emits in rule and
skill frontmatter (scalars, booleans, inline lists, and block lists). This is
deliberately not a full YAML parser; it covers ``description``, ``globs``,
``alwaysApply``, ``name``, and ``disable-model-invocation``.
"""

from __future__ import annotations

import re
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?", re.DOTALL)


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (metadata, body). Empty metadata when no frontmatter is present."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    meta = _parse_block(match.group(1))
    body = text[match.end():]
    return meta, body


def _parse_block(block: str) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        i += 1
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            # Possible block list on following indented "- item" lines.
            items: list[str] = []
            while i < len(lines) and lines[i].lstrip().startswith("- "):
                items.append(_coerce_scalar(lines[i].lstrip()[2:].strip()))
                i += 1
            meta[key] = items if items else ""
        else:
            meta[key] = _coerce_value(value)
    return meta


def _coerce_value(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_coerce_scalar(part.strip()) for part in _split_csv(inner)]
    # Bare comma-separated lists (Cursor commonly writes `globs: *.ts, *.tsx`).
    if "," in value and not (value.startswith('"') or value.startswith("'")):
        return [_coerce_scalar(part.strip()) for part in _split_csv(value)]
    return _coerce_scalar(value)


def _split_csv(value: str) -> list[str]:
    return [part for part in (p.strip() for p in value.split(",")) if part != ""]


def _coerce_scalar(value: str) -> Any:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    low = value.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    return value


def as_list(value: Any) -> list[str]:
    """Normalize a metadata value into a list of non-empty strings."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]


def is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def classify_rule(meta: dict[str, Any]) -> str:
    """Classify a Cursor rule by its frontmatter.

    Returns one of: ``always``, ``glob``, ``agent``, ``manual``.
    Precedence matches Cursor's own activation model.
    """
    if is_truthy(meta.get("alwaysApply")):
        return "always"
    if as_list(meta.get("globs")):
        return "glob"
    if str(meta.get("description", "")).strip():
        return "agent"
    return "manual"
