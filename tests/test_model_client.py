"""Failure checks for the startup gate; no model download or third-party packages."""

import contextlib
import io
import json
from pathlib import Path
import unittest
import urllib.error
from unittest.mock import patch

from scripts.model_client import ModelClient


CONFIG = json.loads((Path(__file__).parents[1] / "models/gemma.lock.json").read_text())


def missing():
    error = urllib.error.HTTPError("http://runner/models/test", 404, "missing", {}, None)
    error.close()
    return error


class StartupGateTests(unittest.TestCase):
    def setUp(self):
        self.client = ModelClient("http://runner", CONFIG)
        self.output = io.StringIO()
        self.quiet = contextlib.redirect_stdout(self.output)
        self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__, None, None, None)

    def test_http_200_with_streamed_pull_error_does_not_mark_ready(self):
        stream = io.BytesIO(b'{"type":"progress"}\n{"error":"registry download failed"}\n')
        with patch.object(self.client, "json_request", side_effect=missing()), \
             patch.object(self.client, "request", return_value=stream), \
             patch.object(self.client, "complete") as inference:
            with self.assertRaisesRegex(RuntimeError, "registry download failed"):
                self.client.initialize()
        inference.assert_not_called()
        self.assertNotIn("model_ready", self.output.getvalue())

    def test_incomplete_pull_requires_model_to_exist_before_configuring(self):
        with patch.object(self.client, "json_request", side_effect=[missing(), missing()]) as api, \
             patch.object(self.client, "request", return_value=io.BytesIO(b"")), \
             patch.object(self.client, "complete") as inference:
            with self.assertRaises(urllib.error.HTTPError):
                self.client.initialize()
        self.assertEqual(api.call_count, 2)
        inference.assert_not_called()

    def test_cached_model_skips_pull_but_still_requires_working_inference(self):
        with patch.object(self.client, "json_request", return_value={}), \
             patch.object(self.client, "request") as pull, \
             patch.object(self.client, "complete", side_effect=RuntimeError("out of memory")):
            with self.assertRaisesRegex(RuntimeError, "out of memory"):
                self.client.initialize()
        pull.assert_not_called()
        self.assertNotIn("model_ready", self.output.getvalue())

    def test_registry_or_permission_errors_are_not_treated_as_cache_misses(self):
        forbidden = urllib.error.HTTPError("http://runner", 403, "forbidden", {}, None)
        self.addCleanup(forbidden.close)
        with patch.object(self.client, "json_request", side_effect=forbidden), \
             patch.object(self.client, "request") as pull:
            with self.assertRaises(urllib.error.HTTPError):
                self.client.initialize()
        pull.assert_not_called()

    def test_reasoning_without_final_answer_is_not_success(self):
        response = {"choices": [{"message": {"content": "", "reasoning_content": "thinking"}}]}
        with patch.object(self.client, "json_request", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "no final text"):
                self.client.complete("test")

    def test_wrong_startup_answer_does_not_mark_ready(self):
        with patch.object(self.client, "json_request", return_value={}), \
             patch.object(self.client, "complete", return_value={"answer": "I should say READY"}):
            with self.assertRaisesRegex(RuntimeError, "did not return READY"):
                self.client.initialize()
        self.assertNotIn("model_ready", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
