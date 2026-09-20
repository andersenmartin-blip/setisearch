#!/usr/bin/env python3
"""Build exact LS8H GJ 849 paired-image scope after unique native-time joins."""
import csv, hashlib, json
from pathlib import Path
import numpy as np
from astropy.io import fits
from ls8a_l2_evaluate import dtype

ROOT=Path(__file__).resolve().parents[1]
META=ROOT/'results_ls8h_metadata'
KEY='CH_PR100018_TG032401_V0300'
START=75
DURATION=1
LO=61
HI=90

def main():
    h=fits.Header.fromstring((ROOT/'results_ls8g_l2_metadata'/KEY/'lightcurve_header.bin').read_bytes().decode(),sep='')
    l2=np.frombuffer((ROOT/'results_ls8g_l2_screen'/KEY/'lightcurve_table.bin').read_bytes(),dtype=dtype(h))
    sources={KEY:{}}; tables={}
    for kind in ('SCI_CAL_SubArray','SCI_COR_SubArray'):
        folder=META/KEY
        hdus=json.loads((folder/f'{kind}_hdus.json').read_text())
        receipt=json.loads((folder/f'{kind}_ranges.json').read_text())
        image=next(x for x in hdus if x['name']==kind)
        ih=fits.Header.fromstring((folder/image['header_file']).read_text(),sep='\n')
        assert ih['BITPIX']==-64 and ih['NAXIS1']==ih['NAXIS2']==200
        assert ih.get('BSCALE',1)==1 and ih.get('BZERO',0)==0
        for field in ('NEXP','EXPTIME','TEXPTIME','PIPE_VER'):
            assert ih[field]==h[field],(kind,field,ih[field],h[field])
        mh=next(x for x in hdus if x['name']==kind.replace('SubArray','ImageMetadata'))
        with fits.open(folder/mh['metadata_file'],memmap=False) as f:
            table=f[1].data.copy()
        assert len(table)==ih['NAXIS3']
        tables[kind]=table
        disposition=next(v for k,v in receipt['ranges'][0]['headers'].items() if k.lower()=='content-disposition')
        spec={'total':receipt['total_file_bytes'],'etag':receipt['etag'],'content_disposition':disposition,
              'image_hdu':image['hdu'],'image_data_start':image['data_start'],
              'frame_bytes':320000,'frames':ih['NAXIS3'],'shape':[200,200],
              'bitpix':-64,'bunit':ih['BUNIT'],'xoff':ih['X_WINOFF'],'yoff':ih['Y_WINOFF'],
              'metadata_file':str((folder/mh['metadata_file']).relative_to(ROOT)),
              'metadata_sha256':hashlib.sha256((folder/mh['metadata_file']).read_bytes()).hexdigest()}
        if kind=='SCI_COR_SubArray':
            smear=next(x for x in hdus if x['name']=='SCI_COR_SmearingRow')
            sh=fits.Header.fromstring((folder/smear['header_file']).read_text(),sep='\n')
            assert sh['BITPIX']==-64 and sh['NAXIS1']==200 and sh['NAXIS2']==1 and sh['NAXIS3']==len(table)
            spec['smear_data_start']=smear['data_start']; spec['smear_row_bytes']=1600
            spec['smear_bunit']=sh.get('BUNIT')
        sources[KEY][kind]=spec
    for k in ('xoff','yoff','bunit','shape'):
        assert sources[KEY]['SCI_CAL_SubArray'][k]==sources[KEY]['SCI_COR_SubArray'][k]

    context={'id':'TG032401_P0','file_key':KEY,'sign':'positive','cluster_id':0,
             'start':START,'duration':DURATION,'lo':LO,'hi':HI,'ranges':{},'image_rows':{}}
    ledger=[]
    for kind in ('SCI_CAL_SubArray','SCI_COR_SubArray'):
        tab=tables[kind]; matched=[]
        for row in range(LO,HI):
            target=l2[row]
            dt=(tab['MJD_TIME'].astype(float)-target['MJD_TIME'])*86400.
            indices=np.flatnonzero(np.abs(dt)<=.001)
            assert len(indices)==1,(kind,row,'non-unique MJD join',indices.tolist())
            idx=int(indices[0]); matched.append(idx)
            utc=target['UTC_TIME'].decode().strip()
            assert utc==str(tab['UTC_TIME'][idx]).strip(),(kind,row,'UTC mismatch')
            dbjd=float((tab['BJD_TIME'][idx]-target['BJD_TIME'])*86400.)
            assert abs(dbjd)<=.001,(kind,row,'BJD mismatch',dbjd)
            ledger.append({'id':'TG032401_P0','kind':kind,'l2_row':row,'image_row':idx,
                           'utc':utc,'mjd_delta_seconds':float(dt[idx]),'bjd_delta_seconds':dbjd,
                           'ce_counter':int(tab['CE_COUNTER'][idx]),'ce_integrity':int(tab['CE_INTEGRITY'][idx])})
        assert matched==list(range(matched[0],matched[0]+len(matched)))
        context['image_rows'][kind]=matched
        spec=sources[KEY][kind]
        context['ranges'][kind]={'start':spec['image_data_start']+matched[0]*320000,'count':len(matched)*320000}
        if kind=='SCI_COR_SubArray':
            context['ranges']['SMEAR']={'start':spec['smear_data_start']+matched[0]*1600,'count':len(matched)*1600}
    cal,cor=tables['SCI_CAL_SubArray'],tables['SCI_COR_SubArray']
    for a,b in zip(context['image_rows']['SCI_CAL_SubArray'],context['image_rows']['SCI_COR_SubArray']):
        assert cal['CE_COUNTER'][a]==cor['CE_COUNTER'][b]
        assert cal['CE_INTEGRITY'][a]==cor['CE_INTEGRITY'][b]

    manifest={'stage':'LS8H','status':'METADATA_JOINED_IMAGES_CLOSED','sources':sources,'contexts':[context],
              'join_tolerance_seconds':.001,'join_rows':len(ledger),
              'image_science_bytes':sum(context['ranges'][k]['count'] for k in ('SCI_CAL_SubArray','SCI_COR_SubArray')),
              'smearing_bytes':context['ranges']['SMEAR']['count'],'image_pixels_read':0}
    (ROOT/'config/ls8h_images.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (META/'joins.json').write_text(json.dumps(ledger,indent=2)+'\n')
    with (META/'joins.csv').open('w') as stream:
        writer=csv.DictWriter(stream,list(ledger[0])); writer.writeheader(); writer.writerows(ledger)
    summary={k:v for k,v in manifest.items() if k not in ('sources','contexts')}
    (META/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
