#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6", "anthropic"]
# ///
"""Trial runner for the OKF trust benchmark (PROTOCOL.md).

Assembles trial directories (§8: item pair + 6 distractors), runs the
executable preflight checks (§10 integrity checks, §8 corpus-delivery
constraints) that ABORT rather than warn, then drives one fresh
tool-use conversation per (item, arm, repetition) against the frozen
harness config in harness.yaml. Every value that harness.yaml declares
is read from it, never hardcoded here.

B-arm documents are not authored separately: they are derived at run
time by stripping each source document's frontmatter down to exactly
`type`/`title`/`description` (§9's "which arms carry full frontmatter"
comment in harness.yaml -> `full_frontmatter_arms`). This is what makes
the §10 byte-identity requirement hold by construction; the preflight
check only has to confirm the derivation did what it claims.

Run:
  uv run benchmark/trust/run.py --phase calibration [--dry-run]
  uv run benchmark/trust/run.py --phase measurement [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import random
import shlex
import subprocess
import threading
import zlib
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

TRUST_DIR = Path(__file__).resolve().parent
CORPUS_DIR = TRUST_DIR / "corpus"

# Reuse the frontmatter splitter from okf_validate.py rather than writing a
# second parser (task instructions: copy file conventions, reuse the helper).
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "skills" / "validate" / "scripts")
)
from okf_validate import split_frontmatter  # noqa: E402

FRONTMATTER_KEEP = ("type", "title", "description")

# The single tool the model uses to read the corpus directory (§8: "read
# through a file-read tool"). No input_schema beyond the one string param, so
# no need for the schema-less Anthropic-defined tool types.
READ_FILE_TOOL = {
    "name": "read_file",
    "description": "Read one document from the corpus by its filename.",
    "input_schema": {
        "type": "object",
        "properties": {"filename": {"type": "string"}},
        "required": ["filename"],
    },
}


# The `claude` CLI backend (§8, rev 6). The session's own model access stands in
# for API credentials this environment does not have; `Read` stands in for
# `read_file`. The consumer's framing is stated here rather than left to the
# CLI's default so it is frozen in the pre-registration package like everything
# else, and one allowed tool plus `--permission-mode dontAsk` keeps a trial from
# touching anything but the corpus directory it was handed.
#
# `--safe-mode` is load-bearing and was arrived at by measurement, not by
# reading the flag list: an earlier `--settings '{"hooks": {}}'` did *not* stop
# this machine's SessionStart hooks, its user-level CLAUDE.md or its skill
# listing from entering a trial. Asked to quote what preceded its prompt, a
# trial under that configuration read back a persona instruction and the
# maintainer's global coding rules. Safe mode removes hooks, CLAUDE.md, plugins,
# skills and MCP servers; what remains is the CLI's own boilerplate (the
# deferred-tool and agent-type reminders), identical in every arm and declared
# in §8 rather than assumed away.
CLI_TOOL_NAME = "Read"
CLI_SYSTEM_PROMPT = (
    "You answer questions from a corpus of documents. Read the documents you are "
    "given and answer only from them."
)


class PreflightError(Exception):
    """Raised to abort a run (§8/§10: aborts, never warnings)."""


# --------------------------------------------------------------------------
# Harness + corpus loading
# --------------------------------------------------------------------------


def load_harness(path: Path = TRUST_DIR / "harness.yaml") -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Item:
    id: str
    shape: str
    question: str
    f_old: str
    f_new: str
    superseded_filename: str
    current_filename: str
    superseded_text: str
    current_text: str


def discover_items(corpus_dir: Path = CORPUS_DIR) -> list[Item]:
    """Every item.yaml under corpus_dir becomes one Item.

    Does not enforce harness.yaml's `calibration.candidates` count: that
    number documents the intended corpus size, it is not an operational
    input (the corpus currently has 1 item; tests build their own).
    """
    items = []
    for item_yaml in sorted(corpus_dir.rglob("item.yaml")):
        meta = yaml.safe_load(item_yaml.read_text(encoding="utf-8"))
        item_dir = item_yaml.parent
        superseded_text = (item_dir / meta["superseded"]["source"]).read_text(encoding="utf-8")
        current_text = (item_dir / meta["current"]["source"]).read_text(encoding="utf-8")
        items.append(
            Item(
                id=meta["id"],
                shape=meta["shape"],
                question=meta["question"],
                f_old=meta["f_old"],
                f_new=meta["f_new"],
                superseded_filename=meta["superseded"]["filename"],
                current_filename=meta["current"]["filename"],
                superseded_text=superseded_text,
                current_text=current_text,
            )
        )
    return items


# --------------------------------------------------------------------------
# Frontmatter derivation (the core arm rule)
# --------------------------------------------------------------------------


def strip_frontmatter_to_core(text: str) -> str:
    """Derive the B-arm variant: keep only type/title/description, body untouched.

    Nothing is authored twice (PROTOCOL §5/§9); this is the one derivation
    point, so §10 byte-identity holds by construction.
    """
    raw, body = split_frontmatter(text)
    if raw is None:
        raise PreflightError("document has no frontmatter block to derive from")
    meta = yaml.safe_load(raw) or {}
    core = {k: meta[k] for k in FRONTMATTER_KEEP if k in meta}
    stripped_yaml = yaml.safe_dump(core, sort_keys=False, allow_unicode=True)
    return f"---\n{stripped_yaml}---\n{body}"


def parsed_meta(text: str) -> dict:
    raw, _ = split_frontmatter(text)
    return yaml.safe_load(raw) if raw else {}


def assert_derivation_identity(full_text: str, stripped_text: str) -> list[str]:
    """§10 field identity check: body AND type/title/description byte-identical
    between the full and stripped variant of the same document.

    Comparing parsed values, not raw YAML bytes: re-serialization does not
    reproduce the source bytes (quoting/order), so "byte-identical" here means
    the body text is byte-identical and the three field *values* match.
    """
    _, full_body = split_frontmatter(full_text)
    _, stripped_body = split_frontmatter(stripped_text)
    mismatches = []
    if full_body != stripped_body:
        mismatches.append("body differs between full and stripped variant")
    full_meta = parsed_meta(full_text)
    stripped_meta = parsed_meta(stripped_text)
    for key in FRONTMATTER_KEEP:
        if full_meta.get(key) != stripped_meta.get(key):
            mismatches.append(f"{key!r} differs between full and stripped variant")
    return mismatches


# --------------------------------------------------------------------------
# Trial assembly (§8)
# --------------------------------------------------------------------------


def _to_date(value) -> date | None:
    """Normalize a stale_after/today value to a date.

    PyYAML resolves an unquoted `stale_after:` to a `datetime.date`, but
    harness.yaml's `today` is a quoted string; both must compare equal.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))


