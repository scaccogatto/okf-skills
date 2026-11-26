#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Deterministic conformance checker for Open Knowledge Format (OKF) v0.3.

Implements the §11.1 conformance rules:
  1. Each frontmatter block in a `.md` file under the bundle root parses as a YAML
     mapping (§4). Duplicate keys at any level are rejected (§4), and so is a value
     PyYAML cannot build (an impossible date, nesting too deep to parse).
  2. Reserved filenames (`index.md`, `log.md`) follow §8 / §9 when present: an
     `index.md` below the bundle root has no frontmatter (§8), a `log.md` has no
     frontmatter and dates every `## ` heading as ISO 8601 `YYYY-MM-DD` (§9).

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

`--lint` adds this plugin's house style (warnings worded "okf-skills lint": missing
`title`, `description`, `tags`, `generated`). It is a convention, not spec, so it
is off by default and a concept with only `type` passes `--strict`.

Run:  uv run scripts/okf_validate.py <bundle-dir>
        [--strict | --max-warnings N] [--lint] [--migrate] [--json]
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
# §5: a timestamp is a date-only `full-date` (the start of that day in UTC) or an
# RFC 3339 `date-time`, which REQUIRES an offset (`Z` or `±HH:MM`). Nothing else is
# valid, including a date-time without an offset. The shape alone is not enough:
# `2099-02-30` and hour 24 match it, so a string must also parse to a real instant.
_DATE = r"\d{4}-\d{2}-\d{2}"
ISO_DATE = re.compile(_DATE)
TS_DATETIME = re.compile(rf"{_DATE}[Tt ](?:[01]\d|2[0-3]):\d{{2}}:\d{{2}}(?:\.\d+)?(?:[Zz]|[+-]\d{{2}}:\d{{2}})")
TS_NO_OFFSET = re.compile(rf"{_DATE}[Tt ]\d{{2}}:\d{{2}}(?::\d{{2}}(?:\.\d+)?)?")
# A URI scheme (RFC 3986) makes a value absolute rather than a bundle path (§6).
URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
# §8.1 keys of the bundle-root index.md. `x-` keys are extensions (§4.1), which
# covers this plugin's own Stop hook flags, `x-okf-skills-upkeep` and
# `x-okf-skills-recursive`.
ROOT_KEYS = {"okf_version", "title", "description", "license"}
# The Stop hook flags as first shipped. §4.1 reserves unprefixed keys for future OKF
# versions, so they are deprecated aliases: still read by the hook, warned about
# here, renamed by `--migrate`.
DEPRECATED_ROOT_KEYS = {"upkeep": "x-okf-skills-upkeep",
                        "recursive": "x-okf-skills-recursive"}
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
# markdown link target capture: [text](target) — ignores images ![...]
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# §6.1 counts reference-style links too: a link reference definition line. A label
# starting with `^` is a footnote definition (§4.2), not a link.
REF_DEF = re.compile(r"^ {0,3}\[([^\]]+)\]:[ \t]*<?([^\s>]+)>?")
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


# §9 constrains the date headings of log.md. A `## ` heading that looks like a
# date in another form is an error: three numeric groups joined by `/`, `-` or `.`
# (`22/05/2026`, `2026-5-2`, `2026-13-45`, `22.05.2026`), or an English month name,
# full or three letters, next to a 1-2 digit day and a 4-digit year (`May 22, 2026`,
# `22 May 2026`). Any other heading text is not a date heading and only warned about.
_MONTH = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|"
          r"aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
DATE_LIKE_HEADING = re.compile(
    rf"\d+[/.-]\d+[/.-]\d+|{_MONTH}\.?[ \t]+\d{{1,2}},?[ \t]+\d{{4}}|"
    rf"\d{{1,2}}[ \t]+{_MONTH}\.?,?[ \t]+\d{{4}}", re.IGNORECASE)


