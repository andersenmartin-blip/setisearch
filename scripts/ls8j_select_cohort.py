#!/usr/bin/env python3
"""LS8J archive-wide CHEOPS metadata-only cohort selection."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls8j_selection'
LIMIT=1000
MAX_STACKED=60.0
EXCLUDED={re.sub(r'[^a-z0-9]+','',x.lower()) for x in ('55 Cnc','GJ 876','GJ 514','GJ 849','GJ 649')}
REQUIRED={'SCI_CAL_SubArray','SCI_COR_SubArray'}

def scalar(v:Any)->Any:
    if hasattr(v,'item'): v=v.item()
    if isinstance(v,bytes): return v.decode()
    if isinstance(v,float) and not math.isfinite(v): return None
    return v

def rows(data):
    if not data:return []
    lengths=[len(v) for v in data.values() if hasattr(v,'__len__') and not isinstance(v,(str,bytes))]
    if not lengths:return []
    n=min(lengths)
    return [{k:scalar(v[i]) for k,v in data.items()} for i in range(n)]

def norm(v):
    return re.sub(r'[^a-z0-9]+','',str(v or '').lower())

def basic(row):
    reasons=[]
    key=str(row.get('file_key') or '')
    if not key.endswith('_V0300'):reasons.append('NOT_V0300')
    if str(row.get('data_pipe_version') or '')!='14.1.2':reasons.append('PIPE_NOT_14_1_2')
    if row.get('status_published') is not True:reasons.append('NOT_PUBLISHED')
    if row.get('db_lc_available') is not True:reasons.append('NO_PUBLIC_LC')
    name=str(row.get('obj_id_catname') or '').strip()
    if not name:reasons.append('NO_TARGET_NAME')
    try:
        ex=float(row.get('obs_exptime')); ne=int(row.get('obs_nexp')); st=float(row.get('obs_total_exptime'))
        if not(math.isfinite(ex) and ex>0):reasons.append('BAD_EXPTIME')
        if ne<=0:reasons.append('BAD_NEXP')
        if not(math.isfinite(st) and 0<st<=MAX_STACKED):reasons.append('STACKED_EXPOSURE_OUTSIDE_BOUND')
    except (TypeError,ValueError):reasons.append('MISSING_EXPOSURE_METADATA')
    if not key:reasons.append('NO_FILE_KEY')
    if norm(name) in EXCLUDED:reasons.append('CLOSED_HOST')
    return not reasons,reasons

def product_flags(data):
    rr=rows(data)
    types={str(r.get('file_ext') or '') for r in rr}
    files=[str(r.get('file') or '') for r in rr]
    default=any('SCI_COR_Lightcurve-DEFAULT' in f and f.endswith('_V0300.fits') for f in files)
    return {'product_rows':len(rr),'has_default_lightcurve':default,
            'has_cal_subarray':'SCI_CAL_SubArray' in types,
            'has_cor_subarray':'SCI_COR_SubArray' in types,
            'eligible':default and REQUIRED<=types,
            'file_types':sorted(types)}

def save(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    assert not OUT.exists(),'refuse completed LS8J selection overwrite'
    OUT.mkdir();(OUT/'products').mkdir()
    from dace_query import DaceClass
    from dace_query.cheops import CheopsClass
    client=CheopsClass(DaceClass(dace_rc_config_path=Path('/dev/null')))

    result=client.query_database(
        limit=LIMIT,
        filters={'status_published':{'equal':[True]}},
        sort={'date_mjd_start':'asc'},
        output_format='dict',
    )
    plain={k:[scalar(x) for x in v] for k,v in result.items()}
    census=rows(result)
    assert 0<len(census)<=LIMIT
    save(OUT/'census.json',{'limit':LIMIT,'sort':'date_mjd_start asc',
                            'published_filter':True,'row_count':len(census),'result':plain})

    by_key={}
    for r in census:
        key=str(r.get('file_key') or '')
        if key and key not in by_key:by_key[key]=r

    ledger=[]
    for r in sorted(by_key.values(),key=lambda x:(float(x.get('date_mjd_start') or 1e99),str(x.get('file_key') or ''))):
        ok,reasons=basic(r)
        rec={k:scalar(r.get(k)) for k in (
            'file_key','visit_id','obs_id','obj_id_catname','date_mjd_start','date_mjd_end',
            'data_pipe_version','data_arch_rev','obs_exptime','obs_nexp','obs_total_exptime',
            'status_published','db_lc_available')}
        rec['normalized_target']=norm(rec['obj_id_catname'])
        rec['basic_eligible']=ok;rec['reasons']=list(reasons)
        if ok:
            products=client.browse_products(filters={'file_key':{'equal':[rec['file_key']]}},
                                            file_type='all',output_format='dict')
            flags=product_flags(products)
            save(OUT/'products'/f"{rec['file_key']}.json",flags)
            rec['products']=flags
            if not flags['has_default_lightcurve']:rec['reasons'].append('NO_DEFAULT_LIGHTCURVE_PRODUCT')
            if not flags['has_cal_subarray']:rec['reasons'].append('NO_CAL_SUBARRAY')
            if not flags['has_cor_subarray']:rec['reasons'].append('NO_COR_SUBARRAY')
        rec['eligible']=ok and not rec['reasons']
        ledger.append(rec)

    groups={}
    for r in ledger:
        if r['eligible']:groups.setdefault(r['normalized_target'],[]).append(r)
    cohorts=[]
    for name,visits in groups.items():
        visits.sort(key=lambda r:(float(r['date_mjd_start']),str(r['file_key'])))
        if len(visits)>=2:
            cohorts.append({'normalized_target':name,
                            'archive_target_name':visits[0]['obj_id_catname'],
                            'eligible_visit_count':len(visits),
                            'first_mjd':float(visits[0]['date_mjd_start']),
                            'second_mjd':float(visits[1]['date_mjd_start']),
                            'eligible_file_keys':[v['file_key'] for v in visits],
                            'selected_visits':visits[:2]})
    cohorts.sort(key=lambda c:(c['second_mjd'],c['first_mjd'],c['normalized_target']))
    for i,c in enumerate(cohorts,1):c['rank']=i
    selected=cohorts[0] if cohorts else None

    out={'stage':'LS8J_ARCHIVE_WIDE_METADATA_SELECTION',
         'status':'SELECTED' if selected else 'NO_ELIGIBLE_COHORT_IN_BOUNDED_CENSUS',
         'census_limit':LIMIT,'census_rows':len(census),'unique_file_keys':len(by_key),
         'excluded_normalized_targets':sorted(EXCLUDED),
         'requirements':{'visit_version':'V0300','pipeline':'14.1.2','published':True,
                         'public_lightcurve_available':True,'max_stacked_exposure_seconds':MAX_STACKED,
                         'required_products':['SCI_COR_Lightcurve-DEFAULT','SCI_CAL_SubArray','SCI_COR_SubArray'],
                         'minimum_eligible_visits':2,
                         'cohort_rank':'second eligible MJD, first eligible MJD, normalized target name'},
         'visit_ledger':ledger,'eligible_cohorts':cohorts,'selection':selected,
         'science_product_bytes_read':0,'fits_table_rows_read':0,'lightcurve_values_read':0,
         'image_pixels_read':0,'product_download_calls':0}
    save(OUT/'selection.json',out)
    files=sorted(p for p in OUT.rglob('*') if p.is_file())
    (OUT/'SHA256SUMS').write_text(''.join(f"{sha(p)}  {p.relative_to(OUT)}\n" for p in files if p.name!='SHA256SUMS'))
    print(json.dumps({'status':out['status'],'census_rows':len(census),
                      'eligible_cohorts':len(cohorts),
                      'selection':None if not selected else {
                          'rank':selected['rank'],'target':selected['archive_target_name'],
                          'visits':[v['file_key'] for v in selected['selected_visits']]},
                      'science_product_bytes_read':0},indent=2))

if __name__=='__main__':main()
