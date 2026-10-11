#!/usr/bin/env python3
"""Single-GPU ENTH equilibration with durable, immutable segment snapshots."""
import argparse
from datetime import datetime, timezone
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
from enth_analysis import contact_audit, parse_gro, leaflet_analysis

WARNING = re.compile(r'LINCS WARNING|constraint error|Fatal error|Segmentation fault', re.I)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite_energy(text):
    rows = []
    for line in text.splitlines():
        if line.strip() and not line.startswith(('#', '@')):
            values = [float(x) for x in line.split()]
            if not all(math.isfinite(x) for x in values):
                raise RuntimeError('Nonfinite energy observable')
            rows.append(values)
    if not rows:
        raise RuntimeError('No energy samples recovered')
    temperatures = [r[2] for r in rows]
    volumes = [r[4] for r in rows]
    result = {'samples': len(rows), 'start_ps': rows[0][0], 'end_ps': rows[-1][0],
              'temperature_mean_K': sum(temperatures)/len(temperatures),
              'temperature_min_K': min(temperatures), 'temperature_max_K': max(temperatures),
              'volume_start_nm3': volumes[0], 'volume_end_nm3': volumes[-1],
              'volume_change_percent': 100*(volumes[-1]/volumes[0]-1)}
    if min(volumes) <= 0 or not 250 < result['temperature_mean_K'] < 350:
        raise RuntimeError('Energy sanity check failed: ' + str(result))
    if abs(result['volume_change_percent']) > 20:
        raise RuntimeError('Volume changed more than 20% within segment')
    return result


