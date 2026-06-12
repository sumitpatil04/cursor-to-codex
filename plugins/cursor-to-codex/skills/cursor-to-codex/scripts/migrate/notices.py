"""Report-only notices for Cursor surfaces Codex cannot consume.

Some Cursor configuration has no Codex equivalent and must not be silently
dropped or fabricated into an unsupported target:

- ``.cursorignore`` / ``.cursorindexingignore`` -- Codex has no ``.codexignore``
  (https://github.com/openai/codex/issues/1397); context is restricted via
  ``.gitignore`` + the sandbox / ``shell_environment_policy``.
- ``.cursor/environment.json`` -- Cursor background/cloud-agent setup; Codex
  cloud uses its own environment configuration.

This module writes NO Codex files. It only adds ``Not Added`` report rows and
``MANUAL MIGRATION REQUIRED`` notes, which keeps it trivially idempotent.
"""

from __future__ import annotations

from utils.report import NOT_ADDED

from migrate import MigrationContext

_IGNORE_NOTE = (
    "Codex has no `.codexignore`; restrict agent context via `.gitignore` plus "
    "the sandbox / `shell_environment_policy`. Review the patterns in {name} and "
    "apply the relevant ones manually."
)
_ENVIRONMENT_NOTE = (
    "Codex cloud uses its own environment setup; re-create the install/terminal "
    "steps from .cursor/environment.json in your Codex cloud config or document "
    "them in AGENTS.md."
)


def run(ctx: MigrationContext) -> None:
    scope = ctx.scope
    for path in (scope.cursorignore, scope.cursorindexingignore):
        if path.is_file():
            ctx.report.add(
                scope.name, NOT_ADDED, "Settings", path.name,
                "No Codex equivalent; restrict context via .gitignore + sandbox.",
            )
            ctx.report.manual(_IGNORE_NOTE.format(name=path.name))

    if scope.environment_json.is_file():
        ctx.report.add(
            scope.name, NOT_ADDED, "Settings", ".cursor/environment.json",
            "Cursor cloud-agent setup; Codex cloud uses its own environment config.",
        )
        ctx.report.manual(_ENVIRONMENT_NOTE)
