#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Two-stage harness for the write-side gate benchmark (#48, PROTOCOL.md).

Stage W: a writer agent applies a fact change to an implementation artifact, with
or without an `AGENTS.md` process gate. Graded deterministically from the files
it leaves behind — no model judge.

Stage C: a consumer agent answers the item's question against a corpus state
built deterministically, and is graded by the trust benchmark's own grader.

Everything the trust benchmark already paid to get right is imported rather than
rewritten: the frozen CLI invocation (safe mode, advisor disabled), the corpus
and its validated items, the injected-date rule, the forced answer field and the
grader.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import shlex
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import yaml

GATE_DIR = Path(__file__).resolve().parent
TRUST_DIR = GATE_DIR.parent / "trust"
sys.path.insert(0, str(TRUST_DIR))

from run import (  # noqa: E402  (the trust benchmark's module, hence the rename of this one)
    CLI_SETTINGS,
    CLI_TOOL_NAME,
    Item,
    discover_items,
    load_harness,
    parsed_meta,
    render_base_prompt,
    split_frontmatter,
    strip_frontmatter_to_core,
)
from grade import extract_answer, grade  # noqa: E402

# The gate, in the FastEndpoints spirit: a rule in prose, in the repository, that
# says the task is not finished until the documentation is reconciled. Quoted in
# PROTOCOL.md §4 and frozen here.
AGENTS_MD = """# Repository conventions

A task is not finished until the documentation in `docs/` is synced with the
change, or the task explicitly declares the documentation unaffected.
"""

WRITER_SYSTEM_PROMPT = (
    "You are a software engineer working in a repository. Make the change you "
    "are asked for."
)

CONSUMER_SYSTEM_PROMPT = (
    "You answer questions from a corpus of documents. Read the documents you are "
    "given and answer only from them."
)

# Corpus states for Stage C (§5). `synced` is the item's replacement document;
# the three stale states are the same superseded document differing only in
# lifecycle frontmatter, so the contrast between them is the read side and
# nothing else.
STATES = ("synced", "stale_unmarked", "stale_expired", "stale_marked")

# Stage W happens at the moment of the change, so the document the writer meets
# carries no staleness signal of its own: status stable, expiry well in the
# future, no `verified` claim to contradict.
WRITER_DOC_STALE_AFTER = "2028-12-31"


# --------------------------------------------------------------------------
# The implementation artifact
# --------------------------------------------------------------------------


def setting_key(item: Item) -> str:
    """A stable config key for the item, derived from its document title."""
    title = parsed_meta(item.superseded_text).get("title", item.id)
    words = re.findall(r"[A-Za-z]+", title.lower())[:3]
    return "_".join(words) or item.id.replace("-", "_")


def artifact_text(item: Item, value: str) -> str:
    """The runtime configuration the service actually enforces.

    The question is quoted verbatim as the setting's comment. That is a
    deliberate simplification (§5): it makes the artifact unambiguously about
    the fact under test, identically in every arm and every state, instead of
    leaving the consumer to infer which key answers the question.
    """
    return (
        "# Runtime configuration. These are the values the service enforces.\n"
        f"# {item.question.strip()}\n"
        f"{setting_key(item)}: {value}\n"
    )


def _with_frontmatter(text: str, overrides: dict, drop: tuple[str, ...] = ()) -> str:
    raw, body = split_frontmatter(text)
    meta = yaml.safe_load(raw) or {}
    for key in drop:
        meta.pop(key, None)
    meta.update(overrides)
    return f"---\n{yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)}---\n{body}"


def doc_for_state(item: Item, state: str, today: str) -> str:
    """The documentation file as the consumer sees it in a given state (§5)."""
    if state == "synced":
        return item.current_text
    if state == "stale_unmarked":
        return strip_frontmatter_to_core(item.superseded_text)
    if state == "stale_expired":
        # Only the field that expires without anyone acting. `status` stays
        # `stable` and there is no `verified` change: this is the state a repo
        # reaches when the writer does nothing and the date was set in advance.
        return _with_frontmatter(item.superseded_text, {"status": "stable"}, drop=("verified",))
    if state == "stale_marked":
        return _with_frontmatter(item.superseded_text, {"status": "deprecated"}, drop=("verified",))
    raise ValueError(f"unknown state {state!r}")


# --------------------------------------------------------------------------
# Stage W — the writer
# --------------------------------------------------------------------------


@dataclass
class WriterRun:
    item: Item
    arm: str  # "gate" | "nogate"
    rep: int
    root: Path
    prompt: str


