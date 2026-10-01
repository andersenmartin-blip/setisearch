'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),
  path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process');
const h=require('../scripts/radio_native_v2_broker_host'),
  client=require('../scripts/radio_native_v2_tool_courier_client'),
  wrapper=require('../scripts/radio_native_v2_qualified_tool_courier');
const ROOT=path.resolve(__dirname,'..'),HELPER=path.join(ROOT,'scripts/radio_native_v2_caller_tail.py'),
  PYTHON='/usr/bin/python3',HELPER_SHA=crypto.createHash('sha256').update(fs.readFileSync(HELPER)).digest('hex'),
  REPO='andersenmartin-blip/setisearch',BRANCH='m43-support-qualification',SHA='a'.repeat(40),
  startup={cmd:'offline pinned controller fixture',max_output_tokens:400000,yield_time_ms:30000};
function coreArgs(operation){
  if(operation==='fetch')return {url:'https://api.github.com/repos/'+REPO+'/git/ref/heads/'+BRANCH};
  if(operation==='create_tree')return {repository_full_name:REPO,base_tree_sha:SHA,
    tree_elements:[{content:'Thy ☃ 🚀',mode:'100644',path:'fixture/path',type:'blob'}]};
  if(operation==='create_commit')return {repository_full_name:REPO,parent_sha:SHA,tree_sha:SHA,message:'fixture'};
  return {repository_full_name:REPO,branch_name:BRANCH,sha:SHA,force:false};
}
const running=output=>({chunk_id:'fixture',wall_time_seconds:0.1,session_id:7,output,original_token_count:1});
const terminal=()=>({chunk_id:'terminal',wall_time_seconds:0.1,exit_code:0,original_token_count:1,
  output:JSON.stringify({schema:client.CONTROLLER_SCHEMA,kind:'terminal',status:'SINGLE_CASE_COMPONENT_ONLY'})+'\n'});
function fixture({idle=false,finalPoll=false,padding=''}={}){
  const seen=[],delivered=[],directory=fs.mkdtempSync(path.join(os.tmpdir(),'qualified-tail-'));
  let pending=null;
  const packets=client.CLIENT_SEQUENCE.map((operation,ordinal)=>({schema:client.CONTROLLER_SCHEMA,kind:'request',ordinal,
    tool:'mcp__codex_apps__github_'+operation,arguments:coreArgs(operation),request_view:null,reads:[],
    delivery_request_reserved_bytes:1024*1024,deadline_ms:30000,automatic_retry:false}));
  if(padding)packets[0].padding=padding;
  const tools={exec_command:async args=>{
    seen.push(['exec_command',args]);
    if(args.cmd===startup.cmd){if(idle){pending=packets[0];return running('');}
      return running(JSON.stringify(packets[0])+'\n');}
    const result=cp.spawnSync('/bin/bash',['-c',args.cmd],{encoding:'utf8',maxBuffer:1024*1024});
    return {exit_code:result.status,output:result.stdout,stderr:result.stderr,wall_time_seconds:0.01,
      original_token_count:1,chunk_id:'actual-local-tail'};
  },write_stdin:async args=>{
    seen.push(['write_stdin',args]);assert.equal(args.yield_time_ms,30000);
    if(args.chars===''){
      const p=pending;pending=null;
      return p&&p.kind==='terminal'?terminal():running(JSON.stringify(p)+'\n');
    }
    const body=JSON.parse(args.chars);delivered.push(body);
    if(body.ordinal===5){if(finalPoll){pending={kind:'terminal'};return running('');}return terminal();}
    if(idle){pending=packets[body.ordinal+1];return running('');}
    return running(JSON.stringify(packets[body.ordinal+1])+'\n');
  }};
  for(const name of Object.keys(client.CLIENT_CORE))tools[name]=async args=>{
    seen.push([name,args]);return {structuredContent:{sha:SHA},content:[{type:'text',text:'Thy ☃ 🚀 complete raw envelope'}]};
  };
  const options={hostLibrary:h,clientLibrary:client,startup_arguments:startup,python:PYTHON,
    tail_helper_path:HELPER,tail_helper_sha256:HELPER_SHA,caller_tail_path:path.join(directory,'tail.json')};
  return {tools,options,seen,delivered,directory,cleanup:()=>fs.rmSync(directory,{recursive:true,force:true})};
}
const run=(f,extra={})=>wrapper.runQualifiedToolCourier(f.tools,{...f.options,...extra});

