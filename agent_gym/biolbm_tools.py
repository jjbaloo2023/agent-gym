"""Bounded BioLBM operations; the MCP process needs no Torch installation.

Numerics run in a separate, operator-configured Python 3.12+ environment.
The first API is synchronous, with a ten-minute limit and one local job.
It is not a durable multiuser queue or a security sandbox.
"""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import uuid
from .core import atomic_json
from .science import ROOT as SCIENCE_ROOT

ROOT = Path(os.environ.get('AGENT_GYM_BIOLBM_RUNS', str(SCIENCE_ROOT / 'biolbm'))).resolve()
TIMEOUT_SECONDS = 600


def _python():
    return os.environ.get('AGENT_GYM_BIOLBM_PYTHON', sys.executable)


def validate_case(kind, config):
    """Return normalized settings and planning bounds, without starting CFD."""
    if kind not in ('benchmark', 'vessel') or not isinstance(config, dict):
        raise ValueError('kind must be benchmark/vessel and config must be an object')
    result = subprocess.run(
        [_python(), '-m', 'agent_gym.biolbm.worker', 'validate'],
        input=json.dumps({'kind': kind, 'config': config}, allow_nan=False),
        capture_output=True, text=True, timeout=30, check=False,
    )
    if result.returncode:
        raise ValueError(result.stderr[-3000:] or 'BioLBM validation failed')
    return json.loads(result.stdout)


def _run_path(run_id):
    if not isinstance(run_id, str) or not re.fullmatch('[0-9a-f]{32}', run_id):
        raise ValueError('Expected an opaque BioLBM run ID')
    path = ROOT / run_id
    if not path.is_dir() or path.is_symlink():
        raise FileNotFoundError('Unknown BioLBM run')
    return path


def inspect_run(run_id):
    folder = _run_path(run_id)
    result = {'run_id': run_id, 'status': json.loads((folder / 'job-status.json').read_text())}
    for name in ('status.json', 'summary.json'):
        path = folder / 'results' / name
        if path.is_file():
            result[name[:-5]] = json.loads(path.read_text())
    return result


def run_case(kind, config):
    """Run inline with one-job lock, bounded inputs, timeout, and opaque ID."""
    checked = validate_case(kind, config)
    if not checked['runnable']:
        raise ValueError('Case fails the current numerical operating envelope; no fluid substitution')
    ROOT.mkdir(parents=True, exist_ok=True)
    lock = ROOT / '.active-job'
    # Do not silently remove stale locks; operator inspection is required.
    lock.mkdir()
    run_id = uuid.uuid4().hex
    folder = ROOT / run_id
    process = None
    try:
        folder.mkdir()
        atomic_json(folder / 'request.json', {'kind': kind, 'config': checked['config']})
        atomic_json(folder / 'job-status.json', {'state': 'running', 'timeout_seconds': TIMEOUT_SECONDS})
        with (folder / 'worker.log').open('w') as log:
            process = subprocess.Popen(
                [_python(), '-m', 'agent_gym.biolbm.worker', 'run', str(folder)],
                stdout=log, stderr=subprocess.STDOUT, start_new_session=(os.name == 'posix'),
            )
            try:
                code = process.wait(timeout=TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                if os.name == 'posix':
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait()
                atomic_json(folder / 'job-status.json', {'state': 'timed_out', 'timeout_seconds': TIMEOUT_SECONDS})
                return inspect_run(run_id)
        state = 'completed' if code == 0 else 'failed'
        status = {'state': state, 'returncode': code}
        if code:
            status['log_tail'] = (folder / 'worker.log').read_text(errors='replace')[-3000:]
        atomic_json(folder / 'job-status.json', status)
        return inspect_run(run_id)
    except Exception as exc:
        if folder.is_dir():
            atomic_json(folder / 'job-status.json', {'state': 'failed', 'error': str(exc)})
        raise
    finally:
        lock.rmdir()
