import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
HAS_GEOMETRY = all(importlib.util.find_spec(m) for m in ("numpy", "yaml"))
if HAS_GEOMETRY:
    import numpy as np
    from agent_gym.biolbm.bioreactor.geometry import Geometry,coordinates,interior,surfaces,write_stl
    from agent_gym.biolbm.bioreactor.workflow import Settings


@unittest.skipUnless(HAS_GEOMETRY, "Install BioLBM extra")
class GeometryTests(unittest.TestCase):
    def test_capacity_and_liquid_volume(self):
        g=Geometry()
        capacity=g.hemisphere_volume+math.pi*g.vessel_radius_m**2*(g.vessel_height-g.vessel_radius_m)
        self.assertAlmostEqual(capacity,0.005)
        shaft_volume=math.pi*g.shaft_radius_m**2*(g.fill_height-g.impeller_height_m-g.hub_height_m/2)
        hub_volume=math.pi*g.hub_radius_m**2*g.hub_height_m
        liquid=g.hemisphere_volume+math.pi*g.vessel_radius_m**2*(g.fill_height-g.vessel_radius_m)-shaft_volume-hub_volume-g.blade_volume
        self.assertAlmostEqual(liquid,0.003)
        vertices=np.concatenate(surfaces(g)['impeller'])
        self.assertLessEqual(np.linalg.norm(vertices[:,:2],axis=1).max(),g.impeller_diameter_m/2+1e-12)
        self.assertAlmostEqual(g.impeller_height_m,0.0508)

    def test_closed_lattice_envelope_and_refinement(self):
        g=Geometry();errors=[]
        envelope=g.hemisphere_volume+math.pi*g.vessel_radius_m**2*(g.fill_height-g.vessel_radius_m)
        for dx in [0.004,0.002]:
            axes=coordinates(g,dx);mask=interior(g,*np.meshgrid(*axes,indexing='ij'))
            self.assertFalse(mask[0,:,:].any());self.assertFalse(mask[-1,:,:].any())
            self.assertFalse(mask[:,:,0].any());self.assertFalse(mask[:,:,-1].any())
            errors.append(abs(mask.sum()*dx**3-envelope))
        self.assertLess(errors[1],errors[0])
        self.assertLess(errors[1]/envelope,0.01)

    def test_water_mapping_is_rejected_without_changing_viscosity(self):
        water=Settings();scaling=water.scaling(Geometry())
        self.assertFalse(scaling['passes_tau_envelope'])
        self.assertAlmostEqual(water.viscosity_pa_s,0.001)
        demo=Settings(viscosity_pa_s=0.1)
        self.assertTrue(demo.scaling(Geometry())['passes_tau_envelope'])


@unittest.skipUnless(importlib.util.find_spec('lettuce'),'Requires solver extra')
class ForceTests(unittest.TestCase):
    def test_spatial_guo_force_moments_and_rotation(self):
        import torch
        from agent_gym.biolbm.bioreactor.model import VesselFlow,RotorForce
        torch.set_num_threads(2)
        flow=VesselFlow(Geometry(),0.008,998,1.0,180,0.1)
        force=RotorForce(flow,flow.units.relaxation_parameter_lu)
        # At startup rotor is stationary and equilibrium is undisturbed.
        force.update();self.assertEqual(float(force.force.abs().max()),0)
        flow.i=100;force.update()
        u=flow.u()+force.u_eq()
        source=force.source_term(u)
        self.assertLess(float(source.sum(dim=0).abs().max()),1e-12)
        first=torch.einsum('qd,q...->d...',flow.torch_stencil.e,source)
        expected=(1-1/(2*force.tau))*force.force
        self.assertLess(float((first-expected).abs().max()),1e-12)
        self.assertGreater(force.torque_si(),0)
        # CCW drives positive y velocity at positive x.
        positive_x=(flow.positions[0]>0)&(force.fraction>0.1)&flow.fluid
        self.assertGreater(float(force.force[1][positive_x].mean()),0)
