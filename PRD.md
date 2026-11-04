# PRD — Storygram

**Status:** Draft for implementation  
**Version:** 0.2.0  
**Product:** Storygram  
**Last updated:** 2026-10-07

## 1. Executive summary

Storygram is a local-first, versionable and interoperable information system for collecting, organizing, linking, verifying and presenting life stories, family structures, relationships, events, places, memories, testimonies, media and narratives.

The product separates a canonical historical record from derived views such as genograms, timelines, maps, biographies, thematic stories, exports and future AI-assisted workflows. The first release must be useful without an AI model.

## 2. Problem statement

Existing tools commonly separate genealogy, genograms, timelines, notes, media archives, oral-history systems and narrative publishing. They rarely represent, in one coherent model, both the original episode and the propositions derived from it, including source, witness, time, certainty, disagreement and revision history.

Storygram addresses this by introducing an evidence-oriented temporal model:

```text
Episode → Annotation → Assertion → Entity / Event / Relationship → Derived view
```

## 3. Vision

Provide a durable archive in which:

- humans can read, edit and review information comfortably;
- software can validate, query, transform and render information reliably;
- sources, perspectives, uncertainty and disagreement remain visible;
- multiple views can be generated without duplicating facts;
- future AI systems can submit evidence-backed proposals instead of silently rewriting the archive.

## 4. Goals and non-goals

### 4.1 MVP goals

1. Define a stable, documented domain model.
2. Store canonical records in portable, versionable files.
3. Represent episodes, people, organizations, places, periods, events, relationships, sources, media, assertions, annotations and narratives.
4. Preserve temporal precision, uncertainty, provenance and disagreement.
5. Validate schemas and references.
6. Provide deterministic search and temporal queries.
7. Generate timelines and genograms from canonical data.
8. Export machine-readable and human-readable representations.
9. Support visibility and privacy metadata.
10. Provide a safe proposal boundary for future AI clients.

### 4.2 MVP non-goals

- clinical diagnosis or psychological assessment;
- automatic identity resolution or person merging;
- autonomous historical truth adjudication;
- mandatory cloud storage;
- public social networking;
- AI chat as the core interface;
- complete OCR/transcription/media-understanding pipeline;
- mandatory graph database or vector database;
- autonomous mutation of canonical records.

## 5. Users and use cases

### Curator

Collects records, reviews evidence, resolves duplicates, marks conflicts and publishes selected views.

### Contributor

Adds memories, testimonies and documents while preserving authorship, perspective and privacy.

### Researcher

Queries people, events, places, periods and sources and verifies the evidence behind a statement.

### Software or future AI client

Reads schemas and canonical records, proposes structured changes and provides evidence-linked outputs.

## 6. Domain model

### 6.1 Core types

```text
Episode
Person
Organization
Place
Period
Event
Relationship
Source
MediaAsset
Assertion
Annotation
Narrative
Collection
Proposal
```

### 6.2 Common metadata

Every persisted object SHOULD provide:

```yaml
id: <namespace>:<stable-id>
type: <Type>
status: draft|proposed|reported|confirmed|disputed|rejected|archived
created_at: <ISO-8601 datetime>
updated_at: <ISO-8601 datetime>
```

IDs MUST be independent of mutable names and titles. UUIDv7, ULID or an equivalent stable strategy is recommended.

## 7. Episode model

An **Episode** is an immutable or append-only record of an information-bearing occurrence or capture. It is not necessarily a historical fact. Examples include:

- an interview;
- a written memory;
- a letter;
- a photograph with contextual notes;
- an audio or video recording;
- a document import;
- an observation;
- a previous version of a narrative;
- a data-import batch.

An episode answers: **what was captured, from where, by whom, when and in what form?**

### 7.1 Episode responsibilities

An Episode MUST:

- have a stable ID;
- preserve its capture or import metadata;
- identify its original content or source;
- preserve checksum or content identity when available;
- support participants, author, recorder or importer;
- declare visibility;
- remain unchanged after ingestion, except for non-semantic metadata corrections or a new superseding revision;
- be usable as provenance for annotations and assertions.

### 7.2 Episode does not mean fact

