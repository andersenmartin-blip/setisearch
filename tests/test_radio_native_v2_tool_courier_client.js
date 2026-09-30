'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const h=require('../scripts/radio_native_v2_broker_host'),
  c=require('../scripts/radio_native_v2_tool_courier_client');
const SHA='a'.repeat(40),BRANCH='m43-support-qualification',REPO='andersenmartin-blip/setisearch',
  PYTHON='/usr/bin/python3',startup={cmd:'pinned prospective controller',max_output_tokens:400000,yield_time_ms:1000};
function argsFor(operation){
  if(operation==='fetch')return{url:'https://api.github.com/repos/'+REPO+'/git/ref/heads/'+BRANCH};
  if(operation==='create_tree')return{base_tree_sha:SHA,repository_full_name:REPO,
    tree_elements:[{content:'fixture',mode:'100644',path:'fixture/path',type:'blob'}]};
  if(operation==='create_commit')return{repository_full_name:REPO,parent_sha:SHA,tree_sha:SHA,message:'prospective'};
  return{repository_full_name:REPO,branch_name:BRANCH,sha:SHA,force:false};
}
function frame(ordinal,extra={}){return{schema:c.CONTROLLER_SCHEMA,kind:'request',ordinal,
  tool:'mcp__codex_apps__github_'+c.CLIENT_SEQUENCE[ordinal],arguments:argsFor(c.CLIENT_SEQUENCE[ordinal]),
  request_view:null,reads:[],delivery_request_reserved_bytes:1024*1024,deadline_ms:30000,automatic_retry:false,...extra};}
