# Local categories versus Linked Art: model evaluation

This comparison measures whether adding Linked Art guidance changes the model's
SQL answers. Both conditions receive the same 17-category sculpture mapping,
same SQL task, and same eight general semantic rules. Only the Linked Art
condition adds the physical-object and Sculpture URI rules. See the
[frozen plan](../../../eval/linked-art-comparison/PLAN.md),
[local prompt](../../../eval/linked-art-comparison/local.json), and
[Linked Art prompt](../../../eval/linked-art-comparison/linked-art.json).

The original sculpture and Linked Art demonstration prompts ask for different
outputs. These experimental variants normalize that difference so it cannot
explain the measured score change. They do not replace the governed prompts.

## Results

| Question set | Local category | Linked Art | Change |
| --- | ---: | ---: | ---: |
| Original questions | 9/20 | 11/20 | +2 |
| Sculpture questions | 3/6 | 1/6 | -2 |
| Combined diagnostic | 12/26 (46.2%) | 12/26 (46.2%) | +0 |

Eval time: local 580.871 seconds; Linked Art 533.167 seconds. Times exclude setup, scoring, and validation.

Fixed: q03, q07, q15.
Regressed: q09, s01, s03.

| Question | Local category | Linked Art |
| --- | --- | --- |
| q01 | wrong_result | wrong_result |
| q02 | correct | correct |
| q03 | query_error | correct |
| q04 | correct | correct |
| q05 | correct | correct |
| q06 | correct | correct |
| q07 | query_error | correct |
| q08 | correct | correct |
| q09 | correct | truncated_response |
| q10 | correct | correct |
| q11 | query_error | query_error |
| q12 | correct | correct |
| q13 | wrong_result | wrong_result |
| q14 | wrong_result | wrong_result |
| q15 | query_error | correct |
| q16 | wrong_result | wrong_result |
| q17 | wrong_result | wrong_result |
| q18 | correct | correct |
| q19 | wrong_result | truncated_response |
| q20 | wrong_result | wrong_result |
| s01 | correct | wrong_result |
| s02 | wrong_result | query_error |
| s03 | correct | query_error |
| s04 | wrong_result | wrong_result |
| s05 | correct | correct |
| s06 | query_error | wrong_result |

The extra Linked Art guidance did **not improve the combined score** in this
run. The gain on original questions was offset by a decline on the questions
that directly test sculpture membership. This does not support teaching Linked
Art as an answer-accuracy improvement on this task.

The main sculpture count (s01) makes the regression concrete: the local prompt
returned **296**; the Linked Art prompt returned **286**. Its SQL omitted
`Sculpture-Wood`, excluding ten objects. Both prompts contained all 17 approved
categories. In s03, the Linked Art condition lost a previously correct answer
by referencing the classification table without joining it. Both conditions
also misread the full-sample count (q01) as a sculpture count and returned 296
instead of 3,025.

These results distinguish three checks: a prompt can contain the approved
rules; a deterministic exporter can produce valid Linked Art records; and the
model can still generate SQL that violates those rules. The first two checks
pass here while answer accuracy remains limited. Retain Linked Art for its
explicit identity and validation role; this run gives no reason to promise that
appending its rules will improve the model's sculpture answers.

## Evidence and validation

- `local-report.json` and `linked-art-report.json` retain the prompts, shared controls, per-question outcomes, tool-call counts, and timings.
- `comparison.json` records matching controls, section scores, fixes, and regressions.
- `answers.json` contains extracted SQL, tool rows, submitted rows, and errors for every attempt; full raw response traces remain outside Git.
- `map-check.json` passes for the unchanged governed assets, including 296 schema-valid and correctly classified Linked Art objects. This is separate from the experimental SQL score.
- All 83 automated tests passed, including six database integration tests and three comparison tests. All 26 reference queries and the agent-image gold isolation check passed.

## Method

Run in the managed Linux cloud environment on October 25, 2026 (UTC), based on
commit `1727c166ae20c332e8df9f132fcce514019c4c00`. The pinned Gemma 4 E2B Q4_K_M
model runs locally on CPU. Both conditions use temperature zero, the same
schema and read-only database, one SQL attempt per question, 384 output tokens
per response, and the existing 271-second question/request limits. Local runs
first, then Linked Art; there is no fixed seed in the current client.

The original q01–q20 and their gold answers are unchanged. Six additional
questions s01–s06 test the sculpture mapping and are reported separately.
All 26 reference SQL queries matched independently source-derived answers
before inference. The model receives no reference SQL or expected answers.
The isolated scorer compares submitted rows exactly, using the existing
numeric normalization and ordered/unordered rules; no model judge is involved.

No retries, post-result prompt tuning, question removal, or budget changes are
allowed. The comparator rejects differing run controls. Full visible action
traces remain in the ignored `artifacts/linked-art-comparison-run/` directory.
Both manifests use the harness's internal stage name `improved`; the prompt
contents and directory names identify the two experimental conditions.

## What this can establish

This is one paired SQL diagnostic. It tests the effect of extra Linked Art
instructions on answers over the existing relational database. It does not
test model-generated JSON-LD, querying a graph, or interoperability with another
museum. URI rules may add little useful information to this particular task.
The local category mapping remains necessary in both conditions.

Answer accuracy and contract compliance are separate. The original governed
prompts and the deterministic Linked Art exporter are checked independently;
a passing contract does not establish that model answers are correct. The
experimental prompts are not registered as new governed MAP assets.

A score difference from one run does not establish a general capability change.
Fixed temperature does not guarantee reproducibility. Prompt length, caching,
run order, and shared CPU load can affect timing, so these timings are descriptive.
