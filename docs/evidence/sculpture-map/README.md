# Sculpture category membership: measured consequence

The proposed workshop definition counts **296 object records** across 17 explicit
classification labels. Narrowing the prompt to the exact label `Sculpture` counts
**151**, excluding **145** records that belong to the proposed group.

These are deterministic counts from the checked-in sample, independently confirmed
by running [both SQL queries](comparison.sql) on the seeded PostgreSQL database as
`eval_reader`. No model inference ran, no evaluation questions or reference answers
changed, and these counts are not model accuracy scores.

[comparison.json](comparison.json) records all labels, counts, excluded categories,
and the 1,457 records with unknown classification. The new profile lives under
`metadataApplicationProfile.additionalProfiles` in the original
[object-images contract](../../../data_contract_components/contract_definition/object_images_contract_spec.json).
The original eight-rule profile and evaluated prompts retain their existing content.

| Included source label | Objects |
| --- | ---: |
| Bark-Sculpture | 2 |
| Beads-Sculpture | 1 |
| Bone/Ivory-Sculpture | 2 |
| Ceramics-Sculpture | 8 |
| Metal-Sculpture | 4 |
| Sculpture | 151 |
| Sculpture-Alabaster | 1 |
| Sculpture-Architectural | 6 |
| Sculpture-Architectural-Stone | 3 |
| Sculpture-Bronze | 8 |
| Sculpture-Ceramics | 1 |
| Sculpture-Miniature | 1 |
| Sculpture-Stone | 11 |
| Sculpture-Wood | 10 |
| Stone Sculpture | 39 |
| Stone-Sculpture | 8 |
| Wood-Sculpture | 40 |
| **Total** | **296** |

This is a proposed local definition for review. The listed labels explicitly name
sculpture; runtime membership uses their exact values after trimming surrounding
spaces. It does not discover categories with a substring search. Labels such as
`Bronzes` and `Vases` do not enter this count solely because of their material or
form. Exclusion does not establish that an object cannot be a sculpture. NULL,
empty, and space-only classifications remain unknown. This is not an asserted
Linked Art or AAT equivalence mapping.

Reproduce from the repository root:

```bash
python3 scripts/compare_sculpture_scope.py \
  --prompt eval/prompts/sculpture-violation.json
```

This compares the contract's complete list with the deliberately narrowed fixture
and writes ignored evidence under `artifacts/sculpture/`. To repeat the SQL check
inside the workshop Codespace after its database has loaded:

```bash
PGPASSWORD=postgres psql -h postgres -U postgres -d postgres \
  -v ON_ERROR_STOP=1 -f artifacts/sculpture/comparison.sql
```

Expected database results: `approved_sculpture_count = 296` and
`proposed_sculpture_count = 151`. The fixture contains no expected answer count.
The generated queries use `COUNT(DISTINCT object_id)` and explicit `IN` lists;
neither query changes database data or schema.

The category list is a policy change. When this implementation is proposed against
a branch with the earlier MAP, the base-branch checker intentionally reports
`policy.change` for the changed MAP, validator, and renderer. Maintainer review is
needed to adopt the new policy; the guard has not been bypassed. A child PR based
on this policy can then isolate a violation of `sculpture_categories` itself.
