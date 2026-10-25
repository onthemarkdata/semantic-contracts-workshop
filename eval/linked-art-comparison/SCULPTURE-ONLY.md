# Follow-up: locally supplied Sculpture guidance

Mark requested a prompt limited to Sculpture and asked that Linked Art be
available locally. Once the local text was connected to the prompt, he expanded
the evaluation from six sculpture questions to the full 26-question set.

The relevant upstream recommended-vocabulary page is now vendored under
`vendor/linked-art/guidance/`, with its license, pinned revision, and checksums.
The prompt builder extracts the Sculpture entry under Object Types, including
its actual description: "Object created by carving or engraving a hard material
or molding a malleable material". The full text is embedded in the model prompt;
no web access or file-reading tool is assumed. See the local attribution README.

Start from the unchanged local prompt. Add only that Sculpture reference and
the instruction to apply the supplied local category mapping. Retain all 17
source categories and the eight general SQL rules. Add no expected counts, SQL
examples, new database fields, prebuilt query, or other Linked Art concepts.

Freeze this replacement before inference. Run a fresh pair: local first, then
`sculpture-only`. Run all 26 questions (q01–q20 and s01–s06), with unchanged gold,
model, temperature, tool access, exact-row scoring, and frozen limits. Report
the original and sculpture sections separately. Preserve failures; do not retry
or tune after results arrive.

The earlier URI-only attempt was stopped when the requirement changed. Its
local control completed and its candidate was interrupted; those artifacts
remain under `artifacts/sculpture-only-run/` and are not a completed comparison.
The first six-question local-documentation attempt was also stopped when Mark
expanded the scope to the full evaluation. It is preserved under
`artifacts/sculpture-local-docs-run/` and is not used for the full-run scores.
Use a new output directory for the full locally documented pair.

This is an exploratory follow-up after seeing the first broader experiment.
That earlier prompt is not rerun; its score is historical. Placement also differs
from that older prompt, so cross-run differences cannot isolate text length or
individual concepts. One paired run is not independent confirmation.
The new pair tests the embedded local Sculpture reference as a whole.

```bash
python3 scripts/build_sculpture_prompt.py
python3 scripts/sql_eval.py build
python3 scripts/sql_eval.py start
python3 scripts/sql_eval.py isolation
python3 scripts/run_linked_art_eval.py --candidate sculpture-only --section all --out artifacts/linked-art-local-docs-full-run
python3 scripts/sql_eval.py stop
```

The experimental prompt is separate from the original governed MAP assets.
The official schema/context and deterministic exporter remain unchanged. This
evaluates SQL answers, not model-generated JSON-LD or full Linked Art conformance.
