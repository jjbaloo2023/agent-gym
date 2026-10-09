"""Regression checks for the inspectable CFD evidence and tamper rejection."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('cfd_evidence', ROOT/'scripts/verify-cfd-evidence.py')
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)
BUNDLE = ROOT/'evidence/cfd-interruption-v1'


class EvidenceTests(unittest.TestCase):
    def test_saved_run_recomputes_successfully(self):
        result = VERIFIER.verify(BUNDLE)
        self.assertTrue(result['passed'])
        self.assertEqual(result['restart_time'], 50)

    def test_modified_result_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory)/'bundle'
            shutil.copytree(BUNDLE, copy)
            with (copy/'verification.json').open('ab') as output:
                output.write(b' ')
            with self.assertRaisesRegex(ValueError, 'Manifest mismatch'):
                VERIFIER.verify(copy)

    def test_parent_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory)/'bundle'
            shutil.copytree(BUNDLE, copy)
            manifest = json.loads((copy/'manifest.json').read_text())
            manifest['files']['../outside'] = {'bytes': 0, 'sha256': ''}
            (copy/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Unsafe manifest path'):
                VERIFIER.verify(copy)

    def test_invalid_fields_are_rejected(self):
        for field in ['internalField nonuniform List<scalar> 2 (1);',
                      'internalField nonuniform List<scalar> 1 (1e999);']:
            with self.subTest(field=field), self.assertRaises(ValueError):
                VERIFIER.values(field)
