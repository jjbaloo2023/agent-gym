"""Linux/OpenFOAM experiment: injected stall, checkpoint restart, control comparison.

Run only in a dedicated output directory. Source case stays unchanged.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def field_values(path):
    text = path.read_text()
    match = re.search(r"internalField\s+nonuniform\s+List<(scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;", text, re.S)
    if not match:
        raise ValueError(f"Expected nonuniform internal field: {path}")
    numbers = [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", match[3])]
    expected = int(match[2]) * (3 if match[1] == 'vector' else 1)
    if len(numbers) != expected or not all(math.isfinite(x) for x in numbers):
        raise ValueError(f"Invalid field values: {path}")
    return numbers


def compare_fields(left, right):
    result = {}
    for field in ['p', 'U', 'phi']:
        a, b = field_values(left / field), field_values(right / field)
        if len(a) != len(b):
            raise ValueError('Field sizes differ')
        rms = math.sqrt(sum((x-y)**2 for x, y in zip(a, b)) / len(a))
        scale = math.sqrt(sum(x*x for x in a) / len(a))
        result[field] = {'count': len(a), 'absolute_rms': rms, 'relative_l2': rms/max(scale, 1e-30)}
    return result


def progress(log):
    text = log.read_text(errors='replace') if log.exists() else ''
    times = re.findall(r'^Time = ([\d.eE+-]+)', text, re.M)
    return (float(times[-1]) if times else 0), text


def checkpoint(case):
    candidates = []
    for path in case.iterdir():
        if path.is_dir() and re.fullmatch(r'\d+(?:\.\d+)?', path.name):
            if all((path/f).is_file() for f in ['p', 'U', 'phi']):
                candidates.append(path)
    return max(candidates, key=lambda p: float(p.name)) if candidates else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.output.resolve()
    if out.exists():
        raise ValueError('Output must be new; no overwrite allowed')
    if source == out or source in out.parents:
        raise ValueError('Output must be outside the source case')
    out.mkdir(parents=True)
    start = time.monotonic()
    trajectory = out/'trajectory.jsonl'

    def event(kind, **data):
        row = {'elapsed_s': round(time.monotonic()-start, 4), 'event': kind, **data}
        with trajectory.open('a') as stream:
            stream.write(json.dumps(row, allow_nan=False)+'\n')
        print(json.dumps(row), flush=True)

    source_hashes = {str(p.relative_to(source)): digest(p) for folder in ['0', 'constant', 'system']
                     for p in (source/folder).rglob('*') if p.is_file()}
    protocol = {'flow_m3_s': 5e-5, 'nu_m2_s': 1.004e-6, 'rho_kg_m3': 998.2,
                'injection': 'SIGSTOP after a complete positive checkpoint',
                'checkpoint_interval_iterations': 50, 'stall_limit_s': 2,
                'wall_limit_s_per_launch': 120, 'field_relative_l2_limit': 1e-4,
                'flux_relative_imbalance_limit': 1e-6,
                'claim': 'solver process stall recovery; not physical CFD validation or power-loss recovery'}
    (out/'protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')

    for name in ['control', 'recovered']:
        case = out/name
        case.mkdir()
        for folder in ['0', 'constant', 'system']:
            shutil.copytree(source/folder, case/folder)
        # A copied steady restart-time dictionary must not define the new time zero.
        inherited = case/'0/uniform/time'
        if inherited.exists():
            inherited.rename(case/'system/source-time-metadata')
        control = case/'system/controlDict'
        text = control.read_text()
        for key, value in [('startFrom', 'startTime'), ('startTime', '0'), ('endTime', '1200'),
                           ('writeInterval', '50'), ('writePrecision', '14')]:
            text = re.sub(r'\b'+key+r'\s+[^;]+;', key+' '+value+';', text)
        control.write_text(text)
    event('prepared', source_hashes=source_hashes)

    def launch(case, label, inject=False):
        log = case/(label+'.log')
        env = {**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}
        command = ['bash', '-lc', 'source /opt/openfoam14/etc/bashrc; exec foamRun -solver incompressibleFluid']
        paused = False
        last_progress = 0
        progress_at = time.monotonic()
        began = progress_at
        proc = None
        try:
            with log.open('w') as stream:
                proc = subprocess.Popen(command, cwd=case, env=env, stdout=stream,
                                        stderr=subprocess.STDOUT, start_new_session=True)
                event('solver_started', label=label, pid=proc.pid)
                while proc.poll() is None:
                    now = time.monotonic()
                    current, _ = progress(log)
                    if current > last_progress:
                        last_progress, progress_at = current, now
                    saved = checkpoint(case)
                    if inject and not paused and saved and float(saved.name) >= 50 and current >= 60:
                        os.killpg(proc.pid, signal.SIGSTOP)
                        state_path = Path(f'/proc/{proc.pid}/status')
                        for _ in range(100):
                            state = re.search(r'^State:\s*(.+)$', state_path.read_text(), re.M)[1]
                            if state.startswith('T'):
                                break
                            time.sleep(0.005)
                        if not state.startswith('T'):
                            raise RuntimeError('Kernel did not confirm stopped process')
                        paused = True
                        progress_at = now
                        event('interruption_injected', signal='SIGSTOP', last_iteration=current,
                              checkpoint=saved.name, kernel_process_state=state)
                    if paused and now-progress_at >= protocol['stall_limit_s']:
                        event('stall_detected', no_progress_s=round(now-progress_at, 4), last_iteration=current)
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=10)
                        event('failed_process_terminated', signal='SIGKILL', returncode=proc.returncode)
                        break
                    if now-began > protocol['wall_limit_s_per_launch']:
                        raise TimeoutError(label+' exceeded wall limit')
                    time.sleep(0.02 if inject and not paused else 0.1)
        finally:
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
        _, text = progress(log)
        result = {'returncode': proc.returncode, 'wall_s': round(time.monotonic()-began, 4),
                  'converged': 'SIMPLE solution converged in' in text, 'injected': paused}
        event('solver_exited', label=label, **result)
        return result

    control_run = launch(out/'control', 'uninterrupted')
    interrupted_run = launch(out/'recovered', 'interrupted', inject=True)
    if not interrupted_run['injected'] or interrupted_run['returncode'] != -signal.SIGKILL:
        raise RuntimeError('Interruption was not demonstrated')
    saved = checkpoint(out/'recovered')
    if saved is None or float(saved.name) <= 0:
        raise RuntimeError('No complete positive checkpoint')
    saved_hashes = {f: digest(saved/f) for f in ['p', 'U', 'phi']}
    for field in ['p', 'U', 'phi']:
        field_values(saved/field)
    shutil.copytree(saved, out/'restart-checkpoint')
    control = out/'recovered/system/controlDict'
    control.write_text(re.sub(r'\bstartFrom\s+[^;]+;', 'startFrom latestTime;', control.read_text()))
    event('correction_selected', action='restart latest complete checkpoint', checkpoint=saved.name,
          checkpoint_hashes=saved_hashes)
    restart_run = launch(out/'recovered', 'restarted')
    restart_text = (out/'recovered/restarted.log').read_text()
    created = re.search(r'Create mesh for time\s*=\s*([\d.eE+-]+)', restart_text)
    restart_time = float(created[1]) if created else None
    left, right = checkpoint(out/'control'), checkpoint(out/'recovered')
    comparison = compare_fields(left, right)
    def flux(text, patch):
        values = re.findall(r'sum\('+patch+r'\) of phi = ([-+\d.eE]+)', text)
        return float(values[-1]) if values else None
    qin, qout = flux(restart_text, 'inlet'), flux(restart_text, 'outlet')
    imbalance = abs(qin+qout)/5e-5 if qin is not None and qout is not None else math.inf
    source_unchanged = all(digest(source/rel) == value for rel, value in source_hashes.items())
    checks = {'actual_stall_injected': interrupted_run['injected'],
              'failed_process_killed': interrupted_run['returncode'] == -signal.SIGKILL,
              'restart_loaded_saved_time': restart_time == float(saved.name),
              'control_converged': control_run['converged'] and control_run['returncode'] == 0,
              'restart_converged': restart_run['converged'] and restart_run['returncode'] == 0,
              'fields_match_control': all(v['relative_l2'] < protocol['field_relative_l2_limit'] for v in comparison.values()),
              'target_flow': qin is not None and abs(abs(qin)-5e-5)/5e-5 < 1e-8,
              'flux_balance': imbalance < protocol['flux_relative_imbalance_limit'],
              'source_unchanged': source_unchanged}
    result = {'passed': all(checks.values()), 'checks': checks, 'control': control_run,
              'interrupted': interrupted_run, 'restart': restart_run, 'restart_time': restart_time,
              'reference_final_time': left.name, 'recovered_final_time': right.name,
              'field_comparison': comparison, 'inlet_flux_m3_s': qin, 'outlet_flux_m3_s': qout,
              'relative_flux_imbalance': imbalance, 'protocol': protocol}
    (out/'verification.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    event('verification', passed=result['passed'], checks=checks)
    if not result['passed']:
        raise SystemExit('Recovery verification failed; preserve output and investigate')


if __name__ == '__main__':
    main()
