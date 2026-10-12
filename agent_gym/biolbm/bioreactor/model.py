# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jophin Joseph
"""Experimental rotating immersed-solid forcing on Lettuce's D3Q19 core.

This is a smooth volumetric penalty, not a sharp-interface moving-wall
solver. Fluid populations exist inside the diffuse rotor. The rigid vessel
uses Lettuce's full-way bounce back. Neither torque nor tank flow is validated.
"""
import math
import numpy as np
import torch
import lettuce as lt
from .geometry import coordinates, interior


class VesselFlow(lt.Flow):
    def __init__(self, geometry, spacing, density, viscosity, rpm, mach, device="cpu"):
        self.geometry=geometry
        self.spacing=spacing
        self.omega=2*math.pi*rpm/60
        self.x,self.y,self.z=coordinates(geometry,spacing)
        if device == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA requested but unavailable')
        context=lt.Context(device=device,dtype=torch.float64,use_native=False)
        arrays=np.meshgrid(self.x,self.y,self.z,indexing='ij')
        self.positions=[context.convert_to_tensor(a) for a in arrays]
        self.fluid=context.convert_to_tensor(interior(geometry,*arrays),dtype=torch.bool)
        tip_speed=self.omega*geometry.impeller_diameter_m/2
        nu=viscosity/density
        units=lt.UnitConversion(reynolds_number=tip_speed*geometry.impeller_diameter_m/nu,
                                mach_number=mach,characteristic_length_pu=geometry.impeller_diameter_m,
                                characteristic_velocity_pu=tip_speed,
                                characteristic_length_lu=geometry.impeller_diameter_m/spacing,
                                characteristic_density_pu=density)
        super().__init__(context,list(self.fluid.shape),units,lt.D3Q19(),lt.QuadraticEquilibrium())
        self.wall=lt.BounceBackBoundary(~self.fluid)

    def initial_pu(self):
        shape=list(self.fluid.shape)
        return self.context.zero_tensor([1,*shape]),self.context.zero_tensor([3,*shape])

    @property
    def post_boundaries(self):
        return [self.wall]


class RotorForce(lt.Force):
    """Implicit penalty plus spatial Guo forcing; force is lattice force density.

    F = rho*alpha*(u_s-j/rho)/(1+alpha/2).
    The denominator accounts for the half-force velocity correction, avoiding
    an explicit stiff penalty update. alpha is a smooth solid fraction.
    """
    def __init__(self,flow,tau,acceleration=None):
        self.flow=flow;self.tau=tau
        self.force=torch.zeros_like(flow.j())
        self.fraction=torch.zeros_like(flow.rho()[0])
        self.impeller_fraction=self.fraction.clone()
        self.shaft_fraction=self.fraction.clone()
        self.dt=float(flow.units.convert_time_to_pu(1))
        self.ramp_seconds=0.05

    def smooth(self,distance):
        return torch.clamp(0.5-distance/self.flow.spacing,0,1)

    def update(self):
        flow=self.flow;g=flow.geometry;x,y,z=flow.positions
        time=flow.i*self.dt
        # Integrate the smooth spin-up speed exactly for orientation.
        r=min(time/self.ramp_seconds,1)
        speed_factor=0.5*(1-math.cos(math.pi*r))
        integrated=0.5*time-self.ramp_seconds/(2*math.pi)*math.sin(math.pi*r) if time<self.ramp_seconds else time-self.ramp_seconds/2
        angle=flow.omega*integrated
        radial=torch.sqrt(x*x+y*y)
        hub=self.smooth(torch.maximum(radial-g.hub_radius_m,torch.abs(z-g.impeller_height_m)-g.hub_height_m/2))
        shaft=self.smooth(torch.maximum(radial-g.shaft_radius_m,g.impeller_height_m+g.hub_height_m/2-z))
        impeller=hub
        pitch=math.radians(g.blade_pitch_deg)
        middle=(g.blade_inner_radius+g.blade_outer_radius)/2
        half_length=(g.blade_outer_radius-g.blade_inner_radius)/2
        for blade in range(g.blade_count):
            a=angle+2*math.pi*blade/g.blade_count
            radial_coordinate=x*math.cos(a)+y*math.sin(a)
            tangential=-x*math.sin(a)+y*math.cos(a)
            vertical=z-g.impeller_height_m
            chord=tangential*math.cos(pitch)+vertical*math.sin(pitch)
            normal=-tangential*math.sin(pitch)+vertical*math.cos(pitch)
            signed_distance=torch.maximum(torch.abs(radial_coordinate-middle)-half_length,
                                          torch.maximum(torch.abs(chord)-g.blade_chord_m/2,
                                                        torch.abs(normal)-g.blade_thickness_m/2))
            impeller=torch.maximum(impeller,self.smooth(signed_distance))
        self.impeller_fraction=impeller*flow.fluid
        self.shaft_fraction=shaft*(1-self.impeller_fraction)*flow.fluid
        self.fraction=torch.maximum(impeller,shaft)*flow.fluid
        # Tangential rigid-body velocity; positive omega is CCW from above.
        target=torch.stack([-flow.omega*speed_factor*y,flow.omega*speed_factor*x,torch.zeros_like(z)])
        target=flow.units.convert_velocity_to_lu(target)
        rho=flow.rho()
        alpha=self.fraction[None,...]
        self.force=rho*alpha*(target-flow.u())/(1+0.5*alpha)
        self.angle=angle
        self.rpm_actual=flow.omega*speed_factor*60/(2*math.pi)

    def source_term(self,u):
        stencil=self.flow.torch_stencil
        e_dot_u=torch.einsum('qd,d...->q...',stencil.e,u)
        e_dot_f=torch.einsum('qd,d...->q...',stencil.e,self.force)
        u_dot_f=(u*self.force).sum(dim=0)
        weights=stencil.w.reshape(-1,1,1,1)
        return (1-1/(2*self.tau))*weights*((e_dot_f-u_dot_f)/stencil.cs**2+e_dot_u*e_dot_f/stencil.cs**4)

    def u_eq(self,flow=None):
        return self.force/(2*self.flow.rho())

    @property
    def ueq_scaling_factor(self): return 0.5
    def native_available(self): return False
    def native_generator(self,index): raise NotImplementedError('Native compiled kernels are not supported for this force')

    def velocity_si(self):
        return self.flow.units.convert_velocity_to_pu(self.flow.u()+self.u_eq())

    def torque_si(self):
        x,y,_=self.flow.positions
        force_per_cell=self.force*self.flow.units.characteristic_density_pu*self.flow.spacing**4/self.dt**2
        torque=x*force_per_cell[1]-y*force_per_cell[0]
        return float(torque.sum())
