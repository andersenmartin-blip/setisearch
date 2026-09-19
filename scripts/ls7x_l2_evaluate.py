#!/usr/bin/env python3
"""Acquire and evaluate the frozen LS7X DEFAULT CHEOPS L2 pilot."""
import gzip, hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import numpy as np
from astropy.io import fits
from seti_repeater.cheops_l2 import SIDE, GUARD, DURATIONS, SCREEN, score_window, cluster_positive

ROOT=Path(__file__).resolve().parents[1]
META=ROOT/'results_ls7x_l2_metadata'
OUT=ROOT/'results_ls7x_l2_pilot'
BASE='https://cheops-webapp-pg.obsuksprd2.unige.ch/'
KEY='CH_PR300024_TG000301_V0300'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(path,value): path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def get_url():
    payload={'fileType':'lightcurves','filters':{'file_key':{'equal':[KEY]}},'aperture':'default'}
    with urlopen(Request(BASE+'download',data=json.dumps(payload).encode(),
                         headers={'Accept':'application/json','User-Agent':'dace-query/3.0.1'}),timeout=45) as r:
        info=json.load(r)
    return BASE+'download/photometry/'+info['key']+'?compressed=false'

def table_dtype(header):
    fields=[]
    for i in range(1,header['TFIELDS']+1):
        count,code=re.fullmatch(r'(\d*)([ADEJI])',header[f'TFORM{i}']).groups()
        n=int(count or '1'); name=header[f'TTYPE{i}']
        if code=='A': fields.append((name,f'S{n}'))
        else:
            typ={'D':'>f8','E':'>f4','J':'>i4','I':'>i2'}[code]
            fields.append((name,typ,(n,)) if n != 1 else (name,typ))
    result=np.dtype(fields); assert result.itemsize == header['NAXIS1']; return result

def robust_diag(values, side, event):
    a=np.asarray(values,float); sf=a[side][np.isfinite(a[side])]; ef=a[event][np.isfinite(a[event])]
    if not len(sf) or not len(ef): return {'available':False}
    med=float(np.median(sf)); mad=float(1.4826*np.median(abs(sf-med))); delta=float(np.mean(ef)-med)
    return {'available':True,'side_median':med,'side_sigma_mad':mad,'event_mean':float(np.mean(ef)),
            'event_minus_side_median':delta,'standardized_delta':(delta/mad if mad>0 else None)}

def candidate_diagnostics(table,row):
    start=row['start']; d=row['duration']
    side=np.r_[np.arange(start-GUARD-SIDE,start-GUARD),
               np.arange(start+d+GUARD,start+d+GUARD+SIDE)]
    ev=np.arange(start,start+d)
    cx=robust_diag(table['CENTROID_X'],side,ev); cy=robust_diag(table['CENTROID_Y'],side,ev)
    centroid=None
    if cx['available'] and cy['available']:
        centroid=float(np.hypot(cx['event_minus_side_median'],cy['event_minus_side_median']))
    baseline=row['baseline_event_sum_electrons']/d; mean_excess=row['excess_electrons']/d
    return {'background':robust_diag(table['BACKGROUND'],side,ev),
            'smearing':robust_diag(table['SMEARING_LC'],side,ev),
            'roll_angle':robust_diag(table['ROLL_ANGLE'],side,ev),
            'contamination':robust_diag(table['CONTA_LC'],side,ev),
            'centroid_x':cx,'centroid_y':cy,'centroid_displacement_pixels':centroid,
            'mean_excess_electrons':mean_excess,
            'fractional_mean_excess':(mean_excess/baseline if baseline != 0 else None)}

