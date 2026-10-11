#!/usr/bin/env python3
"""Build a crystal-headgroup ENTH/200-lipid system and minimize; no MD."""
import argparse
from collections import defaultdict
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
import numpy as np

REPO = Path('/mnt/c/Users/Jophi/OneDrive/Documents/ChatGPT/Agent_gym')
sys.path.insert(0, str(REPO/'scripts'))
import enth_validation as e


def fit(source, target):
    a = np.asarray(source); b = np.asarray(target)
    u, _, vt = np.linalg.svd((a-a.mean(0)).T@(b-b.mean(0)))
    d = np.eye(3); d[-1,-1] = np.linalg.det(u@vt)
    rotation = u@d@vt
    return rotation, b.mean(0)-a.mean(0)@rotation


def heavy(lines):
    return np.array([e.xyz(a) for a in lines if not e.atom_name(a).startswith(('H','D'))])


def inserted_normal(protein):
    ca={int(a[22:26]):np.array(e.xyz(a)) for a in protein if e.atom_name(a)=='CA'}
    center=np.mean([ca[i] for i in range(1,15)],axis=0)
    axis=np.mean([ca[i] for i in range(11,15)],axis=0)-np.mean([ca[i] for i in range(1,5)],axis=0)
    axis/=np.linalg.norm(axis)
    normal=np.mean([v for i,v in ca.items() if i>18],axis=0)-center
    normal-=axis*np.dot(normal,axis)
    return normal/np.linalg.norm(normal)


def headgroup(protein, ligand, template):
    sap = {e.atom_name(a):np.array(e.xyz(a)) for a in template}
    crystal = {e.atom_name(a):np.array(e.xyz(a)) for a in ligand}
    mapping = {'C1'+str(i):'C'+str(i) for i in range(1,7)}
    r,t = fit([sap[k] for k in mapping], [crystal[v] for v in mapping.values()])
    aligned = {k:v@r+t for k,v in sap.items()}
    ring_rmsd = float(np.sqrt(np.mean([np.sum((aligned[k]-crystal[v])**2) for k,v in mapping.items()])))
    mapping.update({'O12':'O1', **{'O'+str(i):'O'+str(i) for i in range(2,7)}, 'P':'P1','P4':'P4','P5':'P5'})
    phosphate_errors = {k:float(np.linalg.norm(aligned[k]-crystal[v])) for k,v in [('P','P1'),('P4','P4'),('P5','P5')]}
    for src,dst in [(['O11','O13','O14'],['O11','O12','O13']),
                    (['OP42','OP43','OP44'],['O41','O42','O43']),
                    (['OP52','OP53','OP54'],['O51','O52','O53'])]:
        choice = min(itertools.permutations(dst), key=lambda p:sum(np.sum((aligned[a]-crystal[b])**2) for a,b in zip(src,p)))
        mapping.update(dict(zip(src,choice)))
    if len(mapping)!=24 or len(set(mapping.values()))!=24: raise RuntimeError('Headgroup map is not bijective')
    corrected = dict(aligned)
    for key,target in mapping.items(): corrected[key]=crystal[target]
    # Move bonded template hydrogens with their mapped parent heavy atom.
    hparents = {'H'+str(i):'C1'+str(i) for i in range(1,7)}
    hparents.update({'HO2':'O2','HO3':'O3','HO6':'O6','HP42':'OP42'})
    for h,parent in hparents.items(): corrected[h] += corrected[parent]-aligned[parent]
    # Attach the unmodified glycerol/tails to the changed phosphate bridge.
    tail_names = set(corrected)-set(mapping)-set(hparents)
    displacement = corrected['O11']-aligned['O11']
    for key in tail_names: corrected[key] += displacement
    protein_xyz=heavy(protein)
    membrane_normal=inserted_normal(protein)
    axis = corrected['O11']-corrected['P']; axis/=np.linalg.norm(axis)
    origin=corrected['O11']
    base={k:corrected[k].copy() for k in tail_names}
    best=None
    for degree in range(0,360,10):
        angle=math.radians(degree); c=math.cos(angle); s=math.sin(angle)
        candidate={k:origin+(v-origin)*c+np.cross(axis,v-origin)*s+axis*np.dot(axis,v-origin)*(1-c) for k,v in base.items()}
        tailxyz=np.array([v for k,v in candidate.items() if not k.startswith('H')])
        distances=np.sum((tailxyz[:,None,:]-protein_xyz[None,:,:])**2,axis=2)
        minimum=float(np.sqrt(distances.min()))
        terminal=np.mean([v for k,v in candidate.items() if k in {'C218','C320','C220','C318'}],axis=0)
        depth=float(np.dot(corrected['P']-terminal,membrane_normal))
        score=depth if minimum>=2.2 else -1000+minimum
        if best is None or score>best[0]: best=(score,degree,candidate,float(np.sqrt(distances.min())))
    corrected.update(best[2])
    if best[3]<1.5: raise RuntimeError(f'Unresolvable PIP2 tail/protein clash: {best[3]} A')
    out=[e.set_xyz(a[:21]+'B'+f'{9001:4d}'+a[26:],corrected[e.atom_name(a)]) for a in template]
    return out, {'atom_map_sapi24_to_i3p':mapping,'rigid_ring_rmsd_angstrom':ring_rmsd,
                 'rigid_fit_phosphate_errors_angstrom':phosphate_errors,'crystal_heavy_coordinates_preserved_before_minimization':24,
                 'glycerol_tail_torsion_rotation_degrees':best[1], 'tail_protein_minimum_angstrom':best[3],
                 'hydrogens':'template hydrogen vectors translated with mapped parents; relaxed by force field'}


