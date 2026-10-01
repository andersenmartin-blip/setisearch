'use strict';
// Qualified-cap component wrapper. Exactly one additional visible tool call
// stores the small caller-only tail. Host custody remains a separate input.
// This code grants no execution, reservation, RNG or publication authority.
const WRAPPER_SCHEMA='radio-native-v2-qualified-caller-component-v1';
const PERSISTENCE_SCHEMA='radio-native-v2-caller-transcript-persistence-v2';
const TAIL_SCHEMA='radio-native-v2-caller-only-tail-v2';
const READBACK_SCHEMA='radio-native-v2-caller-tail-readback-v1';
const MIB=1024*1024;
const CAPS=Object.freeze({actual_calls:59,request_bytes:40*MIB,response_bytes:64*MIB-256*1024,
  support_yield_time_ms:30000,caller_tail_calls:1,caller_tail_request_bytes:8*MIB,
  caller_tail_response_bytes:256*1024});
// exec_command's shell -c command itself is one OS argument. The larger
// original tool allocation must not be mistaken for a permissible argv size.
const TAIL_COMPONENT_LIMITS=Object.freeze({command_bytes:96*1024,base64_bytes:62*1024,
  payload_bytes:Math.floor(62*1024/4)*3,helper_source_bytes:65536});
const AUTHORITY=Object.freeze({execution_authorized:false,reservation_authorized:false,
  scientific_execution_authorized:false,rng_draws:0,telescope_reads:0,automatic_retry:false});
const assert=(ok,message)=>{if(!ok)throw Error(message);};
const USAGE_FIELDS=Object.freeze(['calls','request_bytes','response_bytes','response_charged_bytes',
  'unknown_response_bytes','unknown_response_count','conservatively_charged_local_git_processes',
  'calls_including_declared_git_processes']);

