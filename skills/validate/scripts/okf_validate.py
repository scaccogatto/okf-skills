#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Deterministic conformance checker for Open Knowledge Format (OKF) v0.1.

Implements the §9 conformance rules verbatim:
  1. Every non-reserved `.md` file contains a parseable YAML frontmatter block.
  2. Every frontmatter block contains a non-empty `type` field.
  3. Reserved filenames (`index.md`, `log.md`) follow §6 / §7 when present.

Rules 1 and 2 are hard errors (a bundle that fails them is non-conformant).
Everything else the spec marks as soft guidance: reported as warnings, never
fatal unless `--strict` is given. In particular broken cross-links are NOT
errors — the spec requires consumers to tolerate them (§5.3).

Run:  uv run scripts/okf_validate.py <bundle-dir> [--strict] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

RESERVED = {"index.md", "log.md"}
# `resource` is intentionally excluded: the spec (§4.1) states it is absent for
# concepts describing abstract ideas, so flagging it produces false noise.
RECOMMENDED = ("title", "description", "tags", "timestamp")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FENCE = re.compile(r"^(```|~~~)")
# markdown link target capture: [text](target) — ignores images ![...]
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    concepts: int = 0
    indexes: int = 0
    logs: int = 0

    def err(self, rel: str, msg: str) -> None:
        self.errors.append(f"{rel}: {msg}")

    def warn(self, rel: str, msg: str) -> None:
        self.warnings.append(f"{rel}: {msg}")


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (raw_yaml, body). raw_yaml is None when no frontmatter block."""
    if not text.startswith("---"):
        return None, text
    # first line must be exactly '---' (allow trailing whitespace / BOM already stripped)
    lines = text.splitlines(keepends=True)
    if lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[1:i]), "".join(lines[i + 1 :])
    return None, text  # unterminated block → treated as absent


def check_concept(path: Path, rel: str, report: Report) -> None:
    report.concepts += 1
    text = path.read_text(encoding="utf-8").lstrip("﻿")
    raw, _ = split_frontmatter(text)
    if raw is None:
        report.err(rel, "§9.1 no parseable YAML frontmatter block")
        return
    try:
        meta = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        report.err(rel, f"§9.1 frontmatter is not valid YAML: {exc}".replace("\n", " "))
        return
    if not isinstance(meta, dict):
        report.err(rel, "§9.1 frontmatter must be a YAML mapping")
        return
    type_val = meta.get("type")
    if not (isinstance(type_val, str) and type_val.strip()):
        report.err(rel, "§9.2 missing or empty required `type` field")
    for key in RECOMMENDED:
        if key not in meta:
            report.warn(rel, f"recommended field `{key}` is absent (§4.1)")


def check_index(path: Path, rel: str, is_root: bool, report: Report) -> None:
    report.indexes += 1
    text = path.read_text(encoding="utf-8").lstrip("﻿")
    raw, _ = split_frontmatter(text)
    if raw is not None:
        if not is_root:
            report.warn(rel, "§6 index.md should contain no frontmatter")
        else:
            try:
                meta = yaml.safe_load(raw) or {}
            except yaml.YAMLError:
                report.warn(rel, "§11 root index.md frontmatter is not valid YAML")
                meta = {}
            extra = set(meta) - {"okf_version"}
            if extra:
                report.warn(rel, f"§11 root index.md frontmatter may only carry `okf_version` (found {sorted(extra)})")


def check_log(path: Path, rel: str, report: Report) -> None:
    report.logs += 1
    text = path.read_text(encoding="utf-8").lstrip("﻿")
    raw, _ = split_frontmatter(text)
    if raw is not None:
        report.warn(rel, "§7 log.md should contain no frontmatter")
    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            if not ISO_DATE.match(heading):
                report.warn(rel, f"§7 date heading `{heading}` is not ISO 8601 YYYY-MM-DD")


def collect_link_targets(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    targets: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        targets.extend(LINK.findall(line))
    return targets


def check_links(bundle: Path, md_files: list[Path], report: Report) -> None:
    """Broken bundle-internal links are warnings only (§5.3)."""
    existing = {p.relative_to(bundle).as_posix() for p in md_files}
    for path in md_files:
        rel = path.relative_to(bundle).as_posix()
        for target in collect_link_targets(path):
            t = target.split("#", 1)[0]
            if not t or t.endswith("/"):
                continue
            if re.match(r"^[a-z][a-z0-9+.-]*://", t) or t.startswith("mailto:"):
                continue
            if not t.endswith(".md"):
                continue
            if t.startswith("/"):
                resolved = t.lstrip("/")
            else:
                resolved = (path.parent / t).resolve().relative_to(bundle.resolve()).as_posix() \
                    if (path.parent / t).resolve().is_relative_to(bundle.resolve()) else t
            if resolved not in existing:
                report.warn(rel, f"cross-link target not found: `{target}` (tolerated under §5.3)")


def validate(bundle: Path) -> Report:
    report = Report()
    md_files = sorted(p for p in bundle.rglob("*.md") if p.is_file())
    for path in md_files:
        rel = path.relative_to(bundle).as_posix()
        name = path.name
        if name == "index.md":
            check_index(path, rel, is_root=(path.parent == bundle), report=report)
        elif name == "log.md":
            check_log(path, rel, report)
        else:
            check_concept(path, rel, report)
    check_links(bundle, md_files, report)
    return report


def _force_utf8_stdio() -> None:
    """Ensure stdout/stderr can emit the ✓/✗/— glyphs this tool prints.

    Windows consoles default to cp1252, which raises UnicodeEncodeError on those
    characters and crashes an otherwise-successful run. Reconfiguring to UTF-8
    (Python ≥3.7) fixes it; `errors="replace"` is a belt-and-suspenders fallback
    for any stream that still cannot encode a glyph.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main() -> int:
    _force_utf8_stdio()
    ap = argparse.ArgumentParser(description="Validate an OKF v0.1 bundle.")
    ap.add_argument("bundle", type=Path, help="path to the bundle directory")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--json", action="store_true", help="emit a JSON report")
    args = ap.parse_args()

    if not args.bundle.is_dir():
        print(f"error: {args.bundle} is not a directory", file=sys.stderr)
        return 2

    r = validate(args.bundle)
    conformant = not r.errors
    failed = bool(r.errors) or (args.strict and bool(r.warnings))

    if args.json:
        print(json.dumps({
            "bundle": str(args.bundle),
            "conformant": conformant,
            "passed": not failed,
            "counts": {"concepts": r.concepts, "indexes": r.indexes, "logs": r.logs},
            "errors": r.errors,
            "warnings": r.warnings,
        }, indent=2))
        return 0 if not failed else 1

    print(f"OKF v0.1 conformance — {args.bundle}")
    print(f"  concepts: {r.concepts}   index.md: {r.indexes}   log.md: {r.logs}")
    for e in r.errors:
        print(f"  \033[31m✗ ERROR\033[0m  {e}")
    for w in r.warnings:
        print(f"  \033[33m! warn \033[0m  {w}")
    if conformant and not r.warnings:
        print("  \033[32m✓ conformant — no issues\033[0m")
    elif conformant:
        print(f"  \033[32m✓ conformant\033[0m ({len(r.warnings)} warning(s))")
    else:
        print(f"  \033[31m✗ non-conformant\033[0m ({len(r.errors)} error(s))")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