def writer_doc(item: Item) -> str:
    """The documentation as it stands *before* the change.

    The corpus authors this document already marked `deprecated` with an expired
    `stale_after`, because in the trust benchmark it is the superseded one. Here
    it is the current one: at the moment the writer acts, nothing about it says
    it is out of date, and whether it ends up saying so is the outcome under
    test. The first writer probe graded every run as "already deprecated"
    because this was missed.
    """
    return _with_frontmatter(
        item.superseded_text,
        {"status": "stable", "stale_after": WRITER_DOC_STALE_AFTER},
        drop=("verified",),
    )


def build_writer_repo(item: Item, arm: str) -> Path:
    root = Path(tempfile.mkdtemp(prefix="okf-repo-"))
    (root / "config").mkdir()
    (root / "docs").mkdir()
    (root / "config" / "settings.yaml").write_text(artifact_text(item, item.f_old), encoding="utf-8")
    (root / "docs" / item.superseded_filename).write_text(writer_doc(item), encoding="utf-8")
    if arm == "gate":
        (root / "AGENTS.md").write_text(AGENTS_MD, encoding="utf-8")
    return root


def writer_prompt(item: Item, arm: str, root: Path) -> str:
    key = setting_key(item)
    parts = [
        f"The repository is at {root}.",
        f"Apply this change: `{key}` in `config/settings.yaml` becomes "
        f"{item.f_new} (it is currently {item.f_old}).",
    ]
    if arm == "gate":
        # The gate reaches the agent the way it reaches one in a real repository:
        # a file in the tree it is told to follow. Safe mode disables CLAUDE.md
        # discovery, so the pointer is explicit and its wording is frozen.
        parts.append("Read `AGENTS.md` first and follow the repository's conventions.")
    parts.append("Report what you changed when you are done.")
    return "\n\n".join(parts)


def build_writer_command(harness: dict, prompt: str) -> list[str]:
    return [
        "claude", "-p",
        "--model", harness["model"],
        "--effort", harness["effort"],
        "--output-format", "json",
        "--allowedTools", "Read", "Edit", "Write",
        "--permission-mode", "dontAsk",
        "--system-prompt", WRITER_SYSTEM_PROMPT,
        "--safe-mode",
        "--settings", CLI_SETTINGS,
        prompt,
    ]


def grade_writer(run: WriterRun) -> dict:
    """Deterministic grading from the files, never from what the agent said."""
    config = (run.root / "config" / "settings.yaml").read_text(encoding="utf-8")
    doc_path = run.root / "docs" / run.item.superseded_filename
    doc = doc_path.read_text(encoding="utf-8") if doc_path.is_file() else ""
    meta = parsed_meta(doc) if doc else {}
    states_new = run.item.f_new in doc
    states_old = run.item.f_old in doc
    return {
        "impl_updated": run.item.f_new in config,
        "impl_still_old": run.item.f_old in config,
        # "Synced" is the value present AND the old one gone. The first probe
        # counted a substring hit as a sync, which credited untouched documents
        # that happened to contain the new value's digits somewhere.
        "doc_synced": states_new and not states_old,
        "doc_states_new": states_new,
        "doc_states_old": states_old,
        "doc_marked_deprecated": meta.get("status") == "deprecated",
        "doc_stale_after_moved": str(meta.get("stale_after", "")) != WRITER_DOC_STALE_AFTER,
        "doc_untouched": doc == writer_doc(run.item),
        "doc_deleted": not doc,
    }


def run_writer(harness: dict, run: WriterRun) -> dict:
    command = build_writer_command(harness, run.prompt)
    completed = subprocess.run(command, cwd=run.root, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=1200)
    if completed.returncode != 0:
        raise RuntimeError(f"claude exited {completed.returncode}: {completed.stderr[-400:]}")
    payload = json.loads(completed.stdout)
    if payload.get("is_error"):
        raise RuntimeError(f"claude reported an error: {str(payload.get('result'))[:300]}")
    outcome = grade_writer(run)
    return {
        "stage": "writer",
        "item": run.item.id,
        "shape": run.item.shape,
        "arm": run.arm,
        "rep": run.rep,
        **outcome,
        "session_id": payload.get("session_id"),
        "cost_usd": payload.get("total_cost_usd"),
        "model": harness["model"],
        "request": {"command": shlex.join(command), "cwd": str(run.root)},
    }


# --------------------------------------------------------------------------
# Stage C — the consumer
# --------------------------------------------------------------------------


@dataclass
class ConsumerRun:
    item: Item
    state: str
    rep: int
    root: Path
    prompt: str
    order: list[str]


