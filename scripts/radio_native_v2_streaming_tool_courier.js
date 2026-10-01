'use strict';
// Separate prospective two-call stdin transport; historical one-call custody
// remains unchanged. No execution, reservation or science authority is granted.
const SCHEMA='radio-native-v2-streaming-qualified-caller-component-v1';
const PERSISTENCE_SCHEMA='radio-native-v2-caller-transcript-persistence-v3';
const READY_SCHEMA='radio-native-v2-streaming-caller-tail-ready-v1';
const READBACK_SCHEMA='radio-native-v2-streaming-caller-tail-readback-v1';
const MIB=1024*1024;
const CAPS=Object.freeze({actual_calls:58,request_bytes:40*MIB,response_bytes:64*MIB-256*1024,
  support_yield_time_ms:30000,caller_tail_calls:2,caller_tail_request_bytes:8*MIB,
  caller_tail_response_bytes:256*1024});
const MAX_RAW_BYTES=7*256*1024,MAX_WIRE_BYTES=2*MAX_RAW_BYTES+2048,
  MAX_BASE64_BYTES=Math.ceil(MAX_WIRE_BYTES/3)*4,MAX_CANONICAL_BYTES=6*MAX_RAW_BYTES+2048;
const LIMITS=Object.freeze({polls:6,tail_records:7,raw_envelope_bytes:256*1024,
  raw_bytes:MAX_RAW_BYTES,wire_bytes:MAX_WIRE_BYTES,base64_bytes:MAX_BASE64_BYTES,
  canonical_bytes:MAX_CANONICAL_BYTES,command_bytes:96*1024,helper_source_bytes:65536,
  startup_response_bytes:4096,transfer_response_bytes:256*1024-4096});
const AUTHORITY=Object.freeze({execution_authorized:false,reservation_authorized:false,
  scientific_execution_authorized:false,rng_draws:0,telescope_reads:0,automatic_retry:false});
