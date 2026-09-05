#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Unit tests for okf_backfill_events.py.

Run:  uv run tests/test_okf_backfill_events.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "backfill" / "scripts"))
from okf_backfill_events import (  # noqa: E402
    apply_skip_rules, git_log, normalize_ts, repo_slug,
    sessions_from_transcripts, merge_and_sort, truncate_text, check_coverage,
    split_patch, cap_patch, format_summary, show_commit,
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


class TestRepoSlug(unittest.TestCase):
    def test_maps_every_non_alphanumeric_to_dash(self):
        self.assertEqual(
            repo_slug(Path("/Users/g/dev/p-045_ekar_skills")),
            "-Users-g-dev-p-045-ekar-skills",
        )


class TestSessionExtraction(unittest.TestCase):
    """Test session transcript extraction, against the REAL transcript schema:
    envelope with message.content, timestamp, gitBranch, isMeta, isSidechain,
    plus standalone ai-title lines."""

    # A real, resolvable path: on Windows a POSIX-style fake path resolves to a
    # drive-prefixed one and would never match the slug or the cwd filter.
    REPO = str(Path(tempfile.gettempdir()).resolve() / "okf-backfill-fake-repo")
    SLUG = repo_slug(Path(REPO))

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
                cwd=str(Path(__file__).resolve().parents[1]),
                check=True,
                capture_output=True
            )

            # Second run
            subprocess.run(
                ["uv", "run", "skills/backfill/scripts/okf_backfill_events.py",
                 str(self.repo), "--out", str(out2), "--no-sessions"],
                cwd=str(Path(__file__).resolve().parents[1]),
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


class TestCheckCoverage(unittest.TestCase):
    """Test --check-coverage mode: verify all live events are mapped in bundle."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.scratch = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write_events(self, events: list[dict], filename: str = "events.jsonl") -> Path:
        """Write events to a JSONL file."""
        events_file = self.scratch / filename
        with open(events_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")
        return events_file

    def write_bundle(self, concepts: dict[str, str]) -> Path:
        """Write a minimal bundle with given concepts.

        concepts: dict of {filename: content}
        """
        bundle_dir = self.scratch / "bundle"
        bundle_dir.mkdir(exist_ok=True)
        for fname, content in concepts.items():
            fpath = bundle_dir / fname
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content)
        return bundle_dir

    def test_all_git_events_mapped_by_sha(self):
        """All live git events must be found by full or short sha in bundle."""
        events = [
            {"id": "git:abc1234567890", "source": "git", "skip": None},
            {"id": "git:def9876543210", "source": "git", "skip": None},
        ]
        events_file = self.write_events(events)
        bundle = self.write_bundle({
            "concept1.md": "sources:\n  - resource: git:abc1234567890\n",
            "concept2.md": "def98765",  # Short sha should match
        })

        unmapped = check_coverage(events_file, bundle)
        self.assertEqual(unmapped, [])

    def test_unmapped_git_events_listed(self):
        """Unmapped git events are returned and cause exit 1."""
        events = [
            {"id": "git:abc1234567890", "source": "git"},
            {"id": "git:def9876543210", "source": "git"},
        ]
        events_file = self.write_events(events)
        bundle = self.write_bundle({
            "concept1.md": "sources:\n  - resource: git:abc1234567890\n",
        })

        unmapped = check_coverage(events_file, bundle)
        self.assertEqual(unmapped, ["git:def9876543210"])

    def test_skipped_events_ignored(self):
        """Events with 'skip' field must be ignored (not checked)."""
        events = [
            {"id": "git:abc1234567890", "source": "git"},
            {"id": "git:def9876543210", "source": "git", "skip": "merge-no-files"},
        ]
        events_file = self.write_events(events)
        bundle = self.write_bundle({
            "concept1.md": "abc1234",  # Only first event is in bundle
        })

        unmapped = check_coverage(events_file, bundle)
        # Second event should not be listed even though it's unmapped
        self.assertEqual(unmapped, [])

    def test_session_events_by_literal_id(self):
        """Session events must be found by their literal id (with colons)."""
        events = [
            {"id": "session:file.jsonl:42", "source": "session"},
            {"id": "session:file.jsonl:99", "source": "session"},
        ]
        events_file = self.write_events(events)
        bundle = self.write_bundle({
            "concept1.md": "sources:\n  - resource: session:file.jsonl:42\n",
        })

        unmapped = check_coverage(events_file, bundle)
        self.assertEqual(unmapped, ["session:file.jsonl:99"])

    def test_mixed_git_and_session_events(self):
        """Coverage check handles a mix of git and session events."""
        events = [
            {"id": "git:abc1234567890", "source": "git"},
            {"id": "session:file.jsonl:42", "source": "session"},
            {"id": "git:def9876543210", "source": "git"},
        ]
        events_file = self.write_events(events)
        bundle = self.write_bundle({
            "concept1.md": "abc1234\nsession:file.jsonl:42",
        })

        unmapped = check_coverage(events_file, bundle)
        self.assertEqual(unmapped, ["git:def9876543210"])


class TestSplitPatch(unittest.TestCase):
    """Test patch splitting."""

    def test_empty_input(self):
        result = split_patch("")
        self.assertEqual(result, [])

    def test_single_block(self):
        patch = "diff --git a/file.txt b/file.txt\nindex 123..456\n--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-old\n+new\n"
        result = split_patch(patch)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["path"], "file.txt")
        self.assertEqual(len(result[0]["header"]), 4)  # diff --git, index, ---, +++
        self.assertEqual(len(result[0]["hunks"]), 1)

    def test_two_blocks(self):
        patch = (
            "diff --git a/a.txt b/a.txt\nindex 123..456\n--- a/a.txt\n+++ b/a.txt\n"
            "@@ -1 +1 @@\n-old\n+new\n"
            "diff --git a/b.txt b/b.txt\nindex 789..abc\n--- a/b.txt\n+++ b/b.txt\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )
        result = split_patch(patch)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["path"], "a.txt")
        self.assertEqual(result[1]["path"], "b.txt")


class TestCapPatch(unittest.TestCase):
    """Test patch capping."""

    def test_summary_arithmetic(self):
        """Hand-built blocks: 2 files, 10 lines each."""
        blocks = [
            {
                "path": "a.txt",
                "header": ["diff --git a/a.txt b/a.txt", "index 123..456", "--- a/a.txt", "+++ b/a.txt"],
                "hunks": [["@@ -1,5 +1,5 @@"] + [f"+line{i}" for i in range(5)]],
            },
            {
                "path": "b.txt",
                "header": ["diff --git a/b.txt b/b.txt", "index 789..abc", "--- a/b.txt", "+++ b/b.txt"],
                "hunks": [["@@ -1,5 +1,5 @@"] + [f"+line{i}" for i in range(5)]],
            },
        ]
        numstat_lines = ["5\t0\ta.txt", "5\t0\tb.txt"]

        lines, summary = cap_patch(
            blocks, numstat_lines,
            per_file_lines=20, max_diff_lines=50,
            max_line_chars=1000, skip_globs=[]
        )

        # Both files should fit
        self.assertFalse(summary["truncated"])
        self.assertEqual(summary["files_shown"], 2)
        self.assertEqual(summary["files_total"], 2)
        # Each file: 4 header + 1 @@ + 5 body = 10 lines
        self.assertEqual(summary["total"], 20)
        self.assertEqual(summary["shown"], 20)


class TestShowCommit(unittest.TestCase):
    """Test show_commit and CLI integration."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

        # Initialize git repo with stable branch
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo, check=True, capture_output=True)

    def commit(self, filename: str, content: str, msg: str):
        """Helper to create a single-file commit."""
        (self.repo / filename).write_text(content)
        subprocess.run(["git", "add", filename], cwd=self.repo, check=True, capture_output=True)
        env = os.environ.copy()
        env["GIT_COMMITTER_DATE"] = "2026-01-15 10:00:00 +0000"
        subprocess.run(["git", "commit", "-m", msg], cwd=self.repo, check=True, capture_output=True, env=env)

    def commit_files(self, files: dict[str, str], msg: str):
        """Helper to create a commit touching multiple files."""
        for filename, content in files.items():
            (self.repo / filename).write_text(content)
            subprocess.run(["git", "add", filename], cwd=self.repo, check=True, capture_output=True)
        env = os.environ.copy()
        env["GIT_COMMITTER_DATE"] = "2026-01-15 10:00:00 +0000"
        subprocess.run(["git", "commit", "-m", msg], cwd=self.repo, check=True, capture_output=True, env=env)

    def test_small_commit_passthrough(self):
        """5-line new file: output contains stat, patch, summary."""
        self.commit("newfile.txt", "a\nb\nc\nd\ne\n", "Add file")

        # Get the HEAD commit
        result = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        sha = result.stdout.strip()

        output = show_commit(self.repo, sha)
        lines = output.split("\n")

        # Check structure
        self.assertIn("# commit", lines[0])
        self.assertIn("# stat (complete)", output)
        self.assertIn("# patch", output)
        self.assertIn("[diff: shown=", lines[-2])  # -2 because last line is empty after final \n

        # No truncation for small file
        self.assertIn("truncated=false", output)
        self.assertIn("files_shown=1", output)
        self.assertIn("files_total=1", output)

    def test_per_file_cap_at_hunk_boundary(self):
        """Two hunks in one file, cap at first hunk boundary."""
        # Create 100-line file
        content = "\n".join([f"line{i}" for i in range(100)]) + "\n"
        self.commit("big.txt", content, "Add big file")

        # Modify lines 5 and 95 to create two hunks
        lines = content.split("\n")[:-1]  # Remove trailing empty
        lines[4] = "line4-modified"
        lines[94] = "line94-modified"
        modified_content = "\n".join(lines) + "\n"

        (self.repo / "big.txt").write_text(modified_content)
        subprocess.run(["git", "add", "big.txt"], cwd=self.repo, check=True, capture_output=True)
        env = os.environ.copy()
        env["GIT_COMMITTER_DATE"] = "2026-01-15 10:00:01 +0000"
        subprocess.run(["git", "commit", "-m", "Modify lines"], cwd=self.repo, check=True, capture_output=True, env=env)

        result = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        sha = result.stdout.strip()

        # Call with per_file_lines=15 so header+first hunk fit, second doesn't
        output = show_commit(self.repo, sha, per_file_lines=15)

        self.assertIn("[+", output)
        self.assertIn("more hunks of", output)
        self.assertIn("truncated=true", output)

    def test_oversize_first_hunk_is_cut(self):
        """Single hunk, header+budget fit, hunk is cut."""
        # 300-line file in one commit
        content = "\n".join([f"line{i}" for i in range(300)]) + "\n"
        self.commit("huge.txt", content, "Add huge file")

        result = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        sha = result.stdout.strip()

        # per_file_lines=20 means header(5) + @@ + 14 body
        output = show_commit(self.repo, sha, per_file_lines=20)

        self.assertIn("[hunk truncated:", output)
        self.assertIn("truncated=true", output)
        # Count non-marker, non-section-header lines
        patch_section = output.split("# patch\n")[1].split("[diff:")[0]
        patch_lines = [l for l in patch_section.split("\n") if l and not l.startswith("[")]
        # Should be header + @@ + body lines, totaling around 20
        self.assertLessEqual(len(patch_lines), 25)

    def test_generated_patch_omitted_stat_kept(self):
        """Commit touching app.py and package-lock.json."""
        self.commit_files(
            {"app.py": "print('hello')\n", "package-lock.json": "{}\n"},
            "Mix of files"
        )

        result = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        sha = result.stdout.strip()

        output = show_commit(self.repo, sha)

        # Both in stat
        self.assertIn("app.py", output.split("# patch")[0])
        self.assertIn("package-lock.json", output.split("# patch")[0])

        # Only app.py in patch
        self.assertIn("diff --git a/app.py", output)
        self.assertNotIn("diff --git a/package-lock.json", output)

        # Omission marker present
        self.assertIn("[patch omitted: package-lock.json (generated)", output)

        # Not truncated (we skipped one file by policy, not by cap)
        self.assertIn("truncated=false", output)

    def test_global_cap_at_file_boundary(self):
        """Five 30-line files, max_diff_lines=70."""
        for i in range(5):
            self.commit_files(
                {f"file{i}.txt": "\n".join([f"line{j}" for j in range(30)]) + "\n"},
                f"Add file{i}"
            )

        # Get last commit (which has all 5 files? no, each commit is separate)
        # Actually, let me create one commit with 5 files
        self.repo_init2 = tempfile.TemporaryDirectory()
        repo2 = Path(self.repo_init2.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=repo2, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo2, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo2, check=True, capture_output=True)

        files = {f"file{i}.txt": "\n".join([f"line{j}" for j in range(30)]) + "\n" for i in range(5)}
        for filename, content in files.items():
            (repo2 / filename).write_text(content)
            subprocess.run(["git", "add", filename], cwd=repo2, check=True, capture_output=True)
        env = os.environ.copy()
        env["GIT_COMMITTER_DATE"] = "2026-01-15 10:00:00 +0000"
        subprocess.run(["git", "commit", "-m", "Five files"], cwd=repo2, check=True, capture_output=True, env=env)

        result = subprocess.run(
            ["git", "-C", str(repo2), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        sha = result.stdout.strip()

        output = show_commit(repo2, sha, max_diff_lines=70, per_file_lines=120)

        self.assertIn("[patches omitted for", output)
        self.assertIn("files_total=5", output)
        self.assertIn("truncated=true", output)
        # Accounting closure: every line not shown is declared by exactly one marker
        # ([hunk truncated: +N more lines], [+N more lines in M more hunks of ...],
        # [patches omitted for K more files (+N lines)]), so shown + declared == total.
        summary = dict(p.split("=") for p in output.strip().splitlines()[-1].strip("[]")[6:].split())
        declared = sum(int(n) for n in re.findall(r"\+(\d+) (?:more )?lines", output))
        self.assertEqual(int(summary["total"]), int(summary["shown"]) + declared)

        self.repo_init2.cleanup()

    def test_merge_commit_diffs_against_first_parent(self):
        """Merge commit: diff is against first parent, not combined-diff."""
        # Create a commit on main
        self.commit("main.txt", "main content\n", "Main commit")

        # Create a branch with a different commit
        subprocess.run(["git", "checkout", "-b", "feature"], cwd=self.repo, check=True, capture_output=True)
        self.commit("feature.txt", "feature content\n", "Feature commit")

        # Go back to main
        subprocess.run(["git", "checkout", "main"], cwd=self.repo, check=True, capture_output=True)

        # Add another commit on main
        self.commit("main2.txt", "main2 content\n", "Main commit 2")

        # Merge feature into main
        env = os.environ.copy()
        env["GIT_COMMITTER_DATE"] = "2026-01-15 10:00:10 +0000"
        subprocess.run(
            ["git", "merge", "--no-ff", "feature", "-m", "Merge feature"],
            cwd=self.repo, check=True, capture_output=True, env=env
        )

        result = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        merge_sha = result.stdout.strip()

        output = show_commit(self.repo, merge_sha)

        # Merge commit should show feature.txt (from the branch)
        self.assertIn("diff --git", output)
        # Should NOT use combined-diff format (no diff --cc)
        self.assertNotIn("diff --cc", output)

    def test_only_path(self):
        """--only restricts to single file."""
        self.commit_files(
            {"a.py": "a\n", "b.py": "b\n"},
            "Two files"
        )

        result = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        sha = result.stdout.strip()

        # Only b.py
        output = show_commit(self.repo, sha, only="b.py")
        self.assertIn("diff --git a/b.py", output)
        self.assertNotIn("diff --git a/a.py", output)
        # Stat still has both
        self.assertIn("a.py", output.split("# patch")[0])
        self.assertIn("b.py", output.split("# patch")[0])

        # Invalid path
        with self.assertRaises(KeyError):
            show_commit(self.repo, sha, only="nope.py")

    def test_long_line_truncated(self):
        """Line longer than max_line_chars is truncated."""
        long_line = "x" * 2000
        self.commit("long.txt", long_line + "\n", "Long line")

        result = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        sha = result.stdout.strip()

        output = show_commit(self.repo, sha, max_line_chars=100)

        self.assertIn("[line truncated:", output)
        for line in output.split("\n"):
            if "[line truncated:" in line:
                # Should not exceed 100 + marker length significantly
                self.assertLessEqual(len(line), 150)

    def test_show_is_deterministic(self):
        """Two calls produce identical output."""
        self.commit("file.txt", "content\n", "Test")

        result = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        sha = result.stdout.strip()

        output1 = show_commit(self.repo, sha)
        output2 = show_commit(self.repo, sha)

        self.assertEqual(output1, output2)

    def test_cli_show(self):
        """CLI --show mode works."""
        self.commit("file.txt", "content\n", "Test")

        result = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        sha = result.stdout.strip()

        # Valid sha
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "skills" / "backfill" / "scripts" / "okf_backfill_events.py"),
             str(self.repo), "--show", sha],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("[diff: shown=", result.stdout)

        # Bad sha
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "skills" / "backfill" / "scripts" / "okf_backfill_events.py"),
             str(self.repo), "--show", "deadbeef"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
