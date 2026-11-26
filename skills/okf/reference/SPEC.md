<!--
  Vendored from the Open Knowledge Format reference repository.
  Source:  https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md
  Commit:  527e81aff55992be21507e97004286789126f88c
  Note:    earlier homes, GoogleCloudPlatform/open-knowledge-format (deprecated 2026-11-18)
           and GoogleCloudPlatform/knowledge-catalog/okf (frozen 2026-08-21), are no longer updated.
  License: Apache-2.0 (c) Google LLC — included verbatim under its terms.
           Full license text: ./APACHE-2.0.txt
  This is the canonical normative reference loaded by the okf skill.
-->

# Open Knowledge Format (OKF)

**Version 0.3**

OKF is an open format for *knowledge*: the metadata, context, and curated insight about data and systems. People and agents can read it. People write it, agents generate it, organizations exchange it, and people and agents consume it.

The format is intentionally minimal: a directory of Markdown files with YAML frontmatter. OKF has no schema registry, no central authority, and no required tools. If you can `cat` a file, you can read OKF. If you can `git clone` a repository, you can ship it.

This document is self-contained. It specifies all that is necessary to produce and consume OKF v0.3. §13 gives a summary of the changes from v0.2. Appendix B gives a summary of the changes from v0.1 to v0.2.

---

## 1. Motivation

Knowledge representation for AI agents changes quickly, and many incompatible conventions exist. OKF takes the position that the best representation of knowledge uses common, established formats that are:

- **Readable** by humans without tools.
- **Parseable** by agents without special SDKs.
- **Diffable** in version control.
- **Portable** across tools, organizations, and time.

Frequently, people do not write a knowledge corpus one time and then only read it. Agents **write and maintain the corpus continuously**. When agents generate most concepts, a consumer needs answers that a plain Markdown-plus-frontmatter convention does not supply:

1. What was this made from, and how was it verified? (**provenance**)
2. How much can I trust it? (**trust**)
3. Is it still true? (**freshness**)
4. Is it the current version? (**lifecycle**)
5. Was this number made the way that we said it must be? (**attestation**)

OKF makes provenance, trust, freshness, lifecycle, and attestation first-class. The format stays minimally opinionated. It standardizes only the small set of structural conventions that make a knowledge corpus self-describing. The producer decides all other things.

### Goals

1. Define a universal format that **producers** (people, agents, export pipelines) can write.
2. Tell **consumers** (agents, UIs, search indexes, deterministic code) how to read and traverse it.
3. Make the **exchange** of knowledge across systems and organizations easy.
4. Standardize the small set of frontmatter fields that make an agent-maintained corpus **trustable**. Do not prescribe a runtime.

### Non-goals

- Define a fixed taxonomy of concept types.
- Prescribe storage, serving, or query infrastructure.
- Replace domain-specific schemas (Avro, Protobuf, OpenAPI, and others). OKF *refers to* them. It does not replace them.
- Specify a packaging or invocation standard for the code that an executor or attester refers to. OKF fixes the interface, not the packaging.

---

## 2. Terminology

- **Knowledge Bundle** (or **bundle**): A self-contained, hierarchical collection of knowledge documents. The unit of distribution.
- **Bundle root**: The top directory of a bundle. Paths that start with `/` resolve from the bundle root (§6). A bundle-root `index.md` with frontmatter (§8.1) identifies the bundle root when the bundle is a subdirectory of a larger repository.
- **Producer**: A person, agent, or pipeline that writes a bundle.
- **Consumer**: An agent, UI, index, or program that reads a bundle.
- **Concept**: One unit of knowledge in a bundle. A concept is one Markdown document (§3.2). It can describe a tangible asset (a table, an API), an abstract idea (a metric, a business process), or a thing between these two.
- **Concept ID**: The path of the concept's file within the bundle, with the `.md` suffix removed.
- **Asset**: A file in a bundle whose name does not end in `.md`, for example an image or attester code (§3.2). An asset is not a concept.
- **Frontmatter**: A YAML metadata block at the start of a Markdown file, between two `---` lines (§4).
- **Body**: All of the file after the frontmatter.
- **Link**: A standard Markdown link from one concept to a different concept. A link asserts an untyped, directed relationship. Only the directory tree gives the implicit parent/child structure.
- **Path field**: A frontmatter field whose value is a path or a URI (§6.2).
- **Source**: A material that a concept derives from. A source can be external or internal to the bundle. The `sources` frontmatter field records it.
- **Provenance**: The set of sources that a concept derives from.
- **Credibility signal**: An objective fact about one source (`author`, `usage_count`, `last_modified`). Consumers use it to infer trust. OKF records the signals, not a verdict (§5.1).
- **Actor**: A string that identifies who or what did an action (§7).
- **Trust tier**: A level that a consumer calculates from the current `verified` events of a concept: unverified, machine-confirmed, or human-reviewed (§5.3).
- **Attested Computation**: A concept (`type: Attested Computation`) that contains a sanctioned way to compute a value. A consumer can use it to confirm that a run of that computation made the value (§10).
- **Executor**: Run instructions or code that runs a computation and returns a receipt (§10.2).
- **Receipt**: The evidence that a run returns, in the shape that `executor.receipt` declares. A receipt is a runtime artifact. The bundle does not contain it (§10).
- **Attester**: Deterministic code (no LLM) that examines a receipt and returns a verdict (§10.2).
- **Extension key**: A frontmatter key that this specification does not define (§4.1).

---

## 3. Bundle structure

A bundle is a directory tree of Markdown files. The directory structure does not depend on the domain. Producers organize concepts in the way that is best for the knowledge.

```
path/to/bundle/                 # The bundle root.
  index.md                      # Optional. Directory listing, and bundle metadata (§8).
  log.md                        # Optional. Chronological history of changes (§9).
  <concept>.md                  # A concept at the bundle root.
  <asset>                       # Optional. An image, code, or other non-Markdown file.
  <subdirectory>/               # Subdirectories organize concepts into groups.
    index.md
    <concept>.md
    <subdirectory>/
      ...
```

A bundle MAY be distributed as:

- A git repository (RECOMMENDED, because git supplies history, attribution, and diffs).
- A tarball or zip archive of the directory.
- A subdirectory in a larger repository.