const assert=(ok,message)=>{if(!ok)throw Error(message);};
const quote=value=>"'"+String(value).replace(/'/g,"'\\''")+"'";
function absolutePath(value){assert(typeof value==='string'&&value.length<=4096&&
  /^\/[A-Za-z0-9_./-]+$/.test(value)&&value.slice(1).split('/').every(x=>x&&x!=='.'&&x!=='..'),
  'Canonical absolute streaming-tail path required');return value;}
function projectionLibrary(options){return options.projectionLibrary||(typeof module!=='undefined'?
  require('./radio_native_v2_qualified_tool_courier'):null);}
function utf8Base64(value){
  const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  let word=0,count=0,part='';const pieces=[];
  function emit(text){part+=text;if(part.length>=8192){pieces.push(part);part='';}}
  function byte(n){word=word<<8|n;if(++count===3){emit(alphabet[word>>>18&63]+alphabet[word>>>12&63]+
    alphabet[word>>>6&63]+alphabet[word&63]);word=0;count=0;}}
  for(const char of value){const cp=char.codePointAt(0);
    assert(!(cp>=0xd800&&cp<=0xdfff),'Complete UTF-8 JSON string required');
    if(cp<=127)byte(cp);else if(cp<=2047){byte(0xc0|cp>>>6);byte(0x80|cp&63);}
    else if(cp<=65535){byte(0xe0|cp>>>12);byte(0x80|cp>>>6&63);byte(0x80|cp&63);}
    else{byte(0xf0|cp>>>18);byte(0x80|cp>>>12&63);byte(0x80|cp>>>6&63);byte(0x80|cp&63);}}
  if(count===1)emit(alphabet[word>>>2&63]+alphabet[word<<4&63]+'==');
  if(count===2)emit(alphabet[word>>>10&63]+alphabet[word>>>4&63]+alphabet[word<<2&63]+'=');
  pieces.push(part);return pieces.join('');
}
function planStreamingTail(options,client,h){
  const library=projectionLibrary(options);assert(library&&typeof library.callerTailPayload==='function',
    'Pinned existing caller binding/tail projection library required');
  absolutePath(options.python);absolutePath(options.tail_helper_path);absolutePath(options.caller_tail_path);
  assert(typeof options.tail_helper_sha256==='string'&&/^[0-9a-f]{64}$/.test(options.tail_helper_sha256),
    'Immutable streaming helper source pin required');
  const deliveries=client.records.filter(r=>r.kind==='actual_delivery');
  assert(deliveries.length===6,'Complete final caller delivery acknowledgement required');
  const ordinal=deliveries.at(-1).ordinal,selected=client.records.filter(r=>r.kind==='actual_idle_poll'||r.ordinal===ordinal);
  assert(selected.length<=LIMITS.tail_records&&selected.every(r=>r.response_bytes<=LIMITS.raw_envelope_bytes)&&
    selected.reduce((n,r)=>n+r.response_bytes,0)<=LIMITS.raw_bytes,
    'Streaming tail cannot fit prospectively reserved raw-envelope bounds');
  const clientSha=library.clientBindingSha256(client,h),value={schema:'radio-native-v2-caller-only-tail-v2',
    client_sha256:clientSha,records:selected.map(r=>({ordinal:r.ordinal,response_json:r.response_json}))};
  // Compact UTF-8 wire avoids Python ensure_ascii's sixfold DEL expansion.
  const wire=h.canonical(value),payload=library.asciiCanonical(value),encoded=utf8Base64(wire);
  assert(h.utf8Bytes(wire)<=LIMITS.wire_bytes&&h.utf8Bytes(payload)<=LIMITS.canonical_bytes&&
    encoded.length<=LIMITS.base64_bytes,'Streaming input/canonical output exceeds the prospective bounds');
  const pins={wire_bytes:h.utf8Bytes(wire),wire_sha256:h.sha256(wire),payload_bytes:h.utf8Bytes(payload),
    payload_sha256:h.sha256(payload),client_sha256:clientSha,terminal_ordinal:ordinal};
  const bootstrap='import os,sys,hashlib; p=sys.argv[1]; f=os.open(p,os.O_RDONLY|os.O_NOFOLLOW); '+
    's=os.read(f,65537); os.close(f); assert len(s)<=65536 and hashlib.sha256(s).hexdigest()==sys.argv[2], '+
    '"Pinned streaming caller-tail helper source differs"; sys.argv=[p]+sys.argv[3:]; '+
    'exec(compile(s,p,"exec"),{"__name__":"__main__","__file__":p})';
  const argv=[options.python,'-I','-S','-B','-c',bootstrap,options.tail_helper_path,options.tail_helper_sha256,
    '--destination',options.caller_tail_path,'--wire-bytes',pins.wire_bytes,'--wire-sha256',pins.wire_sha256,
    '--payload-bytes',pins.payload_bytes,'--payload-sha256',pins.payload_sha256,
    '--client-sha256',pins.client_sha256,'--terminal-ordinal',ordinal];
  const startup={cmd:argv.map(quote).join(' '),tty:true,max_output_tokens:4096,yield_time_ms:1000};
  assert(h.utf8Bytes(startup.cmd)<=LIMITS.command_bytes,'Streaming startup exceeds bounded OS command argument');
  const prospective={session_id:Number.MAX_SAFE_INTEGER,chars:encoded+'\n',max_output_tokens:4096,yield_time_ms:30000},
    requestBound=h.utf8Bytes(JSON.stringify({tool:'exec_command',arguments:startup}))+
      h.utf8Bytes(JSON.stringify({tool:'write_stdin',arguments:prospective}));
  assert(requestBound<=CAPS.caller_tail_request_bytes,'Both whole tail requests cannot fit before any tail dispatch');
  return {payload,wire,encoded,pins,startup_arguments:startup,prospective_request_bytes:requestBound,
    stored_record_ordinals:selected.map(r=>r.ordinal)};
}
async function executeStreamingTail(tools,options,client){
  const h=options.hostLibrary||options.h,clock=options.clock||Date.now,started=options.shared_started_at_epoch_ms??clock();
  const records=[],reservation={calls:2,request_bytes:CAPS.caller_tail_request_bytes,
    response_bytes:CAPS.caller_tail_response_bytes,reserved_before_startup:true,
    stored_bytes:MAX_CANONICAL_BYTES,stored_items:1,storage_kind:'host_receipt',...LIMITS};
  let persistence=null,reason=null,status='CLOSED_FAILED';
  async function call(tool,args,responseReservation,kind){
    assert(clock()-started<600000,'Shared case deadline expired before streaming tail dispatch');
    const json=JSON.stringify({tool,arguments:args}),row={ordinal:records.length,tool,kind,request_json:json,
      request_bytes:h.utf8Bytes(json),request_sha256:h.sha256(json),response_reserved_bytes:responseReservation,
      response_unknown:true,response_charged_bytes:responseReservation,dispatch_at_epoch_ms:clock(),automatic_retry:false};
    assert(Number.isSafeInteger(row.dispatch_at_epoch_ms),'Exact streaming dispatch timestamp required');
    records.push(row);let timer;
    try{
      const timeout=new Promise((resolve,reject)=>{timer=(options.setTimer||setTimeout)(()=>
        reject(Error('Streaming tail acknowledgement lost; no retry')),Math.min(120000,600000-(clock()-started)));});
      const raw=await Promise.race([Promise.resolve().then(()=>tools[tool](args)),timeout]),response=JSON.stringify(raw),returned=clock();
      assert(typeof response==='string','Complete raw streaming tool envelope required');
      Object.assign(row,{response_json:response,response_bytes:h.utf8Bytes(response),response_sha256:h.sha256(response),
        raw_result:raw,response_unknown:false,response_charged_bytes:h.utf8Bytes(response),returned_at_epoch_ms:returned,
        elapsed_seconds:(returned-row.dispatch_at_epoch_ms)/1000});
      assert(Number.isSafeInteger(returned)&&returned>=row.dispatch_at_epoch_ms&&clock()-started<=600000&&
        row.response_bytes<=responseReservation,'Streaming reply exceeded prospective byte/time reservation');
      return raw;
    }catch(error){row.error=String(error);throw error;}finally{(options.clearTimer||clearTimeout)(timer);}
  }
  try{
    assert(tools&&typeof tools.exec_command==='function'&&typeof tools.write_stdin==='function',
      'Actual streaming startup and transfer tools required');
    const plan=planStreamingTail(options,client,h),raw=await call('exec_command',plan.startup_arguments,
      LIMITS.startup_response_bytes,'actual_caller_tail_start');
    assert(raw&&typeof raw.output==='string'&&raw.isError!==true&&raw.exit_code===undefined&&
      Number.isSafeInteger(raw.session_id)&&raw.session_id>0,'Complete running streaming helper startup required');
    const ready=JSON.parse(raw.output.trim());
    assert(ready.schema===READY_SCHEMA&&ready.kind==='ready'&&ready.destination===options.caller_tail_path&&
      ready.input_encoding==='base64_utf8_json'&&ready.stdin_raw_noecho_ready===true&&
      ready.stdin_is_tty===true&&ready.stdin_mode==='tty_raw_noecho'&&
      ready.maximum_base64_bytes===LIMITS.base64_bytes&&ready.max_stdin_bytes===LIMITS.base64_bytes+1&&
      Object.entries(plan.pins).every(([key,value])=>ready[key]===value)&&
      Object.entries(AUTHORITY).every(([key,value])=>ready[key]===value),'Exact pinned raw/noecho READY receipt required');
    const args={session_id:raw.session_id,chars:plan.encoded+'\n',max_output_tokens:4096,yield_time_ms:30000};
    assert(records[0].request_bytes+h.utf8Bytes(JSON.stringify({tool:'write_stdin',arguments:args}))<=
      CAPS.caller_tail_request_bytes,'Exact streaming requests exceed their original prospective allocation');
    const final=await call('write_stdin',args,LIMITS.transfer_response_bytes,'actual_caller_tail_transfer');
    assert(final&&final.exit_code===0&&final.session_id===undefined&&final.isError!==true&&typeof final.output==='string',
      'Streaming transfer must return complete terminal readback; no third call or retry');
    const receipt=JSON.parse(final.output.trim());
    assert(receipt.schema===READBACK_SCHEMA&&receipt.destination===options.caller_tail_path&&
      ['wire_bytes','wire_sha256','payload_bytes','payload_sha256','client_sha256'].every(k=>receipt[k]===plan.pins[k])&&
      JSON.stringify(receipt.stored_record_ordinals)===JSON.stringify(plan.stored_record_ordinals)&&
      receipt.reopened_bytes===plan.pins.payload_bytes&&receipt.reopened_sha256===plan.pins.payload_sha256&&
      ['durable','single_authoritative_file','exact_readback_verified','directory_entry_fsynced','independent_reopen',
        'includes_terminal_delivery_acknowledgement'].every(k=>receipt[k]===true)&&
      Object.entries(AUTHORITY).every(([key,value])=>receipt[key]===value),'Exact independently reopened streaming tail receipt required');
    persistence={schema:PERSISTENCE_SCHEMA,client_sha256:plan.pins.client_sha256,
      stored_record_ordinals:plan.stored_record_ordinals,payload_bytes:plan.pins.payload_bytes,payload_sha256:plan.pins.payload_sha256,
      durable:true,single_authoritative_file:true,exact_readback_verified:true,includes_terminal_delivery_acknowledgement:true,
      automatic_retry:false,calls:2,request_bytes:records.reduce((n,r)=>n+r.request_bytes,0),
      stored_bytes:plan.pins.payload_bytes,stored_items:1,stored_bytes_reserved:MAX_CANONICAL_BYTES,storage_kind:'host_receipt',
      response_bytes:records.reduce((n,r)=>n+r.response_bytes,0),unknown_response_bytes:0,unknown_response_count:0,
      dispatch_at_epoch_ms:records[0].dispatch_at_epoch_ms,returned_at_epoch_ms:records[1].returned_at_epoch_ms,
      elapsed_seconds:(records[1].returned_at_epoch_ms-records[0].dispatch_at_epoch_ms)/1000,records};
    status='TAIL_CUSTODY_COMPONENT_COMPLETE';
  }catch(error){reason=String(error);}
  return {schema:SCHEMA,status,reason,persistence,records,reservation,actual_client_runtime_rss_known:false,
    host_custody_qualified:false,...AUTHORITY};
}
function validateClient(client,h){
  assert(client.status==='SINGLE_CASE_COMPONENT_COMPLETE'&&client.reason===null&&client.connector_requests===6&&
    client.pending_delivery_reservation===null&&client.last_supporting_acknowledgement_durable===false&&
    h.canonical(client.prospective_caps)===h.canonical(CAPS),'Complete prospectively reserved two-call client required');
  assert(Object.entries(AUTHORITY).every(([key,value])=>client[key]===value),'Client cannot grant authority');
  assert(client.records.filter(r=>r.kind==='actual_idle_poll').length<=LIMITS.polls,'At most six caller polls permitted');
  for(let i=0;i<client.records.length;i++){const r=client.records[i];assert(r.ordinal===i&&r.response_unknown===false&&
    r.automatic_retry===false&&h.utf8Bytes(r.request_json)===r.request_bytes&&h.sha256(r.request_json)===r.request_sha256&&
    h.utf8Bytes(r.response_json)===r.response_bytes&&h.sha256(r.response_json)===r.response_sha256&&
    JSON.stringify(r.raw_result)===r.response_json,'Complete unchanged streaming caller envelopes required');}
  const u=client.usage;assert(u.calls===client.records.length&&u.calls<=CAPS.actual_calls&&
    u.request_bytes<=CAPS.request_bytes&&u.response_bytes<=CAPS.response_bytes&&u.response_charged_bytes===u.response_bytes&&
    u.unknown_response_count===0&&u.unknown_response_bytes===0&&
    u.request_bytes===client.records.reduce((n,r)=>n+r.request_bytes,0)&&u.response_bytes===client.records.reduce((n,r)=>n+r.response_bytes,0),
    'Exact reduced-cap two-call client accounting required');
}
async function runStreamingToolCourier(tools,options){
  const h=options.hostLibrary||options.h,clock=options.clock||Date.now,started=clock();
  let client=null,tail=null,observation=null,status='CLOSED_FAILED',reason=null;
  const reservation={calls:2,request_bytes:CAPS.caller_tail_request_bytes,response_bytes:CAPS.caller_tail_response_bytes,
    reserved_before_startup:true,dispatch_at_epoch_ms:started,
    stored_bytes:MAX_CANONICAL_BYTES,stored_items:1,storage_kind:'host_receipt',...LIMITS};
  try{
    assert(h&&typeof h.sha256==='function'&&typeof h.canonical==='function'&&typeof h.utf8Bytes==='function',
      'Pinned portable streaming hash/byte/canonical library required');
    absolutePath(options.python);absolutePath(options.tail_helper_path);absolutePath(options.caller_tail_path);
    assert(/^[0-9a-f]{64}$/.test(options.tail_helper_sha256||''),'Pinned streaming helper required before caller startup');
    assert(options.startup_arguments&&options.startup_arguments.yield_time_ms===30000,'Pinned 30-second caller startup required');
    assert(options.production!==true||typeof options.read_actual_client_rss==='function',
      'Production streaming mode requires independent actual caller RSS before startup');
    const library=options.clientLibrary||(typeof module!=='undefined'?require('./radio_native_v2_tool_courier_client'):null);
    assert(library&&typeof library.runToolCourier==='function','Pinned actual client library required');
    let polls=0;const guarded=Object.create(tools);guarded.write_stdin=async args=>{
      if(args.chars===''){assert(polls<LIMITS.polls,'Seventh caller poll refused before actual dispatch; no retry');polls++;}
      return tools.write_stdin(args);};
    client=await library.runToolCourier(guarded,{...options,max_actual_calls:CAPS.actual_calls,max_request_bytes:CAPS.request_bytes,
      max_response_bytes:CAPS.response_bytes,support_yield_time_ms:30000,caller_tail_calls:2});
    validateClient(client,h);
    tail=await executeStreamingTail(tools,{...options,shared_started_at_epoch_ms:started},client);
    assert(tail.status==='TAIL_CUSTODY_COMPONENT_COMPLETE',tail.reason||'Streaming custody component failed');
    if(typeof options.read_actual_client_rss==='function'){
      const context={dispatch_at_epoch_ms:started,returned_at_epoch_ms:clock(),client_sha256:tail.persistence.client_sha256};
      const remaining=600000-(clock()-started);let timer;assert(remaining>0,'Shared streaming deadline expired before RSS readout');
      try{
        const timeout=new Promise((resolve,reject)=>{timer=(options.setTimer||setTimeout)(()=>
          reject(Error('Streaming caller RSS observation deadline lost; no retry')),Math.min(120000,remaining));});
        const value=await Promise.race([Promise.resolve().then(()=>options.read_actual_client_rss(context)),timeout]);
        assert(clock()-started<=600000,'Shared streaming deadline expired during RSS readout');
        assert(value&&value.schema==='radio-native-v2-independent-client-rss-v1'&&value.measured===true&&
          value.client_sha256===context.client_sha256&&value.observer_source==='independent_procfs'&&
          Number.isSafeInteger(value.client_peak_rss_bytes)&&value.client_peak_rss_bytes>0&&value.client_peak_rss_bytes<=512*MIB&&
          typeof value.caller_runtime_identity==='string'&&value.caller_runtime_identity.length>0&&
          typeof value.observer_runtime_identity==='string'&&value.observer_runtime_identity.length>0&&
          value.caller_runtime_identity!==value.observer_runtime_identity&&Number.isSafeInteger(value.interval_start_epoch_ms)&&
          Number.isSafeInteger(value.interval_end_epoch_ms)&&value.interval_start_epoch_ms<=context.dispatch_at_epoch_ms&&
          value.interval_end_epoch_ms>=context.returned_at_epoch_ms,'Independent bound streaming caller RSS required');
        observation=value;
      }finally{(options.clearTimer||clearTimeout)(timer);}
      status='SINGLE_CASE_STREAMING_TRANSPORT_COMPONENT_COMPLETE';
    }else{status='CLOSED_UNQUALIFIED';reason='Actual streaming caller-runtime RSS remains unmeasured';}
  }catch(error){reason=String(error);}
  const finished=clock(),proof=tail&&tail.persistence;
  if(proof){proof.shared_case_started_at_epoch_ms=started;proof.shared_case_finished_at_epoch_ms=finished;
    proof.shared_case_elapsed_seconds=(finished-started)/1000;}
  const records=tail?tail.records:[],u=client&&client.usage;
  const combined=u?{calls:u.calls_including_declared_git_processes+records.length,
    request_bytes:u.request_bytes+records.reduce((n,r)=>n+r.request_bytes,0),
    response_bytes:u.response_bytes+records.reduce((n,r)=>n+(r.response_bytes||0),0),
    response_charged_bytes:u.response_charged_bytes+records.reduce((n,r)=>n+r.response_charged_bytes,0),
    unknown_response_bytes:u.unknown_response_bytes+records.filter(r=>r.response_unknown).reduce((n,r)=>n+r.response_reserved_bytes,0),
    unknown_response_count:u.unknown_response_count+records.filter(r=>r.response_unknown).length,
    elapsed_seconds:(finished-started)/1000,all_visible_polls_and_deliveries_counted:true,hidden_http_bytes_known:false}:null;
  return {schema:SCHEMA,status,reason,client,persistence:proof||null,tail_records:records,tail_reservation:reservation,
    prospective_caps:{...CAPS},combined_usage:combined,host_custody:options.host_custody||null,host_custody_qualified:false,
    client_rss_observation:observation,actual_client_runtime_rss_known:observation!==null,
    receipt_storage_joined_into_host_ledger:false,
    caller_rss_observation_scope:'startup_through_tail_before_observer_accessor',full_host_transport_qualified:false,
    dispatch_at_epoch_ms:started,returned_at_epoch_ms:finished,...AUTHORITY};
}
if(typeof module!=='undefined')module.exports={SCHEMA,PERSISTENCE_SCHEMA,READY_SCHEMA,READBACK_SCHEMA,CAPS,LIMITS,
  utf8Base64,planStreamingTail,executeStreamingTail,runStreamingToolCourier};
