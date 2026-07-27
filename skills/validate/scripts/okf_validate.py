#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Deterministic conformance checker for Open Knowledge Format (OKF) v0.2.

Implements the §11 conformance rules verbatim:
  1. Every non-reserved `.md` file contains a parseable YAML frontmatter block.
  2. Every frontmatter block contains a non-empty `type` field.
  3. Reserved filenames (`index.md`, `log.md`) follow §8 / §9 when present.

Rules 1 and 2 are hard errors (a bundle that fails them is non-conformant).
Everything else the spec marks as soft guidance: reported as warnings, never
fatal unless `--strict` is given. In particular broken cross-links are NOT
errors — the spec requires consumers to tolerate them (§6.1).

v0.1 bundles still validate: the two superseded constructs (`timestamp`, a body
`# Citations` list) are read and reported as warnings pointing at their v0.2
replacements (`generated.at`, `sources`), never as errors (§13.1). `--migrate`
performs that rewrite in place, textually, so `--strict` has a door and not just
a wall.

Run:  uv run scripts/okf_validate.py <bundle-dir>
        [--strict | --max-warnings N] [--migrate] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

OKF_VERSION = "0.2"
RESERVED = {"index.md", "log.md"}
# `resource` is intentionally excluded: the spec (§4.1) states it is absent for
# concepts describing abstract ideas, so flagging it produces false noise.
RECOMMENDED = ("title", "description", "tags")
STATUS_VALUES = {"draft", "stable", "deprecated"}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# RFC 3339, as the spec writes `generated.at` / `verified[].at` throughout. A
# date-only value is tolerated: it is common in the wild and loses only precision.
# PyYAML resolves an unquoted timestamp to a datetime whose str() separates with a
# space, so both spellings have to pass — as with `stale_after` above.
RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}"
    r"(?:[Tt ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:[Zz]|[+-]\d{2}:?\d{2})?)?$")
# §7 gives three actor shapes, and §5.1 reuses them for `sources[].author`. The
# spec's own example (`author: team:ga4-docs`) shows the `<prefix>:<id>` family is
# open, so this is deliberately not a whitelist — it catches the one failure that
# is silent and costly: a near-miss of `human:`, which §5.3 keys trust tiers off.
# `human/dana` or `Human:dana` reads as an agent and downgrades the tier with no
# other symptom.
ACTOR_SHAPE = re.compile(r"^(?:[^\s:/]+:\S+|\S+/\S+)$")
# Anything that opens with human/process in any case — `Human:dana` is the worst
# of these, since it satisfies the generic `<prefix>:<id>` shape and so looks
# entirely well-formed while §5.3 reads it as an agent. The lookahead keeps
# `humanoid_agent/v1` out: only a non-identifier boundary makes it a near-miss.
ACTOR_HUMANISH = re.compile(r"^(?:human|process)(?![A-Za-z0-9_])", re.I)
FENCE = re.compile(r"^(```|~~~)")
# markdown link target capture: [text](target) — ignores images ![...]
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CITATIONS = re.compile(r"^#{1,6}[ \t]+Citations[ \t]*$", re.M)
# a footnote *reference* in the body; the definition line `[^id]: …` matches too,
# which is harmless — both carry the same label, the join key into `sources`.
FOOTNOTE = re.compile(r"\[\^([^\]\s]+)\]")

# --migrate only. `timestamp` is a top-level key (§4.1), so anchor at column 0 —
# an indented one belongs to something else and must not be hoisted.
TIMESTAMP = re.compile(r"^timestamp:[ \t]*(.+?)[ \t]*$", re.M)
HEADING = re.compile(r"^#{1,6}[ \t]", re.M)
# same shape as LINK above, plus the link text — a citation written with a title
# attribute, `[Src](url "Title")`, must not be dropped: the section is deleted
# wholesale once anything parses, so a miss here is silent data loss.
MD_LINK = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
OKF_VERSION_LINE = re.compile(r"^(okf_version:[ \t]*)[\"']?0\.1[\"']?[ \t]*$", re.M)
# True, and it keeps the concept correctly `unverified` under §5.3: who wrote the
# content before `generated` existed is not recoverable, and inventing a `human:`
# actor would fake a review that never happened.
MIGRATE_ACTOR = "process:okf-migrate"


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


