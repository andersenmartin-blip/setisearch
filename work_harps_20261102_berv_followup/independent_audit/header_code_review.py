#!/usr/bin/env python3
"""Independent, synthetic-only review of prospective HARPS header code.

No requests, FITS files or science arrays. Owner modules are loaded without
running their entry points. Extrema entry-point cases use synthetic metadata
and ephemeral local files. Only HEADER_CODE_REVIEW.json is retained.
"""
import contextlib
import copy
import csv
import hashlib
import html
import importlib.util
import io
import json
import math
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OWNER = HERE.parent / 'header_acquisition'
FILES = ['header_tools.py', 'make_plan.py', 'fetch_headers.py', 'select_extremes.py']
checks = []
sys.dont_write_bytecode = True


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def record(name, ok, detail=None):
    checks.append({'case':name,'passed':bool(ok),'detail':detail})


def module(name):
    spec=importlib.util.spec_from_file_location(name,OWNER/(name+'.py'))
    obj=importlib.util.module_from_spec(spec)
    sys.modules[name]=obj
    spec.loader.exec_module(obj)
    return obj


def mjd(y,m,d=1):
    return (datetime(y,m,d,tzinfo=timezone.utc)-datetime(1858,11,17,tzinfo=timezone.utc)).total_seconds()/86400


def card(key,value):
    if isinstance(value,str): literal="'"+value.replace("'","''")+"'"
    elif isinstance(value,bool): literal='T' if value else 'F'
    else: literal=repr(value)
    return (key+' = '+literal) if key.startswith('HIERARCH ') else (f'{key:8s}= '+literal)


def payload(header):
    return ('\n'.join(card(k,v) for k,v in header.items())+'\nEND\n').encode()


def rejected(call):
    try: call()
    except (ValueError,TypeError,KeyError,OverflowError): return True
    return False


def base_fixture(index=0,target='HD122640',berv=20.25):
    dt=datetime(2020,1,2,3,4,5,tzinfo=timezone.utc)
    stamp=f'2020-01-02T03:04:05.{index:03d}'
    dp='ADP.'+stamp
    raw='HARPS.'+stamp
    h={'SIMPLE':True,'ARCFILE':dp+'.fits','OBJECT':target.replace('HD','HD '),
       'INSTRUME':'HARPS','SPECSYS':'BARYCENT','NCOMBINE':1,'SPEC_RES':115000,
       'HIERARCH ESO INS HEFS ST':False,'HIERARCH ESO INS MODE':'HARPS+NIRPS',
       'PROV1':raw+'.fits','MJD-OBS':(dt-datetime(1858,11,17,tzinfo=timezone.utc)).total_seconds()/86400,
       'DATE-OBS':dt.isoformat(),'EXPTIME':900.0,'RA':210.9,'DEC':-27.01,
       'HIERARCH ESO DRS BERV':berv,'HIERARCH ESO DRS BERVMX':99.0,
       'WAVELMIN':378.29,'WAVELMAX':691.34,'SPEC_BIN':0.001,'FLUXCAL':'UNCALIBRATED'}
    job={'job_index':index,'target':target,'dp_id':dp,'month_number':1,'source_file_ids':[raw],
         'metadata':{'t_min':h['MJD-OBS'],'t_max':h['MJD-OBS']+900/86400,'t_exptime':900.0,'s_ra':210.9,'s_dec':-27.01}}
    return h,job


def selector_case(selector,tools,values,status='COMPLETE',damage=None,benchmarks=None):
    with tempfile.TemporaryDirectory(prefix='harps-independent-synthetic-') as td:
        d=Path(td); jobs=[]; rows=[]
        for filename in FILES:
            (d/filename).write_bytes((OWNER/filename).read_bytes())
        for i,(target,berv,disposition) in enumerate(values):
            h,job=base_fixture(i,target,berv)
            jobs.append(job)
            body=d/f'body{i}.txt'; body.write_bytes(payload(h))
            receipt=d/f'receipt{i}.json'; receipt.write_text(json.dumps({'synthetic':True,'dp_id':job['dp_id']}))
            inspection=tools.check_identity(h,job)
            rows.append({**{k:job[k] for k in ['job_index','target','dp_id','month_number']},
                'status':disposition,'inspection':inspection,
                'body_path':body.name,'body_sha256':sha(body),'receipt_path':receipt.name,'receipt_sha256':sha(receipt)})
        plan={'jobs':jobs,'code_hashes':{f:sha(OWNER/f) for f in FILES},
              'existing_berv_benchmark':{t:dict(minimum_berv_km_s=0,maximum_berv_km_s=0,span_km_s=0,
                  scope='synthetic_zero_baseline',existing_exposures=1) for t in ['HD122640','HD135204']},
              'payload_readiness_gate':{'combined_span_km_s_threshold':299792.458/115000},
              'extreme_selection_rule':'synthetic rule fixture for audited minimum/maximum arithmetic'}
        if benchmarks is not None:
            plan['existing_berv_benchmark']=benchmarks
        (d/'PLAN.json').write_text(json.dumps(plan))
        result={'status':status,'plan_sha256':sha(d/'PLAN.json'),'code_hashes':plan['code_hashes'],'results':rows}
        if damage: damage(result,plan)
        (d/'HEADER_RESULTS.json').write_text(json.dumps(result))
        old=selector.HERE; selector.HERE=d
        try:
            with contextlib.redirect_stdout(io.StringIO()): selector.main()
            return json.loads((d/'EXTREME_SELECTION.json').read_text())
        finally: selector.HERE=old


