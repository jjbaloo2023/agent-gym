import math
import unittest
import importlib.util
HAS_CONFIG = importlib.util.find_spec("yaml") is not None
if HAS_CONFIG:
    from agent_gym.biolbm.config import Case, load_case


@unittest.skipUnless(HAS_CONFIG, "Install BioLBM extra")
class ConfigTests(unittest.TestCase):
    def test_case_and_memory(self):
        case = Case(reynolds_number=20)
        self.assertAlmostEqual(case.tau, 0.5 + 3*(32/(2*math.pi))*(0.05/math.sqrt(3))/20)
        self.assertEqual(case.estimate()["distribution_bytes_two_buffers"], 2*9*32**2*8)

    def test_reject_unsafe_or_invalid_inputs(self):
        for change in ({"mach_number": 0.2}, {"steps": True}, {"flow": "tank"},
                       {"reynolds_number": float("nan")}, {"reynolds_number": 1e8},
                       {"precision": "float16"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                Case(**change)

    def test_committed_cases(self):
        for path in ("benchmarks/biolbm/cases/taylor_green_2d/case.yaml", "benchmarks/biolbm/cases/taylor_green_3d/case.yaml"):
            self.assertGreater(load_case(path).tau, 0.51)
