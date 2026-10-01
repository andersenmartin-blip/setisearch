'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),
  os=require('node:os'),path=require('node:path');
const t=require('../scripts/radio_native_v2_local_transport'),h=require('../scripts/radio_native_v2_broker_host');
const MIB=1024*1024,sha=t.sha;
const temporary=()=>fs.mkdtempSync(path.join(os.tmpdir(),'radio-local-transport-'));
function save(root,name,data){const filename=path.join(root,name);fs.writeFileSync(filename,data,{flag:'wx'});
  return {path:filename,bytes:Buffer.byteLength(data),sha256:sha(data)};}
function packet(params){return {schema:'radio-native-v2-filesystem-bridge-v1',ordinal:0,operation:'invoke:create_tree',params,
  response_id:'response-000000',response_reserved_bytes:MIB,case_ordinal:0,automatic_retry:false,deadline_monotonic_seconds:123};}
function beginLedger(options={}){const ledger=new t.SharedLedger(options);ledger.beginCase(0);return ledger;}
test('old numeric shared allocations cannot be enlarged',()=>{
  assert.throws(()=>new t.SharedLedger({limits:{...t.HARD,case_calls:65}}));
  const record=t.capacityRecord();assert.ok(record.calls_per_case<=64);assert.ok(record.calls_eight_cases<=512);
  assert.equal(record.normalized_readback_crosses_tool_boundary,false);
});
test('unknown visible reply retains full reservation and blocks next case',()=>{
  const ledger=beginLedger(),token=ledger.reserve({tool:'read',request_bytes:20,request_sha256:'a'.repeat(64),response_reservation:100});
  assert.equal(ledger.usage().unknown_response_bytes,100);assert.throws(()=>ledger.beginCase(1));
  ledger.complete(token,{output:'x'});assert.equal(ledger.usage().unknown_response_count,0);ledger.beginCase(1);
  assert.throws(()=>ledger.complete(token,{output:'again'}));
});
test('supporting calls consume same original case call limit',()=>{
  const ledger=beginLedger({limits:{...t.HARD,case_calls:2}});
  for(let n=0;n<2;n++){const token=ledger.reserve({tool:'courier',label:'support',request_bytes:1,
    request_sha256:'b'.repeat(64),response_reservation:100});ledger.complete(token,{ok:true});}
  assert.throws(()=>ledger.reserve({tool:'connector',request_bytes:1,request_sha256:'b'.repeat(64),response_reservation:100}));
});
test('unknown delivery request is bounded before dispatch and reconciled once',()=>{
  const ledger=beginLedger(),token=ledger.reserveUnknownRequest({tool:'write_stdin',request_reservation:100,
    request_intent_sha256:'c'.repeat(64),response_reservation:100});
  assert.equal(ledger.usage().request_bytes,100);
  assert.throws(()=>ledger.reconcileRequest(token,'x'.repeat(101)));
  const json=JSON.stringify({tool:'write_stdin',arguments:{chars:'receipt'}});
  ledger.reconcileRequest(token,json);assert.equal(ledger.usage().request_bytes,Buffer.byteLength(json));
  assert.throws(()=>ledger.reconcileRequest(token,json));ledger.complete(token,{output:'next'});
});
test('late visible envelope is accounted without reopening stopped ledger',()=>{
  const ledger=beginLedger(),token=ledger.reserve({tool:'mutation',request_bytes:1,request_sha256:'b'.repeat(64),response_reservation:100});
  ledger.stop('lost acknowledgement');const result=ledger.complete(token,{late:'reply'},{checkDeadline:false});
  assert.equal(ledger.usage().response_bytes,result.bytes);assert.equal(ledger.usage().unknown_response_count,0);
  assert.throws(()=>ledger.reserve({tool:'retry',request_bytes:1,request_sha256:'b'.repeat(64),response_reservation:100}));
});
test('shared deadline is rechecked after reply accounting',()=>{
  let now=0;const ledger=beginLedger({clock:()=>now,limits:{...t.HARD,case_seconds:1}}),
    token=ledger.reserve({tool:'operation',request_bytes:1,request_sha256:'b'.repeat(64),response_reservation:100});
  now=1001;assert.throws(()=>ledger.complete(token,{known:true}));assert.equal(ledger.usage().unknown_response_count,0);
});
test('existing worker request params form exact tool view with no copy',()=>{
  const root=temporary();try{
    const params={base_tree_sha:'c'.repeat(40),repository_full_name:h.REPOSITORY,
      tree_elements:[{content:'abcdef'.repeat(100000),mode:'100644',path:'fixture/a',type:'blob'}]},p=packet(params),
      file=save(root,'request',h.canonical(p)),before=fs.readdirSync(root);
    const view=t.makeRequestView({tool:'mcp__codex_apps__github_create_tree',packet:p,...file}),
      argument=t.readRange(file.path,view.offset,view.bytes).toString('ascii'),
      actual=JSON.stringify({tool:'mcp__codex_apps__github_create_tree',arguments:params});
    assert.equal(view.request_prefix+argument+view.request_suffix,actual);assert.equal(view.request_sha256,sha(actual));
    assert.deepEqual(fs.readdirSync(root),before);
    assert.throws(()=>t.makeRequestView({tool:'arbitrary',packet:p,...file}));
    assert.throws(()=>t.makeRequestView({tool:'mcp__codex_apps__github_create_tree',packet:p,...file,sha256:'e'.repeat(64)}));
  }finally{fs.rmSync(root,{recursive:true});}
});
test('streamed request receipt hash exactly matches nested JavaScript JSON bytes',()=>{
  const root=temporary();try{
    const params={content:'quote=" backslash=\\ newline=\n'.repeat(50000)},p=JSON.parse(h.canonical(packet(params))),
      source=save(root,'request',h.canonical(p)),paramsJson=JSON.stringify(p.params),withNull=h.canonical({...p,params:null}),
      offset=withNull.indexOf('"params":null')+'"params":'.length,
      view=t.makeRequestView({tool:'mcp__codex_apps__github_create_tree',packet:p,...source,params_offset:offset,
        params_bytes:Buffer.byteLength(paramsJson),params_sha256:sha(paramsJson)}),
      response=JSON.stringify({structuredContent:{content:'Unicode: æøå'},isError:false}),
      actual=JSON.stringify({request_json:JSON.stringify({tool:'mcp__codex_apps__github_create_tree',arguments:p.params}),response_json:response}),
      streamed=t.requestViewStoragePin(view,response);
    assert.equal(streamed.bytes,Buffer.byteLength(actual));assert.equal(streamed.sha256,sha(actual));
    assert.throws(()=>t.makeRequestView({tool:'mcp__codex_apps__github_create_tree',packet:p,...source,params_offset:offset,
      params_bytes:Buffer.byteLength(paramsJson),params_sha256:'0'.repeat(64)}));
  }finally{fs.rmSync(root,{recursive:true});}
});
test('full supporting raw read envelope reconstructs exact original property order',()=>{
  const root=temporary();try{
    const source=save(root,'request','abcdef0123456789'),raw={chunk_id:'x',wall_time_seconds:0.125,exit_code:0,
      original_token_count:2,output:'cdef01'},descriptor=t.makeReadDescriptor(raw,{path:source.path,offset:2,bytes:6,source_sha256:source.sha256}),
      restored=t.reconstructReadEnvelope(descriptor,{path:source.path,source_sha256:source.sha256,offset:2,bytes:6,next_offset:2});
    assert.equal(restored.json,JSON.stringify(raw));assert.deepEqual(restored.raw,raw);
    assert.throws(()=>t.reconstructReadEnvelope({...descriptor,envelope_sha256:'0'.repeat(64)}));
    assert.throws(()=>t.reconstructReadEnvelope(descriptor,{path:source.path,source_sha256:source.sha256,offset:2,bytes:6,next_offset:3}));
    fs.writeFileSync(source.path,'abcXYZ0123456789');assert.throws(()=>t.reconstructReadEnvelope(descriptor));
  }finally{fs.rmSync(root,{recursive:true});}
});
test('receiver bounds metadata and forbids duplicate/prototype raw keys',()=>{
  const root=temporary();try{
    const source=save(root,'request','x'),d=t.makeReadDescriptor({exit_code:0,output:'x'},
      {path:source.path,offset:0,bytes:1,source_sha256:source.sha256});
    assert.throws(()=>t.reconstructReadEnvelope({...d,envelope_entries:[['exit_code',0],['output',null],['output',null]]}));
    assert.throws(()=>t.reconstructReadEnvelope({...d,envelope_entries:[['exit_code',0],['output',null],['__proto__',{}]]}));
    assert.throws(()=>t.reconstructReadEnvelope({...d,envelope_entries:[['exit_code',0],['output',null],['extra','x'.repeat(8193)]]}));
  }finally{fs.rmSync(root,{recursive:true});}
});
test('whole extraction plan reserves source-dependent escaped replies before dispatch',()=>{
  const root=temporary();try{
    const params={content:'\\"'.repeat(300000)},p=JSON.parse(h.canonical(packet(params))),
      source=save(root,'request',h.canonical(p)),view=t.makeRequestView({tool:'mcp__codex_apps__github_create_tree',packet:p,...source}),
      ledger=beginLedger(),plan=t.makeCourierReadPlan(view,{python:'/usr/bin/python3',ledger});
    assert.ok(plan.length>1);assert.equal(ledger.usage().unknown_response_count,plan.length);
    for(const row of plan){const output=t.readRange(row.path,row.offset,row.bytes).toString('ascii'),
      raw={chunk_id:'fixture',wall_time_seconds:0.1,exit_code:0,original_token_count:1,output};
      assert.ok(Buffer.byteLength(JSON.stringify(raw))<=row.response_reserved_bytes);
      ledger.complete(row.ledger_token,raw);}
    assert.equal(ledger.usage().unknown_response_count,0);
    assert.ok(plan[0].response_reserved_bytes>t.READ_BYTES);
  }finally{fs.rmSync(root,{recursive:true});}
});

