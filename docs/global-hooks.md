# Global Clarity and Asana hooks

Install these hooks at user scope to apply Clarity and the Asana one-ahead policy across Codex projects on the same execution host. Clarity also works in projectless chats. Asana uses the current workspace and verified source tasks to find the relevant queue; it never defaults an unrelated project to the workshop queue.

## Install and trust

From this checkout, run:

```sh
python3 scripts/install_global_hooks.py
```

The installer uses `$CODEX_HOME`, or `~/.codex` when it is unset. It:

- Copies the two Python handlers to `hooks/otmd-writing-asana/`, so they remain available after this checkout is removed.
- Adds nine handlers to the user-level `hooks.json`, preserving unrelated handlers. Reinstalling replaces this installation's registrations without adding duplicates.
- Keeps an existing global Clarity skill. If none exists, it copies the repository's Clarity skill and references to `skills/clarity/`.
- Backs up the previous hook file and installed scripts under `hook-backups/` and prints that path.

Open `/hooks` in the Codex CLI, review the nine global handlers, and approve their trust. Start or resume a session afterward. The installer does not edit trust hashes or approve hooks. A read-only registry check and passing tests do not prove that a live session has loaded or trusted them.

Global and project hooks both run when configured. This PR removes its project-level `.codex/hooks.json` registrations. Older branches may still contain them: remove only the duplicate Asana/Clarity registrations before using those branches with the global installation. Preserve unrelated hooks. See [Codex hook discovery and trust](https://learn.chatgpt.com/docs/hooks).

Install separately on each remote execution host if needed. This installer affects only the host where it runs. It does not configure Tailscale or other remote access.

## Behavior and scope

[Clarity](clarity-hook.md) covers reader-facing messages and prose in files. Its skill is loaded from the global skill directory, even outside a repository. The agent must still read required references and apply the review.

[Asana](asana-push-hook.md) tracks successful pushes in the active repository's remote-tracking reflogs. It retains pending updates until a task readback includes the full SHA. In projectless chats, verified Asana task completions can still request the next task. An unconfigured or inaccessible task queue is reported rather than guessed.

One-ahead permits one eligible follow-up per session, including when the working directory changes. It respects assignment, dependencies, review gates, user stops, and the current task's authorized scope. Neither hook wakes an idle agent or creates an independent service.

## Verify and update

```sh
python3 -m unittest discover -s tests -p 'test_*hook.py' -v
```

The tests use temporary user homes, real local Git pushes, and synthetic lifecycle events. They cover installation without clobbering other hooks or skills, projectless execution, workspace selection, and one-ahead limits across workspaces. They do not call Asana or establish live hook activation.

After updating the hook code, rerun the installer and review any changed definitions in `/hooks`. Installing is a local configuration change; pushing this PR does not update another host.

To remove the installation, remove only commands pointing to `hooks/otmd-writing-asana/` from the user-level `hooks.json`. Keep unrelated hooks and the Clarity skill. Keep pending Asana state until its updates are resolved; deleting state is not an acknowledgement. The backup path printed during installation holds the previous configuration and scripts for recovery.
