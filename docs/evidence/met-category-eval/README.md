# Met category comparison: historical hard-version run

> These scores apply to the **hard** question set at commit
> [`31c3e83`](https://github.com/onthemarkdata/semantic-contracts-workshop/blob/31c3e83035f6496c40e2804385736c0aac702dc3/eval/category-comparison/questions.json).
> The current questions are medium difficulty and have not had a model evaluation.
> The reports and scores below are preserved unchanged; they do not measure the medium set.

This is one fresh run of each condition on the same 20 questions: ten unchanged basic questions and ten replacement category questions. The database and runtime were unchanged. No prompt or question was revised after inference began.

| Condition | Basic | Hard | Total | Seconds |
| --- | ---: | ---: | ---: | ---: |
| prompt-only | 9/10 | 1/10 | 10/20 | 179.868 |
| prompt-map | 5/10 | 0/10 | 5/20 | 255.296 |
| prompt-map-linked-art | 7/10 | 1/10 | 8/20 | 312.052 |

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
| q11 | Sculpture | wrong answer | wrong answer | wrong answer |
| q12 | Painting | query_error | query_error | wrong answer |
| q13 | Drawing | pass | query_error | query_error |
| q14 | Print | wrong answer | wrong answer | query_error |
| q15 | Furniture | wrong answer | query_error | pass |
| q16 | Architectural objects | wrong answer | query_error | query_error |
| q17 | Overlap | wrong answer | query_error | wrong answer |
| q18 | Overlap | query_error | query_error | query_error |
| q19 | Painting | wrong answer | wrong answer | wrong answer |
| q20 | Furniture | query_error | query_error | query_error |

## Changes between conditions

- **prompt-only → prompt-map**: fixed none; regressed q01, q02, q03, q08, q13.
- **prompt-map → prompt-map-linked-art**: fixed q02, q03, q15; regressed none.

## What the SQL shows

The Linked Art condition recovered three answers from MAP alone, but remained
below prompt only overall. Its furniture query counted all 23 objects; prompt
only counted the six records labeled exactly `Furniture`, and MAP alone used
the wrong table for `classification`.

All three conditions missed the membership-plus-exclusion questions. For q11,
they returned 2,874 objects outside the exact label `Sculpture`, instead of the
145 mapped sculptures outside that label. For q19, they returned 2,680 objects
outside `Paintings`, instead of the eight mapped painting variants. Supplying
the rule did not make the model apply it.

MAP alone also produced 12 query errors, including incorrect table references
and unsupported SQL. These are execution failures, distinct from a disagreement
about category membership. This experiment does not demonstrate a general
accuracy benefit from adding the MAP or Linked Art text.

## Evidence and limits

- [Machine-readable comparison](comparison.json), [input hashes](input-hashes.json), and [source/runtime provenance](provenance.json).
- [Prompt-only report](prompt-only-report.json), [MAP report](prompt-map-report.json), and [Linked Art report](prompt-map-linked-art-report.json) retain the complete controls and prompts.
- [Question details](question-details.json) include generated SQL, database observations, submitted answers, reference answers, errors, token usage, and elapsed time. This evidence is produced after inference and is never mounted into the agent.
- All 20 reference queries agreed with answers independently computed from the checked-in source JSON. Gold remained in the separate scorer.
- All recorded controls match across conditions. The fixed order was prompt only, MAP, then MAP plus Linked Art. Startup and prompt-cache effects can influence elapsed time.
- Condition names come from report filenames. The existing harness records `stage: improved` for all three because each run supplies an explicit prompt file.
- One run per condition, with temperature zero, is a teaching diagnostic. It does not establish a statistically reliable gain or guarantee deterministic inference.
- Earlier 20- and 26-question scores use different questions and are not comparable totals. No collection-interoperability or full Linked Art conformance claim is made.
- Full raw response traces remain in the ignored local `artifacts/met-category-comparison/` directory. The published question details preserve the SQL and answer evidence needed to inspect the outcomes.

See [the experiment and reproduction instructions](../../met-category-comparison.md).
