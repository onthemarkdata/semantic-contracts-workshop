"""Verify category boundaries, the controlled comparison, and gold isolation."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.build_category_eval import build, generate, profiles, vocabulary, CONDITIONS, FIXTURES
from scripts.check_prompt_map import check
from scripts.run_category_eval import compare, main
from sql_eval.common import read_json, write_json
from sql_eval.prompts import render
from tests.test_prompt_map import candidate

ROOT = Path(__file__).resolve().parents[1]


class CategoryEvalTests(unittest.TestCase):
    def test_only_hard_questions_replaced_and_fixtures_reproduce(self):
        build(check=True)
        generated = generate()
        self.assertEqual(generated['questions.json'][:10], read_json(ROOT / 'eval/questions.json')[:10])
        self.assertEqual(generated['question-set.json'], [f'q{i:02}' for i in range(1, 21)])
        old = read_json(ROOT / 'eval/questions.json')
        self.assertTrue(all(new['question'] != prev['question'] for new, prev in
                            zip(generated['questions.json'][10:], old[10:])))
        self.assertEqual({q['category'] for q in generated['questions.json'][10:]},
                         {'Sculpture', 'Painting', 'Drawing', 'Print', 'Furniture', 'Architectural objects', 'Overlap'})

    def test_prompt_only_is_existing_general_prompt_and_linked_art_only_adds_references(self):
        fixtures = generate()
        baseline, mapped, linked = [fixtures[name + '.json'] for name in CONDITIONS]
        self.assertEqual(baseline, read_json(ROOT / 'eval/prompts/semantic.json'))
        self.assertEqual(baseline['semantics'], mapped['semantics'])
        self.assertEqual(mapped['semantics'], linked['semantics'])
        self.assertTrue(mapped['instructions'].startswith(baseline['instructions'] + '\n'))
        self.assertTrue(linked['instructions'].startswith(mapped['instructions'] + '\nLinked Art references'))
        local_profile, linked_profile = profiles()
        self.assertEqual(local_profile['categoryMapping'], linked_profile['categoryMapping'])
        for ref in linked_profile['linkedArtReferences'].values():
            self.assertIn(ref['uri'], render(linked))
            self.assertIn(ref['description'], render(linked))
            self.assertEqual(ref['description'], vocabulary()[ref['name']]['description'])
        self.assertNotIn('http://vocab.getty.edu', render(mapped))

    def test_label_boundaries_overlap_and_source_answers(self):
        local, _ = profiles()
        mapping = local['categoryMapping']
        self.assertNotIn('Sword Furniture-Tsuba', mapping['Furniture'])
        self.assertEqual(set(mapping['Sculpture']) & set(mapping['Architectural objects']),
                         {'Sculpture-Architectural', 'Sculpture-Architectural-Stone'})
        rows = read_json(ROOT / 'data_contract_components/data_assets/db_migrations/raw_data/objects.json')
        furniture = {r['objectID'] for r in rows if r.get('classification') in mapping['Furniture']}
        self.assertNotIn(24623, furniture)  # Sword guard.
        self.assertIn(314034, furniture)  # Wood-Furniture royal seat.
        self.assertIn(491666, furniture)  # Furniture-Wood chair.
        answers = generate()['gold/answers.json']['answers']
        self.assertEqual(answers['q15']['expected'], [[23]])
        self.assertEqual(answers['q17']['expected'], [[9]])
        self.assertEqual(answers['q18']['expected'], [[300]])

    def test_prompt_change_violates_contract(self):
        asset = FIXTURES + '/prompt-map.json'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate(root)
            prompt = read_json(root / asset)
            prompt['instructions'] = prompt['instructions'].replace('"Wood-Furniture", ', '')
            write_json(root / asset, prompt)
            report = check(ROOT, root)
            self.assertEqual([(v['asset'], v['rule']) for v in report['violations']],
                             [(asset, 'prompt.instructions')])

    def test_three_conditions_use_same_questions_budget_and_no_agent_gold_mount(self):
        calls = []
        prompts = []
        budgets = []
        ids = [f'q{i:02}' for i in range(1, 21)]
        def container(service, mounts, *args):
            calls.append(service)
            paths = {dest: src for src, dest, readonly in mounts}
            self.assertEqual(read_json(paths['/app/eval/question-set.json']), ids)
            if service == 'eval-agent':
                self.assertFalse(any('gold' in str(src) or 'gold' in dest for src, dest, readonly in mounts))
                prompts.append(read_json(paths['/prompt.json']))
                budgets.append(read_json(paths['/budget.json']))
            elif '--run' in args:
                write_json(paths['/reports'] / 'report.json', {
                    'controls': {'question_ids': ids}, 'questions': [
                        {'id': qid, 'correct': True} for qid in ids],
                    'correct': 20, 'total': 20, 'elapsed_seconds': 1})
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'run'
            with patch('sys.argv', ['run', '--out', str(out)]), patch(
                    'scripts.run_category_eval.container_run', side_effect=container):
                main()
            self.assertEqual(read_json(out / 'comparison.json')['order'], list(CONDITIONS))
        self.assertEqual(calls, ['eval-scorer'] + ['eval-agent', 'eval-scorer'] * 3)
        self.assertEqual(prompts, [read_json(ROOT / FIXTURES / (name + '.json')) for name in CONDITIONS])
        self.assertTrue(all(budget == budgets[0] for budget in budgets))

    def test_comparison_rejects_changed_controls(self):
        report = {'controls': {'seed': 1}, 'questions': [
            {'id': f'q{i:02}', 'correct': True} for i in range(1, 21)],
            'correct': 20, 'total': 20, 'elapsed_seconds': 1}
        reports = {name: deepcopy(report) for name in CONDITIONS}
        reports[CONDITIONS[2]]['controls']['seed'] = 2
        with self.assertRaisesRegex(ValueError, 'controls differ'):
            compare(reports)
