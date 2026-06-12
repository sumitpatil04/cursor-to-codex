"""Tests for the cursor-to-codex migrator (stdlib unittest; pytest-compatible)."""

from __future__ import annotations

import json
import sys
import tomllib
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / (
    "plugins/cursor-to-codex/skills/cursor-to-codex/scripts"
)
sys.path.insert(0, str(SCRIPTS))

import cli  # noqa: E402
from migrate import MigrationContext, hooks, mcp  # noqa: E402
from migrate.rules import dir_prefix  # noqa: E402
from utils import frontmatter, paths  # noqa: E402
from utils.report import Report  # noqa: E402
from utils.toml_writer import render_mcp_server  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project_ctx(root: Path, dry_run: bool = False) -> MigrationContext:
    return MigrationContext(paths.project_scope(root), Report(), dry_run=dry_run)


class FrontmatterClassification(unittest.TestCase):
    def test_classify(self) -> None:
        self.assertEqual(frontmatter.classify_rule({"alwaysApply": True}), "always")
        self.assertEqual(frontmatter.classify_rule({"globs": "src/**"}), "glob")
        self.assertEqual(frontmatter.classify_rule({"description": "x"}), "agent")
        self.assertEqual(frontmatter.classify_rule({}), "manual")

    def test_globs_list_forms(self) -> None:
        meta, _ = frontmatter.split_frontmatter('---\nglobs: a.ts, b.ts\n---\nbody\n')
        self.assertEqual(frontmatter.as_list(meta["globs"]), ["a.ts", "b.ts"])
        meta2, _ = frontmatter.split_frontmatter('---\nglobs:\n  - a.ts\n  - b.ts\n---\n')
        self.assertEqual(frontmatter.as_list(meta2["globs"]), ["a.ts", "b.ts"])

    def test_dir_prefix(self) -> None:
        self.assertEqual(dir_prefix("src/**/*.ts"), "src")
        self.assertEqual(dir_prefix("src/api/**"), "src/api")
        self.assertIsNone(dir_prefix("*.ts"))
        self.assertIsNone(dir_prefix("**/*.ts"))


class TomlWriter(unittest.TestCase):
    def test_render_roundtrips(self) -> None:
        block = render_mcp_server("fs", {
            "command": "npx", "args": ["-y", "s"],
            "env": {"A": "1"}, "env_vars": ["TOK"],
        })
        parsed = tomllib.loads(block)
        self.assertEqual(parsed["mcp_servers"]["fs"]["command"], "npx")
        self.assertEqual(parsed["mcp_servers"]["fs"]["env_vars"], ["TOK"])
        self.assertEqual(parsed["mcp_servers"]["fs"]["env"]["A"], "1")


class McpConversion(unittest.TestCase):
    def test_stdio_http_sse(self) -> None:
        root = Path(self.tmp.name)
        _write(root / ".cursor" / "mcp.json", json.dumps({"mcpServers": {
            "fs": {"command": "npx", "args": ["-y", "s"],
                   "env": {"TOK": "${TOK}", "LIT": "x"}, "timeout": 4500},
            "remote": {"type": "http", "url": "https://x/mcp",
                       "headers": {"Authorization": "Bearer ${KEY}", "H": "${R}", "S": "v"}},
            "old": {"type": "sse", "url": "https://x/sse"},
        }}))
        ctx = _project_ctx(root)
        mcp.run(ctx)
        cfg = tomllib.loads(ctx.scope.config_toml.read_text())
        servers = cfg["mcp_servers"]
        self.assertEqual(servers["fs"]["env_vars"], ["TOK"])
        self.assertEqual(servers["fs"]["env"], {"LIT": "x"})
        self.assertEqual(servers["fs"]["startup_timeout_sec"], 5)
        self.assertEqual(servers["remote"]["bearer_token_env_var"], "KEY")
        self.assertEqual(servers["remote"]["env_http_headers"], {"H": "R"})
        self.assertEqual(servers["remote"]["http_headers"], {"S": "v"})
        self.assertNotIn("old", servers)
        statuses = {r.item_name: r.status for r in ctx.report.rows}
        self.assertEqual(statuses["old"], "Not Added")

    def test_preserves_unrelated_config(self) -> None:
        root = Path(self.tmp.name)
        _write(root / ".codex" / "config.toml", "notify = [\"x\"]\n[projects.a]\ntrust = true\n")
        _write(root / ".cursor" / "mcp.json",
               json.dumps({"mcpServers": {"fs": {"command": "npx"}}}))
        ctx = _project_ctx(root)
        mcp.run(ctx)
        cfg = tomllib.loads(ctx.scope.config_toml.read_text())
        self.assertEqual(cfg["notify"], ["x"])
        self.assertTrue(cfg["projects"]["a"]["trust"])
        self.assertIn("fs", cfg["mcp_servers"])

    def setUp(self) -> None:
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tmp.cleanup()


