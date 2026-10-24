#!/usr/bin/env python3
"""Export and validate a small Linked Art mapping using pinned, offline resources."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from pyld import jsonld

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = 'data_contract_components/contract_definition/object_images_contract_spec.json'
SOURCE = 'data_contract_components/data_assets/db_migrations/raw_data/objects.json'
PROFILE_ID = 'museum-linked-art-sculpture-map'
CONTEXT = 'https://linked.art/ns/v1/linked-art.json'
CRM = 'http://www.cidoc-crm.org/cidoc-crm/'
P2 = CRM + 'P2_has_type'
E22 = CRM + 'E22_Human-Made_Object'
SCULPTURE = 'http://vocab.getty.edu/aat/300047090'
ARTWORK = 'http://vocab.getty.edu/aat/300133025'
WORK_TYPE = 'http://vocab.getty.edu/aat/300435443'
COLLECTION_ITEM = 'http://vocab.getty.edu/aat/300404024'
PRIMARY_NAME = 'http://vocab.getty.edu/aat/300404670'
PROTECTED_FILES = (
    'scripts/linked_art_sculpture.py', 'requirements-linked-art.txt',
    'vendor/linked-art/object.json', 'vendor/linked-art/core.json',
    'vendor/linked-art/linked-art.json', 'vendor/linked-art/manifest.json',
)


def read(path):
    return json.loads(path.read_text())


@lru_cache(maxsize=4)
def compile_resources(object_bytes, core_bytes, context_bytes):
    schemas = [json.loads(object_bytes), json.loads(core_bytes)]
    registry = Registry().with_resources(
        (s['$id'], Resource.from_contents(s)) for s in schemas)
    validator = Draft202012Validator(schemas[0], registry=registry, format_checker=FormatChecker())
    context = json.loads(context_bytes)

    def offline_loader(url, options=None):
        if url != CONTEXT:
            raise ValueError('Unapproved remote JSON-LD context: ' + url)
        return {'contextUrl': None, 'documentUrl': url, 'document': context}

    return validator, offline_loader


def resources(root):
    folder = root / 'vendor/linked-art'
    manifest = read(folder / 'manifest.json')
    if set(manifest['files']) != {'object.json', 'core.json', 'linked-art.json', 'LICENSE'}:
        raise ValueError('The complete pinned Linked Art snapshot is required.')
    for filename, details in manifest['files'].items():
        if filename not in ('object.json', 'core.json', 'linked-art.json', 'LICENSE'):
            raise ValueError('Unexpected upstream resource: ' + filename)
        if hashlib.sha256((folder / filename).read_bytes()).hexdigest() != details['sha256']:
            raise ValueError('Pinned Linked Art resource changed: ' + filename)
    return compile_resources(*[(folder / p).read_bytes()
                               for p in ('object.json', 'core.json', 'linked-art.json')])


def type_ref(identifier, label):
    return {'id': identifier, 'type': 'Type', '_label': label}


def export_records(source, prompt):
    settings = prompt['semantics']
    labels = settings['sculpture_categories']
    if (not isinstance(labels, list) or not labels
            or not all(isinstance(v, str) and v.strip() for v in labels)
            or len(labels) != len(set(labels))):
        raise ValueError('Sculpture categories must be distinct nonempty strings.')
    ids = [r['objectID'] for r in source]
    if len(set(ids)) != len(ids):
        raise ValueError('Source object IDs must be unique.')
    result = []
    for row in source:
        label = (row.get('classification') or '').strip(' ')
        if label not in labels:
            continue
        title = row.get('title') or f"Museum object {row['objectID']}"
        work_type = type_ref(settings['linked_art_sculpture_type'], 'Sculpture')
        work_type['classified_as'] = [type_ref(WORK_TYPE, 'Type of Work')]
        result.append({
            '@context': CONTEXT,
            # Reserved example.org IDs identify workshop entities, not Met web pages.
            'id': f"https://example.org/semantic-contracts/object/{row['objectID']}",
            'type': settings['linked_art_entity_type'],
            '_label': title,
            'identified_by': [{'type': 'Name', 'content': title,
                               'classified_as': [type_ref(PRIMARY_NAME, 'Primary Name')]}],
            'classified_as': [work_type, type_ref(COLLECTION_ITEM, 'Collection Item')],
            'referred_to_by': [{'type': 'LinguisticObject', 'content':
                f"Local workshop mapping from Met objectID {row['objectID']}, classification {label!r}. "
                'This is a proposed workshop assertion, not a Met-authored Linked Art record.'}],
        })
    return result


def validate_records(records, root):
    validator, loader = resources(root)
    schema_errors = []
    invalid_count = 0
    for record in records:
        errors = list(validator.iter_errors(record))
        invalid_count += bool(errors)
        for error in errors:
            if len(schema_errors) < 10:
                schema_errors.append({'id': record.get('id'), 'path': list(error.absolute_path),
                                      'message': error.message})
    expanded = jsonld.expand(records, options={'documentLoader': loader})
    sculpture_ids = set()
    for node in expanded:
        if E22 in node.get('@type', []) and any(
            concept.get('@id') == SCULPTURE and any(t.get('@id') == WORK_TYPE
                for t in concept.get(P2, [])) for concept in node.get(P2, [])
        ):
            sculpture_ids.add(node['@id'])
    return {'schema_valid': invalid_count == 0, 'schema_invalid_records': invalid_count,
            'schema_errors': schema_errors, 'expanded_sculpture_count': len(sculpture_ids)}, expanded


def evaluate(policy_root, candidate_root, profile, prompt_path=None):
    source = read(policy_root / SOURCE)
    relative = prompt_path or profile['promptAssetResourceName']
    path = (candidate_root / relative).resolve()
    if not path.is_relative_to(candidate_root.resolve()):
        raise ValueError('Prompt must remain within the candidate checkout.')
    prompt = read(path)
    records = export_records(source, prompt)
    validation, expanded = validate_records(records, policy_root)
    expected_labels = next(e['required_value'] for e in profile['elements']
                           if e['id'] == 'sculpture_categories')
    expected_count = sum((r.get('classification') or '').strip(' ') in expected_labels for r in source)
    unknown = sum(not (r.get('classification') or '').strip(' ') for r in source)
    violations = []
    if not validation['schema_valid']:
        violations.append({'rule': 'linked_art.object_schema',
            'expected': 'Linked Art Human-Made Object schema', 'actual': validation['schema_errors'],
            'message': 'Generated records fail the pinned upstream object schema.'})
    if validation['expanded_sculpture_count'] != expected_count:
        violations.append({'rule': 'linked_art.sculpture_identity',
            'expected': {'entity': E22, 'classified_as': SCULPTURE, 'count': expected_count},
            'actual': {'entity': prompt['semantics']['linked_art_entity_type'],
                       'classified_as': prompt['semantics']['linked_art_sculpture_type'],
                       'count': validation['expanded_sculpture_count']},
            'message': 'The expanded graph must identify physical sculpture objects by class and URI. '
                       'Artwork is a separate classification; a display label of Sculpture cannot substitute for its URI.'})
    return {'status': 'fail' if violations else 'pass', 'asset': relative,
            'mapped_records': len(records), 'unclassified_unknown': unknown,
            'unmapped_classified_records': len(source) - unknown - expected_count,
            'expected_sculpture_count': expected_count, **validation, 'violations': violations}, records, expanded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt', default='eval/prompts/linked-art-sculpture.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'artifacts/linked-art-sculpture')
    args = parser.parse_args()
    profile = next(p for p in read(ROOT / CONTRACT)['metadataApplicationProfile']['additionalProfiles']
                   if p['id'] == PROFILE_ID)
    report, records, expanded = evaluate(ROOT, ROOT, profile, args.prompt)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, value in (('report.json', report), ('records.json', records), ('expanded.json', expanded)):
        (args.out / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
