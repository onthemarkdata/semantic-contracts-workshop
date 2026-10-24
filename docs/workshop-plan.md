# Semantic contracts workshop: review proposal

> **Linked Art follow-up:** Extend the sculpture proposal with the official
> Human-Made Object JSON Schema, JSON-LD context, and recommended Sculpture URI.
> Keep source-label mapping decisions explicit and local. Demonstrate that
> substituting Artwork's URI preserves schema validity but violates the agreed
> sculpture identity. This deterministic mapping exercise adds no model score.
> See [the standards-based evidence](evidence/linked-art-map/README.md).

> **Sculpture category follow-up:** Add a separate, proposed MAP profile inside
> the original contract for an explicit group of 17 sculpture classifications.
> Compare its 296 object records with the 151 selected by the exact label
> `Sculpture`, then demonstrate a category-membership violation in a stacked PR.
> Preserve the existing 20-question evaluations and missing-text exercise. These
> are deterministic object counts, not new model accuracy scores. See the
> [category evidence](evidence/sculpture-map/README.md).

> **Current MAP workflow:** Mark requested two evaluations: preserve the current
> prompt for the first, then test a semantics-focused prompt with unchanged
> questions and scoring. Add the MAP as a new section of the original data
> contract, deliberately violate it in the prompt, and show a failed required
> GitHub check with an explanatory PR comment. The regression demonstration
> does not require another model evaluation. See [the workflow](prompt-map-workflow.md).
> Score improvement must be measured; it is not an acceptance claim made in advance.


> **23 October context update:** Mark requested the connected database, full schema,
> and supported SQL operations in the initial prompt. The agent now starts with an
> answer query; schema discovery actions are removed. All three stages receive the
> same context, recorded in their manifests. The revised improved prompt answered
> all five correctly in 3 minutes 38 seconds locally; the first question took
> 130 seconds and subsequent questions took 19–25 seconds. The request timeout
> also increased for this diagnostic. Native Codespaces and three-stage comparison
> acceptance remain open. Mark chose to retain CPU inference.

> **23 October rehearsal scope:** Mark requested the completed local 20-question
> run in Codespaces. The existing `codex/five-question-codespaces` branch now defaults
> to q01–q20 with the improved prompt only, fixed local limits, and no retries or
> pilots. The local CPU run scored 10/20 in 18 minutes 31 seconds. See
> [the run instructions](codespaces-five-question-eval.md).

> **22 October decision update:** The AI exercise now uses 20 SQL questions and
> three scored stages: baseline → prompt improvement → prompt regression. Restore
> the improved prompt, then protect its semantic requirements; neither final step
> runs another eval. Gemma 4 E2B Q4_K_M in Docker/Codespaces is selected and basic
> inference was confirmed by Mark. [The implementation guide](sql-eval.md) defines
> the current scope. The original proposal below is retained as planning history;
> its ten-question and vocabulary-comparison sections are superseded for this exercise.
>
> **PR #9 review decision:** Reuse the existing workshop database and remove
> database fingerprinting. Keep its data unchanged during the three scored stages;
> the eval adds read-only access and does not run a separate seed process.
> Eval metadata uses readable values and direct comparisons; SHA fields and hash
> checks are omitted.
>
> **Answer-format decision:** Keep the 20 questions. The agent submits result
> values as rows; scoring compares them directly with expected values without
> database queries or a model judge. SQL remains a database tool input and trace
> detail. Reference-query validation is a separate setup check.

Documentation-only proposal · 20 October 2026

Mark: review the two-loop agenda, proposed time budgets and benchmark targets, then prioritize the first baseline-validation PR. You own the workshop and review decisions. Model, telemetry UI, vocabulary subset, exact questions, distribution permissions and budget remain open.

The proposed work window is **21–22 October 2026, America/Los_Angeles**; it is not an external deadline. Helsinki is the first delivery. Keep the curriculum reusable for the November O'Reilly version.

## What participants will do

The proposed three-hour, in-person workshop is hands-on and aimed at advanced Python/SQL users. Participants apply the same loop twice: **observe a failure → specify the contract → detect/prevent violations → rerun and interpret evidence**. First use the existing database/data-contract exercise, then repeat with an AI database-reading skill and semantic contracts. Use the same museum scenario, PostgreSQL infrastructure, and data throughout. Semantic rules constrain the skill and its use of data; there is no separate semantic layer.

Participants should leave able to:

1. Run a small local CPU model inside their Codespace.
2. Inspect tool calls and trajectory logs with an open-source local tool.
3. Run a quick evaluation.
4. Interpret its score, failures, and limitations.
5. Constrain skill files with explicit semantic rules and compare outcomes.

Each participant uses a lightweight Docker-based GitHub Codespace. The environment must require no additional service accounts, API keys, gated model access, hosted inference, or hosted telemetry. Choose the model and trace viewer only after benchmarking them together on the intended Codespaces size. Use the checked-in Met subset exclusively; live Met API calls and image downloads are not runtime dependencies.