def _read_text(path: Path, rel: str, report: Report) -> str | None:
    """Read a concept/index/log file, reporting (not raising) on a bad file.

    A binary or non-UTF-8 `.md` file must fail as a per-file error, not crash
    the whole validation run.
    """
    try:
        return path.read_text(encoding="utf-8").lstrip("﻿")
    except (UnicodeDecodeError, OSError) as exc:
        report.err(rel, f"cannot read file: {exc}")
        return None


def check_computation(meta: dict, path: Path, bundle: Path, rel: str, report: Report) -> None:
    """§10.2 — the Attested Computation contract, including its path-valued fields.

    `computation`, `executor.resource` and `attester.resource` name files (§6.2).
    They are exactly the pointer that rots: the concept keeps validating while the
    script it names moves or disappears. A target outside the bundle is legitimate
    and unverifiable from here, so only bundle-relative paths are resolved.
    """
    if not str(meta.get("runtime", "")).strip():
        report.warn(rel, "§10.2 an Attested Computation concept requires `runtime`")
    fields = [("computation", meta.get("computation"))]
    for key in ("executor", "attester"):
        block = meta.get(key)
        if isinstance(block, dict):
            fields.append((f"{key}.resource", block.get("resource")))
    for where, target in fields:
        if target is None:
            continue
        t = str(target).strip()
        if not t or re.match(r"^[a-z][a-z0-9+.-]*://", t) or t.startswith("mailto:"):
            continue
        candidate = (bundle / t.lstrip("/")) if t.startswith("/") else (path.parent / t)
        try:
            inside = candidate.resolve().is_relative_to(bundle.resolve())
        except OSError:
            inside = False
        if inside and not candidate.exists():
            report.warn(rel, f"§6.2 `{where}` points at `{t}`, which does not exist")


def check_concept(path: Path, rel: str, bundle: Path, report: Report) -> None:
    report.concepts += 1
    text = _read_text(path, rel, report)
    if text is None:
        return
    raw, body = split_frontmatter(text)
    if raw is None:
        report.err(rel, "§11.1 no parseable YAML frontmatter block")
        return
    try:
        meta = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        report.err(rel, f"§11.1 frontmatter is not valid YAML: {exc}".replace("\n", " "))
        return
    if not isinstance(meta, dict):
        report.err(rel, "§11.1 frontmatter must be a YAML mapping")
        return
    type_val = meta.get("type")
    if not (isinstance(type_val, str) and type_val.strip()):
        report.err(rel, "§11.2 missing or empty required `type` field")
    for key in RECOMMENDED:
        if key not in meta:
            report.warn(rel, f"recommended field `{key}` is absent (§4.1)")
    check_trust(meta, rel, report)
    check_lifecycle(meta, rel, report)
    check_sources(meta, body, rel, report)
    if isinstance(type_val, str) and type_val.strip() == "Attested Computation":
        check_computation(meta, path, bundle, rel, report)


def check_actor(value, where: str, rel: str, report: Report) -> None:
    """§7 — the actor convention shared by `generated.by`, `verified[].by` and
    `sources[].author`."""
    actor = str(value).strip()
    if not actor:
        return
    if ACTOR_HUMANISH.match(actor) and not actor.startswith(("human:", "process:")):
        report.warn(rel, f"§7 `{where}` `{actor}` is a near-miss of "
                         f"`human:`/`process:` — §5.3 keys trust tiers off that exact "
                         f"lowercase prefix, so this silently reads as an agent")
    elif not ACTOR_SHAPE.match(actor):
        report.warn(rel, f"§7 `{where}` `{actor}` matches no actor shape "
                         f"(`human:<id>`, `process:<id>`, or `<producer>/<version>`)")