### 3.1 Reserved filenames

These filenames have a defined meaning at all levels of the hierarchy. Producers MUST NOT use them for concepts. Consumers MUST NOT treat them as concepts, whatever frontmatter they contain.

| Filename | Purpose |
| :---- | :---- |
| `index.md` | Directory listing and bundle metadata. See §8. |
| `log.md` | History of changes. See §9. |

Tags are first-class through the `tags` frontmatter field (§4.1). OKF does not specify a file format that collects documents by tag. A consumer that shows a tag view can make one when it reads the bundle, from a scan of frontmatter.

### 3.2 Concepts, assets, and other files

A consumer uses these rules to find the concepts in a bundle:

1. A file whose name ends in `.md`, that is not reserved (§3.1), and that has frontmatter with a non-empty `type` (§4.1) is a concept.
2. A `.md` file that has no frontmatter, or no `type` in its frontmatter, is not a concept. Consumers skip it. It does not affect conformance. Validators SHOULD warn about it. This rule lets a bundle contain files such as `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, and `SKILL.md`.
3. A file whose name does not end in `.md` is an asset. An asset MAY be the target of a link or of a path field. A body MAY embed an image asset. An asset is not a concept.
4. Files and directories whose names start with `.` are not part of the bundle.
5. A consumer reads only the files under the bundle root. It does not follow symbolic links that go out of the bundle root.

---

## 4. Concept documents

Each concept is a UTF-8 Markdown file with two parts:

1. A **YAML frontmatter block**.
2. A **Markdown body** with free-form content.

**Frontmatter syntax.** These rules make sure that all tools read the same values:

- The file MUST start with a line that is exactly `---`.
- The block ends at the next line that is exactly `---`.
- The frontmatter MUST parse as a YAML 1.2 mapping with the core schema.
- Producers MUST NOT write duplicate keys. Consumers MAY reject frontmatter that has duplicate keys.
- Producers SHOULD quote values that look like numbers or booleans, for example `okf_version: "0.3"`.
- Producers SHOULD NOT use custom YAML tags.
- A producer that modifies an existing file SHOULD NOT re-serialize values that it did not change. This keeps diffs small.

### 4.1 Frontmatter

```
---
type: <Type name>                  # REQUIRED
title: <Optional display name>
description: <Optional one-line summary>
resource: <Optional canonical URI of the underlying asset>
tags: [<tag>, <tag>, ...]          # Optional
# ... provenance, trust, lifecycle, and computation families (see §5, §10)
# ... extension keys (see "Extensions" below)
---
```

**Required:**

- `type`: A short string that identifies the kind of concept. Consumers use it for routing, filtering, and presentation. Example values: `BigQuery Table`, `BigQuery Dataset`, `API Endpoint`, `Metric`, `Playbook`, `Reference`, `Attested Computation`.

  OKF does not register type values centrally. Consumers MUST accept unknown types. Usually, a consumer treats an unknown type as a generic concept.

`type` is the only key that is always required. A concept that has only `type` is fully conformant (§11).

**Optional:**

- `title`: A display name for humans. If `title` is absent, consumers MAY make a title from the filename.
- `description`: One sentence about the concept. `index.md` generators, search snippets, and previews use it.
- `resource`: A URI that uniquely identifies the underlying asset that the concept describes. Concepts about abstract ideas do not have a `resource`.
- `tags`: A YAML list of short strings for cross-cutting categories.

The optional **provenance**, **trust**, and **lifecycle** families (§5) and the **computation** fields of Attested Computation concepts (§10) can also occur.

**Extensions.** Producers MAY add keys at any level, also inside mappings that this specification defines (for example a `sources` entry, `generated`, a `verified` entry, `executor`, or `attester`). Consumers MUST NOT reject documents that contain unknown keys. A producer that modifies an existing file MUST keep the keys that it does not know. Future OKF versions will not define keys that start with `x-`. Producers SHOULD name their own keys `x-<producer>-<name>`, for example `x-acme-owner`. OKF does not keep a registry of these names.

### 4.2 Body

The body is CommonMark, with GitHub Flavored Markdown (GFM) tables and footnotes in the common `[^label]` form. Producers SHOULD NOT depend on other extensions.

No body sections are required. These headings have a **conventional** meaning:

| Heading | Purpose |
| :---- | :---- |
| `# Schema` | A structured description of the columns or fields of an asset. |
| `# Examples` | Concrete usage examples, frequently as fenced code blocks. |
| `# Computation` | The sanctioned computation of an Attested Computation. See §10.3. |

To attribute one claim to an external source, use a Markdown footnote whose label is the `id` of a `sources` entry (§5.1). Do not use a list of citations in the body.

### 4.3 Example: a concept bound to a resource

The file is `tables/orders.md`:

```
---
type: BigQuery Table
title: Customer Orders
description: One row per completed customer order across all channels.
resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders
tags: [sales, orders, revenue]
generated: { by: reference_agent/gemini-2.5-pro, at: "2026-05-28T14:30:00Z" }
---

# Schema

| Column        | Type      | Description                              |
|---------------|-----------|------------------------------------------|
| `order_id`    | STRING    | Globally unique order identifier.        |
| `customer_id` | STRING    | Foreign key into [customers](customers.md). |
| `total_usd`   | NUMERIC   | Order total in US dollars.               |
| `placed_at`   | TIMESTAMP | When the customer submitted the order.   |

# Joins

Joined with [customers](customers.md) on `customer_id`.
```

### 4.4 Example: a concept not bound to a resource

The file is `playbooks/freshness-alert.md`:

```
---
type: Playbook
title: "Incident response: data freshness alert"
description: Steps to triage a freshness alert on the orders pipeline.
tags: [oncall, incident]
generated: { by: "human:ahormati", at: "2026-04-12T09:00:00Z" }
---

# Trigger

A freshness alert fires when `orders` lags more than 30 minutes behind its
expected SLA. See the [orders table](../tables/orders.md).

# Steps

1. Check the [ingestion job dashboard](https://example.com/dash).
2. ...
```

---

## 5. Provenance, trust, and lifecycle

