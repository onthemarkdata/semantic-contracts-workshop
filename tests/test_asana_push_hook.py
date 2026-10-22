"""Exercise the hook using real pushes to a temporary bare Git remote."""

import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from scripts.asana_push_hook import handle


class PushHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.repo = base / "repo"
        self.remote = base / "remote.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(self.remote)], check=True, capture_output=True)
        subprocess.run(["git", "init", "-b", "main", str(self.repo)], check=True, capture_output=True)
        self.git("config", "user.name", "Hook Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("remote", "add", "origin", str(self.remote))
        self.commit("initial")
        self.git("push", "-u", "origin", "main")
        self.assertEqual(self.event("SessionStart"), {})

    def git(self, *args, check=True):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=check,
                              capture_output=True, text=True)

    def commit(self, message):
        self.git("commit", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD").stdout.strip()

    def event(self, kind, **kwargs):
        return handle(self.repo, {"hook_event_name": kind, **kwargs})

    def push(self):
        sha = self.commit("new work")
        self.git("push", "origin", "main")
        return sha

    def readback(self, sha, **kwargs):
        return self.event("PostToolUse", tool_name="mcp__codex_apps__asana_get_task",
                          tool_input={"task_id": "123"}, tool_response={
                              "structuredContent": {"data": {"gid": "123", "notes": sha}},
                              **kwargs})

    def test_successful_push_triggers_and_stop_blocks_until_readback(self):
        sha = self.push()
        result = self.event("PostToolUse", tool_name="Bash")
        self.assertIn(sha, result["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.event("Stop")["decision"], "block")
        self.readback(sha)
        self.assertEqual(self.event("Stop"), {})

    def test_failed_push_and_up_to_date_push_do_not_trigger(self):
        self.git("push", "origin", "main")
        self.assertEqual(self.event("PostToolUse", tool_name="Bash"), {})
        self.commit("not published")
        result = self.git("push", "missing-remote", "main", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.event("PostToolUse", tool_name="Bash"), {})
        self.assertEqual(self.event("Stop"), {})

    def test_no_duplicate_and_pending_survives_resume(self):
        sha = self.push()
        self.event("PostToolUse", tool_name="Bash")
        self.assertEqual(self.event("PostToolUse", tool_name="Bash"), {})
        self.assertIn(sha, self.event("SessionStart")["hookSpecificOutput"]["additionalContext"])
        self.readback(sha)
        self.assertEqual(self.event("SessionStart"), {})

    def test_write_failure_short_sha_and_wrong_task_do_not_acknowledge(self):
        sha = self.push()
        self.event("PostToolUse", tool_name="Bash")
        self.readback(sha, isError=True)
        self.readback(sha[:7])
        self.event("PostToolUse", tool_name="mcp__codex_apps__asana_update_tasks",
                   tool_input={"task_id": "123"}, tool_response={"data": {"gid": "123", "notes": sha}})
        self.event("PostToolUse", tool_name="mcp__codex_apps__asana_get_task",
                   tool_input={"task_id": "456"}, tool_response={"data": {"gid": "123", "notes": sha}})
        self.assertEqual(self.event("Stop")["decision"], "block")

    def test_json_text_readback_acknowledges(self):
        sha = self.push()
        self.event("PostToolUse", tool_name="mcp__codex_apps__asana_get_task",
                   tool_input={"task_id": "123"}, tool_response={"content": [
                       {"type": "text", "text": json.dumps({"data": {"gid": "123", "notes": sha}})}]})
        self.assertEqual(self.event("Stop"), {})

    def test_live_mcp_tool_name_acknowledges_readback(self):
        sha = self.push()
        self.event("PostToolUse", tool_name="Bash")
        self.event("PostToolUse", tool_name="mcp__codex_apps__asana__get_task",
                   tool_input={"task_id": "123"}, tool_response={
                       "data": {"gid": "123", "notes": sha}})
        self.assertEqual(self.event("Stop"), {})

    def test_live_mcp_tool_name_tracks_completion(self):
        self.event("PostToolUse", session_id="live-session",
                   tool_name="mcp__codex_apps__asana__update_tasks",
                   tool_input={"tasks": [{"task": "123", "completed": True}]})
        self.event("PostToolUse", session_id="live-session",
                   tool_name="mcp__codex_apps__asana__get_task",
                   tool_input={"task_id": "123"}, tool_response={
                       "data": {"gid": "123", "notes": "Verified", "completed": True}})
        self.assertEqual(self.event("Stop", session_id="live-session").get("decision"), "block")

    def test_registration_matches_live_mcp_tool_names(self):
        config = json.loads((Path(__file__).resolve().parents[1] / "scripts/global-hooks.json").read_text())
        groups = config["hooks"]["PostToolUse"]
        for name in ["mcp__codex_apps__asana__get_task", "mcp__codex_apps__asana__update_tasks"]:
            with self.subTest(name=name):
                self.assertTrue(any(re.search(group.get("matcher", ".*"), name) for group in groups))

    def test_outage_blocks_once_without_infinite_continuation(self):
        self.push()
        self.assertEqual(self.event("Stop")["decision"], "block")
        result = self.event("Stop", stop_hook_active=True)
        self.assertNotIn("decision", result)
        self.assertIn("pending", result["systemMessage"])
        self.assertEqual(self.event("Stop")["decision"], "block")

    def test_first_pre_tool_event_initializes_before_push(self):
        state = self.repo / ".git/codex-asana-push/state.json"
        state.unlink()
        self.event("PreToolUse", tool_name="Bash")
        sha = self.push()
        self.assertIn(sha, self.event("PostToolUse", tool_name="Bash")["hookSpecificOutput"]["additionalContext"])

    def test_new_branch_and_batch_push_are_detected(self):
        self.git("switch", "-c", "feature")
        self.commit("first")
        sha = self.commit("second")
        self.git("push", "-u", "origin", "feature")
        message = self.event("PostToolUse", tool_name="Bash")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("refs/remotes/origin/feature", message)
        self.assertIn(sha, message)

    def test_fetch_from_another_clone_is_not_a_local_push(self):
        other = Path(self.temp.name) / "other"
        subprocess.run(["git", "clone", str(self.remote), str(other)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(other), "-c", "user.name=Other",
                        "-c", "user.email=other@example.invalid", "commit", "--allow-empty", "-m", "other work"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(other), "push", "origin", "HEAD:main"],
                       check=True, capture_output=True)
        self.git("fetch", "origin")
        self.assertEqual(self.event("PostToolUse", tool_name="Bash"), {})
        self.assertEqual(self.event("Stop"), {})


    def sync_in_session(self, sha, session="session-a", task="123"):
        return self.event("PostToolUse", session_id=session,
                          tool_name="mcp__codex_apps__asana_get_task",
                          tool_input={"task_id": task}, tool_response={
                              "data": {"gid": task, "notes": sha}})

    def test_one_ahead_starts_after_verified_sync(self):
        sha = self.push()
        self.sync_in_session(sha)
        result = self.event("Stop", session_id="session-a")
        self.assertEqual(result["decision"], "block")
        self.assertIn("Select and DO one next eligible task", result["reason"])
        self.assertIn(sha, result["reason"])
        self.assertIn("Source tasks: 123", result["reason"])
        self.assertIn("approval gates", result["reason"])
        self.assertIn("only report status", result["reason"])
        self.assertIn("If no eligible task exists", result["reason"])

    def test_one_ahead_waits_for_all_pending_pushes(self):
        first = self.push()
        second = self.push()
        self.sync_in_session(first)
        result = self.event("Stop", session_id="session-a")
        self.assertIn("Successful Git pushes need", result["reason"])
        self.assertNotIn("One-ahead policy", result["reason"])
        self.sync_in_session(second, task="456")
        result = self.event("Stop", session_id="session-a")
        self.assertIn("Source tasks: 123, 456", result["reason"])

    def test_one_ahead_does_not_chain_after_followup_push(self):
        self.sync_in_session(self.push())
        self.event("Stop", session_id="session-a")
        self.sync_in_session(self.push())
        self.assertEqual(self.event("Stop", session_id="session-a"), {})
        state = json.loads((self.repo / '.git/codex-asana-push/state.json').read_text())
        self.assertEqual(state['one_ahead']['session-a']['status'], 'requested')
        self.assertEqual(state['pending'], {})

    def test_one_ahead_survives_resume_without_rearming(self):
        self.sync_in_session(self.push())
        self.event("SessionStart", session_id="session-a")
        self.assertEqual(self.event("Stop", session_id="session-a")["decision"], "block")
        self.event("SessionStart", session_id="session-a")
        self.assertEqual(self.event("Stop", session_id="session-a"), {})

    def test_one_ahead_has_its_own_bounded_stop_budget(self):
        self.sync_in_session(self.push())
        result = self.event("Stop", session_id="session-a", stop_hook_active=True)
        self.assertEqual(result["decision"], "block")
        self.assertEqual(self.event("Stop", session_id="session-a", stop_hook_active=True), {})

    def test_one_ahead_sessions_do_not_consume_each_others_slot(self):
        self.sync_in_session(self.push(), session="session-a")
        self.assertEqual(self.event("Stop", session_id="session-b"), {})
        self.sync_in_session(self.push(), session="session-b")
        self.assertIn("One-ahead policy", self.event("Stop", session_id="session-b")["reason"])
        self.assertIn("One-ahead policy", self.event("Stop", session_id="session-a")["reason"])

    def test_missing_session_id_does_not_create_global_one_ahead_slot(self):
        self.readback(self.push())
        self.assertEqual(self.event("Stop", session_id="session-a"), {})
        state = json.loads((self.repo / '.git/codex-asana-push/state.json').read_text())
        self.assertEqual(state['one_ahead'], {})

    def test_reads_without_new_push_evidence_do_not_queue_next_task(self):
        self.sync_in_session('a' * 40)
        self.assertEqual(self.event("Stop", session_id="session-a"), {})


    def completion_request(self, task="123"):
        return self.event("PostToolUse", session_id="session-a", tool_name="mcp__asana_update_tasks",
                          tool_input={"tasks": [{"task": task, "completed": True}]}, tool_response={})

    def completion_readback(self, task="123", completed=True):
        return self.event("PostToolUse", session_id="session-a", tool_name="mcp__asana_get_task",
                          tool_input={"task_id": task}, tool_response={
                              "data": {"gid": task, "notes": "Done with evidence", "completed": completed}})

    def test_completion_without_push_requires_write_then_readback(self):
        self.completion_request()
        self.assertEqual(self.event("Stop", session_id="session-a"), {})
        self.completion_readback()
        self.assertIn("verified task completion", self.event("Stop", session_id="session-a")["reason"])

    def test_incomplete_readback_does_not_start_next_task(self):
        self.completion_request()
        self.completion_readback(completed=False)
        self.assertEqual(self.event("Stop", session_id="session-a"), {})

    def test_old_completed_task_does_not_start_next_task(self):
        self.completion_readback()
        self.assertEqual(self.event("Stop", session_id="session-a"), {})

    def test_different_task_cannot_acknowledge_completion_request(self):
        self.completion_request()
        self.completion_readback(task="456")
        self.assertEqual(self.event("Stop", session_id="session-a"), {})


if __name__ == "__main__":
    unittest.main()
