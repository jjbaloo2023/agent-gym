"""Export a compact, inspectable successful interruption experiment to Git."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument('--run', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root, out = args.run.resolve(), args.output.resolve()
if out.exists():
    raise ValueError('Refuse to overwrite evidence')
result = json.loads((root/'verification.json').read_text())
if not result['passed']:
    raise ValueError('Package only a run with passing verification')
out.mkdir(parents=True)
for name in ['protocol.json', 'trajectory.jsonl', 'verification.json']:
    shutil.copyfile(root/name, out/name)
shutil.copyfile(Path(__file__).with_name('demo-cfd-interruption.py'), out/'reproduce.py')
for case, label in [('control', 'uninterrupted'), ('recovered', 'interrupted'), ('recovered', 'restarted')]:
    (out/(label+'.log.gz')).write_bytes(gzip.compress((root/case/(label+'.log')).read_bytes(), mtime=0))
with tarfile.open(out/'case-inputs.tar.gz', 'w:gz') as tar:
    for name in ['0', 'constant', 'system']:
        tar.add(root/'control'/name, arcname='case/'+name)
for name, source in [('checkpoint', root/'restart-checkpoint'),
                     ('control-final', root/'control'/result['reference_final_time']),
                     ('recovered-final', root/'recovered'/result['recovered_final_time'])]:
    with tarfile.open(out/(name+'.tar.gz'), 'w:gz') as tar:
        for field in ['p', 'U', 'phi']:
            tar.add(source/field, arcname=('checkpoint/' if name == 'checkpoint' else 'fields/')+field)
version = subprocess.run(['bash', '-lc', 'source /opt/openfoam14/etc/bashrc; foamVersion'],
                         capture_output=True, text=True, check=True).stdout.strip()
(out/'versions.json').write_text(json.dumps({'openfoam': version, 'python': __import__('sys').version,
    'platform': __import__('platform').platform(), 'case_origin': 'Luna C, laminar recovery, 8246 cells',
    'run_path': str(root), 'dataset_eligibility': 'unreviewed',
    'source_rights': 'Locally generated mesh and solver evidence; source drawing/PDF and model text not included'}, indent=2)+'\n')
(out/'README.md').write_text('''# Inspectable CFD interruption run

This bundle records one controlled failure-and-recovery episode, plus an uninterrupted control. It contains no source drawing, model conversation or credentials.

## Read the trajectory

1. `trajectory.jsonl` records tool starts, the injected failure, detection, correction and checks.
2. `interrupted.log.gz` records solver progress before SIGSTOP. The trajectory records kernel state `T (stopped)` and termination with return code -9.
3. `checkpoint.tar.gz` contains the saved p, U and phi fields used for restart.
4. `restarted.log.gz` shows the loaded checkpoint time and convergence. `uninterrupted.log.gz` supplies the control.
5. `verification.json` records the declared checks and measured control comparison. Final fields permit an independent recalculation.

The stall threshold was two seconds. Restart selected checkpoint 50 after interruption near iteration 60. `protocol.json` declares field-relative-L2 tolerance 1e-4 and relative flux-imbalance tolerance 1e-6. The final numerical checks passed. This does not establish physical accuracy of the Venturi simulation.

## Verify without the solver

From the repository root:

```sh
python scripts/verify-cfd-evidence.py evidence/cfd-interruption-v1
```

The verifier reads archives without extracting them, checks hashes and trajectory order, checks log evidence, and recomputes p/U/phi field differences and flow balance. It does not execute bundled code. The manifest is not an external signature.

## Repeat in WSL

Use the recorded OpenFOAM 14 environment and Python 3.11+. In the bundle directory, extract the trusted `case-inputs.tar.gz` into a new working directory. It contains `case/0`, `case/constant` and `case/system`. Then run:

```sh
python reproduce.py --source /absolute/path/to/case --output /absolute/path/to/new-demo
```

Output must not exist. The script runs serially, permits 120 seconds per launch, signals only its own solver process group, and kills that group on an exception. It leaves all output for inspection. Checkpoint timing and measured values can differ between machines.

## Limits

The interruption occurs after a complete checkpoint, between field writes. This tests a suspended solver process and checkpoint restart. It does not test power loss, partial checkpoint files, remote workers or LLM conversation persistence. The small laminar case has unresolved mesh and transition-model limits documented in the Venturi validity audit.

The first development run passed. A second run added kernel-state confirmation and checkpoint parsing; this bundle contains that second run. Full development outputs remain local.
''')
files = {str(p.relative_to(out)): {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
         for p in out.rglob('*') if p.is_file()}
(out/'manifest.json').write_text(json.dumps({'schema': 1, 'files': files}, indent=2)+'\n')
print(json.dumps({'files': len(files), 'total_bytes': sum(p.stat().st_size for p in out.rglob('*') if p.is_file())}))
