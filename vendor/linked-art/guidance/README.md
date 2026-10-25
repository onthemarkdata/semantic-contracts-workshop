# Local Linked Art guidance

This directory vendors the unmodified Linked Art recommended-vocabulary page
and its CC BY 4.0 license from revision
`bcbff1761e65f44eeaeb92b4b2b83da2783539f8` of
[linked-art/linked.art](https://github.com/linked-art/linked.art).
The manifest records original paths, immutable source URLs, and SHA-256 checksums.
Credit: Linked Art contributors. No endorsement is implied.

This is the relevant documentation subset, not a checkout of the entire website.
The existing schema and JSON-LD context remain in the parent directory.
Relative links and `crom`/website formatting in upstream material are preserved;
this snapshot is reference Markdown, not a locally served website.

`scripts/build_sculpture_prompt.py` extracts only the Sculpture row under
**Object Types**, expands `aat:300047090` to its full URI, and embeds the entry
verbatim as label, URI, and description in the experimental prompt. Surrounding
instructions are workshop text. The source page is unmodified; the prompt is an
adaptation. The 17-category Met mapping is local policy, not supplied by Linked Art.

The eval agent cannot browse the web or read arbitrary files. The selected local
text is included in the prompt sent to the model. No website request or URI
resolution is needed, and the model is not merely given a file path to open.
