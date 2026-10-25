#!/usr/bin/env python3
"""Build the Met category comparison from the contract and independent source rows."""
from collections import Counter
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
        questions.append(dict(id=qid, difficulty='hard', category=category,
                              question=question, ordered=ordered))
        gold['answers'][qid] = dict(sql=sql, expected=expected)
    add(11, 'Sculpture', 'How many sculptures have a trimmed classification other than the exact label Sculpture? Return one count.',
        f"SELECT COUNT(DISTINCT p.object_id) FROM {table} WHERE {p['Sculpture']} AND BTRIM(p.classification) <> 'Sculpture'",
        [[sum(label(r) != 'Sculpture' for r in selected['Sculpture'])]])
    add(12, 'Painting', 'How many paintings are explicitly marked public domain? Return one count.',
        f"SELECT COUNT(DISTINCT p.object_id) FROM {table} JOIN object_copyright c USING (object_id) WHERE {p['Painting']} AND c.is_public_domain IS TRUE",
        [[sum(r.get('isPublicDomain') is True for r in selected['Painting'])]])
    add(13, 'Drawing', 'For each department with drawings, return department and drawing count, sorted by department ascending.',
        f"SELECT g.department, COUNT(DISTINCT p.object_id) FROM {table} JOIN object_gallery_info g USING (object_id) WHERE {p['Drawing']} GROUP BY g.department ORDER BY g.department",
        [list(x) for x in sorted(Counter(r['department'] for r in selected['Drawing']).items())], True)
    add(14, 'Print', 'How many prints are explicitly marked public domain and have a populated primary image URL? NULL, empty, and whitespace-only URLs are missing. Return one count.',
        f"SELECT COUNT(DISTINCT p.object_id) FROM {table} JOIN object_copyright c USING (object_id) JOIN object_images i USING (object_id) WHERE {p['Print']} AND c.is_public_domain IS TRUE AND NULLIF(BTRIM(i.primary_image), '') IS NOT NULL",
        [[sum(r.get('isPublicDomain') is True and bool((r.get('primaryImage') or '').strip(' ')) for r in selected['Print'])]])
    add(15, 'Furniture', 'How many furniture objects are in the sample? Return one count.',
        f"SELECT COUNT(DISTINCT p.object_id) FROM {table} WHERE {p['Furniture']}", [[len(selected['Furniture'])]])
    add(16, 'Architectural objects', 'How many architectural objects are in the sample? Return one count.',
        f"SELECT COUNT(DISTINCT p.object_id) FROM {table} WHERE {p['Architectural objects']}", [[len(selected['Architectural objects'])]])
    sculpture_ids = {r['objectID'] for r in selected['Sculpture']}
    architecture_ids = {r['objectID'] for r in selected['Architectural objects']}
    add(17, 'Overlap', 'How many objects belong to BOTH sculpture and architectural objects? Count each object once. Return one count.',
        f"SELECT COUNT(DISTINCT p.object_id) FROM {table} WHERE {p['Sculpture']} AND {p['Architectural objects']}",
        [[len(sculpture_ids & architecture_ids)]])
    add(18, 'Overlap', 'How many objects belong to EITHER sculpture OR architectural objects, including those in both categories? Count each object once. Return one count.',
        f"SELECT COUNT(DISTINCT p.object_id) FROM {table} WHERE {p['Sculpture']} OR {p['Architectural objects']}",
        [[len(sculpture_ids | architecture_ids)]])
    add(19, 'Painting', 'How many paintings have a trimmed classification other than the exact label Paintings? Return one count.',
        f"SELECT COUNT(DISTINCT p.object_id) FROM {table} WHERE {p['Painting']} AND BTRIM(p.classification) <> 'Paintings'",
        [[sum(label(r) != 'Paintings' for r in selected['Painting'])]])
    add(20, 'Furniture', 'Return object ID, title, and classification for the five furniture objects with the smallest object IDs, sorted by ID ascending.',
        f"SELECT p.object_id, o.title, p.classification FROM {table} JOIN object o USING (object_id) WHERE {p['Furniture']} ORDER BY p.object_id LIMIT 5",
        [[r['objectID'], r.get('title'), r.get('classification')] for r in sorted(selected['Furniture'], key=lambda r: r['objectID'])[:5]], True)
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
