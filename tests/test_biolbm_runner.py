import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
if importlib.util.find_spec("lettuce"):
    from agent_gym.biolbm.config import Case
    from agent_gym.biolbm.runner import run


@unittest.skipUnless(importlib.util.find_spec("lettuce"), "Install solver extra for integration tests")
class RunnerTests(unittest.TestCase):
    def test_analytical_2d_and_output_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "run"
            result = run(Case(), output)
            self.assertTrue(result["benchmark_passed"])
            self.assertLess(result["final"]["relative_velocity_l2_error"], 0.01)
            self.assertLess(result["final"]["relative_mass_drift"], 1e-10)
            self.assertTrue(list(output.glob("*.vtr")))
            self.assertTrue((output / "checkpoint.npz").exists())
            self.assertEqual(json.loads((output / "status.json").read_text())["state"], "completed")
            with self.assertRaises(FileExistsError):
                run(Case(), output)

    def test_3d_smoke_is_not_analytical_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run(Case(flow="taylor_green_3d", resolution=16, reynolds_number=10, steps=5), Path(temp)/"run")
            self.assertIsNone(result["benchmark_passed"])
            self.assertLess(result["final"]["relative_mass_drift"], 1e-10)

    def test_missing_cuda_records_failure(self):
        import torch
        if torch.cuda.is_available():
            self.skipTest("Requires a CPU-only runtime")
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/"run"
            with self.assertRaisesRegex(RuntimeError, "CUDA requested"):
                run(Case(device="cuda"), output)
            self.assertEqual(json.loads((output/"status.json").read_text())["state"], "failed")
