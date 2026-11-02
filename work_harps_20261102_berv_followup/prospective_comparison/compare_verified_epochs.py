#!/usr/bin/env python3
"""Conditional10-event comparison, reusing frozen original arithmetic unchanged.

No acquisition. Requires a hash-bound root release, the prospective selection,
recorded header verification and exact acquired bytes before interpreting arrays.
"""
import argparse
import csv
import datetime
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
import numpy as np
from astropy.io import fits

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
EXT=REPO/'work_harps_20261101/v2/extension02'
EPOCH=EXT/'epoch_followup'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def dump(path,value):
    with path.open('x')as stream:stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def path_in_repo(relative):
    path=REPO/relative
    if path.is_symlink():raise ValueError('Symlink input refused: '+str(path))
    resolved=path.resolve()
    if not resolved.is_relative_to(REPO.resolve()):raise ValueError('Path outside repository')
    return resolved


def normalize_name(value):
    return re.sub('[^A-Z0-9]','',str(value).upper())


def verified_original_module():
    protocol=read(HERE/'PLAN.json')
    for relative,digest in protocol['source_hashes'].items():
        if sha(path_in_repo(relative))!=digest:raise ValueError('Prospective source changed: '+relative)
    reference=read(HERE/'EXISTING_REFERENCE_RECEIPT.json')
    for relative,digest in reference['source_hashes'].items():
        if sha(path_in_repo(relative))!=digest:raise ValueError('Original source changed: '+relative)
    for relative,digest in reference['output_hashes'].items():
        if sha(HERE/relative)!=digest:raise ValueError('Prepared identity source changed: '+relative)
    spec=importlib.util.spec_from_file_location('frozen_harps_epoch_metrics',EPOCH/'measure_epochs.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # Original main() is guarded and is never called.
    return module,reference


def validate_release(path):
    release=read(path)
    if release.get('schema')!='HARPS_BERV_COMPARISON_RELEASE_V1':raise ValueError('Unknown release schema')
    if release.get('publication_readback_verified')is not True:raise ValueError('Public freeze readback required')
    if not re.fullmatch('[0-9a-f]{40}',release.get('publication_commit','')):raise ValueError('Publication commit required')
    if release.get('comparison_script_sha256')!=sha(Path(__file__)):raise ValueError('Comparison code changed')
    if release.get('prospective_plan_sha256')!=sha(HERE/'PLAN.json'):raise ValueError('Prospective method changed')
    linked={}
    for key in ['selection','header_results','acquisition_manifest']:
        p=path_in_repo(release[key+'_path'])
        if sha(p)!=release[key+'_sha256']:raise ValueError('Release mismatch: '+key)
        linked[key]=(p,read(p))
    selection=linked['selection'][1]
    selected=selection['selected']
    if not 1<=len(selected)<=4:raise ValueError('Require one to four fixed inputs')
    keys=[(r['target'],r['dp_id'])for r in selected]
    if len(set(keys))!=len(keys):raise ValueError('Duplicate selected identities')
    if any(t not in ['HD122640','HD135204']for t,_ in keys):raise ValueError('Unexpected target')
    if any(sum(r['target']==t for r in selected)>2 for t in ['HD122640','HD135204']):raise ValueError('More than two epochs for a target')
    inputs=[dict(row)for row in release['inputs']]
    if [(r['target'],r['dp_id'])for r in inputs]!=keys:raise ValueError('Acquired slots differ from prospective selection')
    if inputs!=linked['acquisition_manifest'][1]['inputs']:raise ValueError('Release inputs differ from canonical acquisition manifest')
    old=list(csv.DictReader((EXT/'next_followup_20261102/EXISTING_TARGET_EXPOSURES.csv').open()))
    if set(r['dp_id']for r in selected)&set(r['dp_id']for r in old):raise ValueError('Old exposure selected as new')
    results=linked['header_results'][1]['results']
    headers={r['dp_id']:r for r in results}
    if len(headers)!=len(results):raise ValueError('Duplicate header result identity')
    if selection['header_results_sha256']!=release['header_results_sha256']:raise ValueError('Selection linked to different header results')
    expected_extremes=[]
    for target in ['HD122640','HD135204']:
        eligible=[r for r in results if r['target']==target and r.get('inspection',{}).get('status')=='PASS_RECORDED_BERV']
        if not eligible:continue
        low=min(eligible,key=lambda r:(r['inspection']['berv_km_s'],r['dp_id']))
        high=min(eligible,key=lambda r:(-r['inspection']['berv_km_s'],r['dp_id']))
        expected_extremes.append((target,low['dp_id']))
        if high['dp_id']!=low['dp_id']:expected_extremes.append((target,high['dp_id']))
    if keys!=expected_extremes:raise ValueError('Selection differs from frozen min/max BERV rule')
    oldraw={r['raw_progenitor_id'].removesuffix('.fits')for r in old}
    newraw=[]
    for item,entry in zip(selected,inputs):
        h=headers[item['dp_id']]
        if h['target']!=item['target'] or h['inspection']['status']!='PASS_RECORDED_BERV':raise ValueError('No passing recorded header')
        if int(item['header_result_job_index'])!=int(h['job_index']):raise ValueError('Header selection link changed')
        if float(item['berv_km_s'])!=float(h['inspection']['berv_km_s']):raise ValueError('Selection BERV changed')
        for name in ['body','receipt']:
            p=linked['header_results'][0].parent/h[name+'_path']
            if sha(p)!=h[name+'_sha256']:raise ValueError('Recorded header evidence changed')
        raw=h['inspection']['raw_progenitor_ids']
        if len(raw)!=1:raise ValueError('New product is not one raw exposure')
        raw_id=raw[0].removesuffix('.fits')
        if raw_id in oldraw or raw_id in newraw:raise ValueError('Repeated raw exposure')
        newraw.append(raw_id)
        entry['_recorded_header']=h
        if entry['status']=='COMPLETE':
            p=path_in_repo(entry['local_path'])
            if p.stat().st_size!=entry['bytes']or sha(p)!=entry['sha256']:raise ValueError('Acquired payload differs')
            receipt=path_in_repo(entry['acquisition_receipt_path'])
            if sha(receipt)!=entry['acquisition_receipt_sha256']:raise ValueError('Acquisition receipt changed')
    return release,inputs,linked


def inspect_payload_headers(item):
    """Headers only: no HDU.data access until every product has passed this phase."""
    if item['status']!='COMPLETE':
        return {'status':'ACQUISITION_'+item['status'],'failures':[item.get('reason','No complete acquired product')], 'pipeline_difference':None}
    record=item['_recorded_header']['inspection']
    recorded=record['primary_header']
    failures=[]
    checks={}
    with fits.open(path_in_repo(item['local_path']),memmap=True,lazy_load_hdus=False)as hd:
        primary=hd[0].header
        extension=hd[1].header if len(hd)>1 else fits.Header()
        for key,value in recorded.items():
            key=key.removeprefix('HIERARCH ')
            actual=primary.get(key)
            checks['recorded_'+key]=(abs(float(actual)-float(value))<=1e-8 if isinstance(value,(int,float))and not isinstance(value,bool)and isinstance(actual,(int,float))else actual==value)
        checks['instrument_harps']=primary.get('INSTRUME')=='HARPS'
        checks['target_identity']=normalize_name(primary.get('OBJECT'))==normalize_name(item['target'])
        checks['barycentric']=primary.get('SPECSYS')=='BARYCENT'
        checks['single_exposure']=primary.get('NCOMBINE')==1 and not isinstance(primary.get('NCOMBINE'),bool)
        checks['resolution_115000']=primary.get('SPEC_RES')==115000
        checks['high_resolution_fiber_HEFS_false']=primary.get('ESO INS HEFS ST')is False
        checks['one_table_row']=extension.get('NAXIS2')==1
        names=[extension.get('TTYPE'+str(i))for i in range(1,int(extension.get('TFIELDS',0))+1)]
        canonical_names=[str(name).strip().casefold()for name in names if name is not None and str(name).strip()]
        checks['valid_table_field_names']=all(isinstance(name,str)and name.strip()for name in names)
        checks['unique_spectral_field_names']=len(canonical_names)==len(set(canonical_names))
        fields={name:i for i,name in enumerate(names,1)}
        checks['wave_flux_err_columns']=all(k in fields for k in ['WAVE','FLUX','ERR'])
        wave_i=fields.get('WAVE',0);flux_i=fields.get('FLUX',0)
        checks['wave_angstrom']=str(extension.get('TUNIT'+str(wave_i),'')).lower()=='angstrom'
        checks['air_wavelength']='obs.atmos'in str(extension.get('TUCD'+str(wave_i),''))
        checks['flux_adu']=str(extension.get('TUNIT'+str(flux_i),'')).lower()=='adu'
        checks['berv_matches_selection']=isinstance(primary.get('ESO DRS BERV'),(int,float))and not isinstance(primary.get('ESO DRS BERV'),bool)and math.isfinite(primary['ESO DRS BERV'])and abs(primary['ESO DRS BERV']-record['berv_km_s'])<=1e-8
        failures=[k for k,v in checks.items()if not v]
        return {'status':'PASS_COMPATIBLE_HEADERS'if not failures else'BLOCKED_INCOMPATIBLE_HEADERS',
                'checks':checks,'failures':failures,'date_obs':primary.get('DATE-OBS'),'mjd_obs':primary.get('MJD-OBS'),
                'exptime':primary.get('EXPTIME'),'berv_km_s':record['berv_km_s'],
                'processing_software':primary.get('PROCSOFT'),
                'recorded_instrument_mode':primary.get('ESO INS MODE'),
                'recorded_HEFS_state':primary.get('ESO INS HEFS ST'),
                'original_file':primary.get('ORIGFILE'),
                'pipeline_difference':primary.get('PROCSOFT')!='HARPS_3.8',
                'new_science_array_read':False}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--release',type=Path,default=HERE/'COMPARISON_RELEASE.json')
    args=parser.parse_args()
    method,reference=verified_original_module()
    release,inputs,links=validate_release(args.release)
    release_digest=sha(args.release)
    events=read(HERE/'EVENTS.json')
    refarrays={}
    for event in events:
        for frame,ref in event['discovery_profiles'].items():
            path=HERE/'inputs'/ref['profile_path']
            if sha(path)!=ref['profile_sha256']:raise ValueError('Existing reference profile changed')
            with np.load(path,allow_pickle=False)as archive:
                offset=np.array(archive['offset_air_angstrom'],copy=True)
                residual=np.array(archive['residual'],copy=True)
            if not np.array_equal(offset,method.X)or residual.shape!=(201,):raise ValueError('Original reference grid changed')
            refarrays[(event['candidate_id'],frame)]=residual
    output=HERE/'results'
    if output.exists():raise RuntimeError('Preserve existing comparison attempt; use a separate reproduction copy')
    output.mkdir()
    dump(output/'STARTED.json',{'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                              'release_sha256':release_digest,'release':release,'new_science_arrays_read':False})
    headers=[]
    for item in inputs:
        try:inspection=inspect_payload_headers(item)
        except Exception as error:inspection={'status':'BLOCKED_HEADER_READ','failures':[repr(error)],'new_science_array_read':False}
        headers.append({'dp_id':item['dp_id'],'target':item['target'],**inspection})
    dump(output/'PAYLOAD_HEADER_VALIDATION.json',headers)
    # All product headers have now been inspected; incompatible slots remain explicit.
    rows=[];array_inputs=[]
    profiles=output/'profiles';profiles.mkdir()
    for item,inspection in zip(inputs,headers):
        selected=[e for e in events if e['target']==item['target']]
        reason=None
        if inspection['status']!='PASS_COMPATIBLE_HEADERS':
            reason=inspection['status']
        else:
            try:
                with fits.open(path_in_repo(item['local_path']),memmap=False)as hd:
                    wave=np.array(hd[1].data['WAVE'][0],float)
                    flux=np.array(hd[1].data['FLUX'][0],float)
                    error=np.array(hd[1].data['ERR'][0],float)
                array_inputs.append(item['dp_id'])
                if wave.ndim!=1 or len(wave)<2 or wave.shape!=flux.shape or wave.shape!=error.shape:raise ValueError('Incompatible array shape')
                if not np.isfinite(wave).all()or not(np.diff(wave)>0).all():raise ValueError('Wavelength must be finite strictly increasing')
            except Exception as exc:reason='BLOCKED_ARRAY_VALIDATION:'+repr(exc)
        for event in selected:
            for frame in ['barycentric','topocentric']:
                base={'candidate_id':event['candidate_id'],'target':event['target'],'source_dp_id':event['discovery_dp_id'],
                      'dp_id':item['dp_id'],'frame':frame,'is_discovery_exposure':False,
                      'input_sha256':item.get('sha256'),'source_berv_km_s':event['discovery_berv_km_s'],
                      'berv_km_s':inspection.get('berv_km_s'),'date_obs':inspection.get('date_obs'),
                      'mjd_obs':inspection.get('mjd_obs'),'exptime':inspection.get('exptime'),
                      'processing_software':inspection.get('processing_software'),'pipeline_difference':inspection.get('pipeline_difference'),
                      'original_classification':'U','classification_changed':False}
                if reason is not None:
                    rows.append({**base,'status':reason,'profile_path':None,'profile_sha256':None,'correlation_to_discovery':None})
                    continue
                bary=event['fitted_center_bary_air_angstrom']
                center=bary if frame=='barycentric'else bary/(1+event['discovery_berv_km_s']/method.C)
                scale=1.0 if frame=='barycentric'else 1+inspection['berv_km_s']/method.C
                arrays,metrics=method.profile(wave,flux,error,center,scale)
                filename=event['candidate_id']+'_'+item['dp_id'].replace(':','_')+'_'+frame+'.npz'
                dest=profiles/filename
                with dest.open('xb')as stream:np.savez_compressed(stream,**arrays)
                delta=inspection['berv_km_s']-event['discovery_berv_km_s']
                rows.append({**base,'status':'MEASURED_DESCRIPTIVE_CONTEXT',
                             'berv_delta_from_source_km_s':delta,'source_epoch_displacement_resolution_elements':abs(delta)/method.C*115000,
                             'profile_path':str(dest.relative_to(output)),'profile_sha256':sha(dest),
                             **metrics,'correlation_to_discovery':method.corr(refarrays[(event['candidate_id'],frame)],arrays['residual'])})
    expected=2*sum(sum(e['target']==i['target']for e in events)for i in inputs)
    if len(rows)!=expected:raise ValueError('Selected event/frame slots lost')
    dump(output/'ALL_COMPARISON_MEASUREMENTS.json',rows)
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with(output/'ALL_COMPARISON_MEASUREMENTS.csv').open('x',newline='')as stream:
        writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(rows)
    summaries=[]
    for event in events:
        erows=[r for r in rows if r['candidate_id']==event['candidate_id']]
        frames={}
        for frame in ['barycentric','topocentric']:
            selected=[r for r in erows if r['frame']==frame]
            measured=[r for r in selected if r['status']=='MEASURED_DESCRIPTIVE_CONTEXT']
            frames[frame]={'selected_epoch_slots':len(selected),'measured_epochs':len(measured),
                           'blocked_epochs':len(selected)-len(measured),
                           'correlation_to_discovery':method.stats([r['correlation_to_discovery']for r in measured]),
                           'narrow_amplitude':method.stats([r['narrow_amplitude']for r in measured]),
                           'broad3_amplitude':method.stats([r['broad3_amplitude']for r in measured]),
                           'integrated_excess':method.stats([r['core_flux_integral_over_linear_background']for r in measured]),
                           'low_continuum_count':sum(r['local_continuum_low']for r in measured)}
        summaries.append({'candidate_id':event['candidate_id'],'target':event['target'],'frames':frames,
                          'origin_assignment':'NOT_PERFORMED','original_classification':'U'})
    dump(output/'EVENT_RESULTS.json',summaries)
    # Recheck immutable method, metadata and reference inputs after execution.
    verified_original_module()
    if sha(args.release)!=release_digest:raise ValueError('Root release changed during comparison')
    validate_release(args.release)  # Recheck selection, headers, receipt and acquired-byte hashes.
    for ref in reference['restored']:
        if sha(HERE/ref['path'])!=ref['sha256']:raise ValueError('Reference array file changed during comparison')
    measured_rows=[r for r in rows if r['status']=='MEASURED_DESCRIPTIVE_CONTEXT']
    run_status=('ALL_SELECTED_SLOTS_BLOCKED_NO_NEW_COMPARISON'if not measured_rows else
                'COMPLETE_FIXED_DESCRIPTIVE_COMPARISON'if len(measured_rows)==len(rows)else
                'PARTIAL_FIXED_DESCRIPTIVE_COMPARISON_WITH_BLOCKED_SLOTS')
    dump(output/'SUMMARY.json',{'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                               'status':run_status,
                               'events':len(events),'selected_new_epoch_slots':len(inputs),'new_input_arrays_read':array_inputs,
                               'events_with_measured_new_profiles':len({r['candidate_id']for r in measured_rows}),
                               'new_epoch_products_measured':len({r['dp_id']for r in measured_rows}),
                               'event_epoch_pairs':expected//2,'frame_slots':len(rows),
                               'measured_profiles':sum(r['status']=='MEASURED_DESCRIPTIVE_CONTEXT'for r in rows),
                               'blocked_profiles':sum(r['status']!='MEASURED_DESCRIPTIVE_CONTEXT'for r in rows),
                               'discovery_references_reused':len(refarrays),'original100_rerun':False,
                               'origin_assignments':0,'repeat_classifications':0,'U_labels_changed':0,
                               'release_sha256':release_digest,'prospective_plan_sha256':sha(HERE/'PLAN.json'),
                               'comparison_script_sha256':sha(Path(__file__)),'original_metrics_script_sha256':sha(EPOCH/'measure_epochs.py'),
                               'limits':read(HERE/'PLAN.json')['limitations']})
    dump(output/'OUTPUT_HASHES.json',{str(p.relative_to(output)):sha(p)for p in sorted(output.rglob('*'))if p.is_file()})
    print(json.dumps(read(output/'SUMMARY.json'),indent=2))


if __name__=='__main__':
    main()
