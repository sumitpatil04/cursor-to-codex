"""Migrate Cursor skills and provide a shared one-file skill writer.

Cursor skills (``.cursor/skills/<name>/SKILL.md`` + support dirs) map directly
to Codex skills under ``.agents/skills/<name>/``. The one-file writer is reused
by the rules and commands converters.
"""

from __future__ import annotations

import re
from pathlib import Path

from utils import frontmatter
from utils.report import ADDED, CHECK

from migrate import MigrationContext

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "skill"


def yaml_quote(value: str) -> str:
    flat = " ".join(value.splitlines()).strip()
    escaped = flat.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_skill_md(name: str, description: str, body: str) -> str:
    body = body.strip()
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {yaml_quote(description)}\n"
        "---\n\n"
        f"{body}\n"
    )


def write_one_file_skill(
    ctx: MigrationContext,
    name: str,
    description: str,
    body: str,
    item_type: str,
    status: str,
    notes: str,
    allow_implicit: bool | None = None,
) -> None:
    slug = slugify(name)
    skill_dir = ctx.scope.skills_dir / slug
    ctx.write_text(skill_dir / "SKILL.md", render_skill_md(slug, description, body))
    if allow_implicit is False:
        ctx.write_text(
            skill_dir / "agents" / "openai.yaml",
            "policy:\n  allow_implicit_invocation: false\n",
        )
    ctx.report.add(ctx.scope.name, status, item_type, name, notes)


def run(ctx: MigrationContext) -> None:
    skills_dir = ctx.scope.cursor_dir / "skills"
    if not skills_dir.is_dir():
        return
    for entry in sorted(skills_dir.iterdir()):
        real = entry.resolve()
        if not real.is_dir():
            continue
        skill_md = real / "SKILL.md"
        if not skill_md.is_file():
            continue
        _migrate_skill_dir(ctx, entry.name, real)


def _migrate_skill_dir(ctx: MigrationContext, name: str, src: Path) -> None:
    slug = slugify(name)
    dst = ctx.scope.skills_dir / slug
    ctx.copy_tree(src, dst)

    meta, _ = frontmatter.split_frontmatter((src / "SKILL.md").read_text(encoding="utf-8"))
    notes = "Copied skill directory (instructions + support files)."
    status = ADDED
    if frontmatter.is_truthy(meta.get("disable-model-invocation")):
        ctx.write_text(
            dst / "agents" / "openai.yaml",
            "policy:\n  allow_implicit_invocation: false\n",
        )
        notes = "Copied; disable-model-invocation mapped to allow_implicit_invocation: false."
        status = CHECK
    ctx.report.add(ctx.scope.name, status, "Skill", name, notes)
