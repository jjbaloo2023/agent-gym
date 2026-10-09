import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import os
from agent_gym.core import PipeEnv, PipeTask, run, atomic_json

class CoreTests(unittest.TestCase):
    def test_transient_checkpoint_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            replace = os.replace
            calls = []
            def locked_once(source, destination):
                calls.append(1)
                if len(calls) == 1:
                    raise PermissionError("temporary lock")
                return replace(source, destination)
            with patch("agent_gym.core.os.replace", side_effect=locked_once):
                atomic_json(path, {"steps": 3})
            self.assertEqual(json.loads(path.read_text()), {"steps": 3})
            self.assertEqual(len(calls), 2)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_physical_reference(self):
        task = PipeTask()
        radius = (8 * task.viscosity_pa_s * task.length_m * task.flow_m3_s
                  / (math.pi * task.target_drop_pa)) ** 0.25
        result = task.evaluate(radius)
        self.assertAlmostEqual(result["pressure_drop_pa"], task.target_drop_pa)
        self.assertAlmostEqual(result["reward"], 1.0)

    def test_invalid_and_exhausted(self):
        env = PipeEnv(budget=2)
        initial = env.radius
        for value in [float("nan"), -1]:
            _, reward, _, info = env.step(value)
            self.assertFalse(info["accepted"])
            self.assertEqual(reward, -1)
        self.assertEqual(env.radius, initial)
        with self.assertRaises(RuntimeError):
            env.step(initial)

    def test_resume_matches_uninterrupted(self):
        with tempfile.TemporaryDirectory() as directory:
            full, split = Path(directory) / "full", Path(directory) / "split"
            run(full, 80, 7)
            run(split, 13, 7)
            run(split, 80, 7, resume=True)
            a = json.loads((full / "checkpoint.json").read_text())
            b = json.loads((split / "checkpoint.json").read_text())
            for key in ["history", "rng_state", "radius_m", "metrics", "steps"]:
                self.assertEqual(a[key], b[key])
            rewards = [row["candidate"]["reward"] for row in a["history"] if row["accepted"]]
            self.assertEqual(rewards, sorted(rewards))
            self.assertGreater(a["metrics"]["reward"], 0.98)

    def test_checkpoint_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            run(directory, 5)
            with self.assertRaises(FileExistsError):
                run(directory, 5)
            with self.assertRaises(ValueError):
                run(directory, 10, seed=2, resume=True)
            with self.assertRaises(ValueError):
                run(directory, 10, resume=True, task=PipeTask(target_drop_pa=5))
            with self.assertRaises(ValueError):
                run(directory, 4, resume=True)

if __name__ == "__main__":
    unittest.main()