# --migrate only. `timestamp` is a top-level key (§4.1), so anchor at column 0 —
# an indented one belongs to something else and must not be hoisted.
TIMESTAMP = re.compile(r"^timestamp:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
HEADING = re.compile(r"^#{1,6}[ \t]", re.MULTILINE)
# same shape as LINK above, plus the link text — a citation written with a title
# attribute, `[Src](url "Title")`, must not be dropped: the section is deleted
# wholesale once anything parses, so a miss here is silent data loss.
MD_LINK = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# The `$`-anchored patterns below run on a copy whose CRLF endings were folded to
# LF (`_rewrite_file` restores them), so no stray `\r` reaches a capture. A trailing
# comment is kept: `okf_version: 0.2  # pinned` is still a declaration.
OKF_VERSION_LINE = re.compile(
    r"^(okf_version:[ \t]*)(?:\"0\.[12]\"|'0\.[12]'|0\.[12])([ \t]+#.*|[ \t]*)$", re.MULTILINE)
# A block-style path field value: `key: value` or a list item `- key: value`,
# optionally quoted, optionally followed by a comment.
PATH_VALUE = re.compile(
    r"""^(?P<head>[ \t]*(?:-[ \t]+)?[A-Za-z_]+:[ \t]*)(?:(?P<q>["'])(?P<qv>.*?)(?P=q)|"""
    r"""(?P<bv>[^\s"'#{\[|>&*!](?:\S|[ \t]+(?!#))*))(?P<tail>[ \t]*(?:#.*)?)$""")
# One block-mapping entry: indentation, an optional list dash, the key, the rest.
ENTRY = re.compile(r"^(?P<indent>[ \t]*)(?P<dash>-[ \t]+)?(?P<key>[A-Za-z_][\w-]*):(?:[ \t]+(?P<rest>.*))?$")
# A value that opens a block scalar (`|`, `>-`, `|2+`): its content lines follow.
BLOCK_SCALAR = re.compile(r"^[|>][-+0-9]*[ \t]*(?:#.*)?$")
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


def frontmatter_parts(text: str) -> tuple[str, str, str, str] | None:
    """(opening line, raw yaml, closing line, body), or None without a block (§4).

    The caller strips a BOM first. Both delimiters are a `---` line at column 0
    with only trailing whitespace: an indented `---` can sit inside a block scalar
    (#66). Keeping the delimiter lines verbatim lets `--migrate` rebuild the file
    without touching them.
    """
    if not text.startswith("---"):
        return None
    lines = text.splitlines(keepends=True)
    if lines[0].rstrip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return lines[0], "".join(lines[1:i]), lines[i], "".join(lines[i + 1:])
    return None  # unterminated block → treated as absent


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (raw_yaml, body). raw_yaml is None when no frontmatter block."""
    parts = frontmatter_parts(text)
    return (None, text) if parts is None else (parts[1], parts[3])


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
                    raise DuplicateKeyError(None, None, f"duplicate key `{show(key)}`",
                                            key_node.start_mark)
        return super().construct_mapping(node, deep=deep)


class ImpossibleValueError(yaml.YAMLError):
    """A scalar YAML accepts but Python cannot build, such as `2026-02-30` (#63)."""


def load_frontmatter(raw: str):
    """Parse a frontmatter block with duplicate-key detection (§4).

    PyYAML resolves an unquoted `2026-02-30` as a timestamp and then raises a bare
    ValueError building it, and its composer recurses once per nesting level, so
    `[[[[...` deep enough raises RecursionError. Re-raised as a YAMLError, every
    caller reports either as a per-file error instead of crashing the run.
    """
    try:
        return yaml.load(raw, Loader=UniqueKeyLoader)  # a SafeLoader subclass: no arbitrary objects
    except ValueError as exc:
        raise ImpossibleValueError(f"impossible value: {exc}") from exc
    except RecursionError as exc:
        raise ImpossibleValueError("impossible value: nesting too deep to parse") from exc


def is_empty(value) -> bool:
    """§11.2 rule 1: null, an empty string, an empty list and an empty mapping read
    as an absent key. Whitespace-only is not empty: `" "` is a value."""
    return value is None or (isinstance(value, (str, list, dict)) and len(value) == 0)


def scalar_text(value) -> str:
    """The text of a scalar frontmatter value, "" for a list, mapping or null.

    Never stringify a value that may be a collection: YAML aliases share one node,
    so a few lines of `a: &a [x, x]; b: &b [*a, *a] ...` expand to gigabytes once
    printed. Scalars only, so a message costs what its source costs.
    """
    if isinstance(value, (str, int, float, bool, datetime.date)):  # datetime is a date
        return str(value)
    return ""


def show(value) -> str:
    """A frontmatter value as quoted in a message: scalar text cut to 80 chars, or
    a placeholder naming the type of a collection."""
    if isinstance(value, list):
        return "<list>"
    if isinstance(value, dict):
        return "<mapping>"
    text = "null" if value is None else scalar_text(value)
    return text if len(text) <= 80 else text[:79] + "…"


def concept_type(meta) -> str | None:
    """§3.2: the `type` that makes a parsed frontmatter a concept, or None. Only a
    non-blank string counts: `type: 42` or `type: [a]` is not a concept."""
    value = meta.get("type") if isinstance(meta, dict) else None
    return value if isinstance(value, str) and value.strip() else None


def is_computation(meta) -> bool:
    return (concept_type(meta) or "").strip() == "Attested Computation"


def path_field_slots(meta: dict) -> list[tuple[tuple, str, str]]:
    """Every §6.2 path field with a string value, as (path, label, value).

    `path` addresses the value in the parsed mapping, `label` names it in messages.
    `computation`, `executor.resource` and `attester.resource` are read on an
    Attested Computation only (§10.2), the others on any concept.
    """
    slots: list[tuple[tuple, str, str]] = []

    def add(path: tuple, label: str, value) -> None:
        if isinstance(value, str):
            slots.append((path, label, value))

    add(("resource",), "resource", meta.get("resource"))
    srcs = meta.get("sources")
    if isinstance(srcs, dict):  # §11.2 rule 2: one item is a list of one
        add(("sources", "resource"), "sources[0].resource", srcs.get("resource"))
    elif isinstance(srcs, list):
        for i, src in enumerate(srcs):
            if isinstance(src, dict):
                add(("sources", i, "resource"), f"sources[{i}].resource", src.get("resource"))
    add(("superseded_by",), "superseded_by", meta.get("superseded_by"))
    if is_computation(meta):
        add(("computation",), "computation", meta.get("computation"))
        for key in PATH_BLOCKS:
            block = meta.get(key)
            if isinstance(block, dict):
                add((key, "resource"), f"{key}.resource", block.get("resource"))
    return slots


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
                 (what the §6.2 / §12.1 fallback would find)
      missing    resolves inside the bundle and does not exist

    Existence is any file or directory, concept or not, never concept membership.
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


def names_bundle_path(value: str, base_dir: Path, bundle: Path, legacy: bool) -> bool:
    """Whether a `resource` / `sources[].resource` value is a bundle path.

    Both may be a scope descriptor or an opaque identifier instead (§4.1, §6.2):
    `proj.ds.users`, `all queries in BigQuery project acme.prod`, `example.com`. A
    value is a path when it is rooted or dot-relative (`/`, `./`, `../`), or when it
    has no whitespace and names an existing FILE, not a directory, from the file's
    directory or, in a legacy bundle, from the root. Anything else is opaque: no
    warning, no `--migrate` rewrite, no graph edge. The MCP server and the
    visualizer apply the same predicate.
    """
    bare = value.strip().split("#", 1)[0]
    if bare.startswith(("/", "./", "../")):
        return True
    if not bare or any(ch.isspace() for ch in bare):
        return False
    decoded = unquote(bare)
    root = bundle.resolve()

    def is_file(base: Path) -> bool:
        try:
            candidate = (base / decoded).resolve()
        except OSError:
            return False
        return candidate.is_relative_to(root) and candidate.is_file()

    return is_file(base_dir) or (legacy and is_file(bundle))


def is_opaque_slot(slot: tuple) -> bool:
    """The slots `names_bundle_path` applies to: `resource` and `sources[].resource`."""
    return slot[0] in ("resource", "sources")


def declared_version(bundle: Path):
    """The `okf_version` the bundle-root index.md declares, or None."""
    try:
        text = (bundle / "index.md").read_text(encoding="utf-8").lstrip("﻿")
        raw, _ = split_frontmatter(text)
        meta = load_frontmatter(raw) if raw is not None else None
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return meta.get("okf_version") if isinstance(meta, dict) else None


def parse_version(declared) -> tuple[int, int] | None:
    """`<major>.<minor>` from a declared `okf_version` (§12), None when unparseable."""
    # No strip: ` 0.2` is not the `<major>.<minor>` form. A patch part is tolerated.
    m = re.fullmatch(r"([0-9]+)\.([0-9]+)(\..*)?", scalar_text(declared))
    return (int(m.group(1)), int(m.group(2))) if m else None


def is_legacy_version(declared) -> bool:
    """True when the bundle declares 0.2 or earlier, or declares no version (§12.1).

    Null and "" are no declaration at all. An unparseable value is a declaration
    this checker does not understand, so the v0.2 fallbacks do not apply to it.
    """
    if declared is None or (isinstance(declared, str) and declared == ""):
        return True
    version = parse_version(declared)
    return version is not None and version <= (0, 2)


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
    problem = timestamp_problem(value)
    if problem == "no_offset":
        report.warn(rel, f"§5 `{where}` `{show(value)}` lacks the required offset (`Z` or "
                         f"`±HH:MM`): a date-time without one is invalid, so add it or "
                         f"write a date-only `YYYY-MM-DD`")
    elif problem == "impossible":
        report.warn(rel, f"§5 `{where}` `{show(value)}` has the shape of a timestamp but "
                         f"names no real date, time or instant")
    elif problem:
        report.warn(rel, f"§5 `{where}` `{show(value)}` is not an RFC 3339 timestamp "
                         f"(`YYYY-MM-DD`, or a date-time with `Z` or `±HH:MM`)")


def timestamp_problem(value) -> str | None:
    """None for a valid §5 timestamp, else `no_offset`, `impossible` or `invalid`.

    A native YAML date is valid, a native datetime only with a timezone. A string
    must match the RFC 3339 shape and then parse: `fromisoformat` (Python 3.11+,
    after upper-casing the `t`/`z` RFC 3339 allows) rejects `2099-02-30` and hour 24.
    Either must also be a real instant in UTC, as consumers compare them there.
    """
    utc = datetime.UTC
    try:
        if isinstance(value, datetime.datetime):
            if value.utcoffset() is None:
                return "no_offset"
            value.astimezone(utc)
            return None
        if isinstance(value, datetime.date):
            return None
        if not isinstance(value, str):
            return "invalid"
        if ISO_DATE.fullmatch(value):
            datetime.date.fromisoformat(value)
            return None
        if TS_DATETIME.fullmatch(value):
            datetime.datetime.fromisoformat(value.upper()).astimezone(utc)
            return None
    # ValueError: Feb 30, hour 24. OverflowError: an impossible instant, such as
    # `0001-01-01T00:00:00+05:00`, which falls before year 1 once read in UTC.
    except (ValueError, OverflowError):
        return "impossible"
    return "no_offset" if TS_NO_OFFSET.fullmatch(value) else "invalid"


def check_path_field(where: str, value, path: Path, bundle: Path, rel: str,
                     report: Report, legacy: bool, may_be_opaque: bool = False) -> None:
    """§6.2 — a path field should resolve (§6) to something in the bundle.

    Fields naming files are exactly the pointers that rot: the concept keeps
    validating while the file it names moves or disappears. URIs and targets
    outside the bundle root are external and unverifiable from here. A bare value
    that exists only relative to the bundle root is the v0.2 reading (§6.2, §12.1):
    tolerated for a bundle that declares 0.2 or earlier, with a nudge to `/`.
    `may_be_opaque` marks `resource` fields, which can be a scope descriptor or an
    identifier rather than a path: they are checked only when `names_bundle_path`
    reads them as one.
    """
    if not isinstance(value, str):
        return
    if may_be_opaque and not names_bundle_path(value, path.parent, bundle, legacy):
        return
    status, bare = path_status(value, path.parent, bundle)
    if status in ("external", "ok"):
        return
    shown = show(bare)
    if status == "root_only" and legacy:
        report.warn(rel, f"§6.2 `{where}` `{shown}` resolves only from the bundle root "
                         f"(the v0.2 reading, kept by the §12.1 fallback): v0.3 resolves a "
                         f"bare value from the file's directory, so `/{shown}` is required "
                         f"to keep this meaning under v0.3")
        return
    if status == "root_only":
        report.warn(rel, f"§6.2 `{where}` `{shown}` names no file from this file's "
                         f"directory. Both path forms are valid (§13.2): if the "
                         f"bundle-root file is meant, did you mean `/{shown}`?")
        return
    report.warn(rel, f"§6.2 `{where}` points at `{shown}`, which does not exist")


def check_computation(meta: dict, rel: str, report: Report) -> None:
    """§10.2 — the Attested Computation contract. Its path fields are checked with
    the others in `check_concept`."""
    if not scalar_text(meta.get("runtime")).strip():
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


def check_concept(path: Path, rel: str, bundle: Path, report: Report, *,
                  legacy: bool = True, lint: bool = False) -> None:
    """Check one non-reserved `.md`. `legacy` is whether the bundle declares okf_version
    0.2 or earlier (or none), which enables the §12.1 path fallback. `lint` adds the
    okf-skills house-style warnings, which are not spec."""
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
    if concept_type(meta) is None:
        report.warn(rel, "§3.2 frontmatter has no non-empty string `type`: skipped as a "
                         "non-concept")
        return
    report.concepts += 1
    # §4.1: a concept with only `type` is fully conformant. These are this plugin's
    # discovery advice, opt-in via --lint and labelled so nobody reads them as spec.
    if lint:
        for key in RECOMMENDED:
            if key not in meta:
                report.warn(rel, f"okf-skills lint: `{key}` is absent (optional in OKF, "
                                 f"recommended for discovery)")
    check_trust(meta, rel, report, lint=lint)
    check_lifecycle(meta, rel, report)
    check_sources(meta, body, rel, report)
    if is_computation(meta):
        check_computation(meta, rel, report)
    for slot, where, value in path_field_slots(meta):
        check_path_field(where, value, path, bundle, rel, report, legacy,
                         may_be_opaque=is_opaque_slot(slot))


def check_actor(value, where: str, rel: str, report: Report) -> None:
    """§7 — the actor convention shared by `generated.by`, `verified[].by` and
    `sources[].author`."""
    raw = scalar_text(value)
    actor = raw.strip()
    if not actor:
        return
    if actor != raw:
        report.warn(rel, f"§7 `{where}` `{show(raw)}` has leading or trailing whitespace, "
                         f"a near-miss: consumers match `human:` exactly, so ` human:a` "
                         f"reads as non-human")
    elif ACTOR_HUMANISH.match(actor) and not actor.startswith(("human:", "process:")):
        report.warn(rel, f"§7 `{where}` `{show(actor)}` is a near-miss of "
                         f"`human:`/`process:` — §5.3 keys trust tiers off that exact "
                         f"lowercase prefix, so this silently reads as an agent")
    elif not ACTOR_SHAPE.match(actor):
        report.warn(rel, f"§7 `{where}` `{show(actor)}` matches no actor shape "
                         f"(`human:<id>`, `process:<id>`, or `<producer>/<version>`)")


def check_trust(meta: dict, rel: str, report: Report, *, lint: bool = False) -> None:
    """§5.2 — `generated` / `verified`, with the v0.1 `timestamp` fallback."""
    gen = meta.get("generated")
    if is_empty(gen):
        if "timestamp" in meta:
            report.warn(rel, "legacy v0.1 `timestamp`: v0.2 and later record the last "
                             "content change as `generated: {by, at}` (Appendix B)")
        elif lint:
            # §5.3: every trust family is optional, so this is plugin advice.
            report.warn(rel, "okf-skills lint: `generated` is absent (optional in OKF, "
                             "recommended so the content records who changed it and when)")
    elif not isinstance(gen, dict):
        report.warn(rel, "§5.2 `generated` must be a mapping with `by` and `at`")
    elif not scalar_text(gen.get("by")).strip():
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
        if not (isinstance(entry, dict) and scalar_text(entry.get("by")).strip()):
            report.warn(rel, "§5.2 every `verified` entry needs a `by` actor")
            continue
        check_actor(entry["by"], f"verified[{i}].by", rel, report)
        if is_empty(entry.get("at")):
            report.warn(rel, f"§5.2 `verified[{i}]` has no `at`: both `by` and `at` are "
                             f"REQUIRED, so consumers ignore this event")
        else:
            check_timestamp(entry["at"], f"verified[{i}].at", rel, report)


def check_lifecycle(meta: dict, rel: str, report: Report) -> None:
    """§5.4 / §5.5 — `status`, `superseded_by` and `stale_after`. A concept is stale
    when `now >= stale_after`. `superseded_by` is resolved with the other path
    fields in `check_concept`."""
    status = meta.get("status")
    # Exact match only: ` stable `, `Stable`, false and 0 are unknown values (§5.4),
    # which consumers keep and treat as not current.
    if not is_empty(status) and not (isinstance(status, str) and status in STATUS_VALUES):
        report.warn(rel, f"§5.4 unknown `status` `{show(status)}` (expected "
                         f"{'|'.join(sorted(STATUS_VALUES))}): consumers treat it as "
                         f"not current")
    superseded = meta.get("superseded_by")
    if not is_empty(superseded) and status != "deprecated":
        report.warn(rel, "§5.4 `superseded_by` has meaning only with `status: deprecated`")
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


def strip_fences(body: str) -> list[str]:
    """The body's lines outside fenced code blocks."""
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
    return kept


def strip_code(body: str) -> str:
    """The body with fenced blocks and inline code spans removed."""
    return CODE_SPAN.sub("", "\n".join(strip_fences(body)))


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
        if not scalar_text(src.get("resource")).strip():
            report.warn(rel, f"§5.1 `sources[{i}]` is missing the required `resource`")
        if "id" in src:
            ids.add(scalar_text(src["id"]))
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
        report.warn(rel, f"§5.1 footnote `[^{show(label)}]` matches no `sources[].id`")


def reserved_block(raw: str) -> tuple[str, dict]:
    """Classify the leading `---` block of an index.md below the root or a log.md.

    Those files carry no frontmatter (§8, §9). Returns ("empty", {}) when the block
    holds nothing YAML can see (blank, or `---` rules around a markdown heading,
    which parses as comments), ("invalid", {}) when it is not a YAML mapping, which
    breaks §11.1 rule 1 like any other frontmatter block, and ("mapping", meta)
    for real frontmatter, which breaks §11.1 rule 2.
    """
    try:
        meta = load_frontmatter(raw)
    except yaml.YAMLError:
        return "invalid", {}
    if is_empty(meta):
        return "empty", {}
    return ("mapping", meta) if isinstance(meta, dict) else ("invalid", {})


def check_index(path: Path, rel: str, is_root: bool, report: Report) -> None:
    report.indexes += 1
    text = _read_text(path, rel, report)
    if text is None:
        return
    raw, _ = split_frontmatter(text)
    if raw is None:
        return
    if not is_root:
        # §8 says it outright and §11.1 rule 2 makes §8 a conformance rule.
        kind, meta = reserved_block(raw)
        if kind == "empty":
            return  # a file that merely opens with `---` rules has no frontmatter
        if kind == "invalid":
            report.err(rel, "§11.1 the leading `---` block is not a YAML mapping, and an "
                            "index.md below the bundle root has no frontmatter (§8): remove it")
        elif "okf_version" in meta:
            report.err(rel, "§8 an index.md below the bundle root has no frontmatter, and "
                            "this one declares `okf_version`: it looks like a nested bundle "
                            "root, so validate that directory separately (§11.1 rule 2)")
        else:
            report.err(rel, "§8 an index.md below the bundle root has no frontmatter: "
                            "remove the block (§11.1 rule 2)")
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
    keys = [scalar_text(k) for k in meta]
    for old, new in DEPRECATED_ROOT_KEYS.items():
        if old in keys:
            report.warn(rel, f"deprecated plugin key `{old}`, rename to `{new}` (§4.1)")
    extra = sorted(show(k) for k in keys
                   if not (k in ROOT_KEYS or k in DEPRECATED_ROOT_KEYS or k.startswith("x-")))
    if extra:
        report.warn(rel, f"§8.1 root index.md frontmatter has unknown key(s) {extra}: "
                         f"name extensions `x-<producer>-<name>` (§4.1)")
    declared = meta.get("okf_version")
    if is_empty(declared):
        return
    shown = show(declared)
    if not isinstance(declared, str):
        report.warn(rel, f"§8.1 `okf_version` must be a quoted string: write "
                         f"`okf_version: \"{shown}\"`")
    if scalar_text(declared) == OKF_VERSION:
        return
    version = parse_version(declared)
    if version is not None and version <= (0, 2):
        report.warn(rel, f"§12.1 bundle declares `okf_version: \"{shown}\"`, older than "
                         f"v{OKF_VERSION}: checked as v{OKF_VERSION} with the §12.1 "
                         f"fallbacks applied")
    elif version is not None and version > (0, 3):
        report.warn(rel, f"§12 bundle declares `okf_version: \"{shown}\"`, newer than "
                         f"this checker, checked best-effort as v{OKF_VERSION} (§12)")
    elif version is None:
        report.warn(rel, f"§12 `okf_version` `{shown}` is not a `<major>.<minor>` "
                         f"version: checked best-effort as v{OKF_VERSION}, without the "
                         f"§12.1 fallbacks")


def check_log(path: Path, rel: str, report: Report) -> None:
    report.logs += 1
    text = _read_text(path, rel, report)
    if text is None:
        return
    # Both are §9 MUSTs, so §11.1 rule 2 makes them conformance errors.
    raw, body = split_frontmatter(text)
    kind = reserved_block(raw)[0] if raw is not None else "none"
    if kind == "mapping":
        report.err(rel, "§9 log.md has no frontmatter: remove the block (§11.1 rule 2)")
    elif kind == "invalid":
        report.err(rel, "§11.1 the leading `---` block is not a YAML mapping, and log.md "
                        "has no frontmatter (§9): remove it")
    elif kind == "empty":
        body = text  # leading `---` rules are markdown: every heading counts
    for line in strip_fences(body):
        if line.startswith("## "):
            heading = line[3:].strip()
            if ISO_DATE.fullmatch(heading) and timestamp_problem(heading) is None:
                continue
            if DATE_LIKE_HEADING.fullmatch(heading):
                report.err(rel, f"§9 date heading `{show(heading)}` is not an ISO 8601 "
                                f"`YYYY-MM-DD` date (§11.1 rule 2)")
            else:
                report.warn(rel, f"§9 heading `## {show(heading)}` is not a `YYYY-MM-DD` "
                                 f"date heading: §9 groups log.md entries under ISO 8601 "
                                 f"date headings, so use `###` or a date if this is one")


def collect_link_targets(path: Path) -> list[str]:
    # Unreadable files are already reported as a per-file error by
    # check_concept/check_index/check_log; fail soft here to avoid a duplicate
    # error and a crash on the second read pass.
    # §6.1 links live in the body: a `[x](y)` inside a frontmatter string is text.
    try:
        text = path.read_text(encoding="utf-8").lstrip("\ufeff")
    except (UnicodeDecodeError, OSError):
        return []
    _, body = split_frontmatter(text)
    targets: list[str] = []
    for line in strip_code(body).splitlines():
        targets.extend(LINK.findall(line))
        ref = REF_DEF.match(line)
        if ref and not ref.group(1).startswith("^"):
            targets.append(ref.group(2))
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
            report.warn(rel, f"cross-link target not found: `{show(target)}` (tolerated under §6.1)")


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


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _quote_closes(text: str, quote: str) -> bool:
    """Whether `text` holds the closing `quote` of a quoted scalar opened earlier.

    Double quotes escape with a backslash, single quotes by doubling (YAML 1.2).
    """
    i = 0
    while i < len(text):
        ch = text[i]
        if quote == '"' and ch == "\\":
            i += 2
            continue
        if ch == quote:
            if quote == "'" and text[i + 1:i + 2] == "'":
                i += 2
                continue
            return True
        i += 1
    return False


def path_field_lines(lines: list[str], with_computation: bool) -> list[int]:
    """Indexes of the block-style lines that may hold a §6.2 path field.

    Top-level `resource` / `superseded_by` (and `computation`), the `resource` child
    of a block-style `executor` / `attester`, and the `resource` of each item of a
    block-style `sources` list (or of a lone `sources` mapping, §11.2 rule 2). The
    child indentation is that of the FIRST child line of the block, so a deeper
    `x-meta:` mapping holding its own `resource` is not taken for the field. Block
    scalar content and the continuation lines of a multi-line quoted scalar are
    skipped wholesale: they are text, whatever they look like. A heuristic on
    purpose: the caller re-parses the result and refuses any rewrite that changes
    more than the intended values.
    """
    top_keys = {"resource", "superseded_by"} | ({"computation"} if with_computation else set())
    blocks = {"sources"} | (set(PATH_BLOCKS) if with_computation else set())
    found: list[int] = []
    block: str | None = None
    child: tuple[int, bool] | None = None  # (indent, is a list item) of the first child
    item_col: int | None = None  # where the keys of the current `sources` item start
    scalar_parent: int | None = None  # block scalar: skip lines indented deeper
    open_quote = ""
    for i, line in enumerate(lines):
        if open_quote:
            if _quote_closes(line, open_quote):
                open_quote = ""
            continue
        if scalar_parent is not None:
            if not line.strip() or _indent(line) > scalar_parent:
                continue
            scalar_parent = None
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = _indent(line)
        m = ENTRY.match(line)
        key = m.group("key") if m else None
        rest = (m.group("rest") or "") if m else ""
        dashed = bool(m and m.group("dash")) or stripped.startswith("- ") or stripped == "-"
        if m:
            col = indent + len(m.group("dash") or "")
            if BLOCK_SCALAR.match(rest):
                scalar_parent = col
            elif rest[:1] in ("'", '"') and not _quote_closes(rest[1:], rest[0]):
                open_quote = rest[0]
        if indent == 0 and not (dashed and block == "sources" and child in (None, (0, True))):
            block, child, item_col = None, None, None
            if key in top_keys:
                found.append(i)
            elif key in blocks and (not rest.strip() or rest.lstrip().startswith("#")):
                block = key
            continue
        if block is None:
            continue
        if child is None:
            child = (indent, dashed)
        if block != "sources" or not child[1]:
            # executor / attester, or a lone `sources` mapping: direct children only
            if not dashed and indent == child[0] and key == "resource":
                found.append(i)
            continue
        if dashed and indent == child[0]:
            item_col = indent + len(m.group("dash")) if m and m.group("dash") else None
            if key == "resource":
                found.append(i)
        elif not dashed and item_col is not None and indent == item_col and key == "resource":
            found.append(i)
    return found


def _at(meta, path: tuple):
    node = meta
    for step in path:
        in_dict = isinstance(node, dict) and step in node
        in_list = isinstance(node, list) and isinstance(step, int) and step < len(node)
        if not (in_dict or in_list):
            return _MISSING
        node = node[step]
    return node


_MISSING = object()


def _same(a, b, memo: dict) -> bool:
    """Structural equality that visits each shared YAML node pair once.

    A plain `==` on two parses of an alias bomb walks every expanded path, which
    is exponential: memoizing on node identity keeps it linear in the source.
    """
    if type(a) is not type(b):
        return False
    if not isinstance(a, (dict, list)):
        return a == b
    key = (id(a), id(b))
    if key not in memo:
        memo[key] = True  # provisional, for a self-referencing alias
        if isinstance(a, dict):
            memo[key] = list(a) == list(b) and all(_same(a[k], b[k], memo) for k in a)
        else:
            memo[key] = len(a) == len(b) and all(_same(x, y, memo) for x, y in zip(a, b))
    return memo[key]


def _same_except(a, b, skip: set, memo: dict, path: tuple = ()) -> bool:
    """`_same`, ignoring the values at the `skip` paths."""
    if path in skip:
        return True
    if not any(p[:len(path)] == path for p in skip):
        return _same(a, b, memo)
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(
            _same_except(a[k], b[k], skip, memo, path + (k,)) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(
            _same_except(x, y, skip, memo, path + (i,)) for i, (x, y) in enumerate(zip(a, b)))
    return a == b


def pending_path_slots(meta: dict, path: Path, bundle: Path) -> list[tuple[tuple, str, str]]:
    """The path field slots of a legacy-bundle concept that resolve only from the
    root, so v0.3 needs them written `/<path>`. An opaque `resource` /
    `sources[].resource` (`names_bundle_path`) is not a path and never pending."""
    return [(slot, where, value) for slot, where, value in path_field_slots(meta)
            if (not is_opaque_slot(slot) or names_bundle_path(value, path.parent, bundle, True))
            and path_status(value, path.parent, bundle)[0] == "root_only"]


def root_prefix_path_fields(raw: str, meta: dict, path: Path,
                            bundle: Path) -> tuple[str, list[str]]:
    """Prefix `/` to block-style path fields that only resolve from the bundle root.

    v0.2 resolved a bare path field from the bundle root, v0.3 from the file's own
    directory (§6, §6.2), so such a value must become `/<path>` to keep pointing at
    the same file. Only `key: value` lines are rewritten, quoting and trailing
    comments preserved. Flow-style mappings are left alone: the validator keeps
    warning about them, which is the prompt to fix them by hand.

    Returns (raw, refusal reasons). The rewrite is accepted only when the new
    frontmatter parses to the old mapping with exactly the rewritten root-only
    values turned from `v` into `/v`. Anything else (a block scalar line that
    looked like a field, an odd indentation) keeps the original text and reports a
    refusal. A value with leading or trailing whitespace is never rewritten: where
    the `/` goes is a guess, so it is left, reported and stays pending.
    """
    pending = pending_path_slots(meta, path, bundle)
    padded = [(where, v) for _, where, v in pending if v != v.strip()]
    reasons = [f"`{where}` `{show(v)}` has leading or trailing whitespace: not "
               f"rewritten, strip it and add the leading `/` by hand" for where, v in padded]
    slots = [(p, v) for p, _, v in pending if v == v.strip()]
    if not slots:
        return raw, reasons
    wanted = {v for _, v in slots}
    lines = raw.split("\n")
    rewritten = 0
    for i in path_field_lines(lines, is_computation(meta)):
        m = PATH_VALUE.match(lines[i])
        if not m:
            continue
        value = m.group("qv") if m.group("q") else m.group("bv")
        if value not in wanted:
            continue
        quote = m.group("q") or ""
        lines[i] = f"{m.group('head')}{quote}/{value}{quote}{m.group('tail')}"
        rewritten += 1
    if not rewritten:
        return raw, reasons
    new_raw = "\n".join(lines)
    refusal = ("path fields not rewritten: the rewrite would change more than the "
               "`/` prefix once parsed, so add it by hand")
    try:
        after = load_frontmatter(new_raw)
    except yaml.YAMLError:
        return raw, reasons + [refusal]
    changed = {p for p, v in slots if _at(after, p) == "/" + v}
    if isinstance(after, dict) and len(changed) == rewritten \
            and _same_except(meta, after, changed, {}):
        return new_raw, reasons
    return raw, reasons + [refusal]


def hoist_timestamp(raw: str, meta: dict) -> tuple[str, str | None]:
    """Turn a v0.1 top-level `timestamp` into `generated: {by, at}` (Appendix B).

    Only when the parsed frontmatter has a top-level `timestamp` and no
    `generated`. Textual, so the result is re-parsed and accepted only when it has
    `generated.at` equal to the old `timestamp`, `generated.by` the migrate actor,
    no `timestamp`, and every other key unchanged and in place. Returns
    (raw, refusal reason or None).
    """
    if not isinstance(meta, dict) or "timestamp" not in meta or "generated" in meta:
        return raw, None
    hoisted = TIMESTAMP.sub(
        lambda m: f"generated:\n  by: {MIGRATE_ACTOR}\n  at: {m.group(1)}", raw, count=1)
    refusal = ("`timestamp` not hoisted: the rewrite would change more than that once "
               "parsed, so write `generated: {by, at}` by hand")
    try:
        after = load_frontmatter(hoisted)
    except yaml.YAMLError:
        return raw, refusal
    memo: dict = {}
    gen = after.get("generated") if isinstance(after, dict) else None
    ok = isinstance(gen, dict) and list(gen) == ["by", "at"] \
        and gen["by"] == MIGRATE_ACTOR and _same(meta["timestamp"], gen["at"], memo) \
        and list(after) == ["generated" if k == "timestamp" else k for k in meta] \
        and all(_same(meta[k], after[k], memo) for k in meta if k != "timestamp")
    return (hoisted, None) if ok else (raw, refusal)


@dataclass
class Migration:
    """What `--migrate` did, so the summary claims only what happened."""
    changed: list[str] = field(default_factory=list)
    bumped: bool = False
    hoisted_timestamp: bool = False
    hoisted_citations: bool = False
    # `rel: field value`: root-only path fields still bare after the rewrite
    pending: list[str] = field(default_factory=list)
    # `rel: reason`: files the rewrite left untouched on purpose
    refused: list[str] = field(default_factory=list)
    # "`old` to `new`": plugin keys renamed in the root index.md
    renamed_keys: list[str] = field(default_factory=list)


def migrate_concept(text: str, path: Path, bundle: Path, legacy: bool,
                    result: Migration) -> tuple[str | None, str | None]:
    """Rewrite one concept's v0.1 / v0.2 constructs to v0.3.

    Returns (new text or None when nothing changes, refusal reason or None).
    Textual on purpose: dumping the frontmatter back through PyYAML would flatten
    comments, key order and quoting across every file in the bundle. Each branch
    is guarded on the newer key already being present, so a half-migrated bundle
    converges instead of growing a duplicate key that PyYAML then refuses to load.
    Only concepts (§3.2) are touched, and the path rewrite only in a legacy bundle,
    where the §12.1 fallback gives a bare value its root-relative meaning.
    """
    parts = frontmatter_parts(text)
    if parts is None:
        return None, None
    opener, raw, closer, body = parts
    try:
        meta = load_frontmatter(raw)
    except yaml.YAMLError:
        return None, None
    if concept_type(meta) is None:
        return None, None
    new_raw, new_body, reasons = raw, body, []
    if legacy:
        new_raw, reasons = root_prefix_path_fields(raw, meta, path, bundle)
    # Re-read after the path rewrite, which root_prefix_path_fields accepted only
    # when it parses back, so the hoist is checked against what it actually edits.
    hoisted, refusal = hoist_timestamp(new_raw, meta if new_raw == raw else load_frontmatter(new_raw))
    result.hoisted_timestamp |= hoisted != new_raw
    new_raw = hoisted
    reasons += [refusal] if refusal else []
    if "sources" not in meta:
        new_raw, cited = citations_to_sources(new_raw, new_body)
        result.hoisted_citations |= cited != new_body
        new_body = cited
    reason = ". ".join(reasons) or None
    if (new_raw, new_body) == (raw, body):
        return None, reason
    return opener + new_raw + closer + new_body, reason


def migrate_root_index(text: str, bump: bool,
                       renamed: list[str] | None = None) -> tuple[str | None, str | None]:
    """Rename the deprecated plugin keys and, when `bump`, set `okf_version` to 0.3.

    Same contract as `root_prefix_path_fields`: accepted only when the new
    frontmatter parses to the old mapping with exactly those changes. The accepted
    renames are appended to `renamed` as `old -> new`.
    """
    parts = frontmatter_parts(text)
    if parts is None:
        return None, None
    opener, raw, closer, body = parts
    try:
        meta = load_frontmatter(raw)
    except yaml.YAMLError:
        return None, None
    if not isinstance(meta, dict):
        return None, None
    new_raw = raw
    renames = {}
    for old, new in DEPRECATED_ROOT_KEYS.items():
        if old in meta and new not in meta:  # never grow a duplicate key
            new_raw = re.sub(rf"^{re.escape(old)}:", f"{new}:", new_raw, count=1,
                             flags=re.MULTILINE)
            renames[old] = new
    bumped = False
    if bump:
        bumped_raw = OKF_VERSION_LINE.sub(rf'\g<1>"{OKF_VERSION}"\g<2>', new_raw, count=1)
        bumped, new_raw = bumped_raw != new_raw, bumped_raw
    if new_raw == raw:
        return None, None
    try:
        after = load_frontmatter(new_raw)
    except yaml.YAMLError:
        after = None
    memo: dict = {}
    ok = isinstance(after, dict) and list(after) == [renames.get(k, k) for k in meta] \
        and all(after[renames.get(k, k)] == OKF_VERSION if k == "okf_version" and bumped
                else _same(meta[k], after[renames.get(k, k)], memo) for k in meta)
    if not ok:
        return None, ("root index not rewritten: renaming the plugin keys or bumping "
                      "`okf_version` would change more than that once parsed")
    if renamed is not None:
        renamed.extend(f"`{old}` to `{new}`" for old, new in renames.items())
    return opener + new_raw + closer + body, None


def _rewrite_file(path: Path, rewrite) -> tuple[bool, str | None]:
    """Apply `rewrite(text) -> (new text | None, note)` to a file, byte-faithfully.

    The rewrite sees the text without its BOM and with CRLF folded to LF, so the
    `$`-anchored patterns never capture a stray `\\r`. Both are restored on write.
    A file mixing CRLF and LF endings is not rewritten: restoring one ending would
    change every line of the other.
    """
    try:
        original = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return False, None
    bom = original.startswith("﻿")
    text = original[1:] if bom else original
    crlf = text.count("\r\n")
    normalized = text.replace("\r\n", "\n")
    new, note = rewrite(normalized)
    if new is None or new == normalized:
        return False, note
    if crlf and crlf != text.count("\n"):
        return False, "mixed CRLF and LF line endings: not rewritten, normalize them first"
    out = new.replace("\n", "\r\n") if crlf else new
    path.write_bytes((("﻿" if bom else "") + out).encode("utf-8"))
    return True, note


def root_only_path_fields(bundle: Path) -> list[str]:
    """Every concept path field (§6.2) that still resolves only from the bundle root."""
    pending = []
    for path in iter_bundle_md(bundle):
        if path.name in RESERVED:
            continue
        try:
            text = path.read_text(encoding="utf-8").lstrip("﻿")
            raw, _ = split_frontmatter(text)
            meta = load_frontmatter(raw) if raw is not None else None
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        if concept_type(meta) is None:
            continue
        rel = path.relative_to(bundle).as_posix()
        for _, where, value in pending_path_slots(meta, path, bundle):
            bare = path_status(value, path.parent, bundle)[1]
            pending.append(f"{rel}: `{where}` `{show(bare)}` → `/{show(bare)}`")
    return pending


def migrate(bundle: Path) -> Migration:
    """Migrate a bundle in place. Returns what was rewritten, bumped and left over."""
    result = Migration()
    legacy = is_legacy_version(declared_version(bundle))
    for path in iter_bundle_md(bundle):
        if path.name in RESERVED:
            continue
        rel = path.relative_to(bundle).as_posix()
        changed, note = _rewrite_file(
            path, lambda text, p=path: migrate_concept(text, p, bundle, legacy, result))
        if changed:
            result.changed.append(rel)
        if note:
            result.refused.append(f"{rel}: {note}")
    # §12.1: the root-relative reading of a bare path field lasts only while the
    # bundle declares 0.2 or earlier. Bumping with one left would silently repoint
    # it, so the version moves only once none remains anywhere.
    if legacy:
        result.pending = root_only_path_fields(bundle)
    index = bundle / "index.md"
    if index.is_file():
        bump = legacy and not result.pending
        before = declared_version(bundle)
        renamed: list[str] = []
        changed, note = _rewrite_file(index, lambda text: migrate_root_index(text, bump, renamed))
        if changed:
            result.changed.append("index.md")
            result.bumped = bump and declared_version(bundle) != before
            result.renamed_keys = renamed
        if note:
            result.refused.append(f"index.md: {note}")
    return result


def validate(bundle: Path, *, lint: bool = False) -> Report:
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
            check_concept(path, rel, bundle, report, legacy=legacy, lint=lint)
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
    ap.add_argument("--lint", action="store_true",
                    help="also warn on okf-skills house style (missing title, description, "
                         "tags, generated): a convention, not spec")
    ap.add_argument("--max-warnings", type=int, default=None, metavar="N",
                    help="fail if warnings exceed N (--strict is the N=0 case)")
    ap.add_argument("--migrate", action="store_true",
                    help="rewrite v0.1 / v0.2 constructs to v0.3 in place, then validate")
    ap.add_argument("--json", action="store_true", help="emit a JSON report")
    args = ap.parse_args()

    if not args.bundle.is_dir():
        print(f"error: {args.bundle} is not a directory", file=sys.stderr)
        return 2

    mig = migrate(args.bundle) if args.migrate else Migration()

    r = validate(args.bundle, lint=args.lint)
    conformant = not r.errors
    max_warn = 0 if args.strict else args.max_warnings
    failed = bool(r.errors) or (max_warn is not None and len(r.warnings) > max_warn) \
        or (args.strict and bool(mig.pending))

    if args.json:
        print(json.dumps({
            "bundle": str(args.bundle),
            "conformant": conformant,
            "passed": not failed,
            "lint": args.lint,
            "counts": {"concepts": r.concepts, "indexes": r.indexes, "logs": r.logs},
            "errors": r.errors,
            "warnings": r.warnings,
            "migrated": mig.changed,
            "migration": {"bumped": mig.bumped, "pending": mig.pending,
                          "refused": mig.refused, "renamed_keys": mig.renamed_keys},
        }, indent=2))
        return 0 if not failed else 1

    if args.migrate:
        for rel in mig.changed:
            print(f"  \033[36m→ migrated\033[0m  {rel}")
        for note in mig.refused:
            print(f"  \033[33m! migrate\033[0m  {note}")
        print(f"  rewrote {len(mig.changed)} file(s)"
              + (f", `okf_version` bumped to \"{OKF_VERSION}\"" if mig.bumped else "")
              + (f", `generated.by` recorded as `{MIGRATE_ACTOR}`" if mig.hoisted_timestamp else ""))
        if mig.pending:
            print(f"  `okf_version` left as declared: {len(mig.pending)} path field(s) still"
                  f" resolve only from the bundle root. Add the leading `/` by hand, then"
                  f" run --migrate again:")
            for item in mig.pending:
                print(f"    {item}")
        if mig.renamed_keys:
            print(f"  note: renamed {', '.join(mig.renamed_keys)}."
                  f" Collaborators on okf-skills 0.12 or older must update the plugin:"
                  f" older Stop hooks read only the old key.")
        if mig.hoisted_citations:
            print("  note: per-claim attribution (the `[^id]` footnotes of §5.1) is not"
                  " recoverable from a v0.1 `# Citations` list. The sources moved up, but"
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
