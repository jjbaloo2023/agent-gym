"""Geometry invariants used in crystal-pose reconstruction."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('enth_colab',Path(__file__).parents[1]/'scripts/prepare-enth-colab.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class CrystalGeometry(unittest.TestCase):
    def test_fit_preserves_chirality_even_for_mirrored_target(self):
        source=np.array([[0.,0,0],[1,0,0],[0,2,0],[0,0,3]])
        target=source*np.array([-1,1,1])
        rotation,translation=module.fit(source,target)
        self.assertAlmostEqual(np.linalg.det(rotation),1.0)
        self.assertGreater(np.linalg.norm(source@rotation+translation-target),0.1)

    def test_periodic_contact_across_both_cell_edges(self):
        distance,delta=module.closest(np.array([[0.1,0.1,1.]]),np.array([[9.9,9.9,1.]]),np.array([10.,10.,10.]))
        self.assertAlmostEqual(distance,np.sqrt(0.08))
        np.testing.assert_allclose(delta,[0.2,0.2,0.0])


if __name__=='__main__':unittest.main()
