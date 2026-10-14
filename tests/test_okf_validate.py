#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Unit tests for okf_validate.py internals (issue #1).

Run:  uv run tests/test_okf_validate.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "validate" / "scripts"))
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

    def test_missing_recommended_fields_warn_only(self):
        self.write("c.md", "---\ntype: A\n---\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertEqual(r.errors, [])
        self.assertEqual(len(r.warnings), 4)  # title, description, tags, generated

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
        # an empty `generated` still gets the recommendation
        self.assertIn("recommended field `generated`", self.only(self.concept('generated: ""\n')))

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
        self.assertIn("does not exist", self.only(r))
        self.assertIn("did you mean `/references/att.py`?", r.warnings[0])

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

    def test_root_upkeep_flag_is_clean(self):
        # The Stop hook's opt-in lives here; warning on it would make every
        # enforced-mode bundle fail its own `--strict` run.
        self.write("index.md", "---\nokf_version: '0.3'\nupkeep: enforced\n---\n# Index\n")
        r = self.run_check(check_index, "index.md", True)
        self.assertEqual((r.errors, r.warnings), ([], []))

    def test_root_recursive_is_clean(self):
        # Read by the Stop hook alongside `upkeep`; same reasoning applies.
        self.write("index.md", "---\nokf_version: '0.3'\nupkeep: enforced\nrecursive: true\n---\n# Index\n")
        r = self.run_check(check_index, "index.md", True)
        self.assertEqual((r.errors, r.warnings), ([], []))

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

    def test_non_root_frontmatter_warns(self):
        self.write("sub/index.md", "---\nokf_version: '0.3'\n---\n")
        r = self.run_check(check_index, "sub/index.md", False)
        self.assertIn("§8", r.warnings[0])

    def test_no_frontmatter_is_clean(self):
        self.write("sub/index.md", "# Plain index\n")
        r = self.run_check(check_index, "sub/index.md", False)
        self.assertEqual(r.warnings, [])


class TestCheckLog(TmpBundle):
    def test_iso_headings_are_clean(self):
        self.write("log.md", "# Log\n\n## 2026-01-31\n* entry\n")
        r = self.run_check(check_log, "log.md")
        self.assertEqual((r.errors, r.warnings, r.logs), ([], [], 1))

    def test_non_iso_heading_warns(self):
        self.write("log.md", "## January 2026\n")
        r = self.run_check(check_log, "log.md")
        self.assertIn("not ISO 8601", r.warnings[0])

    def test_frontmatter_warns(self):
        self.write("log.md", "---\ntype: Log\n---\n## 2026-01-01\n")
        r = self.run_check(check_log, "log.md")
        self.assertIn("§9", r.warnings[0])


class TestCollectLinkTargets(TmpBundle):
    def test_links_collected_images_ignored(self):
        p = self.write("c.md", 'See [a](a.md) and [b](b.md "title") but not ![img](pic.png).\n')
        self.assertEqual(collect_link_targets(p), ["a.md", "b.md"])

    def test_fenced_code_is_skipped(self):
        p = self.write("c.md", "[real](a.md)\n```\n[fake](in-fence.md)\n```\n~~~\n[fake2](tilde.md)\n~~~\n[also](b.md)\n")
        self.assertEqual(collect_link_targets(p), ["a.md", "b.md"])


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
            self.write("index.md", f"---\n{line}\nupkeep: enforced\n---\n# Root\n")
            self.assertEqual(migrate(self.bundle), ["index.md"], line)
            self.assertEqual((self.bundle / "index.md").read_text(encoding="utf-8"),
                             '---\nokf_version: "0.3"\nupkeep: enforced\n---\n# Root\n')
            self.assertEqual(migrate(self.bundle), [])

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
        self.assertEqual(migrate(self.bundle), ["sub/c.md"])
        out = (self.bundle / "sub/c.md").read_text(encoding="utf-8")
        self.assertEqual(out, original
                         .replace("computation: references", "computation: /references")
                         .replace("'references/run.md'", "'/references/run.md'")
                         .replace('"references/att.py#frag"', '"/references/att.py#frag"')
                         .replace("superseded_by: new.md", "superseded_by: /new.md"))
        self.assertEqual(migrate(self.bundle), [])

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
        self.assertEqual(migrate(self.bundle), [])

    def test_path_rewrite_does_not_touch_non_concept_dot_paths_or_nested_resource(self):
        self.write("references/att.py", "print(1)\n")
        self.write(".hidden/c.md", "---\ntype: A\nsuperseded_by: references/att.py\n---\n")
        self.write("sub/c.md", "---\ntype: A\nsources:\n  - resource: references/att.py\n---\n")
        self.assertEqual(migrate(self.bundle), [])

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
        self.assertEqual(migrate(self.bundle), [])
        self.assertEqual((self.bundle / "c.md").read_text(encoding="utf-8"), before)

    def test_a_v02_concept_is_left_alone(self):
        self.write("c.md", FULL_META)
        self.assertEqual(migrate(self.bundle), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