def main():
    before={f:sha(OWNER/f) for f in FILES}
    tools=module('header_tools'); planner=module('make_plan'); selector=module('select_extremes')
    h,job=base_fixture(); body=payload(h)
    parsed,evidence=tools.parse_header_response(body,'text/plain; charset=utf-8')
    record('synthetic_plain_primary_roundtrip',parsed==h and evidence['primary_only'])
    wrapped=('<html><pre>'+html.escape(body.decode())+'</pre></html>').encode()
    record('synthetic_html_primary_roundtrip',tools.parse_header_response(wrapped,'text/html')[0]==h)
    joined=''.join(line.ljust(80) for line in body.decode().splitlines()).encode()
    record('fixed80_card_roundtrip',tools.parse_header_response(joined,'text/plain')[0]==h)
    extended=body+b"XTENSION= 'BINTABLE'\nHIERARCH ESO DRS BERV = -99.0\nEND\n"
    record('extension_berv_not_substituted',tools.parse_header_response(extended,'text/plain')[0]['HIERARCH ESO DRS BERV']==20.25)
    record('quoted_slash_and_doubled_quote',tools.fits_value("'a/b''c' / comment")=="a/b'c")
    record('fortran_D_exponent',tools.fits_value('1.25D+01 / comment')==12.5)
    malformed=[('missing_end',body.rsplit(b'END',1)[0],'text/plain'),
        ('duplicate_berv',body.replace(b'END',b'HIERARCH ESO DRS BERV = 1\nEND'),'text/plain'),
        ('two_primaries',body+body,'text/plain'),('binary_byte',body+b'\x00','text/plain'),
        ('unsupported_mime',body,'application/fits'),('no_primary',b'ERROR 503\n','text/plain'),
        ('unclosed_pre',b'<pre>'+body,'text/html'),('nested_pre',b'<pre><pre>'+body+b'</pre></pre>','text/html'),
        ('unterminated_string',body.replace(b"'HARPS'",b"'HARPS"),'text/plain')]
    for name,b,mime in malformed:
        record('parser_reject_'+name,rejected(lambda b=b,mime=mime:tools.parse_header_response(b,mime)))
    result=tools.check_identity(h,job)
    record('valid_header_identity_pass',result['status']=='PASS_RECORDED_BERV' and not result['failures'])
    record('primary_band_units_remain_provisional',result['table_units_air_wavelength_compatibility']=='PROVISIONAL_REQUIRE_PAYLOAD_HEADERS_BEFORE_ARRAY_ACCESS')
    mutations=[('wrong_adp','ARCFILE','ADP.1999-01-01T00:00:00.000.fits','EXCLUDED_HEADER_VALIDATION'),
        ('wrong_target','OBJECT','HD 135204','EXCLUDED_HEADER_VALIDATION'),
        ('wrong_instrument','INSTRUME','ESPRESSO','EXCLUDED_HEADER_VALIDATION'),
        ('wrong_frame','SPECSYS','TOPOCENT','EXCLUDED_HEADER_VALIDATION'),
        ('combined','NCOMBINE',2,'EXCLUDED_HEADER_VALIDATION'),
        ('boolean_ncombine','NCOMBINE',True,'EXCLUDED_HEADER_VALIDATION'),
        ('wrong_spec_res','SPEC_RES',80000,'EXCLUDED_HEADER_VALIDATION'),
        ('eggs','HIERARCH ESO INS HEFS ST',True,'EXCLUDED_HEADER_VALIDATION'),
        ('unknown_mode','HIERARCH ESO INS HEFS ST',None,'PENDING_MODE_COMPATIBILITY'),
        ('integer_mode_not_boolean','HIERARCH ESO INS HEFS ST',0,'PENDING_MODE_COMPATIBILITY'),
        ('text_mode_not_boolean','HIERARCH ESO INS HEFS ST','F','PENDING_MODE_COMPATIBILITY'),
        ('missing_berv','HIERARCH ESO DRS BERV',None,'EXCLUDED_HEADER_VALIDATION'),
        ('boolean_berv','HIERARCH ESO DRS BERV',False,'EXCLUDED_HEADER_VALIDATION'),
        ('nan_berv','HIERARCH ESO DRS BERV',float('nan'),'EXCLUDED_HEADER_VALIDATION'),
        ('infinite_berv','HIERARCH ESO DRS BERV',float('inf'),'EXCLUDED_HEADER_VALIDATION'),
        ('inherited_berv_bound_positive','HIERARCH ESO DRS BERV',100.00001,'EXCLUDED_HEADER_VALIDATION'),
        ('inherited_berv_bound_negative','HIERARCH ESO DRS BERV',-100.00001,'EXCLUDED_HEADER_VALIDATION'),
        ('huge_finite_berv','HIERARCH ESO DRS BERV',1e300,'EXCLUDED_HEADER_VALIDATION'),
        ('wrong_raw','PROV1','HARPS.1999-01-01T00:00:00.000.fits','EXCLUDED_HEADER_VALIDATION'),
        ('substring_raw','PROV1','PREFIX'+h['PROV1']+'SUFFIX','EXCLUDED_HEADER_VALIDATION'),
        ('extra_adp_provenance','PROV2','ADP.1999-01-01T00:00:00.000.fits','EXCLUDED_HEADER_VALIDATION'),
        ('extra_raw','PROV2','HARPS.1999-01-01T00:00:00.000.fits','EXCLUDED_HEADER_VALIDATION'),
        ('wrong_mjd','MJD-OBS',h['MJD-OBS']+2e-7,'EXCLUDED_HEADER_VALIDATION'),
        ('wrong_date','DATE-OBS','2020-01-02T03:04:05.03Z','EXCLUDED_HEADER_VALIDATION'),
        ('wrong_exptime','EXPTIME',900.021,'EXCLUDED_HEADER_VALIDATION'),
        ('wrong_dec','DEC',h['DEC']+1.01/3600,'EXCLUDED_HEADER_VALIDATION')]
    for name,key,val,expected in mutations:
        modified={**h,key:val}; observed=tools.check_identity(modified,job)
        record(name,observed['status']==expected,{'expected':expected,'observed':observed['status']})
    for berv in [-100,0,100]:
        record('berv_bound_inclusive_'+str(berv),tools.check_identity({**h,'HIERARCH ESO DRS BERV':berv},job)['status']=='PASS_RECORDED_BERV')
    removed={k:v for k,v in h.items() if k!='HIERARCH ESO DRS BERV'}
    record('bervmx_never_substituted',tools.check_identity(removed,job)['status']=='EXCLUDED_HEADER_VALIDATION')
    record('within_timing_tolerances',tools.check_identity({**h,'MJD-OBS':h['MJD-OBS']+0.5e-7,'EXPTIME':900.019},job)['status']=='PASS_RECORDED_BERV')
    record('within_position_tolerance',tools.check_identity({**h,'DEC':h['DEC']+.99/3600},job)['status']=='PASS_RECORDED_BERV')
    candidates=[]
    for ti,target in enumerate(['HD122640','HD135204']):
        for year in [2010,2020,2025]:
            for month in range(1,13):
                stamp=f'{year}-{month:02d}-01T0{ti}:00:00.000'
                candidates.append({'status':'METADATA_CANDIDATE_PENDING_HEADER_IDENTITY_BERV','reasons':[],
                    'target':target,'dp_id':'ADP.'+stamp,'source_file_ids':['HARPS.'+stamp],
                    'metadata':{'t_min':mjd(year,month)+ti/24,'snr':100000 if year==2010 else 1}})
    chosen=planner.select(list(reversed(candidates)))
    record('24_month_number_latest_across_all_years',len(chosen)==24 and all('2025-' in r['dp_id'] for r in chosen))
    record('fixed_target_then_month_order',[(r['target'],r['month_number']) for r in chosen]==[(t,m) for t in ['HD122640','HD135204'] for m in range(1,13)])
    record('sequential_job_indices',[r['job_index'] for r in chosen]==list(range(24)))
    older=copy.deepcopy(candidates[-1]); older['dp_id']='ADP.2001-12-01T01:00:00.000'
    record('equal_time_lexicographic_dp_tie',planner.select(candidates+[older])[-1]['dp_id']==older['dp_id'])
    unwanted=copy.deepcopy(older); unwanted['status']='EXCLUDED'; unwanted['metadata']['t_min']=mjd(2026,12)
    record('excluded_candidate_skipped',planner.select(candidates+[unwanted])==chosen)
    unwanted['status']='METADATA_CANDIDATE_PENDING_HEADER_IDENTITY_BERV'; unwanted['reasons']=['unresolved']
    record('nonempty_reasons_skipped',planner.select(candidates+[unwanted])==chosen)
    record('empty_months_not_filled',len(planner.select(candidates[:1]))==1)
    record('boundary_december_vs_january', [r['month_number'] for r in planner.select([
        {**candidates[0],'dp_id':'ADP.2020-01-01T00:00:00.000','source_file_ids':['HARPS.2020-01-01T00:00:00.000'],'metadata':{'t_min':mjd(2020,1)}},
        {**candidates[0],'dp_id':'ADP.2019-12-31T23:59:59.000','source_file_ids':['HARPS.2019-12-31T23:59:59.000'],'metadata':{'t_min':mjd(2020,1)-1/86400}},
    ])]==[1,12])
    values=[('HD122640',10,'PASS_RECORDED_BERV'),('HD122640',-20,'PASS_RECORDED_BERV'),
            ('HD122640',10,'PASS_RECORDED_BERV'),('HD122640',90,'EXCLUDED_HEADER_VALIDATION'),
            ('HD135204',4,'PASS_RECORDED_BERV'),('HD135204',4,'PASS_RECORDED_BERV')]
    extreme=selector_case(selector,tools,values)
    record('extrema_min_max_ties_equal_range',[(r['target'],r['berv_km_s'],r['header_result_job_index']) for r in extreme['selected']]==[
        ('HD122640',-20,1),('HD122640',10,0),('HD135204',4,4)])
    record('extrema_scope_no_payload_authorization',extreme['spectral_payload_acquisition_authorized'] is False)
    record('extrema_span_arithmetic',extreme['target_summary']['HD122640']['recorded_berv_span_km_s']==30
        and extreme['target_summary']['HD135204']['recorded_berv_span_km_s']==0)
    record('extrema_combined_range_arithmetic',extreme['target_summary']['HD122640']['combined_span_km_s']==30
        and extreme['target_summary']['HD135204']['combined_span_km_s']==4)
    record('excluded_or_uninspected_rows_flag_partial_sample',extreme['header_sampling_is_partial'] is True)
    resolution=299792.458/115000
    for label,value,expected in [('below',resolution-1e-9,False),('exact',resolution,False),('above',resolution+1e-9,True)]:
        out=selector_case(selector,tools,[('HD122640',value,'PASS_RECORDED_BERV')])
        record('planning_coverage_strict_boundary_'+label,out['target_summary']['HD122640']['payload_readiness_gate_passed'] is expected)
    coverage_path=ROOT/'work_harps_20261101/v2/extension02/next_followup_20261102/BERV_COVERAGE.csv'
    benchmark={}
    for row in csv.DictReader(coverage_path.open()):
        if row['scope']=='all_existing300':
            lo,hi=map(float,[row['berv_min_km_s'],row['berv_max_km_s']])
            benchmark[row['target']]={'minimum_berv_km_s':lo,'maximum_berv_km_s':hi,'span_km_s':hi-lo,
                'scope':'all_existing300','existing_exposures':int(row['exposures'])}
    for target,b in benchmark.items():
        for label,new_values in [('inside',[(b['minimum_berv_km_s']+b['maximum_berv_km_s'])/2]),
            ('lower',[b['minimum_berv_km_s']-3]),('upper',[b['maximum_berv_km_s']+3]),
            ('both',[b['minimum_berv_km_s']-3,b['maximum_berv_km_s']+3])]:
            values2=[(target,v,'PASS_RECORDED_BERV') for v in new_values]
            out=selector_case(selector,tools,values2,benchmarks=benchmark)
            actual=out['target_summary'][target]
            expected=max(new_values+[b['maximum_berv_km_s']])-min(new_values+[b['minimum_berv_km_s']])
            record(target+'_historical_combined_'+label,abs(actual['combined_span_km_s']-expected)<1e-12
                and abs(actual['combined_span_increase_km_s']-(expected-b['span_km_s']))<1e-12
                and actual['payload_readiness_gate_passed']==(expected>resolution)
                and abs(actual['combined_span_resolution_elements_R115000']-expected/resolution)<1e-12)
    record('extrema_reject_in_progress',rejected(lambda:selector_case(selector,tools,values,'IN_PROGRESS')))
    record('extrema_reject_changed_plan_digest',rejected(lambda:selector_case(selector,tools,values,damage=lambda r,p:r.update(plan_sha256='0'*64))))
    record('extrema_reject_result_job_identity_mismatch',rejected(lambda:selector_case(selector,tools,values,
        damage=lambda r,p:r['results'][1].update(dp_id='ADP.1999-01-01T00:00:00.000'))))
    record('extrema_reject_result_code_hash_mismatch',rejected(lambda:selector_case(selector,tools,values,
        damage=lambda r,p:r.update(code_hashes={}))))
    after={f:sha(OWNER/f) for f in FILES}
    record('owner_code_unchanged_during_review',before==after)
    plan_path=OWNER/'PLAN.json'
    input_status={'plan_exists':plan_path.exists(),'scientific_code_hashes':after}
    if plan_path.exists():
        plan=json.loads(plan_path.read_text()); input_status['plan_sha256']=sha(plan_path)
        input_status['planned_jobs']=len(plan.get('jobs',[]))
        input_status['candidate_input_hashes']=plan.get('inputs',[])
        record('available_plan_code_hashes_match',plan['code_hashes']==after)
        record('available_plan_frozen_maxima',plan['limits']==dict(max_jobs=24,max_jobs_per_target=12,timeout_seconds=30,
            max_response_bytes=524288,max_total_response_bytes=12582912,attempts_per_job=1,retries=0,redirects=0))
    failed=[r['case'] for r in checks if not r['passed']]
    report={'schema':'INDEPENDENT_HARPS_PROSPECTIVE_HEADER_CODE_REVIEW_V1',
        'status':'CONTINGENT_SYNTHETIC_PASS' if not failed else 'REVISION_REQUIRED',
        'created_utc':datetime.now(timezone.utc).isoformat(),'audit_script_sha256':sha(Path(__file__)),
        'scope':dict(network_requests=0,science_arrays_read=0,actual_header_products_opened=0,owner_files_mutated=0),
        'cases_passed':sum(r['passed'] for r in checks),'cases_total':len(checks),'failed_cases':failed,'cases':checks,
        'inputs':input_status,'saved_baseline_source':{'path':str(coverage_path.relative_to(ROOT)),'sha256':sha(coverage_path)},
        'scientific_conclusions':[
            'Month selection uses latest t_min per calendar month number across all years, in fixed target/month order; no BERV, SNR or morphology ranking enters this first stage.',
            'Extrema are minimum/maximum recorded BERV only among passing inspected headers. They are extrema of the bounded inspected sample, not the archive or entire target history.',
            'The root-authorized prospective operational readiness requirement uses combined existing+passing-new BERV span strictly greater than c/115000. Equality does not pass; this changes no scientific classification or statistical-power criterion.',
            'Primary SPECSYS=BARYCENT and SPEC_RES=115000 plus explicit HEFS=false are tested; HEFS missing or nonboolean remains pending. INS MODE text alone is not used to infer high-resolution compatibility.',
            'Primary WAVELMIN/WAVELMAX/SPEC_BIN and flux calibration fields do not establish table units, air/vacuum convention, event-window coverage or usable science arrays. These remain explicitly provisional for a separate payload-header plan.',
            'Any later event comparison must retain barycentric air wavelengths, no stellar-RV correction, classical inverse BERV with c=299792.458 km/s, and original frame-specific windows/positive continuum normalization. No such numerical science operation is performed here.',
            'BERV alone neither identifies an emission origin nor makes an event statistical classification. Resolution c/115000 is a descriptive coverage scale, not a significance threshold.'
        ],
        'limitations':[
            'This review is contingent until real metadata candidates, exact header IDs, final code/plan hashes and a separate root release exist and are independently reconciled.',
            'No actual new header was requested or parsed; server rendering remains untested until the frozen canary. Unexpected formats must stop without fallback.',
            'Transport deadlines, byte caps, no-repeat and root-release enforcement are outside this scientific review and are reviewed by the parent/other independent preflight.',
            'Selection may be partial if requests stop; any reported BERV range must be labelled as the passing inspected sample, and no uninspected month is implied absent.'
        ]}
    (HERE/'HEADER_CODE_REVIEW.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ['status','cases_passed','cases_total','failed_cases']}))
    return bool(failed)


if __name__=='__main__':
    raise SystemExit(main())
