"""Portable checkpoint preflight parsing; no MD or external downloads."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('restart', Path(__file__).parents[1]/'scripts/prepare-enth-restart.py')
restart = importlib.util.module_from_spec(spec); spec.loader.exec_module(restart)


class RestartPreflight(unittest.TestCase):
    def test_observed_gromacs_2023_checkpoint_header(self):
        result = restart.checkpoint_fields('#atoms = 39045\nstep = 4200\nt = 8.400000\n')
        self.assertEqual(result['natoms'], 39045)

    def test_checkpoint_time_is_observed_not_assumed(self):
        result = restart.checkpoint_fields('step = 4200\nt = 8.400000\nnatoms = 39045\n')
        self.assertEqual(result, {'step':4200, 't':8.4, 'natoms':39045})

    def test_missing_checkpoint_state_is_rejected(self):
        with self.assertRaises(RuntimeError): restart.checkpoint_fields('step = 4200\nnatoms = 39045\n')

    def test_oversized_system_is_rejected(self):
        with self.assertRaises(RuntimeError): restart.checkpoint_fields('step = 0\nt = 0\nnatoms = 100001\n')


if __name__ == '__main__': unittest.main()
