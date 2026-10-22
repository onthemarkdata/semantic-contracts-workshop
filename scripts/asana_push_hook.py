"""Codex lifecycle hook: queue successful Git pushes until Asana readback confirms them.

No network requests or credentials. Git's remote-tracking reflogs supply push
evidence; the agent's existing Asana connector performs the actual update.
"""

import fcntl
import hashlib
import json
import os
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



def next_task_instruction(item):
    sources = ", ".join(item["task_ids"])
    trigger = f"verified push {item['sha']}" if item.get("sha") else "verified task completion"
    return (
        "One-ahead policy: current work has a verified Asana readback. "
        f"Source tasks: {sources}. Trigger: {trigger}. "
        "If the current user has asked to stop, pause, cancel, or only report status, "
        "honor that request and do not start another task. Otherwise, when the current "
        "authorized work is ready for handoff, use the AI Agent Asana connection to "
        "read the source tasks above and their parent/project to identify the relevant "
        "AI Agent queue for the current work. Use project instructions and verified "
        "task links; never assume an unrelated project is the queue. "
        "Select and DO one next eligible task; do not merely "
        "recommend it or ask whether to proceed. Follow the user's explicit order, "
        "then recorded priority and dependencies. Read the selected task's acceptance "
        "criteria, dependencies, assignee, recent discussion and approval gates first. "
        "It must be existing, incomplete, assigned to AI Agent, within the current work's "
        "authorized scope, not already being handled by another agent, and unblocked. "
        "Read prerequisite tasks to verify completion; absence of dependency fields "
        "is not proof that there are none. A push or open PR does not complete a task "
        "or waive a review gate. Reuse an independent branch/PR for a separate workstream. "
        "Record the selected task, work performed, validation, outcome and remaining "
        "blockers in the relevant Asana notes, then read them back. Apply Clarity to "
        "the files and messages. Do not merge, invent tasks, change assignees, remove "
        "dependencies, or send messages without existing authorization. If no eligible "
        "task exists, the queue is inaccessible, or ordering requires a user decision, "
        "report the concrete blocker instead of guessing. This is one additional task "
        "for this session, not a recursive queue-draining loop. Its pushes still need "
        "normal Asana synchronization but must not start a second follow-up task."
    )


def handle(root, event, *, storage=None, scan_pushes=True, sessions=None):
    common = git_dir(root) if scan_pushes else None
    state_dir = storage if storage is not None else common / "codex-asana-push"
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state_dir / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = state_dir / "state.json"
        events = push_events(common) if common is not None else {}
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

        session_id = event.get("session_id")
        session_state = sessions if sessions is not None else state
        awaiting = session_state.setdefault("completion_requests", {})
        confirmed = []
        # A successful write alone is insufficient: observe a real task readback.
        # MCP lifecycle names use a double separator; the tool API exposed to
        # the agent and older fixtures may use a single underscore instead.
        tool_name = event.get("tool_name", "").replace("asana__", "asana_")
        if kind == "PostToolUse" and tool_name.endswith("asana_update_tasks") and session_id:
            requested_completions = {
                str(task.get("task", "")) for task in event.get("tool_input", {}).get("tasks", [])
                if task.get("completed") is True and str(task.get("task", "")).isdigit()
            }
            if requested_completions:
                awaiting[session_id] = sorted(set(awaiting.get(session_id, [])) | requested_completions)
        if kind == "PostToolUse" and tool_name.endswith("asana_get_task"):
            requested = str(event.get("tool_input", {}).get("task_id", ""))
            for task in task_records(event.get("tool_response")):
                if str(task["gid"]) != requested:
                    continue
                if session_id and requested in awaiting.get(session_id, []) and task.get("completed") is True:
                    confirmed.append({"sha": None, "task_id": requested})
                    awaiting[session_id].remove(requested)
                for key, item in list(state["pending"].items()):
                    if re.search(r"(?<![0-9a-f])" + item["sha"] + r"(?![0-9a-f])", task["notes"]):
                        state["verified"][key] = {**item, "task_id": requested}
                        confirmed.append({"sha": item["sha"], "task_id": requested})
                        del state["pending"][key]

        # One slot per real Codex session; preserve it across resumes and later pushes.
        one_ahead = session_state.setdefault("one_ahead", {})
        slot = one_ahead.get(session_id) if session_id else None
        if confirmed and session_id:
            if slot is None:
                slot = {"status": "pending", "sha": confirmed[0]["sha"], "task_ids": []}
                one_ahead[session_id] = slot
            if slot["status"] == "pending":
                slot["task_ids"] = sorted(set(slot["task_ids"]) | {x["task_id"] for x in confirmed})

        pending = state["pending"]
        result = {}
        if pending:
            message = reminder(pending)
            if kind == "Stop":
                if event.get("stop_hook_active"):
                    result = {"systemMessage": "Asana sync remains pending. " + message}
                else:
                    result = {"decision": "block", "reason": message}
            elif kind == "SessionStart" or (kind == "PostToolUse" and added):
                result = {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": message}}
        elif kind == "Stop" and slot and slot["status"] == "pending":
            # This has its own single-use budget: sync or Clarity may already have
            # continued the turn. Persist consumption before issuing the prompt.
            slot["status"] = "requested"
            result = {"decision": "block", "reason": next_task_instruction(slot)}

        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2) + "\n")
        temporary.replace(path)
        return result


def global_handle(event, home):
    """Resolve the active workspace and share one follow-up budget across projects."""
    cwd = event.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        raise ValueError("Global Asana hook requires an absolute event cwd")
    root = Path(cwd).resolve(strict=True)
    probe = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=5)
    is_git = probe.returncode == 0
    if not is_git and "not a git repository" not in probe.stderr:
        raise ValueError("Cannot inspect workspace Git state; check Git access manually")
    state_home = home / "hook-state/otmd"
    state_home.mkdir(parents=True, mode=0o700, exist_ok=True)
    storage = None if is_git else state_home / "workspaces" / hashlib.sha256(str(root).encode()).hexdigest()
    with (state_home / "sessions.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = state_home / "sessions.json"
        sessions = json.loads(path.read_text()) if path.exists() else {}
        # Preserve a previously consumed repository-local slot on migration.
        if is_git:
            old = git_dir(root) / "codex-asana-push/state.json"
            if old.exists():
                prior = json.loads(old.read_text())
                for key in ("one_ahead", "completion_requests"):
                    target = sessions.setdefault(key, {})
                    for session, value in prior.get(key, {}).items():
                        target.setdefault(session, value)
        result = handle(root, event, storage=storage, scan_pushes=is_git, sessions=sessions)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(sessions, indent=2) + "\n")
        temporary.replace(path)
        return result


def main():
    event = json.load(sys.stdin)
    try:
        home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        result = global_handle(event, home) if "--global" in sys.argv else handle(ROOT, event)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # Surface failure instead of silently declaring Asana up to date.
        result = {"systemMessage": f"Asana push hook failed: {error}. Check Asana sync manually."}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
