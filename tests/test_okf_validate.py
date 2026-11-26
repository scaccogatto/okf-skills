#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Unit tests for okf_validate.py internals (issue #1).

Run:  uv run tests/test_okf_validate.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "validate" / "scripts" / "okf_validate.py"
sys.path.insert(0, str(SCRIPT.parent))
import okf_validate
from okf_validate import (
    Report,
    check_concept,
    check_index,
    check_links,
    check_log,
    collect_link_targets,
    migrate,
    split_frontmatter,
    validate,
)

FULL_META = ('---\ntype: Reference\ntitle: t\ndescription: d\ntags: [x]\n'
             'generated: { by: human:tester, at: "2026-01-01T00:00:00Z" }\n---\n\nbody\n')


class TmpBundle(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bundle = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write(self, rel: str, text: str) -> Path:
        p = self.bundle / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def run_check(self, fn, rel, *args) -> Report:
        report = Report()
        fn(self.bundle / rel, rel, *args, report)
        return report


class TestSplitFrontmatter(unittest.TestCase):
    def test_normal(self):
        raw, body = split_frontmatter("---\ntype: A\n---\nbody\n")
        self.assertEqual(raw, "type: A\n")
        self.assertEqual(body, "body\n")

    def test_no_frontmatter(self):
        self.assertEqual(split_frontmatter("just text"), (None, "just text"))

    def test_unterminated_is_absent(self):
        raw, _ = split_frontmatter("---\ntype: A\nno closing fence\n")
        self.assertIsNone(raw)

    def test_first_line_must_be_bare_dashes(self):
        raw, _ = split_frontmatter("---not a fence\ntype: A\n---\n")
        self.assertIsNone(raw)

    def test_trailing_whitespace_on_fences_ok(self):
        raw, body = split_frontmatter("---  \ntype: A\n---  \nbody")
        self.assertEqual(raw, "type: A\n")
        self.assertEqual(body, "body")

    def test_indented_dashes_in_block_scalar_do_not_close(self):
        raw, body = split_frontmatter("---\ndescription: |\n  a\n  ---\n  b\ntitle: T\n---\nbody")
        self.assertEqual(raw, "description: |\n  a\n  ---\n  b\ntitle: T\n")
        self.assertEqual(body, "body")

    def test_empty_block(self):
        raw, body = split_frontmatter("---\n---\nbody")
        self.assertEqual(raw, "")
        self.assertEqual(body, "body")


class TestCheckConcept(TmpBundle):
    def test_valid_full_metadata_is_clean(self):
        self.write("c.md", FULL_META)
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertEqual((r.errors, r.warnings, r.concepts), ([], [], 1))

    def test_bom_prefixed_file_still_parses(self):
        self.write("c.md", "﻿" + FULL_META)
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertEqual(r.errors, [])

    def test_missing_frontmatter_is_a_skipped_non_concept(self):
        # §3.2 rule 2: README.md / AGENTS.md may live in a bundle. The warning
        # names the fix for someone who did mean it to be a concept (#42).
        self.write("c.md", "no frontmatter\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertEqual((r.errors, r.concepts), ([], 0))
        self.assertIn("§3.2", r.warnings[0])
        self.assertIn("`type`", r.warnings[0])

    def test_unterminated_frontmatter_is_a_skipped_non_concept(self):
        self.write("c.md", "---\ntype: A\nbody without closing fence\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertEqual((r.errors, r.concepts), ([], 0))
        self.assertIn("§3.2", r.warnings[0])

    def test_invalid_yaml_is_error(self):
        self.write("c.md", "---\ntype: [unclosed\n---\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertIn("not valid YAML", r.errors[0])

    def test_impossible_date_is_error_not_crash(self):
        self.write("c.md", "---\ntype: A\ndecided: 2026-02-30\n---\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertIn("not valid YAML", r.errors[0])

    def test_non_mapping_frontmatter_is_error(self):
        self.write("c.md", "---\n- a\n- b\n---\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertIn("YAML mapping", r.errors[0])

    def test_missing_or_empty_type_is_a_skipped_non_concept(self):
        for meta in ("title: t", "type: ''", "type:   ", "type:"):
            self.write("c.md", f"---\n{meta}\n---\nbody\n")
            r = self.run_check(check_concept, "c.md", self.bundle)
            self.assertEqual((r.errors, r.concepts), ([], 0), meta)
            self.assertEqual(len(r.warnings), 1, meta)
            self.assertIn("§3.2", r.warnings[0])

    def test_empty_frontmatter_block_is_a_non_concept_not_an_error(self):
        self.write("c.md", "---\n---\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertEqual((r.errors, r.concepts), ([], 0))

    def test_duplicate_keys_are_an_error_at_any_level(self):
        for meta in ("type: A\ntype: B\n",
                     "type: A\ngenerated:\n  by: human:t\n  by: human:u\n",
                     "type: A\nsources:\n  - { resource: x, resource: y }\n"):
            self.write("c.md", f"---\n{meta}---\nbody\n")
            r = self.run_check(check_concept, "c.md", self.bundle)
            self.assertIn("§4", r.errors[0], meta)
            self.assertIn("duplicate key", r.errors[0], meta)

    def test_unknown_yaml_tag_is_an_error(self):
        self.write("c.md", "---\ntype: A\nx: !!python/object:os.system {}\n---\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertIn("not valid YAML", r.errors[0])

    def test_yaml_merge_key_is_not_a_duplicate(self):
        self.write("c.md", "---\ntype: A\nbase: &b { k: 1 }\nuses: { <<: *b, k: 2 }\n---\nb\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertEqual(r.errors, [])

    def test_type_only_concept_is_clean_without_lint(self):
        # §4.1: a concept with only `type` is fully conformant, so the default run
        # (and therefore --strict) reports nothing.
        self.write("c.md", "---\ntype: A\n---\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertEqual((r.errors, r.warnings, r.concepts), ([], [], 1))

    def test_missing_recommended_fields_warn_only_with_lint(self):
        self.write("c.md", "---\ntype: A\n---\nbody\n")
        r = Report()
        check_concept(self.bundle / "c.md", "c.md", self.bundle, r, lint=True)
        self.assertEqual(r.errors, [])
        self.assertEqual(len(r.warnings), 4)  # title, description, tags, generated
        self.assertTrue(all("okf-skills lint:" in w for w in r.warnings), r.warnings)

    def test_strict_passes_a_type_only_bundle_unless_lint_is_on(self):
        self.write("c.md", "---\ntype: Policy\n---\nbody\n")
        cmd = [sys.executable, str(SCRIPT), str(self.bundle), "--strict", "--json"]
        plain = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(plain.returncode, 0, plain.stdout)
        self.assertFalse(json.loads(plain.stdout)["lint"])
        linted = subprocess.run(cmd + ["--lint"], capture_output=True, text=True, check=False)
        self.assertEqual(linted.returncode, 1, linted.stdout)
        report = json.loads(linted.stdout)
        self.assertTrue(report["lint"])
        self.assertTrue(report["conformant"])
        self.assertEqual(len(report["warnings"]), 4)

    def test_non_utf8_file_is_a_per_file_error_not_a_crash(self):
        (self.bundle / "c.md").write_bytes(b"\xff\xfe invalid")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertTrue(any("c.md" in e for e in r.errors), r.errors)


class TestV02Families(TmpBundle):
    """§5 trust / lifecycle / provenance, and the v0.1 fallbacks (§13.1)."""

    def concept(self, meta: str, body: str = "body\n") -> Report:
        self.write("c.md", f"---\ntype: Reference\ntitle: t\ndescription: d\ntags: [x]\n{meta}---\n\n{body}")
        return self.run_check(check_concept, "c.md", self.bundle)

    def only(self, r: Report) -> str:
        self.assertEqual(r.errors, [])
        self.assertEqual(len(r.warnings), 1, r.warnings)
        return r.warnings[0]

    def test_legacy_timestamp_warns_and_never_errors(self):
        r = self.concept('timestamp: "2026-01-01T00:00:00Z"\n')
        self.assertIn("legacy v0.1 `timestamp`", self.only(r))

    def test_generated_without_by_warns(self):
        self.assertIn("§5.2", self.only(self.concept('generated: { at: "2026-01-01T00:00:00Z" }\n')))

    def test_bare_verified_mapping_is_a_one_element_list(self):
        r = self.concept('generated: { by: human:t }\nverified: { by: human:t, at: "2026-01-01T00:00:00Z" }\n')
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_verified_entry_without_by_warns(self):
        r = self.concept('generated: { by: human:t }\nverified:\n  - { at: "2026-01-01T00:00:00Z" }\n')
        self.assertIn("§5.2", self.only(r))

    def test_unknown_status_warns_known_is_clean(self):
        self.assertIn("§5.4", self.only(self.concept("generated: { by: human:t }\nstatus: retired\n")))
        for status in ("draft", "stable", "deprecated"):
            r = self.concept(f"generated: {{ by: human:t }}\nstatus: {status}\n")
            self.assertEqual((r.errors, r.warnings), ([], []), status)

    def test_list_or_mapping_status_warns_and_does_not_crash(self):
        for status in ("[draft, stable]", "{a: 1}"):
            r = self.concept(f"generated: {{ by: human:t }}\nstatus: {status}\n")
            self.assertIn("§5.4", self.only(r), status)

    def test_stale_after_must_be_an_absolute_date(self):
        # unquoted YAML dates resolve to date objects — both spellings must pass
        for ok in ("2026-09-23", "'2026-09-23'"):
            r = self.concept(f"generated: {{ by: human:t }}\nstale_after: {ok}\n")
            self.assertEqual((r.errors, r.warnings), ([], []), ok)
        self.assertIn("`stale_after`", self.only(self.concept("generated: { by: human:t }\nstale_after: 30d\n")))

    def test_stale_after_accepts_an_iso_datetime(self):
        r = self.concept("generated: { by: human:t }\nstale_after: 2026-09-21T00:00:00Z\n")
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_usage_window_accepts_iso_datetimes(self):
        r = self.concept(
            "generated: { by: human:t }\n"
            "usage_window: { from: 2026-06-01T00:00:00Z, to: 2026-06-30T00:00:00Z }\n"
            "sources:\n  - { resource: https://x, usage_count: 5 }\n")
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_source_last_modified_accepts_an_iso_datetime(self):
        r = self.concept(
            "generated: { by: human:t }\n"
            "sources:\n  - { resource: https://x, last_modified: 2026-09-21T10:00:00+02:00 }\n")
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_source_needs_a_resource(self):
        r = self.concept("generated: { by: human:t }\nsources:\n  - { id: a, title: A }\n")
        self.assertIn("§5.1", self.only(r))

    def test_footnote_label_must_name_a_source(self):
        good = ("generated: { by: human:t }\nsources:\n"
                "  - { id: pol, resource: https://x/pol, title: Policy }\n")
        r = self.concept(good, "Claim.[^pol]\n\n[^pol]: Policy\n")
        self.assertEqual((r.errors, r.warnings), ([], []))
        r = self.concept(good, "Claim.[^nope]\n\n[^nope]: Nope\n")
        self.assertIn("[^nope]", self.only(r))

    def test_regex_classes_in_code_are_not_footnotes(self):
        # #56: a negated character class in a code span or fence is code, not a
        # footnote reference (CommonMark recognizes neither inside code).
        good = ("generated: { by: human:t }\nsources:\n"
                "  - { id: pol, resource: https://x/pol, title: Policy }\n")
        body = ("- `.../clients/(?<client_code>[^#?/]+).*` matches `clients/folders` too\n"
                "- ``a `[^a-z]` b`` in a double-backtick span\n\n"
                "```\nre.compile(r\"[^0-9]+\")\n```\n\n"
                "~~~python\n[^x]\n~~~\n\n"
                "Claim.[^pol]\n\n[^pol]: Policy\n")
        r = self.concept(good, body)
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_footnote_outside_code_still_checked_next_to_a_code_span(self):
        good = ("generated: { by: human:t }\nsources:\n"
                "  - { id: pol, resource: https://x/pol, title: Policy }\n")
        r = self.concept(good, "`[^a-z]` then a claim.[^nope]\n\n```\n[^b]\n```\nAfter.[^gone]\n")
        self.assertEqual(r.errors, [])
        self.assertEqual(len(r.warnings), 2, r.warnings)
        self.assertTrue(any("[^nope]" in w for w in r.warnings))
        self.assertTrue(any("[^gone]" in w for w in r.warnings))

    def test_legacy_citations_body_section_warns(self):
        r = self.concept("generated: { by: human:t }\n", "# Citations\n\n[1] [x](https://x)\n")
        self.assertIn("legacy v0.1 `# Citations`", self.only(r))

    def test_actor_near_miss_of_human_is_caught(self):
        # §5.3 keys trust tiers off the exact `human:` prefix, so this is the one
        # actor typo that changes meaning with no other symptom.
        # `Human:dana` is the nastiest: it satisfies the generic `<prefix>:<id>`
        # shape, so it looks well-formed while §5.3 still reads it as an agent.
        for bad in ("human/dana", "Human:dana", "human-dana", "PROCESS:nightly"):
            self.assertIn("§7", self.only(self.concept(f"generated: {{ by: {bad} }}\n")), bad)

    def test_an_actor_merely_starting_with_human_is_not_a_near_miss(self):
        r = self.concept("generated: { by: humanoid_agent/v1 }\n")
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_actor_shapes_the_spec_uses_are_all_accepted(self):
        # §7's three shapes plus the open `<prefix>:<id>` family the spec's own
        # §5.1 example relies on (`author: team:ga4-docs`) — not a whitelist.
        for ok in ("human:dana", "process:nightly", "reference_agent/gemini-2.5-pro"):
            r = self.concept(f"generated: {{ by: {ok} }}\n")
            self.assertEqual((r.errors, r.warnings), ([], []), ok)
        r = self.concept("generated: { by: human:t }\nsources:\n"
                         "  - { resource: https://x, author: team:ga4-docs }\n")
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_bare_actor_with_no_shape_warns(self):
        self.assertIn("§7", self.only(self.concept("generated: { by: dana }\n")))

    def test_timestamps_are_a_date_or_a_datetime_with_an_offset(self):
        # §5: date-only is fully valid, native YAML dates and tz-aware datetimes too
        for ok in ('"2026-06-20T22:53:05Z"', '"2026-06-20"', "2026-06-20",
                   "2026-06-20T22:53:05Z", "2026-06-20 22:53:05+02:00",
                   '"2026-06-20T22:53:05+02:00"', '"2026-06-20T22:53:05.5Z"'):
            r = self.concept(f"generated: {{ by: human:t, at: {ok} }}\n")
            self.assertEqual((r.errors, r.warnings), ([], []), ok)
        self.assertIn("RFC 3339",
                      self.only(self.concept('generated: { by: human:t, at: "last tuesday" }\n')))

    def test_a_datetime_without_an_offset_is_invalid_in_every_timestamp_field(self):
        for bad in ('"2026-06-20T22:53:05"', "2026-06-20T22:53:05", "2026-06-20 22:53:05",
                    '"2026-06-20T22:53"'):
            for meta in (f"generated: {{ by: human:t, at: {bad} }}\n",
                         f"generated: {{ by: human:t }}\nverified: {{ by: human:t, at: {bad} }}\n",
                         f"generated: {{ by: human:t }}\nstale_after: {bad}\n",
                         f"generated: {{ by: human:t }}\nsources: [{{ resource: x, last_modified: {bad} }}]\n",
                         (f"generated: {{ by: human:t }}\nusage_window: {{ from: {bad}, to: 2026-06-30 }}\n"
                          "sources: [{ resource: x, usage_count: 1 }]\n")):
                self.assertIn("lacks the required offset", self.only(self.concept(meta)), (bad, meta))

    def test_empty_optional_families_are_the_same_as_absent(self):
        # §11.2 rule 1
        base = "generated: { by: human:t }\n"
        for extra in ('verified: []\n', 'verified:\n', 'stale_after: ""\n', 'stale_after:\n',
                      'sources: []\n', 'sources: ""\n', 'status: ""\n', 'usage_window: ""\n',
                      'superseded_by: ""\n'):
            r = self.concept(base + extra)
            self.assertEqual((r.errors, r.warnings), ([], []), extra)
        # an empty `generated` gets the recommendation only under --lint
        self.assertEqual(self.concept('generated: ""\n').warnings, [])
        self.write("c.md", '---\ntype: Reference\ntitle: t\ndescription: d\ntags: [x]\n'
                           'generated: ""\n---\n\nbody\n')
        r = Report()
        check_concept(self.bundle / "c.md", "c.md", self.bundle, r, lint=True)
        self.assertIn("okf-skills lint: `generated`", self.only(r))

    def test_verified_event_without_at_is_ignored_with_a_warning(self):
        r = self.concept("generated: { by: human:t }\nverified: { by: human:t }\n")
        self.assertIn("ignore", self.only(r))
        self.assertIn("`at`", r.warnings[0])

    def test_unknown_status_says_not_current(self):
        self.assertIn("not current", self.only(self.concept("generated: { by: human:t }\nstatus: retired\n")))

    def test_superseded_by_needs_a_deprecated_status(self):
        self.write("new.md", FULL_META)
        base = "generated: { by: human:t }\n"
        r = self.concept(base + "status: deprecated\nsuperseded_by: /new.md\n")
        self.assertEqual((r.errors, r.warnings), ([], []))
        self.assertIn("only with `status: deprecated`",
                      self.only(self.concept(base + "status: stable\nsuperseded_by: /new.md\n")))
        self.assertIn("only with `status: deprecated`",
                      self.only(self.concept(base + "superseded_by: /new.md\n")))

    def test_superseded_by_is_resolved_like_a_path_field(self):
        base = "generated: { by: human:t }\nstatus: deprecated\n"
        self.assertIn("does not exist", self.only(self.concept(base + "superseded_by: /gone.md\n")))
        self.write("my concept.md", FULL_META)
        # a URI, a target outside the bundle, and a percent-encoded + fragment one
        for ok in ("https://x/y.md", "../../outside.md", "/my%20concept.md#frag"):
            r = self.concept(base + f"superseded_by: {ok}\n")
            self.assertEqual((r.errors, r.warnings), ([], []), ok)

    def test_parameters_must_be_a_list_of_named_typed_entries(self):
        head = ("---\ntype: Attested Computation\ntitle: t\ndescription: d\ntags: [x]\n"
                "generated: { by: human:t }\nruntime: bigquery\n")

        def check(extra: str) -> Report:
            self.write("c.md", head + extra + "---\n\nbody\n")
            return self.run_check(check_concept, "c.md", self.bundle)

        good = check("parameters:\n  - { name: year, type: integer, required: true }\n")
        self.assertEqual((good.errors, good.warnings), ([], []))
        # §11.2 rule 2: one mapping is a list of one
        self.assertEqual(check("parameters: { name: year, type: integer }\n").warnings, [])
        self.assertEqual(check("parameters: []\n").warnings, [])
        self.assertIn("must be a list", self.only(check("parameters: year\n")))
        self.assertIn("missing `type`", self.only(check("parameters:\n  - { name: year }\n")))
        self.assertIn("missing `name`", self.only(check("parameters:\n  - { type: integer }\n")))

    def test_usage_count_without_a_window_warns(self):
        base = "generated: { by: human:t }\nsources:\n  - {{ resource: https://x, usage_count: 5 }}\n"
        self.assertIn("usage_window", self.only(self.concept(base.replace("{{", "{").replace("}}", "}"))))
        # a sibling of `sources` frames every entry
        r = self.concept("generated: { by: human:t }\n"
                         "usage_window: { from: 2026-06-01, to: 2026-06-30 }\n"
                         "sources:\n  - { resource: https://x, usage_count: 5 }\n")
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_usage_window_bounds_must_be_absolute_dates(self):
        r = self.concept("generated: { by: human:t }\n"
                         "usage_window: { from: 2026-06-01, to: last month }\n"
                         "sources:\n  - { resource: https://x, usage_count: 5 }\n")
        self.assertIn("usage_window.to", self.only(r))

    def test_computation_paths_that_point_nowhere_warn(self):
        head = ("---\ntype: Attested Computation\ntitle: t\ndescription: d\ntags: [x]\n"
                "generated: { by: human:t }\nruntime: bigquery\n")
        self.write("c.md", head + "attester: { resource: references/gone.py }\n---\n\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertIn("§6.2", self.only(r))
        # an external resource is not ours to resolve
        self.write("c.md", head + "attester: { resource: https://x/att.py }\n---\n\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertEqual((r.errors, r.warnings), ([], []))
        # and one that exists is clean
        self.write("references/att.py", "print(1)\n")
        self.write("c.md", head + "attester: { resource: references/att.py }\n---\n\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_path_fields_resolve_from_the_file_dir_or_the_root_with_a_slash(self):
        head = ("---\ntype: Attested Computation\ntitle: t\ndescription: d\ntags: [x]\n"
                "generated: { by: human:t }\nruntime: bigquery\n")
        self.write("references/att.py", "print(1)\n")
        self.write("sub/local.py", "print(2)\n")
        self.write("my att.py", "print(3)\n")

        def check(rel: str, fields: str, legacy: bool) -> Report:
            self.write(rel, head + fields + "---\n\nbody\n")
            report = Report()
            check_concept(self.bundle / rel, rel, self.bundle, report, legacy=legacy)
            return report

        for legacy in (True, False):
            for ok in ("/references/att.py", "../references/att.py", "/references/att.py#frag",
                       "/my%20att.py", "https://x/a.py", "../../../out.py"):
                r = check("sub/c.md", f"computation: {ok}\n", legacy)
                self.assertEqual((r.errors, r.warnings), ([], []), (legacy, ok))
            self.assertEqual(check("sub/c.md", "attester: { resource: local.py }\n", legacy).warnings, [])
            self.assertIn("does not exist", self.only(check("sub/c.md", "computation: nope.py\n", legacy)))
        # bare `references/att.py` from sub/ exists only from the root: v0.2 reading
        bare = "executor: { resource: references/att.py }\n"
        self.assertIn("resolves only from the bundle root", self.only(check("sub/c.md", bare, True)))
        self.assertIn("`/references/att.py`", check("sub/c.md", bare, True).warnings[0])
        r = check("sub/c.md", bare, False)
        self.assertIn("names no file", self.only(r))
        self.assertIn("did you mean `/references/att.py`?", r.warnings[0])
        self.assertIn("Both path forms are valid (§13.2)", r.warnings[0])
        self.assertIn("required to keep this meaning under v0.3",
                      check("sub/c.md", bare, True).warnings[0])

    def test_validate_reads_the_declared_version_for_the_path_fallback(self):
        self.write("references/att.py", "print(1)\n")
        self.write("sub/c.md", "---\ntype: Attested Computation\ntitle: t\ndescription: d\n"
                               "tags: [x]\ngenerated: { by: human:t }\nruntime: bigquery\n"
                               "computation: references/att.py\n---\n\nbody\n")
        for index, expected in (('---\nokf_version: "0.2"\n---\n', "resolves only from"),
                                ("", "resolves only from"),
                                ('---\nokf_version: "0.3"\n---\n', "did you mean")):
            self.write("index.md", index + "# Root\n")
            warned = " ".join(validate(self.bundle).warnings)
            self.assertIn(expected, warned, index)

    def test_attested_computation_needs_a_runtime(self):
        self.write("c.md", "---\ntype: Attested Computation\ntitle: t\ndescription: d\ntags: [x]\n"
                           "generated: { by: human:t }\n---\n\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertIn("§10.2", self.only(r))
        self.write("c.md", "---\ntype: Attested Computation\ntitle: t\ndescription: d\ntags: [x]\n"
                           "generated: { by: human:t }\nruntime: bigquery\n---\n\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertEqual((r.errors, r.warnings), ([], []))


class TestCheckIndex(TmpBundle):
    def test_root_okf_version_only_is_clean(self):
        self.write("index.md", "---\nokf_version: '0.3'\n---\n# Index\n")
        r = self.run_check(check_index, "index.md", True)
        self.assertEqual((r.errors, r.warnings, r.indexes), ([], [], 1))

    def test_root_plugin_keys_are_clean(self):
        # The Stop hook's flags live here, named as §4.1 extensions; warning on them
        # would make every enforced-mode bundle fail its own `--strict` run.
        self.write("index.md", "---\nokf_version: '0.3'\nx-okf-skills-upkeep: enforced\n"
                               "x-okf-skills-recursive: true\n---\n# Index\n")
        r = self.run_check(check_index, "index.md", True)
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_unprefixed_plugin_keys_are_deprecated_aliases(self):
        self.write("index.md", "---\nokf_version: '0.3'\nupkeep: enforced\nrecursive: true\n---\n")
        r = self.run_check(check_index, "index.md", True)
        self.assertEqual(r.errors, [])
        self.assertEqual(r.warnings, [
            "index.md: deprecated plugin key `upkeep`, rename to `x-okf-skills-upkeep` (§4.1)",
            "index.md: deprecated plugin key `recursive`, rename to `x-okf-skills-recursive` (§4.1)"])

    def test_root_extra_keys_warn_and_suggest_the_x_prefix(self):
        self.write("index.md", "---\nokf_version: '0.3'\ntype: X\n---\n")
        r = self.run_check(check_index, "index.md", True)
        self.assertIn("§8.1", r.warnings[0])
        self.assertIn("x-<producer>-<name>", r.warnings[0])

    def test_root_spec_keys_and_x_extensions_are_clean(self):
        self.write("index.md", "---\nokf_version: '0.3'\ntitle: T\ndescription: D\n"
                               "license: MIT\nx-acme-owner: me\n---\n")
        r = self.run_check(check_index, "index.md", True)
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_unquoted_okf_version_warns(self):
        self.write("index.md", "---\nokf_version: 0.3\n---\n")  # PyYAML reads a float
        r = self.run_check(check_index, "index.md", True)
        self.assertEqual(len(r.warnings), 1, r.warnings)
        self.assertIn("quoted string", r.warnings[0])

    def test_older_declared_version_warns_but_still_validates(self):
        for old in ("0.1", "0.2"):
            self.write("index.md", f"---\nokf_version: '{old}'\n---\n# Index\n")
            r = self.run_check(check_index, "index.md", True)
            self.assertEqual(r.errors, [])
            self.assertIn("okf_version", r.warnings[0])
            self.assertIn("§12.1", r.warnings[0])

    def test_broken_root_frontmatter_is_an_error(self):
        # §11.1 rule 1 covers every frontmatter block, not only concepts'.
        for raw in ("okf_version: [\n", "- a list\n", "okf_version: '0.3'\nokf_version: '0.3'\n"):
            self.write("index.md", f"---\n{raw}---\n")
            r = self.run_check(check_index, "index.md", True)
            self.assertEqual(len(r.errors), 1, (raw, r.errors))

    def test_non_root_frontmatter_is_an_error(self):
        # §8 plus §11.1 rule 2: a conformance rule, not guidance.
        self.write("sub/index.md", "---\nokf_version: '0.3'\n---\n")
        r = self.run_check(check_index, "sub/index.md", False)
        self.assertIn("§11.1 rule 2", r.errors[0])

    def test_root_impossible_date_is_an_error_not_a_crash(self):
        # §11.1 rule 1 covers the root index's frontmatter too, so since v0.3 this
        # is a conformance error rather than the warning it was under v0.2.
        self.write("index.md", "---\nokf_version: '0.2'\nd: 2026-13-45\n---\n")
        r = self.run_check(check_index, "index.md", True)
        self.assertIn("not valid YAML", r.errors[0])

    def test_non_root_rules_around_a_heading_are_not_frontmatter(self):
        for text in ("---\n# Section\n---\n* [a](../a.md)\n", "---\n---\n# S\n"):
            self.write("sub/index.md", text)
            r = self.run_check(check_index, "sub/index.md", False)
            self.assertEqual(r.errors, [], text)

    def test_non_root_non_mapping_block_breaks_rule_1(self):
        # A leading `---` block YAML can see but that is not a mapping is still a
        # frontmatter block, and §11.1 rule 1 requires every one to be a mapping.
        for name, check, args in (("sub/index.md", check_index, (False,)),
                                  ("log.md", check_log, ())):
            for text in ("---\n- a\n---\n", "---\nkey: [\n---\n"):
                self.write(name, text)
                r = self.run_check(check, name, *args)
                self.assertEqual(len(r.errors), 1, (name, text, r.errors))
                self.assertIn("§11.1", r.errors[0])

    def test_a_nested_bundle_root_is_named(self):
        self.write("sub/index.md", "---\nokf_version: '0.3'\ntitle: nested\n---\n")
        r = self.run_check(check_index, "sub/index.md", False)
        self.assertIn("nested bundle root", r.errors[0])
        self.assertIn("validate that directory separately", r.errors[0])

    def test_no_frontmatter_is_clean(self):
        self.write("sub/index.md", "# Plain index\n")
        r = self.run_check(check_index, "sub/index.md", False)
        self.assertEqual(r.warnings, [])


class TestCheckLog(TmpBundle):
    def test_iso_headings_are_clean(self):
        self.write("log.md", "# Log\n\n## 2026-01-31\n* entry\n")
        r = self.run_check(check_log, "log.md")
        self.assertEqual((r.errors, r.warnings, r.logs), ([], [], 1))

    def test_a_date_in_another_form_is_an_error(self):
        for heading in ("22/05/2026", "May 22, 2026", "22 May 2026", "September 3 2026",
                        "2026-5-2", "2026-13-45", "22.05.2026", "2026-1-5"):
            self.write("log.md", f"## {heading}\n")
            r = self.run_check(check_log, "log.md")
            self.assertEqual(len(r.errors), 1, heading)
            self.assertIn("not an ISO 8601", r.errors[0], heading)

    def test_a_heading_that_is_not_a_date_is_a_warning(self):
        # §9 constrains date headings, not every `## ` heading.
        for heading in ("Unreleased", "2026-05-21 (hotfix)", "January 2026", "v1.2"):
            self.write("log.md", f"## {heading}\n")
            r = self.run_check(check_log, "log.md")
            self.assertEqual(r.errors, [], heading)
            self.assertIn("§9 heading", r.warnings[0], heading)

    def test_an_iso_heading_is_clean(self):
        self.write("log.md", "# Log\n\n## 2026-05-22\n* x\n\n### 2026-13-45\n")
        r = self.run_check(check_log, "log.md")
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_leading_horizontal_rules_are_not_frontmatter(self):
        self.write("log.md", "---\n\n# Log\n\n---\n\n## 2026-05-22\n## 22/05/2026\n")
        r = self.run_check(check_log, "log.md")
        self.assertEqual(len(r.errors), 1, r.errors)
        self.assertIn("22/05/2026", r.errors[0])

    def test_frontmatter_is_an_error(self):
        self.write("log.md", "---\ntype: Log\n---\n## 2026-01-01\n")
        r = self.run_check(check_log, "log.md")
        self.assertEqual(len(r.errors), 1, r.errors)
        self.assertIn("§9", r.errors[0])

    def test_headings_in_a_fence_are_not_date_headings(self):
        self.write("log.md", "## 2026-01-01\n\n```\n## not a date\n```\n")
        self.assertEqual(self.run_check(check_log, "log.md").errors, [])


class TestCollectLinkTargets(TmpBundle):
    def test_links_collected_images_ignored(self):
        p = self.write("c.md", 'See [a](a.md) and [b](b.md "title") but not ![img](pic.png).\n')
        self.assertEqual(collect_link_targets(p), ["a.md", "b.md"])

    def test_fenced_code_is_skipped(self):
        p = self.write("c.md", "[real](a.md)\n```\n[fake](in-fence.md)\n```\n~~~\n[fake2](tilde.md)\n~~~\n[also](b.md)\n")
        self.assertEqual(collect_link_targets(p), ["a.md", "b.md"])

    def test_inline_code_span_is_skipped(self):
        p = self.write("c.md", "[real](a.md) and `[fake](x.md)` and ``[fake2](y.md)``\n")
        self.assertEqual(collect_link_targets(p), ["a.md"])


class TestCheckLinks(TmpBundle):
    def links(self, *files: tuple[str, str]) -> Report:
        paths = [self.write(rel, text) for rel, text in files]
        report = Report()
        check_links(self.bundle, paths, report)
        return report

    def test_resolution_matrix(self):
        r = self.links(
            ("a.md", ("[ok](sub/b.md) [ok abs](/sub/b.md) [anchor](sub/b.md#x) "
                      "[ext](https://example.com/x.md) [mail](mailto:x@y.z) "
                      "[dir](sub/) [asset](img.png) [missing](nope.md)")),
            ("sub/b.md", "[up ok](../a.md) [escape](../../etc/passwd.md)"),
        )
        # a target outside the bundle root is external (§6), not broken
        self.assertEqual(len(r.warnings), 1, r.warnings)
        self.assertIn("nope.md", r.warnings[0])

    def test_percent_decoding_dot_paths_and_non_concepts(self):
        self.write(".hidden/secret.md", "no frontmatter\n")
        r = self.links(
            ("a.md", ("[sp](my%20note.md) [frag](my%20note.md#x) [hid](.hidden/secret.md) "
                      "[readme](README.md) [gone](gone%20too.md)")),
            ("my note.md", "x"),
            ("README.md", "not a concept"),
        )
        self.assertEqual(len(r.warnings), 1, r.warnings)
        self.assertIn("gone%20too.md", r.warnings[0])


class TestValidateEndToEnd(TmpBundle):
    def test_counts_and_conformance(self):
        self.write("index.md", "---\nokf_version: '0.3'\n---\n# Root\n\n* [c](c.md)\n")
        self.write("c.md", FULL_META)
        self.write("log.md", "## 2026-01-01\n* created\n")
        r = validate(self.bundle)
        self.assertEqual((r.errors, r.warnings), ([], []))
        self.assertEqual((r.concepts, r.indexes, r.logs), (1, 1, 1))

    def test_non_concepts_warn_and_are_not_counted(self):
        self.write("c.md", FULL_META)
        self.write("README.md", "# Just a readme\n")
        self.write("notype.md", "---\ntitle: x\n---\nbody\n")
        r = validate(self.bundle)
        self.assertEqual(r.errors, [])
        self.assertEqual(r.concepts, 1)
        self.assertEqual(len([w for w in r.warnings if "§3.2" in w]), 2, r.warnings)

    def test_dot_paths_are_not_part_of_the_bundle(self):
        self.write("c.md", FULL_META)
        self.write(".git/bad.md", "---\n- not a mapping\n---\n")
        self.write("sub/.cache/bad.md", "---\n: [\n---\n")
        self.write(".hidden.md", "---\n- x\n---\n")
        r = validate(self.bundle)
        self.assertEqual((r.errors, r.warnings, r.concepts), ([], [], 1))

    def test_bundle_root_may_itself_be_a_dot_directory(self):
        root = self.bundle / ".okf"
        root.mkdir()
        (root / "c.md").write_text(FULL_META, encoding="utf-8")
        r = validate(root)
        self.assertEqual((r.errors, r.warnings, r.concepts), ([], [], 1))

    def test_symlinks_leaving_the_bundle_are_not_followed(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / "evil.md").write_text("---\n- x\n---\n", encoding="utf-8")
        self.write("c.md", FULL_META)
        (self.bundle / "link.md").symlink_to(Path(outside.name) / "evil.md")
        r = validate(self.bundle)
        self.assertEqual((r.errors, r.concepts), ([], 1))

    def test_a_duplicate_key_makes_the_bundle_non_conformant(self):
        self.write("c.md", "---\ntype: A\ntype: B\n---\nbody\n")
        self.assertIn("§4", validate(self.bundle).errors[0])


LEGACY_CONCEPT = (
    "---\n"
    "type: Service\n"
    "title: Auth API        # inline comment\n"
    "description: Issues JWTs.\n"
    "tags: [auth]\n"
    'timestamp: "2026-01-01T00:00:00Z"\n'
    "resource: https://github.com/acme/auth\n"
    "---\n"
    "\n# Overview\n\nIssues tokens.\n"
    "\n# Citations\n\n[1] [Auth README](https://github.com/acme/auth#readme)\n"
    "\n# Endpoints\n\n`POST /token`\n"
)


class TestMigrate(TmpBundle):
    def legacy(self) -> str:
        self.write("index.md", '---\nokf_version: "0.1"\n---\n# Root\n\n* [c](c.md)\n')
        self.write("c.md", LEGACY_CONCEPT)
        migrate(self.bundle)
        return (self.bundle / "c.md").read_text(encoding="utf-8")

    def test_timestamp_becomes_generated_without_disturbing_the_rest(self):
        out = self.legacy()
        self.assertIn("generated:\n  by: process:okf-migrate\n"
                      '  at: "2026-01-01T00:00:00Z"\n', out)
        self.assertNotIn("timestamp:", out)
        # a YAML round-trip would have dropped the comment and reordered the keys
        self.assertIn("# inline comment", out)
        self.assertLess(out.index("title:"), out.index("generated:"))
        self.assertLess(out.index("generated:"), out.index("resource:"))

    def test_citations_become_sources_and_the_section_goes(self):
        out = self.legacy()
        self.assertIn('  - resource: "https://github.com/acme/auth#readme"\n'
                      '    title: "Auth README"\n', out)
        self.assertNotIn("# Citations", out)
        self.assertIn("# Endpoints", out)  # the section after it survives

    def test_no_citation_is_dropped_when_one_carries_a_title(self):
        # The section is deleted wholesale once anything parses, so an entry the
        # link regex misses would vanish rather than merely stay behind.
        self.write("c.md", FULL_META.replace(
            "\nbody\n",
            "\nbody\n\n# Citations\n\n"
            "[1] [A](https://a.com)\n"
            '[2] [B](https://b.com "Titolo")\n'
            "[3] [C](https://c.com)\n").replace(
            "generated: { by: human:tester, at: \"2026-01-01T00:00:00Z\" }\n", ""))
        migrate(self.bundle)
        out = (self.bundle / "c.md").read_text(encoding="utf-8")
        for url in ("https://a.com", "https://b.com", "https://c.com"):
            self.assertIn(f'resource: "{url}"', out)
        self.assertNotIn("# Citations", out)

    def test_root_index_version_is_bumped(self):
        self.legacy()
        self.assertIn('okf_version: "0.3"',
                      (self.bundle / "index.md").read_text(encoding="utf-8"))

    def test_v02_root_index_version_is_bumped_quoted_or_not(self):
        for line in ('okf_version: "0.2"', "okf_version: 0.2", "okf_version: '0.1'"):
            self.write("index.md", f"---\n{line}\nx-okf-skills-upkeep: enforced\n---\n# Root\n")
            self.assertEqual(migrate(self.bundle).changed, ["index.md"], line)
            self.assertEqual((self.bundle / "index.md").read_text(encoding="utf-8"),
                             '---\nokf_version: "0.3"\nx-okf-skills-upkeep: enforced\n---\n# Root\n')
            self.assertEqual(migrate(self.bundle).changed, [])

    def test_bare_root_relative_path_fields_get_a_leading_slash(self):
        self.write("references/att.py", "print(1)\n")
        self.write("references/run.md", FULL_META)
        self.write("new.md", FULL_META)
        original = (
            "---\ntype: Attested Computation\ntitle: t   # keep me\n"
            "runtime: bigquery\n"
            "computation: references/att.py\n"
            "executor:\n  resource: 'references/run.md'  # quoted, commented\n  receipt: [a]\n"
            'attester:\n  resource: "references/att.py#frag"\n'
            "superseded_by: new.md\n"
            "---\nbody\n")
        self.write("sub/c.md", original)
        self.assertEqual(migrate(self.bundle).changed, ["sub/c.md"])
        out = (self.bundle / "sub/c.md").read_text(encoding="utf-8")
        self.assertEqual(out, original
                         .replace("computation: references", "computation: /references")
                         .replace("'references/run.md'", "'/references/run.md'")
                         .replace('"references/att.py#frag"', '"/references/att.py#frag"')
                         .replace("superseded_by: new.md", "superseded_by: /new.md"))
        self.assertEqual(migrate(self.bundle).changed, [])

    def test_path_fields_that_already_resolve_or_are_flow_style_are_left_alone(self):
        self.write("references/att.py", "print(1)\n")
        self.write("sub/references/att.py", "print(2)\n")
        self.write("sub/c.md",
                   "---\ntype: Attested Computation\nruntime: x\n"
                   "computation: references/att.py\n"            # resolves from sub/
                   "attester: { resource: ../references/att.py }\n"  # flow style
                   "executor: { resource: references/gone.py }\n"
                   "---\nbody\n")
        self.write("other/c.md",
                   "---\ntype: Attested Computation\nruntime: x\n"
                   "attester: { resource: references/att.py }\n---\nbody\n")  # root-only, flow
        self.assertEqual(migrate(self.bundle).changed, [])

    def test_path_rewrite_does_not_touch_dot_paths_or_non_concepts(self):
        self.write("references/att.py", "print(1)\n")
        self.write(".hidden/c.md", "---\ntype: A\nsuperseded_by: references/att.py\n---\n")
        self.write("sub/n.md", "---\ntitle: no type\nsuperseded_by: references/att.py\n---\n")
        self.write("sub/t.md", "---\ntype: 42\nsuperseded_by: references/att.py\n---\n")
        self.assertEqual(migrate(self.bundle).changed, [])

    def test_migrated_v02_bundle_validates_clean(self):
        self.write("index.md", '---\nokf_version: "0.2"\n---\n# Root\n')
        self.write("references/att.py", "print(1)\n")
        self.write("sub/c.md", "---\ntype: Attested Computation\ntitle: t\ndescription: d\n"
                               "tags: [x]\ngenerated: { by: human:t }\nruntime: bigquery\n"
                               "computation: references/att.py\n---\nbody\n")
        self.assertNotEqual(validate(self.bundle).warnings, [])
        migrate(self.bundle)
        r = validate(self.bundle)
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_a_migrated_bundle_validates_strict_clean(self):
        self.legacy()
        self.assertEqual(validate(self.bundle).warnings, [])

    def test_idempotent(self):
        self.legacy()
        before = (self.bundle / "c.md").read_text(encoding="utf-8")
        self.assertEqual(migrate(self.bundle).changed, [])
        self.assertEqual((self.bundle / "c.md").read_text(encoding="utf-8"), before)

    def test_a_v02_concept_is_left_alone(self):
        self.write("c.md", FULL_META)
        self.assertEqual(migrate(self.bundle).changed, [])



BOMB = ("a: &a [x, x, x, x, x, x, x, x, x, x]\n"
        "b: &b [*a, *a, *a, *a, *a, *a, *a, *a, *a, *a]\n"
        "c: &c [*b, *b, *b, *b, *b, *b, *b, *b, *b, *b]\n"
        "d: &d [*c, *c, *c, *c, *c, *c, *c, *c, *c, *c]\n"
        "e: &e [*d, *d, *d, *d, *d, *d, *d, *d, *d, *d]\n"
        "f: &f [*e, *e, *e, *e, *e, *e, *e, *e, *e, *e]\n"
        "g: &g [*f, *f, *f, *f, *f, *f, *f, *f, *f, *f]\n"
        "h: &h [*g, *g, *g, *g, *g, *g, *g, *g, *g, *g]\n")


class TestSharedRules(TmpBundle):
    """The consumer rules the validator shares with the MCP server and visualizer."""

    def concept(self, meta: str, body: str = "body\n", rel: str = "c.md") -> Report:
        self.write(rel, f"---\ntype: Reference\ntitle: t\ndescription: d\ntags: [x]\n"
                        f"generated: {{ by: human:t }}\n{meta}---\n\n{body}")
        return self.run_check(check_concept, rel, self.bundle)

    def warned(self, r: Report) -> str:
        self.assertEqual(r.errors, [])
        return " | ".join(r.warnings)

    def test_r1_the_opening_delimiter_is_at_column_0(self):
        self.assertIsNone(split_frontmatter(" ---\ntype: A\n---\n")[0])

    def test_r2_deep_nesting_is_an_error_not_a_crash(self):
        self.write("c.md", "---\ntype: A\nx: " + "[" * 5000 + "\n---\nbody\n")
        r = validate(self.bundle)
        self.assertIn("nesting too deep", r.errors[0])

    def test_r3_a_non_string_type_is_a_non_concept(self):
        for value in ("42", "true", "[x]", "{a: 1}"):
            self.write("c.md", f"---\ntype: {value}\n---\nbody\n")
            r = self.run_check(check_concept, "c.md", self.bundle)
            self.assertEqual((r.errors, r.concepts), ([], 0), value)
            self.assertIn("§3.2", r.warnings[0])

    def test_r4_an_alias_bomb_is_never_stringified(self):
        start = time.monotonic()
        for field in ("status: *h", "stale_after: *h", "generated2: *h\nverified: { by: *h }"):
            r = self.concept(BOMB + field + "\n")
            self.assertTrue(all(len(w) < 400 for w in r.warnings), field)
        self.assertIn("`<list>`", self.warned(self.concept(BOMB + "status: *h\n")))
        self.assertLess(time.monotonic() - start, 5)

    def test_r4_quoted_values_are_truncated(self):
        r = self.concept(f"status: {'x' * 500}\n")
        self.assertLess(len(r.warnings[0]), 300)

    def test_r5_a_timestamp_must_name_a_real_instant(self):
        for bad in ('"2099-02-30"', '"2026-01-01T24:00:00Z"', '" 2099-01-01"',
                    '"2026-02-30T10:00:00+02:00"'):
            self.assertIn("`stale_after`", self.warned(self.concept(f"stale_after: {bad}\n")), bad)
        for ok in ('"2026-01-01t10:00:00z"', '"2026-01-01 10:00:00Z"', '"2028-02-29"'):
            self.assertEqual(self.concept(f"stale_after: {ok}\n").warnings, [], ok)

    def test_r5_an_instant_out_of_range_in_utc_is_impossible(self):
        for bad in ('"0001-01-01T00:00:00+05:00"', '"9999-12-31T23:59:59-05:00"',
                    "0001-01-01T00:00:00+05:00"):
            self.assertIn("names no real date, time or instant",
                          self.warned(self.concept(f"stale_after: {bad}\n")), bad)
        self.assertEqual(okf_validate.timestamp_problem("9999-12-31T23:59:59-05:00"), "impossible")

    def test_r11_a_padded_actor_is_a_near_miss(self):
        for meta in ('verified: { by: " human:a", at: "2026-01-02" }\n',
                     'sources:\n  - resource: https://x\n    author: "human:a "\n'):
            self.assertIn("consumers match `human:` exactly", self.warned(self.concept(meta)), meta)

    def test_r6_only_the_exact_vocabulary_is_a_known_status(self):
        for bad in ('" stable "', "false", "0", "Stable"):
            self.assertIn("unknown `status`", self.warned(self.concept(f"status: {bad}\n")), bad)
        for absent in ("", '""', "[]", "{}"):
            self.assertEqual(self.concept(f"status: {absent}\n").warnings, [], absent)

    def test_r7_an_empty_version_is_no_version(self):
        self.write("references/att.py", "print(1)\n")
        self.write("sub/c.md", "---\ntype: A\ntitle: t\ndescription: d\ntags: [x]\n"
                               "generated: { by: human:t }\nresource: references/att.py\n---\nb\n")
        for line, legacy in (('okf_version: ""', True), ("okf_version:", True),
                             ('okf_version: "0.2.1"', True), ('okf_version: "v0.2"', False),
                             ('okf_version: " 0.2"', False)):
            self.write("index.md", f"---\n{line}\n---\n# Root\n")
            warned = " ".join(validate(self.bundle).warnings)
            self.assertEqual("resolves only from the bundle root" in warned, legacy, line)

    def test_r7_version_messages_tell_older_from_newer(self):
        for version, expected in (("0.2", "§12.1 fallbacks applied"),
                                  ("0.4", "newer than this checker, checked best-effort as v0.3 (§12)"),
                                  ("1.0", "newer than this checker"),
                                  ("next", "not a `<major>.<minor>` version")):
            self.write("index.md", f"---\nokf_version: '{version}'\n---\n")
            r = self.run_check(check_index, "index.md", True)
            self.assertIn(expected, r.warnings[0], version)

    def test_r9_resource_and_sources_resource_are_path_fields(self):
        self.write("references/att.py", "print(1)\n")
        self.write("sub/local.sql", "select 1\n")
        for meta in ("resource: /references/att.py\n", "resource: local.sql\n",
                     "resource: https://x/y\n", "resource: projects/acme/tables/orders\n",
                     "resource: acme-prod.sales.orders\n", "resource: gone.md\n",
                     "resource: proj.ds.users\n", "resource: example.com\n",
                     "sources:\n  - resource: ../references/att.py\n",
                     "sources:\n  - resource: all orders since 2024\n",
                     "sources:\n  - resource: all queries in BigQuery project acme.prod\n"):
            self.assertEqual(self.concept(meta, rel="sub/c.md").warnings, [], meta)
        for meta, label in (("resource: ./gone.md\n", "`resource`"),
                            ("resource: /gone\n", "`resource`"),
                            ("sources:\n  - resource: https://x\n  - resource: ./gone.sql\n",
                             "`sources[1].resource`"),
                            ("sources: { resource: ../gone.py }\n", "`sources[0].resource`")):
            self.assertIn(f"§6.2 {label}", self.warned(self.concept(meta, rel="sub/c.md")), meta)
        legacy = self.concept("sources:\n  - resource: references/att.py\n", rel="sub/c.md")
        self.assertIn("resolves only from the bundle root", self.warned(legacy))

    def test_r10_links_come_from_the_body_only(self):
        self.write("index.md", "---\nokf_version: '0.3'\n---\n")
        self.write("c.md", '---\ntype: A\ndescription: "see [x](missing.md)"\n---\nbody\n')
        self.assertEqual(collect_link_targets(self.bundle / "c.md"), [])
        self.assertFalse(any("cross-link" in w for w in validate(self.bundle).warnings))

    def test_r10_reference_definitions_are_links_footnotes_are_not(self):
        p = self.write("c.md", "---\ntype: A\n---\n[a][ref] and [^n]\n\n"
                               "[ref]: <gone.md> \"T\"\n   [other]: b.md\n[^n]: note.md\n"
                               "    [indented]: code.md\n")
        self.assertEqual(collect_link_targets(p), ["gone.md", "b.md"])


def legacy_bundle(t: TmpBundle, version: str = '"0.2"') -> None:
    t.write("index.md", f"---\nokf_version: {version}\n---\n# Root\n")
    t.write("references/att.py", "print(1)\n")


AC_HEAD = "---\ntype: Attested Computation\ntitle: t\ndescription: d\ntags: [x]\n" \
          "generated: { by: human:t }\nruntime: bigquery\n"


class TestMigrateHardening(TmpBundle):
    def read(self, rel: str) -> str:
        return (self.bundle / rel).read_text(encoding="utf-8")

    def test_a_block_scalar_inside_executor_is_text(self):
        legacy_bundle(self)
        self.write("sub/c.md", AC_HEAD + "executor:\n  notes: |\n    resource: references/att.py\n"
                                         "  resource: references/att.py\n---\nbody\n")
        m = migrate(self.bundle)
        self.assertEqual((m.changed, m.refused), (["sub/c.md", "index.md"], []))
        self.assertIn("    resource: references/att.py\n  resource: /references/att.py\n",
                      self.read("sub/c.md"))
        self.assertTrue(m.bumped)

    def test_a_nested_mapping_under_executor_is_not_the_field(self):
        legacy_bundle(self)
        self.write("sub/c.md", AC_HEAD + "executor:\n  x-meta:\n    resource: references/att.py\n"
                                         "  resource: references/att.py\n---\nbody\n")
        migrate(self.bundle)
        self.assertIn("  x-meta:\n    resource: references/att.py\n  resource: /references/att.py\n",
                      self.read("sub/c.md"))

    def test_a_column_0_continuation_of_a_quoted_scalar_is_text(self):
        legacy_bundle(self)
        self.write("sub/c.md", '---\ntype: A\ntitle: "two\nresource: references/att.py"\n'
                               "resource: references/att.py\n---\nbody\n")
        migrate(self.bundle)
        self.assertEqual(self.read("sub/c.md"),
                         '---\ntype: A\ntitle: "two\nresource: references/att.py"\n'
                         "resource: /references/att.py\n---\nbody\n")

    def test_a_rewrite_that_parses_differently_is_refused(self):
        legacy_bundle(self)
        self.write("sub/c.md", AC_HEAD + "computation: references/att.py\n"
                               "executor:\n  notes: |\n    resource: references/att.py\n---\nbody\n")
        self.write("sub/d.md", "---\ntype: A\nresource: references/att.py\n---\nb\n")
        # Force the line scanner onto the block scalar line: the parse check must catch it.
        with mock.patch.object(okf_validate, "path_field_lines",
                               lambda lines, _: [i for i, ln in enumerate(lines)
                                                 if "resource:" in ln]):
            m = migrate(self.bundle)
        self.assertEqual(len(m.refused), 1, m.refused)
        self.assertIn("sub/c.md", m.refused[0])
        self.assertIn("computation: references/att.py", self.read("sub/c.md"))
        self.assertIn("resource: /references/att.py", self.read("sub/d.md"))
        # one field still bare: the version stays, the leftover is named
        self.assertFalse(m.bumped)
        self.assertEqual(len(m.pending), 1, m.pending)
        self.assertIn("`computation`", m.pending[0])
        self.assertIn('okf_version: "0.2"', self.read("index.md"))

    def test_sources_resource_is_rewritten_and_keeps_resolving(self):
        legacy_bundle(self)
        self.write("sub/c.md", "---\ntype: A\ntitle: t\ndescription: d\ntags: [x]\n"
                               "generated: { by: human:t }\nsources:\n"
                               "  - resource: references/att.py\n    title: A\n"
                               "  - title: B\n    resource: 'references/att.py'  # c\n"
                               "  - resource: https://x\n"
                               "x-other:\n  - resource: references/att.py\n---\nbody\n")
        before = validate(self.bundle).warnings
        self.assertEqual(len([w for w in before if "resolves only from" in w]), 2, before)
        m = migrate(self.bundle)
        out = self.read("sub/c.md")
        self.assertIn("  - resource: /references/att.py\n", out)
        self.assertIn("    resource: '/references/att.py'  # c\n", out)
        self.assertIn("x-other:\n  - resource: references/att.py\n", out)
        self.assertTrue(m.bumped)
        r = validate(self.bundle)
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_a_root_only_flow_field_blocks_the_bump(self):
        legacy_bundle(self)
        self.write("sub/c.md", AC_HEAD + "attester: { resource: references/att.py }\n---\nb\n")
        m = migrate(self.bundle)
        self.assertEqual((m.changed, m.bumped), ([], False))
        self.assertEqual(m.pending, [("sub/c.md: `attester.resource` `references/att.py` → "
                                      "`/references/att.py`")])
        self.assertIn('okf_version: "0.2"', self.read("index.md"))

    def test_a_v03_bundle_gets_no_path_rewrite(self):
        legacy_bundle(self, '"0.3"')
        self.write("sub/c.md", "---\ntype: A\nresource: references/att.py\n---\nb\n")
        m = migrate(self.bundle)
        self.assertEqual((m.changed, m.pending), ([], []))

    def test_crlf_and_bom_survive(self):
        legacy_bundle(self)
        raw = ("﻿---\r\ntype: A\r\nresource: references/att.py\r\n---\r\nbody\r\n")
        (self.bundle / "sub").mkdir()
        (self.bundle / "sub/c.md").write_bytes(raw.encode("utf-8"))
        (self.bundle / "index.md").write_bytes(b'\xef\xbb\xbf---\r\nokf_version: 0.2 # c\r\n---\r\n')
        m = migrate(self.bundle)
        self.assertEqual(m.changed, ["sub/c.md", "index.md"])
        self.assertEqual((self.bundle / "sub/c.md").read_bytes().decode("utf-8"),
                         raw.replace("resource: ", "resource: /"))
        self.assertEqual((self.bundle / "index.md").read_bytes(),
                         b'\xef\xbb\xbf---\r\nokf_version: "0.3" # c\r\n---\r\n')
        self.assertEqual(migrate(self.bundle).changed, [])

    def test_mixed_line_endings_are_refused(self):
        legacy_bundle(self)
        (self.bundle / "sub").mkdir()
        raw = b"---\r\ntype: A\nresource: references/att.py\r\n---\nbody\n"
        (self.bundle / "sub/c.md").write_bytes(raw)
        m = migrate(self.bundle)
        self.assertIn("mixed", m.refused[0])
        self.assertEqual((self.bundle / "sub/c.md").read_bytes(), raw)

    def test_a_commented_version_is_bumped_and_keeps_the_comment(self):
        for line, out in (("okf_version: 0.2 # c", 'okf_version: "0.3" # c'),
                          ('okf_version: "0.2"  # c', 'okf_version: "0.3"  # c'),
                          ("okf_version: '0.1'", 'okf_version: "0.3"')):
            self.write("index.md", f"---\n{line}\n---\n")
            m = migrate(self.bundle)
            self.assertTrue(m.bumped, line)
            self.assertEqual(self.read("index.md"), f"---\n{out}\n---\n")

    def test_plugin_root_keys_are_renamed(self):
        self.write("index.md", "---\nokf_version: '0.3'\nupkeep: enforced  # on\n"
                               "recursive: 2\n---\n# Root\n")
        m = migrate(self.bundle)
        self.assertEqual((m.changed, m.bumped), (["index.md"], False))
        self.assertEqual(self.read("index.md"),
                         "---\nokf_version: '0.3'\nx-okf-skills-upkeep: enforced  # on\n"
                         "x-okf-skills-recursive: 2\n---\n# Root\n")
        r = validate(self.bundle)
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_a_plugin_key_is_not_renamed_onto_an_existing_one(self):
        text = "---\nokf_version: '0.3'\nupkeep: soft\nx-okf-skills-upkeep: enforced\n---\n"
        self.write("index.md", text)
        self.assertEqual(migrate(self.bundle).changed, [])
        self.assertEqual(self.read("index.md"), text)

    def test_an_opaque_resource_naming_a_directory_is_left(self):
        legacy_bundle(self)
        self.write("sales/x.md", "---\ntype: A\n---\nb\n")
        text = ("---\ntype: A\nresource: sales\nsources:\n  - resource: sales\n"
                "  - resource: all orders in sales\n---\nb\n")
        self.write("tables/orders.md", text)
        m = migrate(self.bundle)
        self.assertEqual((m.pending, m.refused), ([], []))
        self.assertEqual(self.read("tables/orders.md"), text)
        self.assertTrue(m.bumped)

    def test_a_padded_path_value_is_left_and_pending(self):
        legacy_bundle(self)
        text = '---\ntype: A\nstatus: deprecated\nsuperseded_by: " references/att.py"\n---\nb\n'
        self.write("sub/c.md", text)
        m = migrate(self.bundle)
        self.assertEqual(self.read("sub/c.md"), text)
        self.assertIn("leading or trailing whitespace", m.refused[0])
        self.assertEqual(len(m.pending), 1, m.pending)
        self.assertFalse(m.bumped)

    def test_timestamp_hoist_needs_a_top_level_key_and_no_generated(self):
        for text in ('---\ntype: A\ndescription: "foo\ntimestamp: 2020-01-01\nbar"\n---\nb\n',
                     "---\ntype: A\ngenerated:\ntimestamp: 2020-01-01\n---\nb\n"):
            self.write("c.md", text)
            m = migrate(self.bundle)
            self.assertEqual((m.changed, m.hoisted_timestamp), ([], False), text)
            self.assertEqual(self.read("c.md"), text)
        self.write("c.md", "---\ntype: A\ntimestamp: 2025-01-01 # when\ntitle: t\n---\nb\n")
        m = migrate(self.bundle)
        self.assertTrue(m.hoisted_timestamp)
        self.assertEqual(self.read("c.md"), "---\ntype: A\ngenerated:\n  by: process:okf-migrate\n"
                                            "  at: 2025-01-01 # when\ntitle: t\n---\nb\n")

    def test_a_timestamp_hoist_that_parses_differently_is_refused(self):
        text = "---\ntype: A\ntimestamp: &t 2025-01-01\nx: *t\n---\nb\n"
        self.write("c.md", text)
        with mock.patch.object(okf_validate, "TIMESTAMP",
                               okf_validate.re.compile(r"^timestamp:[ \t]*(&t)[ \t]*(.*)$",
                                                       okf_validate.re.MULTILINE)):
            m = migrate(self.bundle)
        self.assertEqual(self.read("c.md"), text)
        self.assertIn("`timestamp` not hoisted", m.refused[0])

    def test_a_plugin_key_rename_tells_collaborators_to_update(self):
        self.write("index.md", "---\nokf_version: '0.3'\nupkeep: enforced\n---\n")
        out = subprocess.run([sys.executable, str(SCRIPT), str(self.bundle), "--migrate"],
                             capture_output=True, text=True, check=False).stdout
        self.assertIn("okf-skills 0.12 or older must update the plugin", out)

    def test_the_summary_claims_only_a_bump_that_happened(self):
        legacy_bundle(self)
        self.write("sub/c.md", AC_HEAD + "attester: { resource: references/att.py }\n---\nb\n")
        out = subprocess.run([sys.executable, str(SCRIPT), str(self.bundle), "--migrate"],
                             capture_output=True, text=True, check=False).stdout
        self.assertNotIn("bumped", out)
        self.assertIn("`okf_version` left as declared", out)
        strict = subprocess.run([sys.executable, str(SCRIPT), str(self.bundle), "--migrate",
                                 "--strict"], capture_output=True, text=True, check=False)
        self.assertEqual(strict.returncode, 1)
        self.write("sub/c.md", AC_HEAD + "attester: { resource: /references/att.py }\n---\nb\n")
        out = subprocess.run([sys.executable, str(SCRIPT), str(self.bundle), "--migrate"],
                             capture_output=True, text=True, check=False).stdout
        self.assertIn('`okf_version` bumped to "0.3"', out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