@dataclass
class Doc:
    filename: str
    role: str  # "target-superseded" | "target-current" | "distractor"
    source_text: str  # original, full-frontmatter authored text
    status: str | None
    stale_after: date | None
    rendered_text: str  # what actually goes in the trial directory for this arm


@dataclass
class Trial:
    item: Item
    arm: str
    rep: int
    root: Path
    docs: list[Doc]
    order: list[str]  # randomised filename order (§8: directory position)
    prompt: str
    seed: int  # the per-trial assembly seed, recorded so one row can be rebuilt


def _render_for_arm(source_text: str, arm: str, full_frontmatter_arms: list[str]) -> str:
    if arm in full_frontmatter_arms:
        return source_text
    return strip_frontmatter_to_core(source_text)


def _doc_from_source(filename: str, role: str, source_text: str, arm: str, full_frontmatter_arms: list[str]) -> Doc:
    meta = parsed_meta(source_text)
    return Doc(
        filename=filename,
        role=role,
        source_text=source_text,
        status=meta.get("status"),
        stale_after=_to_date(meta.get("stale_after")),
        rendered_text=_render_for_arm(source_text, arm, full_frontmatter_arms),
    )


def choose_distractors(item: Item, other_items: list[Item], rng: random.Random, count: int, min_deprecated: int) -> list[tuple[Item, str]]:
    """Pick `count` (other_item, role) pairs satisfying the corpus-assembly
    constraints by construction (§8):
      - at least `min_deprecated` are deprecated-status source docs
      - at least one is a fresh (non-deprecated) source doc, so stale_after
        dates straddle `today` in both directions
    These are properties of the underlying document, independent of the arm's
    visible frontmatter (a B-arm distractor still "is" deprecated even though
    the word does not appear on the page).
    """
    others = [o for o in other_items if o.id != item.id]
    supers = [(o, "superseded") for o in others]  # deprecated, stale_after in the past
    currents = [(o, "current") for o in others]  # fresh, stale_after in the future
    available = len(supers) + len(currents)
    if available < count:
        raise PreflightError(
            f"need {count} distractors from other items, {available} available: "
            f"corpus has {len(other_items)} item(s)"
        )
    if len(supers) < min_deprecated:
        raise PreflightError(
            f"need >= {min_deprecated} deprecated distractors, only {len(supers)} other item(s) available"
        )
    if not currents:
        raise PreflightError("need >= 1 fresh distractor to straddle `today`, none available")

    chosen_dep = rng.sample(supers, min_deprecated)
    chosen_fresh = rng.sample(currents, 1)
    remaining_pool = [p for p in supers + currents if p not in chosen_dep and p not in chosen_fresh]
    remaining_needed = count - len(chosen_dep) - len(chosen_fresh)
    if remaining_needed > len(remaining_pool):
        raise PreflightError(
            f"need {count} distractors total, only {len(chosen_dep) + len(chosen_fresh) + len(remaining_pool)} available"
        )
    chosen_rest = rng.sample(remaining_pool, remaining_needed)
    chosen = chosen_dep + chosen_fresh + chosen_rest
    rng.shuffle(chosen)
    return chosen


