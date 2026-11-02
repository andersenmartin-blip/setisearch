"""Independent aggregate reconciliation from frozen per-exposure summaries."""
from pathlib import Path
import csv,json,hashlib,statistics,datetime,collections
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];PRIOR=OUT.parent/'mapping_followup_20261102'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rows(p):return list(csv.DictReader(p.open()))
def main():
 summary=read(OUT/'SUMMARY.json');execution=read(OUT/'EXECUTION_SUMMARY.json');limits=rows(PRIOR/'ORDER_LIMITATIONS.csv');limit_by_key={(r['dp_id'],int(r['order'])):r for r in limits}
 inputs=[PRIOR/'RAW_REFERENCE_SUMMARY.json']+[OUT/r['summary_path'] for r in execution['runs']];summaries=[read(p) for p in inputs]
 source_hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs};assert source_hashes==summary['input_summary_sha256']
 expected={};checks=[]
 def check(name,ok):checks.append(dict(name=name,pass_=bool(ok)))
 for s in summaries:
  for o in s['order_summaries']:
   key=s['dp_id'],o['order'];assert key not in expected;expected[key]=o
 table=rows(OUT/'ALL_1512_ORDER_DIAGNOSTICS.csv');selected=rows(OUT/'SELECTED_43_ORDER_DIAGNOSTICS.csv');failed=rows(OUT/'FAILED_28_ORDER_DIAGNOSTICS.csv')
 check('full_order_coverage',len(expected)==len(table)==1512 and {(r['dp_id'],int(r['order'])) for r in table}==set(expected))
 correct=True
 for r in table:
  key=r['dp_id'],int(r['order']);o=expected[key];limit=limit_by_key.get(key)
  correct &= r['selected_M_covering_order']==str(bool(limit)) and r['prior_reference_failed']==str(bool(limit and limit['reference_mapping_supported']=='False'))
  for metric in ['original_pearson_median','spearman_median','winsorized_pearson_median','subwindow_pearson_median']:
   correct &= (r[metric]=='' and o[metric] is None) or (r[metric]!='' and abs(float(r[metric])-o[metric])<1e-14)
  correct &= int(r['measured_windows'])==o['measured_windows'] and int(r['valid_subwindows'])==o['valid_64pixel_subwindows']
  for field,metric in [('spearman_minus_original','spearman_median'),('winsorized_minus_original','winsorized_pearson_median'),('subwindow_minus_original','subwindow_pearson_median')]:
   delta=o[metric]-o['original_pearson_median'] if o[metric] is not None and o['original_pearson_median'] is not None else None
   correct &= (r[field]=='' and delta is None) or (r[field]!='' and abs(float(r[field])-delta)<1e-14)
 check('every_metric_and_delta_matches_per_exposure_summary',correct)
 check('selected_and_failed_subsets_exact',selected==[r for r in table if r['selected_M_covering_order']=='True'] and failed==[r for r in selected if r['prior_reference_failed']=='True'] and len(selected)==43 and len(failed)==28)
 def stats(rs):
  d={'unique_exposure_orders':len(rs),'exposures':len({r['dp_id'] for r in rs})}
  for field in ['original_pearson_median','spearman_median','winsorized_pearson_median','subwindow_pearson_median']:d[field]=statistics.median(float(r[field]) for r in rs)
  for field,source in [('median_spearman_change','spearman_minus_original'),('median_winsorized_change','winsorized_minus_original'),('median_subwindow_change','subwindow_minus_original')]:d[field]=statistics.median(float(r[source]) for r in rs)
  for name,col in [('spearman','spearman_median'),('winsorized','winsorized_pearson_median'),('subwindow','subwindow_pearson_median')]:d['descriptive_only_count_'+name+'_above_0p8']=sum(float(r[col])>.8 for r in rs)
  return d
 check('failed28_summary_exact',stats(failed)==summary['failed_reference_diagnostics'])
 check('every_order_group_exact',{str(o):stats([r for r in failed if int(r['order'])==o]) for o in sorted({int(r['order']) for r in failed})}==summary['failed_by_order'])
 check('coverage_counts_exact',summary['total_unique_exposures']==len(summaries)==21 and summary['total_native_order_diagnostics']==len(expected)==1512 and summary['total_reference_windows']==7560 and sum(s['measured_windows'] for s in summaries)==summary['measured_reference_windows']==7517 and sum(s['unavailable_reference_windows'] for s in summaries)==summary['unavailable_reference_windows']==43 and sum(s['original_pearson_windows_verified'] for s in summaries)==summary['verified_previous_reference_windows']==650)
 check('no_origin_or_exposure_inflation',all(summary[k]==0 for k in ['classification_changes','observing_time_added_hours','new_detections','qualified_laser_candidates_added']) and summary['total_mapping_limited_records']==35)
 output_paths=[OUT/n for n in ['SUMMARY.json','ALL_1512_ORDER_DIAGNOSTICS.csv','SELECTED_43_ORDER_DIAGNOSTICS.csv','FAILED_28_ORDER_DIAGNOSTICS.csv']]
 result={'schema':'SETI_MAPPING_REMAINING_AGGREGATE_AUDIT_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if all(c['pass_'] for c in checks) else 'FAIL','checks_passed':sum(c['pass_'] for c in checks),'checks_total':len(checks),'checks':[{('pass' if k=='pass_' else k):v for k,v in c.items()} for c in checks],'coverage':{'exposures':21,'all_order_rows':1512,'selected_order_rows':43,'failed_order_rows':28,'reference_windows':7560,'measured_windows':7517,'unavailable_windows':43,'prior_reference_windows':650},'output_sha256':{str(p.relative_to(OUT)):sha(p) for p in output_paths},'auditor_script_sha256':sha(Path(__file__)),'limitations':['Aggregation audit; pixel-level reconstruction is recorded separately in NUMERICAL_AUDIT.json and the prior exposure audit.','Counts above0.8 for alternate metrics remain descriptive and do not alter original mapping gates.']}
 (OUT/'AGGREGATE_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['checks_passed'],result['checks_total'])
if __name__=='__main__':main()
