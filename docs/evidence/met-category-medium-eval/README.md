# Met category comparison: medium-question run

This is one fresh run of each condition on the same 20 questions: ten unchanged basic questions and ten medium category questions. The database and runtime were unchanged. No prompt or question was revised after inference began.

| Condition | Basic | Medium | Total | Seconds |
| --- | ---: | ---: | ---: | ---: |
| prompt-only | 9/10 | 1/10 | 10/20 | 136.568 |
| prompt-map | 5/10 | 10/10 | 15/20 | 249.725 |
| prompt-map-linked-art | 7/10 | 9/10 | 16/20 | 281.638 |

The first contrast adds the local category agreement to the existing general semantic prompt. The second adds only the pinned Linked Art names, URIs, and descriptions; both MAP conditions have identical membership rules. Extra context does not guarantee improvement.

## Per-question results

| Question | Group | Prompt only | + MAP | + Linked Art |
| --- | --- | --- | --- | --- |
| q01 | Basic | pass | query_error | query_error |
| q02 | Basic | pass | query_error | pass |
| q03 | Basic | pass | query_error | pass |
| q04 | Basic | pass | pass | pass |
| q05 | Basic | pass | pass | pass |
| q06 | Basic | pass | pass | pass |
| q07 | Basic | query_error | query_error | query_error |
| q08 | Basic | pass | query_error | query_error |
| q09 | Basic | pass | pass | pass |
| q10 | Basic | pass | pass | pass |
| q11 | Sculpture | wrong answer | pass | pass |
| q12 | Painting | query_error | pass | pass |
| q13 | Drawing | wrong answer | pass | pass |
| q14 | Print | query_error | pass | query_error |
| q15 | Furniture | query_error | pass | pass |
| q16 | Architectural objects | wrong answer | pass | pass |
| q17 | Sculpture | wrong answer | pass | pass |
| q18 | Architectural objects | wrong answer | pass | pass |
| q19 | Painting | pass | pass | pass |
| q20 | Furniture | wrong answer | pass | pass |

## Changes between conditions

- **prompt-only → prompt-map**: fixed q11, q12, q13, q14, q15, q16, q17, q18, q20; regressed q01, q02, q03, q08.
- **prompt-map → prompt-map-linked-art**: fixed q02, q03; regressed q14.

## What changed in the answers

Adding the MAP fixed nine medium-category answers, giving **10/10 medium**,
while four basic answers regressed. The total rose from 10/20 to 15/20. For
example, prompt only queried the nonexistent label `Sculptures` and returned
zero; MAP used the complete 17-label list and correctly counted 296 sculptures.

Adding Linked Art recovered q02 and q03 (basic artist-name counts), but q14
(print count) regressed. The model queried `object_tags` using an unsupported
JSON operation instead of the agreed classification field. Its total was 16/20,
with **9/10 medium**. The one-point overall gain therefore does not demonstrate
better category mapping from Linked Art; MAP alone had the stronger category
score in this run.

Correct answers do not prove that every generated query follows every MAP rule.
The scorer checks answer values; GitHub checks the prompt configuration. This is
one controlled teaching run, not a statistically reliable performance estimate.

## Evidence and limits

- [Machine-readable comparison](comparison.json), [input hashes](input-hashes.json), and [source/runtime provenance](provenance.json).
- [Prompt-only report](prompt-only-report.json), [MAP report](prompt-map-report.json), and [Linked Art report](prompt-map-linked-art-report.json) retain the complete controls and prompts.
- [Question details](question-details.json) include generated SQL, database observations, submitted answers, reference answers, errors, token usage, and elapsed time. This evidence is produced after inference and is never mounted into the agent.
- All 20 reference queries agreed with answers independently computed from the checked-in source JSON. Gold remained in the separate scorer.
- All recorded controls match across conditions. The fixed order was prompt only, MAP, then MAP plus Linked Art. Startup and prompt-cache effects can influence elapsed time.
- Condition names come from report filenames. The existing harness records `stage: improved` for all three because each run supplies an explicit prompt file.
- One run per condition, with temperature zero, is a teaching diagnostic. It does not establish a statistically reliable gain or guarantee deterministic inference.
- The earlier hard-category and 26-question scores use different questions and are not comparable totals. No collection-interoperability or full Linked Art conformance claim is made.
- Full raw response traces remain in the ignored local `artifacts/met-category-medium-run-1/` directory. The published question details preserve the SQL and answer evidence needed to inspect the outcomes.

See [the experiment and reproduction instructions](../../met-category-comparison.md).