def render_base_prompt(today: str, question: str, instruction: str | None, order: list[str],
                       tool_name: str = "read_file") -> str:
    """§8 base prompt: identical across arms, answer only from the corpus,
    states the injected date, forces the `ANSWER: <value>` schema. The arm
    instruction (harness.yaml `instructions`) is appended for B1/A1 only.

    `order` is the randomised directory listing (§8: file order and directory
    position of the target pair are randomised per trial), without naming the
    files here the model has no way to invoke read_file at all.
    """
    listing = "\n".join(f"- {name}" for name in order)
    parts = [
        "Answer the question below using only the documents in this corpus, "
        f"which you can read with the {tool_name} tool. Available documents:",
        listing,
        f"Today's date is {today}.",
    ]
    if instruction:
        parts.append(instruction)
    parts.append(f"Question: {question}")
    # Rev 7. "ANSWER: <value>" alone produced "The higher-priority task (priority
    # descending; submission time breaks ties)" — an answer that asserts the
    # value and grades `neither`, which loses the item for a reason that has
    # nothing to do with what it measures. The refusal token is the other half:
    # without somewhere to put "I cannot tell", a hedge lands in the value field
    # and is indistinguishable from a verbose commitment.
    parts.append(
        "End your response with a line of the exact form: ANSWER: <value>\n"
        "<value> must be the bare value and nothing else: no explanation, no "
        "citation, no parenthesis. If you cannot commit to a single value, "
        "write: ANSWER: unknown")
    return "\n\n".join(parts)


def trial_seed(run_seed: int, arm: str, item_id: str, rep: int) -> int:
    """A stable per-trial seed derived from the run seed and the trial's identity.

    A single RNG threaded through every trial would make a row reproducible only
    by replaying the whole run in the same order. Deriving the seed from
    (run_seed, arm, item, rep) makes each trial rebuildable on its own, which is
    what the published transcripts need to be checkable one at a time.
    """
    return zlib.crc32(f"{run_seed}:{arm}:{item_id}:{rep}".encode()) & 0xFFFFFFFF