The statement “Mario says he moved in 1987” is an observation about an episode. It is not automatically equivalent to “Mario moved in 1987”. The latter is an assertion that may be reported, probable, confirmed, disputed or rejected.

## 8. Assertion model

An **Assertion** is a proposition about one or more entities, events or relationships. It may be extracted from an episode, directly entered by a curator, imported from a source or derived from other assertions.

Conceptual form:

```text
subject — predicate — object
```

Examples:

```text
Mario Rossi — lived_in — Brescia
Mario Rossi — parent_of — Anna Rossi
Transfer event — occurred_in — 1987
```

An assertion MUST be able to express:

- subject, predicate and optional object;
- validity in represented historical time;
- when it was recorded by Storygram;
- when it was invalidated or superseded;
- source episodes, sources and annotations;
- author, witness, extractor or agent;
- status, certainty and confidence;
- conflict and supersession links.

An assertion is not automatically canonical merely because it exists. Canonical status is an editorial decision represented explicitly by `status` and review metadata.

## 9. Bitemporal model

Storygram uses two independent time axes.

### 9.1 Valid time

`valid_time` represents when the proposition is considered true, applicable or reported to apply in the represented world.

Examples:

```yaml
valid_time:
  start: "1987"
  end: "1995"
  precision: year
```

Relationship records may carry the same optional `valid_time` and `transaction_time` fields when the relation itself has a represented or recorded interval. Assertions remain the general proposition type.

### 9.2 Transaction time

`recorded_at` and `recorded_until` represent when the proposition was present in the Storygram record.

```yaml
transaction_time:
  recorded_at: "2026-10-07T10:00:00+02:00"
  recorded_until: null
```

A replacement or correction closes the previous transaction interval; it does not erase the old record.

### 9.3 Complete lifecycle example

Suppose an interview recorded in 2026 says Mario lived in Brescia from 1987 to 1995. In 2027, a registry suggests the end year was 1994.

Original assertion:

```yaml
id: assertion:01
valid_time:
  start: "1987"
  end: "1995"
transaction_time:
  recorded_at: "2026-01-12T16:00:00+01:00"
  recorded_until: "2027-03-10T09:15:00+01:00"
status: superseded
```

New assertion:

```yaml
id: assertion:02
valid_time:
  start: "1987"
  end: "1994"
transaction_time:
  recorded_at: "2027-03-10T09:15:00+01:00"
  recorded_until: null
status: disputed
supersedes: [assertion:01]
```

The old assertion remains queryable as a historical record. A query can ask:

- what was believed to be true in 1987–1995?
- what did Storygram contain on 2026-12-01?
- what is the current accepted interpretation?

### 9.4 Rules for historical changes

1. Never overwrite a materially different assertion in place.
2. Close its transaction interval or mark it superseded.
3. Create a new assertion with a new ID.
4. Link the new assertion using `supersedes`, `revises`, `contradicts` or `corroborates`.
5. Preserve the old source and annotation links.
6. Record the reviewer, operation and reason.
7. Do not change valid time merely because the record was edited.
8. Treat uncertainty as data, not as an error to hide.

## 10. Conflicting sources

Storygram MUST preserve conflicting reports rather than forcing a premature single truth.

### 10.1 Conflict representation

A conflict is a first-class relation between assertions:

```yaml
id: conflict:01
assertions:
  - assertion:01
  - assertion:02
type: temporal_conflict
status: open
reason: "Different end years are reported."
identified_at: "2027-03-10T09:15:00+01:00"
review:
  state: unresolved
```

The minimum implementation may represent this through `contradicts` arrays on assertions, but a dedicated `Conflict` type is recommended for the next schema revision.

### 10.2 Resolution policy

Conflicts MUST NOT be resolved solely by:

- source recency;
- linguistic confidence;
- model confidence;
- majority vote;
- name similarity.

A curator MAY mark an assertion as:

```text
confirmed
reported
probable
disputed
rejected
superseded
```

The resolution record SHOULD include:

- reviewer;
- decision time;
- rationale;
- evidence considered;
- assertions retained or superseded;
- whether the resolution is provisional.

### 10.3 Narrative behavior

Narratives MUST either:

- present the conflict explicitly;
- state which interpretation is being used and why;
- or omit the disputed claim.

A generated narrative MUST NOT silently convert a disputed assertion into an undisputed fact.

