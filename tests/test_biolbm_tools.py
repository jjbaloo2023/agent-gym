import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from agent_gym import biolbm_tools


class PathTests(unittest.TestCase):
    def test_reject_foreign_paths(self):
        for value in ('../escape', '/tmp', 'g'*32, 'a'*31):
            with self.assertRaises(ValueError):
                biolbm_tools._run_path(value)

    def test_reject_unknown_kind(self):
        with self.assertRaises(ValueError):
            biolbm_tools.validate_case('shell', {})


@unittest.skipUnless(importlib.util.find_spec('lettuce'), 'Install BioLBM extra')
class WorkerTests(unittest.TestCase):
    def test_bounds_and_water_rejection(self):
        for kind, config in [('benchmark', {'steps': 2001}), ('vessel', {'threads': 3})]:
            with self.assertRaises(ValueError):
                biolbm_tools.validate_case(kind, config)
        water = biolbm_tools.validate_case('vessel', {})
        self.assertFalse(water['runnable'])
        self.assertEqual(water['config']['viscosity_pa_s'], 0.001)

    def test_bounded_run_artifacts_and_lock_release(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(biolbm_tools, 'ROOT', Path(temp)):
            result = biolbm_tools.run_case('benchmark', {'steps': 10})
            self.assertEqual(result['status']['state'], 'completed')
            self.assertTrue(result['summary']['benchmark_passed'])
            self.assertFalse((Path(temp)/'.active-job').exists())
            self.assertEqual(biolbm_tools.inspect_run(result['run_id'])['status']['state'], 'completed')

    def test_existing_lock_prevents_second_run(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(biolbm_tools, 'ROOT', Path(temp)):
            (Path(temp)/'.active-job').mkdir()
            with self.assertRaises(FileExistsError):
                biolbm_tools.run_case('benchmark', {'steps': 1})