def assemble_trial(item: Item, other_items: list[Item], arm: str, rep: int, harness: dict,
                    rng: random.Random | None = None, run_seed: int = 0,
                    backend: str = "api") -> Trial:
    seed = trial_seed(run_seed, arm, item.id, rep)
    rng = rng if rng is not None else random.Random(seed)
    full_frontmatter_arms = harness["full_frontmatter_arms"]
    today = harness["today"]

    target_superseded = _doc_from_source(
        item.superseded_filename, "target-superseded", item.superseded_text, arm, full_frontmatter_arms
    )
    target_current = _doc_from_source(
        item.current_filename, "target-current", item.current_text, arm, full_frontmatter_arms
    )

    distractor_picks = choose_distractors(
        item, other_items, rng, harness["distractors"], harness["min_deprecated_distractors"]
    )
    distractor_docs = []
    for other, role in distractor_picks:
        source_text = other.superseded_text if role == "superseded" else other.current_text
        filename = other.superseded_filename if role == "superseded" else other.current_filename
        distractor_docs.append(_doc_from_source(filename, "distractor", source_text, arm, full_frontmatter_arms))

    docs = [target_superseded, target_current, *distractor_docs]
    order = [d.filename for d in docs]
    rng.shuffle(order)  # §8: file order and directory position randomised per trial

    # Neutral directory name (§6, rev 6): the CLI backend hands this path to the
    # model, and a path spelling out the item and the arm would leak the
    # experiment's design through a channel the API backend never had.
    root = Path(tempfile.mkdtemp(prefix="okf-corpus-"))
    for doc in docs:
        (root / doc.filename).write_text(doc.rendered_text, encoding="utf-8")

    instruction = harness["instructions"].get(arm)
    # The CLI's Read tool takes absolute paths, so the listing names them there;
    # the API backend's read_file takes a bare filename and keeps one.
    listing = [str(root / name) for name in order] if backend == "cli" else order
    tool_name = CLI_TOOL_NAME if backend == "cli" else "read_file"
    prompt = render_base_prompt(today, item.question, instruction, listing, tool_name)

    return Trial(item=item, arm=arm, rep=rep, root=root, docs=docs, order=order,
                 prompt=prompt, seed=seed)


# --------------------------------------------------------------------------
# Preflight checks (§8, §10): every one aborts the run, never warns
# --------------------------------------------------------------------------