def check_instant(value, where: str, rel: str, report: Report) -> None:
    """§5.2 — `at` values are RFC 3339; a date-only value is tolerated."""
    if value is not None and not RFC3339.match(str(value).strip()):
        report.warn(rel, f"§5.2 `{where}` `{value}` is not an RFC 3339 timestamp")


def check_trust(meta: dict, rel: str, report: Report) -> None:
    """§5.2 — `generated` / `verified`, with the v0.1 `timestamp` fallback."""
    gen = meta.get("generated")
    if gen is None:
        if "timestamp" in meta:
            report.warn(rel, "legacy v0.1 `timestamp`: v0.2 records the last content "
                             "change as `generated: {by, at}` (§13.1)")
        else:
            report.warn(rel, "recommended field `generated` is absent (§5.2)")
    elif not isinstance(gen, dict):
        report.warn(rel, "§5.2 `generated` must be a mapping with `by` and `at`")
    elif not str(gen.get("by", "")).strip():
        report.warn(rel, "§5.2 `generated.by` is required within `generated`")
    else:
        check_actor(gen["by"], "generated.by", rel, report)
        check_instant(gen.get("at"), "generated.at", rel, report)

    ver = meta.get("verified")
    if ver is None:
        return
    # A bare mapping is one verification event — consumers MUST treat it as a
    # one-element list (§5.2), so normalize before checking the entries.
    entries = [ver] if isinstance(ver, dict) else ver
    if not isinstance(entries, list):
        report.warn(rel, "§5.2 `verified` must be a `{by, at}` mapping or a list of them")
        return
    for i, entry in enumerate(entries):
        if not (isinstance(entry, dict) and str(entry.get("by", "")).strip()):
            report.warn(rel, "§5.2 every `verified` entry needs a `by` actor")
            continue
        check_actor(entry["by"], f"verified[{i}].by", rel, report)
        check_instant(entry.get("at"), f"verified[{i}].at", rel, report)


def check_lifecycle(meta: dict, rel: str, report: Report) -> None:
    """§5.4 / §5.5 — `status` and `stale_after`."""
    status = meta.get("status")
    if status is not None and status not in STATUS_VALUES:
        report.warn(rel, f"§5.4 unknown `status` `{status}` (expected "
                         f"{'|'.join(sorted(STATUS_VALUES))})")
    stale = meta.get("stale_after")
    # PyYAML resolves an unquoted `2026-09-23` to a date object; str() round-trips
    # it back to the ISO form, so both spellings check identically.
    if stale is not None and not ISO_DATE.match(str(stale)):
        report.warn(rel, f"§5.5 `stale_after` `{stale}` is not an absolute YYYY-MM-DD date")


def check_window(window, where: str, rel: str, report: Report) -> None:
    """§5.1 — a `usage_window` is a `{from, to}` pair of absolute dates."""
    if window is None:
        return
    if not isinstance(window, dict):
        report.warn(rel, f"§5.1 `{where}` `usage_window` must be a `{{from, to}}` mapping")
        return
    for bound in ("from", "to"):
        value = window.get(bound)
        if value is None:
            report.warn(rel, f"§5.1 `{where}` `usage_window` is missing `{bound}`")
        elif not ISO_DATE.match(str(value)):
            report.warn(rel, f"§5.1 `{where}` `usage_window.{bound}` `{value}` "
                             f"is not an absolute YYYY-MM-DD date")


