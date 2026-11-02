"""Describe all fixed diagnostics; robust values are never new acceptance gates."""
from pathlib import Path
import json,csv,statistics,collections,hashlib,datetime
OUT=Path(__file__).resolve().parent;PRIOR=OUT.parent/'mapping_followup_20261102'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,d):(OUT/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def median(v):return statistics.median(v) if v else None
def csvsave(n,rows):
 with (OUT/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 queue=read(OUT/'EXPOSURE_QUEUE.json');execution=read(OUT/'EXECUTION_SUMMARY.json')
 assert execution['status']=='COMPLETE_DIAGNOSTIC_ONLY_NO_RECLASSIFICATION' and execution['exposures']==20
 prior_rows=list(csv.DictReader((PRIOR/'ORDER_LIMITATIONS.csv').open()))
 targets={r['dp_id']:r['target'] for r in prior_rows}
 limits={(r['dp_id'],int(r['order'])):r for r in prior_rows}
 input_paths=[PRIOR/'RAW_REFERENCE_SUMMARY.json']+[OUT/r['summary_path'] for r in execution['runs']]
 inputs={str(p.relative_to(OUT.parents[3])):sha(p) for p in input_paths};summaries=[read(p) for p in input_paths]
 assert len(summaries)==21 and len({s['dp_id'] for s in summaries})==21
 order_rows=[];selected=[]
 for s in summaries:
  for o in s['order_summaries']:
   limit=limits.get((s['dp_id'],o['order']))
   row=dict(dp_id=s['dp_id'],target=targets[s['dp_id']],order=o['order'],selected_M_covering_order=bool(limit),
    prior_reference_failed=bool(limit and limit['reference_mapping_supported']=='False'),
    measured_windows=o['measured_windows'],original_pearson_median=o['original_pearson_median'],spearman_median=o['spearman_median'],
    winsorized_pearson_median=o['winsorized_pearson_median'],subwindow_pearson_median=o['subwindow_pearson_median'],
    valid_subwindows=o['valid_64pixel_subwindows'],spearman_minus_original=o['spearman_median']-o['original_pearson_median'] if o['spearman_median'] is not None and o['original_pearson_median'] is not None else None,
    winsorized_minus_original=o['winsorized_pearson_median']-o['original_pearson_median'] if o['winsorized_pearson_median'] is not None and o['original_pearson_median'] is not None else None,
    subwindow_minus_original=o['subwindow_pearson_median']-o['original_pearson_median'] if o['subwindow_pearson_median'] is not None and o['original_pearson_median'] is not None else None)
   order_rows.append(row)
   if limit:
    assert abs(row['original_pearson_median']-float(limit['median_correlation']))<1e-12
    selected.append(row)
 assert len(order_rows)==1512 and len(selected)==43
 failed=[r for r in selected if r['prior_reference_failed']];assert len(failed)==28
 def describe(rs):
  return dict(unique_exposure_orders=len(rs),exposures=len({r['dp_id'] for r in rs}),
   original_pearson_median=median([r['original_pearson_median'] for r in rs]),spearman_median=median([r['spearman_median'] for r in rs]),
   winsorized_pearson_median=median([r['winsorized_pearson_median'] for r in rs]),subwindow_pearson_median=median([r['subwindow_pearson_median'] for r in rs]),
   median_spearman_change=median([r['spearman_minus_original'] for r in rs]),median_winsorized_change=median([r['winsorized_minus_original'] for r in rs]),median_subwindow_change=median([r['subwindow_minus_original'] for r in rs]),
   descriptive_only_count_spearman_above_0p8=sum(r['spearman_median']>.8 for r in rs),
   descriptive_only_count_winsorized_above_0p8=sum(r['winsorized_pearson_median']>.8 for r in rs),
   descriptive_only_count_subwindow_above_0p8=sum(r['subwindow_pearson_median']>.8 for r in rs))
 grouped={str(order):describe([r for r in failed if r['order']==order]) for order in sorted({r['order'] for r in failed})}
 summary=dict(schema='SETI_MAPPING_21_EXPOSURE_DIAGNOSTIC_V1',status='COMPLETE_DESCRIPTIVE_ALL35_REMAIN_M',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  completed_new_exposures=20,completed_prior_exposures=1,total_unique_exposures=21,total_mapping_limited_records=35,total_native_order_diagnostics=1512,
  total_reference_windows=7560,measured_reference_windows=sum(s['measured_windows'] for s in summaries),unavailable_reference_windows=sum(s['unavailable_reference_windows'] for s in summaries),
  verified_previous_reference_windows=sum(s['original_pearson_windows_verified'] for s in summaries),
  selected_unique_covering_exposure_orders=43,previous_failed_reference_exposure_orders=28,
  failed_reference_diagnostics=describe(failed),failed_by_order=grouped,
  classification_changes=0,observing_time_added_hours=0,new_detections=0,qualified_laser_candidates_added=0,
  interpretation='Robust and local correlations characterize sensitivity of the existing Pearson limitation. Counts above0.8 are descriptive comparisons, not applications of a new acceptance rule.',
  limitations=['Posthoc M-selected21-exposure sample; neither a new search nor an independent mapping calibration.',
   'All selected M records retain original edge and reference failures, even where robust metrics exceed0.8.',
   'Same-exposure72-order comparisons share instrumental conditions and are not independent telescope observations.',
   'Changed rank/clipped/local correlation does not identify cosmic rays, pipeline correction, stellar/terrestrial origin, or trace misregistration.'],
  input_summary_sha256=inputs)
 csvsave('ALL_1512_ORDER_DIAGNOSTICS.csv',order_rows);csvsave('SELECTED_43_ORDER_DIAGNOSTICS.csv',selected);csvsave('FAILED_28_ORDER_DIAGNOSTICS.csv',failed)
 write('SUMMARY.json',summary)
 print(json.dumps({k:v for k,v in summary.items() if k not in ['failed_by_order','input_summary_sha256']},indent=2))
if __name__=='__main__':main()
