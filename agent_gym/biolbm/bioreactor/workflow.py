# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jophin Joseph
"""Readable synthetic vessel workflow: geometry → lattice → CPU/GPU run → plots.

CLI imports the numerical backend only for a run, so geometry/check are cheap.
"""
import argparse
from dataclasses import asdict,dataclass
import json
import math
from pathlib import Path
import time
import numpy as np
import yaml
from .geometry import Geometry,coordinates,export_geometry
from ..runner import write_json


@dataclass(frozen=True)
class Settings:
    schema_version:int=1
    rpm:float=180
    rotation:str='ccw_from_above'
    spacing_m:float=0.003
    density_kg_m3:float=998
    viscosity_pa_s:float=0.001
    lattice_tip_mach:float=0.1
    steps:int=1200
    report_interval:int=50
    threads:int=2
    device:str="cpu"

    def __post_init__(self):
        if self.schema_version != 1 or self.rotation != 'ccw_from_above': raise ValueError('Unsupported schema or rotation')
        for name in ['rpm','spacing_m','density_kg_m3','viscosity_pa_s','lattice_tip_mach']:
            v=getattr(self,name)
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0: raise ValueError(f'{name} must be finite and positive')
        for name in ['steps','report_interval','threads']:
            if type(getattr(self,name)) is not int or getattr(self,name)<=0: raise ValueError(f'{name} must be a positive integer')
        if self.device not in ('cpu','cuda'): raise ValueError('device must be cpu or cuda')
        if self.lattice_tip_mach>0.1: raise ValueError('Tip Mach must be <=0.1')
        if not 0.001<=self.spacing_m<=0.008: raise ValueError('Supported spacing: 1–8 mm')

    def scaling(self,g):
        speed=math.pi*self.rpm/60*g.impeller_diameter_m
        dt=self.lattice_tip_mach/math.sqrt(3)*self.spacing_m/speed
        tau=0.5+3*(self.viscosity_pa_s/self.density_kg_m3)*dt/self.spacing_m**2
        shape=[len(a) for a in coordinates(g,self.spacing_m)]
        return {'tip_speed_m_s':speed,'dt_s':dt,'tau':tau,'grid_shape':shape,'grid_cells':math.prod(shape),
                'impeller_reynolds':self.density_kg_m3*(self.rpm/60)*g.impeller_diameter_m**2/self.viscosity_pa_s,
                'requested_simulation_time_s':self.steps*dt,'nominal_revolutions':self.steps*dt*self.rpm/60,
                'passes_tau_envelope':0.51<=tau<=2,
                'working_memory_planning_bytes':(8*19+35)*math.prod(shape)*8,
                'note':'Planning memory only; diffuse rotor and stepped walls require validation/refinement.'}


def load_settings(path):
    data=yaml.safe_load(Path(path).read_text())
    if not isinstance(data,dict): raise ValueError('Expected a case mapping')
    try:return Settings(**data)
    except TypeError as exc:raise ValueError(str(exc)) from exc