The conceptual article combines Mark's Data Contracts work and Jessica Talisman's Ontology Pipeline work. Jessica collaborates on the article only: she is not a workshop developer, instructor, or endorser of these technology candidates.

## What we know about the baseline

Source baseline: `889babb2e30b85c0208f9472cedbc0a78bb466b4`. Existing components include Python 3.12, PostgreSQL 17, Alembic, JSON contract definitions, catalog coverage/violation checks, and database-backed tests. Static inspection is complete; successful startup and tests have **not** yet been demonstrated.

Read-only inspection of `data_contract_components/data_assets/db_migrations/raw_data/objects.json` found:

| Observation | Count |
| --- | ---: |
| Objects / unique object IDs | 3,025 / 3,025 |
| Top-level fields | 57 |
| Objects with tags / tag occurrences | 1,690 / 4,449 |
| Objects with actual AAT URLs | 1,644 |
| Actual AAT URL occurrences / distinct URLs | 3,894 / 443 |
| Other namespaces in the field named `AAT_URL`: IA / ULAN / TGN | 454 / 30 / 15 |
| Tag occurrences without a populated URL | 56 |

Useful fields include `title`, `department`, `classification`, `medium`, `culture`, `objectDate`, and tags containing `term`, `AAT_URL`, and `Wikidata_URL`. Department is populated for all objects; classification for 1,568, medium for 2,376, and culture for 1,392. The database already preserves tags in `object_tags` and related fields in normalized tables.

Before fixing the questions, explore how the data distinguishes subjects from materials, handles missing evidence, uses namespaces, and maps labels to identifiers. The sample maps “Leopards” and “Panthers” to the same stored AAT URL, but this is evidence to investigate, not an automatic synonym exercise or a verified equivalence claim. Do not cherry-pick an example just because it makes the constrained agent look better.

## Proposed 180-minute delivery

Start Codespaces immediately so setup overlaps the introduction. Private access and download preparation must be rehearsed before the event.

| Minutes | Activity | Participant evidence |
| --- | --- | --- |
| 0–15 | Launch environment; museum scenario and common loop | Health check and dataset identity |
| 15–35 | Existing architecture and guided SQL exploration | Read the existing contract and inspect related tables |
| 35–65 | Loop 1: introduce the existing data-contract violation, inspect detection, repair and rerun | Failing then passing contract checks; explain why |
| 65–75 | Debrief and short break | Connect structural guarantees to remaining semantic ambiguity |
| 75–95 | Local model, database-reading skill, tool boundaries; first query | One end-to-end trajectory |
| 95–120 | Loop 2 baseline: run fixed questions and inspect traces | Baseline scores and concrete failure categories |
| 120–150 | Add controlled-vocabulary semantic constraints to skill files | Reviewable rules grounded in museum data |
| 150–165 | Rerun identical evaluation and compare | Paired score/latency differences, including regressions |
| 165–180 | Interpret limitations, recap five takeaways, Q&A | Explain what improved, what did not, and next experiments |

This two-loop proposal replaces the older hour-by-hour outline. Benchmarks must show that evaluation fits these slots. If it does not, reduce agent step/token budgets or simplify scope before rehearsal. Keep questions fixed during the comparison. Recorded traces may support recovery from an environment failure but must be labeled as recordings, not a participant's live result.

## Compare results without exposing gold answers

### Freeze the comparison

After exploring the data and getting Mark's review, freeze approximately ten data-specific questions. Include clear answerable cases, ambiguous or missing evidence, and cases where abstention is appropriate. Define expected answers with reference SQL and human review. Draft constraints against separate development examples.

Keep the model and quantization, data snapshot, questions and order, decoding settings and seeds, tool permissions, step/token budgets, scoring rubric, and runtime identical in both conditions. Change only the versioned skill constraints and their declared vocabulary context. Record hashes and configuration. Fix seeds where supported and repeat a small paired sample to expose nondeterminism; do not claim seeds guarantee deterministic CPU inference.

### Separate the agent from the scorer

Proposed design:

- Give the agent runner only question text, an allowlisted read-only SQL tool with time and row limits, and approved skill/vocabulary files. Give it no arbitrary shell, filesystem, Docker socket, host network, or scorer endpoint.
- Mount gold only in a separate offline scorer container/process, with no agent-visible volume or database table. The scorer reads completed answer files after the agent exits.
- Return scores to the participant-facing viewer, never into an ongoing agent context.
- Exclude gold, reference SQL, expected outputs, and scorer traces from agent images, repository mounts, prompts, tool results, and logs. A prompt saying “do not read gold” is insufficient.

This protects gold from the model, not from a participant with administrative control of their Codespace; make that limitation explicit. Test isolation with sentinel content and attempted tool/file access before accepting the harness. Keep broad workspace mounts and the existing Docker socket away from the agent runtime.

### Interpret the result

Declare the rubric in advance and make it deterministic where possible: normalized answer sets/counts and IDs, explicit null/abstention rules, and evidence requirements. Mark resolves ambiguous cases before the questions and rubric are frozen. Report per-question outcomes, total correct out of N, regressions, timeouts/tool errors, tool-call counts, and latency alongside the paired difference. Ten items are a teaching diagnostic, not a general capability benchmark. No improvement or a regression is a valid result. Never weaken the baseline, leak gold, or change scoring to manufacture improvement.

