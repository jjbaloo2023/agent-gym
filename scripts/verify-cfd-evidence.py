"""Verify the compact CFD bundle offline. Does not execute bundled code."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import tarfile


def values(text):
    match = re.search(r'internalField\s+nonuniform\s+List<(scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;', text, re.S)
    if not match:
        raise ValueError('Missing nonuniform internal field')
    result = [float(x) for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', match[3])]
    expected = int(match[2]) * (3 if match[1] == 'vector' else 1)
    if not expected or len(result) != expected or not all(math.isfinite(x) for x in result):
        raise ValueError('Malformed or nonfinite field')
    return result


def verify(folder):
    manifest = json.loads((folder/'manifest.json').read_text())
    required = {'protocol.json', 'trajectory.jsonl', 'verification.json', 'case-inputs.tar.gz',
                'checkpoint.tar.gz', 'control-final.tar.gz', 'recovered-final.tar.gz',
                'uninterrupted.log.gz', 'interrupted.log.gz', 'restarted.log.gz', 'versions.json', 'reproduce.py', 'README.md'}
    if not required <= set(manifest['files']):
        raise ValueError('Manifest omits required evidence')
    for name, record in manifest['files'].items():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe manifest path')
        data = (folder/name).read_bytes()
        if len(data) != record['bytes'] or hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError('Manifest mismatch: '+name)
    protocol = json.loads((folder/'protocol.json').read_text())
    recorded = json.loads((folder/'verification.json').read_text())
    rows = [json.loads(line) for line in (folder/'trajectory.jsonl').read_text().splitlines()]
    if any(a['elapsed_s'] > b['elapsed_s'] for a, b in zip(rows, rows[1:])):
        raise ValueError('Trajectory is out of order')
    def event(name):
        selected = [r for r in rows if r['event'] == name]
        if len(selected) != 1:
            raise ValueError('Missing or duplicate event: '+name)
        return selected[0]
    injected, stalled, failed, correction = [event(n) for n in
        ['interruption_injected', 'stall_detected', 'failed_process_terminated', 'correction_selected']]
    if not (injected['kernel_process_state'].startswith('T') and injected['signal'] == 'SIGSTOP'
            and stalled['no_progress_s'] >= protocol['stall_limit_s'] and failed['returncode'] == -9
            and injected['elapsed_s'] < stalled['elapsed_s'] < failed['elapsed_s'] < correction['elapsed_s']):
        raise ValueError('Failure/recovery trajectory does not meet protocol')
    def member(archive, name):
        with tarfile.open(folder/archive, 'r:gz') as tar:
            item = tar.getmember(name)
            if not item.isfile() or item.size > 8_000_000:
                raise ValueError('Unexpected archive member')
            return tar.extractfile(item).read()
    for field in ['p', 'U', 'phi']:
        data = member('checkpoint.tar.gz', 'checkpoint/'+field)
        values(data.decode())
        if hashlib.sha256(data).hexdigest() != correction['checkpoint_hashes'][field]:
            raise ValueError('Checkpoint differs from selected restart state')
    logs = {name: gzip.decompress((folder/(name+'.log.gz')).read_bytes()).decode() for name in
            ['uninterrupted', 'interrupted', 'restarted']}
    if 'SIMPLE solution converged in' in logs['interrupted']:
        raise ValueError('Interrupted run unexpectedly converged')
    for name in ['uninterrupted', 'restarted']:
        if 'SIMPLE solution converged in' not in logs[name] or not re.search(r'^End\s*$', logs[name], re.M):
            raise ValueError('Missing convergence/exit evidence: '+name)
    loaded = re.search(r'Create mesh for time\s*=\s*([\d.eE+-]+)', logs['restarted'])
    if not loaded or float(loaded[1]) != float(correction['checkpoint']):
        raise ValueError('Restart did not load selected checkpoint')
    comparison = {}
    for field in ['p', 'U', 'phi']:
        a = values(member('control-final.tar.gz', 'fields/'+field).decode())
        b = values(member('recovered-final.tar.gz', 'fields/'+field).decode())
        if len(a) != len(b):
            raise ValueError('Field lengths differ')
        relative = math.sqrt(sum((x-y)**2 for x,y in zip(a,b))/max(sum(x*x for x in a), 1e-60))
        comparison[field] = relative
        if relative >= protocol['field_relative_l2_limit']:
            raise ValueError('Recovered field differs from control: '+field)
        if not math.isclose(relative, recorded['field_comparison'][field]['relative_l2'], rel_tol=1e-10, abs_tol=1e-15):
            raise ValueError('Recorded comparison differs from recomputed result')
    def flux(patch):
        found = re.findall(r'sum\('+patch+r'\) of phi = ([-+\d.eE]+)', logs['restarted'])
        if not found:
            raise ValueError('Missing flux evidence')
        return float(found[-1])
    qin, qout = flux('inlet'), flux('outlet')
    imbalance = abs(qin+qout)/protocol['flow_m3_s']
    if abs(abs(qin)-protocol['flow_m3_s'])/protocol['flow_m3_s'] >= 1e-8 or imbalance >= protocol['flux_relative_imbalance_limit']:
        raise ValueError('Flow verification failed')
    return {'passed': True, 'manifest_files': len(manifest['files']), 'restart_time': float(loaded[1]),
            'recomputed_relative_l2': comparison, 'relative_flux_imbalance': imbalance,
            'scope': 'offline consistency/integrity check; not external attestation or physical validation'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.bundle), indent=2))
