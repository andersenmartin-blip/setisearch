#!/usr/bin/env python3
"""Review extension adaptations and exact metadata selection, without network."""
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    return json.loads(p.read_bytes())


def main():
    original=ROOT/'main_acquisition'
    extension=ROOT/'extension_main_acquisition'
    checks=[]
    def check(label,condition):
        checks.append({'check':label,'passed':bool(condition)})
    allowed={
        'acquire_main.py':[],
        'run_main.py':[("OUT=ROOT/'main_analysis'","OUT=ROOT/'extension_main_analysis'"),
                       ("'all188_accounted_in_both_streams'","'all_selected_accounted_in_both_streams'")],
        'acquire_trigger_cutouts.py':[("ANALYSIS=ROOT/'main_analysis'","ANALYSIS=ROOT/'extension_main_analysis'"),
                                     ("OUT=ROOT/'main_cutout_review'","OUT=ROOT/'extension_main_cutout_review'")],
    }
    for name,replacements in allowed.items():
        expected=(original/name).read_bytes()
        for before,after in replacements:
            check(name+' exactly one '+before,expected.count(before.encode())==1)
            expected=expected.replace(before.encode(),after.encode())
        check(name+' exact bytes after only allowed substitutions',(extension/name).read_bytes()==expected)
    plan=load(extension/'PLAN.json')
    previous_plan=load(original/'PLAN.json')
    selection=list(csv.DictReader((extension/'MAIN_SELECTION_FROZEN.csv').open()))
    ids=[r['diaObjectId']for r in selection]
    old=list(csv.DictReader((original/'MAIN_SELECTION_FROZEN.csv').open()))
    old_ids={r['diaObjectId']for r in old}
    old_gaia={r['matched_gaia_source_id']for r in old}
    new_gaia={r['matched_gaia_source_id']for r in selection}
    check('exact ordered IDs equal acquisition plan',ids==plan['selected_ids'])
    check('selected count equals plan',len(ids)==plan['objects'])
    check('positive exact signed64bit identity strings',all(isinstance(i,str)and i.isdigit()and 0<int(i)<2**63 for i in ids))
    check('no duplicate selected object IDs',len(ids)==len(set(ids)))
    check('no duplicate selected Gaia IDs',len(ids)==len(new_gaia))
    check('no original main object selected again',not(set(ids)&old_ids))
    check('no original main Gaia counterpart selected again',not(new_gaia&old_gaia))
    previous_metadata=[]
    for filename in ('DEVELOPMENT_SELECTION.csv','MAIN_METADATA_CANDIDATES_UNMATCHED.csv'):
        previous_metadata.extend(csv.DictReader((ROOT/'access_pilot'/filename).open()))
    check('all433 earlier metadata identities remain excluded',not(set(ids)&{r['r:diaObjectId']for r in previous_metadata}))
    separations=[]
    for row in selection:
        ra,dec=math.radians(float(row['ra_deg'])),math.radians(float(row['dec_deg']))
        for old_row in previous_metadata:
            ora,odec=math.radians(float(old_row['r:ra'])),math.radians(float(old_row['r:dec']))
            h=math.sin((dec-odec)/2)**2+math.cos(dec)*math.cos(odec)*math.sin((ra-ora)/2)**2
            separations.append(2*math.asin(math.sqrt(max(0,min(1,h))))*180/math.pi*3600)
    check('all selected coordinates remain beyond2arcsec of initial433',not separations or min(separations)>2)
    check('original188 plus extension does not exceed500',len(old)+len(ids)<=500 and len(old)==188)
    check('selection bytes match frozen hash',sha(extension/'MAIN_SELECTION_FROZEN.csv')==plan['selection_sha256'])
    check('main acquisition response/retry/worker bounds unchanged',plan['limits']==previous_plan['limits'])
    feasibility=list(csv.DictReader((ROOT/'extension_feasibility/OBJECT_FEASIBILITY.csv').open()))
    qualifying={r['object_id']for r in feasibility if r['status']=='MEETS_TEMPORAL_QUALITY_NECESSARY_CONDITION'}
    check('all selected IDs meet prior metadata-only necessary condition',set(ids)<=qualifying)
    for stream in ('sources','fp'):
        jobs=[j for j in plan['jobs']if j['endpoint'].endswith('/'+stream)]
        check(stream+' exact once-only ordered job coverage',[i for j in jobs for i in j['object_ids']]==ids)
        baseline=next(j for j in previous_plan['jobs']if j['endpoint'].endswith('/'+stream))
        for job in jobs:
            check(job['job_id']+' unchanged endpoint',job['endpoint']==baseline['endpoint'])
            check(job['job_id']+' unchanged science/quality field set',job['payload']['columns']==baseline['payload']['columns'])
            check(job['job_id']+' exact request identity list',job['payload']['diaObjectId']==','.join(job['object_ids']))
    freeze=load(ROOT/'method_review/METHOD_FREEZE.json')
    for name,digest in freeze['source_hashes'].items():
        check('original frozen method unchanged '+name,sha(ROOT/'method_review'/name)==digest)
    for name,digest in load(ROOT/'main_analysis/OUTPUT_HASHES.json').items():
        check('original main result unchanged '+name,sha(ROOT/'main_analysis'/name)==digest)
    check('extension science acquisition has not begun',not(extension/'STARTED.json').exists())
    check('extension analysis has not begun',not(ROOT/'extension_main_analysis/STARTED.json').exists())
    output={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'PASS_INDEPENDENT_EXTENSION_PREFLIGHT'if all(c['passed']for c in checks)else'FAIL',
            'checks':checks,'count':len(checks),'extension_selected_objects':len(ids),
            'previous_main_objects':len(old),'cumulative_selected_objects':len(old)+len(ids),
            'minimum_separation_arcsec_to_initial433':min(separations)if separations else None,
            'original_method_and_science_outputs_unchanged':all(c['passed']for c in checks if c['check'].startswith('original ')),
            'plan_sha256':sha(extension/'PLAN.json'),'selection_sha256':sha(extension/'MAIN_SELECTION_FROZEN.csv'),
            'script_sha256':{name:sha(extension/name)for name in allowed},
            'independent_scalar_helper_sha256':sha(ROOT/'independent_main_audit/independent_science.py'),
            'audit_script_sha256':sha(Path(__file__)),
            'limits':['Metadata and Gaia qualification do not guarantee valid flux/errors or baseline precision.',
                      'The extension is a new separately selected cohort; the original188 were not replaced.',
                      'No photometric sensitivity or origin interpretation is established before main execution.']}
    (HERE/'PREFLIGHT.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items()if k!='checks'},indent=2))
    print('Failed checks:',[c['check']for c in checks if not c['passed']])
    if not all(c['passed']for c in checks):
        raise SystemExit(1)


if __name__=='__main__':
    main()
