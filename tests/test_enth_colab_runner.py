"""Exercise orchestration failure boundaries without running GROMACS or MD.

The small fake engine supplies deterministic files and rejects incompatible
offload flags. Actual engine/physics compatibility still requires Colab logs.
"""
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS=Path(__file__).parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('colab_runner',SCRIPTS/'run-enth-colab.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


class FakeEngine:
    def __init__(self, early_stage=None, warning_stage=None):
        self.calls=[];self.restart_states=[]
        self.early_stage=early_stage;self.warning_stage=warning_stage

    def popen(self, argv, cwd, **kwargs):
        args=argv[1:];root=Path(cwd);self.calls.append(args)
        value=lambda flag:args[args.index(flag)+1]
        if args[0]=='grompp':
            text=(root/value('-f')).read_text()
            steps=int(re.search(r'(?m)^nsteps\s*=\s*(\d+)',text).group(1))
            (root/value('-o')).write_text(json.dumps({'end_ps':steps*.002}))
        elif args[0]=='convert-tpr':
            (root/value('-o')).write_text(json.dumps({'end_ps':float(value('-until'))}))
        elif args[0]=='mdrun':
            stage=value('-deffnm')
            if stage.startswith('em'):
                if value('-pme')!='cpu' or value('-update')!='cpu':
                    raise RuntimeError('Steepest descent requested unsupported GPU PME/update')
                log='Steepest Descents converged to Fmax < 1000 in 20 steps\n'
            else:
                endpoint=json.loads((root/value('-s')).read_text())['end_ps']
                if stage==self.early_stage:endpoint-=2
                log=f'           Step           Time\n          {int(endpoint/.002)}       {endpoint:.5f}\n'
                log+='PP tasks will do short-ranged interactions on the GPU\nPME tasks will do all aspects on the GPU\n'
                if '-cpi' in args:
                    self.restart_states.append((root/value('-cpi')).read_bytes())
                    if '-append' not in args:raise RuntimeError('Expected compatible output append')
                (root/(stage+'.cpt')).write_text(json.dumps({'time_ps':endpoint,'velocities':'retained','barostat':'retained'}))
                for suffix in ['edr','xtc']:(root/(stage+'.'+suffix)).write_bytes(b'fake engine output')
            if stage==self.warning_stage:log+='LINCS WARNING: relative constraint deviation\n'
            path=root/(stage+'.log')
            previous=path.read_text() if '-append' in args and path.exists() else ''
            path.write_text(previous+log+'Finished mdrun\n')
            (root/(stage+'.gro')).write_text('Mock coordinates; geometry functions patched\n')
        elif args[0]=='energy':
            (root/value('-o')).write_text('@ title "Energy"\n0 -1000 303.0 1.0 750\n100 -1001 304.0 0.9 751\n')
        class Finished:
            returncode=0
            pid=123456
            stdin=io.BytesIO()
            def poll(self):return 0
            def wait(self,timeout=None):return 0
        return Finished()


class ColabRunnerTests(unittest.TestCase):
    def test_log_time_uses_last_explicit_step_not_finish_marker(self):
        log=' Step Time\n 0 0.000\n Step Time\n 49000 9.80000e+01\nReceived the TERM signal\nFinished mdrun\n'
        self.assertEqual(runner.final_time(log),98)
        self.assertIsNone(runner.final_time('Finished mdrun\n'))

    def test_native_gromacs_header_with_appended_runs(self):
        # Native aligned header, as emitted in the existing GROMACS run logs.
        log=('           Step           Time\r\n'
             '          50000      100.00000\r\n'
             'Finished mdrun\r\nRestarting from checkpoint, appending to previous log\r\n'
             '           Step           Time\r\n'
             '         550000     1100.00000\r\n')
        self.assertEqual(runner.final_time(log),1100)

    def test_nonfinite_energy_is_rejected(self):
        for bad in ['nan','inf','-inf']:
            with self.subTest(bad=bad),self.assertRaisesRegex(RuntimeError,'Nonfinite'):
                runner.finite_energy(f'0 -1000 303 1 750\n1 {bad} 303 1 750\n')

    def test_collapsing_or_expanding_box_is_rejected(self):
        for volume in [0,-1,950,500]:
            with self.subTest(volume=volume),self.assertRaises(RuntimeError):
                runner.finite_energy(f'0 -1000 303 1 750\n1 -1001 303 1 {volume}\n')

    def invoke(self, root, engine, continuation=False, validate_only=True):
        inputs=root/'inputs';inputs.mkdir();output=root/'output';durable=root/'durable';durable.mkdir()
        (inputs/'ions.gro').write_text('initial coordinates')
        for stage in ['em_relax','em','nvt','npt_restraint','npt_release']:
            (inputs/(stage+'.mdp')).write_text('nsteps = 5000\ndt = 0.002\nannealing-time = 0 10\nnstxout-compressed = 1000\n')
        seed=None
        if continuation:
            (inputs/'colab-run.json').write_text(json.dumps({'status':'short_gpu_validation_completed'}))
            (inputs/'validation.tpr').write_text(json.dumps({'end_ps':100}))
            (inputs/'validation.log').write_text(' Step Time\n 50000 100.0\nPP tasks will do short-ranged interactions on the GPU\nPME tasks will do all aspects on the GPU\n')
            seed=b'{"time_ps":100,"velocities":[1.2,3.4],"barostat":[5.6]}'
            (inputs/'validation.cpt').write_bytes(seed)
            for suffix in ['gro','edr','xtc']:(inputs/('validation.'+suffix)).write_text('validated output')
        args=['runner','--inputs',str(inputs),'--output',str(output),'--durable',str(durable),'--hours','1','--target-ns','0.001']
        if continuation:args+=['--continue-validated']
        if validate_only:args+=['--validate-only']
        geometry={'parsed_atom_count':2,'declared_atom_count':2,'atoms':[(1,'ALA','CA',1.,2.,3.)]}
        leaflets={'status':'checked','checks':{'both_leaflets_present':True,'exactly_one_pip2':True},'recognized_lipid_P_count':200}
        with patch.object(sys,'argv',args),patch.object(runner.subprocess,'Popen',side_effect=engine.popen),patch.object(runner,'parse_gro',return_value=geometry),patch.object(runner,'leaflet_analysis',return_value=leaflets),patch.object(runner,'contact_audit',return_value={'intermolecular_heavy_pairs_below_0_18nm':0}),patch('sys.stdout',new=io.StringIO()):
            result=runner.main()
        return result,output,durable,seed

    def test_clean_early_stop_cannot_start_next_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine=FakeEngine(early_stage='nvt')
            result,out,_,_=self.invoke(Path(tmp),engine)
            self.assertEqual(result,1)
            self.assertIn('stopped before requested duration',(out/'colab-run.json').read_text())
            self.assertFalse(any('npt_restraint.tpr' in call for call in engine.calls))

    def test_constraint_warning_blocks_dynamics_even_after_convergence(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine=FakeEngine(warning_stage='em')
            result,out,_,_=self.invoke(Path(tmp),engine)
            self.assertEqual(result,1)
            self.assertIn('Physical warning',(out/'colab-run.json').read_text())
            self.assertFalse(any('nvt.tpr' in call for call in engine.calls))

    def test_validation_uses_supported_minimization_and_full_temperature_ramp(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine=FakeEngine()
            result,out,_,_=self.invoke(Path(tmp),engine)
            self.assertEqual(result,0)
            self.assertIn('annealing-time = 0 100',(out/'nvt.mdp').read_text())
            self.assertEqual(json.loads((out/'colab-run.json').read_text())['status'],'short_gpu_validation_completed')

    def test_completed_warmup_has_its_own_restart_trio(self):
        with tempfile.TemporaryDirectory() as tmp:
            result,out,durable,_=self.invoke(Path(tmp),FakeEngine())
            self.assertEqual(result,0)
            for stage in ['nvt','npt_restraint']:
                for suffix in ['cpt','tpr','gro']:
                    with self.subTest(stage=stage,suffix=suffix):
                        saved=durable/(stage+'-complete')/(stage+'.'+suffix)
                        self.assertEqual(saved.read_bytes(),(out/(stage+'.'+suffix)).read_bytes())

    def test_validated_continuation_reuses_state_without_reheating(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine=FakeEngine()
            result,out,_,seed=self.invoke(Path(tmp),engine,continuation=True,validate_only=False)
            self.assertEqual(result,0,(out/'colab-run.json').read_text())
            self.assertEqual(engine.restart_states,[seed])
            self.assertFalse(any(call[0]=='grompp' for call in engine.calls))
            self.assertEqual(json.loads((out/'colab-run.json').read_text())['additional_equilibration_ns'],.001)


if __name__=='__main__':unittest.main()