test('actual portable client plus one real filesystem command retains exact tail and complete envelope costs',async()=>{
  const f=fixture({idle:true,finalPoll:true});
  try {
    const result=await run(f,{host_custody:{schema:'separate-host-pointer',path:'offline-host'}});
    assert.equal(result.status,'CLOSED_UNQUALIFIED',result.reason);
    assert.equal(result.actual_client_runtime_rss_known,false);
    assert.equal(result.client.actual_client_runtime_rss_known,false);
    assert.equal(result.client.records.filter(r=>r.kind==='actual_idle_poll').length,7);
    assert.deepEqual(result.client.prospective_caps,wrapper.CAPS);
    assert.equal(f.seen.filter(r=>r[0]==='exec_command').length,2,'One startup plus exactly one additional custody command');
    const stored=fs.readFileSync(f.options.caller_tail_path,'utf8');
    assert.equal(stored,wrapper.callerTailPayload(result.client,h));
    assert.equal(crypto.createHash('sha256').update(stored).digest('hex'),result.persistence.payload_sha256);
    assert.equal(result.persistence.request_bytes,Buffer.byteLength(result.persistence.request_json));
    assert.equal(result.persistence.response_bytes,Buffer.byteLength(JSON.stringify(result.persistence.raw_result)));
    assert.equal(result.persistence.request_sha256,h.sha256(result.persistence.request_json));
    assert.equal(result.persistence.response_sha256,h.sha256(result.persistence.response_json));
    assert.equal(result.combined_usage.calls,result.client.usage.calls+4+1);
    assert.equal(result.combined_usage.unknown_response_count,0);
    assert.equal(result.host_custody.schema,'separate-host-pointer');
    assert.equal(result.client.last_supporting_acknowledgement_durable,false);
    assert.equal(result.execution_authorized,false);
    assert.equal(result.reservation_authorized,false);
    // The existing Python contract independently reconstructs the binding and
    // validates the persisted real tool envelopes, including Unicode escaping.
    const validation=cp.spawnSync(PYTHON,['-c',
      'import sys,json; from seti_repeater import native_v2_transport_contract_radio as c; '+
      'v=json.load(sys.stdin); c.validate_client(v["client"],qualified=True); '+
      'c.validate_persistence(v["persistence"],v["client"]); '+
      'print(c.caller_tail_payload(v["client"]).decode())'],{
        input:JSON.stringify({client:result.client,persistence:result.persistence}),encoding:'utf8',
        env:{...process.env,PYTHONPATH:path.join(ROOT,'src')},maxBuffer:2*1024*1024});
    assert.equal(validation.status,0,validation.stderr);
    assert.equal(validation.stdout.trim(),stored);
  }finally{f.cleanup();}
});

test('production mode refuses missing actual independent RSS observer before startup',async()=>{
  const f=fixture();try {
    const result=await run(f,{production:true});assert.equal(result.status,'CLOSED_FAILED');
    assert.match(result.reason,/RSS observation before startup/);assert.equal(f.seen.length,0);
    assert.equal(result.client,null);assert.equal(fs.existsSync(f.options.caller_tail_path),false);
  }finally{f.cleanup();}
});

test('self runtime RSS claim cannot qualify custody even after the actual tail was saved',async()=>{
  const f=fixture();try {
    const result=await run(f,{production:true,read_actual_client_rss:async context=>({
      schema:'radio-native-v2-independent-client-rss-v1',measured:true,client_peak_rss_bytes:1,
      observer_source:'process.memoryUsage',caller_runtime_identity:'self',observer_runtime_identity:'self',
      interval_start_epoch_ms:context.dispatch_at_epoch_ms,interval_end_epoch_ms:context.returned_at_epoch_ms})});
    assert.equal(result.status,'CLOSED_FAILED');assert.match(result.reason,/Independent actual caller RSS/);
    assert.equal(result.actual_client_runtime_rss_known,false);assert.ok(result.persistence);
    assert.equal(result.execution_authorized,false);
  }finally{f.cleanup();}
});

test('RSS observation for a different transcript cannot qualify this caller',async()=>{
  const f=fixture();try {
    const result=await run(f,{production:true,read_actual_client_rss:async context=>({
      schema:'radio-native-v2-independent-client-rss-v1',measured:true,client_peak_rss_bytes:1,
      client_sha256:'b'.repeat(64),observer_source:'independent_procfs',
      caller_runtime_identity:'child',observer_runtime_identity:'parent',
      interval_start_epoch_ms:context.dispatch_at_epoch_ms,interval_end_epoch_ms:context.returned_at_epoch_ms})});
    assert.equal(result.status,'CLOSED_FAILED');assert.equal(result.actual_client_runtime_rss_known,false);
    assert.ok(result.persistence);assert.equal(result.host_custody_qualified,false);
  }finally{f.cleanup();}
});

