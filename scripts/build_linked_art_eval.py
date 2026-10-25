#!/usr/bin/env python3
"""Freeze a paired SQL diagnostic without changing the original question bank."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sql_eval.common import read_json, write_json


def build():
    out = ROOT / 'eval/linked-art-comparison'
    local = read_json(ROOT / 'eval/prompts/semantic.json')
    mapping = read_json(ROOT / 'eval/prompts/sculpture.json')['semantics']['sculpture_categories']
    local['semantics']['sculpture_categories'] = mapping
    linked = deepcopy(local)
    linked['semantics'].update({k: v for k, v in read_json(
        ROOT / 'eval/prompts/linked-art-sculpture.json')['semantics'].items()
        if k.startswith('linked_art_')})
    write_json(out / 'local.json', local)
    write_json(out / 'linked-art.json', linked)
    source = read_json(ROOT / 'data_contract_components/data_assets/db_migrations/raw_data/objects.json')
    label = lambda row: (row.get('classification') or '').strip(' ')
    selected = [r for r in source if label(r) in mapping]
    literal = ', '.join("'" + v.replace("'", "''") + "'" for v in mapping)
    condition = f'BTRIM(p.classification) IN ({literal})'
    table = 'object_physical_properties p'
    cases = [
        ('s01', 'How many sculptures are in the sample under the supplied category mapping? Return one count.',
         False, f'SELECT COUNT(DISTINCT p.object_id) FROM {table} WHERE {condition}', [[len(selected)]]),
        ('s02', 'For each department with mapped sculptures, return department and sculpture count, sorted by department ascending.',
         True, f'SELECT g.department, COUNT(DISTINCT p.object_id) FROM {table} JOIN object_gallery_info g USING (object_id) WHERE {condition} GROUP BY g.department ORDER BY g.department',
         [list(x) for x in sorted(Counter(r['department'] for r in selected).items())]),
        ('s03', 'How many mapped sculptures are explicitly marked public domain? Return one count.',
         False, f'SELECT COUNT(DISTINCT p.object_id) FROM {table} JOIN object_copyright c USING (object_id) WHERE {condition} AND c.is_public_domain IS TRUE',
         [[sum(r['isPublicDomain'] is True for r in selected)]]),
        ('s04', "How many mapped sculptures have a trimmed classification other than the exact label Sculpture? Return one count.",
         False, f"SELECT COUNT(DISTINCT p.object_id) FROM {table} WHERE {condition} AND BTRIM(p.classification) <> 'Sculpture'",
         [[sum(label(r) != 'Sculpture' for r in selected)]]),
        ('s05', 'How many sample objects have unknown sculpture membership because classification is NULL, empty, or whitespace-only? Return one count.',
         False, f"SELECT COUNT(DISTINCT p.object_id) FROM {table} WHERE NULLIF(BTRIM(p.classification), '') IS NULL",
         [[sum(not label(r) for r in source)]]),
        ('s06', 'How many sample objects have a populated classification outside the supplied sculpture mapping? Count these as unmapped, without asserting that they are not sculptures. Return one count.',
         False, f"SELECT COUNT(DISTINCT p.object_id) FROM {table} WHERE NULLIF(BTRIM(p.classification), '') IS NOT NULL AND NOT ({condition})",
         [[sum(bool(label(r)) and label(r) not in mapping for r in source)]]),
    ]
    questions = read_json(ROOT / 'eval/questions.json')
    gold = read_json(ROOT / 'eval/gold/answers.json')
    for qid, question, ordered, sql, expected in cases:
        questions.append(dict(id=qid, question=question, ordered=ordered, difficulty='sculpture'))
        gold['answers'][qid] = dict(sql=sql, expected=expected)
    write_json(out / 'questions.json', questions)
    write_json(out / 'question-set.json', [q['id'] for q in questions])
    write_json(out / 'gold/answers.json', gold)


if __name__ == '__main__':
    build()