def preflight(trial: Trial, harness: dict) -> list[str]:
    errors: list[str] = []
    full_frontmatter_arms = harness["full_frontmatter_arms"]
    is_full_arm = trial.arm in full_frontmatter_arms
    today = _to_date(harness["today"])

    # filename collisions would silently overwrite one doc with another on
    # disk, leaving fewer than target-pair + `distractors` documents present
    filenames = [d.filename for d in trial.docs]
    if len(set(filenames)) != len(filenames):
        errors.append("duplicate filenames among trial documents, would overwrite on disk")

    # distractor frontmatter matches the arm
    for doc in trial.docs:
        if doc.role != "distractor":
            continue
        raw, _ = split_frontmatter(doc.rendered_text)
        rendered_keys = set(yaml.safe_load(raw) or {}) if raw else set()
        if is_full_arm:
            if rendered_keys <= set(FRONTMATTER_KEEP):
                errors.append(f"{doc.filename}: distractor should carry full frontmatter in arm {trial.arm}")
        else:
            if rendered_keys - set(FRONTMATTER_KEEP):
                errors.append(f"{doc.filename}: distractor should be stripped to core fields in arm {trial.arm}")

    # min_deprecated_distractors
    deprecated_count = sum(1 for d in trial.docs if d.role == "distractor" and d.status == "deprecated")
    if deprecated_count < harness["min_deprecated_distractors"]:
        errors.append(
            f"only {deprecated_count} deprecated distractor(s), need >= {harness['min_deprecated_distractors']}"
        )

    # stale_after straddles today in both directions, among distractors
    distractor_dates = [d.stale_after for d in trial.docs if d.role == "distractor" and d.stale_after]
    if not any(sa < today for sa in distractor_dates):
        errors.append("no distractor stale_after date falls before `today`")
    if not any(sa > today for sa in distractor_dates):
        errors.append("no distractor stale_after date falls after `today`")

    # §8 rev 5: "today" sits BETWEEN the two documents of every item. On or after
    # the superseded doc's stale_after, so the spec's `today >= stale_after` rule
    # actually fires where it is under test; and strictly before the
    # replacement's, because a replacement that also reads stale leaves the
    # treatment arm no fresh answer to give and quietly breaks the item.
    for doc in trial.docs:
        if doc.status == "deprecated" and doc.stale_after and doc.stale_after > today:
            errors.append(f"{doc.filename}: `today` ({today}) is before this deprecated doc's stale_after")
    for doc in trial.docs:
        if doc.role != "target-current" or doc.stale_after is None:
            continue
        if doc.stale_after <= today:
            errors.append(
                f"{doc.filename}: the replacement's stale_after ({doc.stale_after}) is not "
                f"after `today` ({today}), so this item has no fresh answer left")

    # §10 no-leakage: rendered prompt contains neither f_old nor f_new
    if trial.item.f_old in trial.prompt:
        errors.append("leakage: f_old appears in the rendered prompt")
    if trial.item.f_new in trial.prompt:
        errors.append("leakage: f_new appears in the rendered prompt")

    # §10 field identity: derivation is correct for every document in the trial
    for doc in trial.docs:
        mismatches = assert_derivation_identity(doc.source_text, strip_frontmatter_to_core(doc.source_text))
        errors.extend(f"{doc.filename}: {m}" for m in mismatches)

    # neutral filenames: authoring names must never appear in the assembled directory
    for doc in trial.docs:
        if doc.filename in ("superseded.md", "current.md"):
            errors.append(f"authoring filename {doc.filename!r} leaked into the trial directory")

    return errors


# --------------------------------------------------------------------------
# Request assembly + tool-use loop (impure edge)
# --------------------------------------------------------------------------


def build_request(harness: dict, trial: Trial) -> dict:
    return {
        "model": harness["model"],
        "max_tokens": harness["max_tokens"],
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": harness["effort"]},
        "tools": [READ_FILE_TOOL],
        "messages": [{"role": "user", "content": trial.prompt}],
    }


def read_file_from_trial(trial: Trial, filename: str) -> str:
    target = (trial.root / filename).resolve()
    if target.parent != trial.root.resolve() or not target.is_file():
        return f"error: no such file {filename!r}"
    return target.read_text(encoding="utf-8")


def run_one_trial(client, harness: dict, trial: Trial) -> dict:
    """The only impure step: one fresh conversation, no shared context (§10)."""
    # Lazy import keeps dry-run and the tests free of an API dependency. Both
    # names come from grade.py: a second local extract_answer would let the
    # recorded `answer` drift from the `grade` computed beside it.
    from grade import extract_answer, grade

    request = build_request(harness, trial)
    # The assembly seed decides which distractors were drawn and in what order,
    # so a row without it cannot be rebuilt from the corpus alone.
    messages = list(request["messages"])
    response = None
    while True:
        response = client.messages.create(**{**request, "messages": messages})
        if response.stop_reason != "tool_use":
            break
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = read_file_from_trial(trial, block.input["filename"])
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )
        messages.append({"role": "user", "content": tool_results})

    final_text = "".join(b.text for b in response.content if b.type == "text")
    answer = extract_answer(final_text) or ""
    grade_result = grade(final_text, trial.item.f_old, trial.item.f_new)

    return {
        "item": trial.item.id,
        "shape": trial.item.shape,
        "arm": trial.arm,
        "rep": trial.rep,
        "assembly_seed": trial.seed,
        "answer": answer,
        "grade": grade_result,
        "response_id": response.id,
        "stop_reason": response.stop_reason,
        "model": response.model,
        "usage": response.usage.model_dump() if hasattr(response.usage, "model_dump") else dict(response.usage),
        "request": request,
    }


