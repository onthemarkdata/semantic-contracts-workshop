"""Load Clarity for reader-facing text and request one final review per turn."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path('.agents/skills/clarity/SKILL.md')
LOAD_EVENTS = {'SessionStart', 'UserPromptSubmit', 'SubagentStart'}
SCOPE = (
    'Apply Clarity to all text you write for people to read: chat replies and progress '
    'updates, PR titles/descriptions/reviews, commit messages, Asana notes, documentation, '
    'UI copy, comments, docstrings, user-visible strings in source files, and messages sent through tools. Preserve facts, attribution, links, '
    'conditions, and the requested tone. Preserve code behavior, identifiers, machine-readable payloads, '
    'verbatim quotations, and captured logs. Review prose inside files as well as the messages describing those files. '
    'Choose the appropriate Clarity mode and read its required references. '
    'For routine factual updates, use the available evidence; do not invent facts or '
    'ask for an interview when no author-specific information is missing. '
    'Check prose before saving or publishing it. Clarity does not authorize sending messages.'
)
REVIEW = (
    'Apply the Clarity final check to the reader-facing text from this turn. '
    'Fix any material problem in the draft before finishing: unsupported claims, lost '
    'conditions, vague wording, unnecessary repetition, or a mismatch with the reader. '
    'Preserve factual evidence and links. Do not repost external messages or repeat '
    'completed writes just to demonstrate the check. This hook cannot retract text '
    'already sent. If nothing needs changing, finish concisely. '
    'Do not claim a Clarity review unless you actually performed it.'
)


def handle(root, event):
    kind = event.get('hook_event_name')
    if kind not in LOAD_EVENTS | {'PreToolUse', 'Stop'}:
        return {}
    skill = root / SKILL
    try:
        source = skill.read_text()
        if not source.strip():
            raise ValueError('skill file is empty')
    except (OSError, ValueError) as error:
        message = f'Clarity could not load {skill}: {error}. Restore the skill before writing prose.'
        if kind == 'Stop' and not event.get('stop_hook_active'):
            return {'decision': 'block', 'reason': message}
        return {'systemMessage': message}
    if kind in LOAD_EVENTS:
        return {'hookSpecificOutput': {'hookEventName': kind,
                'additionalContext': f'{SCOPE}\n\nClarity skill: {skill}\n\n{source}'}}
    if kind == 'PreToolUse':
        return {'hookSpecificOutput': {'hookEventName': kind,
                'additionalContext': f'Clarity applies to reader-facing prose in tool writes. {SCOPE}\nSkill: {skill}'}}
    if event.get('stop_hook_active'):
        return {}
    return {'decision': 'block', 'reason': f'{REVIEW}\nSkill: {skill}'}


def main():
    print(json.dumps(handle(ROOT, json.load(sys.stdin))))


if __name__ == '__main__':
    main()
