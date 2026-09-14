#!/usr/bin/env python3
"""Independent original-MATLAB/SciPy/Simpson audit, no producer import."""
import csv
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from scipy.io import loadmat
from scipy.interpolate import RegularGridInterpolator

from ls7l_review_inputs import image_hdus, verify_manifest

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls7m_response'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def originals(inventory):
    """Restore only the two frozen, hash-identified sources when absent."""
    cache=ROOT/'results_ls7m_prf_inputs/originals';cache.mkdir(exist_ok=True)
    assert len(inventory['sources'])==2 and sum(s['bytes'] for s in inventory['sources'])<32_000_000
    nodes={}
    for ccd,spec in zip([3,4],inventory['sources'],strict=True):
        assert spec['bytes']<16_000_000
        path=cache/spec['name']
        if not path.exists():
            with urlopen(spec['url'],timeout=30) as response:
                assert response.status==200 and int(response.headers['Content-Length'])==spec['bytes']
                raw=response.read(spec['bytes']+1)
            assert len(raw)==spec['bytes'] and hashlib.sha256(raw).hexdigest()==spec['sha256']
            path.write_bytes(raw)
        assert path.stat().st_size==spec['bytes'] and digest(path)==spec['sha256']
        for entry in np.atleast_1d(loadmat(path,struct_as_record=False,squeeze_me=True)['prfStruct']):
            nodes[(ccd,int(entry.ccdRow),int(entry.ccdColumn))]=entry
    assert len(nodes)==50
    return nodes


def independent_integral(surface,uncertainty,axis_y,axis_x,pixel,knots,path,live,pulses):
    """Per-pixel cell crossings, endpoint/midpoint Simpson; no Gauss samples."""
    interpolators=[RegularGridInterpolator((axis_y,axis_x),v,method='linear',bounds_error=True)
                   for v in (surface,uncertainty)]
    totals=np.zeros(2);covered=True
    for left,right in live:
        for on,off in pulses:
            lo,hi=max(left,on),min(right,off)
            if hi<=lo:continue
            times=sorted([lo,hi]+[float(t) for t in knots if lo<t<hi])
            for a,b in zip(times[:-1],times[1:],strict=True):
                j=int(np.searchsorted(knots,(a+b)/2)-1)
                slope=(path[j+1]-path[j])/(knots[j+1]-knots[j]);intercept=path[j]-slope*knots[j]
                cuts=[a,b]
                for dim,axis in [(0,axis_x),(1,axis_y)]:
                    if slope[dim]!=0:
                        candidates=(pixel[dim]-axis-intercept[dim])/slope[dim]
                        cuts.extend(float(t) for t in candidates if a<t<b)
                cuts=np.unique(cuts);ends=np.column_stack([cuts[:-1],(cuts[:-1]+cuts[1:])/2,cuts[1:]])
                positions=intercept+ends[...,None]*slope
                delta=pixel-positions
                valid=((delta[...,0]>=axis_x[0]-1e-11)&(delta[...,0]<=axis_x[-1]+1e-11)&
                       (delta[...,1]>=axis_y[0]-1e-11)&(delta[...,1]<=axis_y[-1]+1e-11))
                covered=covered and bool(valid.all())
                points=np.stack([np.clip(delta[...,1],axis_y[0],axis_y[-1]),
                                 np.clip(delta[...,0],axis_x[0],axis_x[-1])],axis=-1)
                widths=np.diff(cuts)
                for k,f in enumerate(interpolators):
                    values=f(points)
                    totals[k]+=np.sum(widths*(values[:,0]+4*values[:,1]+values[:,2])/6)
    return (totals/sum(b-a for a,b in live) if covered else np.full(2,np.nan)),covered


