"""Verify global installation and isolation using temporary user homes and workspaces."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.asana_push_hook import global_handle
from scripts.install_global_hooks import install


class GlobalHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="global hooks ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "codex"
        self.cwd = self.base / "plain workspace"
        self.cwd.mkdir()

    def event(self, kind, **kwargs):
        return global_handle({"hook_event_name": kind, "cwd": str(self.cwd),
                              "session_id": "session-a", **kwargs}, self.home)

    def complete(self, task="123"):
        self.event("PostToolUse", tool_name="asana_update_tasks",
                   tool_input={"tasks": [{"task": task, "completed": True}]})
        self.event("PostToolUse", tool_name="asana_get_task", tool_input={"task_id": task},
                   tool_response={"data": {"gid": task, "notes": "Verified work", "completed": True}})

    def test_install_preserves_other_hooks_and_is_idempotent(self):
        self.home.mkdir()
        other = {"hooks": [{"type": "command", "command": "echo existing"}]}
        original = {"description": "User hooks", "hooks": {"Stop": [other]}}
        (self.home / "hooks.json").write_text(json.dumps(original))
        first = install(self.home)
        self.assertEqual(json.loads((Path(first["backup"]) / "hooks.json").read_text()), original)
        installed = (self.home / "hooks.json").read_text()
        install(self.home)
        self.assertEqual((self.home / "hooks.json").read_text(), installed)
        config = json.loads(installed)
        self.assertIn(other, config["hooks"]["Stop"])
        self.assertEqual(sum(len(g["hooks"]) for groups in config["hooks"].values() for g in groups), 10)
        self.assertFalse((self.home / "config.toml").exists())

    def test_installed_clarity_runs_outside_git_and_preserves_existing_skill(self):
        skill = self.home / "skills/clarity/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("USER CLARITY SKILL")
        install(self.home)
        config = json.loads((self.home / "hooks.json").read_text())
        command = config["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        result = subprocess.run(command, shell=True, cwd=self.cwd,
                                env={**os.environ, "CODEX_HOME": str(self.home)},
                                input=json.dumps({"hook_event_name": "UserPromptSubmit"}),
                                text=True, capture_output=True, check=True)
        self.assertIn("USER CLARITY SKILL", json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(skill.read_text(), "USER CLARITY SKILL")

    def test_non_git_completion_requests_one_task_from_relevant_queue(self):
        self.assertEqual(self.event("SessionStart"), {})
        self.complete()
        result = self.event("Stop")
        self.assertEqual(result["decision"], "block")
        self.assertIn("source tasks above and their parent/project", result["reason"])
        self.assertNotIn("1219726209116213", result["reason"])
        self.assertEqual(self.event("Stop"), {})

    def test_one_ahead_budget_is_shared_across_workspaces_in_session(self):
        self.complete()
        self.assertEqual(self.event("Stop")["decision"], "block")
        self.cwd = self.base / "another workspace"
        self.cwd.mkdir()
        self.complete("456")
        self.assertEqual(self.event("Stop"), {})

    def test_global_git_detection_uses_event_cwd_not_installed_script(self):
        remote = self.base / "remote.git"
        for args in (["init", "--bare", "-b", "main", str(remote)],
                     ["init", "-b", "main", str(self.cwd)]):
            subprocess.run(["git", *args], check=True, capture_output=True)
        def git(*args):
            return subprocess.run(["git", "-C", str(self.cwd), *args], check=True,
                                  capture_output=True, text=True)
        git("remote", "add", "origin", str(remote))
        self.event("SessionStart")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-m", "Test")
        git("push", "-u", "origin", "main")
        sha = git("rev-parse", "HEAD").stdout.strip()
        self.assertIn(sha, self.event("PostToolUse")["hookSpecificOutput"]["additionalContext"])
        self.assertTrue((self.cwd / ".git/codex-asana-push/state.json").exists())

    def test_missing_cwd_cannot_silently_use_installation_directory(self):
        with self.assertRaises(ValueError):
            global_handle({"hook_event_name": "Stop"}, self.home)


if __name__ == "__main__":
    unittest.main()
