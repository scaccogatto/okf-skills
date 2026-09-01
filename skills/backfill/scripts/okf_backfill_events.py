#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Event-sourcing extractor: reconstruct OKF bundle from git + session history.

Deterministic extraction: same input → byte-identical events.jsonl.

Run:  uv run okf_backfill_events.py <repo-dir> [--out events.jsonl]
      [--branch REF ...] [--no-sessions] [--sessions-dir DIR] [--max-text 2000]
      [--skip-globs GLOB ...]
"""
from __future__ import annotations

import argparse
import glob as glob_module
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Skip rule predicates
@dataclass
class SkipRule:
    id: str
    check: callable


def matches_globs(paths: list[str], globs: list[str]) -> bool:
    """True if ALL paths match at least one glob pattern."""
    if not paths:
        return False
    for path in paths:
        if not any(fnmatch.fnmatch(path, g) for g in globs):
            return False
    return True


LOCKFILE_GLOBS = [
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "uv.lock",
    "Cargo.lock",
    "go.sum",
    "vendor/**",
    "node_modules/**",
    "dist/**",
    "*.min.*",
]


def rule_paths_only_generated(event: dict, skip_globs: list[str]) -> bool:
    """Commit only touches generated/lockfile paths."""
    if event["source"] != "git":
        return False
    globs = LOCKFILE_GLOBS + skip_globs
    paths = [f["path"] for f in event.get("files", [])]
    return matches_globs(paths, globs)


def rule_merge_no_files(event: dict, skip_globs: list[str]) -> bool:
    """Merge commit with no files touched."""
    if event["source"] != "git":
        return False
    return len(event.get("files", [])) == 0


def rule_session_command_noise(event: dict, skip_globs: list[str]) -> bool:
    """Session event that is just a slash command or too short with no outcome."""
    if event["source"] != "session":
        return False
    user = event.get("user", "").strip()

    # Bare slash command (no space or just "/" alone)
    if user == "/" or (user.startswith("/") and " " not in user):
        return True

    # Local command output (starts with "<")
    if user.startswith("<"):
        return True

    # Too short after strip (< 20 chars) AND no useful outcome
    if len(user) < 20 and not event.get("outcome"):
        return True

    return False


SKIP_RULES = [
    SkipRule("paths-only-generated", rule_paths_only_generated),
    SkipRule("merge-no-files", rule_merge_no_files),
    SkipRule("session-command-noise", rule_session_command_noise),
]


def normalize_ts(ts: str) -> float:
    """Convert ISO8601 timestamp to UTC epoch float."""
    # Handle RFC3339 with or without timezone
    ts = ts.strip()

    # If it ends with Z, it's UTC
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"

    # Handle offset timezone offsets like +01:00 or -05:00
    try:
        # Try ISO format parsing
        if "T" in ts:
            dt = datetime.fromisoformat(ts)
        else:
            # Date only
            dt = datetime.fromisoformat(ts + "T00:00:00")
        return dt.timestamp()
    except Exception:
        print(f"Warning: could not parse timestamp {ts!r}, using epoch 0", file=sys.stderr)
        return 0.0


def epoch_to_iso_z(epoch: float) -> str:
    """Format a UTC epoch as ISO8601 with a Z suffix, second precision."""
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_log(repo_dir: Path, branches: list[str]) -> list[dict]:
    """Extract events from git log across one or more branches (union, first
    branch wins on duplicate SHAs)."""
    branches = _resolve_branches(repo_dir, branches)
    if not branches:
        return []

    events = []
    seen_shas = set()
    for branch in branches:
        for event in _git_log_one_branch(repo_dir, branch):
            if event["sha"] in seen_shas:
                continue
            seen_shas.add(event["sha"])
            events.append(event)
    return events


def _resolve_branches(repo_dir: Path, branches: list[str]) -> list[str]:
    """Resolve the branch list to query: explicit branches, else default
    branch from origin/HEAD, else current branch."""
    if branches:
        return branches

    # Try to get default branch from origin/HEAD
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            # Typically returns "refs/remotes/origin/main" or similar
            default_branch = result.stdout.strip().split("/")[-1]
            branches = [default_branch]
    except Exception:
        pass

    if not branches:
        # Fallback to current branch
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, check=True
            )
            branches = [result.stdout.strip()]
        except Exception:
            return []

    return branches


def _git_log_one_branch(repo_dir: Path, branch: str) -> list[dict]:
    """Extract events from git log for a single branch (first-parent,
    reverse, numstat)."""
    events = []

    # Get log info and numstat separately
    try:
        # First, get commit info (SHA, timestamp, author, subject, body)
        log_result = subprocess.run(
            ["git", "-C", str(repo_dir), "log", "--first-parent", "--reverse",
             "--format=%H%n%aI%n%an%n%s%n%b%n<<<SEP>>>", branch],
            capture_output=True, text=True, check=True
        )

        # Get numstat (SHA and file changes)
        numstat_result = subprocess.run(
            ["git", "-C", str(repo_dir), "log", "--first-parent", "--reverse",
             "--numstat", "--format=%H%n<<<STAT_SEP>>>", branch],
            capture_output=True, text=True, check=True
        )

        # Parse log output (maintain order)
        log_blocks = log_result.stdout.split("<<<SEP>>>")
        commits_ordered = []  # List to maintain order
        commits_dict = {}     # Dict for lookup during numstat

        for block in log_blocks:
            if not block.strip():
                continue

            lines = block.strip().split("\n")
            if len(lines) < 4:
                continue

            sha = lines[0].strip()
            ts_str = lines[1].strip()
            author = lines[2].strip()
            subject = lines[3].strip()
            body = "\n".join(lines[4:]).strip() if len(lines) > 4 else ""

            commit_data = {
                "sha": sha,
                "ts": normalize_ts(ts_str),
                "author": author,
                "subject": subject,
                "body": body,
                "files": [],
            }
            commits_ordered.append(commit_data)
            commits_dict[sha] = commit_data

        # Parse numstat output
        numstat_blocks = numstat_result.stdout.split("<<<STAT_SEP>>>")
        current_sha = None

        for block in numstat_blocks:
            lines = block.strip().split("\n")

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # First line in block (after <<<STAT_SEP>>>) is SHA
                if line and "\t" not in line:
                    current_sha = line
                    if current_sha not in commits_dict:
                        # Shouldn't happen, but handle gracefully
                        commits_dict[current_sha] = {
                            "sha": current_sha,
                            "ts": 0,
                            "author": "",
                            "subject": "",
                            "body": "",
                            "files": [],
                        }
                        commits_ordered.append(commits_dict[current_sha])
                elif current_sha and "\t" in line:
                    # Numstat line: additions\tdeletions\tpath
                    parts = line.split("\t", 2)
                    if len(parts) >= 3:
                        try:
                            add = int(parts[0]) if parts[0] != "-" else 0
                            dele = int(parts[1]) if parts[1] != "-" else 0
                            path = parts[2]
                            commits_dict[current_sha]["files"].append({
                                "path": path,
                                "add": add,
                                "del": dele
                            })
                        except (ValueError, IndexError):
                            pass

        # Build events in the order we saw commits
        for c in commits_ordered:
            event = {
                "id": f"git:{c['sha']}",
                "source": "git",
                "ts": c["ts"],
                "sha": c["sha"],
                "author": c["author"],
                "subject": c["subject"],
                "body": c["body"],
                "files": c["files"],
            }
            events.append(event)

    except Exception:
        # Git command failed, return empty
        pass

    return events


def sessions_from_transcripts(repo_dir: Path, sessions_dir: Optional[Path]) -> list[dict]:
    """Extract events from Claude session transcripts."""
    events = []

    if sessions_dir is None:
        sessions_dir = Path.home() / ".claude" / "projects"

    if not sessions_dir.exists():
        return events

    # Compute repo slug and canonical path (for the cwd filter)
    repo_abs = repo_dir.resolve()
    repo_str = str(repo_abs)
    slug = repo_str.replace("/", "-").replace(".", "-")

    # Find session files: <slug>/*.jsonl and <slug>--*/*.jsonl
    session_globs = [
        str(sessions_dir / slug / "*.jsonl"),
        str(sessions_dir / f"{slug}--*/") + "*.jsonl",
    ]

    session_files = []
    for pattern in session_globs:
        session_files.extend(glob_module.glob(pattern))

    session_files = sorted(set(session_files))

    for session_file in session_files:
        session_path = Path(session_file)

        # Read raw lines, keeping the real 1-based line number of each record
        try:
            raw_lines = session_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        records = []  # list of (lineno, dict)
        for lineno, line in enumerate(raw_lines, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if isinstance(rec, dict):
                records.append((lineno, rec))

        # Title: the LAST aiTitle in the file, computed once per file (not
        # rescanned per turn).
        title = None
        for _, rec in records:
            if rec.get("type") == "ai-title" and rec.get("aiTitle"):
                title = rec["aiTitle"]

        n = len(records)
        i = 0
        while i < n:
            lineno, rec = records[i]

            # Skip non-user messages, meta, and sidechain records
            if rec.get("type") != "user" or rec.get("isMeta") or rec.get("isSidechain"):
                i += 1
                continue

            content = (rec.get("message") or {}).get("content")
            if isinstance(content, str):
                user_text = content
            elif isinstance(content, list):
                text_blocks = [
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                if not text_blocks:
                    # e.g. tool_result-only user record: nothing to extract
                    i += 1
                    continue
                user_text = "".join(text_blocks)
            else:
                i += 1
                continue

            # cwd filter: only keep records from this repo (or a worktree under it)
            cwd = rec.get("cwd") or ""
            if cwd != repo_str and not cwd.startswith(repo_str + "/"):
                i += 1
                continue

            ts_str = rec.get("timestamp", "")
            branch = rec.get("gitBranch")

            # Find the outcome: scan forward to the next user record, taking
            # the LAST non-empty text block across the assistant records
            # in between (the turn wrap-up).
            outcome_text = ""
            j = i + 1
            while j < n:
                _, next_rec = records[j]
                if next_rec.get("type") == "user":
                    break
                if next_rec.get("type") == "assistant":
                    acontent = (next_rec.get("message") or {}).get("content")
                    if isinstance(acontent, list):
                        for block in acontent:
                            if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                                outcome_text = block["text"]
                j += 1

            event = {
                "id": f"session:{session_path.name}:{lineno}",
                "source": "session",
                "ts": normalize_ts(ts_str),
                "user": user_text,
                "outcome": outcome_text if outcome_text else None,
                "title": title,
                "branch": branch,
            }
            events.append(event)

            i = j

    return events


def apply_skip_rules(event: dict, skip_globs: list[str]) -> Optional[str]:
    """Apply skip rules and return rule_id if should be skipped, None otherwise."""
    for rule in SKIP_RULES:
        if rule.check(event, skip_globs):
            return rule.id
    return None


def merge_and_sort(git_events: list[dict], session_events: list[dict]) -> list[dict]:
    """Merge and sort events by (ts, source, id)."""
    all_events = git_events + session_events

    # Sort by timestamp, then source (git first), then id
    def sort_key(event):
        source_order = {"git": 0, "session": 1}
        return (event["ts"], source_order.get(event["source"], 999), event["id"])

    all_events.sort(key=sort_key)
    return all_events


def truncate_text(text: str, max_len: int = 2000) -> str:
    """Apply head+tail truncation with marker."""
    if len(text) <= max_len:
        return text

    head_len = max_len * 3 // 4
    tail_len = max_len - head_len

    head = text[:head_len]
    tail = text[-tail_len:] if tail_len else ""
    return head + "\n[...]\n" + tail


def main():
    parser = argparse.ArgumentParser(
        description="Event-sourcing extractor for OKF bundle reconstruction"
    )
    parser.add_argument("repo_dir", help="Repository directory")
    parser.add_argument("--out", default="events.jsonl", help="Output file")
    parser.add_argument(
        "--branch", action="append", default=[], help="Git branch(es) to extract"
    )
    parser.add_argument(
        "--no-sessions", action="store_true", help="Skip session extraction"
    )
    parser.add_argument(
        "--sessions-dir", type=Path, help="Override sessions directory"
    )
    parser.add_argument(
        "--max-text", type=int, default=2000, help="Max text length per field"
    )
    parser.add_argument(
        "--skip-globs", action="append", default=[], help="Additional skip globs"
    )

    args = parser.parse_args()

    repo_dir = Path(args.repo_dir).resolve()
    if not repo_dir.exists():
        print(f"Error: {repo_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    # Extract events
    git_events = git_log(repo_dir, args.branch)
    session_events = [] if args.no_sessions else sessions_from_transcripts(
        repo_dir, args.sessions_dir
    )

    # Merge and sort
    events = merge_and_sort(git_events, session_events)

    # Apply skip rules and truncate
    skip_globs = args.skip_globs
    skip_counts = {}

    for event in events:
        skip_id = apply_skip_rules(event, skip_globs)
        if skip_id:
            event["skip"] = skip_id
            skip_counts[skip_id] = skip_counts.get(skip_id, 0) + 1

        # Truncate text fields
        for key in ["subject", "body", "outcome", "user"]:
            if key in event and isinstance(event[key], str):
                event[key] = truncate_text(event[key], args.max_text)

        # Emit ts as an ISO8601 UTC string; the epoch float was only needed
        # for sorting.
        event["ts"] = epoch_to_iso_z(event["ts"])

    # Write JSONL (deterministic order)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        for event in events:
            # Sort keys for determinism
            sorted_event = {k: event[k] for k in sorted(event.keys())}
            f.write(json.dumps(sorted_event, separators=(',', ':'), sort_keys=True) + "\n")

    # Report
    print(f"Extracted {len(events)} events")
    print(f"  Git: {len(git_events)}")
    print(f"  Sessions: {len(session_events)}")
    if skip_counts:
        print("Skipped:")
        for rule_id, count in sorted(skip_counts.items()):
            print(f"  {rule_id}: {count}")


if __name__ == "__main__":
    main()
