"""cursor-to-codex CLI: orchestrate Cursor -> Codex migration.

Pure stdlib, Python >= 3.11. One-time migration per repository; writes are
idempotent (managed-region markers + content comparison) so the in-session
``scan -> dry-run -> write -> fix -> re-run -> validate`` loop is safe.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from migrate import MigrationContext, commands, hooks, instructions, mcp, rules, skills
from utils import paths
from utils.report import Report
from utils.validate import validate_scope


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cursor-to-codex",
        description="Migrate Cursor configuration into Codex artifacts.",
    )
    p.add_argument("--source", help="Path to a .cursor directory (advanced; pair with --target).")
    p.add_argument("--target", help="Path to a .codex directory (advanced; pair with --source).")
    p.add_argument("--scope", choices=["project", "global", "both"], default="both",
                   help="Which scope(s) to migrate when --source/--target are not given (default: both).")
    p.add_argument("--root", default=".", help="Project root for project scope (default: current dir).")
    p.add_argument("--scan-only", action="store_true", help="List migratable Cursor sources; write nothing.")
    p.add_argument("--dry-run", action="store_true", help="Show what would change; write nothing.")
    p.add_argument("--validate-target", action="store_true",
                   help="Validate migrated Codex artifacts after running.")
    return p


def resolve_scopes(args: argparse.Namespace) -> list[paths.Scope]:
    if args.source or args.target:
        if not (args.source and args.target):
            raise SystemExit("error: --source and --target must be provided together.")
        return [paths.custom_scope(Path(args.source), Path(args.target))]
    chosen: list[paths.Scope] = []
    if args.scope in ("project", "both"):
        chosen.append(paths.project_scope(Path(args.root)))
    if args.scope in ("global", "both"):
        chosen.append(paths.global_scope(Path.home()))
    return [s for s in chosen if s.has_source()]


def migrate_scope(ctx: MigrationContext) -> None:
    rs = rules.collect(ctx)
    instructions.run(ctx, rs)
    rules.write_skill_rules(ctx, rs)
    skills.run(ctx)
    commands.run(ctx)
    mcp.run(ctx)
    hooks.run(ctx)


def scan(scope: paths.Scope) -> None:
    ctx = MigrationContext(scope, Report(), dry_run=True)
    rs = rules.collect(ctx)
    cd = scope.cursor_dir
    print(f"\n[{scope.name}] source: {cd}")
    print(f"  .cursorrules:      {'yes' if scope.cursorrules.is_file() else 'no'}")
    print(f"  rules (always):    {len(rs.always)}")
    print(f"  rules (glob):      {len(rs.glob)}")
    print(f"  rules (agent):     {len(rs.agent)}")
    print(f"  rules (manual):    {len(rs.manual)}")
    print(f"  skills:            {_count_dirs(cd / 'skills', 'SKILL.md')}")
    print(f"  commands:          {_count_files(cd / 'commands', '*.md')}")
    print(f"  mcp.json:          {'yes' if (cd / 'mcp.json').is_file() else 'no'}")
    print(f"  hooks.json:        {'yes' if (cd / 'hooks.json').is_file() else 'no'}")


def _count_files(directory: Path, pattern: str) -> int:
    return len(list(directory.rglob(pattern))) if directory.is_dir() else 0


def _count_dirs(directory: Path, marker: str) -> int:
    return len(list(directory.glob(f"*/{marker}"))) if directory.is_dir() else 0


def print_summary(report: Report, scopes: list[paths.Scope], args: argparse.Namespace) -> None:
    names = [s.name for s in scopes]
    mode = "DRY RUN (no files written)" if args.dry_run else "MIGRATION COMPLETE"
    print(f"\n=== cursor-to-codex: {mode} ===\n")
    print(report.render_markdown(names))
    if report.manual_fixes:
        print("\n## MANUAL MIGRATION REQUIRED")
        for note in report.manual_fixes:
            print(f"- {note}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scopes = resolve_scopes(args)
    if not scopes:
        print("No Cursor configuration found for the selected scope(s). Nothing to do.")
        return 0

    if args.scan_only:
        for scope in scopes:
            scan(scope)
        return 0

    report = Report()
    for scope in scopes:
        ctx = MigrationContext(scope, report, dry_run=args.dry_run)
        migrate_scope(ctx)
        if not args.dry_run and report.scope_rows(scope.name):
            ctx.write_text(scope.report_path, report.render_report_text([scope.name]))

    print_summary(report, scopes, args)

    if args.validate_target:
        problems: list[str] = []
        for scope in scopes:
            problems.extend(validate_scope(scope))
        print("\n=== validate-target ===")
        if problems:
            for prob in problems:
                print(f"  PROBLEM: {prob}")
            return 1
        print("  OK: migrated artifacts are well-formed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
