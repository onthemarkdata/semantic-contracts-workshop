# Linked Art sculpture mapping: validation evidence

This version uses Linked Art's **actual JSON-LD context, Human-Made Object schema,
and recommended Sculpture identifier**. It extends the original contract's MAP
with `museum-linked-art-sculpture-map`, which governs
`eval/prompts/linked-art-sculpture.json`.

The exporter reads that prompt's structured settings directly. This is a
mapping-and-validation exercise; no language model generated these records and
no new model accuracy score is claimed.

## What comes from Linked Art

The source is the [official repository](https://github.com/linked-art/linked.art/tree/bcbff1761e65f44eeaeb92b4b2b83da2783539f8).
The copied resources are pinned and attributed under CC BY 4.0 in
[vendor/linked-art](../../../vendor/linked-art/README.md).

| Meaning | Linked Art representation |
| --- | --- |
| Physical object | `type: HumanMadeObject`, expanding to CIDOC CRM `E22_Human-Made_Object` |
| Sculpture | `classified_as` with full URI `http://vocab.getty.edu/aat/300047090` |
| Kind of work | Sculpture's meta-classification `http://vocab.getty.edu/aat/300435443` |
| Collection item | Separate classification `http://vocab.getty.edu/aat/300404024` |
| Artwork | Separate classification `http://vocab.getty.edu/aat/300133025`; not inferred from collection membership |
| Primary name | `identified_by` with a `Name` classified as `http://vocab.getty.edu/aat/300404670` |

The distinctions and identifiers are documented in Linked Art's
[basic patterns](https://github.com/linked-art/linked.art/blob/bcbff1761e65f44eeaeb92b4b2b83da2783539f8/docs/model/base/index.md),
[recommended vocabulary](https://github.com/linked-art/linked.art/blob/bcbff1761e65f44eeaeb92b4b2b83da2783539f8/docs/model/vocab/recommended/index.md),
and [required vocabulary](https://github.com/linked-art/linked.art/blob/bcbff1761e65f44eeaeb92b4b2b83da2783539f8/docs/model/vocab/required/index.md).
A display label is human-readable documentation; the class and concept URIs carry
the identity used by the check.

## What remains a local decision

The 17 Met classification labels from the preceding example are explicitly mapped
to the broader Sculpture concept. This grouping is proposed workshop policy, not
a crosswalk published by the Met, Getty, or Linked Art. It does not assert exact
vocabulary equivalence for labels such as `Wood-Sculpture`.

Only those 296 source records are exported. The 1,457 unclassified records remain
unknown, and the other 1,272 classified records remain unmapped in this exercise.
Neither group is declared to be non-art or non-sculpture. The export preserves one
identity per source `objectID` and records the source classification in a note.
The `example.org` object URIs are workshop identifiers, not hosted museum records.

[example-object.json](example-object.json) shows the generated representation of
Met object 200668, *Sabine Houdon (1787–1836)*. Its
[expanded form](example-expanded.json) shows the actual CIDOC CRM properties and
full classification URIs obtained using the pinned Linked Art context.

## Observed results

| Case | Exported records | Official object schema | Physical Sculpture identities after expansion | MAP |
| --- | ---: | --- | ---: | --- |
| Agreed class and Sculpture URI | 296 | PASS | 296 | PASS |
| Substitute Artwork URI for Sculpture URI | 296 | PASS | 0 | FAIL |
| Substitute `DigitalObject` for `HumanMadeObject` | 296 | FAIL | 0 | FAIL |

Reports: [approved](pass-report.json), [wrong concept](concept-violation-report.json),
[wrong entity class](class-violation-report.json).

**Zero is the consequence of the deliberately incorrect encoding.** The 296 source
objects have not disappeared. Their records no longer match the agreed physical
Sculpture identity. The concept violation deliberately retains the display label
“Sculpture,” demonstrating why label matching cannot replace identifier checks.
The class violation fails the selected physical-object schema; DigitalObject is a
valid Linked Art class for other kinds of entities.

No museum data, original prompt, question bank, or reference answer was changed.
These checks do not establish full Linked Art conformance, curatorial validity,
or model obedience.

## Reproduce

From the repository root in the workshop Codespace:

```bash
python3 -m pip install -r requirements-linked-art.txt
python3 scripts/linked_art_sculpture.py --out artifacts/linked-art/pass
```

Expect exit code 0. The script writes all 296 records, their expanded JSON-LD, and
the validation report. To demonstrate a schema-valid semantic violation:

```bash
python3 scripts/linked_art_sculpture.py \
  --prompt eval/prompts/linked-art-concept-violation.json \
  --out artifacts/linked-art/concept-fail
```

Expect exit code 1, `schema_valid: true`, and `expanded_sculpture_count: 0`.
The other fixture demonstrates the physical/digital class distinction:

```bash
python3 scripts/linked_art_sculpture.py \
  --prompt eval/prompts/linked-art-class-violation.json \
  --out artifacts/linked-art/class-fail
```

Expect exit code 1 and `schema_valid: false`. Schema resolution and JSON-LD
expansion use only vendored resources. Installing the Python packages requires
normal package-index access; running the checks does not call an external
vocabulary service.

`python3 scripts/check_prompt_map.py` also validates this mapping as part of the
normal MAP check. In a PR, the base branch's validator, contract, schemas, and
context are used. A proposal to change the mapping policy or validation resources
requires review; editing them alongside a violating prompt cannot silently approve
that prompt.
