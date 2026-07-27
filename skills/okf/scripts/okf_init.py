#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Scaffold a conformant starter Open Knowledge Format (OKF) v0.2 bundle.

Creates a root `index.md` (frontmatter carries only `okf_version`), a `log.md`
with a creation entry under today's ISO date heading, and one starter concept
(`getting-started.md`) with the full set of recommended frontmatter fields.
The scaffold is meant to be exemplary: `okf_validate.py --strict` should pass
it with zero warnings.

Run:  uv run scripts/okf_init.py <target-dir> [--title "..."] [--force]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

OKF_VERSION = "0.2"
STARTER_CONCEPT = "getting-started.md"
# Actor convention (§7): an automated process, not an agent with a version.
ACTOR = "process:okf_init"


def humanize(name: str) -> str:
    words = name.replace("-", " ").replace("_", " ").strip()
    return words.title() if words else "Untitled"


def frontmatter(meta: dict) -> str:
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n"


def build_index(title: str) -> str:
    meta = frontmatter({"okf_version": OKF_VERSION})
    return (
        f"{meta}\n"
        f"# {title}\n\n"
        f"* [Getting started]({STARTER_CONCEPT}) - starting point for this bundle.\n"
    )


def build_log(today: str, title: str) -> str:
    return (
        "# Update Log\n\n"
        f"## {today}\n"
        f"* **Creation**: Scaffolded the {title} bundle with `okf_init.py` — "
        f"see [getting started]({STARTER_CONCEPT}).\n"
    )


def build_concept(title: str, now_iso: str) -> str:
    meta = frontmatter({
        "type": "Reference",
        "title": f"Getting started — {title}",
        "description": f"Starting point for the {title} OKF bundle.",
        "tags": ["getting-started"],
        "status": "stable",
        "generated": {"by": ACTOR, "at": now_iso},
    })
    return (
        f"{meta}\n"
        "# Overview\n\n"
        "This is the first concept in a freshly scaffolded OKF bundle. Replace "
        "it with real knowledge — one concept per file, cross-linked with "
        "standard markdown links — and keep `index.md` and `log.md` updated as "
        "you go.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=f"Scaffold a starter OKF v{OKF_VERSION} bundle.")
    ap.add_argument("target", type=Path, help="directory to create the bundle in")
    ap.add_argument("--title", default=None, help="bundle title (default: humanized target dir name)")
    ap.add_argument("--force", action="store_true", help="scaffold even if the target already has .md files")
    args = ap.parse_args()

    if args.target.exists() and not args.target.is_dir():
        print(f"error: {args.target} exists and is not a directory", file=sys.stderr)
        return 2

    existing_md = list(args.target.rglob("*.md")) if args.target.is_dir() else []
    if existing_md and not args.force:
        print(f"refusing: {args.target} already contains .md files (pass --force to scaffold anyway)", file=sys.stderr)
        for p in sorted(existing_md)[:5]:
            print(f"  {p.relative_to(args.target)}", file=sys.stderr)
        return 1

    title = args.title or humanize(args.target.resolve().name)
    today = datetime.now(timezone.utc).date().isoformat()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    args.target.mkdir(parents=True, exist_ok=True)
    (args.target / "index.md").write_text(build_index(title), encoding="utf-8")
    (args.target / "log.md").write_text(build_log(today, title), encoding="utf-8")
    (args.target / STARTER_CONCEPT).write_text(build_concept(title, now_iso), encoding="utf-8")

    validator = Path(__file__).resolve().parents[2] / "validate" / "scripts" / "okf_validate.py"
    print(f"created OKF bundle scaffold at {args.target}")
    print(f"hint: validate it — uv run {validator} {args.target} --strict (or the validate skill)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
