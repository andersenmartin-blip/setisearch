// Offline adapter tests. No live connector, RNG, native case or telescope read.
const test=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const h=require('../scripts/radio_native_v2_broker_host');
const bridge=require('../scripts/radio_native_v2_host_bridge');
const hash=value=>crypto.createHash('sha256').update(value).digest('hex');

function fixture(overrides={}) {
  const items=new Map(),calls=[],saved=[];
  const tools={exec_command:async args=>{
    calls.push(args);
    if(overrides.raw)return overrides.raw(args,calls.length);
    const text=args.cmd.split("<<'SETI_NATIVE_V2_BRIDGE_JSON'\n")[1].split('\nSETI_NATIVE_V2_BRIDGE_JSON')[0];
    const request=JSON.parse(text);
    for(const receipt of request.support_receipts||[]) {
      assert.equal(hash(receipt.response_json),receipt.response_sha256);
      assert.equal(Buffer.byteLength(receipt.response_json),receipt.response_bytes);saved.push(receipt);
    }
    let result;
    if(request.action==='reserve') {assert.ok(!items.has(request.id));items.set(request.id,{...request,data:Buffer.alloc(0)});result={reserved:true};}
    else if(request.action==='append') {const item=items.get(request.id),bytes=Buffer.from(request.content_base64,'base64');
      assert.equal(request.offset,item.data.length);item.data=Buffer.concat([item.data,bytes]);result={appended:bytes.length};}
    else if(request.action==='seal') {const item=items.get(request.id);assert.equal(item.data.length,item.bytes);assert.equal(hash(item.data),item.sha256);
      result={bytes:item.bytes,sha256:item.sha256,path:'/fixture/items/'+request.id,durable:true};}
    else if(request.action==='read') {const item=items.get(request.id);result={offset:request.offset,bytes:request.length,total_bytes:item.bytes,
      sha256:item.sha256,next_offset:request.offset+request.length,
      content_base64:item.data.subarray(request.offset,request.offset+request.length).toString('base64')};}
    else if(request.action==='status')result={known:true};
    else throw Error('Unexpected fixture helper action');
    return {exit_code:0,output:JSON.stringify({result,support_receipts_persisted:(request.support_receipts||[]).length}),wall_time_seconds:0};
  }};
  const adapter=bridge.createHostWorkerBridge({hostLibrary:h,tools,root:'/fixture/store',python:'/usr/bin/python3',
    helper:'/fixture/helper.py',sourceRoot:'/fixture/src',...overrides.options});
  return{adapter,calls,items,saved};
}

test('bounded UTF-8 writes durably preserve Unicode and raw connector receipts',async()=>{
  const f=fixture(),request=JSON.stringify({operation:'fetch',unicode:'🎯 æ\n'}),response=JSON.stringify({content:[{type:'text',text:'λ complete framing'}]});
  const storage=JSON.stringify({request_json:request,response_json:response});
  const receipt=await f.adapter.persistRaw({request_json:request,response_json:response,storage_json:storage});
  assert.equal(receipt.stored_sha256,hash(storage));assert.deepEqual([...f.items.values()][0].data,Buffer.from(storage));
  assert.equal(f.saved.length,f.calls.length-1);
  const usage=f.adapter.usage();assert.equal(usage.calls,f.calls.length);assert.equal(usage.unknown_response_count,0);
  assert.ok(usage.supporting_receipt_pending_bytes>0);assert.equal(usage.final_support_acknowledgement_durable,false);
  assert.equal(f.adapter.capabilityManifest().execution_authorized,false);
});

test('multimegabyte ASCII projection traverses bounded tool chunks exactly',async()=>{
  const f=fixture(),value='x'.repeat(2*1024*1024+7),receipt=await f.adapter.put('git_projection',value);
  assert.equal(await f.adapter.read(receipt),value);
  for(const args of f.calls) assert.ok(Buffer.byteLength(args.cmd)<131072);
  assert.equal(f.adapter.usage().append_bytes,Buffer.byteLength(value));assert.equal(f.adapter.usage().read_bytes,Buffer.byteLength(value));
});

test('known truncated helper output is charged and permanently stops without retry',async()=>{
  const f=fixture({raw:async()=>({exit_code:0,output:'{"result":',wall_time_seconds:0})});
  await assert.rejects(f.adapter.action({action:'status'}));assert.equal(f.calls.length,1);
  assert.equal(f.adapter.usage().unknown_response_count,0);assert.ok(f.adapter.state().final_support_acknowledgement);
  await assert.rejects(f.adapter.action({action:'status'}),/no retry/);assert.equal(f.calls.length,1);
});

test('yielded helper acknowledgement retains evidence and never polls',async()=>{
  const f=fixture({raw:async()=>({session_id:9,output:'',wall_time_seconds:1})});
  await assert.rejects(f.adapter.action({action:'status'}),/incomplete/);assert.equal(f.calls.length,1);
  assert.equal(f.adapter.state().stopped,true);assert.equal(f.adapter.usage().unknown_response_count,0);
});

test('unaffordable reply is refused before any supporting dispatch',async()=>{
  const f=fixture({options:{limits:{response_bytes:1024}}});
  await assert.rejects(f.adapter.action({action:'status'}),/Cannot reserve/);assert.equal(f.calls.length,0);
});

test('lost helper acknowledgement retains full unknown reservation',async()=>{
  const f=fixture({raw:async()=>{throw Error('lost helper reply');}});
  await assert.rejects(f.adapter.action({action:'status'}));const usage=f.adapter.usage();
  assert.equal(usage.calls,1);assert.equal(usage.unknown_response_count,1);
  assert.equal(usage.unknown_response_bytes,bridge.BRIDGE_LIMITS.response_reservation_bytes);
});

test('prior complete support reply must be durable before next action returns',async()=>{
  const f=fixture({raw:async(args,ordinal)=>({exit_code:0,output:JSON.stringify({result:{known:true},support_receipts_persisted:0}),wall_time_seconds:0})});
  await f.adapter.action({action:'status'});
  await assert.rejects(f.adapter.action({action:'status'}),/durability unconfirmed/);assert.equal(f.calls.length,2);
  assert.equal(f.adapter.state().outstanding_support_acknowledgements.length,2);
});