These frontmatter families answer three questions from frontmatter only: "Where did this come from?", "How much can I trust it?", and "Is it still current?". All families are optional. When a family is absent, this also has a meaning: a consumer can tell an unverified concept from a verified concept. But a consumer never rejects an unverified concept (§11).

**Timestamps.** The timestamp keys are `generated.at`, `verified[].at`, `stale_after`, `sources[].last_modified`, `usage_window.from`, and `usage_window.to`. Each value has one of two forms from RFC 3339 (a profile of ISO 8601). No other form is valid.

| Form | RFC 3339 rule | Example | Meaning |
| :---- | :---- | :---- | :---- |
| Date-time | `date-time` | `"2026-06-30T14:00:00Z"` | That instant. |
| Date only | `full-date` | `"2026-06-30"` | The start of that day in UTC (`2026-06-30T00:00:00Z`). |

- Consumers MUST accept a quoted string and a YAML-native timestamp. A YAML-native date value means the start of that day in UTC.
- Producers SHOULD use the date-time form for `generated.at` and `verified[].at`, because consumers compare these two values (§5.3).

### 5.1 Provenance: `sources`

`sources` records the materials that a concept derives from. A source can be external or internal to the bundle.

```
sources:
  - id: ga4-schema
    resource: https://developers.google.com/analytics/bigquery/export-schema
    title: GA4 BigQuery Export schema
    author: "team:ga4-docs"
    usage_count: 5000
    last_modified: "2026-05-30T00:00:00Z"
usage_window: { from: "2026-06-01T00:00:00Z", to: "2026-06-30T00:00:00Z" }
```

Each `sources` entry has these keys:

- `resource`: REQUIRED in an entry. The value is one of these:
  - A concrete artifact that a consumer can follow: an absolute URL, or a path in the bundle (§6.2).
  - A population or scope descriptor that a consumer cannot follow, for example `all queries in BigQuery project X`.
- `id`: Optional. A stable key that attributes individual claims (see "Per-claim attribution" below). It SHOULD be present when the body cites the source.
- `title`: Optional. A label for humans.
- The optional credibility signals `author`, `usage_count`, and `last_modified`. The next paragraphs describe them.

**Source credibility signals.** OKF records objective signals for each source. A consumer uses them to decide how much to trust a concept, from the sources that the concept came from. OKF does not store a credibility score, for three reasons: a score is subjective, it is not portable between consumers, and it becomes stale. A consumer *infers* credibility from the signals, in the same way that it calculates trust tiers (§5.3). Each signal is optional and is a key of a `sources` entry:

- `author`: Who or what made the source, as an actor (§7). An authority signal.
- `usage_count`: How frequently something used `resource` (dashboard views, query runs, page reads) during `usage_window`. An adoption and liveness signal. For one artifact, it is the use count of that artifact. For a scope descriptor, it is the number of uses in the scope that touch the concept.
- `last_modified`: When the source itself last changed. A recency signal. It is different from `generated.at` (§5.2), which records the last meaningful change to the concept content.
- `usage_window`: A sibling of `sources`, written one time. It gives the `{ from, to }` time range for each `usage_count`. One entry MAY have its own `usage_window`, which then applies to that entry only.

`usage_count` is a coarse signal. You can compare it at the level of "alive or dead" and of order of magnitude. You can also compare it with the history of the same source. Do not use it as a precise ranking across different kinds of use: the runs of a scheduled query and the deliberate dashboard views of a human do not have equal weight. Consumers SHOULD read it as liveness and trend, not as a score.

Links and path fields express lineage. OKF has no dedicated lineage field. When a `resource` refers to a different concept in the bundle, the derivation edge is already in the bundle graph (§6.4). Thus a consumer MAY read the `sources` of that concept recursively and let credibility propagate. External leaf sources have only their own signals. Deeper lineage (an explicit external `derived_from`, or data lineage) is out of scope for v0.3.

**Per-claim attribution.** To attribute a specific claim, use a Markdown footnote whose label is a `sources[].id`:

```
The `events_` table is sharded daily as `events_YYYYMMDD`.[^ga4-schema]

[^ga4-schema]: GA4 BigQuery Export schema
```

The footnote label is the join key into `sources`. Consumers find the attribution through the matching entry. They do not parse the footnote text. Labels use a key, not a position (`sources[0]`), because agents rewrite these documents frequently. When the list order changes, a position gives the wrong attribution and nothing shows the error. A stable `id` stays correct.

### 5.2 Trust: `generated` and `verified`

`generated` records how the current content was made. `verified` records who or what confirmed the content against its sources or its `resource`. OKF keeps these two fields separate, because the actor that *wrote* a concept is not necessarily the actor that *confirmed* it.

```
generated: { by: reference_agent/gemini-2.5-pro, at: "2026-06-20T22:53:05Z" }
```

- `generated.by`: REQUIRED in `generated`. An actor (§7).
- `generated.at`: The time of the last meaningful change to the content. A trivial edit (format, whitespace, link repair) does not change `generated.at`. Consumers use `generated.at` to decide if a verification is current (§5.3). Only `stale_after` (§5.5) decides freshness.

```
verified:
  - { by: "human:ahormati", at: "2026-06-25T09:00:00Z" }
  - { by: "process:finance-nightly", at: "2026-06-26T02:00:00Z" }
```

- `verified`: A list of verification events. Each event has `by` (an actor) and `at` (a timestamp). Both keys are REQUIRED in an event. Consumers ignore an event that does not have both. More than one event records independent checks, for example a human sign-off and a nightly process. The most recent check is the event with the latest `at`.
- A producer MAY write one verifier as one `{ by, at }` mapping without the list dash. Consumers MUST treat a bare mapping as a list with one item:

```
verified: { by: "human:ahormati", at: "2026-06-25T09:00:00Z" }
```

Content can change without a new confirmation, and a person or a process can confirm facts again without a new generation. §5.3 tells how a consumer uses the two fields together.

### 5.3 Trust tiers

A verification event is **current** when its `at` is equal to or later than `generated.at`, or when `generated` is absent. Consumers MUST calculate the trust tier only from current events. Earlier events stay in the file as history. Consumers MAY show them, for example as "verified before the last change".

Consumers calculate a trust tier from the current events, from lowest to highest:

