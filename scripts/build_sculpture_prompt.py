#!/usr/bin/env python3
"""Embed the Sculpture entry from the pinned local Linked Art documentation."""
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sql_eval.common import read_json, write_json


def from_local_docs(root=ROOT):
    folder = root / 'vendor/linked-art/guidance'
    manifest = read_json(folder / 'manifest.json')
    if set(manifest['files']) != {'recommended-vocabulary.md', 'LICENSE'}:
        raise ValueError('The pinned documentation and license are required.')
    for name, details in manifest['files'].items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != details['sha256']:
            raise ValueError('Pinned Linked Art documentation changed: ' + name)
    source = (folder / 'recommended-vocabulary.md').read_text()
    section = source.split('### Object Types\n', 1)[1].split('\n### ', 1)[0]
    entries = [[cell.strip() for cell in line.strip().strip('|').split('|')]
               for line in section.splitlines() if line.startswith('|')]
    rows = [row for row in entries if row[0] == 'Sculpture']
    if len(rows) != 1 or len(rows[0]) != 3 or rows[0][1] != 'aat:300047090':
        raise ValueError('Expected the pinned Sculpture vocabulary entry.')
    name, identifier, description = rows[0]
    uri = 'http://vocab.getty.edu/aat/' + identifier.split(':')[1]
    prompt = read_json(root / 'eval/linked-art-comparison/local.json')
    prompt['instructions'] += (
        '\nLinked Art reference, embedded from the local recommended vocabulary (Object Types):\n'
        f'{name} ({uri}): {description}\n'
        'Workshop application: use the supplied source-category mapping for membership.')
    return prompt


if __name__ == '__main__':
    write_json(ROOT / 'eval/linked-art-comparison/sculpture-only.json', from_local_docs())