def final_time(log):
    rows = re.findall(r'Step\s+Time\s*\n\s*(\d+)\s+([0-9.eE+\-]+)', log)
    return float(rows[-1][1]) if rows else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--durable', type=Path, required=True)
    parser.add_argument('--gmx', default='/content/enth-gpu/install/bin/gmx')
    parser.add_argument('--hours', type=float, default=8)
    parser.add_argument('--target-ns', type=float, default=70)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--continue-validated', action='store_true')
    args = parser.parse_args()
    if not 0 < args.hours <= 8 or not 0 < args.target_ns <= 70:
        raise ValueError('Session cap is 8 hours and first-phase target is 70 ns')
    if args.output.exists():
        raise FileExistsError('Use a new output directory; earlier evidence is immutable')
    if not args.durable.is_dir():
        raise RuntimeError('Durable checkpoint directory must already exist')
    parent_report = None
    if args.continue_validated:
        parent_report = json.loads((args.inputs/'colab-run.json').read_text())
        if parent_report.get('status') != 'short_gpu_validation_completed':
            raise RuntimeError('Continuation requires an accepted short GPU validation')
        if not all((args.inputs/n).exists() for n in ('validation.cpt','validation.tpr','validation.edr','validation.log','validation.xtc')):
            raise RuntimeError('Validated checkpoint/output set incomplete')
    started = time.monotonic()
    deadline = started + args.hours*3600
    shutil.copytree(args.inputs, args.output)
    work = args.output
    if parent_report is not None:
        (work/'parent-validation-report.json').write_text(json.dumps(parent_report,indent=2))
    report = {'status': 'running', 'phase': 'inserted_state_equilibration',
              'started_utc': datetime.now(timezone.utc).isoformat(),
              'wall_hours_cap': args.hours, 'target_ns': args.target_ns,
              'gpu_count': 1, 'cpu_threads': 2, 'paid_purchase': False,
              'commands': [], 'segments': [], 'biological_agreement': 'not_tested'}
    env = {**os.environ, 'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '1'}

    def persist():
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        (work/'colab-run.json').write_text(json.dumps(report, indent=2))

    def command(arguments, name, stdin=None, md=False, md_log=None, analysis=False):
        if not analysis and time.monotonic() > deadline-90:
            raise TimeoutError('Session budget exhausted; checkpoints preserved')
        persist()
        command_deadline = deadline + (120 if analysis else 0)
        outpath = work/(name+'.console.log')
        with outpath.open('w') as output:
            proc = subprocess.Popen([args.gmx]+arguments, cwd=work, env=env,
                                    stdin=subprocess.PIPE if stdin else subprocess.DEVNULL,
                                    stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            if stdin:
                proc.stdin.write(stdin.encode()); proc.stdin.close()
            graceful = False
            kill_at = None
            next_backup = time.monotonic()+300
            try:
                while proc.poll() is None:
                    now = time.monotonic()
                    if now > command_deadline-90 and not graceful:
                        os.killpg(proc.pid, signal.SIGTERM); graceful = True
                    if graceful and kill_at is None:
                        kill_at = now+60
                    if now > command_deadline-15 or (kill_at is not None and now > kill_at):
                        os.killpg(proc.pid, signal.SIGKILL)
                    if md and now >= next_backup:
                        next_backup = now+300
                        checkpoint = work/((md_log or name)+'.cpt')
                        if checkpoint.exists():
                            backup = args.durable/('periodic-'+name+'-'+str(int(now-started)))
                            backup.mkdir()
                            before = digest(checkpoint)
                            shutil.copy2(checkpoint, backup/checkpoint.name)
                            if digest(backup/checkpoint.name) != before or digest(checkpoint) != before:
                                (backup/'COPY_INCOMPLETE.txt').write_text('Checkpoint changed during copy; use a verified snapshot instead.')
                            else:
                                selected_tpr = work/('extended.tpr' if md_log else name+'.tpr')
                                shutil.copy2(selected_tpr, backup/selected_tpr.name)
                                (backup/'checkpoint-sha256.txt').write_text(before)
                                shutil.copy2(work/'colab-run.json',backup/'colab-run.json')
                                print('Periodic checkpoint:',backup,flush=True)
                    total = sum(p.stat().st_size for root in (work,args.durable) for p in root.rglob('*') if p.is_file())
                    if total > 2*1024**3 and not graceful:
                        os.killpg(proc.pid, signal.SIGTERM); graceful = True
                    if md:
                        stage_log = work/((md_log or name)+'.log')
                        if stage_log.exists() and WARNING.search(stage_log.read_text(errors='replace')):
                            os.killpg(proc.pid, signal.SIGTERM)
                            try:
                                proc.wait(timeout=30)
                            except subprocess.TimeoutExpired:
                                os.killpg(proc.pid, signal.SIGKILL); proc.wait()
                            raise RuntimeError('Physical warning in '+name)
                    time.sleep(2)
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL); proc.wait()
        result = {'arguments': arguments, 'name': name, 'returncode': proc.returncode,
                  'graceful_stop_requested': graceful, 'log_sha256': digest(outpath)}
        report['commands'].append(result); persist()
        if proc.returncode and not graceful:
            raise RuntimeError(name+' failed; inspect '+str(outpath))
        return graceful

    def snapshot(label, full=False):
        dest = args.durable/label
        if dest.exists():
            raise FileExistsError('Durable snapshot already exists: '+str(dest))
        dest.mkdir()
        records = []
        for p in sorted(work.rglob('*')):
            if p.is_file() and p.suffix in ({'.cpt','.tpr','.gro','.log','.json','.mdp','.top','.itp','.xvg','.xtc','.edr','.dat'} if full else {'.cpt','.tpr','.gro','.json','.xvg'}) and (full or p.name in {'validation.cpt','extended.tpr','validation.tpr','validation.gro','colab-run.json'} or p.name == label+'-energy.xvg' or (label.endswith('-complete') and p.name in {label[:-9]+ext for ext in ('.cpt','.tpr','.gro')})):
                relative = p.relative_to(work)
                target = dest/relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)
                if digest(target) != digest(p):
                    raise IOError('Durable copy hash mismatch: '+str(relative))
                records.append({'path': str(relative), 'sha256': digest(p), 'bytes':p.stat().st_size})
        (dest/'snapshot-manifest.json').write_text(json.dumps(records,indent=2))
        print('Durable checkpoint:',dest,flush=True)

    mdargs = ['-ntmpi','1','-ntomp','2','-pin','off','-nb','gpu','-pme','gpu','-bonded','auto','-update','cpu','-gpu_id','0','-cpt','5']
    last = 'ions'
    try:
        snapshot('inputs', full=True)
        for stage in ([] if args.continue_validated else ['em_relax','em','nvt','npt_restraint','validation']):
            mdp = stage+'.mdp'
            if stage in {'nvt','npt_restraint','validation'}:
                text = (work/('npt_release.mdp' if stage == 'validation' else mdp)).read_text()
                steps = 250000 if stage == 'npt_restraint' else 50000
                text = re.sub(r'(?m)^nsteps\s*=.*$', 'nsteps = '+str(steps), text)
                if stage == 'nvt':
                    text = re.sub(r'(?m)^annealing-time\s*=.*$', 'annealing-time = 0 100', text)
                text = re.sub(r'(?m)^nstxout-compressed\s*=.*$', 'nstxout-compressed = 50000', text)
                (work/mdp).write_text(text)
            preprocess = ['grompp','-f',mdp,'-c',last+'.gro','-p','topol.top','-o',stage+'.tpr']
            if stage in {'nvt','npt_restraint'}:
                preprocess += ['-r',last+'.gro']
            if stage in {'npt_restraint','validation'}:
                preprocess += ['-t',last+'.cpt']
            command(preprocess,stage+'-grompp')
            stage_args = mdargs.copy()
            if stage.startswith('em'):
                stage_args[stage_args.index('-pme')+1] = 'cpu'
            command(['mdrun','-s',stage+'.tpr','-deffnm',stage]+stage_args,stage,md=True)
            log = (work/(stage+'.log')).read_text(errors='replace')
            if WARNING.search(log):
                raise RuntimeError('Physical warning in '+stage)
            if stage.startswith('em'):
                if not re.search(r'Steepest Descents converged to Fmax <\s*1000',log):
                    raise RuntimeError(stage+' failed force convergence')
            else:
                expected = 500 if stage == 'npt_restraint' else 100
                if (final_time(log) or -1) < expected-0.001:
                    raise RuntimeError(stage+' stopped before requested duration')
            last = stage
            snapshot(stage+'-complete')
        command(['energy','-f','validation.edr','-o','validation-energy.xvg'], 'validation-energy', 'Potential\nTemperature\nPressure\nVolume\n0\n')
        geometry = parse_gro(work/'validation.gro')
        report['validation_leaflets'] = leaflet_analysis(geometry)
        report['validation_contacts'] = contact_audit(work/'validation.gro')
        if geometry.get('parsed_atom_count') != geometry.get('declared_atom_count') or not all(math.isfinite(x) for atom in geometry.get('atoms',[]) for x in atom[3:]):
            raise RuntimeError('Coordinate integrity failed')
        if not all(report['validation_leaflets'].get('checks',{}).values()) or report['validation_leaflets'].get('recognized_lipid_P_count') != 200:
            raise RuntimeError('Membrane geometry failed')
        if report['validation_contacts'].get('intermolecular_heavy_pairs_below_0_18nm',1):
            raise RuntimeError('Short intermolecular heavy atom contact after validation')
        report['validation_energy'] = finite_energy((work/'validation-energy.xvg').read_text())
        command(['check','-f','validation.xtc'],'validation-check')
        gpu_log = (work/'validation.log').read_text()
        if not (re.search(r'(nonbonded|PP tasks).*GPU|GPU.*nonbonded',gpu_log,re.I) and re.search(r'PME.*GPU|GPU.*PME',gpu_log,re.I)):
            raise RuntimeError('GPU assignment missing from validation log')
        report['gpu_assignment_excerpt'] = [line for line in gpu_log.splitlines() if re.search('GPU|PME tasks|nonbonded',line,re.I)][:35]
        report['performance_lines'] = re.findall(r'Performance:.*',gpu_log)
        report['status'] = 'short_gpu_validation_completed'; persist(); snapshot('validated', full=True)
        if args.validate_only:
            return 0
        # Extend the SAME TPR and resume the SAME checkpoint/output set. This
        # preserves velocities, thermostat/barostat state and simulation time.
        origin_ps = final_time((work/'validation.log').read_text())
        total_ps = 0
        while total_ps < args.target_ns*1000 and time.monotonic() < deadline-180:
            stage = 'equil-'+str(len(report['segments'])+1).zfill(3)
            endpoint_ps = origin_ps + min(total_ps+1000, args.target_ns*1000)
            command(['convert-tpr','-s','validation.tpr','-until',str(endpoint_ps),'-o','extended.tpr'],stage+'-extend')
            interrupted = command(['mdrun','-s','extended.tpr','-deffnm','validation','-cpi','validation.cpt','-append']+mdargs,stage,md=True,md_log='validation')
            log = (work/'validation.log').read_text(errors='replace')
            observed = final_time(log) or origin_ps
            command(['energy','-f','validation.edr','-o',stage+'-energy.xvg','-b',str(origin_ps+total_ps)],stage+'-energy','Potential\nTemperature\nPressure\nVolume\n0\n',analysis=True)
            energy = finite_energy((work/(stage+'-energy.xvg')).read_text())
            leaflets = leaflet_analysis(parse_gro(work/'validation.gro'))
            contacts = contact_audit(work/'validation.gro')
            if leaflets.get('status') != 'checked' or not all(leaflets.get('checks',{}).values()) or leaflets.get('recognized_lipid_P_count') != 200:
                raise RuntimeError('Membrane integrity failed during '+stage)
            if contacts.get('intermolecular_heavy_pairs_below_0_18nm',1):
                raise RuntimeError('Severe heavy-atom contact during '+stage)
            elapsed_ps = max(0, observed-origin_ps-total_ps)
            total_ps = max(0, observed-origin_ps)
            report['segments'].append({'stage':stage,'observed_ps':elapsed_ps,'absolute_end_ps':observed,'energy':energy,'leaflets':leaflets,'contacts':contacts,'performance':re.findall(r'Performance:.*',log)[-1:],'interrupted':interrupted})
            report['additional_equilibration_ns'] = total_ps/1000
            persist(); snapshot(stage)
            if interrupted or observed < endpoint_ps-0.001:
                break
        command(['check','-f','validation.xtc'],'final-trajectory-check',analysis=True)
        report['status'] = 'equilibration_target_completed' if total_ps >= args.target_ns*1000 else 'session_budget_completed_partial_equilibration'
        persist(); snapshot('session-final', full=True)
    except Exception as exc:
        report['status'] = 'stopped'; report['error'] = type(exc).__name__+': '+str(exc)
        persist()
        snapshot('stopped-'+datetime.now(timezone.utc).strftime('%H%M%S'))
        print(report['error'],flush=True)
        return 1
    finally:
        persist()
    print(json.dumps(report,indent=2),flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