function hostFixture({mutateFreeze,...overrides}={}) {
  const root=temporary(),parent='a'.repeat(40),parentTree='b'.repeat(40),tree='c'.repeat(40),candidate='d'.repeat(40),
    prefix=h.PREFIX+'/case00-'+'e'.repeat(16),manifest='{}',head=sha(manifest)+'\n',files={};
  const blob=data=>require('node:crypto').createHash('sha1').update('blob '+Buffer.byteLength(data)+'\0').update(data).digest('hex');
  for(const [name,content]of[['HEAD',head],['manifest.json',manifest]])files[prefix+'/'+name]={bytes:Buffer.byteLength(content),sha256:sha(content),blob:blob(content)};
  const freeze={schema:'radio-native-v2-inline-terminal-archive-v1',mode:'ENGINEERING_ONLY',broker_protocol:h.BROKER_PROTOCOL,
    repository:h.REPOSITORY,branch:h.BRANCH,ordinal:0,prefix,parent,parent_tree:parentTree,
    limits:{calls:64,request_bytes:48*MIB,response_bytes:64*MIB,stored_bytes:36*MIB,files:28,seconds:600,peak_rss_bytes:512*MIB},
    files,manifest_sha256:sha(manifest),per_operation_response_reservations:{fetch:4*MIB,create_tree:MIB,create_commit:65536,update_ref:16384,fetch_files:48*MIB},
    single_inline_tree_request:true,single_grouped_readback:true,force:false,automatic_retry:false,
    execution_restart_authorized:false,scientific_admission_authorized:false};
  if(mutateFreeze)mutateFreeze(freeze);
  let updated=false;const courierCalls=[],gitCalls=[],durable=[];
  const localGit={withDeadline:(ms,fn)=>fn(),expectedTree:()=>tree,immutableRead:url=>url.includes('/commits/')?
    {sha:url.split('/').at(-1),tree:{sha:url.endsWith(parent)?parentTree:tree},parents:url.endsWith(candidate)?[{sha:parent}]:[]}:
    {sha:url.split('/').at(-1),tree:[],truncated:false},snapshot:()=>({actual_tool_calls:0})};
  const courier=async(tool,args)=>{
    courierCalls.push(tool);if(tool.endsWith('_fetch'))return{structuredContent:{content:JSON.stringify({ref:'refs/heads/'+h.BRANCH,
      object:{type:'commit',sha:updated?candidate:parent}})}};
    if(tool.endsWith('_create_tree'))return{structuredContent:{sha:tree}};
    if(tool.endsWith('_create_commit'))return{structuredContent:{sha:candidate}};
    updated=true;return{structuredContent:{success:true}};
  };
  const persistRaw=async r=>{durable.push(r);return{request_bytes:Buffer.byteLength(r.request_json),request_sha256:sha(r.request_json),
    response_bytes:Buffer.byteLength(r.response_json),response_sha256:sha(r.response_json),stored_bytes:Buffer.byteLength(r.storage_json),stored_sha256:sha(r.storage_json)};};
  const groupedGitReadback=async job=>{
    await job.callGit('git_fetch');await job.callGit('git_cat_file_batch');
    const raw={path:job.spool_path,bytes:job.raw_git_reserved_bytes,sha256:'f'.repeat(64),durable:true},
      projection={id:'projection',path:root+'/projection',bytes:49*MIB-1024,sha256:'1'.repeat(64),durable:true};
    // Use actual bound in tests: near maximal 48-MiB normalized reply.
    projection.bytes=48*MIB-1024;
    return{commit:job.commit,single_cat_file_batch:true,raw_git_receipt:raw,local_projection:projection,
      projection_verification:{schema:'radio-native-v2-local-projection-verification-v1',commit:job.commit,
        paths_sha256:sha(h.canonical(job.paths)),file_pins_sha256:sha(h.canonical(job.files)),raw_git_sha256:raw.sha256,
        projection_sha256:projection.sha256,exact_frozen_blob_sha256:true,exact_git_blob_identity:true,exact_batch_framing:true}};
  };
  const host=t.createLocalBrokerHost({repoPath:root,spoolRoot:root,localGit,courier,persistRaw,groupedGitReadback,
    runGit:async(kind,plan)=>{gitCalls.push({kind,plan});return{exit_code:0,output:''};},...overrides});
  const freezeJson=h.canonical(freeze);host.beginCase(freezeJson,sha(freezeJson));
  let packetOrdinal=0;
  const invoke=async(operation,params)=>{
    const p=JSON.parse(h.canonical(packet(params))),source=save(root,'packet-'+packetOrdinal++,h.canonical(p));
    host.setRequestSource({packet:p,...source});return host.withWorkerDeadline(Date.now()+10000,()=>host.invoke(operation,p.params));
  };
  return{host,invoke,root,parent,parentTree,tree,candidate,prefix,freeze,files,manifest,head,courierCalls,gitCalls,durable};
}
async function publishFixture(f) {
  const base='https://api.github.com/repos/'+h.REPOSITORY+'/git/';
  await f.invoke('fetch',{url:base+'ref/heads/'+encodeURIComponent(h.BRANCH)});
  await f.invoke('fetch',{url:base+'commits/'+f.parent});await f.invoke('fetch',{url:base+'trees/'+f.parentTree});
  await f.invoke('create_tree',{repository_full_name:h.REPOSITORY,base_tree_sha:f.parentTree,tree_elements:[
    {content:f.head,mode:'100644',path:f.prefix+'/HEAD',type:'blob'},
    {content:f.manifest,mode:'100644',path:f.prefix+'/manifest.json',type:'blob'}]});
  await f.invoke('fetch',{url:base+'trees/'+f.tree});
  await f.invoke('create_commit',{repository_full_name:h.REPOSITORY,parent_sha:f.parent,tree_sha:f.tree,message:'fixture'});
  await f.invoke('fetch',{url:base+'commits/'+f.candidate});
  await f.invoke('fetch',{url:base+'ref/heads/'+encodeURIComponent(h.BRANCH)});
  await f.invoke('update_ref',{repository_full_name:h.REPOSITORY,branch_name:h.BRANCH,sha:f.candidate,force:false});
  const deferred=await f.invoke('fetch_files',{repository_full_name:h.REPOSITORY,ref:f.candidate,
    paths:Object.keys(f.files).sort(),encoding:'base64'});
  await f.invoke('fetch',{url:base+'ref/heads/'+encodeURIComponent(h.BRANCH)});
  return deferred;
}
test('strict host uses six connectors and three charged Git operations; full reply stays a pin',async()=>{
  const f=hostFixture();try{const deferred=await publishFixture(f),receipt=f.host.finishCase();
    assert.equal(deferred.schema,'radio-native-v2-local-projection-reply-v1');assert.equal(deferred.projection.bytes,48*MIB-1024);
    assert.ok(Buffer.byteLength(JSON.stringify(deferred))<1024);assert.equal(f.courierCalls.length,6);assert.equal(f.gitCalls.length,3);
    assert.equal(receipt.actual_tool_usage.calls,9);assert.equal(receipt.explicit_git_operations,3);
    assert.equal(f.durable.length,9);assert.equal(f.host.capabilityManifest().execution_authorized,false);
  }finally{fs.rmSync(f.root,{recursive:true});}
});
const networkEnvironment={PATH:'/usr/bin:/bin',LANG:'C',LC_ALL:'C',GIT_CONFIG_NOSYSTEM:'1',
  GIT_CONFIG_SYSTEM:'/dev/null',GIT_CONFIG_GLOBAL:'/dev/null',GIT_NO_REPLACE_OBJECTS:'1',GIT_NO_LAZY_FETCH:'1',
  GIT_TERMINAL_PROMPT:'0',GIT_OPTIONAL_LOCKS:'0',HTTPS_PROXY:'http://127.0.0.1:12345',GIT_SSL_CAINFO:'/fixed/input.pem'};