def main():
    assert not (OUT/'audit.json').exists(),'refuse to overwrite a completed audit'
    cfg=json.loads((ROOT/'config/ls7m_response.json').read_text())
    for path,sha in cfg['input_sha256'].items():assert digest(ROOT/path)==sha,path
    preserved={folder:verify_manifest(ROOT/folder) for folder in
               ['results_ls7k_inputs','results_ls7l_engineering','results_ls7l_inputs']}
    inv=json.loads((ROOT/'results_ls7m_prf_inputs/inventory.json').read_text())
    earlier=json.loads((ROOT/'results_ls7k_inputs/inventory.json').read_text())
    raw=originals(inv);scalar_count=0;annotations=[]
    for record in inv['models']:
        entry=raw[(record['ccd'],record['grid_row'],record['grid_col'])]
        assert set(entry._fieldnames)==set(record['mat_fields'])
        for name,desc in record['field_descriptions'].items():
            arr=np.asarray(getattr(entry,name))
            assert list(arr.shape)==desc['shape'] and str(arr.dtype)==desc['dtype']
            assert int(np.isfinite(arr).sum())==desc['finite']
            if arr.size:assert float(arr.min())==desc['minimum'] and float(arr.max())==desc['maximum']
            if 'values' in desc:np.testing.assert_array_equal(arr,desc['values'])
        assert entry.widthPixels==13 and entry.samplesPerPixel==9
        np.testing.assert_allclose(entry.prfRow,np.arange(-58,59)/9,atol=1e-15,rtol=0)
        np.testing.assert_array_equal(entry.prfRow,entry.prfColumn)
        prior=next(m for m in earlier['prf_models'] if m['name']==record['fits_file'])
        images=image_hdus(ROOT/'results_ls7k_inputs'/prior['path'])
        for name,image in zip(['values','uncertainties'],images,strict=True):
            np.testing.assert_array_equal(getattr(entry,name),image);scalar_count+=image.size
            assert record['comparisons'][name]['identity_equal'] and record['comparisons'][name]['identity_max_abs']==0
            assert not record['comparisons'][name]['transpose_equal']
        if entry.rowShift!=0 or entry.columnShift!=0:
            annotations.append({'ccd':record['ccd'],'row':record['grid_row'],'column':record['grid_col'],
                                'row_shift':int(entry.rowShift),'column_shift':int(entry.columnShift)})
    assert len(annotations)==3
    phases=list(csv.DictReader((OUT/'phase_checks.csv').open()))
    assert len(phases)==4050
    seen=set();phase_error=0.
    for phase in phases:
        ccd,y,x,r,c=[int(phase[k]) for k in ['ccd','grid_row','grid_col','row_residue','column_residue']]
        assert (ccd,y,x,r,c) not in seen and 0<=r<9 and 0<=c<9
        seen.add((ccd,y,x,r,c));entry=raw[(ccd,y,x)]
        yy,xx=np.meshgrid(np.arange(-6,7)+(r-4)/9,np.arange(-6,7)+(c-4)/9,indexing='ij')
        points=np.stack([np.clip(yy,entry.prfRow[0],entry.prfRow[-1]),np.clip(xx,entry.prfColumn[0],entry.prfColumn[-1])],axis=-1)
        for name,label in [('values','maximum_flux_difference'),('uncertainties','maximum_uncertainty_difference')]:
            array=getattr(entry,name)
            computed=RegularGridInterpolator((entry.prfRow,entry.prfColumn),array)(points)
            error=float(np.max(np.abs(computed-array[r::9,c::9])));phase_error=max(phase_error,error)
            assert error<=cfg['absolute_tolerance'] and 0<=float(phase[label])<=cfg['absolute_tolerance']
        assert abs(float(np.sum(entry.values[r::9,c::9]))-float(phase['phase_sum']))<=cfg['absolute_tolerance']
    rows=json.loads((OUT/'cases.json').read_text());data=np.load(OUT/'predictions.npz',allow_pickle=False)
    assert len(rows)==144 and len(data.files)==432
    expected={(s,o,p,t['name'],pulse['name']) for s in cfg['sectors'] for o in cfg['column_offsets']
              for p in cfg['integration_start_phases_seconds'] for t in cfg['trajectories'] for pulse in cfg['pulses']}
    assert {(r['sector'],r['column_offset'],r['integration_start_seconds'],r['trajectory'],r['pulse']) for r in rows}==expected
    maxerr=np.zeros(2);coverage_checks=0;finite_checks=0;audits=[]
    field_records=json.loads((OUT/'field_weights.json').read_text())
    for row in rows:
        sector=next(r for r in earlier['light_curves'] if r['sector']==row['sector'])
        ccd=sector['ccd'];geo=sector['geometry'];source=np.array(geo['nominal_target_cutout_xy'])
        yy=sorted({y for c,y,x in raw if c==ccd});xx=sorted({x for c,y,x in raw if c==ccd})
        location=np.array(geo['nominal_target_detector_xy'])+[row['column_offset'],0]
        field=next(f for f in field_records if f['sector']==row['sector'] and f['column_offset']==row['column_offset'])
        assert abs(sum(n['weight'] for n in field['nodes'])-1)<1e-14
        for node in field['nodes']:
            meta=next(m for m in inv['models'] if m['fits_file']==node['file'])
            assert meta['field_descriptions']['rowShift']['values']==meta['field_descriptions']['columnShift']['values']==0
            i=xx.index(meta['grid_col']);j=yy.index(meta['grid_row'])
            basis=np.zeros((len(yy),len(xx)));basis[j,i]=1
            weight=float(RegularGridInterpolator((yy,xx),basis)([location[::-1]])[0])
            assert abs(weight-node['weight'])<1e-14
        images=[]
        for name in ['values','uncertainties']:
            cube=np.array([[getattr(raw[(ccd,y,x)],name) for x in xx] for y in yy])
            images.append(RegularGridInterpolator((yy,xx),cube)([location[::-1]])[0])
        axis_y,axis_x=raw[(ccd,yy[0],xx[0])].prfRow,raw[(ccd,yy[0],xx[0])].prfColumn
        trajectory=next(t for t in cfg['trajectories'] if t['name']==row['trajectory'])
        path=source+np.array(trajectory['displacement_xy']);knots=np.array(cfg['trajectory_times_seconds'])
        live=[(-10+2*k+row['integration_start_seconds'],-10+2*k+row['integration_start_seconds']+1.98) for k in range(10)]
        pulse=next(p for p in cfg['pulses'] if p['name']==row['pulse'])['intervals']
        pulses=[[-10,10]] if pulse is None else pulse
        overlap=sum(max(0,min(b,d)-max(a,c)) for a,b in live for c,d in pulses)
        assert abs(overlap-row['pulse_live_seconds'])<1e-13
        shape=tuple(geo['array_shape_yx']);prediction=np.empty((*shape,2));mask=np.empty(shape,dtype=bool)
        for y in range(shape[0]):
            for x in range(shape[1]):
                prediction[y,x],mask[y,x]=independent_integral(*images,axis_y,axis_x,np.array([x,y]),knots,path,live,pulses)
        np.testing.assert_array_equal(mask,data[row['case']+'_covered']);coverage_checks+=mask.size
        assert int(mask.sum())==row['covered_pixels'] and mask.size==row['stamp_pixels']
        errs=[]
        for k,name in enumerate(['flux','uncertainty']):
            recorded=data[row['case']+'_'+name]
            np.testing.assert_array_equal(np.isfinite(recorded),mask)
            error=float(np.max(np.abs(recorded[mask]-prediction[...,k][mask])));errs.append(error)
            assert error<=cfg['absolute_tolerance'],(row['case'],name,error)
            maxerr[k]=max(maxerr[k],error);finite_checks+=int(mask.sum())
        assert abs(float(np.nansum(prediction[...,0]))-row['summed_covered_flux'])<=cfg['absolute_tolerance']*mask.size
        assert abs(float(np.nansum(prediction[...,1]))-row['summed_covered_uncertainty_entries'])<=cfg['absolute_tolerance']*mask.size
        audits.append({'case':row['case'],'covered_pixels':int(mask.sum()),'max_flux_difference':errs[0],'max_uncertainty_difference':errs[1]})
        if len(audits)%36==0:print('Independent cases verified:',len(audits),flush=True)
    for comparison in json.loads((OUT/'coordinate_sensitivity.json').read_text()):
        a,b=comparison['case_offset_0'],comparison['case_offset_minus44']
        mask=data[a+'_covered']&data[b+'_covered'];fa,fb=data[a+'_flux'][mask],data[b+'_flux'][mask]
        assert int(mask.sum())==comparison['common_pixels']
        assert abs(float(np.sqrt(np.sum((fa-fb)**2)/np.sum(fa**2)))-comparison['relative_l2_difference'])<1e-14
        assert abs(float(np.sum(abs(fa-fb)))-comparison['absolute_l1_difference'])<1e-14
    audit={'status':'PASS','method':'original MATLAB + SciPy field/subpixel interpolation + per-pixel Simpson integration',
           'preserved_manifest_entries':preserved,'original_image_scalar_values':scalar_count,
           'coordinate_and_annotation_metadata_verified':True,'nonzero_shift_nodes':annotations,
           'phase_images':len(phases),'maximum_independent_phase_difference':phase_error,
           'calibration_cases':len(audits),'coverage_boolean_checks':coverage_checks,'finite_numeric_checks':finite_checks,
           'maximum_flux_difference':float(maxerr[0]),'maximum_uncertainty_difference':float(maxerr[1]),
           'absolute_tolerance':cfg['absolute_tolerance'],'cases':audits}
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in audit.items() if k!='cases'},indent=2),flush=True)


if __name__=='__main__':main()