def check_sources(meta: dict, body: str, rel: str, report: Report) -> None:
    """§5.1 — the `sources` provenance family and its footnote join keys."""
    if CITATIONS.search(body):
        report.warn(rel, "legacy v0.1 `# Citations` body list: v0.2 records provenance "
                         "in the `sources` frontmatter (§13.1)")
    srcs = meta.get("sources")
    if srcs is None:
        return
    if not isinstance(srcs, list):
        report.warn(rel, "§5.1 `sources` must be a list of entries")
        return
    ids = set()
    for i, src in enumerate(srcs):
        if not isinstance(src, dict):
            report.warn(rel, f"§5.1 `sources[{i}]` must be a mapping")
            continue
        if not str(src.get("resource", "")).strip():
            report.warn(rel, f"§5.1 `sources[{i}]` is missing the required `resource`")
        if "id" in src:
            ids.add(str(src["id"]))
        if src.get("author") is not None:
            check_actor(src["author"], f"sources[{i}].author", rel, report)
        # §5.1 — `usage_count` is framed by a `usage_window`, written once as a
        # sibling of `sources` or overridden on the entry. Without one the count
        # is a number with no units, and the spec asks consumers to read it as
        # liveness and trend rather than a score.
        window = src.get("usage_window", meta.get("usage_window"))
        if src.get("usage_count") is not None and window is None:
            report.warn(rel, f"§5.1 `sources[{i}].usage_count` has no `usage_window` "
                             f"framing it (a sibling of `sources`, or on the entry)")
        check_window(window, f"sources[{i}]", rel, report)
        last_mod = src.get("last_modified")
        if last_mod is not None and not ISO_DATE.match(str(last_mod)):
            report.warn(rel, f"§5.1 `sources[{i}].last_modified` `{last_mod}` is not YYYY-MM-DD")
    # Attribution joins on the label, not on position (§5.1) — a footnote whose
    # label names no source silently attributes a claim to nothing.
    for label in sorted(set(FOOTNOTE.findall(body)) - ids):
        report.warn(rel, f"§5.1 footnote `[^{label}]` matches no `sources[].id`")


def check_index(path: Path, rel: str, is_root: bool, report: Report) -> None:
    report.indexes += 1
    text = _read_text(path, rel, report)
    if text is None:
        return
    raw, _ = split_frontmatter(text)
    if raw is not None:
        if not is_root:
            report.warn(rel, "§8 index.md should contain no frontmatter")
        else:
            try:
                meta = yaml.safe_load(raw) or {}
            except yaml.YAMLError:
                report.warn(rel, "§12 root index.md frontmatter is not valid YAML")
                meta = {}
            extra = set(meta) - {"okf_version"}
            if extra:
                report.warn(rel, f"§12 root index.md frontmatter may only carry `okf_version` (found {sorted(extra)})")
            declared = meta.get("okf_version")
            if declared is not None and str(declared) != OKF_VERSION:
                report.warn(rel, f"§12 bundle declares `okf_version: \"{declared}\"`; "
                                 f"checked against v{OKF_VERSION}")


def check_log(path: Path, rel: str, report: Report) -> None:
    report.logs += 1
    text = _read_text(path, rel, report)
    if text is None:
        return
    raw, _ = split_frontmatter(text)
    if raw is not None:
        report.warn(rel, "§9 log.md should contain no frontmatter")
    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            if not ISO_DATE.match(heading):
                report.warn(rel, f"§9 date heading `{heading}` is not ISO 8601 YYYY-MM-DD")


def collect_link_targets(path: Path) -> list[str]:
    # Unreadable files are already reported as a per-file error by
    # check_concept/check_index/check_log; fail soft here to avoid a duplicate
    # error and a crash on the second read pass.
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
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
    """Broken bundle-internal links are warnings only (§6.1)."""
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
                report.warn(rel, f"cross-link target not found: `{target}` (tolerated under §6.1)")


def citations_to_sources(raw: str, body: str) -> tuple[str, str]:
    """Hoist a v0.1 `# Citations` list into the `sources` family (§5.1, §13.1)."""
    heading = CITATIONS.search(body)
    if heading is None:
        return raw, body
    rest = body[heading.end():]
    nxt = HEADING.search(rest)
    section, tail = (rest[:nxt.start()], rest[nxt.start():]) if nxt else (rest, "")
    entries = MD_LINK.findall(section)
    if not entries:
        return raw, body  # nothing extractable — leave it and keep warning
    # json.dumps gives a correctly escaped YAML double-quoted scalar for free.
    block = "sources:\n" + "".join(
        f"  - resource: {json.dumps(url)}\n    title: {json.dumps(title)}\n"
        for title, url in entries)
    kept = body[:heading.start()].rstrip("\n")
    return raw + block, kept + ("\n\n" + tail if tail else "\n")


