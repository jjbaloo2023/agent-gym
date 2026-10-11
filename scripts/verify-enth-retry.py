#!/usr/bin/env python3
"""Read-only provenance checks plus an audit report for the single Astra retry."""
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path('/home/gym/agent-gym-md/validation-007')
    previous = root.parent/'validation-006'
    load = lambda name: json.loads((root/name).read_text())
    start = load('supervisor-start.json')
    first = load('supervisor-result.json')
    final = load('continuation-result.json')
    report = load('validation.json')
    analysis = load('independent-analysis.json')
    checks = {}
    sources = []
    for source, metadata in [('worker.executed.py', 'supervisor-start.json'),
                              ('continuation-01.executed.py', 'continuation-01-start.json'),
                              ('continuation.executed.py', 'continuation-start.json')]:
        expected = load(metadata)['worker_sha256']; actual = sha(root/source)
        sources.append({'source': source, 'metadata': metadata, 'recorded_sha256': expected,
                        'actual_sha256': actual, 'matches': actual == expected})
    checks['executed_source_hashes_match'] = all(row['matches'] for row in sources)
    files = ['c36.tgz', 'popc_bilayer.tar.gz', 'pdb_1h0a.pdb', 'popc_template.pdb', 'sapi24_template.pdb']
    input_checks = [{'name': name, 'previous_sha256': sha(previous/'inputs'/name),
                     'retry_sha256': sha(root/'inputs'/name)} for name in files]
    checks['public_input_hashes_identical_to_006'] = all(row['previous_sha256'] == row['retry_sha256'] for row in input_checks)
    checks['reconstructed_complex_identical_to_006'] = sha(root/'run/inserted_complex.pdb') == sha(previous/'run/inserted_complex.pdb')
    old_tpr = next(row for row in first['files'] if row['path'] == 'run/nvt.tpr')
    checks['nvt_tpr_unchanged_across_continuation'] = sha(root/'run/nvt.tpr') == old_tpr['sha256']
    checks['all_segments_share_original_start'] = all(load(name)['original_started_utc'] == start['started_utc']
                                                       for name in ('continuation-01-start.json', 'continuation-start.json'))
    checks['total_wall_time_within_original_1800_seconds'] = final['total_elapsed_seconds'] <= 1800
    checks['scientific_workflow_commands_within_20'] = len(report['commands']) <= 20
    steps = sum(analysis['stages'][name]['expected_nsteps'] for name in ('nvt', 'npt_restraint', 'npt_release'))
    checks['requested_md_steps_within_50000'] = steps <= 50000
    checks['actual_atoms_within_100000'] = 0 < analysis['final_structure'].get('declared_atom_count', 0) <= 100000
    current_size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    checks['artifacts_after_analysis_within_1GiB'] = current_size < 1024**3
    mismatches = []
    for row in final['files']:
        # The second supervisor enumerated the previous report occupying this
        # same name before replacing it. Its self-entry is historical, and is
        # excluded explicitly; the archived first report is verified normally.
        if row['path'] == 'continuation-result.json': continue
        path = root/row['path']
        if not path.exists() or sha(path) != row['sha256']: mismatches.append(row['path'])
    checks['final_nonself_manifest_hashes_match'] = not mismatches
    result = {'model': 'gpt-6-astra', 'reasoning_effort': 'high', 'attribution': 'assisted retry; inherited inputs/code and parent orchestration',
              'independent_model_score': False, 'checks': checks, 'all_provenance_checks_passed': all(checks.values()),
              'executed_sources': sources, 'input_comparison': input_checks, 'manifest_mismatches': mismatches,
              'manifest_exclusion': 'continuation-result.json self-entry refers to the previous report before replacement; archived continuation-01-result.json is retained and checked',
              'analyzer_sha256': sha(root/'analyzer.executed.py'), 'total_elapsed_seconds': final['total_elapsed_seconds'],
              'output_bytes_after_analysis': current_size, 'scientific_workflow_command_count': len(report['commands']),
              'requested_md_steps': steps, 'observed_saved_dynamics_ps': analysis['trajectory']['observed_last_time_ps'],
              'analysis_scope': 'Independent read-only analysis and provenance verification performed after the shared MD wall window',
              'final_analysis_scientific_command_count': len(analysis['commands']),
              'analysis_attempts': 2 if (root/'independent-analysis-initial.json').exists() else 1,
              'analysis_scientific_command_count': len(analysis['commands']) +
                  (len(load('independent-analysis-initial.json')['commands']) if (root/'independent-analysis-initial.json').exists() else 0),
              'additional_checkpoint_inspection_command': 'gmx dump -cp run/npt.cpt; step/time captured separately in exported checkpoint-time.txt'}
    (root/'provenance-audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__': raise SystemExit(main())
