# Pinned Linked Art resources

These files are unmodified copies from [Linked Art](https://linked.art/), maintained
in [linked-art/linked.art](https://github.com/linked-art/linked.art), revision
`bcbff1761e65f44eeaeb92b4b2b83da2783539f8`.

| Local file | Upstream file |
| --- | --- |
| `object.json` | `docs/api/1.0/schema/object.json` |
| `core.json` | `docs/api/1.0/schema/core.json` |
| `linked-art.json` | `docs/ns/v1/linked-art.json` |
| `LICENSE` | `LICENSE` |

[manifest.json](manifest.json) records the immutable source URLs and SHA-256
checksums. Runtime validation verifies the checksums, resolves schema references
from this directory, and loads only the approved JSON-LD context from disk. It
cannot fetch an unapproved context. No Linked Art or Getty network service is
needed during the exercise.

The upstream content is licensed under **CC BY 4.0**; see [LICENSE](LICENSE).
Credit belongs to the Linked Art community. No modifications have been made to
these copied resources, and their inclusion does not imply endorsement of this
workshop or its local classification mappings.

The workshop uses these upstream resources with `jsonschema` and `PyLD`. It checks
the generated subset against the Human-Made Object schema and expands the JSON-LD
before checking physical sculpture identities. Schema validity is not proof of
complete Linked Art conformance or of the curatorial correctness of a mapping.