- No current event ⇒ **unverified**.
- Current events from non-`human:` actors only ⇒ **machine-confirmed**.
- A current event from a `human:<id>` actor ⇒ **human-reviewed**.

This rule is important in a corpus that agents maintain. When an agent rewrites a concept after a human review, the human did not read the new text. Thus the concept is not human-reviewed until a human confirms it again.

A concept with no trust frontmatter is still consumable. Consumers MUST NOT reject it (§11). Trust tiers are advisory signals, not access control.

### 5.4 Lifecycle: `status` and `superseded_by`

```
status: stable        # draft | stable | deprecated
```

- `draft`: Not yet reviewed. Possibly incomplete.
- `stable`: The default. Ready for consumption.
- `deprecated`: Kept for links and history. Not current.

When `status` is absent, the value is `stable`. A value that is not in this list is not `stable`. Consumers that filter to current knowledge exclude the concept. Consumers SHOULD show the raw value (§11.2).

```
status: deprecated
superseded_by: /metrics/gross-margin.md
```

- `superseded_by`: Optional. One path (§6.2) to the concept that replaces this concept. It has a meaning only with `status: deprecated`. Consumers that filter results to current knowledge SHOULD follow it, and give the replacement concept.

**Retire or move a concept (informative).** To retire a concept, keep the file and set `status: deprecated`. When a replacement exists, add `superseded_by`. When you move or rename a concept, keep a short deprecated concept at the old path, with `superseded_by` set to the new path. Then links and stored references to the old path continue to work.

### 5.5 Lifecycle: `stale_after`

```
stale_after: "2026-09-23T00:00:00Z"   # content is stale on or after this instant
```

Optional. An absolute instant. A concept is stale when `now >= stale_after`. OKF uses an absolute instant, not a relative TTL. Thus the staleness decision is a plain comparison, and it does not depend on when a consumer read the concept.

- Stale means that a person or a process must check the content again. It does not mean that the content is false.
- Omit `stale_after` when no review date is known. Do not invent one.
- An empty or null `stale_after` is the same as an absent key (§11.2).
- A consumer MUST NOT treat a `stale_after` value that it cannot parse as fresh. It SHOULD show the value as malformed.

---

## 6. Links and paths

Links (§6.1) and path fields (§6.2) refer to other files with the same rules.

**Resolution.** A consumer resolves a link target or a path field value with these rules:

1. A value with a URI scheme (for example `https:`) is an absolute URL.
2. A value that starts with `/` resolves from the bundle root.
3. Any other value resolves from the directory of the file that contains it.

Both in-bundle forms (rules 2 and 3) are valid. Consumers MUST resolve both forms. A value that resolves to a location outside the bundle root is external. Consumers MUST NOT read it from the local file system.

**Identifiers.** Link targets and path field values are URI references (RFC 3986). A value that contains a space or another reserved character MUST be percent-encoded, for example `my%20concept.md`. Paths are case-sensitive. Producers SHOULD NOT make two paths that differ only by case.

### 6.1 Links between concepts

A concept MAY link to other concepts with standard Markdown links. The target resolves as §6 tells:

```
See the [neighboring concept](./other.md).
See the [customers table](/tables/customers.md) for the join key.
```

A link refers to a concept when its target, without a `#fragment`, resolves (§6) to a concept file (§3.2). A link to an asset, a directory, or a file that is not a concept is valid, but it does not refer to a concept.

**Meaning of a link.** A link from concept A to concept B asserts a *relationship*. The text near the link tells the specific kind (references, joins-with, depends-on). The link itself does not. Consumers that make a graph view usually treat all links as directed edges of an untyped relationship. Only `[text](target)` links (and reference-style links) are links. Other syntaxes, for example `[[wikilinks]]`, are not links in OKF.

Consumers MUST accept broken links. A link whose target is not in the bundle is not malformed. It can be knowledge that nobody has written yet.

### 6.2 Path fields

These fields contain a path or a URI: `resource`, `sources[].resource`, `computation`, `executor.resource`, `attester.resource` (§10), and `superseded_by` (§5.4). Their values resolve as §6 tells. A `sources[].resource` can be a scope descriptor (§5.1). In that case, it is not a path.

**Compatibility with v0.2.** If a path field value without a leading `/` does not resolve from the directory of its file, and the bundle declares `okf_version` 0.2 or earlier or declares no version, a consumer MAY try to resolve the value from the bundle root.

### 6.3 The `references/` convention

A `references/` subdirectory is a conventional location for copies of external material, run instructions, and code. Sources, executors, and attesters frequently refer to it, for example `/references/attesters/sql-equality.py`. It is only a naming convention. It is not a requirement, and other concepts can also be in it.

### 6.4 The bundle graph

The bundle graph has two kinds of directed edges:

- A link (§6.1) from a concept to a concept in the bundle.
- A path field (§6.2) that resolves to a concept in the bundle. The edge goes from the concept that contains the field to the target.

---

## 7. Actor convention

Fields that record an identity (`generated.by`, `verified[].by`, and `sources[].author`) use one actor convention. An actor has one of two forms:

- `<producer>/<version>` for agents and tools, for example `reference_agent/gemini-2.5-pro`.
- `<scheme>:<id>` for other actors. The `id` is an opaque string. OKF defines these schemes:

| Scheme | Meaning | Example |
| :---- | :---- | :---- |
| `human:` | A person. | `human:ahormati` |
| `team:` | A group of people. | `team:finance-fpa` |
| `process:` | An automated process. | `process:finance-nightly` |

Producers MAY use other schemes. Consumers MUST accept other schemes and treat them as non-human.

Only the `human:` scheme gives the human-reviewed trust tier (§5.3). Thus producers MUST use `human:` for content that a person wrote or confirmed. A `team:` actor in `verified` gives the machine-confirmed tier, because a team name does not identify the person who did the check.

---

## 8. Index files

An `index.md` file MAY be in any directory, also the bundle root. It lists the contents of the directory to support **progressive disclosure**: a human or an agent can see what is available before they open individual documents.

An index file in a subdirectory has no frontmatter. A bundle-root `index.md` MAY have frontmatter (§8.1). The body has one or more sections. Each section groups entries under a heading:

