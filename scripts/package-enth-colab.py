#!/usr/bin/env python3
"""Package the corrected, preprocessed (not minimized) Colab input system."""
import json
from pathlib import Path
import shutil
import sys
import tarfile
import numpy as np
import os
import re
import subprocess

REPO=Path('/mnt/c/Users/Jophi/OneDrive/Documents/ChatGPT/Agent_gym')
sys.path.insert(0,str(REPO/'scripts'))
import enth_analysis as analysis
from enth_validation import sha256,parse_atoms,atom_name,xyz,resname


def main():
    base=Path('/home/gym/agent-gym-md');source=base/'validation-010'
    report=json.loads((source/'preparation.json').read_text())
    if report['status']!='preprocessed_ready_for_gpu_minimization':raise RuntimeError('Preprocessing incomplete')
    bundle=base/'colab-input-010-portable';bundle.mkdir(exist_ok=False)
    run=bundle/'run';run.mkdir()
    for p in (source/'run').iterdir():
        if p.suffix in {'.gro','.pdb','.top','.itp','.mdp','.tpr'} and not p.name.startswith('#'):
            shutil.copy2(p,run/p.name)
    ff=next((source/'inputs').rglob('forcefield.itp')).parent
    shutil.copytree(ff,run/ff.name)
    provenance=bundle/'provenance';provenance.mkdir()
    include_changes=[]
    for path in run.rglob('*'):
        if path.suffix not in {'.top','.itp'}:continue
        body=path.read_text();portable=body.replace(str(ff)+'/',ff.name+'/')
        if re.search(r'^\s*#include\s+"/',portable,re.M):raise RuntimeError('Unresolved absolute include: '+str(path))
        if portable!=body:
            before=sha256(path);path.write_text(portable)
            include_changes.append({'path':str(path.relative_to(bundle)),'source_sha256':before,'portable_sha256':sha256(path)})
    command=['gmx','grompp','-f','em_relax.mdp','-c','ions.gro','-p','topol.top','-o','portable-preflight.tpr']
    cp=subprocess.run(command,cwd=run,capture_output=True,text=True,timeout=180,env={**os.environ,'OMP_NUM_THREADS':'2','GMXLIB':str(run)})
    (provenance/'portable-preflight.log').write_text(cp.stdout+'\n'+cp.stderr)
    (provenance/'portability.json').write_text(json.dumps({'command':command,'returncode':cp.returncode,'include_path_changes':include_changes,'scientific_parameters_changed':False},indent=2)+'\n')
    if cp.returncode:raise RuntimeError('Portable standalone grompp failed')
    for name in ['preparation.json','geometry.json','command-ledger.json','supervisor-start.json','supervisor-result.json','worker.executed.py','supervisor.executed.py','enth_validation.executed.py']:
        if (source/name).exists():shutil.copy2(source/name,provenance/name)
    inputs=bundle/'source-inputs';inputs.mkdir()
    for p in (source/'inputs').iterdir():
        if p.is_file():shutil.copy2(p,inputs/p.name)
    checks={'contact_audit':analysis.contact_audit(run/'ions.gro'),
            'leaflets':analysis.leaflet_analysis(analysis.parse_gro(run/'ions.gro')),
            'atom_count':int((run/'ions.gro').read_text().splitlines()[1]),
            'grompp_passed_without_maxwarn':all(c['returncode']==0 for c in report['commands']),
            'minimization_performed':False,'dynamics_performed':False,
            'gpu_gate_required':'Unconstrained bond relaxation, then clean constrained minimization, then restrained warmup; stop on physical warnings',
            'checkpoint_included':False,'checkpoint_reason':'Fresh corrected coordinates cannot reuse the old proxy checkpoint'}
    original=parse_atoms((source/'inputs/pdb_1h0a.pdb').read_text().splitlines())
    original_ca=np.array([xyz(a) for a in original if a.startswith('ATOM') and a[21]=='A' and atom_name(a)=='CA'])
    gro=analysis.parse_gro(run/'ions.gro')['atoms']
    final_ca=np.array([a[3:] for a in gro if a[2]=='CA'])
    u,_,vt=np.linalg.svd((original_ca-original_ca.mean(0)).T@(final_ca-final_ca.mean(0)))
    rotation=u@vt;translation=final_ca.mean(0)-original_ca.mean(0)@rotation
    crystal={atom_name(a):np.array(xyz(a))@rotation+translation for a in original if resname(a)=='I3P' and a[21]=='A'}
    sap={a[2]:np.array(a[3:]) for a in gro if a[1]=='SAP'}
    mapping=report['headgroup']['atom_map_sapi24_to_i3p']
    errors=[float(np.linalg.norm(sap[key]-crystal[value])) for key,value in mapping.items()]
    checks['crystal_headgroup_in_protein_frame']={'mapped_heavy_atoms':len(errors),'rmsd_angstrom':float(np.sqrt(np.mean(np.square(errors)))),'maximum_deviation_angstrom':max(errors)}
    if max(errors)>0.02:raise RuntimeError('Crystal headgroup pose changed during preparation')
    if checks['contact_audit']['intermolecular_heavy_pairs_below_0_18nm']:
        raise RuntimeError('Unexpected severe contact after topology conversion')
    if checks['leaflets']['upper']!={'POPC':99,'PIP2':1,'total':100} or checks['leaflets']['lower']!={'POPC':100,'PIP2':0,'total':100}:
        raise RuntimeError('Final coordinate composition/leaflets differ from target')
    (provenance/'input-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    readme='''# Corrected ENTH Colab inputs: validation-010

This is a fresh reconstructed inserted-state system, preprocessed with GROMACS
2023.3, and **not yet energy-minimized or dynamically validated**. It is not a
Figure 4 reproduction. Do not continue the old validation-007 checkpoint.

Run from `run/`; all topology includes and the complete CHARMM36 July 2020 force
field are local. Rebuild TPRs using the installed Colab GROMACS release.
Start from `ions.gro` and `topol.top`, relax using `em_relax.mdp`, then constrained
`em.mdp`. Both must reach Fmax <1000 kJ/mol/nm without LINCS/SETTLE/fatal errors.
Only then generate NVT velocities and proceed to restrained NPT and released
equilibration. The supplied dynamic MDPs retain the short validation-007 pilot
durations and 2-ps XTC interval: the GPU runner must explicitly record longer
warmup/endpoint and sparser output settings before production-sized execution.

The system contains 99 upper POPCs plus one SAPI24 PIP2 and 100 lower POPCs.
The original 256-lipid template is repacked by translating whole lipids into an
8.264381-nm square, retaining its 68.300-A^2 nominal area per lipid. Clashing
molecules are removed to exact composition, then rigid XY repulsion removes
remaining severe contacts. Protein and PIP2 remain fixed during packing.

SAPI24 C11-C16 map to crystal I3P C1-C6 (rigid-fit RMSD 0.1404 A). Because the
template phosphate torsions differ, all 24 mapped headgroup heavy coordinates
are replaced with their crystal positions, with an explicit bijective map and
minimum-displacement equivalent-oxygen mapping. Template H vectors move with
their heavy parents; the glycerol/tails translate with the bridging oxygen and
rotate 60 degrees around P-O11. This attachment is an explicit reconstruction
choice requiring minimization. The bound protein/headgroup move together.
H0 proxy residues1-14 define the membrane-parallel axis, the protein body defines
the outward normal; residues1-18 remain the reported H0 proxy for continuity.
The H0 C-alpha range is -4.48 to +5.01 A from the upper phosphate plane, protein
body +17.26 A, PIP2 terminal tail average -15.77 A. The exact original placement,
protonation, pulling protocol and state coordinates remain unavailable.

Salt is the paper's literal0.15 mM KCl. No added pairs fit this small neutral box;
this is not0.15 M. CHARMM36 uses the inherited USE_OLD_C36 protein toggle and P4-
protonated SAPI24 (-4 charge), both documented assumptions. The full paper's
70-ns equilibration and150-ns production, three states and replica uncertainty
have not been completed. Long dynamics must retain checkpoint/provenance and
enforce the explicitly authorized cloud time/output bounds.

`provenance/` holds preprocessing command output, geometry and independent
contact/leaflet checks; `source-inputs/` holds the cached public source files.
`manifest.json` hashes every packaged file except itself. No credentials or
private user data are included. Astra reconstruction was assisted by inherited
worker code and parent orchestration; it is not an independent model trial.
'''
    (bundle/'README.md').write_text(readme)
    manifest=[{'path':str(p.relative_to(bundle)),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(bundle.rglob('*')) if p.is_file()]
    (bundle/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=REPO/'artifacts/enth/colab-input-010-portable.tar.gz'
    if archive.exists():raise RuntimeError('Archive already exists')
    with tarfile.open(archive,'w:gz') as tf:tf.add(bundle,arcname='enth-colab')
    evidence=REPO/'benchmarks/enth/evidence/validation-010-portable';evidence.mkdir(exist_ok=False)
    for p in provenance.iterdir():shutil.copyfile(p,evidence/p.name)
    for name in ['README.md','manifest.json']:shutil.copyfile(bundle/name,evidence/name)
    summary={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha256(archive),
             'status':'preprocessed_not_minimized','checks':checks}
    (evidence/'archive.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
