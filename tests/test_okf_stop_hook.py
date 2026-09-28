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
                           capture_output=True, text=True, env={**base, **env})
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
                           capture_output=True, text=True)
        self.assertIn("nothing under .okf/ changed", r.stdout)
        self.assertIn("only for a lifecycle event", r.stdout)


if __name__ == "__main__":
    unittest.main()