def migrate_text(text: str, is_root_index: bool) -> str | None:
    """Rewrite one file's v0.1 constructs to v0.2. None when nothing changes.

    Textual on purpose: dumping the frontmatter back through PyYAML would flatten
    comments, key order and quoting across every file in the bundle. Each branch
    is guarded on the v0.2 key already being present, so a half-migrated bundle
    converges instead of growing a duplicate key that PyYAML then refuses to load.
    """
    raw, body = split_frontmatter(text)
    if raw is None:
        return None
    if is_root_index:
        new_raw = OKF_VERSION_LINE.sub(rf'\g<1>"{OKF_VERSION}"', raw, count=1)
        return None if new_raw == raw else f"---\n{new_raw}---\n{body}"
    try:
        meta = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None
    new_raw, new_body = raw, body
    if "generated" not in meta:
        new_raw = TIMESTAMP.sub(
            lambda m: f"generated:\n  by: {MIGRATE_ACTOR}\n  at: {m.group(1)}",
            new_raw, count=1)
    if "sources" not in meta:
        new_raw, new_body = citations_to_sources(new_raw, new_body)
    if (new_raw, new_body) == (raw, body):
        return None
    return f"---\n{new_raw}---\n{new_body}"


def migrate(bundle: Path) -> list[str]:
    """Migrate a bundle in place. Returns the relative paths actually rewritten."""
    changed = []
    for path in sorted(p for p in bundle.rglob("*.md") if p.is_file()):
        rel = path.relative_to(bundle).as_posix()
        if path.name == "log.md":
            continue
        try:
            # Universal newlines on purpose: a CRLF bundle is rewritten with the
            # platform ending, consistently. Passing newline="" to preserve them
            # exactly would leave a stray \r inside every `$`-anchored capture
            # below, so those patterns need hardening first if byte fidelity is
            # ever required.
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        is_root_index = path.name == "index.md" and path.parent == bundle
        if path.name == "index.md" and not is_root_index:
            continue
        new = migrate_text(text.lstrip("﻿"), is_root_index)
        if new is not None and new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(rel)
    return changed


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
            check_concept(path, rel, bundle, report)
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
    ap = argparse.ArgumentParser(description=f"Validate an OKF v{OKF_VERSION} bundle.")
    ap.add_argument("bundle", type=Path, help="path to the bundle directory")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--max-warnings", type=int, default=None, metavar="N",
                    help="fail if warnings exceed N (--strict is the N=0 case)")
    ap.add_argument("--migrate", action="store_true",
                    help="rewrite v0.1 constructs to v0.2 in place, then validate")
    ap.add_argument("--json", action="store_true", help="emit a JSON report")
    args = ap.parse_args()

    if not args.bundle.is_dir():
        print(f"error: {args.bundle} is not a directory", file=sys.stderr)
        return 2

    migrated = migrate(args.bundle) if args.migrate else []

    r = validate(args.bundle)
    conformant = not r.errors
    max_warn = 0 if args.strict else args.max_warnings
    failed = bool(r.errors) or (max_warn is not None and len(r.warnings) > max_warn)

    if args.json:
        print(json.dumps({
            "bundle": str(args.bundle),
            "conformant": conformant,
            "passed": not failed,
            "counts": {"concepts": r.concepts, "indexes": r.indexes, "logs": r.logs},
            "errors": r.errors,
            "warnings": r.warnings,
            "migrated": migrated,
        }, indent=2))
        return 0 if not failed else 1

    if args.migrate:
        for rel in migrated:
            print(f"  \033[36m→ migrated\033[0m  {rel}")
        print(f"  migrated {len(migrated)} file(s) to v{OKF_VERSION}"
              + (f", `generated.by` recorded as `{MIGRATE_ACTOR}`" if migrated else ""))
        if migrated:
            print("  note: per-claim attribution (the `[^id]` footnotes of §5.1) is not"
                  " recoverable from a v0.1 `# Citations` list — sources moved up, but"
                  " which claim cited which was never encoded.")

    print(f"OKF v{OKF_VERSION} conformance — {args.bundle}")
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
