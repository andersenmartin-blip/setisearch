#!/usr/bin/env python3
"""Evaluate frozen LS8A held-out DEFAULT CHEOPS L2 transfer."""
import gzip, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import numpy as np
from astropy.io import fits
from seti_repeater.cheops_l2 import SIDE, GUARD, DURATIONS, SCREEN, score_window, cluster_positive

ROOT=Path(__file__).resolve().parents[1]
META=ROOT/'results_ls8a_l2_metadata'; OUT=ROOT/'results_ls8a_l2_transfer'
BASE='https://cheops-webapp-pg.obsuksprd2.unige.ch/'
KEY='CH_PR100006_TG000301_V0300'

def sha(b): return hashlib.sha256(b).hexdigest()
def save(p,x): p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')

def get_url():
    payload={'fileType':'lightcurves','filters':{'file_key':{'equal':[KEY]}},'aperture':'default'}
    with urlopen(Request(BASE+'download',data=json.dumps(payload).encode(),
      headers={'Accept':'application/json','User-Agent':'dace-query/3.0.1'}),timeout=45) as r:
        info=json.load(r)
    assert isinstance(info.get('key'),str) and info['key']
    return BASE+'download/photometry/'+info['key']+'?compressed=false'

def dtype(h):
    fs=[]
    for i in range(1,h['TFIELDS']+1):
        n,c=re.fullmatch(r'(\d*)([ADEJI])',h[f'TFORM{i}']).groups(); n=int(n or '1')
        name=h[f'TTYPE{i}']
        if c=='A': fs.append((name,f'S{n}'))
        else:
            typ={'D':'>f8','E':'>f4','J':'>i4','I':'>i2'}[c]
            fs.append((name,typ,(n,)) if n!=1 else (name,typ))
    d=np.dtype(fs); assert d.itemsize==h['NAXIS1']; return d

