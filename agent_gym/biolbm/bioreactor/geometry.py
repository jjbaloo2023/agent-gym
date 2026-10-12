# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jophin Joseph
"""Synthetic rounded vessel and pitched paddle, in SI metres.

The CAD triangle mesh is for inspection. The solver uses analytic geometry
on a Cartesian lattice, not tetrahedra or the STL surface triangles.
"""
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import numpy as np


@dataclass(frozen=True)
class Geometry:
    capacity_m3: float = 0.005
    working_volume_m3: float = 0.003
    vessel_radius_m: float = 0.080
    impeller_diameter_m: float = 2.36 * 0.0254
    impeller_height_m: float = 2 * 0.0254
    shaft_radius_m: float = 0.003
    hub_radius_m: float = 0.006
    hub_height_m: float = 0.010
    blade_count: int = 4
    blade_chord_m: float = 0.012
    blade_thickness_m: float = 0.002
    blade_pitch_deg: float = 45.0

    @property
    def hemisphere_volume(self):
        return 2 * math.pi * self.vessel_radius_m**3 / 3

    @property
    def vessel_height(self):
        return self.vessel_radius_m + (self.capacity_m3-self.hemisphere_volume)/(math.pi*self.vessel_radius_m**2)

    @property
    def blade_inner_radius(self):
        return self.hub_radius_m

    @property
    def blade_outer_radius(self):
        # Keep the entire blade (including pitch/chord corners) within stated OD.
        tip = self.impeller_diameter_m/2
        lateral = (self.blade_chord_m*math.cos(math.radians(self.blade_pitch_deg))
                   + self.blade_thickness_m*math.sin(math.radians(self.blade_pitch_deg)))/2
        return math.sqrt(tip**2-lateral**2)

    @property
    def blade_volume(self):
        return self.blade_count*(self.blade_outer_radius-self.blade_inner_radius)*self.blade_chord_m*self.blade_thickness_m

    @property
    def fill_height(self):
        # Fluid-volume contract: deduct analytic solids displacement.
        # Shaft begins at the hub upper face; blades start at hub outer radius.
        area = math.pi*self.vessel_radius_m**2
        shaft_area = math.pi*self.shaft_radius_m**2
        hub_volume = math.pi*self.hub_radius_m**2*self.hub_height_m
        shaft_start = self.impeller_height_m+self.hub_height_m/2
        return (self.working_volume_m3-self.hemisphere_volume+area*self.vessel_radius_m
                +hub_volume+self.blade_volume-shaft_area*shaft_start)/(area-shaft_area)

    def details(self):
        return {**asdict(self), 'vessel_height_m':self.vessel_height, 'fill_height_m':self.fill_height,
                'volume_definition':'3 L liquid after analytic hub, shaft, and blade displacement; vessel capacity before internals',
                'shape':'hemispherical bottom plus cylinder; synthetic proportions; no baffles',
                'rotation_convention':'positive about +z is counterclockwise viewed from above',
                'surface_model':'closed rigid lid at the liquid level; headspace not simulated'}


def coordinates(g, spacing):
    """Cell centres with a solid padding layer enclosing all fluid."""
    n = math.ceil(2*g.vessel_radius_m/spacing)+4
    x = (np.arange(n)-(n-1)/2)*spacing
    z = (np.arange(math.ceil(g.fill_height/spacing)+4)-1.5)*spacing
    return x, x.copy(), z


def interior(g, x, y, z):
    radius_squared = x*x+y*y
    inside_bottom = radius_squared+(z-g.vessel_radius_m)**2 < g.vessel_radius_m**2
    return ((z > 0)&(z < g.fill_height)&(radius_squared < g.vessel_radius_m**2)
            &((z >= g.vessel_radius_m)|inside_bottom))


def box_triangles(vertices):
    faces = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    return [vertices[list(indices)] for a,b,c,d in faces for indices in [(a,b,c),(a,c,d)]]


def blade_vertices(g, angle):
    vertices=[]
    pitch=math.radians(g.blade_pitch_deg)
    for r,b,h in [(g.blade_inner_radius,-1,-1),(g.blade_outer_radius,-1,-1),
                  (g.blade_outer_radius,1,-1),(g.blade_inner_radius,1,-1),
                  (g.blade_inner_radius,-1,1),(g.blade_outer_radius,-1,1),
                  (g.blade_outer_radius,1,1),(g.blade_inner_radius,1,1)]:
        tangential=b*g.blade_chord_m/2*math.cos(pitch)-h*g.blade_thickness_m/2*math.sin(pitch)
        height=b*g.blade_chord_m/2*math.sin(pitch)+h*g.blade_thickness_m/2*math.cos(pitch)
        vertices.append([r*math.cos(angle)-tangential*math.sin(angle),
                         r*math.sin(angle)+tangential*math.cos(angle),g.impeller_height_m+height])
    return np.array(vertices)


