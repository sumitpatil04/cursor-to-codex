"""Collect and classify Cursor rules (``.cursor/rules/*.mdc``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from utils import frontmatter

from migrate import MigrationContext


@dataclass
class Rule:
    name: str
    path: Path
    meta: dict[str, Any]
    body: str
    kind: str  # always | glob | agent | manual


@dataclass
class RuleSet:
    always: list[Rule] = field(default_factory=list)
    glob: list[Rule] = field(default_factory=list)
    agent: list[Rule] = field(default_factory=list)
    manual: list[Rule] = field(default_factory=list)

    def all(self) -> list[Rule]:
        return self.always + self.glob + self.agent + self.manual


def collect(ctx: MigrationContext) -> RuleSet:
    rules_dir = ctx.scope.cursor_dir / "rules"
    rs = RuleSet()
    if not rules_dir.is_dir():
        return rs
    for mdc in sorted(rules_dir.rglob("*.mdc")):
        try:
            text = mdc.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = frontmatter.split_frontmatter(text)
        kind = frontmatter.classify_rule(meta)
        rule = Rule(name=mdc.stem, path=mdc, meta=meta, body=body.strip(), kind=kind)
        getattr(rs, kind).append(rule)
    return rs


def write_skill_rules(ctx: MigrationContext, rs: RuleSet) -> None:
    """Agent-requested and manual rules become Codex skills (description-driven)."""
    from migrate import skills

    for rule in rs.agent:
        description = str(rule.meta.get("description", "")).strip() or f"Apply the {rule.name} rule."
        skills.write_one_file_skill(
            ctx, rule.name, description, rule.body, "Rule", "Check before using",
            "agent-requested rule -> Codex skill (description drives invocation).",
        )
    for rule in rs.manual:
        description = f"Apply the {rule.name} rule (manual, @-referenced in Cursor)."
        skills.write_one_file_skill(
            ctx, rule.name, description, rule.body, "Rule", "Check before using",
            "manual rule -> Codex skill; invoke explicitly with $skill.",
        )


def dir_prefix(glob: str) -> str | None:
    """Return a clean directory prefix for a glob, or None if not directory-scoped."""
    leading: list[str] = []
    for seg in glob.strip().split("/"):
        if seg in ("", "."):
            continue
        if any(c in seg for c in "*?[]{}"):
            break
        leading.append(seg)
    return "/".join(leading) if leading else None