def main():
    assert not OUT.exists(),'refuse completed transfer overwrite'
    m=json.loads((META/'summary.json').read_text())
    assert m['table_data_bytes_acquired']==0 and m['candidate_decisions']==0
    assert m['file_key']==KEY and m['selection']['aperture']=='default'
    h=fits.Header.fromstring((META/'lightcurve_header.bin').read_bytes().decode('ascii'),sep='')
    start=m['table_data_start']; count=m['table_bytes_declared']
    assert count==h['NAXIS1']*h['NAXIS2']==162564
    url=get_url()
    with urlopen(Request(url,headers={'Range':f'bytes={start}-{start+count-1}','If-Match':m['etag'],
      'Accept':'application/octet-stream','Accept-Encoding':'identity'}),timeout=45) as r:
        assert r.status==206
        assert r.headers['Content-Range']==f'bytes {start}-{start+count-1}/{m["total_file_bytes"]}'
        assert r.headers.get('ETag')==m['etag']
        assert int(r.headers['Content-Length'])==count
        assert r.headers.get('Content-Disposition')==m['content_disposition']
        raw=r.read(count+1); assert len(raw)==count
        receipt={'start':start,'count':count,'sha256':sha(raw),'status':r.status,
          'etag':r.headers.get('ETag'),'content_range':r.headers.get('Content-Range'),
          'content_disposition':r.headers.get('Content-Disposition'),
          'retrieved_utc':datetime.now(timezone.utc).isoformat()}
    OUT.mkdir(); (OUT/'lightcurve_table.bin').write_bytes(raw)
    t=np.frombuffer(raw,dtype=dtype(h),count=h['NAXIS2'])
    bjd=t['BJD_TIME'].astype(float); flux=t['FLUX'].astype(float); err=t['FLUXERR'].astype(float)
    status=t['STATUS'].astype(np.int64); event=t['EVENT'].astype(np.int64)
    cadence=float(m['keywords']['TEXPTIME'])
    rows=[]
    for d in DURATIONS:
        for i in range(len(t)-d+1):
            x=score_window(bjd,flux,err,status,event,i,d,cadence)
            if x is not None: rows.append(x)
    rows=sorted(rows,key=lambda x:(x['duration'],x['start']))
    clusters=cluster_positive(rows,SCREEN)
    reps=[]
    for n,c in enumerate(clusters):
        x=dict(c['representative']); x['cluster_id']=n
        x['cluster_members']=[{'start':z['start'],'duration':z['duration'],'score':z['score']} for z in c['members']]
        reps.append(x)
    led=''.join(json.dumps(x,sort_keys=True,allow_nan=False)+'\n' for x in rows).encode()
    (OUT/'ledger.jsonl.gz').write_bytes(gzip.compress(led,mtime=0))
    save(OUT/'candidates.json',{'threshold':SCREEN,'clusters':reps})
    save(OUT/'source.json',{'file_key':KEY,'filename':m['content_disposition'],'etag':m['etag'],
      'total_file_bytes':m['total_file_bytes'],'table_receipt':receipt,'other_apertures_opened':False})
    dr={}
    for d in DURATIONS:
        rr=[x for x in rows if x['duration']==d]
        dr[str(d)]={'duration_seconds':d*cadence,'eligible_windows':len(rr),
          'positive_screens':sum(x['score']>=SCREEN for x in rr),
          'negative_controls':sum(x['score']<=-SCREEN for x in rr),
          'maximum_score':max((x['score'] for x in rr),default=None),
          'minimum_score':min((x['score'] for x in rr),default=None)}
    valid=np.isfinite(bjd)&np.isfinite(flux)&np.isfinite(err)&(err>0)&(status==0)
    union=set()
    for x in rows: union.update(x['event_indices'])
    summary={'stage':'LS8A_HELDOUT_L2_TRANSFER','status':'COMPLETE_UNAUDITED','file_key':KEY,
      'selection_rule':m['selection_rule'],'aperture':'DEFAULT','rows':len(t),
      'status_zero_finite_rows':int(valid.sum()),'cadence_seconds':cadence,
      'sideband_rows_each_side':SIDE,'guard_rows':GUARD,'screen_threshold':SCREEN,
      'duration_results':dr,'eligible_ledger_rows':len(rows),
      'unique_event_rows_in_eligible_windows':len(union),
      'eligible_event_row_union_seconds':len(union)*cadence,
      'positive_screen_clusters':len(reps),
      'negative_control_screens':sum(x['score']<=-SCREEN for x in rows),
      'highest_positive_representative_score':max((x['score'] for x in reps),default=None),
      'other_apertures_evaluated':False,'image_followup_performed':False,
      'interpretation':'held-out transfer of frozen LS7X L2 screen; not detector qualification or calibrated false-alarm probability'}
    save(OUT/'summary.json',summary)
    lines=['# LS8A held-out CHEOPS DEFAULT L2 transfer','',
      'Prospectively selected and frozen before table bytes were opened. LS7X cadence-unit screen unchanged.','',
      f'- Rows: **{len(t)}**',f'- Finite STATUS=0 rows: **{int(valid.sum())}**',
      f'- Cadence: **{cadence:.6f} s**',f'- Eligible windows: **{len(rows)}**',
      f'- Positive clusters: **{len(reps)}**',f'- Negative controls: **{summary["negative_control_screens"]}**','']
    if reps:
        lines += ['## Positive cluster representatives','','| Cluster | Start | Duration rows | Duration s | Score | EVENT OR |',
          '|---:|---:|---:|---:|---:|---:|']
        for x in reps: lines.append(f'| {x["cluster_id"]} | {x["start"]} | {x["duration"]} | {x["duration"]*cadence:.3f} | {x["score"]:.6f} | {x["event_or"]} |')
        lines += ['','Each is an L2 excursion only; any image follow-up requires a separate predeclared protocol.']
    else:
        lines += ['## Result','','No positive cluster crossed the unchanged +8.5 screen.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
