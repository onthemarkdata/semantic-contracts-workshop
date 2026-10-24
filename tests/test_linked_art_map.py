"""Exercise upstream schemas/context separately from local semantic constraints."""
import copy
import json
from pathlib import Path
import shutil
import socket
import tempfile
import unittest
from unittest.mock import patch

from pyld import jsonld
from scripts.check_prompt_map import check
from scripts.linked_art_sculpture import (
    ARTWORK, CONTEXT, E22, P2, SCULPTURE, export_records, resources, validate_records,
)
from tests.test_prompt_map import candidate, write

ROOT = Path(__file__).resolve().parents[1]
PROMPT = 'eval/prompts/linked-art-sculpture.json'


class LinkedArtTests(unittest.TestCase):
    def setUp(self):
        self.prompt = json.loads((ROOT / PROMPT).read_text())
        self.source = [
            {'objectID': 1, 'classification': 'Sculpture', 'title': 'A figure'},
            {'objectID': 2, 'classification': 'Wood-Sculpture', 'title': 'A carved figure'},
            {'objectID': 3, 'classification': '', 'title': 'Unclassified'},
            {'objectID': 4, 'classification': 'Bronzes', 'title': 'Unmapped'},
        ]

    def test_official_schema_and_jsonld_context_work_without_network(self):
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')):
            records = export_records(self.source, self.prompt)
            result, expanded = validate_records(records, ROOT)
        self.assertEqual(len(records), 2)
        self.assertTrue(result['schema_valid'])
        self.assertEqual(result['expanded_sculpture_count'], 2)
        self.assertIn(E22, expanded[0]['@type'])
        self.assertTrue(any(c['@id'] == SCULPTURE for c in expanded[0][P2]))

    def test_artwork_uri_passes_schema_but_is_not_sculpture(self):
        self.prompt['semantics']['linked_art_sculpture_type'] = ARTWORK
        records = export_records(self.source, self.prompt)
        self.assertEqual(records[0]['classified_as'][0]['_label'], 'Sculpture')
        result, _ = validate_records(records, ROOT)
        self.assertTrue(result['schema_valid'])
        self.assertEqual(result['expanded_sculpture_count'], 0)

    def test_digital_object_fails_physical_object_schema(self):
        self.prompt['semantics']['linked_art_entity_type'] = 'DigitalObject'
        result, _ = validate_records(export_records(self.source, self.prompt), ROOT)
        self.assertFalse(result['schema_valid'])
        self.assertEqual(result['schema_invalid_records'], 2)
        self.assertEqual(result['expanded_sculpture_count'], 0)

    def test_display_labels_do_not_decide_category_identity(self):
        records = export_records(self.source, self.prompt)
        for record in records:
            record['classified_as'][0]['_label'] = 'A different display label'
        result, _ = validate_records(records, ROOT)
        self.assertTrue(result['schema_valid'])
        self.assertEqual(result['expanded_sculpture_count'], 2)

    def test_collection_membership_does_not_infer_artwork(self):
        for record in export_records(self.source, self.prompt):
            self.assertNotIn(ARTWORK, [c['id'] for c in record['classified_as']])

    def test_unapproved_context_cannot_be_fetched(self):
        records = export_records(self.source, self.prompt)
        records[0]['@context'] = 'https://example.org/unapproved-context'
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')):
            with self.assertRaises(jsonld.JsonLdError):
                validate_records(records, ROOT)

    def test_upstream_snapshot_changes_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'vendor/linked-art', root / 'vendor/linked-art')
            path = root / 'vendor/linked-art/object.json'
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'Pinned Linked Art resource changed'):
                resources(root)

    def test_pr_cannot_weaken_its_own_upstream_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate(root)
            path = root / 'vendor/linked-art/object.json'
            path.write_text('{}')
            result = check(ROOT, root)
            self.assertTrue(result['linked_art'][0]['schema_valid'])
            self.assertTrue(any(v['rule'] == 'policy.change' and
                                v['actual'] == 'vendor/linked-art/object.json'
                                for v in result['violations']))

    def test_swapped_uri_fails_declaration_and_expanded_identity_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate(root)
            prompt = copy.deepcopy(self.prompt)
            prompt['semantics']['linked_art_sculpture_type'] = ARTWORK
            write(root / PROMPT, prompt)
            result = check(ROOT, root)
            self.assertEqual({v['rule'] for v in result['violations']},
                             {'linked_art_sculpture_type', 'linked_art.sculpture_identity'})
            self.assertTrue(result['linked_art'][0]['schema_valid'])
            self.assertEqual(result['linked_art'][0]['mapped_records'], 296)
            self.assertEqual(result['linked_art'][0]['expanded_sculpture_count'], 0)