def build_cli_command(harness: dict, trial: Trial) -> list[str]:
    """The `claude` invocation for one trial (§8, rev 6).

    Pure, so the frozen flags are checkable in the test suite rather than only
    by spending a trial on them.
    """
    return [
        "claude", "-p",
        "--model", harness["model"],
        "--effort", harness["effort"],
        "--output-format", "json",
        "--allowedTools", CLI_TOOL_NAME,
        "--permission-mode", "dontAsk",
        "--system-prompt", CLI_SYSTEM_PROMPT,
        "--safe-mode",
        trial.prompt,
    ]


def run_one_trial_cli(harness: dict, trial: Trial) -> dict:
    """One fresh `claude -p` process per trial: the process boundary is what
    carries §10's independence requirement here, in place of a fresh Messages
    conversation. Recorded fields mirror the API backend's row so grade.py and
    analyze.py read either run without knowing which produced it."""
    from grade import extract_answer, grade

    command = build_cli_command(harness, trial)
    completed = subprocess.run(
        command, cwd=trial.root, capture_output=True, text=True,
        stdin=subprocess.DEVNULL, timeout=900,
    )
    if completed.returncode != 0:
        raise PreflightError(f"claude exited {completed.returncode}: {completed.stderr[-500:]}")
    payload = json.loads(completed.stdout)
    final_text = payload.get("result") or ""
    if payload.get("is_error"):
        raise PreflightError(f"claude reported an error: {final_text[:500]}")

    return {
        "item": trial.item.id,
        "shape": trial.item.shape,
        "arm": trial.arm,
        "rep": trial.rep,
        "assembly_seed": trial.seed,
        "answer": extract_answer(final_text) or "",
        "grade": grade(final_text, trial.item.f_old, trial.item.f_new),
        "response_id": payload.get("session_id"),
        "stop_reason": payload.get("stop_reason"),
        "model": harness["model"],
        "usage": payload.get("usage"),
        "cost_usd": payload.get("total_cost_usd"),
        "backend": "cli",
        "request": {"command": shlex.join(command), "cwd": str(trial.root)},
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _completed_trials(outdir: Path) -> set[tuple[str, str, int]]:
    """Which (arm, item, rep) triples the run directory already holds."""
    done: set[tuple[str, str, int]] = set()
    for path in outdir.glob("*.jsonl"):
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                done.add((row["arm"], row["item"], row["rep"]))
    return done


def phase_config(harness: dict, phase: str) -> dict:
    """Resolve a phase block, folding in the measurement plan when there is one.

    Calibration is fully specified up front. Measurement is not, and deliberately
    so (§3.6): the *rule* for picking k and n is committed before calibration and
    the *numbers* fall out of it afterwards. `power.py` writes them to the plan
    file, which has to exist before the measurement run starts.
    """
    config = dict(harness[phase])
    plan_name = config.pop("plan", None)
    if plan_name:
        plan_path = TRUST_DIR / plan_name
        if not plan_path.is_file():
            raise PreflightError(
                f"{phase} needs {plan_path}, which does not exist yet. Run the "
                f"calibration phase, then power.py, before measuring (§7).")
        plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
        config["repetitions"] = plan["repetitions"]
        config["items"] = plan["items"]
    if config.get("repetitions") is None:
        raise PreflightError(f"{phase}.repetitions is unset and no plan supplied it")
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["calibration", "measurement"], required=True)
    parser.add_argument("--dry-run", action="store_true", help="assemble + preflight everything, call no API")
    parser.add_argument("--seed", type=int, default=0, help="trial-assembly RNG seed")
    parser.add_argument("--jobs", type=int, default=1, help="trials to run concurrently (§10: they are independent)")
    parser.add_argument("--backend", choices=["api", "cli"], default="api",
                        help="api: the Messages API (needs credentials); cli: the `claude` CLI (§8, rev 6)")
    args = parser.parse_args(argv)

    harness = load_harness()
    items = discover_items()
    try:
        config = phase_config(harness, args.phase)
    except PreflightError as exc:
        print(f"ABORT: {exc}", file=sys.stderr)
        return 1
    outdir = TRUST_DIR / config["outdir"]

    planned = 0
    aborted = 0
    done: set[tuple[str, str, int]] = set()
    if not args.dry_run:
        outdir.mkdir(parents=True, exist_ok=True)
        # A measurement run is several hundred billed calls. Resuming from what
        # is already on disk means a crash costs the trial it died on, not the
        # whole run. Trials are keyed by (arm, item, rep), which is exactly the
        # independence unit of §10.
        done = _completed_trials(outdir)
        if done:
            print(f"resuming: {len(done)} trial(s) already recorded", file=sys.stderr)
        client = None
        if args.backend == "api":
            import anthropic

            client = anthropic.Anthropic()

    selected = config.get("items")
    if selected:
        items = [i for i in items if i.id in set(selected)]

    # §11 weighting: the primary arms get the k §3.6 derived, the descriptive
    # arms get `descriptive_repetitions`. An arm is primary iff it appears in
    # the §3.1 contrast, so this cannot drift from the analysis.
    primary_arms = set(harness["analysis"]["primary_contrast"])
    descriptive_reps = config.get("descriptive_repetitions", config["repetitions"])

    ready: list[Trial] = []
    for arm in config["arms"]:
        reps = config["repetitions"] if arm in primary_arms else descriptive_reps
        for item in items:
            for rep in range(reps):
                if (arm, item.id, rep) in done:
                    continue
                try:
                    trial = assemble_trial(item, items, arm, rep, harness, run_seed=args.seed,
                                           backend=args.backend)
                except PreflightError as exc:
                    print(f"ABORT (assembly) {item.id} {arm} rep{rep}: {exc}", file=sys.stderr)
                    aborted += 1
                    continue
                errors = preflight(trial, harness)
                if errors:
                    print(f"ABORT (preflight) {item.id} {arm} rep{rep}:", file=sys.stderr)
                    for e in errors:
                        print(f"  - {e}", file=sys.stderr)
                    aborted += 1
                    continue
                planned += 1
                if args.dry_run:
                    print(f"OK {item.id} {arm} rep{rep}: would send {len(trial.docs)} docs, prompt {len(trial.prompt)} chars")
                    continue
                ready.append(trial)

    # Trials are independent by construction (§10), so they run concurrently.
    # The only shared state is the append to the arm's file, which the lock
    # serializes; a failed trial is left unrecorded and the next run's resume
    # logic picks it up rather than the run dying on it.
    failed = 0
    if ready:
        lock = threading.Lock()

        def execute(trial: Trial) -> None:
            nonlocal failed
            try:
                if args.backend == "cli":
                    row = run_one_trial_cli(harness, trial)
                else:
                    row = run_one_trial(client, harness, trial)
            except Exception as exc:  # noqa: BLE001 - one trial must not end the run
                with lock:
                    failed += 1
                print(f"FAILED {trial.item.id} {trial.arm} rep{trial.rep}: {exc}", file=sys.stderr)
                return
            line = json.dumps(row) + "\n"
            with lock:
                with (outdir / f"{trial.arm}.jsonl").open("a", encoding="utf-8") as f:
                    f.write(line)

        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for _ in pool.map(execute, ready):
                pass

    print(f"\n{planned} trial(s) planned, {aborted} aborted, {failed} failed.", file=sys.stderr)
    return 1 if aborted else 0


if __name__ == "__main__":
    raise SystemExit(main())
