
import base64,hashlib,json,os,sys
from pathlib import Path
root=Path(sys.argv[1]); python=sys.argv[2]
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
hash=lambda b:hashlib.sha256(b).hexdigest()
def write(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
source_bytes=26*1024*1024;domain=b'seti-local-transport-sha256-counter-v1\0'+(0).to_bytes(8,'big')
buffer=bytearray()
for counter in range((source_bytes+31)//32):buffer.extend(hashlib.sha256(domain+counter.to_bytes(8,'big')).digest())
source=bytes(buffer[:source_bytes]);del buffer
write(root/'deterministic-source.bin',source)
prefix='results_radio_native_v2_tail_integration_20261001a/offline_full02/case00-fixed'
files={}; chunks=[]
for i,start in enumerate(range(0,len(source),1024*1024)):
 raw=source[start:start+1024*1024]; encoded=base64.b64encode(raw); p=prefix+f'/chunk{i:04d}.b64'
 files[p]=encoded;chunks.append({'path':p,'stored_bytes':len(encoded),'stored_sha256':hash(encoded)})
manifest={'schema':'radio-native-v2-offline-maximum-archive-v1','fixture_only':True,'source_bytes':len(source),
 'source_sha256':hash(source),'source_mode':'sha256-counter-deterministic-no-rng','chunk_bytes':1024*1024,
 'chunks':chunks,'execution_authorized':False,'scientific_execution_authorized':False,'rng_draws':0,'telescope_reads':0,'padding':''}
manifest['padding']='x'*(524288-len(canon(manifest))); manifest_bytes=canon(manifest)
assert len(manifest_bytes)==524288
files[prefix+'/manifest.json']=manifest_bytes; files[prefix+'/HEAD']=hash(manifest_bytes).encode()+b'\n'
assert len(files)==28 and sum(map(len,files.values()))==36875057
params={'base_tree_sha':'a'*40,'repository_full_name':'andersenmartin-blip/setisearch',
 'tree_elements':[{'content':data.decode('ascii'),'mode':'100644','path':p,'type':'blob'} for p,data in sorted(files.items())]}
params_json=canon(params); packet={'automatic_retry':False,'fixture_only':True,'kind':'offline-worker-request','ordinal':1,'params':params,
 'schema':'radio-native-v2-offline-frozen-request-v1','tool':'mcp__codex_apps__github_create_tree'}
wire=canon(packet); null=canon({**packet,'params':None}); marker=b'"params":null'; at=null.index(marker)
assert null.count(marker)==1
prefix_bytes=null[:at]+b'"params":'; suffix_bytes=null[at+len(marker):]
assert wire==prefix_bytes+params_json+suffix_bytes
source_path=root/'store/items/request-000001/part';write(source_path,wire); source_path.chmod(0o400)
request_prefix='{"tool":"mcp__codex_apps__github_create_tree","arguments":'; request_suffix='}'
request=request_prefix.encode()+params_json+request_suffix.encode()
view={'schema':'radio-native-v2-existing-request-view-v1','path':str(source_path),'source_bytes':len(wire),'source_sha256':hash(wire),
 'offset':len(prefix_bytes),'bytes':len(params_json),'sha256':hash(params_json),'request_prefix':request_prefix,
 'request_suffix':request_suffix,'request_bytes':len(request),'request_sha256':hash(request)}
script='import os,sys; f=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW); n=int(sys.argv[3]); b=os.pread(f,n,int(sys.argv[2])); assert len(b)==n; sys.stdout.buffer.write(b); os.close(f)'
q=lambda s:"'"+s.replace("'","'\\''")+"'"
reads=[]
for rel in range(0,len(params_json),1024*1024-65536):
 raw=params_json[rel:rel+1024*1024-65536]; offset=len(prefix_bytes)+rel
 args={'cmd':q(python)+' -I -S -B -c '+q(script)+' '+q(str(source_path))+' '+str(offset)+' '+str(len(raw)),
 'max_output_tokens':400000,'yield_time_ms':1000}
 reads.append({'ordinal':len(reads),'tool':'exec_command','arguments':args,'path':str(source_path),'offset':offset,'bytes':len(raw),
 'source_sha256':hash(wire),'output_sha256':hash(raw),'response_reserved_bytes':len(canon({'output':raw.decode('ascii')}))+8192})
assert len(reads)==38
write(root/'prepared.json',canon({'schema':'radio-native-v2-offline-maximum-prepared-v1','python':python,'scope':str(root),
 'source_bytes':len(source),'source_sha256':hash(source),'archive_bytes':sum(map(len,files.values())),'archive_files':len(files),'actual_source_read_fragments':len(reads),'conservative_source_read_fragment_ceiling':39,
 'manifest_bytes':len(manifest_bytes),'request_view':view,'reads':reads,'files':{p:{'bytes':len(data),'sha256':hash(data)} for p,data in sorted(files.items())}}))
