#!/usr/bin/env python3
"""Check a prompt data asset against a separately approved MAP (stdlib only)."""
import argparse
import ast
import json
from pathlib import Path
import sys

# When invoked by CI from the base checkout, load validation code from that checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CONTRACT = 'data_contract_components/contract_definition/object_images_contract_spec.json'
MARKER = '<!-- museum-prompt-map -->'


def read_json(path):
    return json.loads(path.read_text())


def within(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Contract paths must stay within the checkout.')
    return path


def check_profile(candidate_root, profile, prompt_path=None):
    violations = []
    def reject(rule, expected, actual, message):
        violations.append(dict(rule=rule, expected=expected, actual=actual, message=message))
    ref = profile
    if (not isinstance(profile.get('id'), str) or not profile['id']
            or not isinstance(profile.get('version'), str) or not profile['version']):
        raise ValueError('The MAP requires an identifier and version.')
    asset = prompt_path or ref['promptAssetResourceName']
    prompt = read_json(within(candidate_root, asset))
    if not isinstance(prompt, dict):
        raise ValueError('Prompt must be a JSON object.')
    if set(prompt) != {'instructions', 'semantics'}:
        reject('prompt.fields', ['instructions', 'semantics'], sorted(prompt), 'Only approved prompt fields are allowed.')
    if prompt.get('instructions') != ref['approved_instructions']:
        reject('prompt.instructions', ref['approved_instructions'], prompt.get('instructions'), 'Free-text instructions differ from the approved data contract.')
    semantics = prompt.get('semantics')
    if not isinstance(semantics, dict):
        raise ValueError('Prompt semantics must be a JSON object.')
    elements = profile['elements']
    keys = [element['id'] for element in elements]
    if len(set(keys)) != len(keys) or not keys:
        raise ValueError('MAP elements must have distinct, nonempty identifiers.')
    for element in elements:
        key = element['id']
        expected = element['required_value']
        is_list = element['value_type'] == 'array'
        valid_value = (isinstance(expected, list) and bool(expected)
                       and all(isinstance(v, str) and v.strip() for v in expected)
                       and len(expected) == len(set(expected))
                       and element.get('items_type') == 'string'
                       and element.get('unique_items') is True) if is_list else (
                           element['value_type'] == 'string' and isinstance(expected, str))
        if (element['prompt_path'] != 'semantics.' + key or element['required'] is not True
                or element['max_occurs'] != 1 or not valid_value
                or not isinstance(element['definition'], str)):
            raise ValueError('Unsupported MAP element constraint: ' + key)
        actual = semantics.get(key)
        matches = actual == expected
        if is_list:
            matches = (isinstance(actual, list) and all(isinstance(v, str) for v in actual)
                       and len(actual) == len(set(actual)) and set(actual) == set(expected))
        if not matches:
            message = element['definition']
            if is_list and isinstance(actual, list) and all(isinstance(v, str) for v in actual):
                message += '\nMissing approved categories: ' + json.dumps(sorted(set(expected) - set(actual)))
                message += '\nUnapproved categories: ' + json.dumps(sorted(set(actual) - set(expected)))
            reject(key, expected, actual, message)
    for key in sorted(set(semantics) - set(keys)):
        reject(key, 'no additional semantic setting', semantics[key], 'This setting is not in the approved MAP.')
    # Read the literal rule table without importing or executing candidate code.
    tree = ast.parse((candidate_root / 'sql_eval/prompts.py').read_text())
    tables = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == 'RULES' for target in node.targets)]
    if len(tables) != 1:
        raise ValueError('Expected one literal RULES table.')
    for element in elements:
        render_key = 'explicit_list' if element['value_type'] == 'array' else element['required_value']
        actual = tables[0].get(element['id'], {}).get(render_key)
        if actual != element['definition']:
            reject('render.' + element['id'], element['definition'], actual, 'Rendered rule text differs from the approved MAP.')
    return dict(status='fail' if violations else 'pass', asset=asset,
                map_id=profile['id'], map_version=profile['version'], violations=violations)


