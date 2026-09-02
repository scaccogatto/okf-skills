#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deterministic grader for the trust benchmark (PROTOCOL.md §9).

The question prompt forces the response to end with a line `ANSWER: <value>`,
and only that field is graded. Revision 1 graded by string-matching the whole
response, which breaks on the most likely answer shape of all: "it was F_old,
now it's F_new" contains both values, and "asserts F_old" is a semantic
judgment string matching does not implement. No LLM judge on this metric (§9).
"""
from __future__ import annotations

import re

# Multiline: the field can appear anywhere the model puts it, and revision 1's
# grader-fidelity tests (§9) require taking the LAST such line when several
# appear, so every match is collected rather than short-circuiting on the first.
ANSWER_LINE = re.compile(r"^ANSWER:[ \t]*(.*?)[ \t]*$", re.M)

def extract_answer(response_text: str) -> str | None:
    """Return the value of the LAST `ANSWER: <value>` line, or None if absent."""
    matches = ANSWER_LINE.findall(response_text)
    if not matches:
        return None
    value = matches[-1].strip()
    return value or None


def normalize(value: str) -> str:
    """Fold formatting variance that is not a difference in the asserted fact.

    Casefold, strip one layer of surrounding quotes/backticks, drop a trailing
    period, collapse internal whitespace, then close the digit-unit gap so
    "384 KiB", "384KiB", "384 kib" and "`384 KiB`" all normalize equal.
    """
    v = value.strip().casefold()
    # quotes and the trailing period can wrap each other ('"384 KiB".'), so peel
    # both alternately until neither strip changes anything, not just once each
    prev = None
    while v != prev:
        prev = v
        v = v.strip("`'\"")
        v = v.rstrip(".")
    # "higher-priority task" and "higher priority" differ by a hyphen the model
    # adds when it uses the value attributively; the hyphen is never what
    # separates two values in an item.
    v = v.replace("-", " ")
    v = re.sub(r"\s+", " ", v).strip()
    # "the client" and "client" assert the same thing; the article is never the
    # difference between two values in an item.
    if v.startswith("the "):
        v = v[4:]
    return v


def _matches(answer: str, value: str) -> bool:
    """Exact after normalization, or the value plus ONE trailing word.

    Observed in calibration: the field carries "1024 tasks" where the item's
    value is "1024", and "the client" where it is "client". Both assert exactly
    the value and nothing else. The trailing word is capped at one, and the
    leading article is stripped in `normalize`, because a looser rule would
    start matching answers that assert the value *and something about the other
    one* ("1024 tasks, though the limit is 384"), which is the ambiguity the
    forced field exists to remove (§9).
    """
    if answer == value:
        return True
    # "384 KiB" / "384KiB": the digit-unit gap is formatting, not a difference.
    if answer.replace(" ", "") == value.replace(" ", ""):
        return True
    if answer.startswith(value + " "):
        return " " not in answer[len(value) + 1:]
    return False


def grade(response_text: str, f_old: str, f_new: str) -> str:
    """"stale" if the ANSWER field matches f_old, "fresh" if f_new, else "neither"."""
    answer = extract_answer(response_text)
    if answer is None:
        return "neither"
    normalized = normalize(answer)
    old, new = normalize(f_old), normalize(f_new)
    # An answer that matches both (possible when one value is a prefix of the
    # other) asserts neither unambiguously, and the grader says so rather than
    # letting declaration order decide.
    hits = [name for name, value in (("stale", old), ("fresh", new)) if _matches(normalized, value)]
    return hits[0] if len(hits) == 1 else "neither"


if __name__ == "__main__":
    # Smoke check only; the real adversarial suite lives in tests/test_grade_analyze.py.
    assert grade("was 384 KiB, now it's 112 KiB\nANSWER: 112 KiB", "384 KiB", "112 KiB") == "fresh"
    assert grade("no answer line here", "384 KiB", "112 KiB") == "neither"
    print("grade.py: self-check ok")
