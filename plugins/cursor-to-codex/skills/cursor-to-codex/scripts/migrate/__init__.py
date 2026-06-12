"""Cursor -> Codex conversion modules and the shared migration context."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from utils import paths
from utils.report import Report


@dataclass
class MigrationContext:
    """Holds scope, report, and dry-run aware file IO with change tracking."""

    scope: paths.Scope
    report: Report
    dry_run: bool = False
    planned: list[Path] = field(default_factory=list)
    changed: list[Path] = field(default_factory=list)

    # --- file IO helpers -------------------------------------------------
    def write_text(self, path: Path, content: str) -> bool:
        """Write text unless unchanged. Returns True when content differs."""
        self.planned.append(path)
        if path.is_file():
            try:
                if path.read_text(encoding="utf-8") == content:
                    return False
            except OSError:
                pass
        self.changed.append(path)
        if not self.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return True

    def write_managed(self, path: Path, payload: str) -> bool:
        existing = ""
        if path.is_file():
            try:
                existing = path.read_text(encoding="utf-8")
            except OSError:
                existing = ""
        return self.write_text(path, paths.upsert_managed_region(existing, payload))

    def copy_file(self, src: Path, dst: Path) -> bool:
        """Copy a (possibly binary) file unless byte-identical."""
        self.planned.append(dst)
        try:
            data = src.read_bytes()
        except OSError:
            return False
        if dst.is_file():
            try:
                if dst.read_bytes() == data:
                    return False
            except OSError:
                pass
        self.changed.append(dst)
        if not self.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
        return True

    def copy_tree(self, src_dir: Path, dst_dir: Path, skip_names: set[str] | None = None) -> int:
        """Recursively copy a directory (following symlinks). Returns file count."""
        skip = skip_names or set()
        count = 0
        for src in sorted(src_dir.rglob("*")):
            if src.is_dir():
                continue
            rel = src.relative_to(src_dir)
            if rel.parts and rel.parts[0] in skip:
                continue
            if self.copy_file(src, dst_dir / rel):
                count += 1
            else:
                count += 1  # still counts as migrated even if identical
        return count