```
# Section / Group Heading

* [Title 1](relative-url-1) - short description of item 1
* [Title 2](relative-url-2) - short description of item 2

# Another Section

* [Subdirectory](subdir/) - short description of the subdirectory
```

Entries SHOULD include the `description` from the frontmatter of the linked concept. Producers MAY generate `index.md` automatically. Consumers MAY make one when they read a directory that has no `index.md`.

### 8.1 Bundle metadata

A bundle-root `index.md` MAY have frontmatter with these optional keys:

```
---
okf_version: "0.3"
title: Acme retail analytics
description: Tables, metrics, and sanctioned computations for Acme retail. Use it for sales and margin questions.
license: CC-BY-4.0
---
```

- `okf_version`: The OKF version that the bundle uses (§12). A quoted string.
- `title`: A display name for the bundle.
- `description`: One sentence about the scope of the bundle and when to use it. An agent that has access to many bundles can read this sentence to select a bundle.
- `license`: The license of the bundle content, as an SPDX expression or as a path (§6.2) to a license file in the bundle.

Extension keys (§4.1) are also permitted. These keys apply to the bundle. They do not apply to the concepts in it.

A producer that regenerates `index.md` MUST keep the existing frontmatter of the bundle-root `index.md`. Producers SHOULD put a bundle-root `index.md` with `okf_version` in each bundle.

---

## 9. Log files

A `log.md` file MAY be at any level of the hierarchy. It records the history of changes in that scope. The format is a flat list of entries that are grouped by date, with the newest date first:

```
# Directory Update Log

## 2026-05-22
* **Update**: Added a BigQuery table reference for [Customer Metrics](tables/customer-metrics.md).
* **Creation**: Established the [Dataplex Playbook](playbooks/dataplex.md).

## 2026-05-15
* **Initialization**: Created foundational directory structure.
```

- Date headings MUST use the ISO 8601 `YYYY-MM-DD` form.
- Log entries are prose. The bold word at the start (`**Update**`, `**Creation**`, `**Deprecation**`) is a convention, not a requirement.
- `log.md` has no frontmatter.

---

## 10. Attested computations

An Attested Computation concept tells what a value *means*. It also gives a sanctioned way to *compute* the value. A consumer can then confirm that the agent ran the approved computation, and did not write a different one. Provenance (§5.1) answers "Where did this claim come from?". Attestation answers "Was this number made the way that we said it must be?". OKF records the computation and the means to check it. OKF itself does not run anything.

### 10.1 A computation is its own concept

A sanctioned computation is a standalone concept with `type: Attested Computation`. A concept that needs the value (a `Metric`, a `BigQuery Table`) links to it with a normal Markdown link (§6). There are three reasons for a standalone concept:

- **`runtime` defines what `parameters` mean.** A parameter is a SQL bind variable, a dbt var, or a Python argument, as the runtime sets. When `runtime` and `parameters` are in one frontmatter, the binding is clear.
- **One computation, many consumers.** One computation can support a metric, a dashboard concept, and a report. As a concept, other concepts refer to it one time each, and use it again.
- **Each computation has its own trust state.** `verified`, `stale_after`, and one `attester` describe one thing. Revenue, profit, and margin each have their own verification and attestation. Thus they are three concepts, not three entries in one frontmatter.

### 10.2 Contract fields

The contract is the top-level frontmatter of the concept. An Attested Computation concept has the families of §5. It also has these fields:

- `runtime`: REQUIRED for this type. It tells how to run the computation. Thus it also tells how the executor and the attester read the computation, and what `parameters` mean. Example values: `bigquery`, `postgres`, `dbt`, `python`, `Looker`.
- `parameters`: Optional. A list of the typed, named holes that the agent can fill. Each entry is `{ name, type, required }`. `name` and `type` are REQUIRED in an entry. `required` is optional. Its default value is `false`. The binding follows `runtime`. Common types are `string`, `integer`, `number`, `boolean`, `date`, and `timestamp`. Other types are specific to a runtime.
- `computation`: Optional. A path (§6.2) to a file that contains the computation. Use it in place of a fenced block in the body (§10.3).
- `executor`: Optional. How to run the computation. `executor.resource` is a path (§6.2) to run instructions or code. A runner (an agent, or deterministic consumer code) follows it. `executor.receipt` is a list of the fields that a run must return. These fields are the evidence that the attester examines, for example a BigQuery `job_id` and the SQL that the job ran.
- `attester`: Optional. The deterministic check. `attester.resource` is a path (§6.2) to code (no LLM) that takes a receipt and returns a verdict. It runs on the consumer side.

Consumers MUST NOT show a value as attested when the concept has no `runtime` or no `attester`.

A Skill, a script, or a container can be behind a `resource`. This is a packaging decision. OKF fixes the interface, not the packaging (§1).

The file is `computations/revenue.md`. Appendix A shows it in a complete bundle:

````
---
type: Attested Computation
title: Revenue for fiscal year
description: Recognized revenue for a fiscal year, per Finance's definition.
tags: [finance, revenue]
status: stable
runtime: bigquery
parameters:
  - { name: year, type: integer, required: true }
executor:
  resource: /references/skills/run-on-bq.md
  receipt: [job_id, executed_sql, result]
attester:
  resource: /references/attesters/sql-equality.py
generated: { by: reference_agent/gemini-2.5-pro, at: "2026-06-20T14:00:00Z" }
verified: { by: "human:ahormati", at: "2026-06-25T09:00:00Z" }
stale_after: "2026-12-31T00:00:00Z"
sources:
  - id: rev-policy
    resource: https://wiki.acme/finance/revenue-recognition
    title: Revenue recognition policy
    author: "team:finance-fpa"
    last_modified: "2026-04-02T00:00:00Z"
  - id: exec-rev-dash
    resource: https://bi.acme.example/dashboards/exec-revenue
    title: Executive revenue dashboard
    author: "team:finance-fpa"
    usage_count: 5000
    last_modified: "2026-06-18T00:00:00Z"
usage_window: { from: "2026-06-01T00:00:00Z", to: "2026-06-30T00:00:00Z" }
---

# Computation

```sql
SELECT SUM(amount) AS revenue
FROM finance.recognized_revenue
WHERE fiscal_year = @year
```

