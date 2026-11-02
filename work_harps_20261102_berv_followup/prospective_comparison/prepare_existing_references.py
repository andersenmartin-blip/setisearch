#!/usr/bin/env python3
"""Identify and restore only20 existing discovery profiles; no new science/network."""
from pathlib import Path
import csv
import datetime
import hashlib
import io
import json
import zipfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
EXT=REPO/'work_harps_20261101/v2/extension02'
EPOCH=EXT/'epoch_followup'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def main():
    if (HERE/'EXISTING_REFERENCE_RECEIPT.json').exists():
        raise RuntimeError('Preserve existing reference preparation; verify or reproduce in a separate copy.')
    queue_path=EXT/'next_followup_20261102/FRAME_BASELINE_QUEUE.csv'
    queue=list(csv.DictReader(queue_path.open()))
    ids=[r['candidate_id']for r in queue]
    assert len(ids)==10 and len(set(ids))==10
    assert all(r['current_code_unchanged']=='U'for r in queue)
    assert {r['target']for r in queue}=={'HD122640','HD135204'}
    catalog={r['candidate_id']:r for r in csv.DictReader((EXT/'production/V2_HITS.csv').open())}
    plan=load(EPOCH/'PLAN.json')
    inputs={r['dp_id']:r for r in plan['inputs']}
    all_rows=list(csv.DictReader((EPOCH/'ALL_EPOCH_MEASUREMENTS.csv').open()))
    rows=[]
    events=[]
    saved_header_sources=[]
    columns=['candidate_id','target','source_dp_id','dp_id','is_discovery_exposure','date_obs',
             'mjd_obs','berv_km_s','source_berv_km_s','frame','profile_path','profile_sha256',
             'center_in_frame_air_angstrom','center_sampled_bary_air_angstrom']
    for order,item in enumerate(queue,1):
        hit=catalog[item['candidate_id']]
        assert hit['dp_id']==item['dp_id'] and hit['canonical_target']==item['target']
        assert float(hit['fitted_center_angstrom'])==float(item['center_bary_air_angstrom'])
        assert hit['input_sha256']==item['source_input_sha256']
        discovery=inputs[item['dp_id']]
        assert discovery['sha256']==item['source_input_sha256']
        found=[r for r in all_rows if r['candidate_id']==item['candidate_id'] and r['is_discovery_exposure']=='True']
        assert len(found)==2 and {r['frame']for r in found}=={'barycentric','topocentric'}
        header_path=EXT/'production/spectra'/(item['dp_id'].replace(':','_')+'_v2.json')
        header=load(header_path)['input']
        assert header['sha256']==discovery['sha256']
        assert header['SPECSYS']=='BARYCENT' and header['wavelength_unit']=='angstrom' and 'obs.atmos'in header['wavelength_ucd']
        assert header['flux_unit']=='adu'
        saved_header_sources.append(header_path)
        event={'comparison_order':order,'candidate_id':item['candidate_id'],'target':item['target'],
               'discovery_dp_id':item['dp_id'],'discovery_input_sha256':discovery['sha256'],
               'discovery_date_obs':discovery['date_obs'],'discovery_mjd_obs':discovery['mjd_obs'],
               'discovery_exptime_seconds':discovery['exptime'],'discovery_berv_km_s':discovery['berv_km_s'],
               'fitted_center_bary_air_angstrom':float(hit['fitted_center_angstrom']),
               'existing_header_metadata':header,'discovery_profiles':{}}
        for frame in ['barycentric','topocentric']:
            r=next(r for r in found if r['frame']==frame)
            assert r['dp_id']==item['dp_id'] and r['source_dp_id']==item['dp_id']
            assert float(r['berv_km_s'])==discovery['berv_km_s']
            rows.append({key:r[key]for key in columns})
            event['discovery_profiles'][frame]={key:r[key]for key in ['profile_path','profile_sha256','center_in_frame_air_angstrom']}
        events.append(event)
    with (HERE/'DISCOVERY_PROFILES.csv').open('w',newline='')as stream:
        writer=csv.DictWriter(stream,columns);writer.writeheader();writer.writerows(rows)
    write_json(HERE/'EVENTS.json',events)
    parts=load(EPOCH/'PROFILE_ARRAYS_PARTS.json')
    archive_bytes=bytearray()
    verified_parts=[]
    for part in parts['parts']:
        path=EPOCH/part['path']
        assert path.stat().st_size==part['bytes'] and sha(path)==part['sha256'],path
        archive_bytes.extend(path.read_bytes())
        verified_parts.append(part)
    assert len(archive_bytes)==parts['bytes'] and hashlib.sha256(archive_bytes).hexdigest()==parts['sha256']
    restored=[]
    with zipfile.ZipFile(io.BytesIO(archive_bytes))as archive:
        assert len(archive.namelist())==4370
        for r in rows:
            payload=archive.read(r['profile_path'])
            assert hashlib.sha256(payload).hexdigest()==r['profile_sha256']
            dest=HERE/'inputs'/r['profile_path']
            dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists():
                assert dest.read_bytes()==payload
            else:
                with dest.open('xb')as stream:stream.write(payload)
            restored.append({'path':str(dest.relative_to(HERE)),'archive_member':r['profile_path'],
                             'bytes':len(payload),'sha256':r['profile_sha256']})
    sources=[queue_path,EXT/'production/V2_HITS.csv',EPOCH/'PLAN.json',EPOCH/'measure_epochs.py',
             EPOCH/'ALL_EPOCH_MEASUREMENTS.csv',EPOCH/'PROFILE_ARCHIVE.json',EPOCH/'PROFILE_ARRAYS_PARTS.json',
             *dict.fromkeys(saved_header_sources)]
    receipt={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'status':'PASS_EXISTING_20_REFERENCE_PROFILES_RESTORED_WITHOUT_ARRAY_INTERPRETATION',
             'events':len(events),'discovery_exposures':len({r['discovery_dp_id']for r in events}),
             'profiles':len(rows),'restored_bytes':sum(r['bytes']for r in restored),
             'archive_bytes':parts['bytes'],'archive_sha256':parts['sha256'],'parts_verified':verified_parts,
             'restored':restored,'source_hashes':{str(p.relative_to(REPO)):sha(p)for p in sources},
             'output_hashes':{name:sha(HERE/name)for name in ['EVENTS.json','DISCOVERY_PROFILES.csv']},
             'script_sha256':sha(Path(__file__)),
             'network_calls':0,'new_science_inputs':0,'new_array_values_read':False,
             'original_science_rerun':False,'origin_assignments':0,'classifications_changed':0}
    write_json(HERE/'EXISTING_REFERENCE_RECEIPT.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items()if k not in ['restored','parts_verified','source_hashes']},indent=2))


if __name__=='__main__':
    main()
