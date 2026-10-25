#!/usr/bin/env python3
"""Run one fixed pair; gold is mounted only into the separate scorer."""
import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.sql_eval import container_run
from scripts.compare_map_eval import compare_pair
from scripts.build_sculpture_prompt import from_local_docs
from sql_eval.common import read_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--candidate', choices=['linked-art', 'sculpture-only'], default='linked-art',
                        help='Compare the unchanged local prompt with this frozen variant.')
    parser.add_argument('--section', choices=['all', 'sculpture'], default='all')
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error('Use a new output directory; preserve earlier evidence.')
    fixtures = ROOT / 'eval/linked-art-comparison'
    if args.candidate == 'sculpture-only' and read_json(fixtures / 'sculpture-only.json') != from_local_docs():
        raise ValueError('The Sculpture prompt differs from the pinned local guidance; rebuild and review it.')
    out.mkdir(parents=True)
    inputs = fixtures
    gold_path = fixtures / 'gold/answers.json'
    if args.section == 'sculpture':
        inputs = out / 'inputs'
        questions = [q for q in read_json(fixtures / 'questions.json') if q['id'].startswith('s')]
        ids = [q['id'] for q in questions]
        gold = read_json(gold_path)
        write_json(inputs / 'questions.json', questions)
        write_json(inputs / 'question-set.json', ids)
        gold_path = inputs / 'gold.json'
        write_json(gold_path, {'answers': {qid: gold['answers'][qid] for qid in ids}})
    shared = [(inputs / name, '/app/eval/' + name, True)
              for name in ('questions.json', 'question-set.json')]
    gold = (gold_path, '/app/eval/gold/answers.json', True)
    container_run('eval-scorer', [*shared, gold], '--verify-gold')
    budget = out / 'budget.json'
    shutil.copyfile(ROOT / 'eval/rehearsal-budget.json', budget)
    for condition in ('local', args.candidate):
        run = out / condition
        report = out / (condition + '-reports')
        run.mkdir()
        report.mkdir()
        container_run('eval-agent', [*shared, (budget, '/budget.json', True),
                      (fixtures / (condition + '.json'), '/prompt.json', True),
                      (run, '/out', False)], '--stage', 'improved', '--prompt', '/prompt.json')
        container_run('eval-scorer', [*shared, gold, (run, '/run', True),
                      (report, '/reports', False)], '--run', '/run', '--out', '/reports/report.json')
    local = read_json(out / 'local-reports/report.json')
    linked = read_json(out / (args.candidate + '-reports/report.json'))
    comparison = compare_pair(local, linked)
    comparison['conditions'] = {'current': 'local', 'semantic': args.candidate}
    comparison['sections'] = {}
    for section, prefix in [('original', 'q'), ('sculpture', 's')]:
        if not any(q['id'].startswith(prefix) for q in local['questions']):
            continue
        comparison['sections'][section] = {
            name: {'correct': sum(q['correct'] for q in r['questions'] if q['id'].startswith(prefix)),
                   'total': sum(q['id'].startswith(prefix) for q in r['questions'])}
            for name, r in [('local', local), (args.candidate, linked)]}
    write_json(out / 'comparison.json', comparison)
    print(comparison, flush=True)


if __name__ == '__main__':
    main()
