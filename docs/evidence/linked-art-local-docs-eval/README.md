# Full evaluation with local Linked Art Sculpture guidance

Mark requested a prompt limited to Linked Art's Sculpture section, then asked
that Linked Art be present locally and that the full evaluation be rerun.
This compares fresh runs of the local-category prompt and the prompt containing
the actual local Sculpture reference, across all 26 questions.

The upstream recommended-vocabulary page is vendored under
[`vendor/linked-art/guidance/`](../../../vendor/linked-art/guidance/README.md),
with its license, pinned revision, and checksums. The builder extracts the
Sculpture entry under Object Types and embeds its label, full URI, and description
in the model prompt:

> Sculpture (http://vocab.getty.edu/aat/300047090): Object created by carving or engraving a hard material or molding a malleable material

The model receives this text directly. It does not need to open a URL or read
an arbitrary file; neither capability is available to this eval agent. Only the
Sculpture entry goes into the prompt, not the other vocabulary sections.
The 17 Met categories remain the workshop's local membership rule.

See the [prompt](../../../eval/linked-art-comparison/sculpture-only.json),
[frozen plan](../../../eval/linked-art-comparison/SCULPTURE-ONLY.md), and
[previous broader experiment](../linked-art-eval/README.md).

## Results

| Question set | Local category | Local Sculpture reference | Change |
| --- | ---: | ---: | ---: |
| Original questions | 9/20 | 10/20 | +1 |
| Sculpture questions | 3/6 | 2/6 | -1 |
| Combined diagnostic | 12/26 (46.2%) | 12/26 (46.2%) | +0 |

Eval time: local 567.066 seconds; Local Sculpture reference 520.912 seconds. Times exclude setup, scoring, and validation.

Fixed: q03, q13, q20, s02.
Regressed: q09, q18, s01, s03.

| Question | Local category | Local Sculpture reference |
| --- | --- | --- |
| q01 | wrong_result | wrong_result |
| q02 | correct | correct |
| q03 | query_error | correct |
| q04 | correct | correct |
| q05 | correct | correct |
| q06 | correct | correct |
| q07 | query_error | query_error |
| q08 | correct | correct |
| q09 | correct | query_error |
| q10 | correct | correct |
| q11 | query_error | query_error |
| q12 | correct | correct |
| q13 | wrong_result | correct |
| q14 | wrong_result | wrong_result |
| q15 | query_error | query_error |
| q16 | wrong_result | wrong_result |
| q17 | wrong_result | wrong_result |
| q18 | correct | query_error |
| q19 | wrong_result | truncated_response |
| q20 | wrong_result | correct |
| s01 | correct | wrong_result |
| s02 | wrong_result | correct |
| s03 | correct | query_error |
| s04 | wrong_result | wrong_result |
| s05 | correct | correct |
| s06 | query_error | query_error |

The local reference fixed the missing-context problem: the model received the
actual Sculpture description. It did **not improve overall accuracy** in this
pair. Four questions improved and four regressed, with a one-question decline
on the sculpture section.

For the main sculpture count (s01), the local control returned 296 and the
reference condition returned 286. The latter SQL omitted `Sculpture-Wood`,
excluding ten records despite the complete list being in the prompt. It did
correctly answer the departmental sculpture question (s02), which the control
missed. Its public-domain sculpture query (s03) failed on an invalid table
reference. Both conditions still counted sculptures instead of all 3,025 sample
objects in q01.

This distinguishes access to a correct reference from applying the agreed
mapping correctly. The local documentation is available and tested, but that
alone does not enforce the model's generated SQL. This one paired run supports
no claim of an accuracy gain from the added reference.

## Evidence and validation

- `local-report.json` and `sculpture-only-report.json` retain the prompts, shared controls, per-question outcomes, tool-call counts, and timings.
- `comparison.json` records matching controls, section scores, fixes, and regressions.
- `answers.json` contains extracted SQL, tool rows, submitted rows, and errors for every attempt; full raw response traces remain outside Git.
- `map-check.json` passes for the unchanged governed assets, including 296 schema-valid and correctly classified Linked Art objects. This is separate from the experimental SQL score.
- All 87 automated tests passed, including six database integration tests and seven comparison tests. The added tests verify local-source integrity and delivery of the actual Sculpture description into the model request. All 26 reference queries and the agent-image gold isolation check passed.

## Method and limits

Executed October 25, 2026 (UTC), starting from `355ab153af1777a4fa6e5fb7a4dcbeea73e788a2`.
Run a fresh local control first, then the local-documentation prompt. The original
20 questions and six sculpture questions, their order, and their gold are
unchanged. Both prompts keep all 17 categories and eight general SQL rules.
No reference counts, SQL examples, or additional Linked Art concepts are added.
Both conditions already have the complete category mapping; the added reference
provides the Sculpture description, not new source-category membership facts.

The pinned Gemma 4 E2B Q4_K_M CPU model, temperature zero, database and schema,
one SQL attempt, 384 output tokens, 271-second limits, and exact-row scoring
remain unchanged. Gold is mounted only into the scorer. Every question starts
with a fresh model prompt; no answer history is supplied across questions.

Two narrower attempts were interrupted when Mark changed the requirements:
the URI-only attempt under `artifacts/sculpture-only-run/`, then the six-question
local-documentation attempt under `artifacts/sculpture-local-docs-run/`. Their
completed local controls and incomplete candidates are preserved, but neither
is used in this full comparison. The full run's raw response traces remain in
the ignored `artifacts/linked-art-local-docs-full-run/` directory.

This is an exploratory follow-up designed after the previous broader result.
The fresh local control is the paired comparator. The earlier broader prompt
was not rerun here; its scores are historical. Placement also differs from that
version, so historical differences cannot isolate individual concepts or text
length. One paired run cannot establish reliable improvement. No retries or
post-result tuning are included. Runtime and caching can affect timing.

The model still generates SQL. This does not test generating JSON-LD, running
a local Linked Art website, or using an enforced query/view. These experimental
prompts are separate from the original governed MAP assets. The existing
schema/context and exporter remain unchanged. MAP validity and model accuracy
are separate checks. The original README is unchanged.
