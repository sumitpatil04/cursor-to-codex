"""Migrate Cursor commands (``.cursor/commands/*.md``) into one-file Codex skills.

Codex has no separate "prompts" directory; reusable prompts are skills. Each
command becomes a one-file skill whose description is derived from the first
heading (or the filename), so it can be invoked with ``$<name>``.
"""

from __future__ import annotations

from utils.report import ADDED

from migrate import MigrationContext, skills


def run(ctx: MigrationContext) -> None:
    commands_dir = ctx.scope.cursor_dir / "commands"
    if not commands_dir.is_dir():
        return
    for md in sorted(commands_dir.rglob("*.md")):
        try:
            body = md.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        name = md.stem
        description = _derive_description(body, name)
        skills.write_one_file_skill(
            ctx, name, description, body, "Command", ADDED,
            "Cursor command -> one-file Codex skill (invoke with $name).",
        )


def _derive_description(body: str, name: str) -> str:
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            if heading:
                return heading
        elif line:
            return line[:140]
    return f"Run the {name} command."
