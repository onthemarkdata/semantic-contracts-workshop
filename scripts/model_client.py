"""Initialize and smoke-test the workshop's pinned Docker Hub model (stdlib only)."""

import argparse
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_LOCK = Path(__file__).resolve().parent.parent / "models" / "gemma.lock.json"
if not DEFAULT_LOCK.exists():
    DEFAULT_LOCK = Path(__file__).with_name("gemma.lock.json")


class ModelClient:
    def __init__(self, base_url, config):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.model = config["model"]
        self.model_path = "/models/" + urllib.parse.quote(self.model, safe="/")

    def request(self, path, payload=None, timeout=30):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        return urllib.request.urlopen(req, timeout=timeout)

    def json_request(self, path, payload=None, timeout=30):
        with self.request(path, payload, timeout) as response:
            body = response.read()
        return json.loads(body) if body else None

    def initialize(self):
        try:
            self.json_request(self.model_path)
            print("Pinned model is already cached.", flush=True)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            error.close()
            print(f"Pulling {self.model} from Docker Hub (about 4.09 GB).", flush=True)
            # DMR streams pull progress. Do not buffer the whole stream or treat
            # a successful HTTP header as evidence that the download completed.
            last_report = 0.0
            with self.request("/models/create", {"from": self.model}, timeout=1800) as response:
                for line in response:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        raise RuntimeError(f"Invalid pull response: {line[:300]!r}") from None
                    if event.get("error"):
                        raise RuntimeError(f"Model pull failed: {event['error']}")
                    if time.monotonic() - last_report > 10:
                        print(json.dumps(event), flush=True)
                        last_report = time.monotonic()
            # Resolve exactly the requested digest; never silently use another tag.
            self.json_request(self.model_path)

        self.json_request(
            "/engines/llama.cpp/_configure",
            {
                "model": self.model,
                "context-size": self.config["context_size"],
                "llamacpp": {"reasoning-budget": 0},
                "runtime-flags": [
                    "--jinja",
                    "--chat-template-kwargs", '{"enable_thinking":false}',
                    "--n-gpu-layers", "0",
                    "--no-mmproj-offload",
                    "--parallel", "1",
                    "--threads", str(self.config["threads"]),
                    "--threads-batch", str(self.config["threads"]),
                    "--batch-size", "128",
                    "--ubatch-size", "128",
                ],
            },
        )
        result = self.complete("Reply with exactly READY.", max_tokens=32)
        if result["answer"].strip() != "READY":
            raise RuntimeError(f"Startup probe did not return READY: {result['answer']!r}")
        print(json.dumps({"event": "model_ready", **result}), flush=True)

    def complete(self, prompt, max_tokens=None):
        started = time.monotonic()
        result = self.json_request(
            "/engines/llama.cpp/v1/chat/completions",
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": max_tokens or self.config["max_tokens"],
                "stream": False,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=self.config["request_timeout_seconds"],
        )
        if result.get("error"):
            raise RuntimeError(f"Inference failed: {result['error']}")
        choice = result["choices"][0]
        answer = choice["message"].get("content")
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("Inference returned no final text.")
        return {
            "model": self.model,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "answer": answer,
            "finish_reason": choice.get("finish_reason"),
            "usage": result.get("usage"),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "check", "benchmark"])
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--prompt", default="In one sentence, explain what a database data contract checks.")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.runs <= 20:
        parser.error("--runs must be between 1 and 20")
    config = json.loads(args.lock.read_text())
    client = ModelClient(os.environ.get("MODEL_RUNNER_URL", "http://model-runner:12434"), config)
    if args.action == "init":
        client.initialize()
    else:
        count = args.runs if args.action == "benchmark" else 1
        for number in range(count):
            result = client.complete(args.prompt)
            print(json.dumps({"run": number + 1, **result}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as error:
        print(f"Model request failed: HTTP {error.code}: {error.read().decode(errors='replace')[:1000]}", file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        print(f"Model request failed: {error}", file=sys.stderr)
        sys.exit(1)
