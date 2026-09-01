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
    merge_and_sort, truncate_text,
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


class TestGitLogMultiBranch(unittest.TestCase):
    """Test --branch given multiple times: union of commits, first branch wins on dup SHAs."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo, check=True, capture_output=True)

    def commit(self, filename: str, content: str, msg: str):
        (self.repo / filename).write_text(content)
        subprocess.run(["git", "add", filename], cwd=self.repo, check=True, capture_output=True)
        env = os.environ.copy()
        env["GIT_COMMITTER_DATE"] = "2026-01-15 10:00:00 +0000"
        subprocess.run(["git", "commit", "-m", msg], cwd=self.repo, check=True, capture_output=True, env=env)

    def test_union_of_two_branches_no_duplicate_shas(self):
        self.commit("a.txt", "a", "Common commit")
        subprocess.run(["git", "checkout", "-b", "feature"], cwd=self.repo, check=True, capture_output=True)
        self.commit("b.txt", "b", "Feature commit")
        subprocess.run(["git", "checkout", "main"], cwd=self.repo, check=True, capture_output=True)
        self.commit("c.txt", "c", "Main-only commit")

        events = git_log(self.repo, ["main", "feature"])
        shas = [e["sha"] for e in events]
        self.assertEqual(len(shas), len(set(shas)), "no duplicate SHAs across branches")
        subjects = {e["subject"] for e in events}
        self.assertEqual(subjects, {"Common commit", "Feature commit", "Main-only commit"})


class TestTruncateText(unittest.TestCase):
    def test_within_bound_for_small_max_len(self):
        text = "x" * 5000
        max_len = 200
        result = truncate_text(text, max_len)
        self.assertLessEqual(len(result), max_len + 7)
        self.assertIn("[...]", result)

    def test_short_text_untouched(self):
        self.assertEqual(truncate_text("short", 200), "short")


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
    """Test session transcript extraction, against the REAL transcript schema:
    envelope with message.content, timestamp, gitBranch, isMeta, isSidechain,
    plus standalone ai-title lines."""

    REPO = "/Users/fake/repo"
    SLUG = REPO.replace("/", "-").replace(".", "-")

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sessions_dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write_session_jsonl(self, records: list[dict], filename: str = "session.jsonl", subdir: str = None):
        """Helper to write a session JSONL file, defaulting to the slug dir
        that matches self.REPO so sessions_from_transcripts finds it."""
        session_dir = self.sessions_dir / (subdir or self.SLUG)
        session_dir.mkdir(parents=True, exist_ok=True)
        session_file = session_dir / filename

        with open(session_file, "w") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")

    @staticmethod
    def user_rec(content, ts="2026-01-15T10:00:00.000Z", cwd=REPO, branch="main",
                 is_meta=None, is_sidechain=False):
        return {
            "type": "user",
            "timestamp": ts,
            "cwd": cwd,
            "gitBranch": branch,
            "isMeta": is_meta,
            "isSidechain": is_sidechain,
            "message": {"role": "user", "content": content},
        }

    @staticmethod
    def assistant_rec(text_blocks, ts="2026-01-15T10:00:05.000Z"):
        content = [{"type": "text", "text": t} for t in text_blocks]
        return {
            "type": "assistant",
            "timestamp": ts,
            "message": {"role": "assistant", "content": content},
        }

    def test_extract_user_assistant_pair(self):
        records = [
            self.user_rec("What is OKF?"),
            self.assistant_rec(["OKF is an open knowledge format."]),
        ]
        self.write_session_jsonl(records)

        events = sessions_from_transcripts(Path(self.REPO), self.sessions_dir)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["user"], "What is OKF?")
        self.assertEqual(events[0]["outcome"], "OKF is an open knowledge format.")
        self.assertEqual(events[0]["branch"], "main")

    def test_skip_meta_and_sidechain_records(self):
        records = [
            self.user_rec("Real question"),
            self.assistant_rec(["Real answer"]),
            self.user_rec("Meta message", is_meta=True),
            self.user_rec("Sidechain message", is_sidechain=True),
        ]
        self.write_session_jsonl(records)

        events = sessions_from_transcripts(Path(self.REPO), self.sessions_dir)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["user"], "Real question")

    def test_tool_result_only_user_excluded(self):
        """A user record whose content is only tool_result blocks (no text)
        must be excluded entirely, not turned into an empty-string event."""
        records = [
            self.user_rec("Real question"),
            self.assistant_rec(["Real answer", ""]),
            self.user_rec([{"type": "tool_result", "content": "some output"}]),
        ]
        self.write_session_jsonl(records)

        events = sessions_from_transcripts(Path(self.REPO), self.sessions_dir)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["user"], "Real question")

    def test_wrong_cwd_excluded(self):
        records = [
            self.user_rec("In repo", cwd=self.REPO),
            self.assistant_rec(["ok"]),
            self.user_rec("Other repo entirely", cwd="/Users/fake/other-repo"),
            self.assistant_rec(["ok2"]),
        ]
        self.write_session_jsonl(records)

        events = sessions_from_transcripts(Path(self.REPO), self.sessions_dir)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["user"], "In repo")

    def test_worktree_cwd_included(self):
        """cwd under <repo>/.claude/worktrees/* must still count as in-repo."""
        records = [
            self.user_rec("From a worktree", cwd=self.REPO + "/.claude/worktrees/foo"),
            self.assistant_rec(["ok"]),
        ]
        self.write_session_jsonl(records)

        events = sessions_from_transcripts(Path(self.REPO), self.sessions_dir)
        self.assertEqual(len(events), 1)

    def test_last_text_block_is_outcome(self):
        """Outcome must be the LAST non-empty text block across all assistant
        records before the next user record (the turn wrap-up), not the first."""
        records = [
            self.user_rec("Do a thing"),
            self.assistant_rec(["I'll start by looking at the files."]),
            self.assistant_rec(["Here's the final wrap-up."]),
        ]
        self.write_session_jsonl(records)

        events = sessions_from_transcripts(Path(self.REPO), self.sessions_dir)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["outcome"], "Here's the final wrap-up.")

    def test_real_line_numbers_in_ids(self):
        """Event ids must use the true 1-based line number of the user
        record in the file, including non-user/junk lines interspersed."""
        records = [
            {"type": "mode", "mode": "normal"},
            self.user_rec("First"),
            self.assistant_rec(["ok1"]),
            {"type": "system", "subtype": "noise"},
            self.user_rec("Second"),
            self.assistant_rec(["ok2"]),
        ]
        self.write_session_jsonl(records, filename="session.jsonl")

        events = sessions_from_transcripts(Path(self.REPO), self.sessions_dir)
        self.assertEqual(len(events), 2)
        # "First" is on line 2 (1-based), "Second" is on line 5
        self.assertEqual(events[0]["id"], "session:session.jsonl:2")
        self.assertEqual(events[1]["id"], "session:session.jsonl:5")

    def test_title_is_last_ai_title_in_file(self):
        records = [
            self.user_rec("Q1"),
            self.assistant_rec(["A1"]),
            {"type": "ai-title", "aiTitle": "First title"},
            self.user_rec("Q2"),
            self.assistant_rec(["A2"]),
            {"type": "ai-title", "aiTitle": "Final title"},
        ]
        self.write_session_jsonl(records)

        events = sessions_from_transcripts(Path(self.REPO), self.sessions_dir)
        self.assertEqual(len(events), 2)
        # Both turns get the last aiTitle in the whole file
        self.assertEqual(events[0]["title"], "Final title")
        self.assertEqual(events[1]["title"], "Final title")


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


SCRIPT_ROOT = str(Path(__file__).resolve().parents[1])


class TestTsFormat(unittest.TestCase):
    """Output ts must be an ISO8601 UTC string ending in Z, not an epoch float."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

        subprocess.run(["git", "init"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo, check=True, capture_output=True)
        (self.repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "file.txt"], cwd=self.repo, check=True, capture_output=True)
        env = os.environ.copy()
        env["GIT_AUTHOR_DATE"] = "2026-01-15 10:00:00 +0100"
        env["GIT_COMMITTER_DATE"] = "2026-01-15 10:00:00 +0100"
        subprocess.run(["git", "commit", "-m", "Test commit"], cwd=self.repo, check=True, capture_output=True, env=env)

    def test_ts_ends_with_z(self):
        out = Path(tempfile.gettempdir()) / "events_ts_format.jsonl"
        try:
            subprocess.run(
                ["uv", "run", "skills/backfill/scripts/okf_backfill_events.py",
                 str(self.repo), "--out", str(out), "--no-sessions"],
                cwd=SCRIPT_ROOT, check=True, capture_output=True,
            )
            lines = out.read_text().strip().split("\n")
            self.assertEqual(len(lines), 1)
            event = json.loads(lines[0])
            self.assertTrue(event["ts"].endswith("Z"), event["ts"])
            # Local offset +01:00 in the commit must be normalized to UTC:
            # 10:00 +01:00 == 09:00 Z
            self.assertEqual(event["ts"], "2026-01-15T09:00:00Z")
        finally:
            out.unlink(missing_ok=True)


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
