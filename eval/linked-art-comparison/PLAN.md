# Local categories versus Linked Art: frozen comparison

Compare SQL answer accuracy with the same local sculpture mapping, adding only
Linked Art entity and classification guidance to the second condition. Both
prompts use the existing semantic SQL instructions and eight general rules.
The two additional rules come unchanged from the Linked Art prompt renderer.
Neither condition receives gold answers, reference SQL, or example counts.

Run the existing q01–q20 unchanged, followed by six new sculpture questions in
both conditions. Report these sections separately. The additional questions
cover mapping coverage, departmental aggregation, public-domain filtering,
nonliteral category membership, unknown classification, and unmapped categories.
Expected answers are computed from the checked-in source independently of SQL;
verify every reference query against the existing database before inference.

Use the pinned Gemma 4 E2B Q4_K_M model, CPU settings, temperature 0, existing
271-second question/request limits, 384 output tokens per response, one SQL call,
20-row tool limit, existing exact-row scorer, and identical database context.
Run local first, then Linked Art. There is no fixed seed in the current client.
No retries, prompt tuning, budget changes, or question removal after seeing
results. Preserve incorrect answers and all visible action traces. This single
paired run is a teaching diagnostic; caching and order can affect latency.

This measures the effect of Linked Art guidance on relational SQL answers.
The model does not generate or query JSON-LD in this comparison. Schema and MAP
compliance are separate deterministic checks, not points in the answer score.
The normalized eval prompts are experimental variants, not new governed assets
in the original contract. The existing governed prompts stay unchanged.

Reproduce from the repository root after starting the workshop database:

```bash
python3 scripts/build_linked_art_eval.py
python3 scripts/sql_eval.py build
python3 scripts/sql_eval.py start
python3 scripts/sql_eval.py isolation
python3 scripts/run_linked_art_eval.py --out artifacts/linked-art-comparison-run
python3 scripts/sql_eval.py stop
```

The agent receives only questions, the selected prompt, budget, schema, and its
query results. The separate scorer alone receives the combined reference file.
The output directory must be new. Keep it intact for review.