Recognized revenue per the recognition policy,[^rev-policy] corroborated by
the executive revenue dashboard.[^exec-rev-dash]

[^rev-policy]: Revenue recognition policy
[^exec-rev-dash]: Executive revenue dashboard
````

### 10.3 The computation

Give the computation in one of two ways:

- **Inline:** a fenced code block in the body, in the section with the heading `Computation`. This way is best for a short computation that people review together with the contract.
- **File:** set `computation` to a path (§6.2), and do not put a fenced block in the body. This way is best for a long or generated computation, or for a computation that is already a real file that other tools use.

```
runtime: bigquery
computation: /references/computations/lib/revenue.sql
parameters:
  - { name: year, type: integer, required: true }
```

**How a consumer finds the computation:**

1. If `computation` is present, the computation is the file that it refers to.
2. If `computation` is absent, the computation is the first fenced code block in the section with the heading `Computation`, at any ATX heading level. The section ends at the next heading of the same or a higher level.
3. If the section has no fenced code block, or the file does not exist, the computation is missing. Consumers MUST treat the concept as not attestable.

Producers SHOULD put exactly one fenced code block in the `Computation` section.

The agent MAY only supply *values* for the declared `parameters`. The agent MUST NOT write or edit the computation. The consumer binds the computation with the parameter values to make the executable artifact. The attester independently makes the same binding again, and compares it with the artifact that ran. The comparison uses the expanded, compiled artifact in the receipt (`executed_sql`, `compiled_sql`). Thus a rewritten query, a replaced computation file, or a changed dependency fails the check. A typed surface that accepts only parameters makes "Did the sanctioned computation run?" a mechanical comparison, not a judgment.

### 10.4 Concepts that use a computation

A document is rarely only one computation. An overview of an income statement that discusses revenue, profit, and margin stays one readable concept. It links to one Attested Computation for each figure (Appendix A). A concept about one figure links to one computation.

For example, the file `metrics/revenue.md`:

```
---
type: Metric
title: Revenue
description: Recognized revenue for a fiscal year.
tags: [finance, revenue]
status: stable
generated: { by: reference_agent/gemini-2.5-pro, at: "2026-06-20T22:53:05Z" }
---

# Definition

Recognized revenue sums `amount` over rows booked to the fiscal year,
computed by [the revenue computation](../computations/revenue.md).
```

Each computation is its own concept. Thus revenue can be fresh while profit is after its `stale_after`, and each computation has its own attestation for each run. To keep the computations together, use a directory (a `computations/` directory with an `index.md`). Do not use frontmatter for this.

### 10.5 How a consumer uses an attested computation (informative)

This subsection is informative, not normative. The bundle does **not** contain the runtime artifacts in this subsection.

1. **Discover** the concept from a scan of frontmatter for `type: Attested Computation`, or follow a link from a concept that uses it.
2. **Load** the contract from the frontmatter, and the computation as §10.3 tells.
3. **Parameterize**: the agent supplies values for the declared parameters.
4. **Execute**: the executor runs the bound computation and returns a receipt in the shape that `executor.receipt` declares.
5. **Attest**: the consumer runs the attester on the receipt. The attester returns a mapping that contains at least `ok` (a boolean) and an optional `reason` (a string). The attester confirms provenance: the computation that ran is equal to `computation` bound with the claimed parameters, and is not SQL that the agent wrote. It also confirms fidelity: the value on display agrees with the authoritative source of the receipt. The attester reads the source again by the job ID. It does not use the text of the agent.
6. **Gate**: do not show a value whose attestation failed. Show a warning or do not show the value when `now >= stale_after`. When the attestation succeeds, show the verdict (for example a link to the job log), so that the trust is visible.

### 10.6 Verification and attestation

`verified` (§5.2) and attestation are different. OKF uses both:

- `verified` confirms that the *definition* still agrees with the policy. It applies to the document, it is slow, and the bundle records it.
- Attestation confirms that one *run* made the value in the sanctioned way. It applies to each call, it occurs at runtime, and the bundle does not record it.

A concept with a stale definition can still attest correctly. A definition that a person verified recently still needs an attestation for each run. Thus OKF needs both.

---

## 11. Conformance

### 11.1 Bundle conformance

A bundle is **conformant** with OKF v0.3 when:

1. Each frontmatter block in a `.md` file under the bundle root (§3.2) parses as a YAML mapping (§4).
2. Each reserved file (`index.md`, `log.md`) agrees with §8 and §9 when it is present.

A `.md` file without frontmatter or without `type` is not a concept (§3.2). It does not make the bundle non-conformant.

### 11.2 Consumer rules

Consumers:

- MUST resolve both in-bundle forms of links and path fields (§6).
- MUST NOT read a value that resolves outside the bundle root from the local file system (§6).
- MUST NOT treat `index.md` or `log.md` as concepts (§3.1).
- MUST NOT reject keys that they do not know, at any level (§4.1).
- MUST NOT treat a `stale_after` value that they cannot parse as fresh (§5.5).
- MUST NOT show a value as attested without `runtime` and `attester` (§10.2).
- MUST NOT reject a concept because an optional family is missing (§5.3).
- MUST calculate trust tiers only from current verification events (§5.3).
- SHOULD calculate staleness only from `stale_after` (§5.5).
- SHOULD show a failed attestation, and not silently drop it (§10.5).

Consumers apply these rules to values that are absent, empty, or have an unexpected shape:

1. A null value, an empty string, and an empty list are the same as an absent key.
2. Where a field is a list (`tags`, `sources`, `verified`, `parameters`), consumers MUST accept one item as a list with one item. A scalar `tags` value is one tag. Consumers MUST NOT split it at commas.
3. Consumers ignore an entry of a family that does not have its REQUIRED key, and SHOULD warn about it.
4. When a key that this specification defines has a value that is not in its defined vocabulary, the consumer keeps the value and MAY warn. For an unknown `status` value, see §5.4.

In all of these cases, the bundle stays conformant.

Consumers MUST NOT reject a bundle because of:

- Missing optional frontmatter fields.
- Unknown `type` values.
- Unknown extension keys.
- Broken links.
- Missing `index.md` files.

---

## 12. Versioning

This document specifies OKF version **0.3**. OKF versions have the form `<major>.<minor>`.

