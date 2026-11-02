"""Reconcile archived identities and coordinate bounds from saved metadata; no pixel arrays."""
import datetime,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
B=REPO/'work_harps_20261101/v2/extension02/raw_followup_batch03'
DP='ADP.2023-02-23T01:01:36.791';RAW='HARPS.2023-02-22T07:40:53.531';ANC='ADP.2023-02-23T01:01:36.792';CID='V2E2-0235'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def ck(k,v):checks.append({'check':k,'pass':bool(v)})
manifest=read(B/'products/MANIFEST.json');native=read(B/'NATIVE_MAPPING.json');local=read(B/'LOCAL_TRACE_AUDIT.json');five=read(B/'FIVE_WINDOW_MAPPING_AUDIT.json');fiber=read(B/'FIBER_INVENTORY.json');archives=read(B/'checkpoints/INPUT_ARCHIVES.json');evidence=read(B/'EVIDENCE_ARCHIVE.json')
pair=[x for x in manifest['products'] if x['dp_id']==DP];ck('one raw and one ancillary product',len(pair)==2 and {x['kind'] for x in pair}=={'RAW','ANCILLARY'})
r=next(x for x in pair if x['kind']=='RAW');a=next(x for x in pair if x['kind']=='ANCILLARY')
ck('exact DP raw ancillary relation',r['archive_id']==RAW and a['archive_id']==ANC and r['raw_id']==a['raw_id']==RAW and all(x['target']=='HD122640' for x in pair))
ck('single downloaded instance no duplicated raw exposure',len([x for x in manifest['products'] if x['archive_id']==RAW])==1 and {x['dp_id'] for x in manifest['products'] if x['raw_id']==RAW}=={DP})
ck('verified complete original transfer identities',all(x['status']=='DOWNLOADED' and x['metadata_status']=='VERIFIED' and x['bytes']==x['advertised_bytes'] and x['metadata_check']=='PASS_RAW_OR_NATIVE_ID_DATE_AND_CONTAINER' for x in pair))
ck('science and date bindings',r['source_science_sha256']==a['source_science_sha256']=='a2ceff82da6696b30491b403219c15e920192fda7e13c623fcb6f5fdd41f052c' and r['source_date_obs']==a['source_date_obs']=='2023-02-22T07:40:53.531')
spec=next(x for x in native['spectra'] if x['dp_id']==DP);event=next(x for x in native['events'] if x['review_id']==CID);order=[x for x in native['orders'] if x['review_id']==CID]
ck('single event covering order50',len(order)==1 and order[0]['order']==50 and event['covering_orders']==[50]);o=order[0]
ck('native metadata links source product hashes',spec['raw_sha256']==r['sha256'] and spec['ancillary_sha256']==a['sha256'] and spec['date_obs']==r['source_date_obs'])
orientation={k:spec['grid_best'][k] for k in ['row_flip','column_flip','argument_flip']}
ck('fixed original orientation',orientation=={'row_flip':True,'column_flip':False,'argument_flip':True})
ck('saved coordinate relation',o['native_pixel']==956 and o['raw_row']==4095-o['native_pixel']==3139 and o['raw_column']==2323.7701943175816)
ck('existing event full and mapped',o['status']=='EXTRACTED' and o['mapping_verified'] and event['mapping_supported'] and not event['edge_truncated_orders'] and not event['unsupported_orders'])
k=o['native_pixel'];row=o['raw_row'];col=round(o['raw_column'])
wide={'rows':[row-15,row+16],'stitched_columns':[col-16,col+17],'physical_chip':2,'chip_columns':[col-16-2048+50,col+17-2048+50]}
inner={'rows':[row-10,row+11],'stitched_columns':[col-12,col+13],'nested_wide_indices':[[5,26],[4,29]]}
ck('wide window within one chip and detector',0<=wide['rows'][0]<wide['rows'][1]<=4096 and 2048<=wide['stitched_columns'][0]<wide['stitched_columns'][1]<=4096 and 50<=wide['chip_columns'][0]<wide['chip_columns'][1]<=2098)
lt=next(x for x in local['orders'] if x['review_id']==CID);controls=[]
for w in lt['windows']:
 lo,hi=w['relative_interval_half_open'];lo+=k;hi+=k
 controls.append({'native_half_open':[lo,hi],'raw_rows_half_open':[4096-hi,4096-lo],'samples_in_saved_metadata':w['samples']})
ck('two complete local control windows',len(controls)==2 and [x['native_half_open'] for x in controls]==[[676,876],[1037,1237]] and all(x['samples_in_saved_metadata']==200 for x in controls) and lt['local_mapping_usable'])
ck('native reverse-direction mapping exact', [x['raw_rows_half_open'] for x in controls]==[[3220,3420],[2859,3059]])
fo=next(x for x in five['reference_audit'] if x['dp_id']==DP and x['order']==50)
ck('all five saved trace windows supported',fo['valid_reference_windows']==5 and fo['mapping_supported'] and fo['windows_within_one_pixel']==5)
window=next(x for x in fo['windows'] if x['pixel_interval_half_open']==[896,1536]);ck('candidate-excluded window population',window['samples']==640-len(set(range(896,1536))&set(range(k-80,k+81)))==499 and window['excluded_ids']==[CID])
f=next(x for x in fiber if x['dp_id']==DP);am=[x for x in f['members'] if x.endswith('_e2ds_A.fits')]
ck('unique native fiberA exact raw',len(am)==1 and am[0]==spec['native_member'] and Path(am[0]).name==RAW+'_e2ds_A.fits' and f['fiber_headers']['A']['member']==am[0])
ck('fiberB calibration cannot be sky control',f['raw_context']['ESO DPR TYPE']=='STAR,WAVE,NONE' and f['raw_context']['ESO INS OPTI6 NAME']=='FP' and f['independent_sky_fiber_available'] is False)
pack=[x for x in archives['archives'] if any(z['dp_id']==DP for z in x['products'])];ck('one archived input package',len(pack)==1);pack=pack[0]
for x in pair:
 z=[z for z in pack['products'] if z['archive_id']==x['archive_id']];ck('archived exact member '+x['kind'],len(z)==1 and z[0]['relative_path']==x['relative_path'] and z[0]['sha256']==x['sha256'] and z[0]['bytes']==x['bytes'])
