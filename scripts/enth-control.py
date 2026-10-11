#!/usr/bin/env python3
"""Fixed ENTH-only WSL launcher and read-only diagnostic/export operations."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import os
import signal
import hashlib
from datetime import datetime, timezone

BASE = Path('/home/gym/agent-gym-md')
REPO = Path('/mnt/c/Users/Jophi/OneDrive/Documents/ChatGPT/Agent_gym')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['status', 'preflight', 'run', 'export', 'checkpoint', 'analyze', 'continue'])
    args = parser.parse_args()
    roots = sorted(BASE.glob('validation-[0-9][0-9][0-9]'))
    if args.action == 'continue':
        root = BASE / 'validation-007'
        start = json.loads((root/'supervisor-start.json').read_text())['started_utc']
        elapsed = (datetime.now(timezone.utc)-datetime.fromisoformat(start.replace('Z','+00:00'))).total_seconds()
        remaining = int(1800-elapsed)
        if remaining < 120: raise RuntimeError('Original wall budget exhausted')
        return subprocess.call(['systemd-run', '--wait', '--pipe', '--collect',
            '--unit=agent-gym-enth-validation-007-continuation', '-p', 'User=gym', '-p', 'CPUQuota=200%',
            '-p', 'MemoryMax=4G', '-p', 'MemorySwapMax=0', '-p', 'TasksMax=64', '-p', f'RuntimeMaxSec={remaining}',
            '-p', 'NoNewPrivileges=yes', '-p', 'PrivateTmp=yes', '-p', 'ProtectSystem=strict',
            '-p', 'ProtectHome=read-only', '-p', f'ReadWritePaths={BASE}',
            '/usr/bin/python3', str(REPO/'scripts/continue-enth-bounded.py'), '--workdir', str(root)])
    if args.action == 'analyze':
        root = roots[-1]
        if (root/'independent-analysis.json').exists() and not (root/'independent-analysis-initial.json').exists():
            shutil.copy2(root/'independent-analysis.json', root/'independent-analysis-initial.json')
            shutil.copy2(root/'analyzer.executed.py', root/'analyzer-initial.executed.py')
        snapshot = root / 'analyzer.executed.py'
        shutil.copy2(REPO / 'scripts/enth_analysis.py', snapshot)
        shutil.chown(snapshot, user='gym', group='gym')
        command = ['systemd-run', '--wait', '--pipe', '--collect',
                   f'--unit=agent-gym-enth-analysis-{root.name}',
                   '-p', 'User=gym', '-p', 'CPUQuota=200%', '-p', 'MemoryMax=4G',
                   '-p', 'MemorySwapMax=0', '-p', 'RuntimeMaxSec=180',
                   '-p', 'NoNewPrivileges=yes', '-p', 'ProtectSystem=strict',
                   '-p', 'ProtectHome=read-only', '-p', f'ReadWritePaths={root}',
                   '/opt/agent-gym-cad/bin/python', str(snapshot),
                   '--workdir', str(root), '--gmx', '/usr/bin/gmx']
        result = subprocess.call(command)
        report = root / 'independent-analysis.json'
        if report.exists():
            row = json.loads(report.read_text())
            print(json.dumps({k: row.get(k) for k in ['status', 'checks', 'trajectory', 'energy', 'membrane', 'h0_dssp']}, indent=2))
        return result
    if args.action == 'checkpoint':
        root = roots[-1]
        group = Path('/sys/fs/cgroup/system.slice') / f'agent-gym-enth-{root.name}.service/cgroup.procs'
        if group.exists():
            for raw in group.read_text().split():
                pid = int(raw)
                proc = Path('/proc') / raw
                try:
                    cmd = (proc / 'cmdline').read_bytes().split(b'\0')
                    if (proc / 'exe').resolve() == Path('/usr/bin/gmx') and b'mdrun' in cmd and b'npt' in cmd:
                        if (proc / 'cwd').resolve() != root / 'run':
                            raise RuntimeError('Unexpected GROMACS working directory')
                        os.kill(pid, signal.SIGTERM)
                        print('Requested graceful checkpoint of release stage', pid)
                except FileNotFoundError:
                    pass
        return 0
    if args.action == 'status':
        for root in roots[-1:]:
            print(root.name)
            analysis = root / 'independent-analysis.json'
            if analysis.exists():
                row = json.loads(analysis.read_text())
                print(json.dumps({k: row.get(k) for k in ['status', 'all_stage_lincs_warning_count',
                                  'all_stage_constraint_error_count', 'fatal_errors']}, indent=2))
                for name, stage in row.get('stages', {}).items():
                    log = stage.get('log', {})
                    print(name, json.dumps({k: log.get(k) for k in ['lincs_warnings', 'constraint_errors', 'last_step_time_rows']}))
            report = root / 'validation.json'
            if report.exists():
                row = json.loads(report.read_text())
                print(json.dumps({k: row.get(k) for k in ['preparation_status', 'execution_status',
                      'analysis_status', 'error', 'reconstruction', 'analysis']}, indent=2))
                for command in row.get('commands', [])[-2:]:
                    print(json.dumps(command, indent=2))
            else:
                print('No final worker report yet.')
                subprocess.run(['systemctl', 'show', f'agent-gym-enth-{root.name}.service',
                                '-p', 'ActiveState', '-p', 'CPUUsageNSec', '-p', 'MemoryCurrent'])
                solv = root / 'run/solv.gro'
                if solv.exists():
                    with solv.open() as stream:
                        stream.readline()
                        print('Solvated atom count:', stream.readline().strip())
                for log in sorted((root / 'run').glob('*.log')):
                    print(log.name, log.read_text(errors='replace')[-1000:])
        return 0
    if args.action == 'export':
        dest = REPO / 'benchmarks/enth/evidence'
        dest.mkdir(exist_ok=True)
        for root in roots:
            out = dest / root.name
            out.mkdir(exist_ok=True)
            for name in ['validation.json', 'validation.md', 'supervisor-start.json',
                         'supervisor-result.json', 'workflow.stdout.log', 'workflow.stderr.log',
                         'independent-analysis.json', 'independent-analysis.md', 'command-ledger.json',
                         'worker.executed.py', 'supervisor.executed.py', 'analyzer.executed.py',
                         'continuation.executed.py', 'continuation-start.json', 'continuation-result.json',
                         'continuation.stdout.log', 'continuation.stderr.log',
                         'validation-before-continuation.json', 'command-ledger-before-continuation.json', 'provenance-audit.json',
                         'independent-analysis-initial.json', 'analyzer-initial.executed.py']:
                source = root / name
                if source.exists():
                    shutil.copy2(source, out / name)
            for source in list(root.glob('continuation-01*')) + list(root.glob('validation-after-nvt-continuation.json')):
                if source.is_file(): shutil.copy2(source, out / source.name)
            if root == roots[-1]:
                run_out = REPO / 'artifacts/enth' / root.name / 'run'
                run_out.mkdir(parents=True, exist_ok=True)
                for source in (root / 'run').glob('*'):
                    if source.is_file() and source.suffix in {'.log', '.mdp', '.xvg', '.top', '.itp', '.gro', '.dat', '.json'}:
                        shutil.copy2(source, run_out / source.name)
                manifest = [{'path': str(p.relative_to(REPO)), 'bytes': p.stat().st_size,
                             'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                            for p in sorted(run_out.glob('*')) if p.is_file()]
                (out / 'export-manifest.json').write_text(json.dumps(manifest, indent=2))
        print('Exported reports, logs, analysis and text inputs to', dest)
        return 0
    number = max([int(p.name.rsplit('-', 1)[1]) for p in roots] + [0]) + 1
    root = BASE / f'validation-{number:03d}'
    command = ['systemd-run', '--wait', '--pipe', '--collect',
               f'--unit=agent-gym-enth-{root.name}',
               '-p', 'User=gym', '-p', 'CPUQuota=200%', '-p', 'MemoryMax=4G',
               '-p', 'MemorySwapMax=0', '-p', 'TasksMax=64', '-p', 'RuntimeMaxSec=1800',
               '-p', 'NoNewPrivileges=yes', '-p', 'PrivateTmp=yes', '-p', 'ProtectSystem=strict',
               '-p', 'ProtectHome=read-only', '-p', f'ReadWritePaths={BASE}',
               '/usr/bin/python3', str(REPO / 'scripts/run-enth-bounded.py'),
               '--worker', str(REPO / 'scripts/enth_validation.py'), '--workdir', str(root)]
    if args.action == 'preflight':
        command.append('--prepare-only')
    print('Launching', root.name, args.action, flush=True)
    result = subprocess.call(command)
    report = root / 'validation.json'
    if report.exists():
        row = json.loads(report.read_text())
        print(json.dumps({k: row.get(k) for k in ['preparation_status', 'execution_status',
              'analysis_status', 'error', 'atom_count']}, indent=2), flush=True)
        if result:
            for item in row.get('commands', [])[-1:]:
                print(json.dumps(item, indent=2), flush=True)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
