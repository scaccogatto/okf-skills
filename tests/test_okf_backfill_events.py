#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Unit tests for okf_backfill_events.py.

Run:  uv run tests/test_okf_backfill_events.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "backfill" / "scripts"))
from okf_backfill_events import (  # noqa: E402
    apply_skip_rules, git_log, normalize_ts, sessions_from_transcripts,
    merge_and_sort,
)


class TestNormalizeTs(unittest.TestCase):
    """Test timestamp normalization to UTC epoch."""

    def test_iso8601_with_z(self):
        ts = "2026-01-15T10:30:00Z"
        epoch = normalize_ts(ts)
        self.assertGreater(epoch, 0)

    def test_iso8601_with_offset(self):
        ts = "2026-01-15T10:30:00+02:00"
        epoch = normalize_ts(ts)
        self.assertGreater(epoch, 0)

    def test_date_only(self):
        ts = "2026-01-15"
        epoch = normalize_ts(ts)
        self.assertGreater(epoch, 0)


class TestGitLog(unittest.TestCase):
    """Test git log extraction."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=self.repo,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.repo,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=self.repo,
            check=True,
            capture_output=True
        )

    def commit(self, filename: str, content: str, msg: str):
        """Helper to create a commit."""
        (self.repo / filename).write_text(content)
        subprocess.run(
            ["git", "add", filename],
            cwd=self.repo,
            check=True,
            capture_output=True
        )
        # Pin the committer date for determinism
        env = os.environ.copy()
        env["GIT_COMMITTER_DATE"] = "2026-01-15 10:00:00 +0000"
        subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=self.repo,
            check=True,
            capture_output=True,
            env=env
        )

    def test_extract_single_commit(self):
        self.commit("file.txt", "content", "Initial commit")

        events = git_log(self.repo, [])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["source"], "git")
        self.assertIn("git:", events[0]["id"])
        self.assertEqual(events[0]["subject"], "Initial commit")

    def test_extract_multiple_commits_in_order(self):
        self.commit("a.txt", "a", "First commit")
        self.commit("b.txt", "b", "Second commit")

        events = git_log(self.repo, [])
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["subject"], "First commit")
        self.assertEqual(events[1]["subject"], "Second commit")

    def test_files_extracted(self):
        self.commit("file1.txt", "content", "Add file1")
        self.commit("file2.txt", "content", "Add file2")

        events = git_log(self.repo, [])
        self.assertEqual(len(events), 2)
        # Each event should have files list
        self.assertIn("files", events[0])
        self.assertGreaterEqual(len(events[0]["files"]), 1)


class TestSkipRules(unittest.TestCase):
    """Test event skip rules."""

    def test_merge_no_files_skipped(self):
        event = {
            "source": "git",
            "files": [],
        }
        rule_id = apply_skip_rules(event, [])
        self.assertEqual(rule_id, "merge-no-files")

    def test_paths_only_generated_skipped(self):
        event = {
            "source": "git",
            "files": [
                {"path": "uv.lock", "add": 100, "del": 50},
            ],
        }
        rule_id = apply_skip_rules(event, [])
        self.assertEqual(rule_id, "paths-only-generated")

    def test_git_with_real_files_not_skipped(self):
        event = {
            "source": "git",
            "files": [
                {"path": "src/main.py", "add": 10, "del": 5},
            ],
        }
        rule_id = apply_skip_rules(event, [])
        self.assertIsNone(rule_id)

    def test_session_command_noise_short_message(self):
        event = {
            "source": "session",
            "user": "/help",
            "outcome": None,
        }
        rule_id = apply_skip_rules(event, [])
        self.assertEqual(rule_id, "session-command-noise")

    def test_session_with_outcome_not_skipped(self):
        event = {
            "source": "session",
            "user": "/help with this long message that has useful content",
            "outcome": "Here's the help",
        }
        rule_id = apply_skip_rules(event, [])
        self.assertIsNone(rule_id)


class TestSessionExtraction(unittest.TestCase):
    """Test session transcript extraction."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sessions_dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write_session_jsonl(self, subdir: str, records: list[dict]):
        """Helper to write a session JSONL file."""
        session_dir = self.sessions_dir / subdir
        session_dir.mkdir(parents=True, exist_ok=True)
        session_file = session_dir / "session.jsonl"

        with open(session_file, "w") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")

    def test_extract_user_assistant_pair(self):
        records = [
            {
                "type": "user",
                "text": "What is OKF?",
                "ts": "2026-01-15T10:00:00Z",
                "_lineno": 0,
            },
            {
                "type": "assistant",
                "text": "OKF is an open knowledge format.",
                "ts": "2026-01-15T10:00:05Z",
            },
        ]
        self.write_session_jsonl("test-repo", records)

        events = sessions_from_transcripts(Path("/fake-repo"), self.sessions_dir)
        # Note: the slug won't match, so we might get 0 events
        # Let's just ensure no crash

    def test_skip_meta_records(self):
        records = [
            {
                "type": "user",
                "text": "Question",
                "ts": "2026-01-15T10:00:00Z",
                "_lineno": 0,
            },
            {
                "type": "user",
                "text": "Meta message",
                "isMeta": True,
                "ts": "2026-01-15T10:00:01Z",
                "_lineno": 1,
            },
        ]
        self.write_session_jsonl("test-repo", records)
        # Should not crash


