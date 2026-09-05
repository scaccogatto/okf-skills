// ---- injected above this line by build_workflow.py: meta, ANALYZER_MD, WEAVER_MD, UNITS_SOLO, UNITS_BATCHED, LIVE_IDS, P ----

const ALL_ARMS = [
  { key: 'A-sonnet-solo', model: 'sonnet', units: UNITS_SOLO },
  { key: 'B-haiku-solo', model: 'haiku', units: UNITS_SOLO },
  { key: 'C-sonnet-batched', model: 'sonnet', units: UNITS_BATCHED },
  { key: 'D-haiku-batched', model: 'haiku', units: UNITS_BATCHED },
]
const smoke = args && args.smoke
const mapOnly = smoke || (args && args.mapOnly)
const arms = smoke
  ? [{ key: 'S-haiku-smoke', model: 'haiku', units: args.smokeUnits }]
  : args && args.run2
    ? [{ key: 'A2-sonnet-solo', model: 'sonnet', units: UNITS_SOLO }, { key: 'B2-haiku-solo', model: 'haiku', units: UNITS_SOLO }]
    : args && args.run3
      ? [{ key: 'B3-haiku-solo', model: 'haiku', units: UNITS_SOLO }]
      : ALL_ARMS.filter(a => !args || !args.arms || args.arms.includes(a.key))
const POOL = (args && args.pool) || 10
const WEAVE_CHUNK = (args && args.weaveChunk) || 25

// Bounded concurrency across all arms: the repo's own benchmarks lost runs to high concurrency.
async function pool(limit, fns) {
  const results = new Array(fns.length)
  let next = 0
  async function worker() {
    while (next < fns.length) {
      const i = next++
      try { results[i] = await fns[i]() } catch (e) { results[i] = null }
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, fns.length) }, worker))
  return results
}
const chunk = (xs, n) => Array.from({ length: Math.ceil(xs.length / n) }, (_, i) => xs.slice(i * n, i * n + n))
const skipFlags = P.skipGlobs.map(g => `--skip-globs "${g}"`).join(' ')

const ANALYZER_SCHEMA = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          event_id: { type: 'string' },
          path: { type: 'string' },
          candidates: { type: 'integer' },
          truncated: { type: 'boolean' },
          failed: { type: 'string' },
        },
        required: ['event_id'],
      },
    },
  },
  required: ['results'],
}
const WEAVER_SCHEMA = {
  type: 'object',
  properties: {
    folded: { type: 'integer' }, created: { type: 'integer' }, updated: { type: 'integer' },
    bullets: { type: 'integer' }, conflicts: { type: 'integer' }, truncated_inputs: { type: 'integer' },
    last_id: { type: 'string' },
  },
  required: ['folded', 'last_id'],
}
const FINALIZE_SCHEMA = {
  type: 'object',
  properties: {
    coverage_ok: { type: 'boolean' }, unmapped: { type: 'array', items: { type: 'string' } },
    validate_ok: { type: 'boolean' }, validate_errors: { type: 'integer' }, validate_warnings: { type: 'integer' },
    antidegen_ok: { type: 'boolean' }, antidegen_notes: { type: 'string' },
    concept_count: { type: 'integer' }, concepts_by_dir: { type: 'object' }, log_bullets: { type: 'integer' },
  },
  required: ['coverage_ok', 'validate_ok', 'antidegen_ok', 'concept_count'],
}

const armDir = arm => `${P.bench}/arms/${arm.key}`

function analyzerPrompt(arm, ids) {
  const out = `${armDir(arm)}/analyses`
  return `${ANALYZER_MD}

---

# Task

Analyze ${ids.length === 1 ? 'this event' : `these ${ids.length} events, each from its own evidence only`}:
${ids.map(i => `- ${i}`).join('\n')}

- events: ${P.events}
- repo: ${P.repo}
- out: ${out} (run \`mkdir -p ${out}\` first)
- emitter: ${P.emitter} (always append: ${skipFlags})

Return the per-event results as structured output (event_id, path, candidates, truncated; or failed with a one-phrase reason).`
}

function weaverPrompt(arm, ids, i, n) {
  const bundle = `${armDir(arm)}/okf`
  return `${WEAVER_MD}

---

# Task (batch ${i + 1} of ${n})

- Bundle directory (this is the \`.okf/\` of this run): ${bundle}
- Analyses directory: ${armDir(arm)}/analyses (file per event: id with every \`:\` replaced by \`-\`, plus \`.md\`)
- Cursor: ${bundle}/.backfill-state.json
- Repository root (context only, never modify): ${P.repo}
${i === 0 ? `- Bootstrap first if ${bundle}/index.md is missing: \`mkdir -p ${bundle}\`, write \`okf_version: "0.2"\` as the only line of ${bundle}/index.md and \`# Update Log\` as the only line of ${bundle}/log.md, and the cursor \`{"last_id": null, "done": 0}\`.` : '- The bundle already exists from the previous batch; continue from the cursor.'}

Fold exactly these live events, in this order (skip any whose analysis file is missing and count it as a conflict):
${ids.map(x => `- ${x}`).join('\n')}

