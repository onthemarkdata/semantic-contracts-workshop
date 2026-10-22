"""Exercise the hook using real pushes to a temporary bare Git remote."""

import json
from pathlib import Path
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
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
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


if __name__ == "__main__":
    unittest.main()
