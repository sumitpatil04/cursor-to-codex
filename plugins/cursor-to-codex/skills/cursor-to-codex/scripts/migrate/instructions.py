"""Migrate instruction-style sources into AGENTS.md (root + nested).

Sources: ``.cursorrules`` (legacy), always-apply rules, and glob rules. Root
``AGENTS.md`` is shared by Cursor and Codex, so we only ever append/replace a
managed region and never overwrite user content.
"""

from __future__ import annotations

from utils import frontmatter
from utils.report import ADDED, CHECK

from migrate import MigrationContext
from migrate.rules import RuleSet, dir_prefix


def run(ctx: MigrationContext, rs: RuleSet) -> None:
    root_sections: list[str] = []
    nested: dict[str, list[str]] = {}

    cursorrules = ctx.scope.cursorrules
    if cursorrules.is_file():
        try:
            content = cursorrules.read_text(encoding="utf-8").strip()
        except OSError:
            content = ""
        if content:
            root_sections.append(f"## Project rules (from .cursorrules)\n\n{content}")
            ctx.report.add(ctx.scope.name, ADDED, "Instructions", ".cursorrules",
                           "Appended to root AGENTS.md managed block.")

    for rule in rs.always:
        root_sections.append(f"## Rule: {rule.name}\n\n{rule.body}")
        ctx.report.add(ctx.scope.name, ADDED, "Rule", rule.name,
                       "alwaysApply -> root AGENTS.md.")

    for rule in rs.glob:
        globs = frontmatter.as_list(rule.meta.get("globs"))
        dirs = [dir_prefix(g) for g in globs]
        if dirs and all(d for d in dirs):
            for d in sorted(set(d for d in dirs if d)):
                nested.setdefault(d, []).append(f"## Rule: {rule.name}\n\n{rule.body}")
            ctx.report.add(ctx.scope.name, CHECK, "Rule", rule.name,
                           f"globs -> nested AGENTS.md in: {', '.join(sorted(set(d for d in dirs if d)))}. "
                           "Codex scopes by directory, not arbitrary globs.")
        else:
            preamble = f"_Applies to files matching: {', '.join(globs)}_" if globs else ""
            section = f"## Rule: {rule.name}\n\n{preamble}\n\n{rule.body}".strip()
            root_sections.append(section)
            ctx.report.add(ctx.scope.name, CHECK, "Rule", rule.name,
                           "glob not directory-scoped -> inlined into root AGENTS.md. Review scope.")

    if root_sections:
        ctx.write_managed(ctx.scope.agents_md, "\n\n".join(root_sections))
        ctx.report.add(ctx.scope.name, ADDED, "Instructions", "AGENTS.md",
                       "Managed block written; AGENTS.md is shared with Cursor and "
                       "content outside the block is preserved.")

    for d, sections in nested.items():
        target = ctx.scope.base_dir / d / "AGENTS.md"
        ctx.write_managed(target, "\n\n".join(sections))