def main():
    assert not OUT.exists(),'refuse completed pilot overwrite'
    meta=json.loads((META/'summary.json').read_text())
    assert meta['table_data_bytes_acquired']==0 and meta['science_values_inspected']==0
    h=fits.Header.fromstring((META/'lightcurve_header.bin').read_bytes().decode('ascii'),sep='')
    start=meta['table_data_start']; count=meta['table_bytes_declared']
    assert count == h['NAXIS1']*h['NAXIS2'] == 59616
    url=get_url()
    with urlopen(Request(url,headers={'Range':f'bytes={start}-{start+count-1}','If-Match':meta['etag'],
                                      'Accept':'application/octet-stream','Accept-Encoding':'identity'}),timeout=45) as r:
        assert r.status==206
        assert r.headers['Content-Range']==f'bytes {start}-{start+count-1}/{meta["total_file_bytes"]}'
        assert r.headers.get('ETag')==meta['etag']
        assert int(r.headers['Content-Length'])==count
        assert r.headers.get('Content-Disposition')==meta['content_disposition']
        raw=r.read(count+1); assert len(raw)==count
        receipt={'start':start,'count':count,'sha256':sha(raw),'status':r.status,'etag':r.headers.get('ETag'),
                 'content_range':r.headers.get('Content-Range'),
                 'content_disposition':r.headers.get('Content-Disposition'),
                 'retrieved_utc':datetime.now(timezone.utc).isoformat()}
    OUT.mkdir(); (OUT/'lightcurve_table.bin').write_bytes(raw)
    table=np.frombuffer(raw,dtype=table_dtype(h),count=h['NAXIS2'])
    bjd=table['BJD_TIME'].astype(float); flux=table['FLUX'].astype(float)
    err=table['FLUXERR'].astype(float); status=table['STATUS'].astype(np.int64); event=table['EVENT'].astype(np.int64)
    cadence=float(meta['keywords']['TEXPTIME'])
    rows=[]
    for d in DURATIONS:
        for i in range(len(table)-d+1):
            row=score_window(bjd,flux,err,status,event,i,d,cadence)
            if row is not None: rows.append(row)
    rows=sorted(rows,key=lambda r:(r['duration'],r['start']))
    clusters=cluster_positive(rows,SCREEN); representatives=[]
    for n,c in enumerate(clusters):
        rep=dict(c['representative']); rep['cluster_id']=n
        rep['cluster_members']=[{'start':x['start'],'duration':x['duration'],'score':x['score']} for x in c['members']]
        rep['diagnostics']=candidate_diagnostics(table,rep); representatives.append(rep)
    ledger=''.join(json.dumps(r,sort_keys=True,allow_nan=False)+'\n' for r in rows).encode()
    (OUT/'ledger.jsonl.gz').write_bytes(gzip.compress(ledger,mtime=0))
    save(OUT/'candidates.json',{'threshold':SCREEN,'clusters':representatives})
    save(OUT/'source.json',{'file_key':KEY,'filename':meta['content_disposition'],'etag':meta['etag'],
         'total_file_bytes':meta['total_file_bytes'],'table_receipt':receipt,
         'metadata_freeze':'44e40cfeaebf0289a46ee62bcfd385070411b377',
         'evaluation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
         'other_apertures_opened':False})
    duration={}
    for d in DURATIONS:
        rr=[x for x in rows if x['duration']==d]
        duration[str(d)]={'duration_seconds':d*cadence,'eligible_windows':len(rr),
          'positive_screens':sum(x['score']>=SCREEN for x in rr),
          'negative_controls':sum(x['score']<=-SCREEN for x in rr),
          'maximum_score':max((x['score'] for x in rr),default=None),
          'minimum_score':min((x['score'] for x in rr),default=None)}
    valid=(np.isfinite(bjd)&np.isfinite(flux)&np.isfinite(err)&(err>0)&(status==0))
    union=set()
    for x in rows: union.update(x['event_indices'])
    summary={'stage':'LS7X_CHEOPS_L2_NATIVE_PILOT','status':'COMPLETE_UNAUDITED','file_key':KEY,
      'aperture':'DEFAULT','rows':len(table),'status_zero_finite_rows':int(valid.sum()),
      'cadence_seconds':cadence,'sideband_rows_each_side':SIDE,'guard_rows':GUARD,
      'screen_threshold':SCREEN,'duration_results':duration,'eligible_ledger_rows':len(rows),
      'unique_event_rows_in_eligible_windows':len(union),'eligible_event_row_union_seconds':len(union)*cadence,
      'positive_screen_clusters':len(representatives),
      'highest_positive_representative_score':max((x['score'] for x in representatives),default=None),
      'native_result_interpretation':'L2 excursion screening only; not calibrated false-alarm probability or artificial-source classification',
      'other_apertures_evaluated':False,'image_followup_performed':False,'physical_laser_sensitivity_claimed':False}
    save(OUT/'summary.json',summary)
    lines=['# LS7X CHEOPS DEFAULT L2 native short-transient pilot','',
      'Prospectively frozen before any L2 flux row was opened. DEFAULT aperture only.','',
      f'- Rows: **{len(table)}**',f'- Finite STATUS=0 rows: **{int(valid.sum())}**',
      f'- Eligible scored windows: **{len(rows)}**',f'- Positive raw screens: **{sum(x["score"]>=SCREEN for x in rows)}**',
      f'- Positive clusters: **{len(representatives)}**',f'- Negative controls: **{sum(x["score"]<=-SCREEN for x in rows)}**','']
    if representatives:
        lines += ['## Positive clusters','','| Cluster | Start | Duration | Score | EVENT OR | Fractional mean excess |',
                  '|---:|---:|---:|---:|---:|---:|']
        for x in representatives:
            frac=x['diagnostics']['fractional_mean_excess']
            lines.append(f'| {x["cluster_id"]} | {x["start"]} | {x["duration"]} | {x["score"]:.6f} | {x["event_or"]} | {frac if frac is not None else "N/A"} |')
        lines += ['','Each entry is an L2 excursion requiring instrumental/image follow-up; none is classified as artificial or astrophysical by this score alone.']
    else:
        lines += ['## Primary result','','No positive window crossed the predeclared threshold.',
                  'This is a single-visit pilot null, not an occurrence-rate or physical-sensitivity limit.']
    lines += ['','Independent audit: audit.json. Full ledger: ledger.jsonl.gz.','']
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    paths=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS')
    (OUT/'SHA256SUMS').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in paths))
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