def build_consumer_corpus(item: Item, others: list[Item], state: str, harness: dict,
                           rng: random.Random) -> ConsumerRun:
    today = harness["today"]
    root = Path(tempfile.mkdtemp(prefix="okf-corpus-"))
    files: dict[str, str] = {}

    # The changed implementation artifact is present in EVERY state (§5): without
    # it a stale-document state has no reachable correct answer, refusal becomes
    # correct, and the metric is undefined by construction — which is exactly
    # what invalidated #40's primary result.
    files["settings.yaml"] = artifact_text(item, item.f_new)
    doc_name = item.superseded_filename if state != "synced" else item.current_filename
    files[doc_name] = doc_for_state(item, state, today)

    full_frontmatter = state in ("stale_expired", "stale_marked", "synced")
    pool = [o for o in others if o.id != item.id]
    for other, role in rng.sample([(o, r) for o in pool for r in ("superseded", "current")], 6):
        text = other.superseded_text if role == "superseded" else other.current_text
        name = other.superseded_filename if role == "superseded" else other.current_filename
        if name in files:
            continue
        files[name] = text if full_frontmatter else strip_frontmatter_to_core(text)

    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    order = list(files)
    rng.shuffle(order)
    listing = [str(root / name) for name in order]
    prompt = render_base_prompt(today, item.question, None, listing, CLI_TOOL_NAME)
    return ConsumerRun(item=item, state=state, rep=0, root=root, prompt=prompt, order=order)


def consumer_from_writer_repo(item: Item, others: list[Item], repo: Path, harness: dict,
                               rng: random.Random) -> ConsumerRun:
    """Stage E: the consumer meets whatever the writer actually left behind.

    The deterministic writer signals cannot separate "synced" from "mentions the
    new value somewhere", because `f_old` legitimately survives in a document
    that was correctly updated — the probe found one where the old value is a
    row in a table of alternatives. Rather than build a semantic grader for the
    document, the pipeline is closed: a fresh consumer answers the question
    against the repository as it stands, which is the end-to-end quantity the
    experiment is about anyway.
    """
    root = Path(tempfile.mkdtemp(prefix="okf-corpus-"))
    files = {
        "settings.yaml": (repo / "config" / "settings.yaml").read_text(encoding="utf-8"),
        item.superseded_filename: (repo / "docs" / item.superseded_filename).read_text(encoding="utf-8"),
    }
    pool = [o for o in others if o.id != item.id]
    for other, role in rng.sample([(o, r) for o in pool for r in ("superseded", "current")], 6):
        name = other.superseded_filename if role == "superseded" else other.current_filename
        if name in files:
            continue
        files[name] = other.superseded_text if role == "superseded" else other.current_text
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    order = list(files)
    rng.shuffle(order)
    prompt = render_base_prompt(harness["today"], item.question, None,
                                [str(root / n) for n in order], CLI_TOOL_NAME)
    return ConsumerRun(item=item, state="writer_output", rep=0, root=root, prompt=prompt, order=order)


def build_consumer_command(harness: dict, prompt: str) -> list[str]:
    return [
        "claude", "-p",
        "--model", harness["model"],
        "--effort", harness["effort"],
        "--output-format", "json",
        "--allowedTools", CLI_TOOL_NAME,
        "--permission-mode", "dontAsk",
        "--system-prompt", CONSUMER_SYSTEM_PROMPT,
        "--safe-mode",
        "--settings", CLI_SETTINGS,
        prompt,
    ]


def consumer_preflight(run: ConsumerRun, harness: dict) -> list[str]:
    """The checks #40 paid for, applied to this stage's corpus."""
    errors = []
    if run.item.f_old in run.prompt:
        errors.append("leakage: f_old appears in the rendered prompt")
    if run.item.f_new in run.prompt:
        errors.append("leakage: f_new appears in the rendered prompt")
    if len(set(run.order)) != len(run.order):
        errors.append("duplicate filenames in the corpus")
    settings = (run.root / "settings.yaml").read_text(encoding="utf-8")
    if run.item.f_new not in settings:
        errors.append("the implementation artifact does not state the current value")
    if run.state != "synced":
        doc = (run.root / run.item.superseded_filename).read_text(encoding="utf-8")
        if run.item.f_old not in doc:
            errors.append("the stale document does not state the superseded value")
    return errors


