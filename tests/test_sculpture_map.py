"""Verify category membership, policy protection, and the counting consequence."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.check_prompt_map import CONTRACT, check
from scripts.compare_sculpture_scope import compare, count_sql
from sql_eval.prompts import render
from tests.test_prompt_map import candidate, write

ROOT = Path(__file__).resolve().parents[1]
PROMPT = 'eval/prompts/sculpture.json'


class SculptureMapTests(unittest.TestCase):
    def test_both_prompt_assets_are_checked(self):
        result = check(ROOT, ROOT)
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['checked_assets'], ['eval/prompts/semantic.json', PROMPT])

    def test_narrowed_membership_fails_with_excluded_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate(root)
            prompt = json.loads((ROOT / 'eval/prompts/sculpture-violation.json').read_text())
            write(root / PROMPT, prompt)
            result = check(ROOT, root)
            self.assertEqual([v['rule'] for v in result['violations']], ['sculpture_categories'])
            violation = result['violations'][0]
            self.assertEqual(violation['actual'], ['Sculpture'])
            self.assertEqual(len(violation['expected']), 17)
            self.assertIn('Missing approved categories:', violation['message'])
            self.assertIn('Stone Sculpture', violation['message'])
            self.assertEqual(violation['asset'], PROMPT)

    def test_reordering_members_is_allowed_but_duplicates_new_labels_and_wrong_types_fail(self):
        original = json.loads((ROOT / PROMPT).read_text())
        for name, change, expected in (
            ('reorder', lambda x: list(reversed(x)), 'pass'),
            ('duplicate', lambda x: x + ['Sculpture'], 'fail'),
            ('add', lambda x: x + ['Bronzes'], 'fail'),
            ('empty', lambda x: [], 'fail'),
            ('string', lambda x: 'Sculpture', 'fail'),
            ('nested', lambda x: [['Sculpture']], 'fail'),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                candidate(root)
                prompt = copy.deepcopy(original)
                prompt['semantics']['sculpture_categories'] = change(prompt['semantics']['sculpture_categories'])
                write(root / PROMPT, prompt)
                self.assertEqual(check(ROOT, root)['status'], expected)

    def test_changing_prompt_and_category_policy_together_cannot_bypass_base(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate(root)
            prompt = json.loads((root / PROMPT).read_text())
            prompt['semantics']['sculpture_categories'] = ['Sculpture']
            write(root / PROMPT, prompt)
            contract = json.loads((root / CONTRACT).read_text())
            contract['metadataApplicationProfile']['additionalProfiles'][0]['elements'][0]['required_value'] = ['Sculpture']
            write(root / CONTRACT, contract)
            rules = [v['rule'] for v in check(ROOT, root)['violations']]
            self.assertIn('sculpture_categories', rules)
            self.assertIn('policy.change', rules)

    def test_missing_asset_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate(root)
            (root / PROMPT).unlink()
            report = root / 'report.json'
            result = subprocess.run(['python3', str(ROOT / 'scripts/check_prompt_map.py'),
                                     '--policy-root', str(ROOT), '--candidate-root', str(root),
                                     '--report', str(report), '--markdown', str(root / 'report.md')],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(report.read_text())['violations'][0]['rule'], 'input.invalid')

    def test_rendered_instructions_follow_the_proposed_list(self):
        good = render(json.loads((ROOT / PROMPT).read_text()))
        bad = render(json.loads((ROOT / 'eval/prompts/sculpture-violation.json').read_text()))
        self.assertIn('"Stone Sculpture"', good)
        self.assertTrue(bad.endswith('["Sculpture"]'))
        self.assertNotIn('"Stone Sculpture"', bad)

    def test_counts_use_explicit_membership_and_preserve_unknowns(self):
        labels = ['Sculpture', ' Stone Sculpture ', 'Bronzes', '', None, 'Sculpture-New']
        records = [{'objectID': i, 'classification': label, 'objectName': 'Sculpture'}
                   for i, label in enumerate(labels)]
        result = compare(records, ['Sculpture', 'Stone Sculpture'], ['Sculpture'])
        self.assertEqual(result['approved']['count'], 2)
        self.assertEqual(result['proposed']['count'], 1)
        self.assertEqual(result['unclassified_unknown'], 2)
        self.assertEqual(result['excluded_approved_categories'], {'Stone Sculpture': 1})
        with self.assertRaises(ValueError):
            compare(records + [records[0]], ['Sculpture'], ['Sculpture'])

    def test_sql_counts_object_ids_and_escapes_labels(self):
        sql = count_sql(["Sculpture's example"], 'sculpture_count')
        self.assertIn('COUNT(DISTINCT object_id)', sql)
        self.assertIn('BTRIM(classification) IN', sql)
        self.assertIn("'Sculpture''s example'", sql)
        self.assertNotIn('LIKE', sql)
