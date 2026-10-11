#!/usr/bin/env python3
"""Continue validation-007 checkpoints within its original absolute deadline.

No new MD allocation: existing TPR nsteps, command ledger and 30-minute start
time are retained. Caller must supply the same systemd CPU/memory boundary.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import re
import shutil
import signal
import subprocess
import time


def elapsed(root):
    start = json.loads((root / 'supervisor-start.json').read_text())['started_utc']
    return (datetime.now(timezone.utc) - datetime.fromisoformat(start.replace('Z', '+00:00'))).total_seconds()


def size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def check_md_stage(work, name, expected):
    text = (work/f'{name}.log').read_text(errors='replace')
    if re.search(r'constraint error|LINCS WARNING|Fatal error', text, re.I):
        raise RuntimeError(f'{name} has a constraint warning or fatal error')
    rows = re.findall(r'(?m)^\s*Step\s+Time\s*\n\s*(\d+)\s+([0-9.eE+\-]+)', text)
    actual = float(rows[-1][1]) if rows else None
    if not (work/f'{name}.gro').exists() or actual is None or actual < expected-0.001:
        raise RuntimeError(f'{name} incomplete: observed {actual}, requested {expected} ps')
    return {'clean_constraints': True, 'observed_duration_ps': actual, 'source': 'final log step/time row plus final coordinates'}


def worker(root):
    spec = importlib.util.spec_from_file_location('original_worker', root / 'worker.executed.py')
    original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
    report = json.loads((root / 'validation.json').read_text())
    report['started_monotonic'] = time.monotonic() - elapsed(root)
    report.pop('error', None)
    report['execution_status'] = 'running'
    report['continuation'] = {'reason': 'Inherited 0.10-hour warmup sublimit stopped at 7 ps; continue checkpoint within original 1800-second deadline',
                              'initial_supervisor_report': 'supervisor-result.json',
                              'model': 'gpt-6-astra', 'reasoning_effort': 'high',
                              'independent_model_score': False}
    work = root / 'run'
    md_args = ['-ntmpi', '1', '-ntomp', '2', '-pin', 'off', '-nb', 'cpu', '-pme', 'cpu', '-bonded', 'cpu']
    try:
        if not (work / 'nvt.cpt').exists() or (work / 'npt_restraint.tpr').exists():
            raise RuntimeError('This continuation requires the interrupted NVT checkpoint only')
        # Exact checkpoint continuation retains RNG state, velocities, annealing
        # time and original 5000-step TPR endpoint; GROMACS checks append hashes.
        if not (work/'nvt.gro').exists():
            cp = original.run(['gmx', 'mdrun', '-s', 'nvt.tpr', '-deffnm', 'nvt', '-cpi', 'nvt.cpt', '-append'] + md_args, work, report)
            if cp.returncode: raise RuntimeError('NVT checkpoint continuation failed')
        report['nvt_gate'] = check_md_stage(work, 'nvt', 10.0)
        original.write_mdp(work / 'npt_restraint.mdp', 'npt_restraint')
        cp = original.run(['gmx', 'grompp', '-f', 'npt_restraint.mdp', '-c', 'nvt.gro', '-r', 'nvt.gro', '-t', 'nvt.cpt', '-p', 'topol.top', '-o', 'npt_restraint.tpr'], work, report)
        if cp.returncode: raise RuntimeError('Restrained NPT preprocessing failed')
        cp = original.run(['gmx', 'mdrun', '-s', 'npt_restraint.tpr', '-deffnm', 'npt_restraint'] + md_args, work, report)
        if cp.returncode: raise RuntimeError('Restrained NPT failed')
        report['npt_restraint_gate'] = check_md_stage(work, 'npt_restraint', 10.0)
        original.write_mdp(work / 'npt_release.mdp', 'npt_release')
        cp = original.run(['gmx', 'grompp', '-f', 'npt_release.mdp', '-c', 'npt_restraint.gro', '-t', 'npt_restraint.cpt', '-p', 'topol.top', '-o', 'npt.tpr'], work, report)
        if cp.returncode: raise RuntimeError('Released NPT preprocessing failed')
        cp = original.run(['gmx', 'mdrun', '-s', 'npt.tpr', '-deffnm', 'npt'] + md_args, work, report)
        if cp.returncode: raise RuntimeError('Released NPT failed')
        report['release_gate'] = check_md_stage(work, 'npt', 80.0)
        report['execution_status'] = 'completed'
        report['summary'] = 'All requested dynamics stages completed; independent analysis pending.'
    except Exception as exc:
        report['execution_status'] = 'failed_or_interrupted'
        report['error'] = f'{type(exc).__name__}: {exc}'
        report['summary'] = 'Checkpoint continuation stopped; inspect observed trajectory duration and independent analysis.'
    report['analysis_status'] = 'independent_analysis_pending'
    report['interpretation'] = 'Reconstructed inserted-state workflow only; no scientific agreement assessed.'
    original.write_report(root, report)
    return 0 if report['execution_status'] == 'completed' else 1


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--workdir', type=Path, required=True); ap.add_argument('--worker', action='store_true')
    args = ap.parse_args(); root = args.workdir.resolve()
    if root != Path('/home/gym/agent-gym-md/validation-007'):
        raise ValueError('Only the existing validation-007 retry is authorized')
    if args.worker: return worker(root)
    lock = (root.parent / '.validation.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if elapsed(root) >= 1680 or (root / 'continuation-01-start.json').exists():
        raise RuntimeError('Insufficient original budget or two continuations already attempted')
    if (root / 'continuation-start.json').exists():
        if not (root/'run/nvt.gro').exists(): raise RuntimeError('Second segment requires completed NVT')
        for path in list(root.glob('continuation*')):
            if path.is_file(): shutil.copy2(path, root/path.name.replace('continuation', 'continuation-01', 1))
        shutil.copy2(root/'validation.json', root/'validation-after-nvt-continuation.json')
    resource.setrlimit(resource.RLIMIT_FSIZE, (256*1024**2, 256*1024**2))
    snapshot = root / 'continuation.executed.py'; shutil.copy2(__file__, snapshot)
    if not (root/'validation-before-continuation.json').exists():
        shutil.copy2(root / 'validation.json', root / 'validation-before-continuation.json')
        shutil.copy2(root / 'command-ledger.json', root / 'command-ledger-before-continuation.json')
    record = {'original_started_utc': json.loads((root/'supervisor-start.json').read_text())['started_utc'],
              'started_utc': datetime.now(timezone.utc).isoformat(), 'elapsed_at_resume_seconds': elapsed(root),
              'absolute_total_wall_limit_seconds': 1800, 'worker_sha256': hashlib.sha256(snapshot.read_bytes()).hexdigest(),
              'note': 'Same trajectory/checkpoint and original absolute deadline; no new wall allocation'}
    (root / 'continuation-start.json').write_text(json.dumps(record, indent=2))
    reason = None; graceful = False
    with (root/'continuation.stdout.log').open('w') as out, (root/'continuation.stderr.log').open('w') as err:
        proc = subprocess.Popen(['/opt/agent-gym-cad/bin/python', str(snapshot), '--workdir', str(root), '--worker'],
                                stdout=out, stderr=err, start_new_session=True,
                                env={**os.environ, 'OMP_NUM_THREADS':'2', 'OPENBLAS_NUM_THREADS':'1'})
        while proc.poll() is None:
            if elapsed(root) >= 1740 and not graceful:
                for item in Path('/proc').iterdir():
                    if not item.name.isdigit(): continue
                    try:
                        cmd = (item/'cmdline').read_bytes().split(b'\0')
                        if (item/'exe').resolve() == Path('/usr/bin/gmx') and b'mdrun' in cmd and (item/'cwd').resolve() == root/'run':
                            os.kill(int(item.name), signal.SIGTERM)
                    except (FileNotFoundError, ProcessLookupError, PermissionError): pass
                graceful = True
            if elapsed(root) >= 1790: reason = 'original_wall_limit'
            elif size(root) >= 1024**3: reason = 'aggregate_output_limit'
            if reason:
                os.killpg(proc.pid, signal.SIGTERM)
                try: proc.wait(timeout=3)
                except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL)
                break
            time.sleep(0.5)
        record.update(returncode=proc.wait(), terminated_reason=reason, graceful_stop_requested=graceful,
                      total_elapsed_seconds=elapsed(root), output_bytes=size(root))
    record['files'] = [{'path': str(p.relative_to(root)), 'bytes': p.stat().st_size,
                        'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(root.rglob('*')) if p.is_file()]
    (root/'continuation-result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps({k:v for k,v in record.items() if k != 'files'}, indent=2), flush=True)
    return 0 if record['returncode'] == 0 and reason is None else 1


if __name__ == '__main__': raise SystemExit(main())
