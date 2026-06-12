"""Migration report: per-scope status rows + a written report file.

Mirrors the status contract from OpenAI's migrate-to-codex skill:
Status is one of ``Added``, ``Check before using``, or ``Not Added``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ADDED = "Added"
CHECK = "Check before using"
NOT_ADDED = "Not Added"


@dataclass
class Row:
    scope: str
    status: str
    item_type: str  # singular: Rule, Skill, Command, MCP, Hook, Instructions
    item_name: str
    notes: str


@dataclass
class Report:
    rows: list[Row] = field(default_factory=list)
    manual_fixes: list[str] = field(default_factory=list)

    def add(self, scope: str, status: str, item_type: str, item_name: str, notes: str) -> None:
        self.rows.append(Row(scope, status, item_type, item_name, notes))

    def manual(self, message: str) -> None:
        self.manual_fixes.append(message)

    def scope_rows(self, scope: str) -> list[Row]:
        return [r for r in self.rows if r.scope == scope]

    def render_markdown(self, scopes: list[str]) -> str:
        present = [s for s in scopes if self.scope_rows(s)]
        if not present:
            return "_No migratable Cursor configuration was found._"
        blocks: list[str] = []
        multi = len(present) > 1
        for scope in present:
            lines: list[str] = []
            if multi:
                lines.append(f"**{scope}**\n")
            lines.append("| Status | Item | Notes |")
            lines.append("| --- | --- | --- |")
            for r in self.scope_rows(scope):
                lines.append(f"| `{r.status}` | `{r.item_type}` {r.item_name} | {r.notes} |")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def render_report_text(self, scopes: list[str]) -> str:
        lines = ["cursor-to-codex migration report", "=" * 33, ""]
        lines.append(self.render_markdown(scopes))
        if self.manual_fixes:
            lines.append("")
            lines.append("## MANUAL MIGRATION REQUIRED")
            lines.append("")
            for note in self.manual_fixes:
                lines.append(f"- {note}")
        lines.append("")
        return "\n".join(lines)
