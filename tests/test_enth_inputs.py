"""Preflight regressions for legacy lipid inputs; no MD or downloads."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('enth_validation', Path(__file__).parents[1] / 'scripts/enth_validation.py')
enth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(enth)
analysis_spec = importlib.util.spec_from_file_location('enth_analysis', Path(__file__).parents[1] / 'scripts/enth_analysis.py')
analysis = importlib.util.module_from_spec(analysis_spec)
analysis_spec.loader.exec_module(analysis)


class EnthInputs(unittest.TestCase):
    def test_infinite_dielectric_parameter_is_not_failed_energy(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'em.log'
            path.write_text('   epsilon-rf = inf\nPotential Energy = -1234\n')
            self.assertFalse(analysis.parse_log(path)['has_nan_or_inf'])
            path.write_text('   epsilon-rf = inf\nPotential Energy = nan\n')
            self.assertTrue(analysis.parse_log(path)['has_nan_or_inf'])

    def test_contact_audit_uses_periodic_images(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'test.gro'
            atoms = ''.join(f'{i:5d}{"POPC":<5}{"C1":>5}{i:5d}{x:8.3f}{1.0:8.3f}{1.0:8.3f}\n'
                            for i, x in [(1, 0.05), (2, 9.95)])
            path.write_text('Test\n2\n' + atoms + '10 10 10\n')
            audit = analysis.contact_audit(path)
            self.assertAlmostEqual(audit['minimum_distance_nm_within_radius'], 0.1)
            self.assertEqual(audit['intermolecular_heavy_pairs_below_0_18nm'], 1)

    def test_clean_exit_does_not_imply_requested_duration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'nvt.log').write_text('Received the TERM signal\nFinished mdrun\n')
            (root / 'nvt.gro').write_text('System t= 4.000\n0\n1 1 1\n')
            with self.assertRaisesRegex(RuntimeError, 'stopped early'):
                enth.validate_stage(root, 'nvt', 10.0)

    def test_checkpoint_only_stop_is_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'nvt.log').write_text('Run time exceeded\nFinished mdrun\n')
            (root / 'nvt.cpt').write_bytes(b'checkpoint-placeholder')
            with self.assertRaisesRegex(RuntimeError, 'checkpoint continuation'):
                enth.validate_stage(root, 'nvt', 10.0)

    def test_final_coordinates_without_title_time_use_log_endpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'nvt.log').write_text('           Step           Time\n           5000       10.00000\nFinished mdrun\n')
            (root / 'nvt.gro').write_text('Protein in water\n0\n1 1 1\n')
            self.assertEqual(enth.validate_stage(root, 'nvt', 10.0)['observed_duration_ps'], 10.0)

    def test_convergence_does_not_override_constraint_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'em.log').write_text('Constraint error in algorithm Lincs at step 21\nSteepest Descents converged to Fmax < 1000 in 766 steps\n')
            with self.assertRaisesRegex(RuntimeError, 'constraint warning'):
                enth.validate_stage(root, 'em')

    def test_relaxation_followed_by_constrained_minimization(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'stage.mdp'
            enth.write_mdp(path, 'min_relax')
            self.assertIn('constraints = none', path.read_text())
            enth.write_mdp(path, 'min')
            self.assertIn('constraints = h-bonds', path.read_text())
            self.assertIn('emstep = 0.001', path.read_text())

    def test_explicit_periodic_cell_required(self):
        self.assertEqual(enth.pdb_box(['REMARK System Size: 66.1151 X 66.1151 X 63.73387']),
                         (66.1151, 66.1151, 63.73387))
        with self.assertRaises(RuntimeError):
            enth.pdb_box(['REMARK coordinates alone do not establish the periodic cell'])

    def test_legacy_numeric_psf_types_use_atomic_mass(self):
        body = '''PSF
       2 !NATOM
       1 POPC 1 POPC P1 140  1.5 30.974 0
       2 POPC 1 POPC O1 120 -1.5 15.999 0
       1 !NBOND
       1 2
       0 !NTHETA
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'lipid.psf'
            path.write_text(body)
            types, edges, _ = enth.parse_psf_popc_graph(path)
        mapping = enth.graph_isomorphism(types, edges, {'P': 'PL', 'O11': 'O2L'}, {('O11', 'P')})
        self.assertEqual(mapping, {'P1': 'P', 'O1': 'O11'})

    def test_incompatible_bond_graph_is_rejected(self):
        with self.assertRaises(RuntimeError):
            enth.graph_isomorphism({'C1': 'C', 'O1': 'O'}, {('C1', 'O1')},
                                   {'C': 'C', 'O': 'O'}, set())

    def test_lipid_renaming_preserves_coordinates(self):
        line = 'ATOM     20  P1  POPC    1     -26.937  -5.611 -16.168  1.00-17.63      POPC'
        result, count = enth.rename_archive_popc([line], {'P1': 'P'}, {'P1': 'P'})
        self.assertEqual(count, 1)
        self.assertEqual(result[0][:12], line[:12])
        self.assertEqual(result[0][16:], line[16:])
        self.assertEqual(enth.atom_name(result[0]), 'P')


if __name__ == '__main__':
    unittest.main()
