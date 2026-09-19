#!/usr/bin/env python3
"""Independent struct/scalar audit of frozen LS8A L2 transfer."""
import gzip,json,math,struct
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'results_ls8a_l2_transfer'; META=ROOT/'results_ls8a_l2_metadata'
SIDE=12; GUARD=2; SCREEN=8.5; DURATIONS=(1,2,3)
ROW=struct.Struct('>26sddddii7d4f'); assert ROW.size==138

def parse(raw):
    r=list(ROW.iter_unpack(raw))
    return {'bjd':np.array([x[2] for x in r],float),'flux':np.array([x[3] for x in r],float),
      'err':np.array([x[4] for x in r],float),'status':np.array([x[5] for x in r],np.int64),
      'event':np.array([x[6] for x in r],np.int64)}

def score(d,start,n,cad):
    lo=start-GUARD-SIDE; hi=start+n+GUARD+SIDE
    if lo<0 or hi>len(d['flux']): return None
    ctx=np.arange(lo,hi)
    if not(np.isfinite(d['bjd'][ctx]).all() and np.isfinite(d['flux'][ctx]).all() and
      np.isfinite(d['err'][ctx]).all() and (d['err'][ctx]>0).all() and (d['status'][ctx]==0).all()): return None
    gaps=np.diff(d['bjd'][ctx])*86400.
    if not((gaps>=.5*cad)&(gaps<=1.5*cad)).all(): return None
    side=np.r_[np.arange(start-GUARD-SIDE,start-GUARD),np.arange(start+n+GUARD,start+n+GUARD+SIDE)]
    ev=np.arange(start,start+n); t0=float(np.mean(d['bjd'][ev]))
    xs=(d['bjd'][side]-t0)*86400.; xe=(d['bjd'][ev]-t0)*86400.
    sx=float(xs.sum()); sxx=float(xs@xs); nn=len(xs); sy=float(d['flux'][side].sum()); sxy=float(xs@d['flux'][side])
    det=nn*sxx-sx*sx; b0=(sy*sxx-sx*sxy)/det; b1=(nn*sxy-sx*sy)/det
    res=d['flux'][side]-(b0+b1*xs); med=float(np.median(res))
    sig=max(1.4826*float(np.median(abs(res-med))),float(np.median(d['err'][side])),
      1e-12*abs(float(np.median(d['flux'][side]))),1e-12)
    excess=float(np.sum(d['flux'][ev]-(b0+b1*xe)))
    x0=float(n); x1=float(xe.sum()); i00=sxx/det; i01=-sx/det; i11=nn/det
    lev=x0*x0*i00+2*x0*x1*i01+x1*x1*i11; den=sig*math.sqrt(n+lev)
    return {'score':excess/den,'excess':excess,'sigma':sig,'denom':den,
      'event_or':int(np.bitwise_or.reduce(d['event'][ev]))}

def clusters(rows):
    x=sorted([r for r in rows if r['score']>=SCREEN],key=lambda r:(r['start'],r['start']+r['duration']))
    g=[]
    for r in x:
        end=r['start']+r['duration']-1
        if not g or r['start']>g[-1]['end']+1: g.append({'end':end,'m':[r]})
        else: g[-1]['end']=max(g[-1]['end'],end); g[-1]['m'].append(r)
    return [min(a['m'],key=lambda r:(-r['score'],r['duration'],r['start'])) for a in g]

def main():
    m=json.loads((META/'summary.json').read_text()); raw=(OUT/'lightcurve_table.bin').read_bytes()
    assert len(raw)==m['table_bytes_declared'] and len(raw)%ROW.size==0
    d=parse(raw); cad=float(m['keywords']['TEXPTIME']); rebuilt=[]
    for n in DURATIONS:
      for i in range(len(d['flux'])-n+1):
        x=score(d,i,n,cad)
        if x is not None: rebuilt.append({'start':i,'duration':n,**x})
    saved=[json.loads(x) for x in gzip.decompress((OUT/'ledger.jsonl.gz').read_bytes()).decode().splitlines()]
    assert len(rebuilt)==len(saved); lookup={(x['start'],x['duration']):x for x in saved}
    md={'score':0.,'excess':0.,'sigma':0.,'denom':0.}; comp=0
    for r in rebuilt:
      s=lookup[(r['start'],r['duration'])]
      for a,b,k in [(r['score'],s['score'],'score'),(r['excess'],s['excess_electrons'],'excess'),
                    (r['sigma'],s['sigma_electrons'],'sigma'),(r['denom'],s['denominator_electrons'],'denom')]:
        md[k]=max(md[k],abs(a-b)); assert math.isclose(a,b,rel_tol=2e-8,abs_tol=2e-10),(k,a,b); comp+=1
      assert r['event_or']==s['event_or']; comp+=1
    rc=clusters(rebuilt); cand=json.loads((OUT/'candidates.json').read_text())['clusters']
    assert [(x['start'],x['duration']) for x in rc]==[(x['start'],x['duration']) for x in cand]
    sm=json.loads((OUT/'summary.json').read_text()); assert sm['eligible_ledger_rows']==len(rebuilt)
    result={'status':'PASS','raw_rows':len(d['flux']),'ledger_rows':len(rebuilt),
      'numeric_comparisons':comp,'maximum_absolute_differences':md,
      'positive_cluster_representatives':len(rc),
      'method':'independent big-endian struct rows and explicit scalar normal equations'}
    (OUT/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    sm['status']='COMPLETE_AUDITED'; (OUT/'summary.json').write_text(json.dumps(sm,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
