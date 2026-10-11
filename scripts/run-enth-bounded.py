#!/usr/bin/env python3
"""Supervise a single WSL ENTH workflow inside an external systemd cgroup.

The cgroup supplies CPU/memory/process-tree limits; this supervisor supplies
an independent wall clock, an aggregate-size monitor, logs, and a manifest.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time


def size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workdir', type=Path, required=True)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    root = args.workdir.resolve()
    base = Path('/home/gym/agent-gym-md')
    if root.parent != base or not root.name.startswith('validation-'):
        raise ValueError('Use a dedicated validation directory under /home/gym/agent-gym-md')
    root.mkdir(parents=True, exist_ok=False)
    lock = (base / '.validation.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2, 256 * 1024**2))
    snapshot = root / 'worker.executed.py'
    snapshot.write_bytes(args.worker.read_bytes())
    (root / 'supervisor.executed.py').write_bytes(Path(__file__).read_bytes())
    command = ['/opt/agent-gym-cad/bin/python', str(snapshot), '--workdir', str(root)]
    if args.prepare_only:
        command.append('--prepare-only')
    start = time.monotonic()
    record = {'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'command': command, 'worker_sha256': digest(args.worker),
              'wall_limit_seconds': 1800, 'output_limit_bytes': 1024**3,
              'output_poll_seconds': 0.5, 'single_file_limit_bytes': 256 * 1024**2,
              'note': 'Aggregate output is monitored, not a filesystem quota; overshoot between polls is possible.'}
    (root / 'supervisor-start.json').write_text(json.dumps(record, indent=2))
    with (root / 'workflow.stdout.log').open('w') as stdout, (root / 'workflow.stderr.log').open('w') as stderr:
        proc = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True,
                                env={**os.environ, 'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '1'})
        reason = None
        graceful_stop_requested = False
        while proc.poll() is None:
            # Give GROMACS time to checkpoint and the worker time to save its
            # evidence before the whole-process-tree deadline.
            if time.monotonic() - start >= 1740 and not graceful_stop_requested:
                for item in Path('/proc').iterdir():
                    if not item.name.isdigit():
                        continue
                    try:
                        cmd = (item / 'cmdline').read_bytes().split(b'\0')
                        if (item / 'exe').resolve() == Path('/usr/bin/gmx') and b'mdrun' in cmd:
                            if (item / 'cwd').resolve() == root / 'run':
                                os.kill(int(item.name), signal.SIGTERM)
                    except (FileNotFoundError, ProcessLookupError, PermissionError):
                        pass
                graceful_stop_requested = True
            if time.monotonic() - start >= 1790:
                reason = 'wall_limit'
            elif size(root) >= 1024**3:
                reason = 'aggregate_output_limit'
            if reason:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                break
            time.sleep(0.5)
        record.update(returncode=proc.wait(), terminated_reason=reason,
                      graceful_stop_requested=graceful_stop_requested,
                      elapsed_seconds=round(time.monotonic() - start, 3), output_bytes=size(root))
    record['files'] = [{'path': str(p.relative_to(root)), 'bytes': p.stat().st_size, 'sha256': digest(p)}
                       for p in sorted(root.rglob('*')) if p.is_file()]
    (root / 'supervisor-result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps({k: v for k, v in record.items() if k != 'files'}, indent=2), flush=True)
    return 0 if record['returncode'] == 0 and not reason else 1


if __name__ == '__main__':
    raise SystemExit(main())