const rawOutput=output=>({chunk_id:'fixture',wall_time_seconds:0.1,session_id:7,output,original_token_count:10});
function fixture({source=false,idle=false}={}){
  const seen=[],bodies=[];let pending=null;
  const packets=c.CLIENT_SEQUENCE.map((_,i)=>frame(i));
  if(source){
    const p=packets[1],json=JSON.stringify(p.arguments),filename='/tmp/qualification/items/request-000001/part',offset=111,
      prefix='{"tool":"'+p.tool+'","arguments":',suffix='}',request=prefix+json+suffix,
      quote=x=>"'"+x.replace(/'/g,"'\\''")+"'",script='import os,sys; f=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW); '+
        'n=int(sys.argv[3]); b=os.pread(f,n,int(sys.argv[2])); assert len(b)==n; sys.stdout.buffer.write(b); os.close(f)';
    p.request_view={schema:'radio-native-v2-existing-request-view-v1',path:filename,offset,bytes:json.length,
      sha256:h.sha256(json),source_sha256:'b'.repeat(64),request_prefix:prefix,request_suffix:suffix,
      request_bytes:request.length,request_sha256:h.sha256(request)};
    p.arguments=null;p.reads=[{ordinal:0,tool:'exec_command',path:filename,offset,bytes:json.length,
      source_sha256:'b'.repeat(64),output_sha256:h.sha256(json),response_reserved_bytes:8192+2*json.length,
      arguments:{cmd:quote(PYTHON)+' -I -S -B -c '+quote(script)+' '+quote(filename)+' '+offset+' '+json.length,
        max_output_tokens:400000,yield_time_ms:1000},fixture_output:json}];
  }
  const tools={exec_command:async a=>{
    seen.push(['exec_command',a]);if(a.cmd===startup.cmd){if(idle){pending=packets[0];return rawOutput('');}
      return rawOutput(JSON.stringify(packets[0])+'\n');}
    return{chunk_id:'source',wall_time_seconds:0.1,exit_code:0,original_token_count:1,
      output:packets[1].reads[0].fixture_output};
  },write_stdin:async a=>{
    seen.push(['write_stdin',a]);assert.equal(a.yield_time_ms,10000);
    if(a.chars===''){const p=pending;pending=null;return rawOutput(JSON.stringify(p)+'\n');}
    const b=JSON.parse(a.chars);bodies.push(b);
    assert.equal(b.delivery_arguments.yield_time_ms,10000);
    const next=b.ordinal+1;if(next===6)return{chunk_id:'terminal',wall_time_seconds:0.1,exit_code:0,
      original_token_count:1,output:JSON.stringify({schema:c.CONTROLLER_SCHEMA,kind:'terminal',status:'SINGLE_CASE_COMPONENT_ONLY'})+'\n'};
    if(idle){pending=packets[next];return rawOutput('');}
    return rawOutput(JSON.stringify(packets[next])+'\n');
  }};
  for(const [tool]of Object.entries(c.CLIENT_CORE))tools[tool]=async a=>{seen.push([tool,a]);return{
    structuredContent:tool.endsWith('_fetch')?{content:'{"ref":"fixture"}'}:
      tool.endsWith('_update_ref')?{success:true}:{sha:SHA},content:[{type:'text',text:'complete raw fixture envelope'}]};};
  return{tools,seen,bodies,packets};
}
const run=(f,extra={})=>c.runToolCourier(f.tools,{startup_arguments:startup,hostLibrary:h,python:PYTHON,...extra});
test('one awaited run performs all six connectors and deliveries without inter-model gaps',async()=>{
  const f=fixture(),result=await run(f);assert.equal(result.status,'SINGLE_CASE_COMPONENT_COMPLETE');
  assert.equal(result.connector_requests,6);assert.equal(result.usage.calls,13);
  assert.equal(result.usage.calls_including_declared_git_processes,17);
  assert.equal(result.records.length,f.seen.length);assert.equal(result.usage.unknown_response_count,0);
  assert.equal(result.execution_authorized,false);assert.equal(result.last_supporting_acknowledgement_durable,false);
  assert.equal(f.bodies[0].start_raw.output,JSON.stringify(f.packets[0])+'\n');
  assert.ok(f.bodies[1].previous_delivery_raw.output.includes('"ordinal":1'));
});
test('startup and every idle SDK poll are counted once and retain full raw envelopes',async()=>{
  const f=fixture({idle:true}),result=await run(f);
  assert.equal(result.status,'SINGLE_CASE_COMPONENT_COMPLETE');assert.equal(result.usage.calls,19);
  assert.equal(result.records.filter(r=>r.kind==='actual_idle_poll').length,6);
  assert.equal(result.controller_poll_receipts_joined_into_host_ledger,false);
  assert.equal(f.bodies[1].previous_delivery_raw.output,'','Poll output never replaces preceding delivery receipt');
});
test('existing source view is extracted once and its exact full tool envelope metadata is delivered',async()=>{
  const f=fixture({source:true}),result=await run(f);assert.equal(result.status,'SINGLE_CASE_COMPONENT_COMPLETE');
  assert.equal(result.usage.calls,14);const descriptor=f.bodies[1].read_descriptors[0];
  assert.equal(descriptor.envelope_entries.find(x=>x[0]==='output')[1],null);
  assert.equal(descriptor.envelope_sha256,result.records.find(x=>x.kind==='actual_source_read').response_sha256);
  assert.equal(f.seen.find(x=>x[0].endsWith('_create_tree'))[1].tree_elements[0].content,'fixture');
});
test('failure appearing with a request in the same SDK result prevents connector dispatch',async()=>{
  const f=fixture();f.tools.exec_command=async()=>rawOutput(JSON.stringify(frame(0))+'\n'+
    JSON.stringify({schema:c.CONTROLLER_SCHEMA,kind:'failed',error:'worker expired'})+'\n');
  const result=await run(f);assert.equal(result.status,'CLOSED_FAILED');assert.equal(result.usage.calls,1);
  assert.equal(result.records.filter(r=>r.kind==='actual_connector').length,0);
});
test('expired absolute worker deadline prevents any source or connector dispatch',async()=>{
  const f=fixture();f.tools.exec_command=async()=>rawOutput(JSON.stringify(frame(0,{worker_deadline_epoch_ms:1}))+'\n');
  const result=await run(f);assert.equal(result.status,'CLOSED_FAILED');assert.equal(result.usage.calls,1);
  assert.match(result.reason,/deadline expired/);
});
test('valid failure frame wins over accompanying stderr and preserves the complete raw reply',async()=>{
  const f=fixture(),output=JSON.stringify(frame(0))+'\n'+
    JSON.stringify({schema:c.CONTROLLER_SCHEMA,kind:'failed',error:'Store startup failed'})+'\nError: Store startup failed\n';
  f.tools.exec_command=async()=>rawOutput(output);
  const result=await run(f);assert.equal(result.status,'CLOSED_FAILED');
  assert.match(result.reason,/Controller closed before dispatch: Store startup failed/);
  assert.equal(result.records[0].raw_result.output,output);
  assert.equal(result.records.filter(r=>r.kind==='actual_connector').length,0);
});
test('lost connector acknowledgement retains response and future-ingress reservations without retry',async()=>{
  const f=fixture();let dispatched=0;f.tools.mcp__codex_apps__github_fetch=async()=>{dispatched++;throw Error('acknowledgement lost');};
  const result=await run(f);assert.equal(result.status,'CLOSED_FAILED');assert.equal(dispatched,1);
  assert.equal(result.usage.unknown_response_count,1);assert.equal(result.usage.unknown_response_bytes,65536);
  assert.equal(result.pending_delivery_reservation.dispatch_attempted,false);
  assert.equal(result.records.filter(r=>r.kind==='actual_delivery').length,0);
});
test('readonly polling cannot bypass the original60actual plus4Git call bound',async()=>{
  const f=fixture();f.tools.exec_command=async()=>rawOutput('');f.tools.write_stdin=async()=>rawOutput('');
  const result=await run(f,{max_actual_calls:2});assert.equal(result.status,'CLOSED_FAILED');assert.equal(result.usage.calls,2);
  assert.equal(result.records.filter(r=>r.kind==='actual_connector').length,0);
});
test('following delivery space must fit before any mutation dispatch',async()=>{
  const f=fixture();f.tools.exec_command=async()=>rawOutput(JSON.stringify(frame(0,{delivery_request_reserved_bytes:48*1024*1024}))+'\n');
  const result=await run(f);assert.equal(result.status,'CLOSED_FAILED');assert.equal(result.usage.calls,1);
  assert.equal(result.records.filter(r=>r.kind==='actual_connector').length,0);
});
