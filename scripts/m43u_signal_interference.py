"""Prospectively frozen, restartable native signal/interference challenge."""
import argparse
import gzip
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import time
import numpy as np
from m43e_economical_bank import read_sealed, write_sealed
from m43f_source_cache_preflight import build_context
from m43q_integrated_detector import AnchorStore, NativeReceiver
from m43r_joint_calibration import grid_context, compact
from m43s_profile_sensitivity import endpoint, geometry_summary
from seti_repeater import search_v0p6 as core
from seti_repeater import detector_m43u as detector
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43u import JointOverlay
from seti_repeater.mask_m43u import POLICIES, bind_calibration

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_m43u_signal_interference'
CONFIG = ROOT/'config/m43u_signal_interference.json'
WINDOW = 'm43u-central-signal-interference'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frozen(commit):
    cfg = json.loads(CONFIG.read_text())
    if subprocess.check_output(['git','show',commit+':config/m43u_signal_interference.json'],cwd=ROOT) != CONFIG.read_bytes():
        raise ValueError('config differs from public freeze')
    for p, expected in cfg['pinned_sha256'].items():
        if sha(ROOT/p) != expected:
            raise ValueError('changed frozen dependency: '+p)
    if platform.python_version()!=cfg['python_version'] or np.__version__!=cfg['numpy_version']:
        raise ValueError('changed numerical runtime')
    return cfg


