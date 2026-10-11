#!/usr/bin/env python3
"""Prepare a portable ENTH checkpoint bundle. Never launches molecular dynamics."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

BASE = Path('/home/gym/agent-gym-md')
REPO = Path('/mnt/c/Users/Jophi/OneDrive/Documents/ChatGPT/Agent_gym')
ENDPOINT_PS = 70000


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def checkpoint_fields(text):
    result = {}
    for field in ('step', 't', 'natoms'):
        label = r'(?:natoms|#atoms)' if field == 'natoms' else field
        match = re.search(rf'(?m)^\s*{label}\s*=\s*([-+0-9.eE]+)', text)
        if not match: raise RuntimeError(f'Missing checkpoint {field}')
        result[field] = float(match.group(1)) if field == 't' else int(match.group(1))
    if result['natoms'] > 100000 or result['natoms'] <= 0:
        raise RuntimeError('Invalid or excessive atom count')
    return result


def main():
    source = BASE/'validation-007'
    root = BASE/'restart-bundle-001'
    analysis = json.loads((source/'independent-analysis.json').read_text())
    if not analysis.get('physical_checks_passed'):
        raise RuntimeError('Source checkpoint lacks passing partial physical checks')
    root.mkdir(exist_ok=False)
    files = [('run/npt.tpr', 'seed.tpr'), ('run/npt.cpt', 'seed.cpt'),
             ('run/npt_release.mdp', 'seed.mdp'), ('independent-analysis.json', 'seed-analysis.json'),
             ('provenance-audit.json', 'seed-provenance.json')]
    inputs = []
    for relative, name in files:
        shutil.copy2(source/relative, root/name)
        inputs.append({'source': str(source/relative), 'bundle_name': name,
                       'sha256': digest(root/name), 'bytes': (root/name).stat().st_size})
    commands = []
    def run(argv):
        cp = subprocess.run(argv, cwd=root, text=True, capture_output=True, timeout=60,
                            env={**os.environ, 'OMP_NUM_THREADS':'2'})
        commands.append({'command': argv, 'returncode': cp.returncode,
                         'stdout_excerpt': cp.stdout[:3000], 'stderr_excerpt': cp.stderr[-4000:]})
        if cp.returncode: raise RuntimeError(f'Preflight command failed: {argv}')
        return cp
    version = run(['/usr/bin/gmx', '--version'])
    cp = run(['/usr/bin/gmx', 'dump', '-cp', 'seed.cpt'])
    checkpoint = checkpoint_fields(cp.stdout)
    run(['/usr/bin/gmx', 'convert-tpr', '-s', 'seed.tpr', '-until', str(ENDPOINT_PS), '-o', 'eq70ns.tpr'])
    run(['/usr/bin/gmx', 'dump', '-s', 'eq70ns.tpr', '-om', 'effective.mdp'])
    params = {}
    for line in (root/'effective.mdp').read_text().splitlines():
        if '=' in line:
            key, value = line.split('=', 1); params[key.strip()] = value.split(';')[0].strip()
    if int(params['nsteps']) != 35000000 or float(params['dt']) != 0.002:
        raise RuntimeError('Unexpected extended TPR endpoint or timestep')
    report = {'status': 'prepared_not_launched', 'model': 'gpt-6-astra', 'reasoning_effort':'high',
              'source_run':'validation-007', 'source_checkpoint': checkpoint,
              'endpoint_ps': ENDPOINT_PS, 'maximum_tpr_steps':35000000, 'dt_ps':0.002,
              'dynamics_commands_executed':0, 'inputs':inputs, 'commands':commands,
              'portable_restart_command': 'gmx mdrun -s eq70ns.tpr -cpi seed.cpt -deffnm eq -noappend -cpt 5',
              'execution_limits': 'Not launched. Choose and enforce runtime, CPU/GPU, memory and output limits before execution.',
              'scientific_scope': 'Extended equilibration of an explicitly reconstructed membrane-associated proxy, not Figure 4 replication',
              'known_deviations': ['113 retained lipids versus the paper\'s 200',
                  'PIP2 headgroup placement does not guarantee preservation of the crystallographic bound pose',
                  'Original equilibration, pulling constants/rates and state definitions unavailable',
                  'PIP2 protonation and H0 residue mapping remain assumptions',
                  'Salt value retained literally at published 0.15 mM'],
              'no_new_velocities': True, 'source_evidence_unchanged': all(digest(source/relative) == digest(root/name) for relative,name in files)}
    (root/'preflight.json').write_text(json.dumps(report, indent=2)+'\n')
    shutil.copy2(REPO/'benchmarks/enth/longrun-protocol.md', root/'README.md')
    manifest = [{'name':p.name,'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(root.iterdir()) if p.is_file()]
    (root/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    archive = BASE/'restart-bundle-001.tar.gz'
    if archive.exists(): raise RuntimeError('Archive already exists; refusing replacement')
    with tarfile.open(archive, 'w:gz') as output:
        for path in sorted(root.iterdir()): output.add(path, arcname='enth-restart/'+path.name)
    destination = REPO/'artifacts/enth/restart-bundle-001.tar.gz'
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists(): raise RuntimeError('Export already exists; refusing replacement')
    shutil.copy2(archive, destination)
    evidence = REPO/'benchmarks/enth/evidence/restart-bundle-001'
    evidence.mkdir(exist_ok=False)
    for name in ('preflight.json','manifest.json'): shutil.copy2(root/name,evidence/name)
    (evidence/'archive.json').write_text(json.dumps({'path':str(destination),'bytes':destination.stat().st_size,
        'sha256':digest(destination),'status':'prepared_not_launched'},indent=2)+'\n')
    print(json.dumps({'status':report['status'],'checkpoint':checkpoint,'archive':str(destination),
                      'bytes':destination.stat().st_size,'sha256':digest(destination)},indent=2))


if __name__ == '__main__': main()
