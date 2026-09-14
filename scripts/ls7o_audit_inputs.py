#!/usr/bin/env python3
"""Independent LS7O metadata/raw-row reconstruction and normal-equation fit.

No Astropy FITS reader, acquisition parser or reference producer imports.
"""
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct

import numpy as np
from scipy.optimize import linprog
from scipy.linalg import svd

ROOT=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text())
def sha(data):return hashlib.sha256(data).hexdigest()


def header(raw):
    result={}
    for i in range(0,len(raw),80):
        line=raw[i:i+80].decode('ascii');key=line[:8].strip()
        if key=='END':break
        if line[8:10]!='= ':continue
        value=line[10:].strip()
        if value.startswith("'"):
            result[key]=value[1:value.index("'",1)].strip()
        else:
            value=value.split('/')[0].strip()
            if value in ['T','F']:result[key]=value=='T'
            elif value:
                try:result[key]=int(value)
                except ValueError:result[key]=float(value.replace('D','E'))
    return result


def detector_point(h,h0):
    """Independent inverse TAN projection and FITS PC/CDELT linear mapping."""
    assert h['CTYPE1']=='RA---TAN' and h['CTYPE2']=='DEC--TAN'
    assert not any(k.startswith(('PV1_','PV2_','A_','B_')) for k in h)
    ra,dec,ra0,dec0=map(math.radians,[h0['RA_OBJ'],h0['DEC_OBJ'],h['CRVAL1'],h['CRVAL2']])
    divisor=math.sin(dec)*math.sin(dec0)+math.cos(dec)*math.cos(dec0)*math.cos(ra-ra0)
    tangent=np.degrees([math.cos(dec)*math.sin(ra-ra0)/divisor,
                        (math.sin(dec)*math.cos(dec0)-math.cos(dec)*math.sin(dec0)*math.cos(ra-ra0))/divisor])
    pc=np.array([[h.get(f'PC{i}_{j}',float(i==j)) for j in [1,2]] for i in [1,2]])
    linear=np.diag([h['CDELT1'],h['CDELT2']])@pc
    pixel=np.array([h['CRPIX1'],h['CRPIX2']])+np.linalg.solve(linear,tangent)
    return pixel-np.array([h['CRPIX1P'],h['CRPIX2P']])+np.array([h['CRVAL1P'],h['CRVAL2P']])