def revolved_surface(profile, segments=80, caps=False):
    triangles=[]
    rings=[np.array([[r*math.cos(a),r*math.sin(a),z] for a in np.linspace(0,2*math.pi,segments,endpoint=False)]) for r,z in profile]
    for low,high in zip(rings[:-1],rings[1:]):
        for j in range(segments):
            k=(j+1)%segments
            triangles.extend([np.array([low[j],low[k],high[k]]),np.array([low[j],high[k],high[j]])])
    if caps:
        for ring,(_,z) in [(rings[0],profile[0]),(rings[-1],profile[-1])]:
            for j in range(segments): triangles.append(np.array([[0,0,z],ring[j],ring[(j+1)%segments]]))
    return triangles


def surfaces(g):
    r=g.vessel_radius_m
    profile=[(r*math.sin(a),r*(1-math.cos(a))) for a in np.linspace(0,math.pi/2,32)]
    profile.append((r,g.vessel_height))
    shell=revolved_surface(profile)
    shaft=revolved_surface([(g.shaft_radius_m,g.impeller_height_m+g.hub_height_m/2),
                            (g.shaft_radius_m,g.vessel_height+0.02)],caps=True)
    impeller=revolved_surface([(g.hub_radius_m,g.impeller_height_m-g.hub_height_m/2),
                               (g.hub_radius_m,g.impeller_height_m+g.hub_height_m/2)],caps=True)
    for j in range(g.blade_count): impeller.extend(box_triangles(blade_vertices(g,2*math.pi*j/g.blade_count)))
    return {'vessel_inner_surface':shell,'shaft':shaft,'impeller':impeller}


def write_stl(path, triangles):
    with Path(path).open('w') as f:
        f.write('solid synthetic_geometry\n')
        for tri in triangles:
            normal=np.cross(tri[1]-tri[0],tri[2]-tri[0]); length=np.linalg.norm(normal)
            if length<1e-15: continue
            normal/=length
            f.write(' facet normal '+' '.join(map(str,normal))+'\n  outer loop\n')
            for vertex in tri: f.write('   vertex '+' '.join(map(str,vertex))+'\n')
            f.write('  endloop\n endfacet\n')
        f.write('endsolid synthetic_geometry\n')


def export_geometry(g, spacing, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    geometry=surfaces(g)
    for name,triangles in geometry.items(): write_stl(output/(name+'.stl'),triangles)
    x,y,z=coordinates(g,spacing)
    mask=interior(g,*np.meshgrid(x,y,z,indexing='ij'))
    np.savez_compressed(output/'lattice.npz',x_m=x,y_m=y,z_m=z,fluid_envelope=mask)
    details=g.details();details.update(spacing_m=spacing,lattice_shape=list(mask.shape),
                                     envelope_lattice_volume_l=float(mask.sum()*spacing**3*1000))
    (output/'geometry.json').write_text(json.dumps(details,indent=2)+'\n')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig=plt.figure(figsize=(11,6));ax=fig.add_subplot(121,projection='3d')
    for name,triangles in geometry.items():
        collection=Poly3DCollection(np.array(triangles)*1000,alpha=0.14 if name.startswith('vessel') else 0.85,
                                   facecolor='#5a9bc4' if name.startswith('vessel') else '#da8734',linewidth=0)
        ax.add_collection3d(collection)
    ax.set(xlim=(-90,90),ylim=(-90,90),zlim=(0,(g.vessel_height+0.02)*1000),xlabel='x (mm)',ylabel='y (mm)',zlabel='z (mm)')
    ax.set_box_aspect((1,1,1.6));ax.set_title('Synthetic 5 L vessel; 3 L liquid')
    a=fig.add_subplot(122);a.imshow(mask[:,len(y)//2,:].T,origin='lower',extent=[x[0]*1000,x[-1]*1000,z[0]*1000,z[-1]*1000],aspect='equal',cmap='Blues')
    a.axhline(g.impeller_height_m*1000,color='orange',label='impeller centre')
    a.axhline(g.fill_height*1000,color='navy',linestyle='--',label='rigid liquid-level lid')
    a.set(xlabel='x (mm)',ylabel='z (mm)',title=f'Cartesian LBM grid: {spacing*1000:g} mm spacing');a.legend()
    fig.tight_layout();fig.savefig(output/'geometry_and_lattice.png',dpi=170);plt.close(fig)
    return details