def run(work, source_root, checkpoints, freeze):
    cfg = frozen(freeze); started = time.monotonic()
    OUT.mkdir(exist_ok=True); checkpoints.mkdir(parents=True, exist_ok=True)
    if (OUT/'result.json').exists():
        raise ValueError('completed result exists; preserve it')
    try:
        _, _, _, metadata, basis, parent, parent_table, _ = build_context()
        bank, table, bridge = detector.catalogue_bridge(parent,cfg['parent_template_indices'],basis)
        if bridge != cfg['bridge']:
            raise ValueError('bridge changed')
        original, grid, start = grid_context()
        if core.proxy_carrier_grid_sha256(grid) != cfg['grid_sha256']:
            raise ValueError('grid changed')
        old = AnchorStore(work, {'parent_template_indices':cfg['parent_template_indices'], 'support_carriers':original.support_bin_count})
        arrays = {k: old.get(*k)[0][:,start:start+grid.support_bin_count] for k in old.expected_ids}
        provenance = {'family':'M43P-exact-central-slice', 'parent_inventory_sha256':detector.digest(old.inventory),
            'parent_score_ids_sha256':detector.digest([[*k,v] for k,v in sorted(old.expected_ids.items())]),
            'support_start':start,'support_count':grid.support_bin_count,'grid_sha256':cfg['grid_sha256']}
        if provenance != read_sealed(ROOT/'results_m43r_joint_calibration/calibration.json')['baseline_provenance']:
            raise ValueError('original baseline identity differs')
        baseline = ScoreStore(arrays,provenance)
        print('All 96 original arrays and baseline identity exact',flush=True)
        common = dict(window=WINDOW,grid=grid,bank=bank,table=table,basis=basis,scans=metadata['scans'])
        calibrations={}; thresholds={}; bindings={}; nulls={}
        for policy in POLICIES:
            cal, summary = detector.calibrate(**common,store=baseline,mask_policy=policy,
                shifts=np.asarray(cfg['calibration_shifts'],dtype=np.int64),minimum_shift_bins=128)
            threshold = core.calibrated_threshold((cal,),expected_window_ids=(WINDOW,),reference_floor=10.,quantile=1.,scientific_p_ceiling=.01)
            binding=bind_calibration(cal,threshold,policy)
            calibrations[policy]=cal;thresholds[policy]=threshold;bindings[policy]=binding
            write_sealed(OUT/f'{policy}.calibration.json',{'freeze_commit':freeze,'config_sha256':sha(CONFIG),
                'summary':summary,'null_maxima':cal.null_maxima.tolist(),'threshold':threshold.as_record(),'binding':binding})
            print(policy+' sealed threshold '+str(threshold.operational_threshold_snr),flush=True)
        for policy in POLICIES:
            cal, summary = detector.calibrate(**common,store=baseline,mask_policy=policy,
                shifts=np.asarray(cfg['heldout_shifts'],dtype=np.int64),minimum_shift_bins=128)
            cut=thresholds[policy].operational_threshold_snr
            nulls[policy]={'count':128,'maximum':float(max(cal.null_maxima)), 'threshold':cut,
                'at_or_above_threshold':int(np.count_nonzero(cal.null_maxima>=cut))}
            write_sealed(OUT/f'{policy}.heldout.json',{'freeze_commit':freeze,'summary':summary,
                'null_maxima':cal.null_maxima.tolist(),'diagnostic':nulls[policy],'binding':bindings[policy]})
            print(policy+' heldout '+json.dumps(nulls[policy]),flush=True)
        receiver=NativeReceiver(source_root,metadata,basis,parent,parent_table,original)
        overlay=JointOverlay(baseline,receiver,bank,table,basis,grid,progress=lambda m:print(m,flush=True))
        if len(overlay.cache_inventory)!=48 or not all(x['anchor_exact'] for x in overlay.cache_inventory):
            raise ValueError('incomplete 48-anchor ON/OFF validation')
        write_sealed(OUT/'input_anchors.json',{'freeze_commit':freeze,'baseline_provenance':provenance,
            'cache_inventory':overlay.cache_inventory,'all_96_original_arrays_exact':True,'telescope_requests':0})
        print('All 48 ON/OFF native cache/gathers exact',flush=True)
        factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
        def execute(policy, store):
            result=detector.execute(**common,store=store,mask_policy=policy,calibration=calibrations[policy],
                threshold=thresholds[policy],calibration_binding=bindings[policy],receiver_factory=overlay,maximum_records=cfg['maximum_records'])
            audit=compact(result,overlay.overlay_receipt)
            audit.update(mask_policy=policy,calibration_binding=bindings[policy],masked_cell_counts=result['masked_cell_counts'],
                final_diagnostic_survivors=sum(x['passes_evaluated_physical_vetoes'] and x['meets_diagnostic_rank_cut'] for x in result['decisions']))
            return audit
        overlay.trial([])
        for policy in POLICIES:
            write_sealed(OUT/f'{policy}.baseline.json',{'freeze_commit':freeze,'audit':execute(policy,baseline)})
        paths=[]; endpoints=[]
        for case in cfg['cases']:
            truth=case['signal_truth']; path=checkpoints/f'case{case["case_index"]:03d}.json'; t0=time.monotonic()
            if truth is not None:
                if geometry_summary(truth,grid,factors,basis)!=cfg['geometry'][f'{case["stratum"]}:{truth["profile"]}']:
                    raise ValueError('frozen geometry changed')
            if path.exists():
                rec=read_sealed(path)
                if rec['freeze_commit']!=freeze or rec['config_sha256']!=sha(CONFIG) or rec['case']!=case or rec['bindings']!=bindings:
                    raise ValueError('checkpoint scope changed')
            else:
                store=overlay.trial(case['components']); audits={}; outcomes=[]
                for policy in POLICIES:
                    audit=execute(policy,store);audits[policy]=audit
                    e={'case_index':case['case_index'],'stratum':case['stratum'],'case_type':case['case_type'],
                        'mask_policy':policy,'signal_present':truth is not None,'final_diagnostic_survivors':audit['final_diagnostic_survivors'],
                        'control_leakage':truth is None and audit['final_diagnostic_survivors']>0,
                        'on_retained':audit['on_retained'],'off_retained':audit['off_retained'],
                        'physical_survivors':audit['all_member_physical_survivors'],
                        'masked_on_cells':sum(n for k,n in audit['masked_cell_counts'].items() if k.startswith('on:')),
                        'masked_off_cells':sum(n for k,n in audit['masked_cell_counts'].items() if k.startswith('off:'))}
                    if truth is not None:
                        associated=endpoint(audit,truth,grid,factors,basis,32,path.name)
                        associated.pop('zero_level_reuses_m43r_baseline'); e['association']=associated
                    outcomes.append(e)
                if len({a['input_inventory_sha256'] for a in audits.values()})!=1 or any(a['overlay']!=audits['legacy']['overlay'] for a in audits.values()):
                    raise ValueError('three-policy inputs differ')
                rec=write_sealed(path,{'freeze_commit':freeze,'config_sha256':sha(CONFIG),'case':case,
                    'bindings':bindings,'audits':audits,'endpoints':outcomes,'wall_seconds':round(time.monotonic()-t0,3)})
            paths.append(path);endpoints.extend(rec['endpoints'])
            print(f'Case {case["case_index"]} {case["case_type"]}: '+str({e['mask_policy']:(e.get('association',{}).get('recovered'),e['final_diagnostic_survivors']) for e in rec['endpoints']}),flush=True)
            write_sealed(OUT/'progress.json',{'complete':False,'completed_cases':len(paths),'planned_cases':72,'completed_endpoints':len(endpoints)})
        if len(paths)!=72 or len(endpoints)!=216:
            raise ValueError('incomplete denominator')
        lookup={(e['case_index'],e['mask_policy']):e for e in endpoints}; comparisons={}
        for policy in POLICIES[1:]:
            gains=[];losses=[];leak_gains=[];leak_losses=[]
            for case in cfg['cases']:
                a,b=(lookup[case['case_index'],p] for p in ('legacy',policy))
                if case['signal_truth'] is not None:
                    if b['association']['recovered'] and not a['association']['recovered']:gains.append(case['case_index'])
                    if a['association']['recovered'] and not b['association']['recovered']:losses.append(case['case_index'])
                else:
                    if b['control_leakage'] and not a['control_leakage']:leak_gains.append(case['case_index'])
                    if a['control_leakage'] and not b['control_leakage']:leak_losses.append(case['case_index'])
            conditions={'no_signal_recovery_loss':not losses,'no_increase_in_control_leakage_cases':len(leak_gains)<=len(leak_losses),
                'no_ON_OFF_survivors':not any(e['final_diagnostic_survivors'] for e in endpoints if e['mask_policy']==policy and e['case_type']=='ON-OFF'),
                'no_additional_heldout_exceedances':nulls[policy]['at_or_above_threshold']<=nulls['legacy']['at_or_above_threshold']}
            comparisons[policy]={'signal_gain_cases':gains,'signal_loss_cases':losses,'additional_control_leakage_cases':leak_gains,
                'removed_control_leakage_cases':leak_losses,'development_conditions':conditions,'development_gate_passed':all(conditions.values())}
        summary=[]
        for policy in POLICIES:
            for kind in dict.fromkeys(c['case_type'] for c in cfg['cases']):
                rows=[e for e in endpoints if e['mask_policy']==policy and e['case_type']==kind]
                summary.append({'policy':policy,'case_type':kind,'denominator':len(rows),'signal_present':rows[0]['signal_present'],
                    'recovered':sum(e.get('association',{}).get('recovered',False) for e in rows),
                    'control_leakage_cases':sum(e['control_leakage'] for e in rows),
                    'final_diagnostic_survivors':sum(e['final_diagnostic_survivors'] for e in rows),
                    'retained_truths':sum(e.get('association',{}).get('retained',False) for e in rows),
                    'physical_truths':sum(e.get('association',{}).get('passes_physical_vetoes',False) for e in rows)})
        raw=b''.join(p.read_bytes()+b'\n' for p in paths); compressed=gzip.compress(raw,compresslevel=9,mtime=0)
        if gzip.decompress(compressed)!=raw:raise ValueError('lossless ledger failure')
        (OUT/'case_audits.jsonl.gz').write_bytes(compressed)
        write_sealed(OUT/'result.json',{'milestone':'M43U','complete':True,'freeze_commit':freeze,'config_sha256':sha(CONFIG),
            'cases':72,'new_injected_executions':216,'new_baseline_executions':3,'endpoints':endpoints,'summary':summary,
            'comparisons':comparisons,'heldout':nulls,'bindings':bindings,'unique_new_shift_rows':256,'arm_specific_maxima':768,
            'ledger_sha256':hashlib.sha256(compressed).hexdigest(),'ledger_uncompressed_sha256':hashlib.sha256(raw).hexdigest(),
            'wall_seconds':round(time.monotonic()-started,3),'telescope_requests':0,'new_observing_coverage':False,
            'physical_false_alarm_probability_measured':False,'scientific_candidate_selection_authorized':False})
        write_sealed(OUT/'progress.json',{'complete':True,'completed_cases':72,'completed_endpoints':216})
        print(json.dumps({'summary':summary,'comparisons':comparisons},indent=2),flush=True)
    except BaseException as error:
        write_sealed(OUT/'failure.json',{'freeze_commit':freeze,'complete':False,'error':repr(error)})
        raise


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze-commit',required=True)
    p.add_argument('--anchor-root',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--checkpoint-root',type=Path,required=True);a=p.parse_args()
    run(a.anchor_root,a.source_root,a.checkpoint_root,a.freeze_commit)
