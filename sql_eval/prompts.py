"""Render explicit semantic choices and check the protected prompt."""

import json

RULES = {
    "linked_art_entity_type": {
        "HumanMadeObject": "Represent each selected sculpture object with Linked Art type HumanMadeObject. Physical objects, digital files, and visual content have distinct identities; do not count images or VisualItems as extra physical objects.",
        "DigitalObject": "Represent the selected records as Linked Art DigitalObject entities."
    },
    "linked_art_sculpture_type": {
        "http://vocab.getty.edu/aat/300047090": "Use the full Sculpture URI http://vocab.getty.edu/aat/300047090 in classified_as, with Type of Work http://vocab.getty.edu/aat/300435443 as its classification. Collection Item and Artwork are separate concepts. Do not infer Artwork merely from collection membership or substitute its URI for Sculpture.",
        "http://vocab.getty.edu/aat/300133025": "Use the Artwork URI http://vocab.getty.edu/aat/300133025 in place of the Sculpture URI in classified_as."
    },
    "sculpture_categories": {"explicit_list": "For this workshop, a sculpture is one museum object record whose object_physical_properties.classification, after trimming surrounding spaces, exactly matches a listed category. Count each object_id once. Use the complete explicit list below; do not replace it with classification = 'Sculpture', a substring search, or a guess from material, title, or object name. NULL, empty, and space-only classifications are unknown and excluded from the count; exclusion does not establish that an object is not a sculpture. Listed categories:"},
    "missing_text": {
        "null_or_blank": "Treat NULL and empty or whitespace-only text as missing. For populated text, use NULLIF(BTRIM(column), '') IS NOT NULL.",
        "null_only": "For simpler filters, treat only NULL as missing. Use IS NOT NULL to count populated text, including blank strings.",
    },
    "object_key": {"object_id": "Join museum tables on object_id. Count artworks at the object_id grain; do not multiply counts through expansions."},
    "public_domain": {"explicit_true": "Public domain means is_public_domain IS TRUE. An image URL alone does not establish public-domain status."},
    "ordering": {"question": "Return only requested columns in their requested order. Follow requested sorting and tie breakers; do not add a LIMIT unless requested."},
    "sample_scope": {"object_records": "In this exercise, artwork means one museum object record identified by object.object_id. This is a local counting convention, not evidence that every collection item is classified as an artwork in Linked Art. Do not count images, tags, or conceptual works as extra objects."},
    "field_meaning": {"museum_columns": "Artist name is object.artist_display_name; title is object.title; department is object_gallery_info.department; culture is object_history.culture; classification and medium are in object_physical_properties; primary image URL is object_images.primary_image; public-domain status is object_copyright.is_public_domain. Use the stated field, not a related label or proxy."},
    "aggregation": {"requested_grain": "For populated text use NULLIF(BTRIM(column), '') IS NOT NULL; for missing text use NULLIF(BTRIM(column), '') IS NULL. Combine conditions with AND or OR exactly as asked. For object counts count object IDs, not distinct field values. For distinct values use DISTINCT; for counts per category GROUP BY that category. Join only the tables needed, using qualified object_id columns. Preserve the requested row grain and avoid extra columns."},
    "answer_values": {"query_rows": "The query tool returns columns and rows. Submit only its complete rows array as the final rows value, preserving numbers, strings, NULLs, duplicates, and row order. Do not return SQL, column names, explanations, or numbers remembered from other questions."},
}


def render(prompt):
    parts = [prompt["instructions"]]
    for key, value in prompt.get("semantics", {}).items():
        if key == 'sculpture_categories':
            if (not isinstance(value, list) or not value
                    or not all(isinstance(v, str) and v.strip() for v in value)
                    or len(value) != len(set(value))):
                raise ValueError('Sculpture categories must be distinct, nonempty strings.')
            parts.append(RULES[key]['explicit_list'] + '\n' + json.dumps(value, ensure_ascii=False))
            continue
        try:
            parts.append(RULES[key][value])
        except KeyError:
            raise ValueError(f"Unknown semantic setting: {key}={value}") from None
    return "\n".join(parts)


def protect(prompt, contract):
    errors = [key for key, value in contract["required_semantics"].items()
              if prompt.get("semantics", {}).get(key) != value]
    if prompt["instructions"] != contract["approved_instructions"]:
        errors.append("instructions changed; review and update the approved text")
    if set(prompt.get("semantics", {})) != set(contract["required_semantics"]):
        errors.append("semantic rule set changed")
    if errors:
        raise ValueError("Prompt contract failed: " + "; ".join(errors))
    render(prompt)
    return {"status": "pass"}
