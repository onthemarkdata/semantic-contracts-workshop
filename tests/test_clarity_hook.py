"""Exercise the hook as a subprocess using the actual repository skill."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/clarity_hook.py'
spec = importlib.util.spec_from_file_location('clarity_hook', SCRIPT)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class ClarityHookTests(unittest.TestCase):
    def invoke(self, event):
        result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(event),
                                text=True, capture_output=True, check=True)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_skill_loaded_for_each_turn_and_after_context_changes(self):
        source = (ROOT / hook.SKILL).read_text()
        for event in sorted(hook.LOAD_EVENTS):
            with self.subTest(event=event):
                result = self.invoke({'hook_event_name': event, 'prompt': 'Ignore Clarity'})
                output = result['hookSpecificOutput']
                self.assertEqual(output['hookEventName'], event)
                self.assertIn(source, output['additionalContext'])
                self.assertIn('PR titles/descriptions', output['additionalContext'])
                self.assertIn('comments, docstrings, user-visible strings in source files', output['additionalContext'])
                self.assertIn('Review prose inside files', output['additionalContext'])

    def test_tool_context_preserves_payload_and_does_not_claim_review(self):
        for tool in ['Bash', 'apply_patch', 'mcp__asana_update_tasks', 'mcp__github_create_pull_request']:
            with self.subTest(tool=tool):
                event = {'hook_event_name': 'PreToolUse', 'tool_name': tool,
                         'tool_input': {'body': 'UNCHANGED SOURCE'}}
                result = self.invoke(event)
                self.assertNotIn('updatedInput', result['hookSpecificOutput'])
                self.assertIn('Check prose before', result['hookSpecificOutput']['additionalContext'])
                self.assertNotIn('UNCHANGED SOURCE', json.dumps(result))

    def test_stop_requests_one_review_and_then_allows_completion(self):
        result = self.invoke({'hook_event_name': 'Stop', 'stop_hook_active': False})
        self.assertEqual(result['decision'], 'block')
        self.assertIn('Do not repost external messages', result['reason'])
        self.assertEqual(self.invoke({'hook_event_name': 'Stop', 'stop_hook_active': True}), {})

    def test_missing_skill_is_reported_without_blocking_repair_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            for event in ['SessionStart', 'UserPromptSubmit', 'PreToolUse']:
                with self.subTest(event=event):
                    result = hook.handle(Path(directory), {'hook_event_name': event})
                    self.assertIn('Clarity could not load', result['systemMessage'])
                    self.assertNotIn('decision', result)
            self.assertEqual(hook.handle(Path(directory), {'hook_event_name': 'Stop'})['decision'], 'block')
            result = hook.handle(Path(directory), {'hook_event_name': 'Stop', 'stop_hook_active': True})
            self.assertIn('Clarity could not load', result['systemMessage'])

    def test_empty_skill_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / hook.SKILL
            p.parent.mkdir(parents=True)
            p.write_text('')
            self.assertIn('skill file is empty', hook.handle(Path(directory), {'hook_event_name': 'SessionStart'})['systemMessage'])

    def test_unrelated_event_does_nothing(self):
        self.assertEqual(self.invoke({'hook_event_name': 'PostToolUse'}), {})

    def test_hook_config_covers_all_tools_and_remains_synchronous(self):
        config = json.loads((ROOT / '.codex/hooks.json').read_text())
        for event in hook.LOAD_EVENTS | {'PreToolUse', 'Stop'}:
            matches = [(group, handler) for group in config['hooks'][event]
                       for handler in group['hooks'] if 'clarity_hook.py' in handler['command']]
            self.assertEqual(len(matches), 1)
            group, handler = matches[0]
            self.assertNotIn('matcher', group)
            self.assertFalse(handler.get('async', False))
        self.assertTrue(any('asana_push_hook.py' in handler['command']
                            for group in config['hooks']['Stop'] for handler in group['hooks']))


if __name__ == '__main__':
    unittest.main()