def run_consumer(harness: dict, run: ConsumerRun) -> dict:
    command = build_consumer_command(harness, run.prompt)
    completed = subprocess.run(command, cwd=run.root, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=900)
    if completed.returncode != 0:
        raise RuntimeError(f"claude exited {completed.returncode}: {completed.stderr[-400:]}")
    payload = json.loads(completed.stdout)
    text = payload.get("result") or ""
    if payload.get("is_error"):
        raise RuntimeError(f"claude reported an error: {text[:300]}")
    return {
        "stage": "consumer",
        "item": run.item.id,
        "shape": run.item.shape,
        "state": run.state,
        "rep": run.rep,
        "answer": extract_answer(text) or "",
        "grade": grade(text, run.item.f_old, run.item.f_new),
        "session_id": payload.get("session_id"),
        "cost_usd": payload.get("total_cost_usd"),
        "model": harness["model"],
        "request": {"command": shlex.join(command), "cwd": str(run.root)},
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def selected_items() -> list[Item]:
    """#40's surviving items: validated traps, selected on calibration data that
    never entered its result and never enters this one."""
    plan = yaml.safe_load((TRUST_DIR / "measurement-plan.yaml").read_text(encoding="utf-8"))
    keep = set(plan["items"])
    return [i for i in discover_items() if i.id in keep]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=["writer", "consumer", "endtoend"], required=True)
    ap.add_argument("--items", type=int, default=8, help="how many items to use")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--arms", default=None, help="writer: comma-separated (gate,nogate)")
    ap.add_argument("--states", default=None, help="consumer: comma-separated corpus states")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    harness = load_harness()
    # A fixed-seed sample rather than the first n: sorted order is alphabetical
    # by shape, so a prefix would silently make the item set one or two shapes.
    pool = selected_items()
    items = sorted(random.Random(args.seed).sample(pool, min(args.items, len(pool))),
                    key=lambda i: i.id)
    all_items = discover_items()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()

    jobs: list = []
    if args.stage == "endtoend":
        arms = (args.arms or "nogate,gate").split(",")
        for arm in arms:
            for item in items:
                for rep in range(args.reps):
                    root = build_writer_repo(item, arm)
                    jobs.append(WriterRun(item=item, arm=arm, rep=rep, root=root,
                                           prompt=writer_prompt(item, arm, root)))
    elif args.stage == "writer":
        arms = (args.arms or "nogate,gate").split(",")
        for arm in arms:
            for item in items:
                for rep in range(args.reps):
                    root = build_writer_repo(item, arm)
                    jobs.append(WriterRun(item=item, arm=arm, rep=rep, root=root,
                                           prompt=writer_prompt(item, arm, root)))
    else:
        states = (args.states or ",".join(STATES)).split(",")
        for state in states:
            for item in items:
                for rep in range(args.reps):
                    rng = random.Random(f"{args.seed}:{item.id}:{state}:{rep}")
                    run = build_consumer_corpus(item, all_items, state, harness, rng)
                    run.rep = rep
                    errors = consumer_preflight(run, harness)
                    if errors:
                        print(f"ABORT {item.id} {state} rep{rep}: {errors}", file=sys.stderr)
                        shutil.rmtree(run.root, ignore_errors=True)
                        continue
                    jobs.append(run)

    print(f"{len(jobs)} run(s) planned", file=sys.stderr)
    if args.dry_run:
        for job in jobs:
            label = getattr(job, "arm", None) or getattr(job, "state", "")
            print(f"OK {job.item.id} {label} rep{job.rep}")
        return 0

    failures = 0

    def execute(job) -> None:
        nonlocal failures
        try:
            if args.stage == "endtoend":
                row = run_writer(harness, job)
                rng = random.Random(f"{args.seed}:{job.item.id}:{job.arm}:{job.rep}")
                consumer = consumer_from_writer_repo(job.item, all_items, job.root, harness, rng)
                consumer.rep = job.rep
                answer = run_consumer(harness, consumer)
                row = {**row, "stage": "endtoend", "consumer": answer,
                        "grade": answer["grade"], "answer": answer["answer"],
                        "cost_usd": (row.get("cost_usd") or 0) + (answer.get("cost_usd") or 0)}
            elif args.stage == "writer":
                row = run_writer(harness, job)
            else:
                row = run_consumer(harness, job)
        except Exception as exc:  # noqa: BLE001 - one run must not end the batch
            with lock:
                failures += 1
            print(f"FAILED {job.item.id}: {exc}", file=sys.stderr)
            return
        line = json.dumps(row) + "\n"
        with lock:
            with args.out.open("a", encoding="utf-8") as f:
                f.write(line)

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(execute, jobs))

    print(f"done: {len(jobs) - failures} recorded, {failures} failed", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