const incomingCapabilities='packet: git< version 2\npacket: git< fetch=shallow wait-for-done filter\n';
test('configured network prepares capabilities separately and receipts exact environments before dispatch',async()=>{
  const calls=[],f=hostFixture({gitFetchEnvironment:networkEnvironment,runGit:async(kind,plan)=>{
    assert.ok(f.host.usage().unknown_response_count>0,'Local process reserved before spawn');
    const ledgerRequest=f.host.ledger.records.at(-1);assert.equal(ledgerRequest.request_sha256,
      sha(JSON.stringify({tool:'local_git_process',arguments:plan})));
    calls.push({kind,plan});return{exit_code:0,output:'',stderr:kind==='git_protocol_capability'?incomingCapabilities:''};}});
  try{
    const prepared=await f.host.withWorkerDeadline(Date.now()+10000,()=>f.host.prepareNetwork());
    assert.equal(prepared.capability.filter,true);assert.equal(f.courierCalls.length,0);
    assert.deepEqual(calls.map(r=>r.kind),['git_protocol_capability']);
    assert.deepEqual(calls[0].plan.environment,{...networkEnvironment,GIT_TRACE_PACKET:'1'});
    await publishFixture(f);const receipt=f.host.finishCase();
    assert.deepEqual(calls.map(r=>r.kind),['git_protocol_capability','git_fetch','git_fetch','git_cat_file_batch']);
    assert.equal(receipt.explicit_git_operations,4);assert.equal(receipt.actual_tool_usage.calls,10);
    assert.equal(f.courierCalls.length,6);assert.equal(receipt.git_filter_capability.filter,true);
    const blobs=Array.from(new Set(Object.values(f.files).map(pin=>pin.blob))).sort();
    for(const row of calls.filter(r=>r.kind==='git_fetch')){
      assert.deepEqual(row.plan.environment,networkEnvironment);assert.ok(row.plan.args.includes('--filter=blob:none'));
      assert.ok(row.plan.args.includes('--depth=1'));assert.deepEqual(row.plan.args.slice(-1-blobs.length),[f.candidate,...blobs]);
      assert.equal(row.plan.environment.GIT_TRACE_PACKET,undefined);
    }
    assert.equal(calls.at(-1).plan.environment,undefined);
    const stored=JSON.parse(f.durable[0].request_json);assert.equal(stored.arguments.environment.GIT_TRACE_PACKET,'1');
  }finally{fs.rmSync(f.root,{recursive:true});}
});
test('missing incoming filter capability stops before any fetch or connector',async()=>{
  const calls=[],f=hostFixture({gitFetchEnvironment:networkEnvironment,runGit:async(kind)=>{
    calls.push(kind);return{exit_code:0,output:'',stderr:'packet: git< version 2\npacket: git> fetch=shallow filter\n'};}});
  try{
    await assert.rejects(f.host.withWorkerDeadline(Date.now()+10000,()=>f.host.prepareNetwork()),/Incoming protocol/);
    assert.deepEqual(calls,['git_protocol_capability']);assert.equal(f.courierCalls.length,0);
    assert.equal(f.host.state().stopped,true);assert.equal(f.durable.length,1);
    assert.equal(f.host.usage().unknown_response_count,0);assert.equal(f.host.usage().unknown_receipt_bytes,0);
  }finally{fs.rmSync(f.root,{recursive:true});}
});
test('network invocation cannot skip preparation and outgoing capability text never qualifies',async()=>{
  for(const stderr of['packet: git> version 2\npacket: git> fetch=shallow filter\n',
    'packet: git< version 2\npacket: git< fetch=shallow filtering\n',
    'packet: git< version 2\npacket: git< fetch=filter\n'])
    assert.throws(()=>t.filterCapabilityProof({exit_code:0,stderr}),/Incoming protocol/);
  const f=hostFixture({gitFetchEnvironment:networkEnvironment});try{
    await assert.rejects(f.invoke('fetch',{url:'https://api.github.com/repos/'+h.REPOSITORY+'/git/ref/heads/'+h.BRANCH}),/preparation incomplete/);
    assert.equal(f.courierCalls.length,0);assert.equal(f.gitCalls.length,0);
  }finally{fs.rmSync(f.root,{recursive:true});}
});
test('invocation refuses missing claimed worker deadline before connector dispatch',async()=>{
  const f=hostFixture();try{await assert.rejects(f.host.invoke('fetch',{url:'https://api.github.com/repos/'+h.REPOSITORY+'/git/ref/heads/'+h.BRANCH}));
    assert.equal(f.courierCalls.length,0);assert.equal(f.host.state().stopped,true);
  }finally{fs.rmSync(f.root,{recursive:true});}
});
test('inconsistent frozen blob target stops before tree publication or archive fetch',async()=>{
  const calls=[],f=hostFixture({gitFetchEnvironment:networkEnvironment,
    mutateFreeze:freeze=>{freeze.files[freeze.prefix+'/manifest.json'].blob='1'.repeat(40);},
    runGit:async kind=>{calls.push(kind);return{exit_code:0,output:'',stderr:incomingCapabilities};}});
  try{
    await f.host.withWorkerDeadline(Date.now()+10000,()=>f.host.prepareNetwork());
    await assert.rejects(publishFixture(f),/Frozen archive Git blob identity differs/);
    assert.deepEqual(f.courierCalls,['mcp__codex_apps__github_fetch']);
    assert.deepEqual(calls,['git_protocol_capability'],'An inconsistent target never reaches a filtered archive fetch');
    assert.equal(f.host.state().stopped,true);
  }finally{fs.rmSync(f.root,{recursive:true});}
});
test('mismatched independently computed candidate tree stops before commit/update',async()=>{
  const f=hostFixture({localGit:{withDeadline:(ms,fn)=>fn(),immutableRead:url=>({sha:url.split('/').at(-1),tree:{sha:'b'.repeat(40)},parents:[],truncated:false}),
    expectedTree:()=> '0'.repeat(40)}});try{
    const base='https://api.github.com/repos/'+h.REPOSITORY+'/git/';await f.invoke('fetch',{url:base+'ref/heads/'+h.BRANCH});
    await f.invoke('fetch',{url:base+'commits/'+f.parent});
    await assert.rejects(f.invoke('create_tree',{repository_full_name:h.REPOSITORY,base_tree_sha:f.parentTree,tree_elements:[
      {content:f.head,mode:'100644',path:f.prefix+'/HEAD',type:'blob'},
      {content:f.manifest,mode:'100644',path:f.prefix+'/manifest.json',type:'blob'}]}));
    assert.equal(f.courierCalls.filter(n=>n.endsWith('_create_commit')).length,0);assert.equal(f.host.state().stopped,true);
  }finally{fs.rmSync(f.root,{recursive:true});}
});
test('projection proof mismatch closes host after one update with no finish',async()=>{
  const f=hostFixture({groupedGitReadback:async job=>{await job.callGit('git_fetch');await job.callGit('git_cat_file_batch');return{
    commit:job.commit,single_cat_file_batch:true,raw_git_receipt:{path:job.spool_path,bytes:job.raw_git_reserved_bytes,sha256:'f'.repeat(64),durable:true},
    local_projection:{id:'x',path:job.spool_path,bytes:1,sha256:'1'.repeat(64),durable:true},projection_verification:{}};}});
  try{await assert.rejects(publishFixture(f));assert.equal(f.courierCalls.filter(n=>n.endsWith('_update_ref')).length,1);
    assert.equal(f.host.state().update_may_have_landed,true);assert.throws(()=>f.host.finishCase());
  }finally{fs.rmSync(f.root,{recursive:true});}
});
test('large read custody uses two passes and a single lazy frame at a time',async()=>{
  let produced=0,largest=0;const f=hostFixture({persistRawBatchLazy:async({frames,produce})=>{
    const receipts=[];for(let i=0;i<frames.length;i++){
      const raw=await produce(i);produced++;largest=Math.max(largest,Buffer.byteLength(raw));
      assert.equal(Buffer.byteLength(raw),frames[i].stored_bytes);assert.equal(sha(raw),frames[i].stored_sha256);
      receipts.push({...frames[i]});}
    return receipts;}});
  try{
    const p=JSON.parse(h.canonical(packet({content:'ABCD'.repeat(2*MIB)}))),source=save(f.root,'large-read-source',h.canonical(p));
    f.host.setRequestSource({packet:p,...source});const view=t.makeRequestView({tool:'mcp__codex_apps__github_create_tree',packet:p,...source}),
      plan=f.host.prepareCourierReads(view,{python:'/usr/bin/python3'}),descriptors=plan.map(row=>t.makeReadDescriptor(
        {chunk_id:'fixture',wall_time_seconds:0.1,exit_code:0,original_token_count:1,
          output:t.readRange(row.path,row.offset,row.bytes).toString('ascii')},row));
    const result=await f.host.completeCourierReads(plan,descriptors);
    assert.equal(result.items,plan.length);assert.equal(produced,plan.length);assert.ok(largest<2*t.READ_BYTES+8192);
    assert.equal(f.host.usage().unknown_receipt_bytes,0);assert.equal(f.host.usage().unknown_response_count,0);
    await assert.rejects(f.host.completeCourierReads(plan,descriptors));
  }finally{fs.rmSync(f.root,{recursive:true});}
});
test('failed local Git envelope is charged and saved before host terminates',async()=>{
  const f=hostFixture({runGit:async()=>({exit_code:1,output:'explicit Git failure'})});
  try{await assert.rejects(publishFixture(f));assert.ok(f.durable.some(r=>r.response_json.includes('explicit Git failure')));
    assert.equal(f.host.usage().unknown_response_count,0);assert.equal(f.host.usage().unknown_receipt_bytes,0);
    assert.equal(f.courierCalls.filter(n=>n.endsWith('_update_ref')).length,0);
  }finally{fs.rmSync(f.root,{recursive:true});}
});
test('unacknowledged update is marked as possibly landed and cannot retry',async()=>{
  let calls=0;const f=hostFixture({courier:async(tool,args)=>{calls++;
    if(tool.endsWith('_fetch'))return{structuredContent:{content:JSON.stringify({ref:'refs/heads/'+h.BRANCH,object:{type:'commit',sha:'a'.repeat(40)}})}};
    if(tool.endsWith('_create_tree'))return{structuredContent:{sha:'c'.repeat(40)}};
    if(tool.endsWith('_create_commit'))return{structuredContent:{sha:'d'.repeat(40)}};
    throw Error('update acknowledgement lost');}});
  try{await assert.rejects(publishFixture(f));assert.equal(f.host.state().update_may_have_landed,true);
    assert.equal(f.host.usage().unknown_response_count,1);assert.ok(f.host.usage().unknown_receipt_bytes>0);
    const before=calls;await assert.rejects(f.invoke('update_ref',{repository_full_name:h.REPOSITORY,branch_name:h.BRANCH,sha:f.candidate,force:false}));
    assert.equal(calls,before);
  }finally{fs.rmSync(f.root,{recursive:true});}
});
