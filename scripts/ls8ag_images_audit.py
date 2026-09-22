#!/usr/bin/env python3
"""Independent struct/long-double/normal-equation audit of LS8AG."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import numpy as np
from astropy.io import fits

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results_ls8ag_images'
LD=np.longdouble
L2ROW=struct.Struct('>26sddddii7d4f')


def metadata_audit(cfg):
    tables={};l2={};checks=0
    for key,sources in cfg['sources'].items():
        l2[key]=list(L2ROW.iter_unpack((ROOT/'results_ls8af_l2_screen'/key/'lightcurve_table.bin').read_bytes()))
        for kind,spec in sources.items():
            path=ROOT/spec['metadata_file'];raw=path.read_bytes()
            assert hashlib.sha256(raw).hexdigest()==spec['metadata_sha256'];checks+=1
            with fits.open(path,memmap=False) as f:
                h=f[1].header;offset=f[1].fileinfo()['datLoc']
            offsets={};scaling={};position=0
            for i in range(1,h['TFIELDS']+1):
                n,code=re.fullmatch(r'(\d*)([ADEJIB])',h[f'TFORM{i}']).groups()
                offsets[h[f'TTYPE{i}']]=position;position+=int(n or 1)*{'A':1,'B':1,'D':8,'E':4,'J':4,'I':2}[code]
                scaling[h[f'TTYPE{i}']]=(h.get(f'TSCAL{i}',1),h.get(f'TZERO{i}',0))
            assert position==h['NAXIS1'];checks+=1
            rows=[]
            for i in range(h['NAXIS2']):
                p=offset+i*position
                utc,mjd,bjd=struct.unpack_from('>26sdd',raw,p)
                ce=struct.unpack_from('>h',raw,p+offsets['CE_COUNTER'])[0]
                ce=ce*scaling['CE_COUNTER'][0]+scaling['CE_COUNTER'][1]
                integrity=raw[p+offsets['CE_INTEGRITY']]
                rows.append((utc.decode().strip(),mjd,bjd,ce,integrity))
            tables[key,kind]=rows
    ledger=json.loads((ROOT/'results_ls8ag_metadata/joins.json').read_text())
    lookup={(r['id'],r['kind'],r['l2_row']):r for r in ledger}
    joined=0
    for c in cfg['contexts']:
        key=c['file_key']
        for kind in ('SCI_CAL_SubArray','SCI_COR_SubArray'):
            meta=tables[key,kind];spec=cfg['sources'][key][kind]
            matched=[]
            for i in range(c['lo'],c['hi']):
                row=l2[key][i]
                matches=[j for j,r in enumerate(meta) if abs((r[1]-row[1])*86400.)<=.001]
                assert len(matches)==1;idx=matches[0];matched.append(idx)
                assert meta[idx][0]==row[0].decode().strip()
                assert abs((meta[idx][2]-row[2])*86400.)<=.001
                saved=lookup[c['id'],kind,i]
                assert (saved['image_row'],saved['utc'],saved['ce_counter'],saved['ce_integrity'])==(idx,meta[idx][0],meta[idx][3],meta[idx][4])
                checks+=4;joined+=1
            assert matched==c['image_rows'][kind]
            assert c['ranges'][kind]=={'start':spec['image_data_start']+matched[0]*320000,'count':len(matched)*320000}
            checks+=2
        for a,b in zip(c['image_rows']['SCI_CAL_SubArray'],c['image_rows']['SCI_COR_SubArray']):
            assert tables[key,'SCI_CAL_SubArray'][a][3:]==tables[key,'SCI_COR_SubArray'][b][3:];checks+=1
    assert joined==len(ledger)==cfg['join_rows']==58
    return l2,{'status':'PASS','joined_rows':joined,'exact_checks':checks,'image_bytes_read':0}


def event_map(times,cube,side,event,valid):
    result=np.full(cube.shape[1:],np.nan)
    if not valid.any():return result
    x=np.asarray(times,dtype=LD);ys=cube[side][:,valid].astype(LD)
    offset=np.median(ys,axis=0);ys-=offset
    sx=x[side].sum();sxx=(x[side]**2).sum();n=LD(len(side))
    sy=ys.sum(axis=0);sxy=(x[side,None]*ys).sum(axis=0)
    determinant=n*sxx-sx*sx
    b0=(sy*sxx-sxy*sx)/determinant;b1=(n*sxy-sx*sy)/determinant
    residual=cube[event][:,valid].astype(LD)-offset-b0-x[event,None]*b1
    result[valid]=residual.sum(axis=0).astype(float)
    return result


def regression(y,columns):
    if len(y)<len(columns) or not len(y):return {'available':False,'reason':'TOO_FEW_PIXELS'}
    scales=np.array([math.sqrt(math.fsum(float(v)*float(v) for v in col)) for col in columns])
    normalized=[np.asarray(col,float)/(scale if scale>0 else 1) for col,scale in zip(columns,scales)]
    x=np.column_stack(normalized)
    singular=np.linalg.svd(x,compute_uv=False);rank=int(np.sum(singular>singular[0]*1e-12))
    if rank!=len(columns):return {'available':False,'reason':'RANK_DEFICIENT','rank':rank}
    gram=np.array([[math.fsum(float(a)*float(b) for a,b in zip(c,d)) for d in normalized] for c in normalized])
    rhs=np.array([math.fsum(float(a)*float(b) for a,b in zip(c,y)) for c in normalized])
    beta=np.linalg.solve(gram,rhs)
    residual=np.asarray(y)-sum(b*c for b,c in zip(beta,normalized))
    sse=math.fsum(float(v)*float(v) for v in residual);energy=math.fsum(float(v)*float(v) for v in y)
    return {'available':True,'pixels':len(y),'rank':rank,'condition':float(singular[0]/singular[-1]),
            'coefficients':(beta/scales).tolist(),'rms':math.sqrt(sse/len(y)),
            'explained':1-sse/energy if energy>0 else None}


def columns_projection(a,valid):
    projection=np.full_like(a,np.nan)
    for col in range(a.shape[1]):
        use=valid[:,col]
        if use.any():projection[use,col]=math.fsum(float(v) for v in a[use,col])/int(use.sum())
    energy=math.fsum(float(v)*float(v) for v in a[valid])
    fraction=math.fsum(float(v)*float(v) for v in projection[valid])/energy if energy>0 else None
    return projection,fraction


def rebuild(times,cal,cor,smear,side,event,center,sign):
    valid=np.ones(cal.shape[1:],bool)
    for i in list(side)+list(event):valid &= np.isfinite(cal[i])&np.isfinite(cor[i])
    sv=np.ones(smear.shape[1:],bool)
    for i in list(side)+list(event):sv &= np.isfinite(smear[i])
    maps={'CAL':event_map(times,cal,side,event,valid),'COR':event_map(times,cor,side,event,valid),
          'SMEAR':event_map(times,smear,side,event,sv),'COMMON':valid}
    maps['DELTA']=maps['COR']-maps['CAL']
    dcol,dfrac=columns_projection(maps['DELTA'],valid);_,cfrac=columns_projection(maps['COR'],valid)
    means={}
    for name,cube in [('CAL',cal),('COR',cor)]:
        value=np.full(valid.shape,np.nan);value[valid]=cube[side][:,valid].astype(LD).sum(axis=0)/len(side);means[name]=value
    y,x=np.indices(valid.shape);conventions={}
    for number in (0,1):
        cx,cy=center[0]-number,center[1]-number
        dist=(x-cx)**2+(y-cy)**2;geom=dist<=625;aperture=geom&valid
        ann=(dist>900)&(dist<=1600)&valid
        sums={k:math.fsum(float(v) for v in maps[k][aperture]) for k in ('CAL','COR','DELTA')}
        zero=512*2.**-52*max(1.,math.fsum(abs(float(v)) for v in cor[side][:,aperture].flat)/len(side))
        den=abs(sums['COR'])>zero
        modelsets={}
        for name in ('CAL','COR'):
            if not ann.any():
                modelsets[name]={k:{'available':False,'reason':'NO_BACKGROUND_ANNULUS'} for k in ('brightness','displacement','combined')};continue
            profile=means[name]-float(np.median(means[name][ann]))
            dx=np.full_like(profile,np.nan);dy=dx.copy()
            dx[:,1:-1]=.5*(profile[:,2:]-profile[:,:-2]);dy[1:-1]=.5*(profile[2:]-profile[:-2])
            use=aperture&np.isfinite(dx)&np.isfinite(dy)
            ev=maps[name][use];one=np.ones(len(ev));p,gx,gy=profile[use],dx[use],dy[use]
            modelsets[name]={'brightness':regression(ev,[p,one]),'displacement':regression(ev,[gx,gy,one]),'combined':regression(ev,[p,gx,gy,one])}
        outside=(dist>1225)&valid&np.isfinite(maps['SMEAR'])[None,:]
        values=np.tile(maps['SMEAR'],(valid.shape[0],1))[outside]
        smearfit=regression(maps['DELTA'][outside],[np.ones(len(values)),values])
        total=math.fsum(abs(float(v)) for v in maps['COR'][valid])
        complete=bool(np.all(valid[geom]) and 25<=cx<=valid.shape[1]-26 and 25<=cy<=valid.shape[0]-26)
        conventions[f'C{number}']={'center':[float(cx),float(cy)],'aperture_pixels':int(geom.sum()),
            'valid_aperture_pixels':int(aperture.sum()),'aperture_complete':complete,'event_sums':sums,'cor_zero_floor':zero,
            'delta_over_cor':sums['DELTA']/sums['COR'] if den else None,
            'column_delta_over_cor':math.fsum(float(v) for v in dcol[aperture])/sums['COR'] if den else None,
            'sign_matches_l2':bool((sums['COR']>0)==(sign=='positive')) if den else False,
            'cor_l1_aperture_fraction':math.fsum(abs(float(v)) for v in maps['COR'][aperture])/total if total>0 else None,
            'smearing_delta_fit':smearfit,'fits':modelsets}
    required=all(c['aperture_complete'] and c['delta_over_cor'] is not None and c['sign_matches_l2'] for c in conventions.values())
    correction=required and all(abs(c['delta_over_cor'])>=.5 or abs(c['column_delta_over_cor'])>=.5 for c in conventions.values())
    spatial=required
    for c in conventions.values():
        b,d=c['fits']['COR']['brightness'],c['fits']['COR']['displacement']
        spatial &= b['available'] and d['available'] and b.get('explained') is not None and d.get('explained') is not None
        if spatial:spatial &= d['explained']>=.8 and d['explained']-b['explained']>=.2
    label='CORRECTION_LINKED' if correction else ('SPATIALLY_STRUCTURED' if spatial else 'UNRESOLVED_WITHIN_FIXED_SCOPE')
    return {'common_pixels':int(valid.sum()),'cor_column_energy_fraction':cfrac,'delta_column_energy_fraction':dfrac,
            'conventions':conventions,'classification':label},maps


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--metadata-only',action='store_true');args=parser.parse_args()
    cfg=json.loads((ROOT/'config/ls8ag_images.json').read_text());l2,meta=metadata_audit(cfg)
    if args.metadata_only:
        (ROOT/'results_ls8ag_metadata/audit.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta));return
    saved=json.loads((OUT/'diagnostics.json').read_text());assert [r['id'] for r in saved]==[c['id'] for c in cfg['contexts']]
    failures=[];count={'numeric':0,'exact':meta['exact_checks']};maxima={};references=[]

    def compare(actual,expected,path):
        if isinstance(expected,dict):
            count['exact']+=1
            if set(actual)!=set(expected):failures.append({'path':path,'reason':'key mismatch'});return
            for k,v in expected.items():compare(actual[k],v,path+'.'+k)
        elif isinstance(expected,list):
            assert len(actual)==len(expected);count['exact']+=1
            for i,v in enumerate(expected):compare(actual[i],v,path+f'[{i}]')
        elif isinstance(expected,float):
            count['numeric']+=1
            dimensionless=any(s in path for s in ('over_cor','fraction','explained','condition'))
            tolerance=(1e-8 if dimensionless else 1e-6)+2e-8*abs(expected)
            diff=abs(actual-expected) if actual is not None else math.inf
            if not math.isfinite(diff) or diff>tolerance:failures.append({'path':path,'actual':actual,'reference':expected,'tolerance':tolerance})
            maxima['summary']=max(maxima.get('summary',0.),diff)
        else:
            count['exact']+=1
            if actual!=expected:failures.append({'path':path,'actual':actual,'reference':expected})

    for c,actual in zip(cfg['contexts'],saved):
        arrays={};folder=OUT/c['id'];n=c['hi']-c['lo']
        for kind in ('SCI_CAL_SubArray','SCI_COR_SubArray','SMEAR'):
            path=folder/(kind+'.bin.gz');compressed=path.read_bytes();raw=gzip.decompress(compressed)
            rec=json.loads(path.with_suffix(path.suffix+'.json').read_text())
            assert hashlib.sha256(raw).hexdigest()==rec['raw_sha256'] and hashlib.sha256(compressed).hexdigest()==rec['gzip_sha256']
            assert rec['start']==c['ranges'][kind]['start'] and len(raw)==rec['count']==c['ranges'][kind]['count']
            product='SCI_COR_SubArray' if kind=='SMEAR' else kind
            assert rec['etag']==cfg['sources'][c['file_key']][product]['etag'];count['exact']+=5
            values=np.fromiter((v[0] for v in struct.iter_unpack('>d',raw)),dtype=float)
            arrays[kind]=values.reshape((n,200) if kind=='SMEAR' else (n,200,200))
        rows=l2[c['file_key']][c['lo']:c['hi']];d=c['duration']
        times=np.array([(LD(r[2])-LD(rows[14][2]))*86400 for r in rows],dtype=LD)
        side=list(range(12))+list(range(16+d,28+d));event=list(range(14,14+d))
        spec=cfg['sources'][c['file_key']]['SCI_COR_SubArray']
        center=[math.fsum(rows[i][16] for i in side)/24-spec['xoff'],math.fsum(rows[i][17] for i in side)/24-spec['yoff']]
        reference,maps=rebuild(times,arrays['SCI_CAL_SubArray'],arrays['SCI_COR_SubArray'],arrays['SMEAR'],side,event,center,c['sign'])
        reference={'id':c['id'],'file_key':c['file_key'],'sign':c['sign'],'start':c['start'],'duration':d,**reference}
        compare(actual,reference,c['id']);references.append(reference)
        with np.load(folder/'event_maps.npz') as result:
            assert set(result.files)==set(maps)
            for k,v in maps.items():
                assert result[k].shape==v.shape
                if k=='COMMON':assert np.array_equal(result[k],v);count['exact']+=v.size;continue
                assert np.array_equal(np.isfinite(result[k]),np.isfinite(v));count['exact']+=v.size
                use=np.isfinite(v);diff=np.abs(result[k][use]-v[use]);count['numeric']+=int(use.sum())
                maxima[k]=max(maxima.get(k,0.),float(diff.max(initial=0)))
                bad=diff>(1e-6+2e-8*np.abs(v[use]))
                if bad.any():failures.append({'path':c['id']+'.map.'+k,'failed_pixels':int(bad.sum()),'max_difference':float(diff.max())})
        print(c['id'],'audited',reference['classification'],flush=True)
    audit={'status':'FAIL' if failures else 'PASS','comparisons':count,'maximum_absolute_differences':maxima,'disagreements':failures,
           'method':'independent struct decoding, long-double temporal normal equations, scalar-sum spatial normal equations',
           'tolerances':{'relative':2e-8,'native_absolute':1e-6,'dimensionless_absolute':1e-8},'input_l2_audit':'PASS'}
    (OUT/'independent_reference.json').write_text(json.dumps(references,indent=2,allow_nan=False)+'\n')
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2,allow_nan=False)+'\n')
    summary=json.loads((OUT/'summary.json').read_text());summary['status']='COMPLETE_AUDITED' if not failures else 'COMPLETE_AUDIT_FAILED'
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(audit,indent=2));assert not failures,'frozen audit failed'


if __name__=='__main__':main()
