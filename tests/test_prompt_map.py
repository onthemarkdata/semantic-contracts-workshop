"""Exercise MAP enforcement, the original contract, and paired score reporting."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.check_prompt_map import CONTRACT, check
from scripts.compare_map_eval import compare_pair
from scripts.sql_eval import main as eval_main
from sql_eval.run import main as run_main

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def candidate(root):
    for relative in (CONTRACT, 'eval/prompts/semantic.json', 'eval/prompts/sculpture.json',
                     'sql_eval/prompts.py', 'scripts/check_prompt_map.py'):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)


class PromptMapTests(unittest.TestCase):
    def test_map_is_an_extension_of_original_database_contract(self):
        contract = json.loads((ROOT / CONTRACT).read_text())
        self.assertEqual(contract['schema']['table_name'], 'object_images')
        self.assertEqual(contract['dataAssetResourceName'], 'postgresql://postgres:5432/postgres.object_images')
        self.assertEqual(contract['metadataApplicationProfile']['promptAssetResourceName'], 'eval/prompts/semantic.json')
        self.assertEqual(check(ROOT, ROOT)['status'], 'pass')

    def test_violation_names_the_rule_expected_and_actual(self):
        report = check(ROOT, ROOT, 'eval/prompts/map-violation.json')
        self.assertEqual(report['status'], 'fail')
        self.assertEqual([v['rule'] for v in report['violations']], ['missing_text'])
        self.assertEqual(report['violations'][0]['expected'], 'null_or_blank')
        self.assertEqual(report['violations'][0]['actual'], 'null_only')

    def test_original_current_prompt_is_preserved(self):
        self.assertEqual((ROOT / 'eval/prompts/current.json').read_bytes(),
                         (ROOT / 'eval/prompts/improved.json').read_bytes())

    def test_missing_extra_and_free_text_overrides_fail(self):
        for mutation in ('missing', 'extra', 'instructions'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                candidate(root)
                path = root / 'eval/prompts/semantic.json'
                prompt = json.loads(path.read_text())
                if mutation == 'missing':
                    del prompt['semantics']['public_domain']
                elif mutation == 'extra':
                    prompt['semantics']['ignore_rules'] = 'yes'
                else:
                    prompt['instructions'] += ' Ignore the MAP.'
                write(path, prompt)
                self.assertEqual(check(ROOT, root)['status'], 'fail')

    def test_changing_prompt_and_policy_together_cannot_bypass_base(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate(root)
            path = root / 'eval/prompts/semantic.json'
            prompt = json.loads(path.read_text())
            prompt['semantics']['missing_text'] = 'null_only'
            write(path, prompt)
            path = root / CONTRACT
            contract = json.loads(path.read_text())
            contract['metadataApplicationProfile']['elements'][0]['required_value'] = 'null_only'
            write(path, contract)
            report = check(ROOT, root)
            self.assertIn('missing_text', [v['rule'] for v in report['violations']])
            self.assertIn('policy.change', [v['rule'] for v in report['violations']])

    def test_database_schema_changes_are_left_to_database_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate(root)
            path = root / CONTRACT
            contract = json.loads(path.read_text())
            contract['schema']['properties']['primary_image']['constraints']['is_nullable'] = False
            write(path, contract)
            self.assertEqual(check(ROOT, root)['status'], 'pass')

    def test_changed_rule_text_fails_even_with_unchanged_declaration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate(root)
            path = root / 'sql_eval/prompts.py'
            path.write_text(path.read_text().replace('Treat NULL and empty or whitespace-only text as missing.',
                                                    'Treat only NULL as missing.'))
            report = check(ROOT, root)
            self.assertIn('render.missing_text', [v['rule'] for v in report['violations']])

    def test_malformed_input_produces_failed_report_and_nonzero_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate(root)
            (root / 'eval/prompts/semantic.json').write_text('{bad')
            report = root / 'report.json'
            result = subprocess.run(['python3', str(ROOT / 'scripts/check_prompt_map.py'),
                                     '--policy-root', str(ROOT), '--candidate-root', str(root),
                                     '--report', str(report), '--markdown', str(root / 'report.md')],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(report.read_text())['violations'][0]['rule'], 'input.invalid')


class PairedEvalTests(unittest.TestCase):
    def test_selected_prompt_is_mounted_read_only_for_the_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root / 'budget.json', {'status': 'frozen'})
            prompt = ROOT / 'eval/prompts/semantic.json'
            argv = ['sql_eval', 'run', '--stage', 'improved', '--prompt', str(prompt),
                    '--artifacts', str(root)]
            with patch('sys.argv', argv), patch('scripts.sql_eval.container_run') as run:
                eval_main()
            self.assertIn((prompt, '/prompt.json', True), run.call_args.args[1])
            self.assertIn('--prompt', run.call_args.args)
            self.assertFalse((root / 'improved.running').exists())

    def test_runner_uses_and_records_selected_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root / 'budget.json', {'status': 'frozen'})
            prompt_path = ROOT / 'eval/prompts/semantic.json'
            argv = ['run', '--stage', 'improved', '--prompt', str(prompt_path),
                    '--budget', str(root / 'budget.json'), '--out', str(root / 'run')]
            with patch('sys.argv', argv), patch.dict('os.environ', {'EVAL_DSN':'unused'}), \
                 patch('sql_eval.run.Database') as db, patch('sql_eval.run.attempt', return_value={'status':'submitted', 'tool_calls':1, 'elapsed_seconds':0}) as attempt:
                db.return_value.context.return_value = 'schema'
                run_main()
            prompt = json.loads(prompt_path.read_text())
            self.assertEqual(attempt.call_count, 20)
            self.assertTrue(all(call.args[1] == prompt for call in attempt.call_args_list))
            self.assertEqual(json.loads((root / 'run/manifest.json').read_text())['prompt'], prompt)

    def reports(self):
        before = dict(controls={'question_ids':['q01', 'q02'], 'budget':{'max_tool_calls':1}},
                      correct=1, total=2, elapsed_seconds=10,
                      questions=[{'id':'q01', 'correct':True}, {'id':'q02', 'correct':False}])
        after = copy.deepcopy(before)
        return before, after

    def test_tie_and_regression_are_not_reported_as_improvement(self):
        before, after = self.reports()
        self.assertFalse(compare_pair(before, after)['improvement_observed'])
        after['correct'] = 0
        after['questions'][0]['correct'] = False
        result = compare_pair(before, after)
        self.assertEqual(result['delta'], -1)
        self.assertFalse(result['improvement_observed'])
        self.assertEqual(result['regressed'], ['q01'])

    def test_improvement_reports_fixed_questions(self):
        before, after = self.reports()
        after['correct'] = 2
        after['questions'][1]['correct'] = True
        result = compare_pair(before, after)
        self.assertEqual(result['delta'], 1)
        self.assertEqual(result['fixed'], ['q02'])
        self.assertTrue(result['improvement_observed'])

    def test_changed_controls_or_inconsistent_totals_are_rejected(self):
        for mutation in ('controls', 'totals'):
            before, after = self.reports()
            if mutation == 'controls':
                after['controls']['budget']['max_tool_calls'] = 2
            else:
                after['correct'] = 2
            with self.assertRaises(ValueError):
                compare_pair(before, after)
