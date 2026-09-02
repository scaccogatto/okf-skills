#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Unit tests for run.py's trial assembly and preflight checks.

No API calls anywhere: only strip/derive, preflight, and CLI --dry-run
(exercised by tests via assemble_trial/preflight directly) are covered.

Run:  uv run benchmark/trust/tests/test_run.py
"""
from __future__ import annotations

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run import (  # noqa: E402
    Item,
    PreflightError,
    assemble_trial,
    assert_derivation_identity,
    choose_distractors,
    discover_items,
    preflight,
    render_base_prompt,
    strip_frontmatter_to_core,
)

HARNESS = {
    "model": "claude-opus-5",
    "effort": "high",
    "max_tokens": 16000,
    "today": "2027-01-01",
    "distractors": 6,
    "min_deprecated_distractors": 2,
    "instructions": {
        "B0": None,
        "A0": None,
        "B1": "b1 instruction",
        "A1": "a1 instruction",
    },
    "full_frontmatter_arms": ["A0", "A1"],
}


def make_doc(status: str | None, stale_after: str, title: str, extra: str = "") -> str:
    status_line = f"status: {status}\n" if status else ""
    return (
        "---\n"
        "type: Reference\n"
        f"title: {title}\n"
        f"description: desc for {title}\n"
        f"{status_line}"
        "generated: { by: human:tester, at: 2026-01-01T00:00:00Z }\n"
        f"stale_after: {stale_after}\n"
        "---\n\n"
        f"# {title}\n\nBody text for {title}. {extra}\n"
    )


def make_item(item_id: str, shape: str = "shape", f_old: str = "OLD_VAL", f_new: str = "NEW_VAL") -> Item:
    superseded_text = make_doc("deprecated", "2026-06-01", f"{item_id}-superseded", f"The value is {f_old}.")
    current_text = make_doc(None, "2027-06-01", f"{item_id}-current", f"The value is now {f_new}.")
    return Item(
        id=item_id,
        shape=shape,
        question=f"What is the value for {item_id}?",
        f_old=f_old,
        f_new=f_new,
        superseded_filename=f"{item_id}-doc-a.md",
        current_filename=f"{item_id}-doc-b.md",
        superseded_text=superseded_text,
        current_text=current_text,
    )


def make_corpus(n: int) -> list[Item]:
    return [make_item(f"item{i}") for i in range(n)]


class TestStrip(unittest.TestCase):
    def test_strip_keeps_only_core_fields_and_preserves_body(self):
        text = make_item("x").superseded_text
        stripped = strip_frontmatter_to_core(text)
        from run import parsed_meta, split_frontmatter

        meta = parsed_meta(stripped)
        self.assertEqual(set(meta), {"type", "title", "description"})
        _, orig_body = split_frontmatter(text)
        _, stripped_body = split_frontmatter(stripped)
        self.assertEqual(orig_body, stripped_body)


class TestIdentity(unittest.TestCase):
    def test_correct_derivation_passes(self):
        text = make_item("x").superseded_text
        stripped = strip_frontmatter_to_core(text)
        self.assertEqual(assert_derivation_identity(text, stripped), [])

    def test_tampered_derivation_fails(self):
        text = make_item("x").superseded_text
        stripped = strip_frontmatter_to_core(text)
        tampered = stripped.replace("title:", "title: TAMPERED ", 1)
        mismatches = assert_derivation_identity(text, tampered)
        self.assertTrue(any("title" in m for m in mismatches))

    def test_tampered_body_fails(self):
        text = make_item("x").superseded_text
        stripped = strip_frontmatter_to_core(text) + "\nextra line\n"
        mismatches = assert_derivation_identity(text, stripped)
        self.assertTrue(any("body" in m for m in mismatches))


class TestLeakage(unittest.TestCase):
    def test_planted_f_old_in_question_is_caught(self):
        corpus = make_corpus(8)
        item = corpus[0]
        item = Item(**{**item.__dict__, "question": f"What replaced {item.f_old}?"})
        rng = random.Random(1)
        trial = assemble_trial(item, corpus, "B0", 0, HARNESS, rng)
        errors = preflight(trial, HARNESS)
        self.assertTrue(any("leakage" in e for e in errors))

    def test_clean_question_has_no_leakage_error(self):
        corpus = make_corpus(8)
        rng = random.Random(1)
        trial = assemble_trial(corpus[0], corpus, "B0", 0, HARNESS, rng)
        errors = preflight(trial, HARNESS)
        self.assertFalse(any("leakage" in e for e in errors))


class TestDeprecatedDistractorMinimum(unittest.TestCase):
    def test_aborts_when_too_few_other_items(self):
        # only 1 other item -> only 1 possible deprecated distractor, need 2
        corpus = make_corpus(2)
        with self.assertRaises(PreflightError):
            choose_distractors(corpus[0], corpus, random.Random(1), count=6, min_deprecated=2)


class TestStaleAfterStraddle(unittest.TestCase):
    def test_all_distractor_dates_on_one_side_aborts(self):
        corpus = make_corpus(8)
        # force every "current" doc to also be in the past, so no distractor
        # date can fall after `today` regardless of which role is picked
        past_only = [
            Item(**{**c.__dict__, "current_text": c.current_text.replace("2027-06-01", "2026-06-01")})
            for c in corpus
        ]
        rng = random.Random(1)
        trial = assemble_trial(past_only[0], past_only, "B0", 0, HARNESS, rng)
        errors = preflight(trial, HARNESS)
        self.assertTrue(any("after `today`" in e for e in errors))


class TestTodayBeforeStaleAfter(unittest.TestCase):
    def test_today_earlier_than_a_superseded_stale_after_aborts(self):
        corpus = make_corpus(8)
        harness = {**HARNESS, "today": "2026-01-01"}  # before the target's superseded stale_after (2026-06-01)
        rng = random.Random(1)
        trial = assemble_trial(corpus[0], corpus, "B0", 0, harness, rng)
        errors = preflight(trial, harness)
        self.assertTrue(any("before this deprecated doc's stale_after" in e for e in errors))


class TestResume(unittest.TestCase):
    """A measurement run is several hundred billed calls; a crash must not re-bill."""

    def test_completed_trials_are_read_back_from_the_run_directory(self):
        from run import _completed_trials

        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            (outdir / "A1.jsonl").write_text(
                json.dumps({"arm": "A1", "item": "i0", "rep": 0}) + "\n"
                + json.dumps({"arm": "A1", "item": "i0", "rep": 1}) + "\n",
                encoding="utf-8")
            (outdir / "B1.jsonl").write_text(
                json.dumps({"arm": "B1", "item": "i0", "rep": 0}) + "\n", encoding="utf-8")
            self.assertEqual(
                _completed_trials(outdir),
                {("A1", "i0", 0), ("A1", "i0", 1), ("B1", "i0", 0)})

    def test_an_empty_directory_resumes_from_nothing(self):
        from run import _completed_trials

        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_completed_trials(Path(tmp)), set())


class TestReplacementMustStillBeFresh(unittest.TestCase):
    """§8 rev 5: "today" sits between the two documents of an item.

    Revision 4 asked for a "today" later than every `stale_after` in the corpus,
    which marks the replacement stale as well and leaves the treatment arm no
    fresh answer to give. The item would still run, still be graded, and quietly
    contribute a guaranteed non-`fresh` result.
    """

    def test_today_on_or_after_the_replacement_stale_after_aborts(self):
        corpus = make_corpus(8)
        # past every stale_after in the corpus, which is exactly what rev 4 asked for
        harness = {**HARNESS, "today": "2028-01-01"}
        rng = random.Random(1)
        trial = assemble_trial(corpus[0], corpus, "A1", 0, harness, rng)
        errors = preflight(trial, harness)
        self.assertTrue(any("no fresh answer left" in e for e in errors), errors)

    def test_a_today_between_the_two_dates_is_accepted(self):
        corpus = make_corpus(8)
        rng = random.Random(1)
        trial = assemble_trial(corpus[0], corpus, "A1", 0, HARNESS, rng)
        errors = preflight(trial, HARNESS)
        self.assertFalse(any("no fresh answer left" in e for e in errors), errors)


class TestNeutralFilenames(unittest.TestCase):
    def test_authoring_names_never_appear(self):
        corpus = make_corpus(8)
        rng = random.Random(1)
        trial = assemble_trial(corpus[0], corpus, "A1", 0, HARNESS, rng)
        filenames = {d.filename for d in trial.docs}
        self.assertNotIn("superseded.md", filenames)
        self.assertNotIn("current.md", filenames)
        on_disk = {p.name for p in trial.root.iterdir()}
        self.assertNotIn("superseded.md", on_disk)
        self.assertNotIn("current.md", on_disk)


class TestDistractorFrontmatterMatchesArm(unittest.TestCase):
    def test_full_arm_distractors_carry_full_frontmatter(self):
        corpus = make_corpus(8)
        rng = random.Random(1)
        trial = assemble_trial(corpus[0], corpus, "A1", 0, HARNESS, rng)
        errors = preflight(trial, HARNESS)
        self.assertEqual(errors, [])
        distractors = [d for d in trial.docs if d.role == "distractor"]
        from run import parsed_meta

        # at least the deprecated distractors carry a `status` field in the full arm
        self.assertTrue(any("status" in parsed_meta(d.rendered_text) for d in distractors))
        for d in distractors:
            self.assertGreater(len(parsed_meta(d.rendered_text)), 3)

    def test_b_arm_distractors_are_stripped(self):
        corpus = make_corpus(8)
        rng = random.Random(1)
        trial = assemble_trial(corpus[0], corpus, "B0", 0, HARNESS, rng)
        errors = preflight(trial, HARNESS)
        self.assertEqual(errors, [])
        from run import parsed_meta

        for d in trial.docs:
            if d.role != "distractor":
                continue
            self.assertEqual(set(parsed_meta(d.rendered_text)), {"type", "title", "description"})


class TestPromptRendering(unittest.TestCase):
    def test_instruction_appended_only_when_present(self):
        order = ["a.md", "b.md"]
        prompt_b0 = render_base_prompt("2027-01-01", "Q?", None, order)
        prompt_a1 = render_base_prompt("2027-01-01", "Q?", "field semantics here", order)
        self.assertNotIn("field semantics here", prompt_b0)
        self.assertIn("field semantics here", prompt_a1)
        self.assertIn("ANSWER:", prompt_a1)
        self.assertIn("2027-01-01", prompt_a1)

    def test_listing_names_every_document_so_read_file_is_invocable(self):
        corpus = make_corpus(8)
        rng = random.Random(1)
        trial = assemble_trial(corpus[0], corpus, "B0", 0, HARNESS, rng)
        for doc in trial.docs:
            self.assertIn(doc.filename, trial.prompt)


class TestCliBackend(unittest.TestCase):
    """§8, rev 6: the CLI backend has to deliver the same trial the API backend
    would, through a different execution surface."""

    def test_command_pins_every_settable_harness_value(self):
        from run import CLI_SYSTEM_PROMPT, build_cli_command

        corpus = make_corpus(8)
        trial = assemble_trial(corpus[0], corpus, "A1", 0, HARNESS, random.Random(3), backend="cli")
        command = build_cli_command(HARNESS, trial)
        self.assertEqual(command[:2], ["claude", "-p"])
        for flag, value in (("--model", HARNESS["model"]), ("--effort", HARNESS["effort"]),
                            ("--output-format", "json"), ("--allowedTools", "Read"),
                            ("--permission-mode", "dontAsk"),
                            ("--system-prompt", CLI_SYSTEM_PROMPT)):
            self.assertEqual(command[command.index(flag) + 1], value)
        self.assertEqual(command[-1], trial.prompt)

    def test_listing_is_absolute_because_the_read_tool_needs_it(self):
        corpus = make_corpus(8)
        trial = assemble_trial(corpus[0], corpus, "B0", 0, HARNESS, random.Random(4), backend="cli")
        for doc in trial.docs:
            self.assertIn(str(trial.root / doc.filename), trial.prompt)
        self.assertIn("Read tool", trial.prompt)

    def test_trial_directory_name_leaks_neither_item_nor_arm(self):
        # The CLI backend puts this path in the prompt, so a directory named
        # after the item and the arm would hand the model the design.
        corpus = make_corpus(8)
        trial = assemble_trial(corpus[0], corpus, "A1", 2, HARNESS, random.Random(5), backend="cli")
        name = trial.root.name
        self.assertNotIn(trial.item.id, name)
        self.assertNotIn("A1", name)

    def test_api_backend_prompt_is_unchanged_by_the_addition(self):
        corpus = make_corpus(8)
        trial = assemble_trial(corpus[0], corpus, "B0", 0, HARNESS, random.Random(6))
        self.assertIn("read_file tool", trial.prompt)
        for doc in trial.docs:
            self.assertIn(doc.filename, trial.prompt)
            self.assertNotIn(str(trial.root / doc.filename), trial.prompt)


class TestCorpusAuthoringRules(unittest.TestCase):
    def test_no_answer_value_is_a_bare_short_number(self):
        """§10's leakage check compares against the whole rendered prompt, and
        under the CLI backend that prompt contains the trial directory's path.
        An answer of "3" is therefore present in every prompt that has a 3
        anywhere in its path, which aborted every trial of one item rather than
        biasing one silently — but the authoring rule belongs here, not in the
        run log."""
        real_corpus = Path(__file__).resolve().parents[1] / "corpus"
        for item in discover_items(real_corpus):
            for label, value in (("f_old", item.f_old), ("f_new", item.f_new)):
                self.assertFalse(
                    value.isdigit() and len(value) < 3,
                    f"{item.id}: {label}={value!r} is a bare short number",
                )


class TestDiscoverItems(unittest.TestCase):
    def test_discovers_real_corpus_item(self):
        real_corpus = Path(__file__).resolve().parents[1] / "corpus"
        items = discover_items(real_corpus)
        self.assertGreaterEqual(len(items), 1)
        ids = {i.id for i in items}
        self.assertIn("limit-changed-01", ids)


if __name__ == "__main__":
    unittest.main()