- **Before 1.0**, a minor version MAY contain breaking changes. The "Changes" section (§13) MUST list each breaking change, with a consumer fallback where one exists.
- **From 1.0**, a minor version contains only backward-compatible additions (new optional fields, new conventional headings). Only a major version can contain breaking changes.
- A **breaking change** is the removal of a field, the rename of a field, a definition of a field that conflicts with its earlier definition, or a change to how a consumer reads an existing value.
- After the release of a version, a change to its normative text requires a new version.

A bundle MAY declare its version with `okf_version` in the frontmatter of the bundle-root `index.md` (§8.1). A consumer that does not know the declared version SHOULD try best-effort consumption. It SHOULD NOT refuse the bundle.

### 12.1 Bundles from earlier versions

A consumer that reads a bundle that declares `okf_version` 0.2 or earlier, or that declares no version, MAY apply these fallbacks:

- A path field without a leading `/` that does not resolve from its file MAY resolve from the bundle root (§6.2).
- The v0.1 fallbacks in Appendix B (`timestamp`, `# Citations`).

### 12.2 Considered and deferred

These items stay for a future version:

- The full runtime protocol: the wire formats of receipts and verdicts, and the attestation lifecycle around a run.
- The attester ABI, portability, and sandboxes. These will possibly come with future work on serving and Skills.
- Attestation caches.
- Semantic-layer templates (Looker, dbt), where the attester compares a model and its binding, not SQL text.
- Typed relationships between concepts. Use links, path fields (§6.4), and extension keys (§4.1) until the community agrees on one form.
- Validity windows, source drift signals, and a `refuted` verification event. Use extension keys until the community agrees on one form.

---

## 13. Changes from v0.2

v0.3 makes the v0.2 text precise. It also adds three optional capabilities. Under the rules of §12, v0.3 has two breaking changes. Both alter how a consumer reads a v0.2 value. §13.1 lists them, with their fallbacks.

### 13.1 Breaking changes

| Change | Effect on v0.2 bundles | Fallback |
| :---- | :---- | :---- |
| A path field without a leading `/` resolves from the directory of its file (§6.2). | Bare paths that the v0.2 examples wrote from the bundle root do not resolve. | §12.1: try the bundle root. |
| Only current verification events give the trust tier (§5.3). | Some concepts go from human-reviewed to a lower tier. | None necessary. The tier can only go down, which is the safe direction. |

### 13.2 Clarifications and errata

