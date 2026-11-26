#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Deterministic conformance checker for Open Knowledge Format (OKF) v0.3.

Implements the §11.1 conformance rules:
  1. Each frontmatter block in a `.md` file under the bundle root parses as a YAML
     mapping (§4). Duplicate keys at any level are rejected (§4).
  2. Reserved filenames (`index.md`, `log.md`) follow §8 / §9 when present.

Those are the hard errors. A `.md` file with no frontmatter, or none with a
non-empty `type`, is not a concept (§3.2): it is skipped with a warning and never
makes the bundle non-conformant, so `README.md` and `AGENTS.md` may live in a
bundle. Everything else the spec marks as soft guidance: reported as warnings,
never fatal unless `--strict` is given. In particular broken cross-links are NOT
errors: the spec requires consumers to tolerate them (§6.1).

Bundles that declare `okf_version` 0.2 or earlier (or none) are read with the §12.1
fallbacks: a bare path field that only resolves from the bundle root is accepted
with a warning, and the v0.1 constructs (`timestamp`, a body `# Citations` list)
are warned about with their replacements (Appendix B), never errors. `--migrate`
rewrites both to v0.3 in place, textually, so `--strict` has a door and not just
a wall.

Run:  uv run scripts/okf_validate.py <bundle-dir>
        [--strict | --max-warnings N] [--migrate] [--json]
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

import yaml

OKF_VERSION = "0.3"
RESERVED = {"index.md", "log.md"}
# `resource` is intentionally excluded: the spec (§4.1) states it is absent for
# concepts describing abstract ideas, so flagging it produces false noise.
RECOMMENDED = ("title", "description", "tags")
STATUS_VALUES = {"draft", "stable", "deprecated"}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# §5: a timestamp is a date-only `full-date` (the start of that day in UTC) or an
# RFC 3339 `date-time`, which REQUIRES an offset (`Z` or `±HH:MM`). Nothing else is
# valid, including a date-time without an offset. PyYAML resolves an unquoted
# timestamp to a datetime whose str() separates with a space, so both spellings pass.
_DATE = r"\d{4}-\d{2}-\d{2}"
TS_VALID = re.compile(
    rf"^{_DATE}(?:[Tt ]\d{{2}}:\d{{2}}:\d{{2}}(?:\.\d+)?(?:[Zz]|[+-]\d{{2}}:\d{{2}}))?$")
TS_NO_OFFSET = re.compile(rf"^{_DATE}[Tt ]\d{{2}}:\d{{2}}(?::\d{{2}}(?:\.\d+)?)?$")
# A URI scheme (RFC 3986) makes a value absolute rather than a bundle path (§6).
URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
# §8.1 keys of the bundle-root index.md, plus this plugin's own: the Stop hook reads
# its opt-in flag (`upkeep`) and nested-repo switch (`recursive`) from here, so an
# enforced-mode bundle would otherwise fail its own `--strict` run. `x-` keys are
# extensions (§4.1).
ROOT_KEYS = {"okf_version", "title", "description", "license", "upkeep", "recursive"}
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
ACTOR_HUMANISH = re.compile(r"^(?:human|process)(?![A-Za-z0-9_])", re.IGNORECASE)
FENCE = re.compile(r"^(```|~~~)")
# markdown link target capture: [text](target) — ignores images ![...]
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CITATIONS = re.compile(r"^#{1,6}[ \t]+Citations[ \t]*$", re.MULTILINE)
# a footnote *reference* in the body; the definition line `[^id]: …` matches too,
# which is harmless — both carry the same label, the join key into `sources`.
FOOTNOTE = re.compile(r"\[\^([^\]\s]+)\]")
# CommonMark recognizes no footnote inside code (#56): a regex class such as
# `[^#?/]` in a code span or a fence is code. A fence opens with 3+ backticks or
# tildes (up to 3 spaces in) and closes on a run of the same char at least as long.
# A code span closes on a backtick run of exactly its opening length, and may wrap
# lines within a paragraph but never crosses a blank line.
FENCE_RUN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)((?:(?!\n[ \t]*\n).)+?)(?<!`)\1(?!`)", re.DOTALL)


