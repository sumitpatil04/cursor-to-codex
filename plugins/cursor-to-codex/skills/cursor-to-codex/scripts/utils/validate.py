"""Validate that migrated Codex artifacts are well-formed.

Used by ``--validate-target`` to confirm a migration produced parseable output.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from . import frontmatter
from .paths import Scope


def validate_scope(scope: Scope) -> list[str]:
    """Return a list of human-readable problems (empty list == all good)."""
    problems: list[str] = []

    if scope.config_toml.is_file():
        try:
            tomllib.loads(scope.config_toml.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError) as exc:
            problems.append(f"{scope.config_toml}: invalid TOML ({exc})")

    if scope.hooks_json.is_file():
        try:
            data = json.loads(scope.hooks_json.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "hooks" not in data:
                problems.append(f"{scope.hooks_json}: missing top-level 'hooks' object")
        except (json.JSONDecodeError, OSError) as exc:
            problems.append(f"{scope.hooks_json}: invalid JSON ({exc})")

    if scope.agents_md.is_file() and not scope.agents_md.read_text(encoding="utf-8").strip():
        problems.append(f"{scope.agents_md}: file is empty")

    if scope.skills_dir.is_dir():
        for skill_md in sorted(scope.skills_dir.glob("*/SKILL.md")):
            problems.extend(_validate_skill(skill_md))

    return problems


def _validate_skill(skill_md: Path) -> list[str]:
    try:
        meta, _ = frontmatter.split_frontmatter(skill_md.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"{skill_md}: unreadable ({exc})"]
    issues = []
    if not str(meta.get("name", "")).strip():
        issues.append(f"{skill_md}: missing 'name' in frontmatter")
    if not str(meta.get("description", "")).strip():
        issues.append(f"{skill_md}: missing 'description' in frontmatter")
    return issues
