import unittest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from agent_gym.science import mesh
from agent_gym.science import Venturi, run_path

class ScienceTests(unittest.TestCase):
    def test_dimension_constraints(self):
        spec = dict(inlet_diameter_mm=30, throat_diameter_mm=15, inlet_length_mm=20,
                    convergent_length_mm=30, throat_length_mm=15,
                    diffuser_length_mm=60, outlet_length_mm=20)
        self.assertEqual(Venturi(**spec).length_mm, 145)
        self.assertEqual(Venturi(**{**spec, "inlet_length_mm": 0, "outlet_length_mm": 0}).length_mm, 105)
        for value in [float("nan"), float("inf"), -1, True]:
            with self.assertRaises(ValueError):
                Venturi(**{**spec, "throat_diameter_mm": value})
        with self.assertRaises(ValueError):
            Venturi(**{**spec, "throat_diameter_mm": 31})

    def test_path_constraints(self):
        for value in ["../escape", "/tmp/test", "a"*31, "g"*32]:
            with self.assertRaises(ValueError):
                run_path(value)

    def test_mesh_failure_clears_stale_success_and_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            run_id = 'a'*32
            folder = Path(directory)/run_id
            folder.mkdir()
            spec = dict(inlet_diameter_mm=30, throat_diameter_mm=15, inlet_length_mm=20,
                        convergent_length_mm=30, throat_length_mm=15,
                        diffuser_length_mm=60, outlet_length_mm=20)
            (folder/'spec.json').write_text(json.dumps(spec))
            (folder/'mesh-status.json').write_text(json.dumps({'stage': 'mesh_complete'}))
            with patch('agent_gym.science.ROOT', Path(directory)), patch('agent_gym.science.invoke', side_effect=RuntimeError('failed fixture')):
                with self.assertRaises(RuntimeError):
                    mesh(run_id, 3)
            self.assertEqual(json.loads((folder/'mesh-status.json').read_text())['stage'], 'mesh_failed')
            self.assertFalse((folder/'.mesh-lock').exists())