function clientBindingProjection(client) {
  const usage={};
  for(const key of USAGE_FIELDS){assert(Number.isSafeInteger(client.usage[key])&&client.usage[key]>=0,
    'Exact integer caller binding counters required');usage[key]=client.usage[key];}
  assert(Number.isFinite(client.usage.elapsed_seconds)&&client.usage.elapsed_seconds>=0,
    'Finite caller elapsed time required');
  usage.elapsed_milliseconds=Math.ceil(client.usage.elapsed_seconds*1000);
  const records=client.records.map(r=>({ordinal:r.ordinal,kind:r.kind,tool:r.tool,
    request_bytes:r.request_bytes,request_sha256:r.request_sha256,
    response_bytes:r.response_bytes,response_sha256:r.response_sha256}));
  return {schema:'radio-native-v2-caller-binding-v1',prospective_caps:client.prospective_caps,records,usage};
}
function clientBindingSha256(client,h) {return h.sha256(h.canonical(clientBindingProjection(client)));}
// Python's existing canonical JSON uses ensure_ascii=True. This restricted
// projection has only integers and strings; its ASCII escaping is exact and
// does not need to reproduce Python's floating-point JSON formatting.
function asciiCanonical(value) {
  if(Array.isArray(value))return '['+value.map(asciiCanonical).join(',')+']';
  if(value&&typeof value==='object')return '{'+Object.keys(value).sort().map(k=>
    asciiCanonical(k)+':'+asciiCanonical(value[k])).join(',')+'}';
  assert(typeof value==='string'||Number.isSafeInteger(value),'Only tail strings/integers required');
  return JSON.stringify(value).replace(/[\u007f-\uffff]/g,ch=>'\\u'+ch.charCodeAt(0).toString(16).padStart(4,'0'));
}
function callerTailPayload(client,h) {
  const deliveries=client.records.filter(r=>r.kind==='actual_delivery');
  assert(deliveries.length===6,'Exact final delivery acknowledgement required');
  const terminalOrdinal=deliveries[deliveries.length-1].ordinal;
  return asciiCanonical({schema:TAIL_SCHEMA,client_sha256:clientBindingSha256(client,h),
    records:client.records.filter(r=>r.kind==='actual_idle_poll'||r.ordinal===terminalOrdinal)
      .map(r=>({ordinal:r.ordinal,response_json:r.response_json}))});
}
function base64Ascii(value) {
  assert(/^[\x00-\x7f]*$/.test(value),'Canonical ASCII tail required');
  const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';let out='';
  for(let i=0;i<value.length;i+=3){const a=value.charCodeAt(i),b=value.charCodeAt(i+1),c=value.charCodeAt(i+2);
    const word=a<<16|(Number.isNaN(b)?0:b)<<8|(Number.isNaN(c)?0:c);
    out+=alphabet[word>>>18&63]+alphabet[word>>>12&63]+(i+1<value.length?alphabet[word>>>6&63]:'=')+
      (i+2<value.length?alphabet[word&63]:'=');}
  return out;
}
function absolutePath(value) {
  assert(typeof value==='string'&&/^\/[A-Za-z0-9_./-]+$/.test(value)&&
    value.slice(1).split('/').every(x=>x&&x!=='.'&&x!=='..'),'Pinned canonical absolute path required');return value;
}
const quote=value=>"'"+String(value).replace(/'/g,"'\\''")+"'";
function tailArguments(options,payload,client,h) {
  const encoded=base64Ascii(payload);
  assert(h.utf8Bytes(payload)<=TAIL_COMPONENT_LIMITS.payload_bytes&&encoded.length<=TAIL_COMPONENT_LIMITS.base64_bytes,
    'Caller-only tail exceeds the bounded OS argument component; no tail dispatch');
  const bootstrap='import os,sys,hashlib; p=sys.argv[1]; f=os.open(p,os.O_RDONLY|os.O_NOFOLLOW); '+
    's=os.read(f,65537); os.close(f); assert len(s)<=65536 and hashlib.sha256(s).hexdigest()==sys.argv[2], '+
    '"Pinned caller-tail helper source differs"; sys.argv=[p]+sys.argv[3:]; '+
    'exec(compile(s,p,"exec"),{"__name__":"__main__","__file__":p})';
  const terminalOrdinal=client.records.filter(r=>r.kind==='actual_delivery').at(-1).ordinal;
  const argv=[options.python,'-I','-S','-B','-c',bootstrap,options.tail_helper_path,options.tail_helper_sha256,
    '--destination',options.caller_tail_path,'--payload-base64',encoded,'--expected-bytes',h.utf8Bytes(payload),
    '--expected-sha256',h.sha256(payload),'--client-sha256',clientBindingSha256(client,h),
    '--terminal-ordinal',terminalOrdinal];
  const args={cmd:argv.map(quote).join(' '),max_output_tokens:4096,yield_time_ms:30000};
  assert(h.utf8Bytes(args.cmd)<=TAIL_COMPONENT_LIMITS.command_bytes,
    'Caller-tail command exceeds the bounded shell OS argument; no tail dispatch');
  return args;
}
function validateClient(client,h) {
  assert(client.status==='SINGLE_CASE_COMPONENT_COMPLETE'&&client.reason===null&&client.connector_requests===6&&
    client.pending_delivery_reservation===null&&client.last_supporting_acknowledgement_durable===false,
    'Complete unchanged courier component required before tail custody');
  assert(h.canonical(client.prospective_caps)===h.canonical(CAPS),'Tail capacity must be reserved before startup');
  for(const [key,value] of Object.entries(AUTHORITY))assert(client[key]===value,'Courier cannot grant authority');
  for(let i=0;i<client.records.length;i++){
    const r=client.records[i];
    assert(r.ordinal===i&&r.response_unknown===false&&r.automatic_retry===false&&
      h.utf8Bytes(r.request_json)===r.request_bytes&&h.sha256(r.request_json)===r.request_sha256&&
      h.utf8Bytes(r.response_json)===r.response_bytes&&h.sha256(r.response_json)===r.response_sha256&&
      JSON.stringify(r.raw_result)===r.response_json,'Complete unchanged raw caller envelopes required');
  }
  const u=client.usage;
  assert(client.records.filter(r=>r.kind==='actual_idle_poll').length<=7,
    'At most seven prospectively reserved idle polls are permitted');
  assert(u.calls===client.records.length&&u.calls<=CAPS.actual_calls&&u.request_bytes<=CAPS.request_bytes&&
    u.response_bytes<=CAPS.response_bytes&&u.response_charged_bytes===u.response_bytes&&
    u.unknown_response_bytes===0&&u.unknown_response_count===0&&
    u.request_bytes===client.records.reduce((n,r)=>n+r.request_bytes,0)&&
    u.response_bytes===client.records.reduce((n,r)=>n+r.response_bytes,0),
    'Exact reduced-cap caller accounting required');
}
function validateObservation(value,context) {
  assert(value&&value.schema==='radio-native-v2-independent-client-rss-v1'&&value.measured===true&&
    value.client_sha256===context.client_sha256&&
    value.observer_source==='independent_procfs'&&Number.isSafeInteger(value.client_peak_rss_bytes)&&
    value.client_peak_rss_bytes>0&&value.client_peak_rss_bytes<=512*MIB&&
    typeof value.caller_runtime_identity==='string'&&value.caller_runtime_identity.length>0&&
    typeof value.observer_runtime_identity==='string'&&value.observer_runtime_identity.length>0&&
    value.caller_runtime_identity!==value.observer_runtime_identity&&
    Number.isSafeInteger(value.interval_start_epoch_ms)&&Number.isSafeInteger(value.interval_end_epoch_ms)&&
    value.interval_start_epoch_ms<=context.dispatch_at_epoch_ms&&
    value.interval_end_epoch_ms>=context.returned_at_epoch_ms,
    'Independent actual caller RSS observation covering the entire run is required');
  return value;
}

async function runQualifiedToolCourier(tools,options) {
  const h=options.hostLibrary||options.h,clock=options.clock||Date.now,started=clock();
  let client=null,persistence=null,tailRecord=null,observation=null,reason=null,status='CLOSED_FAILED';
  const reservation={calls:1,request_bytes:CAPS.caller_tail_request_bytes,
    response_bytes:CAPS.caller_tail_response_bytes,...TAIL_COMPONENT_LIMITS,
    reserved_before_startup:true,dispatch_at_epoch_ms:started};
  try {
    assert(h&&typeof h.sha256==='function'&&typeof h.utf8Bytes==='function'&&typeof h.canonical==='function',
      'Pinned portable hash/byte/canonical library required');
    const clientLibrary=options.clientLibrary||(typeof module!=='undefined'?
      require('./radio_native_v2_tool_courier_client'):null);
    assert(clientLibrary&&typeof clientLibrary.runToolCourier==='function','Pinned portable client library required');
    absolutePath(options.python);absolutePath(options.tail_helper_path);absolutePath(options.caller_tail_path);
    assert(typeof options.tail_helper_sha256==='string'&&/^[0-9a-f]{64}$/.test(options.tail_helper_sha256),
      'Immutable caller-tail helper source pin required before startup');
    assert(options.startup_arguments&&options.startup_arguments.yield_time_ms===30000,
      'Prospectively pinned 30-second startup wait required');
    assert(options.production!==true||typeof options.read_actual_client_rss==='function',
      'Production mode requires independent actual caller RSS observation before startup');
    // A small source shape must not silently borrow the maximum-size case's
    // read slots for additional idle polls. Refuse the eighth before SDK use.
    let idlePolls=0;
    const guardedTools=Object.create(tools);
    guardedTools.write_stdin=async args=>{
      if(args.chars===''){
        assert(idlePolls<7,'Eighth idle poll refused before actual tool dispatch; no retry');
        idlePolls++;
      }
      return tools.write_stdin(args);
    };
    client=await clientLibrary.runToolCourier(guardedTools,{...options,max_actual_calls:CAPS.actual_calls,
      max_request_bytes:CAPS.request_bytes,max_response_bytes:CAPS.response_bytes,support_yield_time_ms:30000});
    validateClient(client,h);
    const payload=callerTailPayload(client,h),args=tailArguments(options,payload,client,h),
      requestJson=JSON.stringify({tool:'exec_command',arguments:args}),requestBytes=h.utf8Bytes(requestJson);
    assert(requestBytes<=CAPS.caller_tail_request_bytes,'Complete actual tail request exceeds its prospective allocation');
    assert(clock()-started<600000,'Shared case deadline expired before tail custody');
    const dispatched=clock();assert(Number.isSafeInteger(dispatched),'Actual integer tail dispatch time required');
    tailRecord={tool:'exec_command',kind:'actual_caller_tail_persistence',request_json:requestJson,
      request_bytes:requestBytes,request_sha256:h.sha256(requestJson),
      response_reserved_bytes:CAPS.caller_tail_response_bytes,response_unknown:true,
      response_charged_bytes:CAPS.caller_tail_response_bytes,dispatch_at_epoch_ms:dispatched,
      automatic_retry:false};
    let timer;
    try {
      const timeout=new Promise((resolve,reject)=>{timer=(options.setTimer||setTimeout)(()=>
        reject(Error('Caller-tail acknowledgement lost; no retry')),Math.min(120000,600000-(clock()-started)));});
      const raw=await Promise.race([Promise.resolve().then(()=>tools.exec_command(args)),timeout]),json=JSON.stringify(raw),
        returned=clock();
      assert(typeof json==='string','Complete actual tail reply envelope required');
      Object.assign(tailRecord,{raw_result:raw,response_json:json,response_bytes:h.utf8Bytes(json),
        response_sha256:h.sha256(json),response_unknown:false,response_charged_bytes:h.utf8Bytes(json),
        returned_at_epoch_ms:returned,elapsed_seconds:(returned-dispatched)/1000});
      assert(Number.isSafeInteger(returned)&&returned>=dispatched&&clock()-started<=600000&&
        tailRecord.response_bytes<=CAPS.caller_tail_response_bytes,
        'Caller-tail reply exceeded its prospective byte/time allocation');
      assert(raw&&raw.exit_code===0&&raw.session_id===undefined&&raw.isError!==true&&typeof raw.output==='string',
        'Complete successful one-call caller-tail write/readback required');
      const receipt=JSON.parse(raw.output.trim()),selected=JSON.parse(payload),ordinals=selected.records.map(r=>r.ordinal);
      assert(receipt.schema===READBACK_SCHEMA&&receipt.destination===options.caller_tail_path&&
        receipt.client_sha256===selected.client_sha256&&receipt.payload_bytes===h.utf8Bytes(payload)&&
        receipt.payload_sha256===h.sha256(payload)&&receipt.reopened_bytes===receipt.payload_bytes&&
        receipt.reopened_sha256===receipt.payload_sha256&&receipt.durable===true&&
        receipt.single_authoritative_file===true&&receipt.exact_readback_verified===true&&
        receipt.directory_entry_fsynced===true&&receipt.independent_reopen===true&&
        receipt.includes_terminal_delivery_acknowledgement===true&&receipt.automatic_retry===false&&
        JSON.stringify(receipt.stored_record_ordinals)===JSON.stringify(ordinals),
        'Independent exact caller-tail write/hash/readback receipt differs');
      for(const [key,value] of Object.entries(AUTHORITY))assert(receipt[key]===value,'Tail custody cannot grant authority');
      persistence={schema:PERSISTENCE_SCHEMA,client_sha256:selected.client_sha256,stored_record_ordinals:ordinals,
        payload_bytes:receipt.payload_bytes,payload_sha256:receipt.payload_sha256,durable:true,
        single_authoritative_file:true,exact_readback_verified:true,includes_terminal_delivery_acknowledgement:true,
        calls:1,unknown_response_bytes:0,unknown_response_count:0,...tailRecord,automatic_retry:false};
    }finally{(options.clearTimer||clearTimeout)(timer);}
    if(typeof options.read_actual_client_rss==='function'){
      const context={dispatch_at_epoch_ms:started,returned_at_epoch_ms:clock(),client_sha256:persistence.client_sha256};
      const remaining=600000-(clock()-started);let rssTimer;
      assert(remaining>0,'Shared case deadline expired before RSS observation');
      try {
        const timeout=new Promise((resolve,reject)=>{rssTimer=(options.setTimer||setTimeout)(()=>
          reject(Error('Independent caller RSS observation deadline lost; no retry')),Math.min(120000,remaining));});
        const value=await Promise.race([Promise.resolve().then(()=>options.read_actual_client_rss(context)),timeout]);
        assert(clock()-started<=600000,'Shared case deadline expired during RSS observation');
        observation=validateObservation(value,context);
      }finally{(options.clearTimer||clearTimeout)(rssTimer);}
      status='SINGLE_CASE_TRANSPORT_COMPONENT_COMPLETE';
    }else{status='CLOSED_UNQUALIFIED';reason='Actual caller-runtime RSS remains unmeasured';}
  }catch(error){reason=String(error);if(tailRecord)tailRecord.error=reason;}
  const returned=clock();
  if(persistence){persistence.shared_case_started_at_epoch_ms=started;persistence.shared_case_finished_at_epoch_ms=returned;
    persistence.shared_case_elapsed_seconds=(returned-started)/1000;}
  const u=client&&client.usage,combined=u?{calls:u.calls_including_declared_git_processes+(tailRecord?1:0),
    request_bytes:u.request_bytes+(tailRecord?tailRecord.request_bytes:0),
    response_bytes:u.response_bytes+(tailRecord&&tailRecord.response_bytes||0),
    response_charged_bytes:u.response_charged_bytes+(tailRecord?tailRecord.response_charged_bytes:0),
    unknown_response_bytes:u.unknown_response_bytes+(tailRecord&&tailRecord.response_unknown?CAPS.caller_tail_response_bytes:0),
    unknown_response_count:u.unknown_response_count+(tailRecord&&tailRecord.response_unknown?1:0),
    elapsed_seconds:(returned-started)/1000,all_visible_polls_and_deliveries_counted:true,
    hidden_http_bytes_known:false}:null;
  return {schema:WRAPPER_SCHEMA,status,reason,client,persistence,tail_record:tailRecord,tail_reservation:reservation,
    dispatch_at_epoch_ms:started,returned_at_epoch_ms:returned,
    prospective_caps:{...CAPS},combined_usage:combined,host_custody:options.host_custody||null,
    client_rss_observation:observation,actual_client_runtime_rss_known:observation!==null,
    host_custody_qualified:false,caller_rss_observation_scope:'startup_through_tail_before_observer_accessor',
    bounded_tail_component_only:true,full_worst_case_tail_size_qualified:false,
    ...AUTHORITY};
}
if(typeof module!=='undefined')module.exports={WRAPPER_SCHEMA,PERSISTENCE_SCHEMA,TAIL_SCHEMA,READBACK_SCHEMA,
  CAPS,TAIL_COMPONENT_LIMITS,clientBindingProjection,clientBindingSha256,callerTailPayload,asciiCanonical,
  runQualifiedToolCourier};
