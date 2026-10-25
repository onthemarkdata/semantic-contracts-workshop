"""Protect the controlled comparison and its gold isolation."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.build_linked_art_eval import build
from scripts.run_linked_art_eval import main
from sql_eval.common import read_json, write_json
from sql_eval.prompts import render

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'eval/linked-art-comparison'


class LinkedArtEvalTests(unittest.TestCase):
    def test_only_linked_art_guidance_changes(self):
        local = read_json(FIXTURES / 'local.json')
        linked = read_json(FIXTURES / 'linked-art.json')
        extra = {'linked_art_entity_type', 'linked_art_sculpture_type'}
        self.assertEqual(set(linked['semantics']) - set(local['semantics']), extra)
        trimmed = copy.deepcopy(linked)
        for key in extra:
            del trimmed['semantics'][key]
        self.assertEqual(local, trimmed)
        self.assertTrue(render(linked).startswith(render(local) + '\n'))

    def test_fixtures_reproduce_and_preserve_original_questions_and_gold(self):
        before = {p: p.read_bytes() for p in FIXTURES.rglob('*.json')}
        build()
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertEqual(read_json(FIXTURES / 'questions.json')[:20],
                         read_json(ROOT / 'eval/questions.json'))
        gold = read_json(FIXTURES / 'gold/answers.json')['answers']
        original = read_json(ROOT / 'eval/gold/answers.json')['answers']
        self.assertEqual({k: gold[k] for k in original}, original)

    def test_runner_never_mounts_gold_into_agent(self):
        seen = []
        def container(service, mounts, *args):
            seen.append((service, mounts))
            if service == 'eval-agent':
                self.assertFalse(any('gold' in str(src) or 'gold' in dest
                                     for src, dest, readonly in mounts))
                self.assertTrue(all(readonly for src, dest, readonly in mounts if dest != '/out'))
            if service == 'eval-scorer' and '--run' in args:
                report = next(src for src, dest, readonly in mounts if dest == '/reports')
                write_json(report / 'report.json', {
                    'controls': {'question_ids': ['q01', 's01']},
                    'questions': [{'id': 'q01', 'correct': True}, {'id': 's01', 'correct': False}],
                    'correct': 1, 'total': 2, 'elapsed_seconds': 1})
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'run'
            with patch('sys.argv', ['run', '--out', str(out)]), patch(
                    'scripts.run_linked_art_eval.container_run', side_effect=container):
                main()
            result = read_json(out / 'comparison.json')
            self.assertEqual(result['sections']['sculpture']['local']['correct'], 0)
        self.assertEqual([s for s, m in seen],
                         ['eval-scorer', 'eval-agent', 'eval-scorer', 'eval-agent', 'eval-scorer'])
