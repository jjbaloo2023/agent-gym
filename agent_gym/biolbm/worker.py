# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jophin Joseph
"""Fixed-entry worker for the agent-facing bounded API."""
import json
from pathlib import Path
import sys


def validate(request):
    if sys.version_info < (3, 12):
        raise ValueError('BioLBM requires a dedicated Python 3.12+ environment')
    kind = request['kind']
    config = request['config']
    if kind == 'benchmark':
        from .config import Case, case_dict
        case = Case(**config)
        normalized = case_dict(case)
        estimate = case.estimate()
        runnable = True
    elif kind == 'vessel':
        from dataclasses import asdict
        from .bioreactor.geometry import Geometry
        from .bioreactor.workflow import Settings
        case = Settings(**config)
        normalized = asdict(case)
        estimate = case.scaling(Geometry())
        runnable = estimate['passes_tau_envelope']
        if case.threads > 2:
            raise ValueError('Agent vessel jobs are limited to two CPU threads')
    else:
        raise ValueError('Unknown BioLBM case kind')
    cells = estimate.get('cells', estimate.get('grid_cells'))
    limit = 250_000 if case.device == 'cpu' else 2_000_000
    if cells > limit or case.steps > 2000 or case.report_interval > 100:
        raise ValueError('Agent budget exceeded: CPU 250k/GPU 2M cells, 2000 steps, reporting <=100 steps')
    return {'kind': kind, 'config': normalized, 'estimate': estimate, 'runnable': runnable,
            'hardware_checked': False, 'validation_scope': 'configuration only; not physical validation'}


def main():
    try:
        if sys.argv[1] == 'validate':
            print(json.dumps(validate(json.load(sys.stdin)), allow_nan=False))
            return 0
        if sys.argv[1] != 'run' or len(sys.argv) != 3:
            raise ValueError('Expected validate or run <internally-created-folder>')
        folder = Path(sys.argv[2])
        request = json.loads((folder / 'request.json').read_text())
        checked = validate(request)
        if not checked['runnable']:
            raise ValueError('Case fails numerical envelope')
        if request['kind'] == 'benchmark':
            import torch
            torch.set_num_threads(2)
            from .config import Case
            from .runner import run
            summary = run(Case(**checked['config']), folder / 'results')
            return 1 if summary.get('benchmark_passed') is False else 0
        from .bioreactor.workflow import Settings, execute
        execute(Settings(**checked['config']), folder / 'results')
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
