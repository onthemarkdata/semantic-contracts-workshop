"""Codex lifecycle hook: queue successful Git pushes until Asana readback confirms them.

No network requests or credentials. Git's remote-tracking reflogs supply push
evidence; the agent's existing Asana connector performs the actual update.
"""

import fcntl
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")


def git_dir(root):
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-common-dir"],
        check=True, capture_output=True, text=True, timeout=5,
    )
    return (root / result.stdout.strip()).resolve()


def push_events(common):
    events = {}
    logs = common / "logs" / "refs" / "remotes"
    if not logs.exists():
        return events
    for path in sorted(logs.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        ref = "refs/remotes/" + path.relative_to(logs).as_posix()
        for line in path.read_text().splitlines():
            header, separator, message = line.partition("\t")
            if not separator or message != "update by push":
                continue
            fields = header.split()
            if len(fields) < 2 or not all(SHA.fullmatch(x) for x in fields[:2]):
                continue
            key = hashlib.sha256((ref + "\n" + line).encode()).hexdigest()
            events[key] = {"ref": ref, "before": fields[0], "sha": fields[1]}
    return events


def task_records(value, depth=0):
    """Accept structured MCP responses and their JSON text-content equivalent."""
    if depth > 8:
        return
    if isinstance(value, str):
        try:
            yield from task_records(json.loads(value), depth + 1)
        except (ValueError, TypeError):
            pass
    elif isinstance(value, list):
        for item in value:
            yield from task_records(item, depth + 1)
    elif isinstance(value, dict):
        if value.get("isError") is True:
            return
        if isinstance(value.get("notes"), str) and str(value.get("gid", "")).isdigit():
            yield value
        # Only unwrap transport containers, never parse arbitrary task notes.
        for key in ("structuredContent", "content", "text", "data", "result"):
            if key in value:
                yield from task_records(value[key], depth + 1)


def reminder(pending):
    rows = "\n".join(
        f"- {item['ref']}: {item['before']} -> {item['sha']}"
        for item in pending.values()
    )
    return (
        "Successful Git pushes need an Asana update:\n" + rows + "\n"
        "Follow AGENTS.md: verify the remote, update the relevant task using the AI Agent "
        "connection, preserve existing notes and dependencies, and include the FULL pushed "
        "SHA in task notes. Then call asana_get_task with notes included to verify the update. "
        "The hook clears a pending push only when that readback contains its full SHA. "
        "Do not create another commit to acknowledge this. If Asana is unavailable, report "
        "the sync failure explicitly; pending pushes remain queued."
    )


def handle(root, event):
    common = git_dir(root)
    state_dir = common / "codex-asana-push"
    state_dir.mkdir(mode=0o700, exist_ok=True)
    with (state_dir / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = state_dir / "state.json"
        events = push_events(common)
        if path.exists():
            state = json.loads(path.read_text())
            if state.get("version") != 1:
                raise ValueError("Unknown Asana push-hook state version")
        else:
            # SessionStart/PreToolUse establish the baseline BEFORE a push.
            state = {"version": 1, "seen": list(events), "pending": {}, "verified": {}}
        kind = event.get("hook_event_name")
        added = False
        if kind != "PreToolUse":
            seen = set(state["seen"])
            for key, item in events.items():
                if key not in seen:
                    state["pending"][key] = item
                    added = True
            state["seen"] = sorted(seen | events.keys())

        # A successful write alone is insufficient: observe a real task readback.
        tool_name = event.get("tool_name", "")
        if kind == "PostToolUse" and tool_name.endswith("asana_get_task"):
            requested = str(event.get("tool_input", {}).get("task_id", ""))
            for task in task_records(event.get("tool_response")):
                if str(task["gid"]) != requested:
                    continue
                for key, item in list(state["pending"].items()):
                    if re.search(r"(?<![0-9a-f])" + item["sha"] + r"(?![0-9a-f])", task["notes"]):
                        state["verified"][key] = {**item, "task_id": requested}
                        del state["pending"][key]

        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2) + "\n")
        temporary.replace(path)
        pending = state["pending"]
        if not pending:
            return {}
        message = reminder(pending)
        if kind == "Stop":
            if event.get("stop_hook_active"):
                # Avoid an infinite continuation loop during a connector outage.
                return {"systemMessage": "Asana sync remains pending. " + message}
            return {"decision": "block", "reason": message}
        if kind == "SessionStart" or (kind == "PostToolUse" and added):
            return {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": message}}
        return {}


def main():
    event = json.load(sys.stdin)
    try:
        result = handle(ROOT, event)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # Surface failure instead of silently declaring Asana up to date.
        result = {"systemMessage": f"Asana push hook failed: {error}. Check Asana sync manually."}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
