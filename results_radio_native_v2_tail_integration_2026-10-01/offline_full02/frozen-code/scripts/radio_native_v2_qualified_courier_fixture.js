'use strict';
// Maximum-size OFFLINE mock/controller fixture for the unchanged portable caller.
// The actual local Node caller is a child; its entire lifetime is observed by
// this parent through /proc VmRSS/VmHWM, independent of the child's event loop.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto');
const MIB=1024*1024,LIMITS=Object.freeze({calls:64,request_bytes:48*MIB,response_bytes:64*MIB,seconds:600,rss_bytes:512*MIB}),
  SCHEMA='radio-native-v2-qualified-courier-offline-maximum-v1',
  REPO=path.resolve(__dirname,'..'),DEFAULT_SCOPE=path.resolve(REPO,'..','qualified-courier-offline-full02'),
  DEFAULT_EVIDENCE=path.join(REPO,'results_radio_native_v2_tail_integration_2026-10-01/offline_full02'),
  FILES=['scripts/radio_native_v2_qualified_courier_fixture.js','scripts/radio_native_v2_tool_courier_client.js',
    'scripts/radio_native_v2_qualified_tool_courier.js','scripts/radio_native_v2_broker_host.js',
    'scripts/radio_native_v2_caller_tail.py','scripts/radio_native_v2_local_transport.js',
    'scripts/radio_native_v2_local_courier.js','scripts/radio_native_v2_local_git.js','src/seti_repeater/__init__.py',
    'src/seti_repeater/empty_null_radio.py','src/seti_repeater/native_v2_transport_contract_radio.py'];
