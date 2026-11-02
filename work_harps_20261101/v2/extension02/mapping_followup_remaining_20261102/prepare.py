from pathlib import Path
import json,hashlib,datetime,collections
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];BASE=ROOT/'work_harps_20261101';V2=BASE/'v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
state_path=V2/'extension02/raw_followup_batch04/CONTINUATION_STATE.json';state=read(state_path)
prior=V2/'extension02/mapping_followup_20261102/RAW_REFERENCE_SUMMARY.json';done=read(prior)
assert done['status']=='COMPLETE_DIAGNOSTIC_ONLY_NO_RECLASSIFICATION' and done['orders']==72
records=state['followup_queues']['mapping_limited']['records'];remaining=[r for r in records if r['dp_id']!=done['dp_id']]
assert len(records)==35 and len(remaining)==34
archives=[]
for a in read(V2/'triage_batch02/INPUT_CHECKPOINTS.json')['parts']:archives.append(a)
archive_meta={a['filename']:a for a in state['input_archives']}
for a in read(V2/'extension02/raw_followup/checkpoints/RAW_INPUT_CHECKPOINTS.json')['parts']:
 archives.append(dict(a,**{k:v for k,v in archive_meta[a['filename']].items() if k not in ['bytes','sha256']}))
for a in state['input_archives']:
 if 'products' in a:archives.append(a)
queue=[];needed=collections.OrderedDict();hashes={str(state_path.relative_to(ROOT)):sha(state_path),str(prior.relative_to(ROOT)):sha(prior)}
for dp in dict.fromkeys(r['dp_id'] for r in remaining):
 rs=[r for r in remaining if r['dp_id']==dp];first=rs[0]
 if first['cohort']=='V2_first100':original=V2/'triage_batch02';reference=V2/'mapping43_followup/MAPPING_AUDIT.json'
 elif first['review_id']=='V2E2-0225':original=V2/'extension02/raw_followup';reference=original/'mapping_followup/MAPPING_AUDIT.json'
 else:original=V2/first['current_raw_batch'];reference=original/'FIVE_WINDOW_MAPPING_AUDIT.json'
 mapping=original/'NATIVE_MAPPING.json';manifest=original/'products/MANIFEST.json'
 for p in [mapping,manifest,reference]:hashes[str(p.relative_to(ROOT))]=sha(p)
 md=read(mapping);products=[r for r in read(manifest)['products'] if r['dp_id']==dp]
 assert len(products)==2 and {r['kind'] for r in products}=={'RAW','ANCILLARY'}
 prod=[]
 for r in products:
  match=[]
  for a in archives:
   for member in a.get('members',a.get('products',[])):
    if member.get('path',member.get('relative_path'))==r['relative_path']:
     assert member['sha256']==r['sha256'] and member['bytes']==r['bytes'];match.append(a)
  assert len(match)==1,(dp,r['relative_path'],len(match))
  a=match[0]
  if a['filename'] not in needed:
   needed[a['filename']]={k:a[k] for k in ['filename','bytes','sha256','library_file_id','file_id']};needed[a['filename']]['required_members']=[]
  needed[a['filename']]['required_members'].append({k:r[k] for k in ['relative_path','bytes','sha256','dp_id','kind']})
  prod.append({k:r[k] for k in ['dp_id','kind','raw_id','relative_path','bytes','sha256']})
 queue.append(dict(index=len(queue)+1,dp_id=dp,target=first['target'],review_ids=[r['review_id'] for r in rs],original_mapping=str(mapping.relative_to(ROOT)),reference_audit=str(reference.relative_to(ROOT)),products=prod,candidate_exclusion_ids=sorted(set(r['review_id'] for r in md['orders'] if r['dp_id']==dp))))
assert len(queue)==20 and len({r['relative_path'] for a in needed.values() for r in a['required_members']})==40
write('EXPOSURE_QUEUE.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_state=str(state_path.relative_to(ROOT)),source_state_sha256=sha(state_path),order='Exact stable M queue; first completed exposure skipped and retained as M; no rank by wavelength, strength, morphology or availability.',completed_exposure_not_repeated=done['dp_id'],records=34,exposures=20,queue=queue))
write('REQUIRED_INPUTS.json',dict(archives=list(needed.values()),archive_count=len(needed),archive_bytes=sum(a['bytes'] for a in needed.values()),required_products=40,required_product_bytes=sum(r['bytes'] for a in needed.values() for r in a['required_members']),raw_network_fetches_allowed=False,known_partial_or_remnant_members_allowed=False))
write('SOURCE_HASHES.json',hashes)
print(json.dumps({k:v for k,v in read(OUT/'REQUIRED_INPUTS.json').items() if k!='archives'},indent=2))
print('\n'.join(a['filename']+' '+a['library_file_id'] for a in needed.values()))
