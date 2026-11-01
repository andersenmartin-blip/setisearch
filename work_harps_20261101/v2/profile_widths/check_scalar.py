"""Separate scalar least-squares reconstruction on first/middle/last order."""
from pathlib import Path
import json,csv,hashlib,datetime
import numpy as np
OUT=Path(__file__).resolve().parent;V2=OUT.parent
rows=list(csv.DictReader((OUT/'ORDER_WIDTHS.csv').open()))
sources=list(dict.fromkeys(r['source_path'] for r in rows));picked=[sources[i] for i in [0,len(sources)//2,len(sources)-1]]
checked=[]
for source in picked:
    wanted=[r for r in rows if r['source_path']==source];d=np.load(V2/source);y=d['native_flux'];w=d['native_wave']
    ref=float(wanted[0]['reference_fwhm_angstrom']);center=ref*115000;x=(w-center)/ref;B=np.column_stack([np.ones(len(y)),x]);side=np.r_[0:8,33:41]
    for row in wanted:
        method=row['method'];best=None;sidecoef=np.linalg.lstsq(B[side],y[side],rcond=None)[0]
        for ratio in np.r_[np.geomspace(.4,10,121),1.]:
            for shift in np.linspace(-1,1,41):
                g=np.exp(-.5*((x-shift)/(ratio/2.354820045))**2)
                if method=='joint_linear':
                    D=np.column_stack([B,g]);c=np.linalg.lstsq(D,y,rcond=None)[0]
                    if c[-1]<0:c=np.r_[np.linalg.lstsq(B,y,rcond=None)[0],0.]
                else:c=np.r_[sidecoef,max(0,float(g@(y-B@sidecoef)/(g@g)))];D=np.column_stack([B,g])
                sse=float(np.sum((y-D@c)**2))
                if best is None or sse<best['sse']:best=dict(width_ratio=float(ratio),shift=float(shift),sse=sse,amplitude=float(c[-1]))
        expected=float(row['sse']);relative=abs(best['sse']-expected)/max(expected,1.)
        assert abs(best['width_ratio']-float(row['width_ratio']))<1e-12
        assert abs(best['shift']-float(row['center_shift_reference_fwhm']))<1e-12
        assert relative<1e-8
        checked.append(dict(review_id=row['review_id'],order=int(row['order']),method=method,source=source,scalar_best=best,saved_sse=expected,relative_sse_difference=relative))
result=dict(status='PASSED',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selection='First/middle/last complete order in immutable64event table, both backgroundmethods.',checks=checked,
    interpretation='Same primaryagent freshprocess using direct scalar3-column least squares, independently structured fromvectorizedprojectedfits; numericalchecknotindependentresearcherreview.',source_sha256=hashlib.sha256((OUT/'ORDER_WIDTHS.csv').read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'SCALAR_CHECK.json').write_text(json.dumps(result,indent=2)+'\n');print('scalar fits agree',len(checked))
