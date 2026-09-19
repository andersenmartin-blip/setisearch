#!/usr/bin/env python3
"""Independent struct/scalar audit of frozen LS7X L2 pilot."""
import gzip, json, math, struct
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'results_ls7x_l2_pilot'; META=ROOT/'results_ls7x_l2_metadata'
SIDE=12; GUARD=2; SCREEN=8.5; DURATIONS=(1,2,3)
ROW=struct.Struct('>26sddddii7d4f')
assert ROW.size==138

def parse(raw):
    rows=list(ROW.iter_unpack(raw))
    return {'bjd':np.array([r[2] for r in rows],float),'flux':np.array([r[3] for r in rows],float),
      'err':np.array([r[4] for r in rows],float),'status':np.array([r[5] for r in rows],np.int64),
      'event':np.array([r[6] for r in rows],np.int64)}

def score(d,start,duration,cadence):
    lo=start-GUARD-SIDE; hi=start+duration+GUARD+SIDE
    if lo<0 or hi>len(d['flux']): return None
    ctx=np.arange(lo,hi)
    if not (np.isfinite(d['bjd'][ctx]).all() and np.isfinite(d['flux'][ctx]).all()
            and np.isfinite(d['err'][ctx]).all() and (d['err'][ctx]>0).all() and (d['status'][ctx]==0).all()): return None
    gap=np.diff(d['bjd'][ctx])*86400.
    if not ((gap>=.5*cadence)&(gap<=1.5*cadence)).all(): return None
    side=np.r_[np.arange(start-GUARD-SIDE,start-GUARD),np.arange(start+duration+GUARD,start+duration+GUARD+SIDE)]
    ev=np.arange(start,start+duration); t0=float(np.mean(d['bjd'][ev]))
    xs=(d['bjd'][side]-t0)*86400.; xe=(d['bjd'][ev]-t0)*86400.
    sx=float(xs.sum()); sxx=float(np.dot(xs,xs)); n=len(xs); sy=float(d['flux'][side].sum()); sxy=float(np.dot(xs,d['flux'][side]))
    det=n*sxx-sx*sx; b0=(sy*sxx-sx*sxy)/det; b1=(n*sxy-sx*sy)/det
    resid=d['flux'][side]-(b0+b1*xs); med=float(np.median(resid))
    sigma=max(1.4826*float(np.median(abs(resid-med))),float(np.median(d['err'][side])),
              1e-12*abs(float(np.median(d['flux'][side]))),1e-12)
    pred=b0+b1*xe; excess=float(np.sum(d['flux'][ev]-pred))
    x0=float(duration); x1=float(xe.sum()); inv00=sxx/det; inv01=-sx/det; inv11=n/det
    lev=x0*x0*inv00+2*x0*x1*inv01+x1*x1*inv11; denom=sigma*math.sqrt(duration+lev)
    return {'score':excess/denom,'excess':excess,'sigma':sigma,'denom':denom,
            'event_or':int(np.bitwise_or.reduce(d['event'][ev]))}

def clusters(rows):
    s=sorted([r for r in rows if r['score']>=SCREEN],key=lambda r:(r['start'],r['start']+r['duration']))
    out=[]
    for r in s:
        end=r['start']+r['duration']-1
        if not out or r['start']>out[-1]['max_end']+1: out.append({'max_end':end,'m':[r]})
        else: out[-1]['max_end']=max(out[-1]['max_end'],end); out[-1]['m'].append(r)
    return [min(c['m'],key=lambda r:(-r['score'],r['duration'],r['start'])) for c in out]

def main():
    raw=(OUT/'lightcurve_table.bin').read_bytes(); assert len(raw)==59616 and len(raw)%ROW.size==0
    d=parse(raw); cadence=float(json.loads((META/'summary.json').read_text())['keywords']['TEXPTIME'])
    rebuilt=[]
    for duration in DURATIONS:
        for start in range(len(d['flux'])-duration+1):
            x=score(d,start,duration,cadence)
            if x is not None: rebuilt.append({'start':start,'duration':duration,**x})
    saved=[json.loads(x) for x in gzip.decompress((OUT/'ledger.jsonl.gz').read_bytes()).decode().splitlines()]
    assert len(rebuilt)==len(saved); lookup={(x['start'],x['duration']):x for x in saved}
    maxdiff={'score':0.,'excess':0.,'sigma':0.,'denom':0.}; comparisons=0
    for r in rebuilt:
        s=lookup[(r['start'],r['duration'])]
        for a,b,key in [(r['score'],s['score'],'score'),(r['excess'],s['excess_electrons'],'excess'),
                        (r['sigma'],s['sigma_electrons'],'sigma'),(r['denom'],s['denominator_electrons'],'denom')]:
            diff=abs(a-b); maxdiff[key]=max(maxdiff[key],diff)
            assert math.isclose(a,b,rel_tol=2e-10,abs_tol=2e-8),(key,a,b); comparisons+=1
        assert r['event_or']==s['event_or']; comparisons+=1
    rc=clusters(rebuilt); cand=json.loads((OUT/'candidates.json').read_text())['clusters']
    assert [(x['start'],x['duration']) for x in rc]==[(x['start'],x['duration']) for x in cand]
    summary=json.loads((OUT/'summary.json').read_text()); assert summary['eligible_ledger_rows']==len(rebuilt)
    result={'status':'PASS','raw_rows':len(d['flux']),'ledger_rows':len(rebuilt),'numeric_comparisons':comparisons,
            'maximum_absolute_differences':maxdiff,'positive_cluster_representatives':len(rc),
            'method':'independent big-endian struct rows and explicit scalar two-parameter normal equations'}
    (OUT/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    summary['status']='COMPLETE_AUDITED'; (OUT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
