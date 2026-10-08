"""Independent endpoint arithmetic audit; use original endpoint equalities."""
import csv,json,hashlib,statistics
from decimal import Decimal,getcontext
from pathlib import Path
getcontext().prec=45
OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[1]; D=lambda x:Decimal(str(x))
with (OUT/'pulse_geometry.csv').open(newline='') as f: rows=list(csv.DictReader(f))
result=json.loads((OUT/'PULSE_GEOMETRY.json').read_bytes()); assert len(rows)==8114
counts={'full':0,'point':0,'point_not_full':0}; max_error=Decimal(0); absolute=[]; table={}
for r in rows: table[(r['case_id'],r['ON_scan'],int(r['carrier']))]=r
assert len(table)==8114
case_summaries=[]
for i in range(118,130):
    p=ROOT/f'results/radio_pilot_val_b_20261008/case_{i:03d}'
    c=json.loads((p/'case_definition.json').read_bytes());t=json.loads((p/'truth.json').read_bytes());hs=json.loads((p/'all_ON_threshold_carriers.json').read_bytes());rec=json.loads((p/'localized_recovery.json').read_bytes())
    manifest=json.loads((p/'artifact_manifest.json').read_bytes());marker=json.loads((p/'COMMITTED.json').read_bytes())
    assert hashlib.sha256((p/'artifact_manifest.json').read_bytes()).hexdigest()==marker['artifact_manifest_SHA256']
    for name in ['case_definition.json','truth.json','all_ON_threshold_carriers.json','localized_recovery.json']:
        b=(p/name).read_bytes();assert hashlib.sha256(b).hexdigest()==manifest[name]['SHA256'] and len(b)==manifest[name]['size_bytes']
    cc={'full':0,'point':0,'point_not_full':0}; errors=[]
    for h in hs:
        r=table.pop((c['case_id'],h['scan_id'],h['reference_carrier_index']));assert c['transient_row'] in [0,15]
        # The pulse is in the first or last integration; select the recorded
        # endpoint directly, independently of first + row * tsamp arithmetic.
        times=[D(h['scan_first_time_from_tref_s']),D(h['scan_last_time_from_tref_s'])];pt=times[0 if c['transient_row']==0 else 1]
        deltaf=D(h['reference_frequency_hz'])-D(t['reference_frequency_hz']);dd=D(h['drift_hz_s'])-D(t['drift_hz_s']);scale=abs(D(h['df_hz']))
        ep=[(deltaf+dd*time)/scale for time in times];pe=(deltaf+dd*pt)/scale;oracle=t['flux_by_scan'][h['scan_id']]['injection_oracle_width_channels'];tol=D(2)+D(max(h['width_channels'],oracle))/D(2)
        assert tol==D('18.5')
        assert abs(abs(pe)-tol)>D('0.0000003') and abs(max(map(abs,ep))-tol)>D('0.0000003')
        expected={'pulse_midpoint_time_from_tref_s':pt,'signed_first_ON_frequency_error_over_abs_df':ep[0],'signed_pulse_midpoint_frequency_error_over_abs_df':pe,'signed_last_ON_frequency_error_over_abs_df':ep[1],'absolute_pulse_midpoint_frequency_error_over_abs_df':abs(pe),'frozen_recovery_tolerance_over_abs_df':tol}
        for key,value in expected.items():
            error=abs(D(r[key])-value);max_error=max(max_error,error);assert error<D('0.0000003'),(i,key,error)
        full=max(map(abs,ep))<=tol;point=abs(pe)<=tol
        assert r['original_full_ON_endpoint_truth_localized']==str(full) and r['pulse_point_within_widthwise_oracle_tolerance']==r['pulse_point_within_fixed_18_5_channel_widths']==str(point)
        assert r['original_disposition']==h['disposition']=='SURVIVOR_EXPLORATORY'
        assert D(r['original_ON_score'])==D(h['ON_robust_score']) and D(r['winning_width_channels'])==D(h['width_channels']) and D(r['winning_drift_hz_s'])==D(h['drift_hz_s'])
        for key,value in [('full',full),('point',point),('point_not_full',point and not full)]:cc[key]+=value;counts[key]+=value
        errors.append(float(abs(pe)));absolute.append(float(abs(pe)))
    assert cc['full']==rec['per_active_ON_scan'][t['active_ON_scan_ids'][0]]['final_localized_count']
    saved=next(x for x in result['cases'] if x['case_index']==i);assert saved['original_surviving_carriers']==len(hs) and saved['original_full_endpoint_localized_carriers']==cc['full'] and saved['pulse_point_within_fixed_18_5_carriers']==cc['point']
    for key,v in [('minimum',min(errors)),('median',statistics.median(errors)),('maximum',max(errors))]:assert abs(saved['absolute_pulse_point_error_over_abs_df'][key]-v)<3e-7
    case_summaries.append({'case_index':i,'carriers':len(hs),**cc})
assert not table and counts=={'full':428,'point':8103,'point_not_full':7675}
report={'review_status':'PASS_INDEPENDENT_SAVED_PULSE_GEOMETRY','cases':12,'carriers':8114,'counts':counts,'maximum_Decimal_vs_table_error_channel_widths':float(max_error),'absolute_error_summary':{'minimum':min(absolute),'median':statistics.median(absolute),'maximum':max(absolute)},'case_counts':case_summaries,'PULSE_GEOMETRY_json_sha256':hashlib.sha256((OUT/'PULSE_GEOMETRY.json').read_bytes()).hexdigest(),'pulse_geometry_csv_sha256':hashlib.sha256((OUT/'pulse_geometry.csv').read_bytes()).hexdigest(),'new_scores':0,'new_draws':0,'qualification':False,'point_geometry_is_not_new_recovery_or_measured_profile':True}
(OUT/'PEER_PULSE_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'PEER_PULSE_AUDIT.md').write_text('# Independent saved-pulse geometry audit\n\nPASS. Independent45-digit Decimal arithmetic selects the original first/last ON endpoint directly as the pulse time, rather than importing the primary first+row*tsamp calculation. It authenticates original records and checks all8114 table entries. Counts:428 full-endpoint localized,8103 within18.5 channel widths at the pulse midpoint,7675 point matches outside full localization. All12 case counts and absolute-error summaries agree. No raw power or detector score was recomputed; a point match is descriptive geometry, not a new recovery decision.\n')
print(json.dumps({'review_status':report['review_status'],'carriers':8114,'counts':counts,'maximum_error':float(max_error)}))
