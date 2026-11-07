#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Behaviour tests for hooks/okf-stop-check.sh, run against throwaway git repos.

Run:  uv run tests/test_okf_stop_hook.py
"""
from __future__ import annotations

import json
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

    def set_recursive(self, value: str | None = "true") -> None:
        """Declare recursive in the root index and commit it with gitignored repos/."""
        flag = f"recursive: {value}\n" if value is not None else ""
        (self.repo / ".okf/index.md").write_text(f"---\nupkeep: enforced\n{flag}---\n# Bundle\n")
        (self.repo / ".gitignore").write_text("repos/\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "declare recursive")

    @staticmethod
    def init_repo(path: Path) -> Path:
        path.mkdir(parents=True)
        sh(path, "git", "init", "-q")
        sh(path, "git", "config", "user.email", "test@example.com")
        sh(path, "git", "config", "user.name", "test")
        (path / "lib.py").write_text("x = 1\n")
        sh(path, "git", "add", "-A")
        sh(path, "git", "commit", "-qm", "init")
        return path

    def add_nested(self, rel: str) -> Path:
        return self.init_repo(self.repo / rel)

    def dirty(self, nested: Path) -> Path:
        (nested / "lib.py").write_text("x = 2\n")
        return nested

    def hook_output(self, **env: str) -> str:
        base = {k: v for k, v in os.environ.items() if k != "OKF_HOOK"}
        r = subprocess.run(["bash", str(HOOK)], cwd=self.repo, input=INACTIVE,
                           capture_output=True, text=True, env={**base, **env}, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_recursive_absent_ignores_nested(self) -> None:
        self.set_recursive(None)
        self.dirty(self.add_nested("repos/app"))
        self.assertFalse(self.run_hook())

    def test_recursive_blocks_on_nested_change(self) -> None:
        self.set_recursive()
        nested = self.add_nested("repos/app")
        self.assertFalse(self.run_hook())
        self.dirty(nested)
        out = self.hook_output()
        self.assertIn('"decision":"block"', out)
        self.assertIn("nested repos: repos/app)", out)
        self.assertEqual(out.count("\n"), 1)

    def test_recursive_nested_with_bundle_change_passes(self) -> None:
        self.set_recursive()
        self.dirty(self.add_nested("repos/app"))
        (self.repo / ".okf/b.md").write_text("---\ntype: Thing\n---\nB\n")
        self.assertFalse(self.run_hook())

    def test_nested_inside_nested_blocks(self) -> None:
        self.set_recursive()
        app = self.add_nested("repos/app")
        (app / ".gitignore").write_text("inner/\n")
        sh(app, "git", "add", "-A")
        sh(app, "git", "commit", "-qm", "ignore inner")
        self.dirty(self.init_repo(app / "inner"))
        self.assertIn("repos/app/inner", self.hook_output())

    def test_outer_change_has_no_nested_part(self) -> None:
        self.set_recursive()
        self.dirty(self.add_nested("repos/app"))
        self.edit_code()
        out = self.hook_output()
        self.assertIn('"decision":"block"', out)
        self.assertNotIn("nested", out)

    def test_outer_worktree_is_not_counted(self) -> None:
        self.set_recursive()
        wt = self.repo / ".claude/worktrees/wt"
        sh(self.repo, "git", "worktree", "add", "-q", str(wt), "-b", "wt")
        (wt / "code.py").write_text("x = 3\n")
        self.assertFalse(self.run_hook())

    def test_worktree_of_nested_repo_is_not_counted(self) -> None:
        self.set_recursive()
        app = self.add_nested("repos/app")
        wt = self.repo / "repos/app-wt"
        sh(app, "git", "worktree", "add", "-q", str(wt), "-b", "wt")
        (wt / "lib.py").write_text("x = 3\n")
        self.assertFalse(self.run_hook())
        self.dirty(app)
        out = self.hook_output()
        self.assertIn("nested repos: repos/app)", out)
        self.assertNotIn("app-wt", out)

    def test_worktree_of_external_repo_is_counted(self) -> None:
        self.set_recursive()
        with tempfile.TemporaryDirectory() as ext_dir:
            ext = self.init_repo(Path(ext_dir) / "src")
            wt = self.repo / "repos/ext-wt"
            sh(ext, "git", "worktree", "add", "-q", str(wt), "-b", "wt")
            self.assertFalse(self.run_hook())
            (wt / "lib.py").write_text("x = 3\n")
            self.assertIn("repos/ext-wt", self.hook_output())

    def test_node_modules_is_pruned(self) -> None:
        self.set_recursive()
        self.dirty(self.add_nested("node_modules/pkg"))
        self.assertFalse(self.run_hook())

    def test_path_with_space(self) -> None:
        self.set_recursive()
        self.dirty(self.add_nested("repos/with space"))
        out = self.hook_output()
        self.assertIn("nested repos: repos/with space)", json.loads(out)["reason"])

    @unittest.skipIf(os.name == "nt", "Windows cannot create such names")
    def test_path_with_double_quote_is_escaped(self) -> None:
        self.set_recursive()
        self.dirty(self.add_nested('repos/q"uote'))
        self.assertIn('repos/q"uote', json.loads(self.hook_output())["reason"])

    @unittest.skipIf(os.name == "nt", "Windows cannot create such names")
    def test_path_with_backslash_is_escaped(self) -> None:
        self.set_recursive()
        self.dirty(self.add_nested("repos/back" + chr(92) + "slash"))
        self.assertIn("repos/back" + chr(92) + "slash", json.loads(self.hook_output())["reason"])

    def test_nested_repo_with_own_bundle_is_excluded(self) -> None:
        self.set_recursive()
        app = self.add_nested("repos/app")
        (app / ".okf").mkdir()
        (app / ".okf/a.md").write_text("---\ntype: Thing\n---\nA\n")
        sh(app, "git", "add", "-A")
        sh(app, "git", "commit", "-qm", "bundle")
        self.dirty(app)
        self.assertFalse(self.run_hook())

    def add_inner(self) -> None:
        """repos/app (clean, ignores inner/) with a dirty repos/app/inner."""
        app = self.add_nested("repos/app")
        (app / ".gitignore").write_text("inner/\n")
        sh(app, "git", "add", "-A")
        sh(app, "git", "commit", "-qm", "ignore inner")
        self.dirty(self.init_repo(app / "inner"))

    def test_depth_2_sees_repos_app(self) -> None:
        self.set_recursive("2")
        self.dirty(self.add_nested("repos/app"))
        self.assertTrue(self.run_hook())

    def test_depth_2_does_not_see_inner(self) -> None:
        self.set_recursive("2")
        self.add_inner()
        self.assertFalse(self.run_hook())

    def test_depth_3_sees_inner(self) -> None:
        self.set_recursive("3")
        self.add_inner()
        self.assertIn("repos/app/inner", self.hook_output())

    def test_true_reaches_depth_6(self) -> None:
        self.set_recursive()
        self.dirty(self.add_nested("a/b/c/d/e/app"))
        self.assertIn("a/b/c/d/e/app", self.hook_output())

    def test_true_stops_at_depth_7(self) -> None:
        self.set_recursive()
        self.dirty(self.add_nested("a/b/c/d/e/f/app"))
        self.assertFalse(self.run_hook())

    def test_invalid_recursive_values_disable_discovery(self) -> None:
        for i, value in enumerate(("0", "yes", "True", "false", "'3'", "-1")):
            with self.subTest(value=value):
                self.set_recursive(value)
                self.dirty(self.add_nested(f"repos/app{i}"))
                self.assertFalse(self.run_hook())

    def test_settings_local_in_nested_repo_passes(self) -> None:
        self.set_recursive()
        app = self.add_nested("repos/app")
        (app / ".claude").mkdir()
        (app / ".claude/settings.local.json").write_text("{}\n")
        sh(app, "git", "add", "-f", "-A")
        sh(app, "git", "commit", "-qm", "settings")
        (app / ".claude/settings.local.json").write_text('{"a": 1}\n')
        self.assertFalse(self.run_hook())

    def test_hook_off_overrides_recursive(self) -> None:
        self.set_recursive()
        self.dirty(self.add_nested("repos/app"))
        self.assertFalse(self.run_hook(OKF_HOOK="off"))

    def test_clean_nested_repos_pass(self) -> None:
        self.set_recursive()
        self.add_nested("repos/app")
        self.add_nested("repos/api")
        self.assertFalse(self.run_hook())

    def test_names_every_dirty_nested_repo(self) -> None:
        self.set_recursive()
        self.dirty(self.add_nested("repos/app"))
        self.dirty(self.add_nested("repos/api"))
        self.add_nested("repos/clean")
        out = self.hook_output()
        self.assertIn("nested repos: repos/api, repos/app)", out)
        self.assertNotIn("repos/clean", out)

    def test_submodule_is_not_counted(self) -> None:
        self.set_recursive()
        with tempfile.TemporaryDirectory() as sub_dir:
            src = self.init_repo(Path(sub_dir) / "src")
            sh(self.repo, "git", "-c", "protocol.file.allow=always",
               "submodule", "add", "-q", str(src), "vendor/lib")
            sh(self.repo, "git", "commit", "-qm", "add submodule")
            self.dirty(self.repo / "vendor/lib")
            # the outer status sees the submodule itself, so this blocks as an outer change
            self.assertNotIn("nested", self.hook_output())


if __name__ == "__main__":
    unittest.main()
