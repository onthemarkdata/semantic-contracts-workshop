"""Protect the controlled comparison and its gold isolation."""
import copy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts.build_linked_art_eval import build
from scripts.build_sculpture_prompt import from_local_docs
from scripts.run_linked_art_eval import main
from sql_eval.common import read_json, write_json
from sql_eval.prompts import render
from sql_eval.agent import attempt

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'eval/linked-art-comparison'


class LinkedArtEvalTests(unittest.TestCase):
    def test_local_definition_reaches_the_actual_model_request(self):
        requests = []
        class Client:
            config = {}
            def complete(self, prompt, **kwargs):
                requests.append(prompt)
                answer = ('{"action":"query","sql":"SELECT COUNT(*) FROM object"}'
                          if len(requests) == 1 else '{"action":"final","rows":[[1]]}')
                return {'answer': answer, 'finish_reason': 'stop'}
        class Database:
            def query(self, sql, limit):
                return {'columns': ['count'], 'rows': [[1]], 'truncated': False}
        prompt = from_local_docs()
        result = attempt({'id': 's01', 'question': 'How many sculptures?'}, prompt,
                         Database(), Client(), read_json(ROOT / 'eval/rehearsal-budget.json'),
                         database_context='Test schema')
        self.assertEqual(result['status'], 'submitted')
        for request in requests:
            self.assertIn('Object created by carving or engraving a hard material or molding a malleable material', request)
            self.assertIn('http://vocab.getty.edu/aat/300047090', request)

    def test_modified_local_documentation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'vendor/linked-art/guidance'
            shutil.copytree(ROOT / 'vendor/linked-art/guidance', folder)
            path = folder / 'recommended-vocabulary.md'
            path.write_text(path.read_text().replace('carving', 'invented definition'))
            with self.assertRaisesRegex(ValueError, 'Pinned Linked Art documentation changed'):
                from_local_docs(root)

    def test_compact_prompt_preserves_all_local_rules(self):
        local = read_json(FIXTURES / 'local.json')
        compact = read_json(FIXTURES / 'sculpture-only.json')
        self.assertEqual(compact, from_local_docs())
        self.assertEqual(local['semantics'], compact['semantics'])
        self.assertTrue(compact['instructions'].startswith(local['instructions'] + '\n'))
        addition = compact['instructions'][len(local['instructions']):]
        self.assertIn('http://vocab.getty.edu/aat/300047090', addition)
        self.assertIn('Object created by carving or engraving a hard material or molding a malleable material', addition)
        for removed in ('HumanMadeObject', 'DigitalObject', 'VisualItem', 'Artwork', 'Type of Work'):
            self.assertNotIn(removed, addition)

    def test_sculpture_section_excludes_general_questions_and_keeps_gold_private(self):
        expected = [f's{i:02}' for i in range(1, 7)]
        calls = []
        def container(service, mounts, *args):
            calls.append(service)
            paths = {dest: src for src, dest, readonly in mounts}
            self.assertEqual(read_json(paths['/app/eval/question-set.json']), expected)
            self.assertEqual([q['id'] for q in read_json(paths['/app/eval/questions.json'])], expected)
            if service == 'eval-agent':
                self.assertFalse(any('gold' in str(src) or 'gold' in dest
                                     for src, dest, readonly in mounts))
            else:
                self.assertEqual(set(read_json(paths['/app/eval/gold/answers.json'])['answers']), set(expected))
                if '--run' in args:
                    write_json(paths['/reports'] / 'report.json', {
                        'controls': {'question_ids': expected}, 'questions': [
                            {'id': qid, 'correct': True} for qid in expected],
                        'correct': 6, 'total': 6, 'elapsed_seconds': 1})
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'run'
            argv = ['run', '--candidate', 'sculpture-only', '--section', 'sculpture', '--out', str(out)]
            with patch('sys.argv', argv), patch('scripts.run_linked_art_eval.container_run', side_effect=container):
                main()
            result = read_json(out / 'comparison.json')
            self.assertEqual(set(result['sections']), {'sculpture'})
            self.assertEqual(result['conditions']['semantic'], 'sculpture-only')
        self.assertEqual(calls, ['eval-scorer', 'eval-agent', 'eval-scorer', 'eval-agent', 'eval-scorer'])

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
