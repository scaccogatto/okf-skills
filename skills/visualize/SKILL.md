---
name: visualize
description: >-
  Render an Open Knowledge Format (OKF) bundle as a single self-contained,
  interactive HTML graph (viz.html) — concepts as nodes coloured/sized by type,
  markdown links as edges, a wiki-style detail panel with rendered markdown plus
  "Links to" / "Cited by" backlinks, layout switching, per-type filter and search.
  Use when asked to visualize, graph, preview, or explore an OKF bundle.
user-invocable: true
argument-hint: "[bundle-dir] [-o viz.html]"
allowed-tools: Bash
---

# Visualize an OKF bundle

Generate a self-contained HTML graph of the target bundle (default the project's
`.okf/`). No backend, no install on the viewing side, no data leaves the page.

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/okf_visualize.py" $ARGUMENTS
```

If `uv` is unavailable:

```bash
python3 -m pip install --quiet pyyaml && \
python3 "${CLAUDE_SKILL_DIR}/scripts/okf_visualize.py" $ARGUMENTS
```

The output defaults to `<bundle>/viz.html`. Pass `-o <path>` to write elsewhere.
Bundles above 1,000 concepts default to the linear `concentric` layout (the
force layout freezes the page at that size — `--layout cose` overrides), and
`--max-nodes N` refuses oversized bundles, e.g. for CI.
Open it in any browser; `${CLAUDE_SKILL_DIR}` resolves whether this runs as part
of the `okf` plugin or as a standalone skills.sh skill.
