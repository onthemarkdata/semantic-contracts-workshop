# Met categories: prompt, MAP, and Linked Art

This experiment replaces the ten harder questions with questions about sculpture,
painting, drawing, print, furniture, and architectural objects. It keeps the ten
basic questions unchanged. The replacement set lives in
[`eval/category-comparison/questions.json`](../eval/category-comparison/questions.json);
earlier question sets and their recorded scores remain intact.

All three conditions use the same 3,025 Met object records and the existing
read-only SQL tool. No database objects, rows, views, model settings, SQL-tool
rules, or scoring rules change.

## What changes between conditions

| Condition | Prompt contents |
| --- | --- |
| [Prompt only](../eval/category-comparison/prompt-only.json) | The existing general semantic SQL prompt, with its eight general rules and no category mapping |
| [Prompt + MAP](../eval/category-comparison/prompt-map.json) | The same prompt, plus the local category lists and rules for membership, overlap, exclusions, and unknown classifications |
| [Prompt + MAP + Linked Art](../eval/category-comparison/prompt-map-linked-art.json) | The same MAP prompt, plus six names, URIs, and descriptions from the pinned local Linked Art vocabulary |

“Prompt only” is the current general prompt, not the earlier minimal baseline.
It already explains joins, missing values, public-domain status, and result
formatting. The first comparison measures the effect of supplying the local
category agreement. The second isolates the additional Linked Art reference
text; it does not change membership or reference answers.

Both category MAP profiles are sections of the
[`original data contract`](../data_contract_components/contract_definition/object_images_contract_spec.json).
Their approved instructions govern the two generated prompt assets. The shared
vocabulary comes from the existing, unmodified
[`local Linked Art documentation`](../vendor/linked-art/guidance/recommended-vocabulary.md),
with its pinned revision, checksums, attribution, and CC BY 4.0 license preserved.
The agent receives the definitions in its prompt; it does not fetch web pages.

## The category agreement

| Local category | Included Met classifications | Linked Art reference |
| --- | --- | --- |
| Sculpture | The existing 17-label sculpture list | Sculpture, AAT 300047090 |
| Painting | Miscellaneous-Paintings; Paintings; Paintings-Fresco; Paintings-Panels | Painting, AAT 300033618 |
| Drawing | Drawings | Drawing, AAT 300033973 |
| Print | Prints | Print, AAT 300041273 |
| Furniture | Furniture; Furniture-Wood; Wood-Furniture; Woodwork-Furniture | Furniture, AAT 300037680 |
| Architectural objects | Sculpture-Architectural; Sculpture-Architectural-Stone; Wood-Architectural | Architecture, AAT 300263552 |

Match the complete labels after trimming surrounding spaces. Count each object
ID once. Categories can overlap: **both** means intersection; **either** means
union with duplicate object IDs removed. General artwork questions still refer
to all object records.

`Sword Furniture-Tsuba` is a sword fitting and is excluded from Furniture.
Architectural sculpture belongs to both Sculpture and Architectural objects.
Painted or carved furniture does not automatically gain another category: this
exercise uses the agreed source-label mapping, not title or material inference.

These are local workshop decisions based on a desk review of classifications,
titles, and media. Some architectural sculpture records are a table or funerary
figure. They remain explicit review cases. The mapping is not a claim that every
Met label exactly equals the AAT concept, nor a curator-validated classification
of every object. Unknown or unmapped classifications do not establish that an
object falls outside a category in the real world.

## The replacement questions

| ID | Task |
| --- | --- |
| q11 | Count sculptures outside the exact label Sculpture |
| q12 | Count public-domain paintings |
| q13 | Count drawings by department |
| q14 | Count public-domain prints with a populated primary image URL |
| q15 | Count furniture across the agreed labels |
| q16 | Count architectural objects |
| q17 | Count the intersection of sculpture and architectural objects |
| q18 | Count their union without double-counting |
| q19 | Count paintings outside the exact label Paintings |
| q20 | List the first five furniture objects by object ID |

“Hard” identifies the replacement question group, not a measured difficulty
rating. The reference answers are computed independently from the checked-in
source JSON and checked against reference SQL before inference.

## Run the comparison

Use an already prepared workshop environment with the existing database and
read-only eval connection. This runner does not initialize or alter the database.
From the repository root:

```bash
python3 scripts/build_category_eval.py --check
python3 scripts/sql_eval.py build
docker compose -p workshop-sql-eval -f compose.models.yaml -f compose.eval.yaml up -d model-init
docker compose -p workshop-sql-eval -f compose.models.yaml -f compose.eval.yaml wait model-init
python3 scripts/run_category_eval.py --out artifacts/met-categories-run-1
python3 scripts/sql_eval.py stop
```

Use a new output directory for each run. The runner freezes and hashes inputs,
verifies all 20 reference queries, and executes the conditions in the table's
order. All conditions use the same model, decoding settings, question order,
database context, one-query budget, and scorer. It rejects differing recorded
controls. Gold is mounted only in the separate scorer, after each agent exits;
the model receives no scores or reference answers.

For each condition, inspect its `*-reports/report.json` and question traces.
`comparison.json` reports total, basic, and hard scores, plus fixes and
regressions between adjacent conditions. The recorded comparison is in
[`evidence/met-category-eval`](evidence/met-category-eval/README.md).

## What GitHub checks

The existing Prompt MAP workflow checks approved instructions and the eight
general semantic settings. Changing a category in the prompt changes approved
instructions and fails the check. Changing the contract itself triggers
`policy.change` and separate maintainer review. Adding these profiles therefore
produces an expected policy-review failure on the implementation PR, while its
branch self-check can pass. A failed check blocks merging only where the target
branch rules require it.

CI checks prompt configuration. The eval checks whether the model follows that
configuration and answers correctly. Neither result establishes full Linked Art
conformance or curatorial validity.

## Interpret the results

All three runs use the new questions, so compare them with each other, not with
the old 20- or 26-question totals. Report the ten basic and ten hard scores
separately, along with per-question errors and elapsed time. There is one run per
condition, in a fixed order, with no prompt revisions after seeing results.
These are teaching diagnostics; they do not establish a statistically reliable
gain. Extra Linked Art text may help, have no effect, or hurt. This SQL exercise
also does not test interoperability between collections.