Return the counts as structured output.`
}

function finalizePrompt(arm) {
  const bundle = `${armDir(arm)}/okf`
  return `You are finalizing a reconstructed OKF bundle at ${bundle} (it plays the role of \`.okf/\`). Do exactly these steps with Bash, then return the structured result. Never modify anything outside ${bundle}.

1. Write \`index.md\` per directory by hand: for every subdirectory of ${bundle} that holds concept files, write \`<dir>/index.md\` with one \`# Section\` header and one bullet per concept: \`* [Title](file.md) - description\`, taking title and description from each concept's frontmatter. The root ${bundle}/index.md keeps its \`okf_version: "0.2"\` frontmatter line (make it proper YAML frontmatter between \`---\` lines if it is a bare line), a title, and a section that links every subdirectory's index.md.
2. Append to ${bundle}/log.md a final entry under a \`## ${P.today}\` heading: \`- **Backfill**: reconstructed from ${LIVE_IDS.length} events by okf-backfill/0.9.3\`.
3. Delete ${bundle}/.backfill-state.json.
4. Anti-degeneration self-checks (report each as pass/fail in antidegen_notes):
   - \`! find ${bundle} -name "*.md" | grep -E "merge-pull-request|(^|/)(feat|fix|chore|docs)[:-]"\`
   - \`! find ${bundle} -name "*.md" | grep -E "[^a-z0-9/._-]"\` (path prefix excluded: run it on paths relative to the bundle)
   - \`awk 'p==$0 && /^- / {exit 1} {p=$0}' ${bundle}/log.md\`
5. Coverage: \`uv run ${P.emitter} --check-coverage ${P.events} ${bundle}\`; record exit code and the unmapped ids if any.
6. Validation: \`uv run ${P.validate} ${bundle} --strict\`; record pass/fail and the error/warning counts. If it fails on index or frontmatter shape problems that step 1 should have produced, fix those and re-run once; do not touch concept bodies.
7. Count concept files per directory (exclude index.md, log.md) and the \`- \` bullets in log.md.

Return: coverage_ok, unmapped, validate_ok, validate_errors, validate_warnings, antidegen_ok, antidegen_notes, concept_count, concepts_by_dir, log_bullets.`
}

// ---- Map: all arms interleaved, bounded pool ----
phase('Map')
const thunks = []
const maxUnits = Math.max(...arms.map(a => a.units.length))
for (let i = 0; i < maxUnits; i++) {
  for (const arm of arms) {
    const ids = arm.units[i]
    if (!ids) continue
    thunks.push(() => agent(analyzerPrompt(arm, ids), {
      label: `${arm.key} #${i} (${ids.length})`, phase: 'Map', model: arm.model, effort: 'medium', schema: ANALYZER_SCHEMA,
    }).then(r => ({ arm: arm.key, unit: i, ids, r })))
  }
}
log(`Map: ${thunks.length} analyzer calls across ${arms.length} arm(s), pool ${POOL}`)
const mapResults = (await pool(POOL, thunks)).filter(Boolean)
const mapSummary = {}
for (const arm of arms) {
  const rs = mapResults.filter(x => x.arm === arm.key)
  const events = rs.flatMap(x => (x.r && x.r.results) || [])
  mapSummary[arm.key] = {
    calls_planned: arm.units.length, calls_returned: rs.length,
    events_reported: events.length, events_failed: events.filter(e => e.failed).length,
    truncated_reported: events.filter(e => e.truncated).length,
    candidates_total: events.reduce((s, e) => s + (e.candidates || 0), 0),
  }
  log(`${arm.key}: ${rs.length}/${arm.units.length} calls returned, ${events.length} events reported`)
}
if (mapOnly) return { mapSummary, mapResults: smoke ? mapResults : undefined }

// ---- Reduce: one sequential weaver chain per arm, arms in parallel ----
phase('Reduce')
const chunks = chunk(LIVE_IDS, WEAVE_CHUNK)
const reduceResults = await parallel(arms.map(arm => async () => {
  const replies = []
  for (let i = 0; i < chunks.length; i++) {
    const r = await agent(weaverPrompt(arm, chunks[i], i, chunks.length), {
      label: `${arm.key} weave ${i + 1}/${chunks.length}`, phase: 'Reduce', model: 'sonnet', effort: 'high', schema: WEAVER_SCHEMA,
    })
    replies.push(r)
    log(`${arm.key} weave ${i + 1}/${chunks.length}: ${r ? `folded=${r.folded} created=${r.created} updated=${r.updated}` : 'NULL'}`)
  }
  return { arm: arm.key, replies }
}))

// ---- Finalize: indices, checks, counts per arm ----
phase('Finalize')
const finalizeResults = await parallel(arms.map(arm => () =>
  agent(finalizePrompt(arm), { label: `${arm.key} finalize`, phase: 'Finalize', model: 'sonnet', effort: 'low', schema: FINALIZE_SCHEMA })
    .then(r => ({ arm: arm.key, r }))))

return { mapSummary, reduce: reduceResults.filter(Boolean), finalize: finalizeResults.filter(Boolean) }
