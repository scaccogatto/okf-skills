#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
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
from okf_validate import (  # noqa: E402
    Report, check_concept, check_index, check_links, check_log,
    collect_link_targets, migrate, split_frontmatter, validate,
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
        raw, body = split_frontmatter("---\ntype: A\nno closing fence\n")
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

    def test_missing_frontmatter_is_error(self):
        self.write("c.md", "no frontmatter\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertIn("§11.1", r.errors[0])

    def test_unterminated_frontmatter_is_error(self):
        self.write("c.md", "---\ntype: A\nbody without closing fence\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertIn("§11.1", r.errors[0])

    def test_invalid_yaml_is_error(self):
        self.write("c.md", "---\ntype: [unclosed\n---\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertIn("not valid YAML", r.errors[0])

    def test_non_mapping_frontmatter_is_error(self):
        self.write("c.md", "---\n- a\n- b\n---\nbody\n")
        r = self.run_check(check_concept, "c.md", self.bundle)
        self.assertIn("YAML mapping", r.errors[0])

    def test_missing_or_empty_type_is_error(self):
        for meta in ("title: t", "type: ''", "type:   "):
            self.write("c.md", f"---\n{meta}\n---\nbody\n")
            r = self.run_check(check_concept, "c.md", self.bundle)
            self.assertTrue(any("§11.2" in e for e in r.errors), meta)

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

    def test_stale_after_must_be_an_absolute_date(self):
        # unquoted YAML dates resolve to date objects — both spellings must pass
        for ok in ("2026-09-23", "'2026-09-23'"):
            r = self.concept(f"generated: {{ by: human:t }}\nstale_after: {ok}\n")
            self.assertEqual((r.errors, r.warnings), ([], []), ok)
        self.assertIn("§5.5", self.only(self.concept("generated: { by: human:t }\nstale_after: 30d\n")))

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

    def test_instants_are_rfc3339_date_only_tolerated(self):
        for ok in ('"2026-06-20T22:53:05Z"', '"2026-06-20"', "2026-06-20T22:53:05Z",
                   '"2026-06-20T22:53:05+02:00"'):
            r = self.concept(f"generated: {{ by: human:t, at: {ok} }}\n")
            self.assertEqual((r.errors, r.warnings), ([], []), ok)
        self.assertIn("RFC 3339",
                      self.only(self.concept('generated: { by: human:t, at: "last tuesday" }\n')))

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
        self.write("index.md", "---\nokf_version: '0.2'\n---\n# Index\n")
        r = self.run_check(check_index, "index.md", True)
        self.assertEqual((r.errors, r.warnings, r.indexes), ([], [], 1))

    def test_root_extra_keys_warn(self):
        self.write("index.md", "---\nokf_version: '0.2'\ntype: X\n---\n")
        r = self.run_check(check_index, "index.md", True)
        self.assertIn("§12", r.warnings[0])

    def test_older_declared_version_warns_but_still_validates(self):
        self.write("index.md", "---\nokf_version: '0.1'\n---\n# Index\n")
        r = self.run_check(check_index, "index.md", True)
        self.assertEqual(r.errors, [])
        self.assertIn("okf_version", r.warnings[0])

    def test_non_root_frontmatter_warns(self):
        self.write("sub/index.md", "---\nokf_version: '0.2'\n---\n")
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
            ("a.md", "[ok](sub/b.md) [ok abs](/sub/b.md) [anchor](sub/b.md#x) "
                     "[ext](https://example.com/x.md) [mail](mailto:x@y.z) "
                     "[dir](sub/) [asset](img.png) [missing](nope.md)"),
            ("sub/b.md", "[up ok](../a.md) [escape](../../etc/passwd.md)"),
        )
        warned = " ".join(r.warnings)
        self.assertIn("nope.md", warned)
        self.assertIn("passwd.md", warned)
        self.assertEqual(len(r.warnings), 2, r.warnings)


class TestValidateEndToEnd(TmpBundle):
    def test_counts_and_conformance(self):
        self.write("index.md", "---\nokf_version: '0.2'\n---\n# Root\n\n* [c](c.md)\n")
        self.write("c.md", FULL_META)
        self.write("log.md", "## 2026-01-01\n* created\n")
        r = validate(self.bundle)
        self.assertEqual((r.errors, r.warnings), ([], []))
        self.assertEqual((r.concepts, r.indexes, r.logs), (1, 1, 1))


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
        self.assertIn('okf_version: "0.2"',
                      (self.bundle / "index.md").read_text(encoding="utf-8"))

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
