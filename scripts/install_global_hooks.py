"""Install the reviewed hook scripts at user scope without approving their trust."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
OWNER = "otmd-writing-asana"


def install(home):
    home.mkdir(parents=True, exist_ok=True)
    destination = home / "hooks" / OWNER
    config = home / "hooks.json"
    previous = json.loads(config.read_text()) if config.exists() else {"hooks": {}}
    if not isinstance(previous.get("hooks"), dict):
        raise ValueError("Existing hooks.json has no hooks object; leaving it unchanged")
    skill = home / "skills/clarity"
    if skill.exists() and not (skill / "SKILL.md").is_file():
        raise ValueError("Existing global Clarity directory has no SKILL.md; repair it first")
    template = json.loads((ROOT / "scripts/global-hooks.json").read_text())
    # Validate before touching the installed files. Keep unrelated groups intact.
    for event, groups in previous["hooks"].items():
        if not isinstance(groups, list):
            raise ValueError(f"Invalid hook groups for {event}")
    backup = home / "hook-backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup.mkdir(parents=True, mode=0o700)
    if config.exists():
        shutil.copy2(config, backup / "hooks.json")
    if destination.exists():
        shutil.copytree(destination, backup / OWNER)
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("asana_push_hook.py", "clarity_hook.py"):
        shutil.copy2(ROOT / "scripts" / name, destination / name)
    if not skill.exists():
        skill.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ROOT / ".agents/skills/clarity", skill)
    for event, groups in template["hooks"].items():
        keep = []
        for group in previous["hooks"].get(event, []):
            remaining = [h for h in group.get("hooks", [])
                         if str(destination) not in h.get("command", "")]
            if remaining:
                keep.append({**group, "hooks": remaining})
        for group in groups:
            for handler in group["hooks"]:
                handler["command"] = handler["command"].format(
                    python=shlex.quote(sys.executable), hook_dir=shlex.quote(str(destination)))
        previous["hooks"][event] = keep + groups
    temporary = config.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(previous, indent=2) + "\n")
    temporary.replace(config)
    return {"config": str(config), "scripts": str(destination), "backup": str(backup),
            "trust": "Review the nine global handlers in /hooks, then start or resume a session."}


if __name__ == "__main__":
    home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()
    print(json.dumps(install(home), indent=2))