- §2: Defined bundle root, producer, consumer, asset, path field, and extension key.
- §2, §6.1: Wording fix. Only the directory tree defines parent/child structure. A link is an untyped, directed relationship. v0.2 used "parent/child" for both, which readers took to mean that links are parent/child (okf#34).
- §3.2: Rules for which files are concepts. A `.md` file without `type` is not a concept. Non-`.md` files are assets. Dot-paths are not part of the bundle.
- §4: Frontmatter syntax: YAML 1.2 core schema; delimiters; no duplicate keys; quoting of values that look like numbers or booleans; no custom YAML tags; no re-serialization of unchanged values. §4.2: The body dialect is CommonMark, with GFM tables and `[^label]` footnotes. Producers do not depend on other extensions.
- §5: A list of the timestamp keys. Each value is a date-time with an offset or a date only (the start of that day in UTC), in the RFC 3339 profile of ISO 8601. Consumers accept quoted and native timestamps. The v0.2 text did not give a time zone for a date-only value. After its release, the v0.2 text was changed to require an offset (okf#24). v0.3 accepts date-only values again, with a fixed meaning, so v0.2 bundles that contain them stay valid. A date-time without an offset stays invalid.
- §5.2: `generated.at` has one meaning: the last meaningful change to the content. `verified` events require `by` and `at`.
- §5.4: An unknown `status` value is not `stable`. Filters to current knowledge exclude the concept. v0.2 did not define this case.
- §5.5: Stale means "check again", not "false". A `stale_after` value that does not parse is never fresh.
- §6: One resolution rule for links and path fields. A value without a leading `/` resolves from the directory of its file. Both in-bundle forms are valid, and the spec no longer recommends one form. (v0.2 recommended `/` for links.) Consumers MUST resolve both forms. Values outside the bundle root are external. Targets are URI references, and paths are case-sensitive.
- §6.1: A rule tells when a link refers to a concept.
- §6.4: Path fields that resolve to a concept are graph edges.
- §7: The general `<scheme>:<id>` actor form, with the `team:` scheme. `sources[].author` uses the actor convention.
- §9: `log.md` has no frontmatter.
- §10.2: `parameters` entries require `name` and `type`. `required` defaults to `false`. A list of common parameter types.
- §10.3: The locator rule for the inline computation. The examples now use real fenced code blocks.
- §10.5: Discovery is by a scan of frontmatter. An attester verdict has at least `ok` and an optional `reason`.
- §11: Conformance does not require frontmatter in every `.md` file. New consumer rules for absent, empty, and single-item values, and for values outside a vocabulary.
- §12: A versioning policy for versions before 1.0.
- Editorial: removed a duplicate sentence in §1, and added freshness to the list of first-class families. §6.3 no longer says that `references/` contains only external material. The examples quote timestamps, use relative links, and use a leading `/` in path fields. Appendix A uses current verification timestamps and a URL for the dashboard source.

### 13.3 Additive changes

- `superseded_by` for deprecated concepts, and guidance to retire and move concepts (§5.4).
- Bundle metadata in the bundle-root `index.md`: `title`, `description`, and `license` (§8.1). Producers that regenerate `index.md` must keep this frontmatter.
- Rules for extension keys: extension keys are permitted at all levels, and future versions will not define keys that start with `x-` (§4.1).

---

## Appendix A: Worked example, an income statement

The two figures are now attested computations. A narrative concept links to them. All families have values. The two computations are in different states on purpose, so one consumer gets two different results.

```
bundles/finance/
  index.md                         okf_version: "0.3", title, description, license
  metrics/income-statement.md      type: Metric  (narrates, links both)
  computations/revenue.md          type: Attested Computation  (runtime: bigquery)
  computations/profit.md           type: Attested Computation  (runtime: dbt)
  references/skills/run-on-bq.md, run-dbt.md
  references/attesters/sql-equality.py, dbt-binding.py     (assets, §3.2)
```

`index.md`, the bundle metadata:

```
---
okf_version: "0.3"
title: Acme finance
description: Income-statement metrics and their sanctioned computations. Use it for revenue and profit questions.
license: CC-BY-4.0
---

# Metrics

* [Income statement (fiscal year)](metrics/income-statement.md) - Headline income-statement figures for a fiscal year.

# Computations

* [Revenue for fiscal year](computations/revenue.md) - Recognized revenue for a fiscal year, per Finance's definition.
* [Gross profit for fiscal year](computations/profit.md) - Gross profit by segment for a fiscal year, per the cost-allocation standard.
```

`metrics/income-statement.md`, the readable document. It has its own trust state, and each computation that it links to has a separate trust state:

```
---
type: Metric
title: Income statement (fiscal year)
description: Headline income-statement figures for a fiscal year.
tags: [finance, income-statement]
status: stable
generated: { by: reference_agent/gemini-2.5-pro, at: "2026-06-20T22:53:05Z" }
verified: { by: "human:ahormati", at: "2026-06-25T09:00:00Z" }
stale_after: "2026-12-31T00:00:00Z"
sources:
  - id: fpa-handbook
    resource: https://wiki.acme/finance/fpa-handbook
    title: FP&A reporting handbook
---

# Definition
The income statement reports [revenue](../computations/revenue.md) and
[gross profit](../computations/profit.md) for a fiscal year, per the FP&A
reporting handbook.[^fpa-handbook] Each figure is produced by a sanctioned,
attestable computation; this concept only narrates them.

[^fpa-handbook]: FP&A reporting handbook
```

`computations/revenue.md`: BigQuery SQL. Human-reviewed (the verification is after the last change), fresh, and supported by a live dashboard source with credibility signals:

````
---
type: Attested Computation
title: Revenue for fiscal year
description: Recognized revenue for a fiscal year, per Finance's definition.
tags: [finance, revenue]
status: stable
runtime: bigquery
parameters:
  - { name: year, type: integer, required: true }
executor:
  resource: /references/skills/run-on-bq.md
  receipt: [job_id, executed_sql, result]
attester:
  resource: /references/attesters/sql-equality.py
generated: { by: reference_agent/gemini-2.5-pro, at: "2026-06-20T14:00:00Z" }
verified: { by: "human:ahormati", at: "2026-06-25T09:00:00Z" }
stale_after: "2026-12-31T00:00:00Z"
sources:
  - id: rev-policy
    resource: https://wiki.acme/finance/revenue-recognition
    title: Revenue recognition policy
    author: "team:finance-fpa"
    last_modified: "2026-04-02T00:00:00Z"
  - id: exec-rev-dash
    resource: https://bi.acme.example/dashboards/exec-revenue
    title: Executive revenue dashboard
    author: "team:finance-fpa"
    usage_count: 5000
    last_modified: "2026-06-18T00:00:00Z"
usage_window: { from: "2026-06-01T00:00:00Z", to: "2026-06-30T00:00:00Z" }
---

# Computation

```sql
SELECT SUM(amount) AS revenue
FROM finance.recognized_revenue
WHERE fiscal_year = @year
```

Recognized revenue per the recognition policy,[^rev-policy] corroborated by
the executive revenue dashboard.[^exec-rev-dash]

[^rev-policy]: Revenue recognition policy
[^exec-rev-dash]: Executive revenue dashboard
````

`computations/profit.md`: a dbt model. Machine-confirmed by a process (the verification is after the last change), and after its `stale_after`:

````
---
type: Attested Computation
title: Gross profit for fiscal year
description: Gross profit by segment for a fiscal year, per the cost-allocation standard.
tags: [finance, profit]
status: stable
runtime: dbt
parameters:
  - { name: year, type: integer, required: true }
  - { name: segment, type: string, required: true }
executor:
  resource: /references/skills/run-dbt.md
  receipt: [run_id, compiled_sql, result]
attester:
  resource: /references/attesters/dbt-binding.py
generated: { by: reference_agent/gemini-2.5-pro, at: "2026-06-10T14:00:00Z" }
verified: { by: "process:finance-nightly", at: "2026-06-12T08:00:00Z" }
stale_after: "2026-06-15T00:00:00Z"
sources:
  - id: cost-alloc
    resource: https://wiki.acme/finance/cost-allocation
    title: Cost allocation standard
---

# Computation

```sql
SELECT gross_profit
FROM {{ ref('fct_income_statement') }}
WHERE fiscal_year = {{ var('year') }}
  AND segment = {{ var('segment') }}
```

Gross profit by segment per the cost-allocation standard.[^cost-alloc]

[^cost-alloc]: Cost allocation standard
````

A consumer that reads this bundle on or after 2026-06-15 and before 2026-12-31 gets these results:

| Concept | Trust tier | Fresh | Attestable |
| :---- | :---- | :---- | :---- |
| `metrics/income-statement` | human-reviewed | yes | no (not a computation) |
| `computations/revenue` | human-reviewed | yes | yes |
| `computations/profit` | machine-confirmed | no | yes, with a staleness warning |

---

## Appendix B: Changes from v0.1 to v0.2

v0.2 replaced OKF v0.1. It made two changes that renamed or removed v0.1 fields. A consumer can read a v0.1 bundle with the fallbacks below.

### B.1 Breaking changes

- **`generated.at` replaces `timestamp`.** `generated: { by, at }` (§5.2) records the last change to the content of a concept. Consumers MAY use a legacy `timestamp` when `generated` is absent.
- **`sources` replaces the body `# Citations` list.** Provenance is in the frontmatter (§5.1). Consumers MAY parse a legacy `# Citations` body list in v0.1 documents.

### B.2 Additive changes

- The frontmatter families `sources` with its credibility signals (`author`, `usage_count`, `last_modified`) and the `usage_window` sibling; `generated` and `verified`; `status` and `stale_after` (§5).
- The concept type `Attested Computation` and its keys `runtime`, `parameters`, `computation`, `executor`, and `attester` (§10).
- The conventional body heading `# Computation` (§4.2).
- The actor convention (§7).