## 11. Canonical Git repository

Git is the canonical version and review boundary for Storygram records.

### 11.1 Recommended layout

```text
storygram/
├── README.md
├── AGENTS.md
├── PRD.md
├── docs/
├── schema/
│   ├── episode.schema.json
│   └── assertion.schema.json
├── contexts/
├── data/
│   ├── episodes/
│   ├── people/
│   ├── organizations/
│   ├── places/
│   ├── periods/
│   ├── events/
│   ├── relationships/
│   ├── sources/
│   ├── media-assets/
│   ├── assertions/
│   ├── annotations/
│   ├── narratives/
│   └── conflicts/
├── inbox/
├── proposals/
├── generated/
├── media-manifest/
├── src/
├── tests/
└── scripts/
```

### 11.2 Git rules

- `data/` is canonical and reviewable.
- `inbox/` contains unreviewed imports and is never treated as confirmed truth.
- `proposals/` contains human- or AI-generated changes awaiting review.
- `generated/` contains reproducible output and SHOULD be ignored unless publication requires committing it.
- Large or private media SHOULD be stored outside Git, with a manifest containing URI, checksum, MIME type, size, visibility and acquisition metadata.
- Every semantic change SHOULD be a commit with a meaningful message.
- A pull request or equivalent review SHOULD be required for changes to assertions, relationships, visibility or schema.
- Validation MUST run in CI before merge.
- Git history is transaction history, but domain-level transaction metadata MUST also be stored when a queryable bitemporal record is required.

### 11.3 Change workflow

```text
source/episode received
    ↓
inbox or data entry
    ↓
assertion/proposal created
    ↓
validation
    ↓
review and conflict check
    ↓
Git commit / pull request
    ↓
merge into canonical data
    ↓
rebuild indexes and derived views
```

## 12. Functional requirements

### FR-001 Repository initialization

The system MUST initialize a valid archive with the documented layout and an empty dataset that passes validation.

### FR-002 Episode ingestion

The system MUST register an episode without treating its contents as confirmed facts. Episodes MUST retain identity, capture/import metadata, content references and visibility.

### FR-003 Record management

The system MUST create, retrieve, list, update metadata for, and archive supported records while preserving semantic history.

### FR-004 Schema validation

The system MUST validate shape, types, allowed values, timestamps, temporal structures and required fields.

### FR-005 Referential integrity

The system MUST detect duplicate IDs, missing references, invalid relation targets, inaccessible source links and broken annotations.

### FR-006 Assertion lifecycle

The system MUST create assertions with provenance, status, certainty, confidence, valid time and transaction time.

### FR-007 Conflict management

The system MUST expose contradictory assertions, their evidence and their review state without silently selecting one.

### FR-008 Temporal queries

The system MUST support queries by valid time, transaction time, entity, source, status and conflict state.

### FR-009 Deterministic search

The system MUST support exact or normalized search by ID, name, alias, type, tag, place, participant and source.

### FR-010 Timeline view

The system MUST generate an entity-, place-, collection- or archive-level timeline linked to canonical records and evidence.

### FR-011 Genogram view

The system MUST generate a structured and human-readable relationship view. An exact `(subject, predicate, object)` triple is one relationship edge even when multiple records describe it; all distinct valid and transaction intervals from those records MUST remain available in the view. Unsupported relation types MUST remain visible as metadata or warnings.

### FR-012 Narrative view

The system MUST store narratives with author, language, perspective, status, related objects, sources and content location.

### FR-013 Import/export

The system MUST support native YAML/Markdown and JSON. JSON-LD SHOULD be supported as semantic export. Supported round trips MUST be tested and lossiness documented.

### FR-014 Privacy and visibility

Records and sources MUST support visibility metadata, and exports MUST support filtering or redaction.

### FR-015 Git integration

The project MUST provide validation and rebuild commands suitable for local Git hooks and CI. It SHOULD provide a machine-readable change report for changed canonical files.

### FR-016 Future AI proposal boundary

The system SHOULD accept proposals containing target IDs, structured patches, evidence, rationale, confidence, detected conflicts and approval state. A proposal MUST NOT silently modify canonical data.

## 13. Non-functional requirements

