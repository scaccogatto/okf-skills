#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Behaviour tests for hooks/okf-stop-check.sh, run against throwaway git repos.

Run:  uv run tests/test_okf_stop_hook.py
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "okf-stop-check.sh"
INACTIVE = '{"stop_hook_active": false}'


def sh(cwd: Path, *cmd: str) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


class TestStopHook(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        sh(self.repo, "git", "init", "-q")
        sh(self.repo, "git", "config", "user.email", "test@example.com")
        sh(self.repo, "git", "config", "user.name", "test")
        (self.repo / ".okf").mkdir()
        (self.repo / ".okf/index.md").write_text("---\nupkeep: enforced\n---\n# Bundle\n")
        (self.repo / ".okf/log.md").write_text("# Update Log\n")
        (self.repo / ".okf/a.md").write_text("---\ntype: Thing\n---\nA\n")
        (self.repo / "code.py").write_text("x = 1\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "init")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_hook(self, payload: str = INACTIVE, **env: str) -> bool:
        """True when the hook blocks."""
        base = {k: v for k, v in os.environ.items() if k != "OKF_HOOK"}
        r = subprocess.run(["bash", str(HOOK)], cwd=self.repo, input=payload,
                           capture_output=True, text=True, env={**base, **env}, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        return '"decision":"block"' in r.stdout

    def edit_code(self) -> None:
        (self.repo / "code.py").write_text("x = 2\n")

    def test_clean_tree_passes(self) -> None:
        self.assertFalse(self.run_hook())

    def test_code_change_without_bundle_change_blocks(self) -> None:
        self.edit_code()
        self.assertTrue(self.run_hook())

    def test_concept_edit_satisfies_without_log(self) -> None:
        self.edit_code()
        (self.repo / ".okf/a.md").write_text("---\ntype: Thing\n---\nB\n")
        self.assertFalse(self.run_hook())

    def test_new_untracked_concept_satisfies(self) -> None:
        self.edit_code()
        (self.repo / ".okf/new.md").write_text("---\ntype: Thing\n---\nN\n")
        self.assertFalse(self.run_hook())

    def test_log_edit_still_satisfies(self) -> None:
        self.edit_code()
        (self.repo / ".okf/log.md").write_text("# Update Log\n\n## 2026-09-28\n* x\n")
        self.assertFalse(self.run_hook())

    def test_untracked_code_alone_passes(self) -> None:
        (self.repo / "scratch.py").write_text("y = 1\n")
        self.assertFalse(self.run_hook())

    def commit_claude_dir(self) -> None:
        claude = self.repo / ".claude"
        (claude / "hooks").mkdir(parents=True)
        (claude / "skills").mkdir()
        (claude / "settings.json").write_text("{}\n")
        (claude / "settings.local.json").write_text("{}\n")
        (claude / "hooks/h.sh").write_text("#!/bin/sh\n")
        (claude / "skills/s.md").write_text("# s\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "claude dir")

    def test_claude_settings_change_alone_passes(self) -> None:
        # #58: /plugin writes .claude/settings.json, which no concept documents
        self.commit_claude_dir()
        for name in ("settings.json", "settings.local.json"):
            with self.subTest(name=name):
                (self.repo / ".claude" / name).write_text('{"enabledPlugins": {}}\n')
                self.assertFalse(self.run_hook())
                sh(self.repo, "git", "checkout", "--", ".claude")

    def test_claude_settings_change_does_not_hide_a_code_change(self) -> None:
        self.commit_claude_dir()
        (self.repo / ".claude/settings.json").write_text('{"enabledPlugins": {}}\n')
        self.edit_code()
        self.assertTrue(self.run_hook())

    def test_other_claude_paths_still_block(self) -> None:
        self.commit_claude_dir()
        for rel in ("hooks/h.sh", "skills/s.md"):
            with self.subTest(rel=rel):
                (self.repo / ".claude" / rel).write_text("changed\n")
                self.assertTrue(self.run_hook())
                sh(self.repo, "git", "checkout", "--", ".claude")

    def test_nested_settings_json_still_blocks(self) -> None:
        # only the two root settings files are exempt, not any settings.json
        (self.repo / "app").mkdir()
        (self.repo / "app/settings.json").write_text("{}\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "app settings")
        (self.repo / "app/settings.json").write_text('{"a": 1}\n')
        self.assertTrue(self.run_hook())

    def test_loop_guard_passes(self) -> None:
        self.edit_code()
        self.assertFalse(self.run_hook('{"stop_hook_active": true}'))

    def test_opt_out_passes(self) -> None:
        self.edit_code()
        self.assertFalse(self.run_hook(OKF_HOOK="off"))

    def test_bundle_without_flag_passes(self) -> None:
        (self.repo / ".okf/index.md").write_text("# Bundle\n\nupkeep: enforced\n")
        sh(self.repo, "git", "commit", "-qam", "flag outside frontmatter")
        self.edit_code()
        self.assertFalse(self.run_hook())

    def test_block_reason_does_not_demand_a_log_entry(self) -> None:
        self.edit_code()
        r = subprocess.run(["bash", str(HOOK)], cwd=self.repo, input=INACTIVE,
                           capture_output=True, text=True, check=False)
        self.assertIn("nothing under .okf/ changed", r.stdout)
        self.assertIn("only for a lifecycle event", r.stdout)

    def set_upkeep_repos(self, value: str) -> None:
        """Declare upkeep_repos in the root index and commit it with a gitignored repos/."""
        (self.repo / ".okf/index.md").write_text(
            f"---\nupkeep: enforced\nupkeep_repos: {value}\n---\n# Bundle\n")
        (self.repo / ".gitignore").write_text("repos/\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "declare nested repos")

    def add_nested(self, rel: str) -> Path:
        nested = self.repo / rel
        nested.mkdir(parents=True)
        sh(nested, "git", "init", "-q")
        sh(nested, "git", "config", "user.email", "test@example.com")
        sh(nested, "git", "config", "user.name", "test")
        (nested / "lib.py").write_text("x = 1\n")
        sh(nested, "git", "add", "-A")
        sh(nested, "git", "commit", "-qm", "init")
        return nested

    def hook_output(self) -> str:
        r = subprocess.run(["bash", str(HOOK)], cwd=self.repo, input=INACTIVE,
                           capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_nested_repo_change_blocks(self) -> None:
        self.set_upkeep_repos("repos/*")
        nested = self.add_nested("repos/fe")
        self.assertFalse(self.run_hook())
        (nested / "lib.py").write_text("x = 2\n")
        self.assertTrue(self.run_hook())

    def test_nested_change_with_bundle_change_passes(self) -> None:
        self.set_upkeep_repos("repos/*")
        (self.add_nested("repos/fe") / "lib.py").write_text("x = 2\n")
        (self.repo / ".okf/a.md").write_text("---\ntype: Thing\n---\nB\n")
        self.assertFalse(self.run_hook())

    def test_nested_repo_not_listed_is_ignored(self) -> None:
        self.set_upkeep_repos("vendor/*")
        (self.add_nested("repos/fe") / "lib.py").write_text("x = 2\n")
        self.assertFalse(self.run_hook())

    def test_flow_list_form(self) -> None:
        self.set_upkeep_repos("[vendor/lib, repos/*]")
        (self.add_nested("repos/fe") / "lib.py").write_text("x = 2\n")
        self.assertTrue(self.run_hook())

    def test_quoted_items(self) -> None:
        self.set_upkeep_repos("['vendor/lib', \"repos/*\"]")
        (self.add_nested("repos/fe") / "lib.py").write_text("x = 2\n")
        self.assertTrue(self.run_hook())

    def test_missing_glob_target_is_ignored(self) -> None:
        self.set_upkeep_repos("[repos/*, vendor/lib]")
        self.assertFalse(self.run_hook())

    def test_plain_directory_is_not_a_nested_repo(self) -> None:
        self.set_upkeep_repos("[repos/*, app]")
        (self.repo / "app").mkdir()
        (self.repo / "app/m.py").write_text("x = 1\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "app")
        self.assertFalse(self.run_hook())

    def test_untracked_file_in_nested_repo_passes(self) -> None:
        self.set_upkeep_repos("repos/*")
        (self.add_nested("repos/fe") / "scratch.py").write_text("y = 1\n")
        self.assertFalse(self.run_hook())

    def test_block_reason_names_the_nested_repos(self) -> None:
        self.set_upkeep_repos("repos/*")
        (self.add_nested("repos/fe") / "lib.py").write_text("x = 2\n")
        (self.add_nested("repos/be") / "lib.py").write_text("x = 2\n")
        self.add_nested("repos/clean")
        out = self.hook_output()
        self.assertIn("nested repos: repos/be, repos/fe", out)
        self.assertNotIn("repos/clean", out)
        self.assertEqual(out.count("\n"), 1)

    def test_block_reason_without_nested_repos_is_unchanged(self) -> None:
        self.edit_code()
        self.assertNotIn("nested", self.hook_output())


if __name__ == "__main__":
    unittest.main()
