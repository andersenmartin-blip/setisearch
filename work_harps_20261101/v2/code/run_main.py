"""One frozen, prospectively selected extra batch; both algorithms on same data."""
from pathlib import Path
import csv,json,hashlib,sys,time,datetime
BASE=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(BASE/'code'),str(BASE/'v2/code')]
from harps_detector import read_spectrum,analyze_arrays as v1
from profile_detector import analyze_arrays as v2
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def csvout(p,rows):
 fields=sorted({k for r in rows for k in r}) or ['status']
 with p.open('w',newline='') as h:
  wr=csv.DictWriter(h,fieldnames=fields);wr.writeheader()
  for row in rows:wr.writerow({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in row.items()})
def main():
 freeze=json.loads((BASE/'v2/code/FREEZE.json').read_text())
 for name,digest in freeze['source_hashes'].items():assert sha(BASE/name)==digest,name
 sel=json.loads((BASE/'v2/selection/SELECTION_FREEZE.json').read_text())
 assert sha(BASE/'v2/selection/MAIN100.csv')==sel['frozen_selection_hashes']['MAIN100.csv']
 rows=list(csv.DictReader((BASE/'v2/selection/MAIN100.csv').open()))
 manifest={r['dp_id']:r for r in json.loads((BASE/'v2/acquisition/DOWNLOAD_MANIFEST.json').read_text())}
 assert len(rows)==100 and len({r['dp_id'] for r in rows})==100
 checked=[]
 for r in rows:
  m=manifest[r['dp_id']];p=BASE/m['relative_path']
  assert m['header_status']=='PASS_METADATA_ONLY' and all(m['checks'].values())
  assert m['role']=='v2_main_unopened' and sha(p)==m['sha256']
  checked.append((r,m,p))
 validation=json.loads((BASE/'v2/validation/results/SUMMARY.json').read_text())
 assert validation['evaluated_trials']==192
 out=BASE/'v2/production';out.mkdir(parents=True,exist_ok=False);(out/'spectra').mkdir()
 cfg1=json.loads((BASE/'code/DETECTOR_CONFIG.json').read_text());cfg2=json.loads((BASE/'v2/code/CONFIG.json').read_text())
 dump(out/'RUN_INPUTS.json',dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),runner_sha256=sha(Path(__file__)),
  selection_sha256=sha(BASE/'v2/selection/MAIN100.csv'),manifest_sha256=sha(BASE/'v2/acquisition/DOWNLOAD_MANIFEST.json'),
  detector_freeze=freeze,validation_summary=validation,scope='100 extra exposures only; no original-main rerun represented as fresh data.'))
 exposures=[];events1=[];events2=[];start=time.monotonic()
 for r,m,p in checked:
  w,f,meta=read_spectrum(p);assert meta['sha256']==m['sha256']
  rr1,_=v1(w,f,cfg1);rr2,_=v2(w,f,cfg2)
  common=dict(dp_id=r['dp_id'],canonical_target=r['canonical_target'],date_obs=meta['DATE-OBS'],input_sha256=m['sha256'])
  for rr,name in [(rr1,'v1'),(rr2,'v2')]:dump(out/'spectra'/(r['dp_id'].replace(':','_')+'_'+name+'.json'),dict(**common,input=meta,result=rr))
  events1.extend(dict(**common,**e) for e in rr1['all_threshold_runs'])
  events2.extend(dict(**common,**e) for e in rr2['events'])
  exposures.append(dict(**common,exposure_seconds=float(r['t_exptime']),v1_searched=rr1['searched_samples'],v2_searched=rr2['searched_samples'],v1_hits=rr1['preliminary_hit_count'],v2_hits=rr2['preliminary_hit_count'],v2_screened=rr2['screened_events']))
  print(json.dumps(exposures[-1]),flush=True)
 csvout(out/'EXPOSURES.csv',exposures);csvout(out/'V1_ALL_RUNS.csv',events1);csvout(out/'V2_ALL_SCREENED_EVENTS.csv',events2)
 h1=[e for e in events1 if e['status']=='PRELIMINARY_EMISSION_HIT'];h2=[e for e in events2 if e['status']=='PRELIMINARY_PROFILE_HIT']
 csvout(out/'V1_HITS.csv',h1);csvout(out/'V2_HITS.csv',h2)
 csvout(out/'V2_DISPOSITIONS.csv',[dict(**e,origin_status='UNREVIEWED') for e in h2])
 summary=dict(status='COMPLETED',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),exposures=len(exposures),targets=len({r['canonical_target'] for r in rows}),
  exposure_seconds=sum(r['exposure_seconds'] for r in exposures),v1_hits=len(h1),v2_hits=len(h2),v2_screened=len(events2),
  v1_searched_samples=sum(r['v1_searched'] for r in exposures),v2_searched_samples=sum(r['v2_searched'] for r in exposures),wall_seconds=time.monotonic()-start,
  interpretation='All V2 accepted events are UNREVIEWED, not lasers. V1 and V2 have different selection functions. The initial100 and these extra100 give200 unique main exposures, not200 stars.')
 dump(out/'SUMMARY.json',summary);print(json.dumps(summary))
if __name__=='__main__':main()