test('RSS accessor completing after shared deadline retains custody but cannot qualify the case',async()=>{
  const f=fixture();let now=Date.now();try {
    const result=await run(f,{production:true,clock:()=>now,read_actual_client_rss:async context=>{
      now+=600001;return {schema:'radio-native-v2-independent-client-rss-v1',measured:true,
        client_sha256:context.client_sha256,client_peak_rss_bytes:1,observer_source:'independent_procfs',
        caller_runtime_identity:'child',observer_runtime_identity:'parent',
        interval_start_epoch_ms:context.dispatch_at_epoch_ms,interval_end_epoch_ms:now};}});
    assert.equal(result.status,'CLOSED_FAILED');assert.match(result.reason,/deadline expired during RSS/);
    assert.ok(result.persistence);assert.equal(result.persistence.shared_case_elapsed_seconds,600.001);
    assert.equal(result.combined_usage.elapsed_seconds,600.001);
    assert.equal(result.actual_client_runtime_rss_known,false);
  }finally{f.cleanup();}
});

test('lost RSS accessor acknowledgement is bounded without another tool call or retry',async()=>{
  const f=fixture();let timers=0;try {
    const result=await run(f,{production:true,read_actual_client_rss:()=>new Promise(()=>{}),
      setTimer:fn=>{const token={active:true};if(++timers===15)queueMicrotask(()=>{if(token.active)fn();});return token;},
      clearTimer:token=>{if(token)token.active=false;}});
    assert.equal(result.status,'CLOSED_FAILED');assert.match(result.reason,/RSS observation deadline lost/);
    assert.equal(f.seen.length,14);assert.ok(result.persistence);
    assert.equal(result.combined_usage.unknown_response_count,0);
  }finally{f.cleanup();}
});

test('eighth idle poll is refused before actual tool dispatch and no tail command is attempted',async()=>{
  const f=fixture();try {
    f.tools.exec_command=async args=>{f.seen.push(['exec_command',args]);return running('');};
    f.tools.write_stdin=async args=>{f.seen.push(['write_stdin',args]);return running('');};
    const result=await run(f);assert.equal(result.status,'CLOSED_FAILED');
    assert.match(result.reason,/Complete unchanged courier component/);
    assert.match(result.client.reason,/Eighth idle poll/);
    assert.equal(f.seen.filter(r=>r[0]==='write_stdin').length,7);
    assert.equal(f.seen.filter(r=>r[0]==='exec_command').length,1);assert.equal(result.persistence,null);
  }finally{f.cleanup();}
});

test('oversized selected raw poll reply fails bounded argv fit before tail dispatch',async()=>{
  const f=fixture({idle:true,padding:'x'.repeat(60000)});try {
    const result=await run(f);assert.equal(result.client.status,'SINGLE_CASE_COMPONENT_COMPLETE');
    assert.equal(result.status,'CLOSED_FAILED');assert.match(result.reason,/bounded OS argument/);
    assert.equal(f.seen.filter(r=>r[0]==='exec_command').length,1);
    assert.equal(result.persistence,null);assert.equal(fs.existsSync(f.options.caller_tail_path),false);
    assert.equal(result.full_worst_case_tail_size_qualified,false);
  }finally{f.cleanup();}
});

test('lost tail acknowledgement retains charged unknown response without retry',async()=>{
  const f=fixture();try {
    const real=f.tools.exec_command;let attempted=0;
    f.tools.exec_command=async args=>{if(args.cmd===startup.cmd)return real(args);attempted++;throw Error('tail reply lost');};
    const result=await run(f);assert.equal(result.status,'CLOSED_FAILED');assert.equal(attempted,1);
    assert.equal(result.persistence,null);assert.equal(result.combined_usage.unknown_response_count,1);
    assert.equal(result.combined_usage.unknown_response_bytes,256*1024);
    assert.equal(result.tail_record.response_unknown,true);assert.equal(result.automatic_retry,false);
  }finally{f.cleanup();}
});

test('changed receipt hash is refused and existing evidence is preserved',async()=>{
  const f=fixture();try {
    const real=f.tools.exec_command;
    f.tools.exec_command=async args=>{const raw=await real(args);if(args.cmd!==startup.cmd){
      const r=JSON.parse(raw.output);r.reopened_sha256='b'.repeat(64);return {...raw,output:JSON.stringify(r)+'\n'};}return raw;};
    const result=await run(f);assert.equal(result.status,'CLOSED_FAILED');
    assert.match(result.reason,/receipt differs/);assert.equal(result.persistence,null);
    assert.equal(result.tail_record.response_unknown,false);assert.ok(fs.existsSync(f.options.caller_tail_path));
    const again=await run(f);assert.equal(again.status,'CLOSED_FAILED');assert.equal(again.persistence,null);
  }finally{f.cleanup();}
});

test('changed pinned helper source is refused in the sole custody command',async()=>{
  const f=fixture();try {
    const result=await run(f,{tail_helper_sha256:'0'.repeat(64)});
    assert.equal(result.status,'CLOSED_FAILED');assert.equal(result.persistence,null);
    assert.equal(f.seen.filter(r=>r[0]==='exec_command').length,2);
    assert.equal(fs.existsSync(f.options.caller_tail_path),false);
  }finally{f.cleanup();}
});