class HooksConversion(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_event_mapping(self) -> None:
        root = Path(self.tmp.name)
        _write(root / ".cursor" / "hooks.json", json.dumps({"version": 1, "hooks": {
            "afterShellExecution": [{"command": ".cursor/hooks/t.sh", "matcher": "x", "timeout": 5}],
            "beforeReadFile": [{"command": ".cursor/hooks/t.sh"}],
        }}))
        _write(root / ".cursor" / "hooks" / "t.sh", "echo hi\n")
        ctx = _project_ctx(root)
        hooks.run(ctx)
        data = json.loads(ctx.scope.hooks_json.read_text())
        self.assertTrue(data["_cursor_to_codex"])
        self.assertIn("PostToolUse", data["hooks"])
        self.assertEqual(data["hooks"]["PostToolUse"][0]["matcher"], "Bash")
        self.assertEqual(
            data["hooks"]["PostToolUse"][0]["hooks"][0]["command"], ".codex/hooks/t.sh")
        self.assertTrue((ctx.scope.hooks_dir / "t.sh").is_file())
        statuses = {r.item_name: r.status for r in ctx.report.rows}
        self.assertEqual(statuses["beforeReadFile"], "Not Added")

    def test_existing_user_hooks_not_clobbered(self) -> None:
        root = Path(self.tmp.name)
        _write(root / ".codex" / "hooks.json", json.dumps({"hooks": {"Stop": []}}))
        _write(root / ".cursor" / "hooks.json", json.dumps({"version": 1, "hooks": {
            "stop": [{"command": "echo done"}]}}))
        ctx = _project_ctx(root)
        hooks.run(ctx)
        # User file preserved; ours written alongside.
        self.assertEqual(json.loads(ctx.scope.hooks_json.read_text())["hooks"], {"Stop": []})
        alt = ctx.scope.hooks_json.with_name("hooks.cursor-to-codex.json")
        self.assertTrue(alt.is_file())


class EndToEnd(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _write(self.root / ".cursorrules", "legacy\n")
        _write(self.root / ".cursor" / "rules" / "a.mdc",
               "---\nalwaysApply: true\n---\nAlways body.\n")
        _write(self.root / ".cursor" / "rules" / "g.mdc",
               "---\nglobs: src/**/*.ts\n---\nGlob body.\n")
        _write(self.root / ".cursor" / "commands" / "review.md", "# Review\nDo it.\n")
        _write(self.root / ".cursor" / "mcp.json",
               json.dumps({"mcpServers": {"fs": {"command": "npx"}}}))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_command_becomes_skill(self) -> None:
        cli.main(["--scope", "project", "--root", str(self.root)])
        skill = self.root / ".agents" / "skills" / "review" / "SKILL.md"
        self.assertTrue(skill.is_file())
        meta, _ = frontmatter.split_frontmatter(skill.read_text())
        self.assertEqual(meta["name"], "review")
        self.assertEqual(meta["description"], "Review")

    def test_nested_agents_md(self) -> None:
        cli.main(["--scope", "project", "--root", str(self.root)])
        self.assertTrue((self.root / "src" / "AGENTS.md").is_file())
        self.assertIn("Always body.", (self.root / "AGENTS.md").read_text())

    def test_validate_target_passes(self) -> None:
        rc = cli.main(["--scope", "project", "--root", str(self.root), "--validate-target"])
        self.assertEqual(rc, 0)

    def test_idempotent_rerun(self) -> None:
        cli.main(["--scope", "project", "--root", str(self.root)])
        files = sorted(p for p in self.root.rglob("*") if p.is_file() and ".cursor" not in p.parts)
        before = {p: p.read_bytes() for p in files}
        cli.main(["--scope", "project", "--root", str(self.root)])
        after = {p: p.read_bytes() for p in files}
        self.assertEqual(before, after)

    def test_dry_run_writes_nothing(self) -> None:
        cli.main(["--scope", "project", "--root", str(self.root), "--dry-run"])
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertFalse((self.root / ".codex").exists())
        self.assertFalse((self.root / ".agents").exists())


if __name__ == "__main__":
    unittest.main()