def check(policy_root, candidate_root, prompt_path=None):
    ref = read_json(policy_root / CONTRACT)['metadataApplicationProfile']
    profiles = [ref] if prompt_path else [ref, *ref.get('additionalProfiles', [])]
    if (len({p['id'] for p in profiles}) != len(profiles)
            or len({p['promptAssetResourceName'] for p in profiles}) != len(profiles)):
        raise ValueError('MAP profiles must have distinct identifiers and prompt assets.')
    reports = [check_profile(candidate_root, profile, prompt_path) for profile in profiles]
    violations = [dict(v, asset=r['asset']) for r in reports for v in r['violations']]
    linked_reports = []
    protected_files = ['scripts/check_prompt_map.py', 'sql_eval/prompts.py']
    for profile in profiles:
        if profile.get('linkedArt'):
            from scripts.linked_art_sculpture import evaluate, PROTECTED_FILES
            linked_report, _, _ = evaluate(policy_root, candidate_root, profile, prompt_path)
            linked_reports.append(linked_report)
            violations.extend(dict(v, asset=linked_report['asset']) for v in linked_report['violations'])
            protected_files.extend(PROTECTED_FILES)
    def reject(rule, expected, actual, message):
        violations.append(dict(rule=rule, expected=expected, actual=actual, message=message))
    # In PRs the base branch owns policy; changing prompt and policy together cannot evade it.
    if policy_root.resolve() != candidate_root.resolve():
        candidate_contract = read_json(within(candidate_root, CONTRACT))
        if candidate_contract.get('metadataApplicationProfile') != ref:
            reject('policy.change', 'approved MAP section', 'metadataApplicationProfile changed',
                   'The MAP section requires separate maintainer review.')
        for relative in dict.fromkeys(protected_files):
            if within(policy_root, relative).read_bytes() != within(candidate_root, relative).read_bytes():
                reject('policy.change', 'approved base-branch policy', relative,
                       'Policy or validator changes require separate maintainer review; this PR is checked against the base policy.')
    return dict(status='fail' if violations else 'pass', asset=reports[0]['asset'],
                map_id=ref['id'], map_version=ref['version'],
                checked_assets=[r['asset'] for r in reports], linked_art=linked_reports, violations=violations)


def markdown(report):
    lines = [MARKER, '## Prompt MAP: ' + report['status'].upper(), '',
             'The **Prompt MAP contract** check validates the prompt contract. '
             'It blocks merging only when required by the target branch rules.', '']
    for linked in report.get('linked_art', []):
        lines += [f"Linked Art object schema: {'PASS' if linked['schema_valid'] else 'FAIL'}; "
                  f"mapped records: {linked['mapped_records']}; sculpture identities after JSON-LD expansion: "
                  f"{linked['expanded_sculpture_count']} (expected {linked['expected_sculpture_count']}).", '']
    for item in report['violations']:
        # The workflow reporter escapes these values before posting them in a pre block.
        lines += [f"Rule: {item['rule']}", f"Expected: {json.dumps(item['expected'], ensure_ascii=False)}",
                  f"Actual: {json.dumps(item['actual'], ensure_ascii=False)}", item['message'], '']
    if not report['violations']:
        lines.append('The prompt satisfies the approved MAP. This does not establish model accuracy.')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy-root', type=Path, default=Path('.'))
    parser.add_argument('--candidate-root', type=Path, default=Path('.'))
    parser.add_argument('--prompt')
    parser.add_argument('--report', type=Path, default=Path('artifacts/prompt-map/report.json'))
    parser.add_argument('--markdown', type=Path, default=Path('artifacts/prompt-map/report.md'))
    args = parser.parse_args()
    try:
        report = check(args.policy_root, args.candidate_root, args.prompt)
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as error:
        report = dict(status='fail', violations=[dict(rule='input.invalid', expected='valid prompt, MAP and contract',
                                                     actual=str(error), message='The check failed closed.')])
    for path, contents in ((args.report, json.dumps(report, indent=2) + '\n'), (args.markdown, markdown(report))):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    print(markdown(report))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