def closest(a,b,box):
    delta=a[:,None,:]-b[None,:,:]
    delta[:,:,:2]-=np.rint(delta[:,:,:2]/box[:2])*box[:2]
    ds=np.sum(delta*delta,axis=2)
    ij=np.unravel_index(np.argmin(ds),ds.shape)
    return float(np.sqrt(ds[ij])), delta[ij]


def pack(groups, fixed, box, target_upper=99, target_lower=100):
    """Select exact composition, then translate whole POPCs to remove clashes."""
    arrays=[heavy(a) for a in groups]
    centers=np.array([next(e.xyz(a) for a in g if e.atom_name(a)=='P') for g in groups])
    mid=float(np.median(centers[:,2]))
    # Preserve each molecule; scale only its phosphate center into the new XY cell.
    factor=np.sqrt(100/128)
    for i,a in enumerate(arrays):
        shift=np.array([(centers[i,0]-box[0]/2)*(factor-1),(centers[i,1]-box[1]/2)*(factor-1),0])
        arrays[i]=a+shift
        groups[i]=[e.set_xyz(x,np.array(e.xyz(x))+shift) for x in groups[i]]
    centers=np.array([next(e.xyz(a) for a in g if e.atom_name(a)=='P') for g in groups])
    newbox=box.copy(); newbox[:2]*=factor
    # Recentering makes coordinates and the reduced cell share the same origin.
    shift=(newbox-box)/2
    arrays=[a+shift for a in arrays]; fixed=fixed+shift
    groups=[[e.set_xyz(x,np.array(e.xyz(x))+shift) for x in g] for g in groups]
    centers+=shift
    active=set(range(len(groups)))
    removed=[]
    for upper,target in [(True,target_upper),(False,target_lower)]:
        leaf={i for i in active if (centers[i,2]>mid)==upper}
        scores={i:0.0 for i in leaf};paircost={}
        for i in leaf:
            d,_=closest(arrays[i],fixed,newbox)
            scores[i]+=max(0,3.0-d)**2*20
        for i,j in itertools.combinations(sorted(leaf),2):
            d,_=closest(arrays[i],arrays[j],newbox)
            cost=max(0,2.4-d)**2
            paircost[i,j]=cost;scores[i]+=cost;scores[j]+=cost
        while len(leaf)>target:
            worst=max(sorted(leaf),key=lambda i:scores[i])
            active.remove(worst);leaf.remove(worst);removed.append(worst)
            for i in leaf:scores[i]-=paircost.get(tuple(sorted((i,worst))),0.0)
    ids=sorted(active)
    groups=[groups[i] for i in ids];arrays=[arrays[i] for i in ids];centers=centers[ids]
    translations=np.zeros((len(groups),3))
    # Repulsive packing acts on whole-molecule XY translations, leaving molecular
    # conformations and the crystal protein/PIP2 pose unchanged.
    minimum=0
    for iteration in range(120):
        moves=np.zeros_like(translations);minimum=1e9
        for i,a in enumerate(arrays):
            d,delta=closest(a,fixed,newbox);minimum=min(minimum,d)
            if d<2.2:
                norm=np.linalg.norm(delta[:2]);moves[i,:2]+=delta[:2]/max(norm,1e-8)*(2.2-d)*0.25
        for i,j in itertools.combinations(range(len(groups)),2):
            d,delta=closest(arrays[i],arrays[j],newbox);minimum=min(minimum,d)
            if d<2.2:
                norm=np.linalg.norm(delta[:2]);v=delta[:2]/max(norm,1e-8)*(2.2-d)*0.15
                moves[i,:2]+=v;moves[j,:2]-=v
        lengths=np.linalg.norm(moves,axis=1);moves*=np.minimum(1,0.15/np.maximum(lengths,1e-8))[:,None]
        for i in range(len(groups)): arrays[i]+=moves[i]
        centers+=moves;translations+=moves
        if minimum>=1.9:break
    if minimum<1.2:raise RuntimeError(f'Packing retained severe intermolecular clash {minimum:.3f} A')
    groups=[[e.set_xyz(a,np.array(e.xyz(a))+translations[i]) for a in g] for i,g in enumerate(groups)]
    return groups,newbox,shift,{'removed_original_indices':removed,'upper_popc':target_upper,'lower_popc':target_lower,
        'upper_pip2':1,'area_per_leaflet_lipid_angstrom2':float(np.prod(newbox[:2])/100),
        'packing_iterations':iteration+1,'packing_minimum_heavy_distance_angstrom':minimum,
        'maximum_rigid_popc_translation_angstrom':float(np.linalg.norm(translations,axis=1).max())}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workdir',type=Path,required=True);args=parser.parse_args()
    root=args.workdir;root.mkdir(exist_ok=True);run_dir=root/'run';run_dir.mkdir(exist_ok=False)
    report={'attempt_root':str(root),'commands':[],'started_monotonic':time.monotonic(),'status':'preparing',
            'model':'gpt-6-astra','attribution':'Astra scientific reconstruction assisted by inherited worker and parent Colab orchestration',
            'dynamics_executed':False,'scope':'Corrected inserted-state reconstruction, not Figure 4 replication'}
    inputs=root/'inputs';shutil.copytree('/home/gym/agent-gym-md/validation-007/inputs',inputs)
    shutil.copy2(REPO/'scripts/enth_validation.py',root/'enth_validation.executed.py')
    ff=next(inputs.rglob('forcefield.itp')).parent
    # Source007 already contains the parameter-identical SAPI24 -> SAP alias.
    os.environ['GMXLIB']=str(ff.parent)
    try:
        source=(inputs/'pdb_archive/popc/popc_n256.pdb').read_text().splitlines()
        old,edges,_=e.parse_psf_popc_graph(inputs/'pdb_archive/popc/popc_n256.psf')
        _,new,newedges=e.parse_rtp_residue_graph(ff,'POPC')
        name_map=e.graph_isomorphism(old,edges,new,newedges)
        source,_=e.rename_archive_popc(source,old,name_map)
        lipids=e.parse_atoms(source,{'POPC'});box=np.array(e.pdb_box(source))
        coords=np.array([e.xyz(a) for a in lipids]);offset=box/2-(coords.min(0)+coords.max(0))/2
        lipids=[e.set_xyz(a,np.array(e.xyz(a))+offset) for a in lipids]
        pdb=e.parse_atoms((inputs/'pdb_1h0a.pdb').read_text().splitlines())
        protein=[a for a in pdb if a.startswith('ATOM  ') and a[21]=='A']
        ligand=[a for a in pdb if e.resname(a)=='I3P' and a[21]=='A']
        sap,headinfo=headgroup(protein,ligand,e.parse_atoms((inputs/'sapi24_template.pdb').read_text().splitlines()))
        byname={e.atom_name(a):np.array(e.xyz(a)) for a in sap}
        tail=np.mean([v for k,v in byname.items() if k in {'C218','C320','C220','C318'}],axis=0)
        if not np.isfinite(tail).all():raise RuntimeError('Tail terminal atom names unavailable')
        # Rotate the entire bound complex so the PIP2 tails point down into the bilayer.
        rotation=np.array(e.rotate_to_z(inserted_normal(protein)))
        upper=np.mean([e.xyz(a)[2] for a in lipids if e.atom_name(a)=='P' and e.xyz(a)[2]>box[2]/2])
        anchor=np.array([box[0]/2,box[1]/2,upper])
        def orient(a):return e.set_xyz(a,(np.array(e.xyz(a))-byname['P'])@rotation.T+anchor)
        protein=[orient(a) for a in protein];sap=[orient(a) for a in sap]
        h0=[e.xyz(a)[2] for a in protein if e.atom_name(a)=='CA' and int(a[22:26])<=18]
        headinfo.update(protein_ca_height_above_phosphate_angstrom=float(np.mean([e.xyz(a)[2] for a in protein if e.atom_name(a)=='CA'])-upper),
                        h0_ca_height_range_above_phosphate_angstrom=[min(h0)-upper,max(h0)-upper],
                        pip2_tail_terminal_height_below_phosphate_angstrom=float(np.dot(byname['P']-tail,inserted_normal([a for a in pdb if a.startswith('ATOM  ') and a[21]=='A']))))
        if headinfo['protein_ca_height_above_phosphate_angstrom']<0:raise RuntimeError('Protein oriented into membrane')
        grouped=defaultdict(list)
        for a in lipids:grouped[e.resid(a)].append(a)
        groups,newbox,shift,packing=pack(list(grouped.values()),heavy(protein+sap),box)
        protein=[e.set_xyz(a,np.array(e.xyz(a))+shift) for a in protein];sap=[e.set_xyz(a,np.array(e.xyz(a))+shift) for a in sap]
        atoms=[a for g in groups for a in g]+sap+protein
        span=heavy(protein).max(0)-heavy(protein).min(0)
        clearance=float(min(newbox[:2]-span[:2]));
        if clearance<12:raise RuntimeError('Protein periodic image separation too small')
        # Use the actual molecular z extent plus solvent padding, avoiding image overlap.
        atomxyz=np.array([e.xyz(a) for a in atoms]);newbox[2]=max(newbox[2]+24,float(np.ptp(atomxyz[:,2]))+24)
        header=f'CRYST1{newbox[0]:9.3f}{newbox[1]:9.3f}{newbox[2]:9.3f}{90:7.2f}{90:7.2f}{90:7.2f} P 1           1\n'
        (run_dir/'inserted_complex.pdb').write_text(header+''.join(a[:6]+f'{i:5d}'+a[11:].rstrip()+'\n' for i,a in enumerate(atoms,1))+'TER\nEND\n')
        report.update(headgroup=headinfo,packing=packing,box_angstrom=newbox.tolist(),protein_xy_image_clearance_angstrom=clearance)
        (root/'geometry.json').write_text(json.dumps(report,indent=2))
        def run(cmd,stdin=None):
            cp=e.run(cmd,run_dir,report,stdin)
            if cp.returncode:raise RuntimeError('Command failed: '+' '.join(cmd))
            return cp
        run(['gmx','pdb2gmx','-f','inserted_complex.pdb','-o','processed.gro','-p','topol.top','-ff',ff.name.removesuffix('.ff'),'-water','tip3p'])
        run(['gmx','editconf','-f','processed.gro','-o','boxed.gro','-c','-box',*[f'{v/10:.5f}' for v in newbox]])
        run(['gmx','solvate','-cp','boxed.gro','-cs','spc216.gro','-o','solv.gro','-p','topol.top'])
        report['atom_count']=int((run_dir/'solv.gro').read_text().splitlines()[1])
        if report['atom_count']>100000:raise RuntimeError('100k atom limit exceeded')
        e.write_mdp(run_dir/'em.mdp','min')
        run(['gmx','grompp','-f','em.mdp','-c','solv.gro','-p','topol.top','-o','ions.tpr'])
        run(['gmx','genion','-s','ions.tpr','-o','ions.gro','-p','topol.top','-pname','K','-nname','CL','-neutral','-conc','0.00015'],'SOL\n')
        for stage in ['nvt','npt_restraint','npt_release']:e.write_mdp(run_dir/(stage+'.mdp'),stage)
        e.write_mdp(run_dir/'em_relax.mdp','min_relax')
        run(['gmx','grompp','-f','em_relax.mdp','-c','ions.gro','-p','topol.top','-o','em_relax.tpr'])
        # Parent executes the two minimizations on the allocated Colab GPU.
        report['status']='preprocessed_ready_for_gpu_minimization'
        return
    except Exception as exc:
        report['status']='failed';report['error']=repr(exc)
        raise
    finally:
        report['elapsed_seconds']=time.monotonic()-report.pop('started_monotonic')
        (root/'preparation.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
