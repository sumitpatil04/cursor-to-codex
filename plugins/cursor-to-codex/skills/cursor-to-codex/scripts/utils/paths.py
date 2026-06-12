"""Centralized source/target path resolution for each migration scope.

Codex target locations are intentionally defined in one place so that, if Codex
changes a path (e.g. skills under ``.agents/skills`` vs ``.codex/skills``), only
this module needs updating.

Docs last checked: 2026-06-12
- Skills:        $REPO_ROOT/.agents/skills (repo) / ~/.agents/skills (user)
- Instructions:  AGENTS.md (repo root, nested) / ~/.codex/AGENTS.md (user)
- MCP + config:  .codex/config.toml (repo, trusted) / ~/.codex/config.toml (user)
- Hooks:         .codex/hooks.json (repo) / ~/.codex/hooks.json (user)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MANAGED_BEGIN = "# >>> cursor-to-codex managed (do not edit inside) >>>"
MANAGED_END = "# <<< cursor-to-codex managed <<<"
REPORT_NAME = "cursor-to-codex-report.txt"
HOOKS_SENTINEL = "_cursor_to_codex"


@dataclass(frozen=True)
class Scope:
    """Resolved source + target paths for a single migration scope."""

    name: str
    cursor_dir: Path
    cursorrules: Path
    agents_md: Path
    base_dir: Path
    skills_dir: Path
    codex_dir: Path
    config_toml: Path
    hooks_json: Path
    hooks_dir: Path

    @property
    def report_path(self) -> Path:
        return self.codex_dir / REPORT_NAME

    def has_source(self) -> bool:
        return self.cursor_dir.is_dir() or self.cursorrules.is_file()


def project_scope(root: Path) -> Scope:
    """Project scope rooted at a repository working directory."""
    root = root.resolve()
    return Scope(
        name="project",
        cursor_dir=root / ".cursor",
        cursorrules=root / ".cursorrules",
        agents_md=root / "AGENTS.md",
        base_dir=root,
        skills_dir=root / ".agents" / "skills",
        codex_dir=root / ".codex",
        config_toml=root / ".codex" / "config.toml",
        hooks_json=root / ".codex" / "hooks.json",
        hooks_dir=root / ".codex" / "hooks",
    )


def global_scope(home: Path) -> Scope:
    """Global (user) scope rooted at the user's home directory."""
    home = home.resolve()
    return Scope(
        name="global",
        cursor_dir=home / ".cursor",
        cursorrules=home / ".cursorrules",
        agents_md=home / ".codex" / "AGENTS.md",
        base_dir=home / ".codex",
        skills_dir=home / ".agents" / "skills",
        codex_dir=home / ".codex",
        config_toml=home / ".codex" / "config.toml",
        hooks_json=home / ".codex" / "hooks.json",
        hooks_dir=home / ".codex" / "hooks",
    )


def upsert_managed_region(existing: str, payload: str) -> str:
    """Insert or replace the cursor-to-codex managed region in a text file.

    Content outside the managed markers (including user comments) is preserved
    verbatim, making repeated runs idempotent.
    """
    block = f"{MANAGED_BEGIN}\n{payload.rstrip(chr(10))}\n{MANAGED_END}\n"
    begin = existing.find(MANAGED_BEGIN)
    end = existing.find(MANAGED_END)
    if begin != -1 and end != -1 and end > begin:
        end_full = end + len(MANAGED_END)
        # Swallow a single trailing newline after the end marker.
        if end_full < len(existing) and existing[end_full] == "\n":
            end_full += 1
        return existing[:begin] + block + existing[end_full:]
    if existing and not existing.endswith("\n"):
        existing += "\n"
    if existing:
        existing += "\n"
    return existing + block


def outside_managed(text: str) -> str:
    """Return file text with the cursor-to-codex managed region removed."""
    begin = text.find(MANAGED_BEGIN)
    end = text.find(MANAGED_END)
    if begin != -1 and end != -1 and end > begin:
        return text[:begin] + text[end + len(MANAGED_END):]
    return text


def custom_scope(source: Path, target: Path) -> Scope:
    """Advanced scope from explicit --source (.cursor) and --target (.codex).

    AGENTS.md and .agents/skills are placed relative to the target's parent so
    that ``--target ./.codex`` yields ``./AGENTS.md`` and ``./.agents/skills``.
    """
    source = source.resolve()
    target = target.resolve()
    base = target.parent
    return Scope(
        name="custom",
        cursor_dir=source,
        cursorrules=base / ".cursorrules",
        agents_md=base / "AGENTS.md",
        base_dir=base,
        skills_dir=base / ".agents" / "skills",
        codex_dir=target,
        config_toml=target / "config.toml",
        hooks_json=target / "hooks.json",
        hooks_dir=target / "hooks",
    )
