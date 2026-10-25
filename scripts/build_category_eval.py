#!/usr/bin/env python3
"""Build the Met category comparison from the contract and independent source rows."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sql_eval.common import read_json, write_json

CONTRACT = 'data_contract_components/contract_definition/object_images_contract_spec.json'
FIXTURES = 'eval/category-comparison'
PROFILE = 'museum-met-categories-map'
CONDITIONS = ('prompt-only', 'prompt-map', 'prompt-map-linked-art')


def vocabulary(root=ROOT):
    folder = root / 'vendor/linked-art/guidance'
    manifest = read_json(folder / 'manifest.json')
    if set(manifest['files']) != {'recommended-vocabulary.md', 'LICENSE'}:
        raise ValueError('Pinned documentation and license are required.')
    for name, details in manifest['files'].items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != details['sha256']:
            raise ValueError('Pinned Linked Art documentation changed: ' + name)
    section = (folder / 'recommended-vocabulary.md').read_text().split(
        '### Object Types\n', 1)[1].split('\n### ', 1)[0]
    result = {}
    for line in section.splitlines():
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) == 3 and cells[1].startswith('aat:'):
                name, identifier, description = cells
                result[name] = {'uri': 'http://vocab.getty.edu/aat/' + identifier[4:],
                                'description': description}
    return result


def instructions(base, mapping, references=None):
    text = base + '\nLocal Met category MAP:\n'
    text += ('Each category selects object IDs whose classification, after PostgreSQL BTRIM, '
             'exactly matches any of its listed labels. Use the complete list, preserving spelling '
             'and word order. Do not substitute substring matching or guesses from title or medium. '
             'General artwork questions use all object records. NULL, empty and space-only '
             'classifications are unknown; other labels are unmapped, not proof of non-membership. '
             'Categories may overlap: BOTH means intersection; EITHER means union, counting each '
             'object ID once. An exclusion of an exact label still requires category membership.\n')
    for category, labels in mapping.items():
        text += category + ': ' + json.dumps(labels, ensure_ascii=False) + '\n'
    text += ('Sword Furniture-Tsuba is a sword fitting, excluded from Furniture. Architectural '
             'objects include the architectural sculpture labels and Wood-Architectural. '
             'Do not infer additional memberships from titles; these are workshop agreements, '
             'not exhaustive curatorial classifications.')
    if references is not None:
        text += '\nLinked Art references, embedded from the pinned local Object Types guidance:\n'
        for category, ref in references.items():
            text += f"{category} -> {ref['name']} ({ref['uri']}): {ref['description']}\n"
        text += ('These shared concepts identify the meanings behind the local mappings. '
                 'They do not change the membership lists or create database fields. '
                 'The mappings are local applications, not exact equivalence claims.')
    return text


def profiles(root=ROOT):
    all_profiles = read_json(root / CONTRACT)['metadataApplicationProfile']['additionalProfiles']
    return [next(p for p in all_profiles if p['id'] == name)
            for name in (PROFILE, PROFILE + '-linked-art')]


def generate(root=ROOT):
    local_profile, linked_profile = profiles(root)
    mapping = local_profile['categoryMapping']
    if linked_profile['categoryMapping'] != mapping:
        raise ValueError('The two MAP conditions must use identical membership.')
    base = read_json(root / 'eval/prompts/semantic.json')
    prompts = {CONDITIONS[0]: base}
    refs = linked_profile['linkedArtReferences']
    source_vocab = vocabulary(root)
    if set(refs) != set(mapping):
        raise ValueError('Every category needs a pinned Linked Art reference.')
    for ref in refs.values():
        if {k: ref[k] for k in ('uri', 'description')} != source_vocab[ref['name']]:
            raise ValueError('Linked Art reference differs from pinned guidance.')
    for condition, profile, reference in [(CONDITIONS[1], local_profile, None),
                                           (CONDITIONS[2], linked_profile, refs)]:
        prompt = deepcopy(base)
        prompt['instructions'] = instructions(base['instructions'], mapping, reference)
        if prompt['instructions'] != profile['approved_instructions']:
            raise ValueError('Generated prompt differs from approved MAP instructions.')
        prompts[condition] = prompt
    rows = read_json(root / 'data_contract_components/data_assets/db_migrations/raw_data/objects.json')
    if len({r['objectID'] for r in rows}) != len(rows):
        raise ValueError('Source object IDs must be unique.')
    label = lambda r: (r.get('classification') or '').strip(' ')
    selected = {name: [r for r in rows if label(r) in labels] for name, labels in mapping.items()}
    def predicate(name):
        literals = ', '.join("'" + x.replace("'", "''") + "'" for x in mapping[name])
        return f'BTRIM(p.classification) IN ({literals})'
    p = {name: predicate(name) for name in mapping}
    table = 'object_physical_properties p'
    questions = read_json(root / 'eval/questions.json')[:10]
    old_gold = read_json(root / 'eval/gold/answers.json')
    gold = {'sentinel': old_gold['sentinel'],
            'answers': {q['id']: old_gold['answers'][q['id']] for q in questions}}
    def add(number, category, question, sql, expected, ordered=False):
        qid = f'q{number:02}'
        questions.append(dict(id=qid, difficulty='medium', category=category,
                              question=question, ordered=ordered))
        gold['answers'][qid] = dict(sql=sql, expected=expected)
    categories = [('Sculpture', 'sculptures'), ('Painting', 'paintings'),
                  ('Drawing', 'drawings'), ('Print', 'prints'),
                  ('Furniture', 'furniture objects'), ('Architectural objects', 'architectural objects')]
    for number, (category, noun) in enumerate(categories, start=11):
        add(number, category,
            f'Using object_physical_properties.classification, how many {noun} are in the sample? Count each object_id once and return one count.',
            f'SELECT COUNT(DISTINCT p.object_id) FROM {table} WHERE {p[category]}',
            [[len(selected[category])]])
    for number, category, noun in [(17, 'Sculpture', 'sculptures'),
                                    (18, 'Architectural objects', 'architectural objects'),
                                    (19, 'Painting', 'paintings'),
                                    (20, 'Furniture', 'furniture objects')]:
        add(number, category,
            f'Using object_physical_properties.classification, return only the object IDs of the five {noun} with the smallest object IDs, sorted by object ID ascending.',
            f'SELECT DISTINCT p.object_id FROM {table} WHERE {p[category]} ORDER BY p.object_id LIMIT 5',
            [[r['objectID']] for r in sorted(selected[category], key=lambda r: r['objectID'])[:5]], True)
    return {'questions.json': questions, 'question-set.json': [q['id'] for q in questions],
            'gold/answers.json': gold, **{name + '.json': value for name, value in prompts.items()}}


def build(root=ROOT, check=False):
    for name, value in generate(root).items():
        target = root / FIXTURES / name
        if check:
            if read_json(target) != value:
                raise ValueError('Frozen fixture differs: ' + name)
        else:
            write_json(target, value)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(check=parser.parse_args().check)