## Prioritized work for the proposed two-day window

These timeboxes are estimates. The assistant prepares focused draft PRs and evidence; Mark reviews the teaching approach and accepts tradeoffs. No automatic merges or public distribution.

### Validate the baseline

P0 · Oct 21 · 60–90 min

Task: Reproduce original baseline before adding AI.

Acceptance and owner: The assistant records fresh startup, migrations, 3,025 seeded IDs, existing checks, an intentional failure and recovery, and a repeatable reset. Mark confirms loop matches the workshop. If blocked, fix baseline first.

### Explore the sample

P0 · Oct 21 · 60–90 min

Task: Explore sample and draft question categories; follows baseline.

Acceptance and owner: The assistant profiles joins, missingness, tags and namespace ambiguity. Mark selects failures worth teaching and approves approximately ten questions and their rubric; do not freeze synonyms in advance.

### Benchmark model and trace viewer

P0 · Oct 21 · 90–120 min

Task: Benchmark a small shortlist of ungated, commercially usable CPU models and open-source local trace viewers; follows baseline.

Acceptance and owner: Record the exact model, quantization and license; download size; cold and warm startup times; peak RAM; per-query p50/p95 latency; and total evaluation time with the database and viewer running. Proposed targets: fresh setup ≤15 min, warm setup ≤5 min, ten-question run ≤10 min, peak RAM ≤75% of selected machine. Mark accepts measured fit or revises scope. No account or API key may be required.

### Review access, cost and rights

P0 · Oct 21 · 30–45 min

Task: Review private participant access, Codespaces machine/cost, source permissions and vocabulary provenance.

Acceptance and owner: Mark owns access, budget and rights decisions; the assistant supplies options. Confirm distribution path and cost cap before invitations, paid settings, or broader sharing. These are not enabled by this plan.

### Build isolated evaluation

P1 · Oct 22 · 90–120 min

Task: Design and build isolated evaluation and minimal trace capture; depends on model, questions and access design.

Acceptance and owner: The assistant demonstrates gold isolation, read-only bounded SQL, frozen manifests, score validity and offline trace viewing. Log question and run IDs, skill version, tool inputs and results, final answer, duration and errors; do not promise hidden model reasoning. Mark reviews one complete run.

### Add semantic constraints

P1 · Oct 22 · 60–90 min

Task: Add minimal licensed vocabulary subset and semantic skill constraints; depends on data exploration and provenance gate.

Acceptance and owner: The assistant versions the source, retrieval date, hash, attribution, notices and explicit rules. Run the unchanged baseline and constrained comparison and report all outcomes. Mark approves instructional value, not a required score increase.

### Rehearse both loops

P1 · Oct 22 · 60–90 min

Task: End-to-end rehearsal and reusable instructor and participant notes; depends on all gates.

Acceptance and owner: Mark rehearses transitions and timing; assistant records timings, recovery steps and known failures. Both loops and five takeaways fit three hours. Keep November reuse in mind without expanding scope now.

If a timebox expires, deliver findings and scope a smaller next PR. Work proceeds from baseline validation to model/runtime fit and dataset exploration, then isolated evaluation, semantic constraints, and rehearsal.

Keep the trace UI lightweight. Reject candidates that require cloud sign-in, heavyweight services, or too much memory. Once selected, pin dependencies and dataset/model artifacts. Startup currently installs unpinned Python dependencies; measure reproducibility rather than assuming it.

## Vocabulary and rights candidates, not selections

- [Getty vocabulary data services](https://www.getty.edu/research-conservation/tools-databases/vocabularies/data-services/) identifies ODC-By 1.0 as its data license. [The license](https://opendatacommons.org/licenses/by/1-0/) permits use/adaptation subject to its conditions, including attribution and notices. A small frozen AAT subset is a candidate for commercial workshop use; retain source URIs, provenance, license link/text and applicable notices. Do not infer that every stored `AAT_URL` is AAT or import a vocabulary in this planning PR.
- [CIDOC CRM 7.1.3](https://cidoc-crm.org/sites/default/files/Documents/cidoc_crm_version_7.1.3.html), whose definition identifies CC BY 4.0, is an optional source for a tiny conceptual model. [Linked Art](https://linked.art/model/index.html) is an optional modeling profile. Neither is selected, required infrastructure, nor Jessica-endorsed.
- [Met Open Access documentation](https://metmuseum.github.io/) describes selected metadata under CC0. Image rights are separate; this exercise uses local metadata and must not assume every linked image is reusable.
- The original repository contains no explicit LICENSE/COPYING/NOTICE in the inspected tree. Preserve its README, attribution and history; Mark reviews permission before broader redistribution. Do not invent a source license or infer one from public availability.

## What this PR changes

This PR changes documentation only. The repository remains private, Actions disabled, and Pages disabled. No runtime, vocabulary import, participant invitations, spending changes, or workshop delivery claims are made here.
