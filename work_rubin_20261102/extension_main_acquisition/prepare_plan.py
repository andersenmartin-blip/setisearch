#!/usr/bin/env python3
"""Freeze exact Gaia-selected metadata identities; no photometry or network."""
import csv
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = Path(sys.argv[1]).resolve()
    with source.open() as f:
        rows = list(csv.DictReader(f))
    ids = [r['diaObjectId'] for r in rows]
    assert 0 < len(ids) <= 104 and len(ids) + 188 <= 500
    assert len(set(ids)) == len(ids)
    assert all(isinstance(i,str) and i.isdigit() and 0 < int(i) < 2**63 for i in ids)
    assert [int(r['selection_index']) for r in rows] == list(range(1,len(ids)+1))
    with (ROOT/'extension_feasibility/OBJECT_FEASIBILITY.csv').open() as f:
        eligible = {r['object_id'] for r in csv.DictReader(f) if r['status'] == 'MEETS_TEMPORAL_QUALITY_NECESSARY_CONDITION'}
    assert set(ids) <= eligible
    assert not (P/'PLAN.json').exists() and not (P/'MAIN_SELECTION_FROZEN.csv').exists()
    original = json.loads((ROOT/'main_acquisition/PLAN.json').read_text())
    assert not set(ids).intersection(original['selected_ids'])
    jobs = []
    for batch in range(0,len(ids),50):
        subset = ids[batch:batch+50]
        for stream in ('sources','fp'):
            template = next(j for j in original['jobs'] if j['job_id'].startswith(stream+'_'))
            job_id = f'{stream}_{batch//50+1:02}'
            jobs.append({'job_id':job_id,'endpoint':template['endpoint'],'object_ids':subset,
                         'payload':{**template['payload'],'diaObjectId':','.join(subset)},
                         'canonical_path':f'raw/{job_id}.json'})
    plan = {k:v for k,v in original.items() if k not in ('jobs','selected_ids')}
    plan.update(schema='RUBIN_EXTENSION_MAIN_ACQUISITION_V1',
                created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                status='FROZEN_BEFORE_EXTENSION_FLUX',objects=len(ids),selected_ids=ids,jobs=jobs,
                selection_sha256=sha(source),selection_source=os.path.relpath(source,P),
                selection_order='Frozen Gaia metadata rule and selection_index; all prior 433 identity/position/Gaia counterpart exclusions applied upstream; no flux-dependent replacement.',
                data_integrity=[s.replace('all188','all selected') for s in original['data_integrity']],
                extension_scope={'prior_selected_objects':188,'extension_selected_objects':len(ids),
                                 'combined_selected_objects':188+len(ids),'combined_selection_cap':500,
                                 'metadata_prerequisite_pool':104,'one_degree_field_extension_count':1,
                                 'further_field_expansion':False,'original188_unchanged':True,
                                 'selection_conditioned_on_metadata_cadence_and_quality':True,
                                 'metadata_prerequisite_does_not_establish_numeric_evaluability':True},
                scientific_method={'path':'../method_review/METHOD_FREEZE.json',
                                   'sha256':sha(ROOT/'method_review/METHOD_FREEZE.json'),
                                   'config_sha256':sha(ROOT/'method_review/CONFIG.json'),
                                   'detector_sha256':sha(ROOT/'method_review/detector.py'),
                                   'changed_for_extension':False},
                output_directories={'photometry':'extension_main_acquisition/raw','analysis':'extension_main_analysis',
                                    'cutouts':'extension_main_cutout_review'},
                prerequisite_hashes={str(p.relative_to(ROOT)):sha(p) for p in [
                    ROOT/'extension_feasibility/PLAN.json',ROOT/'extension_feasibility/SUMMARY.json',
                    ROOT/'extension_feasibility/OBJECT_FEASIBILITY.csv',ROOT/'extension_feasibility/independent_review/RESULTS_AUDIT.json',
                    source,ROOT/'main_acquisition/MAIN_SELECTION_FROZEN.csv',ROOT/'main_analysis/OUTPUT_HASHES.json']},
                code_hashes={name:sha(P/name) for name in ['acquire_main.py','run_main.py','acquire_trigger_cutouts.py','check_offline_guards.py','prepare_plan.py','CODE_ADAPTATIONS.json']})
    with (P/'MAIN_SELECTION_FROZEN.csv').open('xb') as f:
        f.write(source.read_bytes())
    with (P/'PLAN.json').open('x') as f:
        f.write(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({'objects':len(ids),'jobs':len(jobs),'selection_sha256':plan['selection_sha256'],
                      'plan_sha256':sha(P/'PLAN.json'),'extension_flux_read':False},indent=2))


if __name__ == '__main__':
    main()
