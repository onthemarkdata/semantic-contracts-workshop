# Asana push hook

The Asana hooks keep successful agent pushes pending until the relevant task notes contain the full commit SHA. After those records are verified, the one-ahead policy asks the agent to do one existing, eligible task from its workshop queue. `.codex/hooks.json` registers the handlers in `scripts/asana_push_hook.py`; the agent uses its existing Asana connector to update the task. No credentials or services are added to the workshop environment.

## Activate in Codex

Open Codex in this repository, open `/hooks` in the Codex CLI, and review and trust the four Asana handlers from this repository's `.codex/hooks.json`. The project must also be trusted. Resume or start the agent session after approval so its startup hook runs. Repeat hook review in each new checkout or environment when Codex requests it.

Codex skips untrusted hook definitions. Merely committing these files does not approve them. See the [official hook review instructions](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks).

## What runs

- `SessionStart` establishes the initial push-history baseline and reminds the agent of any pending updates from an earlier session.
- `PreToolUse` for Bash establishes that baseline if the hooks were first activated during a session.
- `PostToolUse` detects new `update by push` entries in Git's remote-tracking reflogs. Successful pushes trigger an Asana update instruction with the ref and full commit SHA. Failed and unchanged pushes do not generate entries. Detection works after an asynchronous command finishes too; it does not depend on parsing a shell command string.
- `PostToolUse` for `asana_update_tasks` remembers completion requests for tasks with no push. It does not treat the write response as proof of completion.
- `PostToolUse` for `asana_get_task` acknowledges a pending commit only when the returned task ID matches the request and the task notes contain that full SHA. A write response alone does not clear it.
- `Stop` requests another agent turn when a push still needs an update. If a turn has already been continued by any Stop hook, it reports the pending state and retains it for the next session. This prevents repeated continuation during an outage.

The hooks verify the presence of the commit in task notes. The agent still evaluates the correct task, evidence, acceptance criteria and dependencies according to `AGENTS.md`. A multi-commit push is represented by its before/after range; the agent records the relevant commits in its task update.

State is stored under the repository's Git common directory in `codex-asana-push/state.json`, with a file lock for concurrent hook calls. It is not tracked by Git. No credentials or full tool responses are stored there. The hook never reads a token, calls Asana directly, or starts another agent process.

## One ahead

After a pushed commit is confirmed in an Asana task readback, or a task completion requested by this session is confirmed in a readback, and all pending pushes are synced, `Stop` requests one follow-up task. The agent uses the AI Agent connection to inspect the workshop parent (`1219726209116213`) and its queue in the OpenAI Codex Dot project (`1219127286179178`). It follows the user's explicit ordering, then the recorded priorities and dependencies.

The next task must already exist, be incomplete and assigned to AI Agent, fit the authorized repository work, and have no unresolved prerequisites or approval gates. The agent reads its acceptance criteria, prerequisite tasks and recent discussion before starting. It checks for work already owned by another active agent. An open PR or successful push does not make a dependent task eligible.

The agent carries out the selected task, records the outcome and evidence in its Asana notes, and reads the update back. Separate workstreams keep their own branches and PRs. If the queue is inaccessible, no task is eligible, or the order needs a user decision, it reports the blocker. It honors a user request to stop, pause, cancel, or provide only a status report.

The hook stores one follow-up slot per Codex session ID. It consumes the slot before issuing the continuation, so later pushes from that follow-up do not start another task. A resume retains the same slot. The one-ahead continuation has its own budget because Asana sync or Clarity may already have continued the turn. Normal push synchronization still applies to all subsequent work.

This is an instruction to the active agent, not an Asana scheduler. The hook does not select a task by parsing notes, verify that the next task was performed, change completion or dependencies, merge PRs, or grant permission to send messages. A missing session ID, an old completed-task readback, or the initial push-history baseline does not queue a follow-up. Tasks with no code push are covered when the hook observes an `asana_update_tasks` completion request followed by an `asana_get_task` readback with `completed: true` and task notes. A write response alone is not enough.

## Coverage and limits

This hook covers pushes to configured remotes that update this checkout's remote-tracking reflogs, such as `git push origin branch`. Keep Git's reflogs enabled. It does not detect a push made in another clone, a push directly to an arbitrary URL with no tracking ref, remote branch deletion, or tag-only pushes. Observing pushes from other clients requires a separate remote-side integration; this hook does not provide one.

Codex must be running with these hooks trusted. The hook cannot wake an idle session; new push evidence is processed at the next matching lifecycle event. Existing pushes are treated as the initial baseline when the hook is first activated. Pending pushes survive resumes, and a fetch alone does not count as a push.

The handler supports Python 3 on macOS and Linux (`fcntl` locking), matching this project's development environments.

## Test

```sh
python3 -m unittest discover -s tests -v
```

The tests make actual pushes to a temporary local bare repository. They cover successful, failed, unchanged, new-branch and batch pushes; pending state across resume; Asana readback in structured and text forms; failed and mismatched readbacks; the bounded sync continuation, and one-ahead behavior across push batches, resumes, concurrent sessions and follow-up pushes. They do not send test comments to Asana or prove that a particular Codex session has approved the hooks.