const ensure=(ok,message)=>{if(!ok)throw Error(message);},sha=data=>crypto.createHash('sha256').update(data).digest('hex'),
  quote=s=>"'"+s.replace(/'/g,"'\\''")+"'",delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function writeExclusive(filename,value){const fd=fs.openSync(filename,'wx',0o600);try{fs.writeFileSync(fd,typeof value==='string'?value:JSON.stringify(value,null,2)+'\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
function inventory(root){const rows=[];const visit=d=>{for(const entry of fs.readdirSync(d,{withFileTypes:true})){const filename=path.join(d,entry.name);
  if(entry.isDirectory())visit(filename);else {ensure(entry.isFile(),'Ordinary fixture entries required');const s=fs.statSync(filename);rows.push({path:path.relative(root,filename),bytes:s.size,allocated_bytes:s.blocks*512});}}};visit(root);
  return {files:rows.length,logical_bytes:rows.reduce((n,r)=>n+r.bytes,0),allocated_bytes:rows.reduce((n,r)=>n+r.allocated_bytes,0),rows};}
function procMemory(pid){const raw=fs.readFileSync('/proc/'+pid+'/status','utf8'),fields={};for(const line of raw.split('\n')){const a=line.split(':');fields[a[0]]=a.slice(1).join(':').trim();}
  return {at_epoch_ms:Date.now(),rss_bytes:Number((fields.VmRSS||'0').split(' ')[0])*1024,kernel_high_water_bytes:Number((fields.VmHWM||'0').split(' ')[0])*1024};}
function streamJson(filename,value){const fd=fs.openSync(filename,'wx',0o600);try{const put=s=>fs.writeSync(fd,s);const walk=v=>{
  if(Array.isArray(v)){put('[');v.forEach((x,i)=>{if(i)put(',');walk(x);});put(']');}
  else if(v&&typeof v==='object'){put('{');Object.keys(v).forEach((k,i)=>{if(i)put(',');put(JSON.stringify(k)+':');walk(v[k]);});put('}');}
  else put(JSON.stringify(v));};walk(value);put('\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
const PREPARE=String.raw`
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
`;
const VERIFY=String.raw`
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'frozen-code/src'))
from seti_repeater import native_v2_transport_contract_radio as c
value=json.loads((root/'caller-result.json').read_bytes()); rss=json.loads((root/'independent-rss-final.json').read_bytes())
ledger=c.RunTranscript();error=None;case=None
try:case=ledger.append(0,value['qualified']['client'],value['qualified']['persistence'],client_peak_rss_bytes=rss['client_peak_rss_bytes'])
except BaseException as failure:error=repr(failure)
receipt=ledger.receipt(); result={'schema':'radio-native-v2-offline-python-contract-verification-v1','status':'PASSED' if error is None else 'CLOSED_FAILED',
 'error':error,'run_transcript_stopped':ledger.stopped,'case_count':receipt['case_count'],'receipt_status':receipt['status'],
 'calls':receipt['calls'],'request_bytes':receipt['request_bytes'],'response_bytes':receipt['response_bytes'],'elapsed_seconds':receipt['elapsed_seconds'],
 'client_binding_sha256':c.client_binding_sha256(value['qualified']['client']),'tail_payload_sha256':hashlib.sha256(c.caller_tail_payload(value['qualified']['client'])).hexdigest(),
 'full_scratch_transcript_sha256':hashlib.sha256((root/'caller-result.json').read_bytes()).hexdigest(),'complete_envelopes_validated':error is None,
 'one_case_only':True,'eight_case_contract_complete':False,'execution_authorized':False,'scientific_execution_authorized':False,'automatic_retry':False}
with (root/'python-verification.json').open('x') as f:json.dump(result,f,sort_keys=True,separators=(',',':'));f.write('\n')
print(json.dumps({'status':result['status'],'error':error,'case_count':receipt['case_count']},sort_keys=True))
`;
async function caller(scope){
  const code=path.join(scope,'frozen-code'),h=require(path.join(code,'scripts/radio_native_v2_broker_host.js')),
    c=require(path.join(code,'scripts/radio_native_v2_tool_courier_client.js')),
    q=require(path.join(code,'scripts/radio_native_v2_qualified_tool_courier.js')),
    prepared=JSON.parse(fs.readFileSync(path.join(scope,'prepared.json'),'utf8')),
    startup={cmd:'offline mock controller maximum source-only fixture',max_output_tokens:400000,yield_time_ms:30000},
    started=Date.now(),checkpoints=[],seen=[],deliveries=[],readReceipts=[],identity='node-proc:'+fs.readlinkSync('/proc/self'),session=741;
  const sample=label=>{const r=process.memoryUsage();checkpoints.push({label,at_epoch_ms:Date.now(),rss_bytes:r.rss,heap_used_bytes:r.heapUsed,external_bytes:r.external});};sample('caller_entry');
  writeExclusive(path.join(scope,'caller-start.json'),{identity,pid:process.pid,proc_pid:Number(fs.readlinkSync('/proc/self')),started_at_epoch_ms:started});
  const argsFor=operation=>operation==='fetch'?{url:'https://api.github.com/repos/andersenmartin-blip/setisearch/git/ref/heads/m43-support-qualification'}:
    operation==='create_commit'?{repository_full_name:'andersenmartin-blip/setisearch',parent_sha:'a'.repeat(40),tree_sha:'b'.repeat(40),message:'Offline maximum-size fixture; no public mutation'}:
    {repository_full_name:'andersenmartin-blip/setisearch',branch_name:'m43-support-qualification',sha:'c'.repeat(40),force:false};
  const frame=ordinal=>({schema:c.CONTROLLER_SCHEMA,kind:'request',ordinal,tool:'mcp__codex_apps__github_'+c.CLIENT_SEQUENCE[ordinal],
    arguments:ordinal===1?null:argsFor(c.CLIENT_SEQUENCE[ordinal]),request_view:ordinal===1?prepared.request_view:null,
    reads:ordinal===1?prepared.reads:[],delivery_request_reserved_bytes:2*c.CLIENT_CORE['mcp__codex_apps__github_'+c.CLIENT_SEQUENCE[ordinal]]+
      (ordinal===1?prepared.reads.length*(2*8192+1024):0)+2*128*1024+8192,
    worker_deadline_epoch_ms:started+LIMITS.seconds*1000,deadline_ms:LIMITS.seconds*1000,automatic_retry:false});
  const output=ordinal=>({chunk_id:'offline-controller-'+ordinal,wall_time_seconds:0,session_id:session,
    original_token_count:100,output:JSON.stringify(frame(ordinal))+'\n',offline_fixture:true});
  const readByCommand=new Map(prepared.reads.map(row=>[row.arguments.cmd,row]));
  let tailCount=0,connectorOrdinal=0,deliveryOrdinal=0,sourceReads=0;
  const execLocal=args=>new Promise((resolve,reject)=>{const at=Date.now();cp.execFile('/bin/bash',['--noprofile','--norc','-c',args.cmd],
    {encoding:'utf8',maxBuffer:2*MIB,timeout:Math.max(1,Math.min(120000,started+600000-Date.now())),env:{PATH:'/usr/bin:/bin',LANG:'C',LC_ALL:'C'}},
    (error,stdout,stderr)=>{if(error)return reject(Error('Real local Python execution failed without retry: '+String(error)));ensure(stderr==='','Real local Python helper stderr must be empty');
      resolve({chunk_id:'offline-local-python-'+(readByCommand.get(args.cmd)?.ordinal??'tail'),wall_time_seconds:(Date.now()-at)/1000,
        exit_code:0,original_token_count:Math.ceil(Buffer.byteLength(stdout)/4),output:stdout,offline_fixture:true});});});
  const tools={exec_command:async args=>{
    if(args.cmd===startup.cmd){seen.push({kind:'mock_controller_start'});sample('controller_start');return output(0);}
    const plan=readByCommand.get(args.cmd);
    if(plan){ensure(JSON.stringify(args)===JSON.stringify(plan.arguments),'Frozen source reader exact arguments changed');const raw=await execLocal(args);
      sourceReads++;const json=JSON.stringify(raw);readReceipts.push({ordinal:plan.ordinal,path:plan.path,offset:plan.offset,bytes:plan.bytes,
        source_sha256:plan.source_sha256,envelope_entries:Object.entries(raw).map(([k,v])=>[k,k==='output'?null:v]),
        envelope_bytes:Buffer.byteLength(json),envelope_sha256:sha(json),output_sha256:sha(raw.output)});sample('source_read_'+plan.ordinal);return raw;}
    ensure(args.cmd.includes(quote(path.join(code,'scripts/radio_native_v2_caller_tail.py'))),'Only the pinned real tail saver may follow the fixture source readers');
    ensure(tailCount++===0,'Exactly one real local caller-tail saver; no retry');const raw=await execLocal(args);sample('tail_saved_and_reopened');return raw;
  },write_stdin:async args=>{
    ensure(args.session_id===session&&args.yield_time_ms===30000&&args.chars!=='' ,'Exact offline six-delivery shape required');
    const body=JSON.parse(args.chars);ensure(body.ordinal===deliveryOrdinal&&body.automatic_retry===false,'Exact ordered mock controller ingress required');
    ensure(body.read_descriptors.length===(deliveryOrdinal===1?prepared.reads.length:0),'Exact source extraction descriptors required');
    deliveries.push({ordinal:body.ordinal,request_bytes:Buffer.byteLength(JSON.stringify({tool:'write_stdin',arguments:args})),
      read_descriptors:body.read_descriptors,start_raw_present:body.start_raw!==null,previous_delivery_raw_present:body.previous_delivery_raw!==null});
    deliveryOrdinal++;sample('delivery_'+body.ordinal);if(deliveryOrdinal<6)return output(deliveryOrdinal);
    return {chunk_id:'offline-terminal',wall_time_seconds:0,exit_code:0,original_token_count:32,offline_fixture:true,
      output:JSON.stringify({schema:c.CONTROLLER_SCHEMA,kind:'terminal',status:'SINGLE_CASE_COMPONENT_ONLY',fixture_only:true})+'\n'};
  }};
  for(const tool of Object.keys(c.CLIENT_CORE))tools[tool]=async args=>{
    ensure(tool==='mcp__codex_apps__github_'+c.CLIENT_SEQUENCE[connectorOrdinal],'Exact six ordered mock connectors required');
    if(tool.endsWith('_create_tree')){ensure(args.tree_elements.length===28,'Maximum archive must contain 28 files');let bytes=0;
      for(const row of args.tree_elements){const pin=prepared.files[row.path];ensure(pin&&Buffer.byteLength(row.content)===pin.bytes&&sha(row.content)===pin.sha256,'Actual reassembled archive differs from frozen byte pins');bytes+=pin.bytes;}
      ensure(bytes===36875057,'Exact maximum 36,875,057-byte ASCII archive required');}
    const payload=tool.endsWith('_fetch')?{ref:'refs/heads/m43-support-qualification',object:{type:'commit',sha:connectorOrdinal<4?'a'.repeat(40):'c'.repeat(40)}}:
      tool.endsWith('_create_tree')?{sha:'b'.repeat(40)}:tool.endsWith('_create_commit')?{sha:'c'.repeat(40)}:{success:true};
    const raw={content:[{type:'text',text:JSON.stringify(payload)}],structuredContent:payload,_meta:{offline_fixture:true},isError:false};
    seen.push({kind:'mock_connector',ordinal:connectorOrdinal,tool,request_sha256:sha(JSON.stringify({tool,arguments:args})),response_sha256:sha(JSON.stringify(raw))});
    connectorOrdinal++;sample('connector_'+(connectorOrdinal-1));return raw;
  };
  const independentRss=async interval=>{
    sample('wrapper_interval_complete');writeExclusive(path.join(scope,'rss-observation-request.json'),interval);
    const deadline=Date.now()+30000;while(!fs.existsSync(path.join(scope,'rss-observation.json'))&&Date.now()<deadline)await delay(10);
    ensure(fs.existsSync(path.join(scope,'rss-observation.json')),'Independent parent procfs observation timed out');return JSON.parse(fs.readFileSync(path.join(scope,'rss-observation.json'),'utf8'));
  };
  const qualified=await q.runQualifiedToolCourier(tools,{hostLibrary:h,clientLibrary:c,python:prepared.python,startup_arguments:startup,
    tail_helper_path:path.join(code,'scripts/radio_native_v2_caller_tail.py'),tail_helper_sha256:sha(fs.readFileSync(path.join(code,'scripts/radio_native_v2_caller_tail.py'))),
    caller_tail_path:path.join(scope,'caller-tail.json'),production:false,read_actual_client_rss:independentRss,
    onProgress:event=>sample('progress_'+event.kind+'_'+(event.ordinal??''))});sample('qualified_wrapper_returned');
  // Stream each retained scalar separately so evidence writing does not add a
  // second enormous serialization of the complete client transcript.
  streamJson(path.join(scope,'caller-result.json'),{schema:SCHEMA,qualified,seen,deliveries,read_receipts:readReceipts});sample('full_scratch_transcript_written');
  const result={schema:SCHEMA,status:qualified.status,source_reads:sourceReads,mock_connector_operations:connectorOrdinal,mock_delivery_operations:deliveryOrdinal,
    real_local_tail_saver_calls:tailCount,process_memory_usage_checkpoints:checkpoints,
    process_memory_usage_peak_sampled_rss_bytes:Math.max(...checkpoints.map(r=>r.rss_bytes)),process_resource_usage_max_rss_bytes:process.resourceUsage().maxRSS*1024,
    caller_identity:identity,caller_started_at_epoch_ms:started,caller_finished_at_epoch_ms:Date.now(),elapsed_seconds:(Date.now()-started)/1000,
    combined_usage:qualified.combined_usage,tail_record:qualified.tail_record,persistence:qualified.persistence,client_rss_observation:qualified.client_rss_observation,
    client_status:qualified.client?.status,client_reason:qualified.client?.reason,read_receipts:readReceipts,deliveries,seen,
    execution_authorized:false,scientific_execution_authorized:false,automatic_retry:false};
  writeExclusive(path.join(scope,'caller-summary.json'),result);process.stdout.write(JSON.stringify({status:result.status,source_reads:sourceReads,mock_connectors:connectorOrdinal,mock_deliveries:deliveryOrdinal})+'\n');
}
async function runOfflineFixture({scope=DEFAULT_SCOPE,evidence=DEFAULT_EVIDENCE,python=process.env.CODEX_PRIMARY_RUNTIME_PYTHON||'/usr/bin/python3'}={}){
  ensure(path.isAbsolute(scope)&&path.isAbsolute(evidence),'Absolute fresh scopes required');ensure(!fs.existsSync(scope)&&!fs.existsSync(evidence),'Fresh exclusive fixture/evidence scopes required; no retry or overwrite');
  const started=Date.now();fs.mkdirSync(scope,{mode:0o700,recursive:true});fs.mkdirSync(evidence,{mode:0o700,recursive:true});
  const pins={};for(const relative of FILES){const raw=fs.readFileSync(path.join(REPO,relative)),destination=path.join(scope,'frozen-code',relative);fs.mkdirSync(path.dirname(destination),{recursive:true});writeExclusive(destination,raw.toString('utf8'));pins[relative]={bytes:raw.length,sha256:sha(raw)};}
  const preparedProcess=cp.spawnSync(python,['-I','-S','-B','-c',PREPARE,scope,python],{encoding:'utf8',maxBuffer:MIB,timeout:60000});
  ensure(preparedProcess.status===0&&!preparedProcess.error,'Deterministic maximum preparation failed: '+preparedProcess.stderr);
  const prepared=JSON.parse(fs.readFileSync(path.join(scope,'prepared.json'),'utf8')),
    frozenTransport=require(path.join(scope,'frozen-code/scripts/radio_native_v2_local_transport.js')),
    planLedger=new frozenTransport.SharedLedger();planLedger.beginCase(0);
  const actualHostPlan=frozenTransport.makeCourierReadPlan(prepared.request_view,{python,ledger:planLedger}),
    fields=['ordinal','tool','arguments','path','offset','bytes','source_sha256','output_sha256','response_reserved_bytes'];
  ensure(actualHostPlan.length===prepared.reads.length,'Actual frozen host source-plan count differs');
  for(let i=0;i<actualHostPlan.length;i++)for(const key of fields)
    ensure(JSON.stringify(actualHostPlan[i][key])===JSON.stringify(prepared.reads[i][key]),'Actual frozen host source-plan field differs: '+key);
  writeExclusive(path.join(evidence,'source-pins-and-read-plan.json'),{...prepared,scope:undefined,source_read_plan_independently_matched_frozen_local_host:true});writeExclusive(path.join(evidence,'code-pins.json'),pins);
  const stdout=fs.openSync(path.join(scope,'caller-stdout.log'),'wx'),stderr=fs.openSync(path.join(scope,'caller-stderr.log'),'wx'),observerIdentity='node-proc:'+fs.readlinkSync('/proc/self');
  const child=cp.spawn(process.execPath,[path.join(scope,'frozen-code/scripts/radio_native_v2_qualified_courier_fixture.js'),'--caller',scope],{cwd:scope,env:{PATH:'/usr/bin:/bin',LANG:'C',LC_ALL:'C'},stdio:['ignore',stdout,stderr]});
  fs.closeSync(stdout);fs.closeSync(stderr);let done=false,exitCode=null,samples=[],maxRss=0,maxHwm=0,observationWritten=false,watchdogFailure=null,actualProcPid=null;
  const observerStarted=Date.now();child.on('close',code=>{done=true;exitCode=code;});
  while(!done){
    const startPath=path.join(scope,'caller-start.json');if(actualProcPid===null&&fs.existsSync(startPath))actualProcPid=JSON.parse(fs.readFileSync(startPath,'utf8')).proc_pid;
    try{if(actualProcPid===null)throw Object.assign(Error('Awaiting caller proc identity'),{code:'ENOENT'});const r=procMemory(actualProcPid);samples.push(r);maxRss=Math.max(maxRss,r.rss_bytes);maxHwm=Math.max(maxHwm,r.kernel_high_water_bytes);}catch(error){if(error.code!=='ENOENT'&&error.code!=='ESRCH')throw error;}
    const requestPath=path.join(scope,'rss-observation-request.json');
    if(!observationWritten&&fs.existsSync(requestPath)){
      const request=JSON.parse(fs.readFileSync(requestPath,'utf8')),end=Date.now();
      writeExclusive(path.join(scope,'rss-observation.json'),{schema:'radio-native-v2-independent-client-rss-v1',measured:true,
        client_peak_rss_bytes:Math.max(maxRss,maxHwm),observer_source:'independent_procfs',caller_runtime_identity:'node-proc:'+actualProcPid,
        observer_runtime_identity:observerIdentity,interval_start_epoch_ms:observerStarted,interval_end_epoch_ms:end,
        procfs_sample_count:samples.length,procfs_sampled_peak_rss_bytes:maxRss,procfs_kernel_vm_hwm_bytes:maxHwm,client_sha256:request.client_sha256});observationWritten=true;
    }
    if(Date.now()-observerStarted>LIMITS.seconds*1000){watchdogFailure='Whole actual local Node caller exceeded original 600-second interval';child.kill('SIGKILL');}
    await delay(5);
  }
  const rssFinal={schema:'radio-native-v2-independent-client-rss-final-v1',observer_source:'independent_procfs',caller_runtime_identity:'node-proc:'+actualProcPid,
    observer_runtime_identity:observerIdentity,interval_start_epoch_ms:observerStarted,interval_end_epoch_ms:Date.now(),sample_count:samples.length,
    sampled_peak_rss_bytes:maxRss,kernel_vm_hwm_bytes:maxHwm,client_peak_rss_bytes:Math.max(maxRss,maxHwm),exit_code:exitCode,
    includes_entire_actual_local_node_caller_lifetime:true,measurements:samples};writeExclusive(path.join(scope,'independent-rss-final.json'),rssFinal);
  let verification=null,verificationFailure=null,summary=null;
  if(fs.existsSync(path.join(scope,'caller-summary.json')))summary=JSON.parse(fs.readFileSync(path.join(scope,'caller-summary.json'),'utf8'));
  if(fs.existsSync(path.join(scope,'caller-result.json'))){const verified=cp.spawnSync(python,['-I','-S','-B','-c',VERIFY,scope],{encoding:'utf8',maxBuffer:MIB,timeout:120000});
    if(verified.status===0&&!verified.error)verification=JSON.parse(fs.readFileSync(path.join(scope,'python-verification.json'),'utf8'));
    else verificationFailure={error:String(verified.error||'Python verification subprocess failed'),stderr:verified.stderr.slice(-4096),exit_code:verified.status};}
  const capFailures=[];
  if(maxRss>LIMITS.rss_bytes||maxHwm>LIMITS.rss_bytes||summary?.process_resource_usage_max_rss_bytes>LIMITS.rss_bytes)capFailures.push('Original 512MiB actual local Node caller RSS cap exceeded');
  if(summary?.elapsed_seconds>LIMITS.seconds)capFailures.push('Original 600-second whole caller cap exceeded');
  if(verification?.calls>LIMITS.calls)capFailures.push('Original 64-call conservative case cap exceeded');
  if(verification?.request_bytes>LIMITS.request_bytes)capFailures.push('Original 48MiB case request cap exceeded');
  if(verification?.response_bytes>LIMITS.response_bytes)capFailures.push('Original 64MiB case response cap exceeded');
  const passed=summary&&exitCode===0&&!watchdogFailure&&!verificationFailure&&verification?.status==='PASSED'&&capFailures.length===0&&
    summary.source_reads===prepared.reads.length&&summary.mock_connector_operations===6&&summary.mock_delivery_operations===6&&summary.real_local_tail_saver_calls===1;
  const result={schema:SCHEMA,mode:'OFFLINE_MOCK_CONNECTOR_CONTROLLER_SHAPE',status:passed?'PASSED':'CLOSED_FAILED',
    source_bytes:prepared.source_bytes,archive_bytes:prepared.archive_bytes,archive_files:prepared.archive_files,source_fragment_reads:prepared.reads.length,conservative_source_read_fragment_ceiling:39,source_read_plan_independently_matched_frozen_local_host:true,
    caller:summary,independent_caller_rss:{...rssFinal,measurements:undefined},python_contract_verification:verification,
    verification_failure:verificationFailure,watchdog_failure:watchdogFailure,cap_failures:capFailures,original_caps:LIMITS,
    storage_before_summary:{scratch:inventory(scope),publishable_evidence:inventory(evidence)},elapsed_seconds:(Date.now()-started)/1000,
    actual_functions_sdk_calls:0,actual_connector_calls:0,network_fetches:0,actual_git_processes:0,real_public_github_mutations:0,
    native_case_reservations:0,native_case_executions:0,scientific_cases_run:0,rng_draws:0,telescope_reads:0,external_messages_sent:0,
    automatic_retry:false,execution_authorized:false,reservation_authorized:false,scientific_execution_authorized:false,live_transport_qualified:false,
    limitations:['Controller and six connector exchanges are explicitly offline mocks; no actual SDK or live qualification.',
      'Only source readers and the exclusive Python caller-tail saver execute real local processes.',
      'Controller ingress reserves the same source-descriptor and reply envelope formula as the frozen local ToolCourier; actual controller execution remains mocked.',
      'Large source replies are reproducible from the scratch frozen request and complete source/read-envelope descriptors; published evidence does not contain their raw body bytes.',
      'One accepted offline case leaves the eight-case shared RunTranscript receipt INCOMPLETE.']};
  writeExclusive(path.join(evidence,'measured-summary.json'),result);
  if(fs.existsSync(path.join(scope,'caller-tail.json')))fs.copyFileSync(path.join(scope,'caller-tail.json'),path.join(evidence,'caller-tail.json'),fs.constants.COPYFILE_EXCL);
  fs.copyFileSync(path.join(scope,'independent-rss-final.json'),path.join(evidence,'independent-rss-final.json'),fs.constants.COPYFILE_EXCL);
  writeExclusive(path.join(evidence,'storage-inventory.json'),{scratch:inventory(scope),publishable_evidence:inventory(evidence),final_inventory_file_excluded:true});
  return result;
}
module.exports={SCHEMA,LIMITS,runOfflineFixture,inventory};
if(require.main===module){const arguments_=process.argv.slice(2);let promise;
  if(arguments_[0]==='--caller'){ensure(arguments_.length===2,'--caller requires exact scope');promise=caller(path.resolve(arguments_[1]));}
  else{ensure(arguments_.length===0||arguments_.length===2,'Usage: node fixture.js [fresh-scratch-scope fresh-evidence-scope]');promise=runOfflineFixture(arguments_.length?{scope:path.resolve(arguments_[0]),evidence:path.resolve(arguments_[1])}:{}).then(r=>process.stdout.write(JSON.stringify({status:r.status,archive_bytes:r.archive_bytes,
    source_fragment_reads:r.source_fragment_reads,independent_peak_rss_bytes:r.independent_caller_rss.client_peak_rss_bytes,
    process_max_rss_bytes:r.caller?.process_resource_usage_max_rss_bytes,python_contract_status:r.python_contract_verification?.status,cap_failures:r.cap_failures,result_path:path.join(arguments_[1]||DEFAULT_EVIDENCE,'measured-summary.json')})+'\n'));}
  promise.catch(error=>{process.stderr.write(String(error)+'\n');process.exitCode=1;});}