ck('input package known identity',pack['filename']=='SETI_HARPS_RAW_BATCH03_INPUTS_PART8_2026-11-01.zip' and pack['sha256']=='f950ce0c99069c87f792f084237e5971dfba6b9480231cfbc34af2d5b2aa6096' and pack['bytes']==99302855)
cut=next(x for x in evidence['members'] if x['path']==o['cutout']);ref=next(x for x in evidence['members'] if x['path']==spec['reference_grid'])
ck('cutout archived hash matches native mapping',cut['sha256']==o['cutout_sha256']=='d70580a306b873a49e585bc66750bf12ad838306c54c40915a8d9fe7bc812c51' and cut['bytes']==8473)
extract=(B/'extract_native.py').read_text();registration=(B/'registration.py').read_text()
ck('source declares zero-based array coordinates','zero-based native order and wavelength-array pixel' in registration)
ck('source raw trim stitch no transpose','np.hstack([hdus[1].data[:, 50:2098], hdus[2].data[:, 50:2098]])' in extract)
ck('source cutout convention exact','raw[raw_row - 15:raw_row + 16, rounded_column - 16:rounded_column + 17]' in extract and 'cutout[5:26, 4:29]' in extract and 'native_slice = slice(k - 20, k + 21)' in extract)
names=['products/MANIFEST.json','NATIVE_MAPPING.json','LOCAL_TRACE_AUDIT.json','FIVE_WINDOW_MAPPING_AUDIT.json','FIBER_INVENTORY.json','checkpoints/INPUT_ARCHIVES.json','EVIDENCE_ARCHIVE.json','EVIDENCE_PARTS.json','PLAN.json','extract_native.py','registration.py','mapping_quality.py','local_registration.py','SELECTED_EVENTS.csv','SELECTED_EXPOSURES.csv']
sources={str((B/n).relative_to(REPO)):{'sha256':sha(B/n),'bytes':(B/n).stat().st_size} for n in names}
baseline=read(HERE.parent/'BASELINE_VERIFICATION.json');diff=subprocess.run(['git','diff','--name-only',baseline['baseline_commit'],'--',str(B.relative_to(REPO))],cwd=REPO,capture_output=True,text=True,check=True).stdout.splitlines();ck('old batch03 tracked files unchanged',not diff)
out={'schema':'HARPS_SPATIAL0235_INPUT_METADATA_AUDIT_V1','status':'PASS_METADATA_ONLY_PENDING_RESTORED_BYTES' if all(x['pass'] for x in checks) else 'FAIL','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline_commit':baseline['baseline_commit'],'script_sha256':sha(Path(__file__)),'checks':checks,'check_count':len(checks),'inputs':{x['kind']:{k:x[k] for k in ['archive_id','relative_path','sha256','bytes','source_science_sha256']} for x in pair},'archive':{k:pack[k] for k in ['filename','sha256','bytes']},'cutout':cut,'reference_grid':ref,'native_member':am[0],'axis_contract':{'index_origin':0,'native_array':'[zero-based order, zero-based dispersion pixel]','raw_stitched':'[detector row, cross-dispersion column]; hstack(chip1[:,50:2098], chip2[:,50:2098])','native_dispersion_to_raw_row':'raw_row = 4095 - native_pixel','trace_argument':'4095 - native_pixel, no +1 offset','column_flip':False,'chip2_column':'stitched_column - 2048 + 50','event_center':{'native_order':50,'native_pixel':956,'raw_row':3139,'raw_stitched_column':o['raw_column'],'chip2_physical_column':o['raw_column']-2048+50},'old_wide_cutout_half_open':wide,'old_inner_cutout_half_open':inner,'native_snippet_half_open':[k-20,k+21],'local_controls':controls,'candidate_exclusion_native_inclusive':[k-80,k+80]},'coverage_limit':'The saved 31x33 event cutout does not contain flanking trace-control rows. Fresh bounded extraction requires the exact full raw input after release. No new trace fit or orientation selection is justified.','fiberB_role':'FP simultaneous-calibration context, not an independent sky fiber.','scientific_sources_preserved':sources,'network_requests':0,'raw_or_native_array_values_read':0,'new_science_calculations':0,'scope':'Saved identity/geometry metadata and source conventions; no local flux, spatial morphology, or origin assessment.'}
(HERE/'INPUT_METADATA_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'checks':len(checks),'failed':[x['check'] for x in checks if not x['pass']]}));assert all(x['pass'] for x in checks)
