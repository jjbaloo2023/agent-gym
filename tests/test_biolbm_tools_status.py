import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from agent_gym import biolbm_tools


class JobStatusTests(unittest.TestCase):
    def _run_worker_fixture(self, returncode=0, timeout=False):
        process = Mock(pid=12345)
        process.wait.side_effect = (
            [subprocess.TimeoutExpired("fixture", 600), -9] if timeout else [returncode]
        )

        def start_worker(command, **kwargs):
            folder = Path(command[-1])
            results = folder / "results"
            results.mkdir()
            solver_state = "running" if timeout else "completed"
            (results / "status.json").write_text(json.dumps({"state": solver_state}))
            (results / "summary.json").write_text(json.dumps({"benchmark_passed": returncode == 0}))
            kwargs["stdout"].write("synthetic worker fixture\n")
            kwargs["stdout"].flush()
            return process

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checked = {"runnable": True, "config": {}}
            with patch.object(biolbm_tools, "ROOT", root), \
                    patch.object(biolbm_tools, "validate_case", return_value=checked), \
                    patch.object(biolbm_tools.subprocess, "Popen", side_effect=start_worker), \
                    patch.object(biolbm_tools.os, "killpg", create=True):
                result = biolbm_tools.run_case("benchmark", {})
                self.assertFalse((root / ".active-job").exists())
                inspected = biolbm_tools.inspect_run(result["run_id"])
                self.assertEqual(inspected, result)
                return result, process

    def test_completed_job_keeps_public_status_and_solver_status(self):
        result, _ = self._run_worker_fixture()
        self.assertEqual(result["status"], {"state": "completed", "returncode": 0})
        self.assertEqual(result["solver_status"]["state"], "completed")
        self.assertTrue(result["summary"]["benchmark_passed"])

    def test_worker_failure_is_not_hidden_by_completed_solver(self):
        result, _ = self._run_worker_fixture(returncode=1)
        self.assertEqual(result["status"]["state"], "failed")
        self.assertEqual(result["status"]["returncode"], 1)
        self.assertIn("synthetic worker fixture", result["status"]["log_tail"])
        self.assertEqual(result["solver_status"]["state"], "completed")
        self.assertFalse(result["summary"]["benchmark_passed"])

    def test_timeout_is_not_hidden_by_last_running_solver_status(self):
        result, process = self._run_worker_fixture(timeout=True)
        self.assertEqual(result["status"]["state"], "timed_out")
        self.assertEqual(result["status"]["timeout_seconds"], biolbm_tools.TIMEOUT_SECONDS)
        self.assertEqual(result["solver_status"]["state"], "running")
        self.assertEqual(process.wait.call_count, 2)

    def test_inspection_before_solver_output_keeps_job_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_id = "a" * 32
            folder = root / run_id
            folder.mkdir()
            (folder / "job-status.json").write_text(json.dumps({"state": "failed", "returncode": 1}))
            with patch.object(biolbm_tools, "ROOT", root):
                result = biolbm_tools.inspect_run(run_id)
            self.assertEqual(result["status"]["state"], "failed")
            self.assertNotIn("solver_status", result)


if __name__ == "__main__":
    unittest.main()