### NFR-001 Local-first operation

Core validation, query and rendering MUST work without network access.

### NFR-002 Portability

Canonical records MUST be understandable independently of a single database or UI.

### NFR-003 Reproducibility

Derived views MUST be rebuildable from canonical records and documented tool versions.

### NFR-004 Data integrity

The system MUST avoid silent data loss and report lossy conversions or unavailable media.

### NFR-005 Usability

Human-oriented commands and views MUST show readable dates, stable IDs, evidence, status, conflicts and actionable errors.

### NFR-006 Privacy

Fixtures MUST be synthetic. Sensitive data MUST be opt-in for export and filterable by visibility.

### NFR-007 Accessibility

Generated HTML SHOULD use semantic structure, keyboard navigation, labels, readable contrast and non-color-only status indicators.

### NFR-008 Performance

The initial implementation SHOULD document a benchmark target of at least 100,000 entities and 1,000,000 assertions, unless a lower limit is justified.

## 14. Technical baseline

Unless the repository already specifies a compatible alternative:

- Python 3.12+;
- `uv` for packaging/environment;
- Pydantic for application models;
- JSON Schema as public contract;
- YAML/Markdown for human editing;
- SQLite/FTS5 for deterministic local search;
- JSON-LD for semantic export;
- pytest, ruff and a type checker;
- Git for versioning and review.

## 15. CLI baseline

```bash
storygram init PATH
storygram validate [PATH]
storygram ingest episode FILE
storygram get ID
storygram list --type Person
storygram search QUERY
storygram timeline ID
storygram timeline --all
storygram genogram ID
storygram conflicts [--status open]
storygram export --format json
storygram export --format jsonld
storygram rebuild
storygram git-check [BASE]
```

Read commands SHOULD support human-readable and `--json` output.

## 16. MVP acceptance criteria

The MVP is accepted when:

1. a new archive can be initialized locally;
2. schemas for Episode and Assertion validate valid fixtures and reject invalid fixtures;
3. the fixture includes episodes, people, generations, events, places, relationships, sources, annotations, competing assertions, a conflict and a narrative;
4. episode ingestion does not automatically confirm assertions;
5. bitemporal fields can represent a historical correction without overwriting the previous record;
6. conflict inspection shows both assertions and their evidence;
7. exact search and retrieval work without AI;
8. timeline and genogram views derive from canonical data;
9. JSON export works and supported round trips are tested;
10. visibility filtering is tested;
11. Git validation detects invalid changed canonical files;
12. documentation enables a new developer to install, validate, query and rebuild views;
13. formatting, linting, type checks, unit tests and integration tests pass.

## 17. Milestones

### M0 — Foundation

Packaging, CLI skeleton, documentation, fixture, tests and CI.

### M1 — Canonical model

Schemas, models, identifiers, statuses, time, references and validation.

### M2 — Episodes and evidence

Episode ingestion, sources, media manifest, annotations, assertions and provenance.

### M3 — Bitemporal history and conflicts

Transaction intervals, supersession, contradiction, conflict inspection and review metadata.

### M4 — Queries and derived views

SQLite index, deterministic search, timeline, genogram, exports, HTML/SVG and rebuild commands.

### M5 — Human interface

Local browser interface for browsing, editing, reviewing, filtering and exporting.

### M6 — Optional AI adapter

Retrieval, extraction to proposals, evidence citations, conflict reporting and explicit approval.

## 18. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Domain model becomes too complex | Start with a small vocabulary and versioned extensions |
| Source and fact are confused | Keep Episode, Source, Annotation and Assertion distinct |
| Conflicts are erased | Represent disagreement explicitly and preserve both sides |
| Historical changes overwrite history | Use new IDs, transaction intervals and supersession links |
| Git becomes a media store | Keep large media external and commit checksummed manifests |
| AI becomes a hidden dependency | Keep core operations deterministic |
| Private material is exposed | Visibility metadata, filtered exports and synthetic fixtures |
| Derived output becomes canonical | Mark and rebuild generated data |

## 19. Definition of done

A feature is complete only when behavior, data contract, validation, tests, documentation, compatibility impact and limitations are clear. Canonical changes are reviewable, derived output is reproducible, and conflicts or failures are visible rather than silently ignored.