def audit_inputs():
    cfg=read(ROOT/'config/ls7o_reference.json')
    meta=read(ROOT/'results_ls7o_metadata/inventory.json')
    sources=read(ROOT/'results_ls7o_inputs/sources.json')
    raw_refs={};coordinates={};count=0;centroid_pixels={};max_time=0.
    for sector,ccd in [(29,3),(32,4)]:
        eligible=[]
        a0,d0=map(math.radians,(124.531756290083,-68.3129998725044))
        for line in (ROOT/'results_ls7o_metadata/archive'/f'all_targets_20s_S{sector:03d}_v1.txt').read_text().splitlines():
            if not line or line.startswith('#'):continue
            tic,cam,chip,mag,ra,dec=map(float,line.split())
            a,d=map(math.radians,(ra,dec))
            sep=math.degrees(math.atan2(math.hypot(math.cos(d)*math.sin(a-a0),math.cos(d0)*math.sin(d)-math.sin(d0)*math.cos(d)*math.cos(a-a0)),
                                       math.sin(d0)*math.sin(d)+math.cos(d0)*math.cos(d)*math.cos(a-a0)))
            if cam==4 and chip==ccd and 8<=mag<=12 and .25<=sep<=3 and tic!=307210830:
                eligible.append((sep,int(tic)))
        eligible.sort()
        records=[r for r in meta['references'] if r['sector']==sector]
        assert [t for sep,t in eligible[:6]]==[r['tic'] for r in records]
        source_records=[r for r in sources['records'] if r['sector']==sector]
        archived=np.load(ROOT/f'results_ls7o_inputs/references_s{sector:03d}.npz',allow_pickle=False)
        target_time=np.load(ROOT/f'results_ls7k_inputs/timing_s{sector:03d}.npz',allow_pickle=False)
        target=next(x for x in meta['spatial'] if x['sector']==sector)['target_detector_xy']
        vectors=[];xy=[];masks=[]
        for j,record in enumerate(records):
            tic=record['tic'];assert archived['tic'][j]==tic
            source=source_records[j];assert source['tic']==tic
            prefix=ROOT/'results_ls7o_metadata'/record['header_prefix']
            h0=header(Path(str(prefix)+'_primary.hdr').read_bytes())
            h1=header(Path(str(prefix)+'_lightcurve.hdr').read_bytes())
            h2=header(Path(str(prefix)+'_aperture.hdr').read_bytes())
            assert (h0['TICID'],h0['SECTOR'],h0['CAMERA'],h0['CCD'])==(tic,sector,4,ccd)
            assert abs(h1['TIMEDEL']*86400-20)<2e-5 and h1['NAXIS1']==100
            assert h1['TIMESYS']=='TDB' and h1['TIMEREF']=='SOLARSYSTEM'
            assert h2['CDELT1P']==h2['CDELT2P']==1
            point=detector_point(h2,h0)
            np.testing.assert_allclose(point,record['geometry']['nominal_target_detector_xy'],atol=1e-8,rtol=0)
            xy.append(point)
            mask_raw=Path(str(prefix)+'_aperture.bin').read_bytes()
            mask=struct.unpack('>'+str(len(mask_raw)//4)+'i',mask_raw)
            pix=[]
            for k,value in enumerate(mask):
                if value&8:
                    y,x=divmod(k,h2['NAXIS1'])
                    pix.append((x+h2['CRVAL1P']+1-h2['CRPIX1P'],y+h2['CRVAL2P']+1-h2['CRPIX2P']))
            assert len(pix)==record['moment_centroid_pixels']>0
            minimum=min(math.dist(p,target) for p in pix)
            np.testing.assert_allclose(minimum,record['minimum_target_to_centroid_pixel_distance'],atol=1e-10)
            assert minimum>40
            for previous in masks:assert set(pix).isdisjoint(previous)
            masks.append(set(pix))
            # Every structural field is interpreted from preserved raw cards.
            names=[h1[f'TTYPE{i}'] for i in range(1,h1['TFIELDS']+1)]
            code={'D':'d','E':'f','J':'i'}
            parser=struct.Struct('>'+''.join(code[h1[f'TFORM{i}']] for i in range(1,len(names)+1)))
            assert parser.size==100
            raw=gzip.decompress((ROOT/'results_ls7o_inputs'/source['raw_path']).read_bytes())
            assert len(raw)==401000 and sha(raw)==source['raw_sha256']
            allocation=next(r for r in cfg['acquisition'] if (r['sector'],r['tic'])==(sector,tic))
            assert len(allocation['ranges'])==len(source['ranges'])==10
            for a,(expected,request) in enumerate(zip(allocation['ranges'],source['ranges'],strict=True)):
                assert request['start']==expected['start'] and request['length']==expected['length']==40100
                assert expected['start']==record['table_start']+int(target_time['indices'][a,0])*100
                assert request['etag']==record['product']['etag']
                assert sha(raw[a*40100:(a+1)*40100])==request['sha256']
            vals=np.array(list(parser.iter_unpack(raw))).reshape(10,401,20)
            fields={name:vals[:,:,i] for i,name in enumerate(names)}
            centroid=np.stack([fields['MOM_CENTR1'],fields['MOM_CENTR2']],axis=-1)
            error=np.stack([fields['MOM_CENTR1_ERR'],fields['MOM_CENTR2_ERR']],axis=-1)
            expected={'centroid_xy':centroid,'error_xy':error,'quality':fields['QUALITY'].astype(np.int64),
                      'cadence':fields['CADENCENO'].astype(np.int64),'time_barycentric_btjd':fields['TIME'],
                      'time_correction_days':fields['TIMECORR']}
            for key,value in expected.items():
                np.testing.assert_array_equal(value,archived[key][j]);count+=value.size
            np.testing.assert_array_equal(expected['cadence'],target_time['cadence'])
            timing=(fields['TIME']-fields['TIMECORR']-target_time['time_spacecraft_btjd'])*86400
            assert np.isfinite(timing).all() and np.max(abs(timing))<=cfg['spacecraft_alignment_tolerance_seconds']
            max_time=max(max_time,float(np.max(abs(timing))))
            valid=np.isfinite(centroid).all(-1)&np.isfinite(error).all(-1)&(error>0).all(-1)&(expected['quality']==0)
            assert valid.sum()==source['valid_centroid_rows']
            vectors.append(expected)
        design=np.column_stack([np.ones(6),(np.array(xy)-target)/1024])
        np.testing.assert_allclose(design,next(r for r in meta['spatial'] if r['sector']==sector)['reference_design'],atol=1e-11,rtol=0)
        # Convex membership checked by nonnegative barycentric weights, not Delaunay.
        assert linprog(np.zeros(6),A_eq=design.T,b_eq=[1,0,0],bounds=(0,None),method='highs').success
        raw_refs[sector]={k:np.stack([v[k] for v in vectors]) for k in vectors[0]}
        coordinates[sector]=design
        centroid_pixels[sector]=sum(map(len,masks))
    report={'reference_products':12,'raw_reference_rows':48120,'exact_scalar_values_checked':count,
            'selection_reproduced':True,'raw_mask_target_exclusion_pass':True,'reference_masks_pairwise_disjoint':True,
            'centroid_pixel_counts':centroid_pixels,'maximum_time_join_error_seconds':max_time,
            'raw_row_bytes_checked':4_812_000,'whole_file_fits_checksum_verified':False}
    return raw_refs,coordinates,report


def rebuild_motion(reference,design,anchor,side,selected):
    c=reference['centroid_xy'][:,anchor];e=reference['error_xy'][:,anchor];q=reference['quality'][:,anchor]
    if not (np.isfinite(c[:,selected]).all() and np.isfinite(e[:,selected]).all() and
            (e[:,selected]>0).all() and (q[:,selected]==0).all()):return None
    center=np.array([[np.median([c[j,t,k] for t in side]) for k in range(2)] for j in range(6)])
    error=np.array([[np.median([e[j,t,k] for t in side]) for k in range(2)] for j in range(6)])
    positions=np.full((401,2),np.nan);formal=np.full((401,2),np.nan);operators=[];conditions=[];scatter=[]
    for axis in [0,1]:
        weight=np.diag(error[:,axis]**-2)
        singular=svd(design/error[:,axis,None],compute_uv=False,lapack_driver='gesvd')
        condition=float(singular[0]/singular[-1]) if singular[-1]>0 else np.inf
        if int(np.sum(singular>singular[0]*1e-10))!=3 or condition>1e8:return None
        op=np.linalg.solve(design.T@weight@design,design.T@weight)
        delta=c[:,selected,axis]-center[:,axis,None]
        beta=op@delta
        positions[selected,axis]=beta[0]
        formal[selected,axis]=np.sqrt(np.array([sum((op[0,j]*e[j,t,axis])**2 for j in range(6)) for t in selected]))
        res=delta-design@beta
        scatter.append(float(np.mean(np.sum((res/e[:,selected,axis])**2,axis=0)/3)))
        operators.append(op);conditions.append(condition)
    if np.max(abs(positions[selected]))>.25:return None
    return {'positions_xy':positions,'formal_sigma_xy':formal,'centers_xy':center,
            'sideband_median_error_xy':error,'operators_xy':operators,'conditions_xy':conditions,
            'reference_residual_mean_chi2_per_3_dof_xy':scatter}