def execute(settings,output):
    """Run one closed-vessel transient, refusing unsafe scaling and overwrite."""
    g=Geometry();scaling=settings.scaling(g)
    if not scaling['passes_tau_envelope']:
        raise ValueError(f"Requested fluid maps to tau={scaling['tau']:.8f}, outside [0.51,2]. No silent viscosity adjustment.")
    import torch
    import lettuce as lt
    from .model import VesselFlow,RotorForce
    torch.set_num_threads(settings.threads)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    write_json(output/'case.json',asdict(settings));write_json(output/'scaling.json',scaling)
    export_geometry(g,settings.spacing_m,output/'geometry')
    write_json(output/'status.json',{'state':'starting','step':0})
    try:
        flow=VesselFlow(g,settings.spacing_m,settings.density_kg_m3,settings.viscosity_pa_s,settings.rpm,settings.lattice_tip_mach,device=settings.device)
        force=RotorForce(flow,flow.units.relaxation_parameter_lu)
        simulation=lt.Simulation(flow,lt.BGKCollision(flow.units.relaxation_parameter_lu,force=force),[])
        mask=flow.fluid
        mass0=float(flow.rho()[0][mask].sum())
        total_mass0=float(flow.rho().sum())
        history=[];flow.context.synchronize();start=time.perf_counter()
        with torch.no_grad():
            for step in range(settings.steps+1):
                force.update()
                if step%settings.report_interval==0 or step==settings.steps:
                    rho=flow.rho()[0];u=force.velocity_si();speed=torch.linalg.vector_norm(u,dim=0)
                    if not bool(torch.isfinite(flow.f).all()) or bool((rho[mask]<=0).any()): raise RuntimeError('Invalid distributions or density')
                    max_mach=float(flow.units.convert_velocity_to_lu(speed[mask]).max())*math.sqrt(3)
                    drift=abs(float(rho[mask].sum())/mass0-1)
                    # Full-way wall nodes store populations; fluid-only mass can oscillate.
                    closed_drift=abs(float(flow.rho().sum())/total_mass0-1)
                    torque=force.torque_si()
                    row={'step':step,'time_s':step*scaling['dt_s'],'rpm':force.rpm_actual,
                         'max_speed_m_s':float(speed[mask].max()),'mean_speed_m_s':float(speed[mask].mean()),
                         'max_lattice_mach':max_mach,'envelope_mass_drift':drift,'closed_grid_mass_drift':closed_drift,
                         'drive_torque_nm_estimate':torque,'drive_power_w_estimate':torque*flow.omega*force.rpm_actual/settings.rpm}
                    history.append(row);write_json(output/'history.json',history);write_json(output/'status.json',{'state':'running',**row})
                    print(f"step {step:5d} | t={row['time_s']:.4f}s | max|u|={row['max_speed_m_s']:.4f}m/s | Mach={max_mach:.4f} | mass={closed_drift:.2e}",flush=True)
                    if max_mach>0.2 or closed_drift>1e-7 or drift>0.02: raise RuntimeError('Mach/conservation guard failed')
                if step==settings.steps:break
                simulation(1)
            np.savez_compressed(output/'fields.npz',x_m=flow.x,y_m=flow.y,z_m=flow.z,
                                velocity_m_s=u.detach().cpu().numpy(),density_kg_m3=rho.detach().cpu().numpy()*settings.density_kg_m3,
                                fluid=mask.detach().cpu().numpy(),solid_fraction=force.fraction.detach().cpu().numpy(),time_s=step*scaling['dt_s'])
            np.savez_compressed(output/'state.npz',f=flow.f.detach().cpu().numpy(),step=step)
            from pyevtk.hl import gridToVTK
            gridToVTK(str(output/'fields_si'),flow.x,flow.y,flow.z,pointData={
                'velocity_m_s':tuple(np.ascontiguousarray(u[j].detach().cpu().numpy()) for j in range(3)),
                'fluid_envelope':np.ascontiguousarray(mask.detach().cpu().numpy().astype(np.uint8)),
                'rotor_fraction':np.ascontiguousarray(force.fraction.detach().cpu().numpy()),
                'density_kg_m3':np.ascontiguousarray(rho.detach().cpu().numpy()*settings.density_kg_m3)})
        summary={'state':'completed','elapsed_wall_seconds':time.perf_counter()-start,
                 'engine':f'Lettuce D3Q19 BGK on {settings.device} float64','lettuce_version':lt.__version__,
                 'validation_status':'experimental transient only; no validated tank, torque, or mixing prediction',
                 'limitations':['diffuse volumetric rotor penalty; blade thickness and shaft are under-resolved',
                                'full-way voxel vessel walls; rigid no-slip lid at liquid level; no free surface',
                                'no turbulence, scalar mixing, or steady-state claim','torque is total penalty estimate for shaft + hub + blades, not validated impeller torque'],
                 'case':asdict(settings),'scaling':scaling,'geometry':g.details(),'final':history[-1]}
        write_json(output/'summary.json',summary);write_json(output/'status.json',{'state':'completed','step':flow.i})
        plot(output)
        return summary
    except Exception as exc:
        write_json(output/'status.json',{'state':'failed','error':str(exc)});raise


