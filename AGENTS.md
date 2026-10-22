# Repository working agreements

## Asana after a successful push

After every successful push by an agent, update the relevant Asana task before reporting the work as finished. Executable Codex lifecycle hooks are configured in `.codex/hooks.json`; see [activation and behavior](docs/asana-push-hook.md). They detect push updates in this checkout's remote-tracking reflogs and retain pending commits until an Asana task readback confirms the full SHA. They require Codex's hook trust approval and an active agent session.

1. Verify the pushed branch and full commit SHA on the remote. Never report an unpushed commit as published.
2. Read the relevant task, its acceptance criteria, dependencies and recent updates. Use the **AI Agent** Asana connection. Start from the workshop parent task below to find the correct workstream; do not put every change on the model task.
3. Record the pushed commit links, what changed, validation evidence, remaining work and blockers. For a push containing several commits, one update per relevant task can cover all its commits. Store routine push records in task notes, preserving existing content. Reserve comments for user discussion, feedback and supplied evidence; do not duplicate Asana's automatic field-change activity.
4. Deduplicate by full commit SHA and task ID. Before retrying after an uncertain response, reread the task. Add new evidence to the existing record rather than repeating the same push update.
5. Update completion and dependencies only when their acceptance conditions are met. A successful push alone does not complete a task or remove a dependency. Inspect dependents when a prerequisite is actually completed.
6. Read back the update with `asana_get_task`, including the `notes` field and full commit SHA, so the hook can acknowledge it. Report the push and Asana sync separately if the update fails; retry the missing sync without creating an empty commit or another push. Include the task link in the final response.

Asana task entry points:

- Workshop parent: `1219726209116213` — https://app.asana.com/0/0/1219726209116213/f
- Model and trace-viewer benchmark: `1219726078017588` — https://app.asana.com/0/0/1219726078017588/f

Do not put Asana credentials in the repository, workshop containers or participant setup. The hook prompts the agent to use its existing connector. It does not run an independent background service or a GitHub workflow. Do not delete hook state to silence a pending update.

## Tailscale administration

- Tailscale is manual-only. Do not make any changes to Tailscale through any tool, API, CLI, connector, browser, configuration-file edit, service command, or indirect automation. Provide instructions for the user to carry out manually.
- This includes device removal or enrollment, VPN connections, authentication and keys, access policies, routes, DNS, settings, service restarts, and changes to integrations that configure Tailscale access.
- Do not operate the Tailscale website or sign-in flows in any browser, including login.tailscale.com and console.tailscale.com.
- For Tailscale troubleshooting, provide diagnostic commands or steps for the user to run and interpret the output they supply. Do not execute Tailscale operations on their behalf.
- A request to fix a Tailscale problem, an open tab, or completion of sign-in does not override this rule. Do not seek API or connector access as a workaround. Only an explicit user revision of this standing rule changes it.
- This restriction is specific to Tailscale. Website use for other services and read-only research of public Tailscale documentation remain allowed under normal permissions.
