#!/usr/bin/env python3
"""Freeze a complete/bounded exact-ID trigger review queue, then retrieve FITS."""
import csv,hashlib,importlib.util,json,time
from pathlib import Path
from astropy.io import fits
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
ANALYSIS=ROOT/'main_analysis'
OUT=ROOT/'main_cutout_review'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    associations=json.loads((ANALYSIS/'CUTOUT_ASSOCIATIONS.json').read_text())
    with (HERE/'MAIN_SELECTION_FROZEN.csv').open() as f:selection=list(csv.DictReader(f))
    rank={r['diaObjectId']:int(r['selection_index']) for r in selection}
    source_context={}
    for row in associations:
        if row['cutout_status']!='EXACT_SOURCE_ID_AVAILABLE':continue
        sid=row['matching_source_ids'][0]
        entry=source_context.setdefault(sid,{'diaSourceId':sid,'object_id':row['trigger_object_id'],'visit':row['visit'],
            'detector':row['detector'],'band':row['band'],'time_mjd_tai':row['time_mjd_tai'],'triggers':[]})
        if entry['object_id']!=row['trigger_object_id']:raise ValueError('SourceID associated to different main object')
        entry['triggers'].append({'stream':row['trigger_stream'],'measurement_id':row['trigger_measurement_id']})
    order=sorted(source_context.values(),key=lambda r:(rank[r['object_id']],r['time_mjd_tai'],int(r['diaSourceId'])))
    selected=order[:30]
    OUT.mkdir(parents=True,exist_ok=True)
    plan={'status':'FROZEN_BEFORE_TRIGGER_IMAGE_BYTES','all_trigger_rows':len(associations),'unique_exact_source_ids':len(order),
          'selected_source_ids':selected,'omitted_by30source_bound':order[30:],
          'no_exact_source_or_ambiguous':[r for r in associations if r['cutout_status']!='EXACT_SOURCE_ID_AVAILABLE'],
          'selection_order':'Frozen main selection_index, timeMJDTAI, exact sourceID; all exact source IDs if<=30, first30 otherwise. No intensity ranking.',
          'kinds':['Science','Template','Difference'],'max_attempts_per_product':2,'maximum_response_bytes':2000000,
          'total_payload_budget':30000000,'concurrency':1,'nearest_source_substitution':False,
          'trigger_association_sha256':sha(ANALYSIS/'CUTOUT_ASSOCIATIONS.json'),'script_sha256':sha(Path(__file__)),
          'transfer_helper_sha256':sha(ROOT/'access_pilot/access.py')}
    with (OUT/'PLAN.json').open('x') as f:json.dump(plan,f,indent=2)
    spec=importlib.util.spec_from_file_location('trigger_transfer',ROOT/'access_pilot/access.py')
    transfer=importlib.util.module_from_spec(spec);spec.loader.exec_module(transfer);transfer.ROOT=OUT
    records=[];charged=0
    for entry in selected:
        for kind in plan['kinds']:
            record={**entry,'kind':kind,'status':'NOT_ATTEMPTED','attempts':[]}
            for attempt in (1,2):
                if charged+plan['maximum_response_bytes']>plan['total_payload_budget']:
                    record['status']='PAYLOAD_BUDGET_UNAVAILABLE';break
                label=f'raw/{entry["diaSourceId"]}_{kind}_attempt{attempt}.fits'
                receipt,data=transfer.fetch('/api/v1/cutouts',{'diaSourceId':entry['diaSourceId'],'kind':kind,'output-format':'FITS'},label,max_bytes=plan['maximum_response_bytes'])
                record['attempts'].append(receipt)
                charged+=len(data) if receipt['error'] is None or receipt['http_status'] is not None else plan['maximum_response_bytes']
                if receipt['complete']:
                    try:
                        with fits.open(OUT/label) as hdus:
                            record['hdus']=[{'name':h.name,'shape':list(h.data.shape) if h.data is not None else None,
                                             'BUNIT':h.header.get('BUNIT'),'UTYPE':h.header.get('UTYPE')} for h in hdus]
                            if hdus[0].data is None or hdus[0].data.ndim!=2:raise ValueError('No primary2D image')
                        record.update(status='FITS_AVAILABLE',canonical_path=label,sha256=receipt['sha256'],bytes=receipt['bytes_saved'])
                    except Exception as exc:record.update(status='INVALID_FITS_RESPONSE',validation_error=repr(exc))
                    break
                record['status']='API_UNAVAILABLE'
                if receipt['http_status'] not in (None,500,502,503,504):break
                if attempt==1:time.sleep(1)
            records.append(record)
    summary={'status':'IMAGE_ACQUISITION_COMPLETE_REVIEW_PENDING' if selected else 'NO_EXACT_SOURCE_CUTOUT_REQUESTS',
             'all_trigger_rows':len(associations),'unique_exact_source_ids':len(order),'selected_source_ids':len(selected),
             'products_requested':len(records),'products_available':sum(r['status']=='FITS_AVAILABLE' for r in records),
             'charged_payload_bytes':charged,'source_ids_omitted_by_bound':len(order[30:]),
             'trigger_rows_without_unique_source_cutout':len(plan['no_exact_source_or_ambiguous']),
             'physical_origin_classifications':0,'image_morphology_review_performed':False,'records':records}
    (OUT/'ACQUISITION.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='records'},indent=2))

if __name__=='__main__':main()
