#!/usr/bin/env python3
"""Measure the effect of explicit category membership, without model inference."""
import argparse
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = 'data_contract_components/contract_definition/object_images_contract_spec.json'
SOURCE = 'data_contract_components/data_assets/db_migrations/raw_data/objects.json'


def categories(value):
    if (not isinstance(value, list) or not value
            or not all(isinstance(v, str) and v.strip() for v in value)
            or len(value) != len(set(value))):
        raise ValueError('Categories must be distinct, nonempty strings.')
    return set(value)


def compare(records, approved, proposed):
    approved_set, proposed_set = categories(approved), categories(proposed)
    ids = [r['objectID'] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError('Source records must have unique object IDs.')
    # PostgreSQL BTRIM(text) removes surrounding spaces, not arbitrary whitespace.
    counts = Counter((r.get('classification') or '').strip(' ') for r in records)
    approved_count = sum(counts[label] for label in approved_set)
    proposed_count = sum(counts[label] for label in proposed_set)
    return {
        'question': 'How many sculptures are in our sample?',
        'measurement': 'Deterministic category counts; no model evaluation or accuracy score.',
        'source': SOURCE,
        'records': len(records),
        'unclassified_unknown': counts[''],
        'approved': {'categories': sorted(approved_set), 'count': approved_count},
        'proposed': {'categories': sorted(proposed_set), 'count': proposed_count},
        'delta': proposed_count - approved_count,
        'excluded_approved_categories': {
            label: counts[label] for label in sorted(approved_set - proposed_set)},
        'added_unapproved_categories': {
            label: counts[label] for label in sorted(proposed_set - approved_set)},
        'approved_category_counts': {label: counts[label] for label in sorted(approved_set)},
    }


def count_sql(labels, column):
    categories(labels)
    values = ',\n    '.join("'" + label.replace("'", "''") + "'" for label in sorted(labels))
    return (f'SELECT COUNT(DISTINCT object_id) AS {column}\n'
            'FROM object_physical_properties\n'
            f'WHERE BTRIM(classification) IN (\n    {values}\n);\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt', type=Path, default=ROOT / 'eval/prompts/sculpture.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'artifacts/sculpture/comparison.json')
    parser.add_argument('--sql', type=Path, default=ROOT / 'artifacts/sculpture/comparison.sql')
    args = parser.parse_args()
    contract = json.loads((ROOT / CONTRACT).read_text())
    profile = next(p for p in contract['metadataApplicationProfile']['additionalProfiles']
                   if p['id'] == 'museum-sculpture-category-map')
    approved = next(e['required_value'] for e in profile['elements']
                    if e['id'] == 'sculpture_categories')
    proposed = json.loads(args.prompt.read_text())['semantics']['sculpture_categories']
    report = compare(json.loads((ROOT / SOURCE).read_text()), approved, proposed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    args.sql.parent.mkdir(parents=True, exist_ok=True)
    args.sql.write_text(count_sql(approved, 'approved_sculpture_count') + '\n'
                        + count_sql(proposed, 'proposed_sculpture_count'))
    print(json.dumps(report, indent=2))
    print(f'Read-only SQL for the seeded database: {args.sql}')


if __name__ == '__main__':
    main()
