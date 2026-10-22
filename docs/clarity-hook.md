# Clarity for reader-facing text

The Clarity hook loads the user's global writing skill into the agent's context and requests a final review before a turn ends. It applies to chat replies and progress updates, PR titles and descriptions, review comments, commit messages, Asana notes, documentation, UI copy, comments, docstrings, user-visible strings in source files, and messages written through tools. Review the prose in the files themselves, not just their PR descriptions.

## Activation

Install using the [global setup](global-hooks.md), then open `/hooks` in the Codex CLI and review and trust the five global Clarity handlers. Start or resume the session after approval. Trust applies to the hook definitions; installation alone does not activate them. See the [official hook trust instructions](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks).

## What runs

- `SessionStart`, `UserPromptSubmit`, and `SubagentStart` load the full `$CODEX_HOME/skills/clarity/SKILL.md` (normally `~/.codex/skills/clarity/SKILL.md`). The agent selects the appropriate mode and reads its required references. `SessionStart` also runs after compaction, restoring the guidance when context is reduced.
- `PreToolUse` supplies a reminder for all supported tools, including shell commands, file edits and connectors. It asks the agent to check prose before writing it. It does not inspect or rewrite tool payloads, and it does not block a publication until a quality check has passed.
- `Stop` requests one Clarity review continuation. On a continuation already triggered by any Stop hook, it allows the turn to end. The review must not repost external messages or repeat completed writes.

The hook reads the user-level skill independently of the working directory and emits JSON on standard output. It stores no state, reads no credentials or transcript, sends no messages, and starts no background service. If the skill is missing or empty, it reports the problem and requests one repair pass at Stop. Tool calls remain available so the agent can restore the file.

## Limits

This hook makes Clarity part of the writing process; it cannot establish that prose is accurate or well written. The agent must still apply the skill, read the appropriate references, and check its work. It must not claim a review solely because the hook ran.

A final review cannot retract progress messages or external text already sent. The pre-tool reminder is guidance, not a publication gate. Some specialized tools may not run lifecycle hooks. Untrusted hooks are skipped, and hooks cannot wake an idle session. These limits follow the [documented hook behavior](https://learn.chatgpt.com/docs/hooks).

When reviewing prose inside source files, preserve code behavior and identifiers. Keep machine-readable values, captured logs, verbatim quotations, facts, conditions and links intact. Clarity does not grant permission to send messages or expand the task. The user-level configuration applies to all projects and projectless chats on that execution host. Remote hosts need their own installation.

## Verification

Run `python3 -m unittest discover -s tests -v` from the repository root. The Development hooks workflow runs the hook tests on relevant PR changes. The tests exercise skill loading through the script's JSON interface, tool reminders without payload changes, missing and empty skill files, bounded Stop continuation, and coexistence with the Asana hook. They verify hook behavior, not writing quality or trust approval in a live session.