def plot(output):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    output=Path(output);data=np.load(output/'fields.npz');u=data['velocity_m_s'];mask=data['fluid'];solid=data['solid_fraction']
    x,y,z=[data[a]*1000 for a in ['x_m','y_m','z_m']]
    j=int(np.argmin(abs(y)));k=int(np.argmin(abs(z-50.8)))
    speed=np.linalg.norm(u,axis=0)
    fig,axs=plt.subplots(1,2,figsize=(12,6))
    slices=[(speed[:,j,:].T,mask[:,j,:].T,solid[:,j,:].T,x,z,u[0,:,j,:].T,u[2,:,j,:].T,'Vertical centre slice'),
            (speed[:,:,k].T,mask[:,:,k].T,solid[:,:,k].T,x,y,u[0,:,:,k].T,u[1,:,:,k].T,'Impeller-level slice')]
    vmax=float(speed[mask].max())
    for ax,(v,m,s,a,b,ua,ub,title) in zip(axs,slices):
        image=ax.pcolormesh(a,b,np.ma.masked_where(~m,v),shading='nearest',cmap='viridis',vmin=0,vmax=vmax)
        ax.contour(a,b,s,levels=[0.3],colors=['white'],linewidths=0.7)
        aa,bb=np.meshgrid(a,b);skip=(slice(None,None,3),slice(None,None,3))
        ax.quiver(aa[skip],bb[skip],np.where(m,ua,np.nan)[skip],np.where(m,ub,np.nan)[skip],color='white',scale=max(vmax,1e-9)*15,width=0.003)
        ax.set(title=title,xlabel='x (mm)',ylabel='z (mm)' if 'Vertical' in title else 'y (mm)');ax.set_aspect('equal')
    fig.colorbar(image,ax=axs,label='Speed (m/s)',shrink=0.7)
    fig.suptitle(f"Experimental viscous-fluid transient, t={float(data['time_s']):.3f}s — NOT water validation")
    fig.savefig(output/'velocity_slices.png',dpi=180,bbox_inches='tight');plt.close(fig)
    rows=json.loads((output/'history.json').read_text());t=[r['time_s'] for r in rows]
    fig,axs=plt.subplots(1,3,figsize=(13,4))
    axs[0].plot(t,[r['max_speed_m_s'] for r in rows],label='maximum');axs[0].plot(t,[r['mean_speed_m_s'] for r in rows],label='mean');axs[0].set_ylabel('Speed (m/s)');axs[0].legend()
    axs[1].plot(t,[r['drive_torque_nm_estimate']*1000 for r in rows]);axs[1].set_ylabel('Penalty drive torque estimate (mN m)')
    axs[2].plot(t,[r['closed_grid_mass_drift'] for r in rows]);axs[2].set_ylabel('Closed-grid relative mass drift')
    for ax in axs:ax.set_xlabel('Time (s)');ax.grid(alpha=0.3)
    fig.suptitle('Startup diagnostics — unvalidated torque, no steady-state claim');fig.tight_layout();fig.savefig(output/'diagnostics.png',dpi=180);plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['geometry','check','run','plot'])
    parser.add_argument('--case',default='benchmarks/biolbm/cases/bioreactor_5l/water.yaml')
    parser.add_argument('--output',default='outputs/bioreactor-geometry')
    args=parser.parse_args()
    try:
        if args.command=='plot':plot(args.output);return 0
        settings=load_settings(args.case)
        if args.command=='geometry': result=export_geometry(Geometry(),settings.spacing_m,args.output)
        elif args.command=='check': result=settings.scaling(Geometry())
        else: result=execute(settings,args.output)
        print(json.dumps(result,indent=2));return 0
    except (ValueError,RuntimeError,OSError) as exc:
        print(f'bioreactor: {exc}');return 1


if __name__=='__main__':raise SystemExit(main())