# --migrate only. `timestamp` is a top-level key (§4.1), so anchor at column 0 —
# an indented one belongs to something else and must not be hoisted.
TIMESTAMP = re.compile(r"^timestamp:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
HEADING = re.compile(r"^#{1,6}[ \t]", re.MULTILINE)
# same shape as LINK above, plus the link text — a citation written with a title
# attribute, `[Src](url "Title")`, must not be dropped: the section is deleted
# wholesale once anything parses, so a miss here is silent data loss.
MD_LINK = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
OKF_VERSION_LINE = re.compile(r"^(okf_version:[ \t]*)[\"']?0\.[12][\"']?[ \t]*$", re.MULTILINE)
# A block-style path field value: `key: value`, optionally quoted, optionally
# followed by a comment. Group 1 = up to the value, 2 = quote char, 3 = value.
PATH_VALUE = re.compile(
    r"""^(?P<head>[ \t]*[A-Za-z_]+:[ \t]*)(?:(?P<q>["'])(?P<qv>.*?)(?P=q)|"""
    r"""(?P<bv>[^\s"'#{\[|>&*!](?:\S|[ \t]+(?!#))*))(?P<tail>[ \t]*(?:#.*)?)$""")
TOP_KEY = re.compile(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$")
PATH_BLOCKS = ("executor", "attester")
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


class DuplicateKeyError(yaml.constructor.ConstructorError):
    """A mapping repeats a key. YAML 1.2 requires unique keys (§4)."""


class UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys at every nesting level.

    PyYAML silently keeps the last value, so two readers (one strict, one not)
    would see different frontmatter. Unknown tags still fail as in `safe_load`.
    """

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            seen = set()
            for key_node, _ in node.value:
                if key_node.tag == "tag:yaml.org,2002:merge":
                    continue  # `<<` is expanded by the parent class, not a real key
                key = self.construct_object(key_node, deep=True)
                try:
                    duplicate = key in seen
                    seen.add(key)
                except TypeError:
                    break  # unhashable key: the parent class reports it
                if duplicate:
                    raise DuplicateKeyError(None, None, f"duplicate key `{key}`",
                                            key_node.start_mark)
        return super().construct_mapping(node, deep=deep)


def load_frontmatter(raw: str):
    """Parse a frontmatter block with duplicate-key detection (§4)."""
    return yaml.load(raw, Loader=UniqueKeyLoader)  # a SafeLoader subclass: no arbitrary objects


def is_empty(value) -> bool:
    """§11.2 rule 1: null, an empty string and an empty list read as an absent key."""
    return value is None or value == [] or (isinstance(value, str) and not value.strip())


def iter_bundle_md(bundle: Path) -> list[Path]:
    """The `.md` files that belong to the bundle (§3.2).

    Rule 4: anything whose path RELATIVE to the root has a component starting with
    `.` is not part of the bundle (the root itself may be `.okf`). Rule 5: a symlink
    that resolves outside the root is not followed. Pruning dot-directories during
    the walk also avoids descending into `.git` and friends.
    """
    root = bundle.resolve()
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(bundle):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if name.startswith(".") or not name.endswith(".md"):
                continue
            p = Path(dirpath) / name
            try:
                inside = p.resolve().is_relative_to(root)
            except OSError:
                inside = False
            if inside and p.is_file():
                found.append(p)
    return sorted(found)


def path_status(value: str, base_dir: Path, bundle: Path) -> tuple[str, str]:
    """§6 resolution of a link target or path field value.

    Returns (status, bare) where `bare` is the value without its `#fragment`, and
    status is one of:
      external   a URI scheme, empty, or resolves outside the bundle root: not ours
      ok         resolves to an existing file or directory
      root_only  missing from the base directory but present from the bundle root
                 (the §6.2 / §12.1 fallback)
      missing    resolves inside the bundle and does not exist
    """
    bare = value.strip().split("#", 1)[0]
    if not bare or URI_SCHEME.match(bare):
        return "external", bare
    decoded = unquote(bare)
    root = bundle.resolve()

    def locate(candidate: Path) -> Path | None:
        try:
            resolved = candidate.resolve()
        except OSError:
            return None
        return resolved if resolved.is_relative_to(root) else None

    if decoded.startswith("/"):
        target = locate(bundle / decoded.lstrip("/"))
        if target is None:
            return "external", bare
        return ("ok" if target.exists() else "missing"), bare
    target = locate(base_dir / decoded)
    if target is None:
        return "external", bare
    if target.exists():
        return "ok", bare
    from_root = locate(bundle / decoded)
    return ("root_only" if from_root is not None and from_root.exists() else "missing"), bare


def declared_version(bundle: Path):
    """The `okf_version` the bundle-root index.md declares, or None."""
    try:
        text = (bundle / "index.md").read_text(encoding="utf-8").lstrip("﻿")
        raw, _ = split_frontmatter(text)
        meta = load_frontmatter(raw) if raw is not None else None
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return meta.get("okf_version") if isinstance(meta, dict) else None


def is_legacy_version(declared) -> bool:
    """True when the bundle declares 0.2 or earlier, or declares no version (§12.1)."""
    if declared is None:
        return True
    try:
        major, minor = (int(p) for p in str(declared).split(".")[:2])
    except ValueError:
        return False
    return (major, minor) <= (0, 2)


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


def check_timestamp(value, where: str, rel: str, report: Report) -> None:
    """§5 — a timestamp is `YYYY-MM-DD` or a date-time WITH an offset (`Z`/`±HH:MM`).

    PyYAML turns an unquoted one into a native object: a date is a valid date-only
    value, a datetime is valid only when it carries a timezone.
    """
    if is_empty(value):
        return
    if isinstance(value, datetime.datetime):
        problem = None if value.tzinfo is not None else "no_offset"
    elif isinstance(value, datetime.date):
        problem = None
    else:
        text = str(value).strip()
        problem = (None if TS_VALID.match(text)
                   else "no_offset" if TS_NO_OFFSET.match(text) else "invalid")
    if problem == "no_offset":
        report.warn(rel, f"§5 `{where}` `{value}` lacks the required offset (`Z` or "
                         f"`±HH:MM`): a date-time without one is invalid, so add it or "
                         f"write a date-only `YYYY-MM-DD`")
    elif problem:
        report.warn(rel, f"§5 `{where}` `{value}` is not an RFC 3339 timestamp "
                         f"(`YYYY-MM-DD`, or a date-time with `Z` or `±HH:MM`)")


def check_path_field(where: str, value, path: Path, bundle: Path, rel: str,
                     report: Report, legacy: bool) -> None:
    """§6.2 — a path field must resolve (§6) to something in the bundle.

    Fields naming files are exactly the pointers that rot: the concept keeps
    validating while the file it names moves or disappears. URIs and targets
    outside the bundle root are external and unverifiable from here. A bare value
    that exists only relative to the bundle root is the v0.2 reading (§6.2, §12.1):
    tolerated for a bundle that declares 0.2 or earlier, with a nudge to `/`.
    """
    if not isinstance(value, str):
        return
    status, bare = path_status(value, path.parent, bundle)
    if status in ("external", "ok"):
        return
    if status == "root_only" and legacy:
        report.warn(rel, f"§6.2 `{where}` `{bare}` resolves only from the bundle root "
                         f"(v0.2 reading): write `/{bare}`")
        return
    hint = f" (did you mean `/{bare}`?)" if status == "root_only" else ""
    report.warn(rel, f"§6.2 `{where}` points at `{bare}`, which does not exist{hint}")


def check_computation(meta: dict, path: Path, bundle: Path, rel: str, report: Report,
                      legacy: bool) -> None:
    """§10.2 — the Attested Computation contract."""
    if not str(meta.get("runtime", "")).strip():
        report.warn(rel, "§10.2 an Attested Computation concept requires `runtime`")
    params = meta.get("parameters")
    if not is_empty(params):
        entries = [params] if isinstance(params, dict) else params  # §11.2 rule 2
        if not isinstance(entries, list):
            report.warn(rel, "§10.2 `parameters` must be a list of `{name, type, required}`")
        else:
            for i, entry in enumerate(entries):
                missing = [k for k in ("name", "type")
                           if not (isinstance(entry, dict) and not is_empty(entry.get(k)))]
                if missing:
                    report.warn(rel, f"§10.2 `parameters[{i}]` needs `name` and `type` "
                                     f"(missing {', '.join(f'`{k}`' for k in missing)})")
    check_path_field("computation", meta.get("computation"), path, bundle, rel, report, legacy)
    for key in PATH_BLOCKS:
        block = meta.get(key)
        if isinstance(block, dict):
            check_path_field(f"{key}.resource", block.get("resource"), path, bundle,
                             rel, report, legacy)


def check_concept(path: Path, rel: str, bundle: Path, report: Report, *,
                  legacy: bool = True) -> None:
    """Check one non-reserved `.md`. `legacy` is whether the bundle declares okf_version
    0.2 or earlier (or none), which enables the §12.1 path fallback."""
    text = _read_text(path, rel, report)
    if text is None:
        return
    raw, body = split_frontmatter(text)
    if raw is None:
        report.warn(rel, "§3.2 no frontmatter: skipped as a non-concept "
                         "(add frontmatter with a `type` to make it one)")
        return
    try:
        meta = load_frontmatter(raw)
    except DuplicateKeyError as exc:
        report.err(rel, f"§4 frontmatter has a {exc.problem} (YAML 1.2 requires unique keys)")
        return
    except yaml.YAMLError as exc:
        report.err(rel, f"§11.1 frontmatter is not valid YAML: {exc}".replace("\n", " "))
        return
    if meta is None:
        meta = {}  # an empty block parses to null: it is a mapping with no `type`
    if not isinstance(meta, dict):
        report.err(rel, "§11.1 frontmatter must be a YAML mapping")
        return
    type_val = meta.get("type")
    if not (isinstance(type_val, str) and type_val.strip()):
        report.warn(rel, "§3.2 frontmatter has no non-empty `type`: skipped as a "
                         "non-concept")
        return
    report.concepts += 1
    for key in RECOMMENDED:
        if key not in meta:
            report.warn(rel, f"recommended field `{key}` is absent (§4.1)")
    check_trust(meta, rel, report)
    check_lifecycle(meta, path, bundle, rel, report, legacy)
    check_sources(meta, body, rel, report)
    if type_val.strip() == "Attested Computation":
        check_computation(meta, path, bundle, rel, report, legacy)


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


def check_trust(meta: dict, rel: str, report: Report) -> None:
    """§5.2 — `generated` / `verified`, with the v0.1 `timestamp` fallback."""
    gen = meta.get("generated")
    if is_empty(gen):
        if "timestamp" in meta:
            report.warn(rel, "legacy v0.1 `timestamp`: v0.2 and later record the last "
                             "content change as `generated: {by, at}` (Appendix B)")
        else:
            report.warn(rel, "recommended field `generated` is absent (§5.2)")
    elif not isinstance(gen, dict):
        report.warn(rel, "§5.2 `generated` must be a mapping with `by` and `at`")
    elif not str(gen.get("by", "")).strip():
        report.warn(rel, "§5.2 `generated.by` is required within `generated`")
    else:
        check_actor(gen["by"], "generated.by", rel, report)
        check_timestamp(gen.get("at"), "generated.at", rel, report)

    ver = meta.get("verified")
    if is_empty(ver):
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
        if is_empty(entry.get("at")):
            report.warn(rel, f"§5.2 `verified[{i}]` has no `at`: both `by` and `at` are "
                             f"REQUIRED, so consumers ignore this event")
        else:
            check_timestamp(entry["at"], f"verified[{i}].at", rel, report)


def check_lifecycle(meta: dict, path: Path, bundle: Path, rel: str, report: Report,
                    legacy: bool) -> None:
    """§5.4 / §5.5 — `status`, `superseded_by` and `stale_after`. A concept is stale
    when `now >= stale_after`."""
    status = meta.get("status")
    if not is_empty(status) and status not in STATUS_VALUES:
        report.warn(rel, f"§5.4 unknown `status` `{status}` (expected "
                         f"{'|'.join(sorted(STATUS_VALUES))}): consumers treat it as "
                         f"not current")
    superseded = meta.get("superseded_by")
    if not is_empty(superseded):
        if status != "deprecated":
            report.warn(rel, "§5.4 `superseded_by` has meaning only with `status: deprecated`")
        check_path_field("superseded_by", superseded, path, bundle, rel, report, legacy)
    check_timestamp(meta.get("stale_after"), "stale_after", rel, report)


def check_window(window, where: str, rel: str, report: Report) -> None:
    """§5.1 — a `usage_window` is a `{from, to}` pair of timestamps (§5)."""
    if is_empty(window):
        return
    if not isinstance(window, dict):
        report.warn(rel, f"§5.1 `{where}` `usage_window` must be a `{{from, to}}` mapping")
        return
    for bound in ("from", "to"):
        value = window.get(bound)
        if is_empty(value):
            report.warn(rel, f"§5.1 `{where}` `usage_window` is missing `{bound}`")
        else:
            check_timestamp(value, f"{where}.usage_window.{bound}", rel, report)


def strip_code(body: str) -> str:
    """The body with fenced blocks and inline code spans removed."""
    kept: list[str] = []
    fence = ""
    for line in body.splitlines():
        m = FENCE_RUN.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                    and not line[m.end():].strip():
                fence = ""
            continue
        if m and not (m.group(1)[0] == "`" and "`" in line[m.end():]):
            fence = m.group(1)
            continue
        kept.append(line)
    return CODE_SPAN.sub("", "\n".join(kept))


def check_sources(meta: dict, body: str, rel: str, report: Report) -> None:
    """§5.1 — the `sources` provenance family and its footnote join keys."""
    if CITATIONS.search(body):
        report.warn(rel, "legacy v0.1 `# Citations` body list: v0.2 and later record "
                         "provenance in the `sources` frontmatter (Appendix B)")
    srcs = meta.get("sources")
    if is_empty(srcs):
        return
    if isinstance(srcs, dict):  # §11.2 rule 2: one item is a list of one
        srcs = [srcs]
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
        check_actor(src.get("author", ""), f"sources[{i}].author", rel, report)
        # §5.1 — `usage_count` is framed by a `usage_window`, written once as a
        # sibling of `sources` or overridden on the entry. Without one the count
        # is a number with no units, and the spec asks consumers to read it as
        # liveness and trend rather than a score.
        window = src.get("usage_window", meta.get("usage_window"))
        if src.get("usage_count") is not None and is_empty(window):
            report.warn(rel, f"§5.1 `sources[{i}].usage_count` has no `usage_window` "
                             f"framing it (a sibling of `sources`, or on the entry)")
        check_window(window, f"sources[{i}]", rel, report)
        check_timestamp(src.get("last_modified"), f"sources[{i}].last_modified", rel, report)
    # Attribution joins on the label, not on position (§5.1) — a footnote whose
    # label names no source silently attributes a claim to nothing.
    # Code is skipped: a regex class in a code span is not a footnote (#56).
    for label in sorted(set(FOOTNOTE.findall(strip_code(body))) - ids):
        report.warn(rel, f"§5.1 footnote `[^{label}]` matches no `sources[].id`")


def check_index(path: Path, rel: str, is_root: bool, report: Report) -> None:
    report.indexes += 1
    text = _read_text(path, rel, report)
    if text is None:
        return
    raw, _ = split_frontmatter(text)
    if raw is None:
        return
    if not is_root:
        report.warn(rel, "§8 index.md should contain no frontmatter")
        return
    try:
        meta = load_frontmatter(raw)
    # §11.1 rule 1 covers every frontmatter block, the root index's included, so a
    # broken one is non-conformant here just as in a concept.
    except DuplicateKeyError as exc:
        report.err(rel, f"§4 frontmatter has a {exc.problem} (YAML 1.2 requires unique keys)")
        return
    except yaml.YAMLError as exc:
        report.err(rel, f"§11.1 root index.md frontmatter is not valid YAML: {exc}".replace("\n", " "))
        return
    if meta is None:
        return
    if not isinstance(meta, dict):
        report.err(rel, "§11.1 root index.md frontmatter must be a YAML mapping")
        return
    extra = sorted(k for k in meta if not (str(k) in ROOT_KEYS or str(k).startswith("x-")))
    if extra:
        report.warn(rel, f"§8.1 root index.md frontmatter has unknown key(s) {extra}: "
                         f"name extensions `x-<producer>-<name>` (§4.1)")
    declared = meta.get("okf_version")
    if is_empty(declared):
        return
    if not isinstance(declared, str):
        report.warn(rel, f"§8.1 `okf_version` must be a quoted string: write "
                         f"`okf_version: \"{declared}\"`")
    if str(declared) != OKF_VERSION:
        report.warn(rel, f"§12.1 bundle declares `okf_version: \"{declared}\"`: checked "
                         f"against v{OKF_VERSION} with the §12.1 fallbacks applied for "
                         f"0.2 or earlier")


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
    """Broken bundle-internal links are warnings only (§6.1).

    A target resolving outside the bundle root is external (§6), never broken. One
    that exists is fine even when it is a skipped dot-path or a non-concept `.md`.
    """
    root = bundle.resolve()
    existing = {p.resolve() for p in md_files}
    for path in md_files:
        rel = path.relative_to(bundle).as_posix()
        for target in collect_link_targets(path):
            status, bare = path_status(target, path.parent, bundle)
            decoded = unquote(bare)
            if status == "external" or not decoded.endswith(".md"):
                continue
            # Case-sensitive membership, not `exists()`: paths are case-sensitive
            # (§6) and a case-insensitive filesystem would hide a wrong-case link.
            base = bundle if decoded.startswith("/") else path.parent
            resolved = (base / decoded.lstrip("/")).resolve()
            if resolved in existing:
                continue
            # A skipped dot-path is not in `existing` but is still a real file.
            if resolved.is_file() and any(
                    part.startswith(".") for part in resolved.relative_to(root).parts):
                continue
            report.warn(rel, f"cross-link target not found: `{target}` (tolerated under §6.1)")


def citations_to_sources(raw: str, body: str) -> tuple[str, str]:
    """Hoist a v0.1 `# Citations` list into the `sources` family (§5.1, Appendix B)."""
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


def root_prefix_path_fields(raw: str, path: Path, bundle: Path, with_computation: bool) -> str:
    """Prefix `/` to block-style path fields that only resolve from the bundle root.

    v0.2 resolved a bare path field from the bundle root, v0.3 from the file's own
    directory (§6, §6.2), so such a value must become `/<path>` to keep pointing at
    the same file. Only `key: value` lines are rewritten, quoting and trailing
    comments preserved. Flow-style mappings are left alone: the validator keeps
    warning about them, which is the prompt to fix them by hand.
    """
    top_keys = ("superseded_by", "computation") if with_computation else ("superseded_by",)
    blocks = PATH_BLOCKS if with_computation else ()
    block: str | None = None
    child_indent: str | None = None
    out: list[str] = []
    for line in raw.split("\n"):
        top = TOP_KEY.match(line)
        candidate = False
        if top:
            key, rest = top.groups()
            block = key if key in blocks and (not rest.strip() or rest.lstrip().startswith("#")) else None
            child_indent = None
            candidate = key in top_keys
        elif block and (m := re.match(r"^([ \t]+)resource:", line)):
            child_indent = m.group(1) if child_indent is None else child_indent
            candidate = m.group(1) == child_indent
        elif line and not line[0].isspace() and not line.startswith("#"):
            block = None
        m = PATH_VALUE.match(line) if candidate else None
        if m:
            value = m.group("qv") if m.group("q") else m.group("bv")
            if path_status(value, path.parent, bundle)[0] == "root_only":
                quote = m.group("q") or ""
                line = f"{m.group('head')}{quote}/{value}{quote}{m.group('tail')}"
        out.append(line)
    return "\n".join(out)


def migrate_text(text: str, is_root_index: bool, path: Path | None = None,
                 bundle: Path | None = None) -> str | None:
    """Rewrite one file's v0.1 / v0.2 constructs to v0.3. None when nothing changes.

    Textual on purpose: dumping the frontmatter back through PyYAML would flatten
    comments, key order and quoting across every file in the bundle. Each branch
    is guarded on the newer key already being present, so a half-migrated bundle
    converges instead of growing a duplicate key that PyYAML then refuses to load.
    `path` and `bundle` (both or neither) enable the path-field rewrite, which needs
    the filesystem to tell a root-relative value from a missing one.
    """
    raw, body = split_frontmatter(text)
    if raw is None:
        return None
    if is_root_index:
        new_raw = OKF_VERSION_LINE.sub(rf'\g<1>"{OKF_VERSION}"', raw, count=1)
        return None if new_raw == raw else f"---\n{new_raw}---\n{body}"
    try:
        meta = load_frontmatter(raw)
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None
    new_raw, new_body = raw, body
    if path is not None and bundle is not None:
        new_raw = root_prefix_path_fields(
            new_raw, path, bundle, meta.get("type") == "Attested Computation")
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
    for path in iter_bundle_md(bundle):
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
        new = migrate_text(text.lstrip("﻿"), is_root_index, path, bundle)
        if new is not None and new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(rel)
    return changed


def validate(bundle: Path) -> Report:
    report = Report()
    md_files = iter_bundle_md(bundle)
    legacy = is_legacy_version(declared_version(bundle))
    for path in md_files:
        rel = path.relative_to(bundle).as_posix()
        name = path.name
        if name == "index.md":
            check_index(path, rel, is_root=(path.parent == bundle), report=report)
        elif name == "log.md":
            check_log(path, rel, report)
        else:
            check_concept(path, rel, bundle, report, legacy=legacy)
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
                    help="rewrite v0.1 / v0.2 constructs to v0.3 in place, then validate")
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
