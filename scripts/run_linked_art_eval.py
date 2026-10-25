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
from sql_eval.common import read_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error('Use a new output directory; preserve earlier evidence.')
    fixtures = ROOT / 'eval/linked-art-comparison'
    shared = [(fixtures / name, '/app/eval/' + name, True)
              for name in ('questions.json', 'question-set.json')]
    gold = (fixtures / 'gold/answers.json', '/app/eval/gold/answers.json', True)
    container_run('eval-scorer', [*shared, gold], '--verify-gold')
    out.mkdir(parents=True)
    budget = out / 'budget.json'
    shutil.copyfile(ROOT / 'eval/rehearsal-budget.json', budget)
    for condition in ('local', 'linked-art'):
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
    linked = read_json(out / 'linked-art-reports/report.json')
    comparison = compare_pair(local, linked)
    comparison['conditions'] = {'current': 'local', 'semantic': 'linked-art'}
    comparison['sections'] = {}
    for section, prefix in [('original', 'q'), ('sculpture', 's')]:
        comparison['sections'][section] = {
            name: {'correct': sum(q['correct'] for q in r['questions'] if q['id'].startswith(prefix)),
                   'total': sum(q['id'].startswith(prefix) for q in r['questions'])}
            for name, r in [('local', local), ('linked-art', linked)]}
    write_json(out / 'comparison.json', comparison)
    print(comparison, flush=True)


if __name__ == '__main__':
    main()