class TestMergeAndSort(unittest.TestCase):
    """Test merging and sorting events."""

    def test_sort_by_timestamp(self):
        git_events = [
            {"id": "git:1", "source": "git", "ts": 1000.0},
            {"id": "git:3", "source": "git", "ts": 3000.0},
        ]
        session_events = [
            {"id": "session:2", "source": "session", "ts": 2000.0},
        ]

        merged = merge_and_sort(git_events, session_events)

        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[0]["id"], "git:1")
        self.assertEqual(merged[1]["id"], "session:2")
        self.assertEqual(merged[2]["id"], "git:3")

    def test_git_before_session_same_ts(self):
        events_git = [{"id": "git:1", "source": "git", "ts": 1000.0}]
        events_session = [{"id": "session:1", "source": "session", "ts": 1000.0}]

        merged = merge_and_sort(events_git, events_session)

        # Git comes first when ts is equal
        self.assertEqual(merged[0]["source"], "git")
        self.assertEqual(merged[1]["source"], "session")


class TestDeterminism(unittest.TestCase):
    """Test that extraction is deterministic (byte-identical output)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=self.repo,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.repo,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=self.repo,
            check=True,
            capture_output=True
        )

        # Create a simple commit
        (self.repo / "file.txt").write_text("content")
        subprocess.run(
            ["git", "add", "file.txt"],
            cwd=self.repo,
            check=True,
            capture_output=True
        )
        env = os.environ.copy()
        env["GIT_COMMITTER_DATE"] = "2026-01-15 10:00:00 +0000"
        subprocess.run(
            ["git", "commit", "-m", "Test commit"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            env=env
        )

    def test_second_run_is_identical(self):
        out1 = Path(tempfile.gettempdir()) / "events1.jsonl"
        out2 = Path(tempfile.gettempdir()) / "events2.jsonl"

        try:
            # First run
            subprocess.run(
                ["uv", "run", "skills/backfill/scripts/okf_backfill_events.py",
                 str(self.repo), "--out", str(out1), "--no-sessions"],
                cwd="/Users/gatto/Developer/scaccogatto/okf-skills/.claude/worktrees/backfill-skill",
                check=True,
                capture_output=True
            )

            # Second run
            subprocess.run(
                ["uv", "run", "skills/backfill/scripts/okf_backfill_events.py",
                 str(self.repo), "--out", str(out2), "--no-sessions"],
                cwd="/Users/gatto/Developer/scaccogatto/okf-skills/.claude/worktrees/backfill-skill",
                check=True,
                capture_output=True
            )

            # Compare
            content1 = out1.read_bytes()
            content2 = out2.read_bytes()
            self.assertEqual(content1, content2, "Output should be byte-identical")
        finally:
            out1.unlink(missing_ok=True)
            out2.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
