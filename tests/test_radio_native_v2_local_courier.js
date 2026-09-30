const test=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {SharedLedger}=require('../scripts/radio_native_v2_local_transport'),
  {SCHEMA,ToolCourier,deliveryRequest,BoundedLines}=require('../scripts/radio_native_v2_local_courier');
const hash=value=>crypto.createHash('sha256').update(value).digest('hex');
const args={session_id:123,max_output_tokens:400000,yield_time_ms:10000};
function fixture(){
  const ledger=new SharedLedger();ledger.beginCase(0);const saved=[],outgoing=[];
  const persistRaw=async r=>{saved.push(r);return{request_bytes:Buffer.byteLength(r.request_json),response_bytes:Buffer.byteLength(r.response_json),
    request_sha256:hash(r.request_json),response_sha256:hash(r.response_json),
    stored_bytes:Buffer.byteLength(r.storage_json),stored_sha256:hash(r.storage_json)};};
  const courier=new ToolCourier({ledger,persistRaw,persistRawBatch:async()=>[],python:'/usr/bin/python3',
    startRequest:JSON.stringify({tool:'exec_command',arguments:{cmd:'fixed prospective command'}}),emit:r=>outgoing.push(r)});
  courier.bindHost({prepareCourierReads:()=>[],completeCourierReads:async()=>{throw Error('Unplanned reads');}});
  return{courier,ledger,saved,outgoing};
}
function packet(ordinal,extra={}){return JSON.stringify({schema:SCHEMA,ordinal,automatic_retry:false,
  delivery_arguments:args,raw_connector_result:{structuredContent:{sha:'a'.repeat(40)}},read_descriptors:[],
  start_raw:ordinal===0?{session_id:123,output:'initial full envelope',chunk_id:'fixture-start'}:null,
  previous_delivery_raw:ordinal?{session_id:123,output:'next request',chunk_id:'fixture-delivery'}:null,...extra});}

test('full delivery request reconstructs exact observed chars and argument order',()=>{
  const line=packet(0),actual=JSON.stringify({tool:'write_stdin',arguments:{session_id:123,chars:line+'\n',
    max_output_tokens:400000,yield_time_ms:10000}});
  assert.equal(deliveryRequest(line,args),actual);
  assert.throws(()=>deliveryRequest(line,{...args,extra:true}),/Exact visible/);
});

test('two courier deliveries reserve before dispatch and retain exact preceding envelopes',async()=>{
  const f=fixture(),context={request_view:null,response_reserved_bytes:65536};
  const first=f.courier.request('mcp__codex_apps__github_fetch',{url:'fixed'},context);
  assert.equal(f.ledger.records.length,2);assert.equal(f.ledger.records[1].request_unknown,true);
  assert.equal(f.outgoing.length,1);await f.courier.receive(packet(0));await first;
  assert.equal(f.saved.length,1);assert.equal(f.ledger.records[0].response_unknown,false);
  assert.equal(f.ledger.records[1].request_unknown,false);
  const second=f.courier.request('mcp__codex_apps__github_fetch',{url:'fixed'},context);
  assert.equal(f.ledger.records.length,3,'Startup reserved exactly once');
  await f.courier.receive(packet(1));await second;
  assert.equal(f.saved.length,2);assert.equal(f.ledger.records[1].response_unknown,false);
  assert.equal(f.ledger.records[2].response_unknown,true);
  assert.equal(f.courier.terminalRecord().last_delivery_acknowledgement_durable,false);
  assert.equal(f.courier.terminalRecord().execution_authorized,false);
});

test('unreserved oversized actual delivery cannot reconcile or reach connector caller',async()=>{
  const f=fixture();const call=f.courier.request('mcp__codex_apps__github_fetch',{},
    {request_view:null,response_reserved_bytes:1024});call.catch(()=>{});
  await assert.rejects(f.courier.receive(packet(0,{padding:'x'.repeat(400000)})),/exceeded prospective reservation/);
  assert.equal(f.saved.length,0);assert.equal(f.ledger.records[1].request_unknown,true);
  f.courier.fail(Error('fixture closed'));
});

test('unterminated stdin is bounded before line parsing or additional allocation',()=>{
  const lines=[],framer=new BoundedLines(line=>lines.push(line),16);
  framer.accept(Buffer.from('first\nse'));framer.accept(Buffer.from('cond\n'));
  assert.deepEqual(lines,['first','second']);
  framer.accept(Buffer.alloc(16,120));assert.equal(framer.bytes,16);
  assert.throws(()=>framer.accept(Buffer.from('x')),/bounded allocation/);
  assert.equal(framer.bytes,16);assert.equal(lines.length,2);
});

test('lost supporting acknowledgement keeps its entire unknown reservation',async()=>{
  const f=fixture();const call=f.courier.request('mcp__codex_apps__github_fetch',{},
    {request_view:null,response_reserved_bytes:65536});call.catch(()=>{});
  f.courier.fail(Error('lost reply'));await assert.rejects(call,/lost reply/);
  assert.equal(f.ledger.totals.unknown_response_count,2);
  assert.equal(f.ledger.records[1].request_unknown,true);assert.equal(f.ledger.stopped,true);
});
