# Semantic contracts workshop development

This repository contains the workshop code and teaching materials. These agent
instructions and `.agents/`, `.codex/`, and `scripts/dev/` support development.
The delivered workshop must work independently of HQ and these developer tools.

## Workshop boundaries

- Read [the workshop plan](docs/workshop-plan.md) when changing scope, curriculum,
  evaluation, or participant setup. Proposed choices are not implemented features.
- Keep participant startup, exercises, tests, and CI independent of HQ, Codex,
  1Password, Kata, Asana, paid APIs, and developer accounts. Do not load development
  skills into the participant agent. Give future teaching skills their own location.
- Use the checked-in museum dataset. Preserve source attribution and provenance;
  do not add live API/image downloads or select models and vocabularies by assumption.
- Preserve unrelated work and the existing README's teaching content. Do not
  enable Actions, Pages, sharing, or paid services as part of ordinary development.

## Repository map

- `data_contract_components/contract_definition/`: JSON contract specifications.
- `data_contract_components/data_assets/`: PostgreSQL helpers, seeding, and Alembic migrations.
- `data_contract_components/detection/`: catalog, coverage, and violation checks.
- `data_contract_components/prevention/`: database-backed contract tests.
- `docker-compose*.yml`, `.devcontainer.json`: participant and test environments.
- `docs/workshop-plan.md`: intended workshop scope and unresolved decisions.

## Development workflow

Follow [work and continuity](.agents/references/workflow.md) and
[tool and writing rules](.agents/references/tools-and-writing.md).
Use the repository-local Clarity skill for course materials and reader-facing
writing, and the 1Password skill when managing developer credentials. Kata is
available for optional local continuity through `./scripts/dev/kata`; never use
HQ's database or snapshot. See [developer setup](docs/development-agent-setup.md).

For agreed changes, prepare checked branches and PRs under `otmd-ai-agent` for
Mark's review; Mark merges. Verify identity and signing before committing. Do
not use Mark's human credentials as a fallback. Other publishing and messaging
require explicit authorization.

## Verification

Run checks appropriate to the files changed and `git diff --check`. Configuration
and skill changes can be checked with `python3 scripts/dev/check-agent-setup.py`
(Python 3.11+); runtime changes need their relevant workshop checks.

The existing integration suite is
`data_contract_components/prevention/test_data_contract_violations.py` and needs
PostgreSQL with migrations applied. Inspect the Compose files before running it.
Use an isolated Compose project and `--exit-code-from devcontainer` when running
`docker-compose.test.yml`; do not claim a pass merely because containers started.
Never delete existing database volumes as routine cleanup. Report unavailable
checks and failures without changing their meaning.

## Reader-facing text

Apply [Clarity](.agents/skills/clarity/SKILL.md) before delivering text for people to read, including chat replies, progress updates, PR descriptions, commit messages, Asana notes, documentation, UI copy, comments, docstrings and user-visible strings in source files. Apply the skill to the files themselves as well as the messages describing them. Preserve facts, conditions, links and the requested tone. Read the references required by the selected mode and perform the skill's final check. Preserve code behavior, identifiers, captured logs, verbatim quotations and machine-readable data.

The [Clarity hook](docs/clarity-hook.md) loads the skill into agent context and requests a final review. It does not certify writing quality or authorize external messages.

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
