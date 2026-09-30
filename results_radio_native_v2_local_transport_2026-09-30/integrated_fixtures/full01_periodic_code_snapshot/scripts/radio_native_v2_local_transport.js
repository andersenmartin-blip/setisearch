'use strict';
// Prospective local host. Local numerical/receipt validation stays pinned;
// functions is a courier. This module grants no execution or reservation.
const fs = require('node:fs');
const crypto = require('node:crypto');
const h = require('./radio_native_v2_broker_host');
const MIB = 1024 * 1024;
const SCHEMA = 'radio-native-v2-local-courier-host-v1';
const FIXTURE_PREFIX='results_radio_native_v2_local_transport_20260930a/live01';
const HARD = Object.freeze({cases:8,calls:512,request_bytes:384*MIB,response_bytes:512*MIB,
  case_calls:64,case_request_bytes:48*MIB,case_response_bytes:64*MIB,
  seconds:4800,case_seconds:600});
const RESERVATIONS = Object.freeze({fetch:64*1024,create_tree:4*MIB,
  create_commit:256*1024,update_ref:64*1024,git_fetch:MIB,git_cat_file_batch:MIB,
  courier_read:2*(MIB-64*1024)+16*1024,courier_delivery:64*1024});
const READ_BYTES = MIB-64*1024;
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const integer = (n,max=Number.MAX_SAFE_INTEGER) => Number.isSafeInteger(n)&&n>=0&&n<=max;
const assert = (ok,message) => {if(!ok)throw Error(message);};
const exact = (value,names) => assert(value&&typeof value==='object'&&!Array.isArray(value)&&
  Object.keys(value).sort().join()===names.slice().sort().join(),'Exact fields required');
const safeFile = filename => {
  assert(typeof filename==='string'&&/^\/[A-Za-z0-9_./-]+$/.test(filename)&&
    filename.slice(1).split('/').every(p=>p&&p!=='.'&&p!=='..'),'Canonical local file required');
  return filename;
};
function openRegular(filename) {
  safeFile(filename);
  let parent='';
  for(const part of filename.slice(1).split('/').slice(0,-1)) {
    parent+='/'+part;assert(fs.lstatSync(parent).isDirectory()&&!fs.lstatSync(parent).isSymbolicLink(),
      'Symlinked source ancestor refused');
  }
  const fd=fs.openSync(filename,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
  const stat=fs.fstatSync(fd);
  if(!stat.isFile()||stat.nlink!==1){fs.closeSync(fd);throw Error('Exclusive immutable regular source required');}
  return {fd,stat};
}
function readRange(filename,offset,bytes) {
  assert(integer(offset)&&integer(bytes,READ_BYTES),'Bounded source range required');
  const {fd,stat}=openRegular(filename);
  try {
    assert(offset+bytes<=stat.size,'Source range beyond pinned file');
    const result=Buffer.alloc(bytes);let used=0;
    while(used<bytes){const n=fs.readSync(fd,result,used,bytes-used,offset+used);assert(n>0,'Source range truncated');used+=n;}
    assert(fs.fstatSync(fd).size===stat.size,'Source changed while reading');return result;
  }finally{fs.closeSync(fd);}
}
function hashFile(filename,offset=0,length=null) {
  const {fd,stat}=openRegular(filename),hash=crypto.createHash('sha256');
  try {
    const bytes=length===null?stat.size:length;
    assert(integer(offset)&&integer(bytes,64*MIB)&&offset+bytes<=stat.size,'Bounded immutable hash range required');
    const buffer=Buffer.alloc(32768);let at=0;
    while(at<bytes){const n=fs.readSync(fd,buffer,0,Math.min(buffer.length,bytes-at),offset+at);
      assert(n>0,'Source truncated during hash');hash.update(buffer.subarray(0,n));at+=n;}
    assert(fs.fstatSync(fd).size===stat.size,'Source changed during hash');
    return {bytes,sha256:hash.digest('hex')};
  }finally{fs.closeSync(fd);}
}

class SharedLedger {
  constructor({limits=HARD,clock=Date.now}={}) {
    exact(limits,Object.keys(HARD));for(const [key,value] of Object.entries(limits))
      assert(integer(value,HARD[key])&&value>0,'Unchanged finite shared limits required');
    this.limits={...limits};this.clock=clock;this.started=clock();this.caseStart=null;
    this.caseOrdinal=-1;this.base={calls:0,request_bytes:0,response_bytes:0,response_charged_bytes:0};
    this.totals={calls:0,request_bytes:0,response_bytes:0,response_charged_bytes:0,
      unknown_response_bytes:0,unknown_response_count:0};this.records=[];this.stopped=false;
  }
  beginCase(ordinal) {
    assert(!this.stopped&&this.totals.unknown_response_count===0&&this.records.every(r=>r.request_unknown!==true)&&
      integer(ordinal,7)&&ordinal===this.caseOrdinal+1,
      'Ordered fresh shared case with no prior unknown reply required');
    this.caseOrdinal=ordinal;this.caseStart=this.clock();this.base={...this.totals};this.check();
  }
  left() {return Math.min(this.limits.seconds*1000-(this.clock()-this.started),
    this.caseStart===null?this.limits.case_seconds*1000:this.limits.case_seconds*1000-(this.clock()-this.caseStart));}
  check() {
    const c=this.caseUsage();assert(!this.stopped&&this.caseStart!==null&&this.left()>0,'Shared host closed or expired');
    for(const key of ['calls','request_bytes','response_charged_bytes']){
      const limit=key==='response_charged_bytes'?'response_bytes':key;
      assert(this.totals[key]<=this.limits[limit]&&c[key]<=this.limits['case_'+limit],
        'Shared actual tool/courier budget exhausted');}
  }
  reserve({tool,request_bytes,request_sha256,response_reservation,label='actual_tool'}) {
    this.check();assert(typeof tool==='string'&&integer(request_bytes)&&/^[0-9a-f]{64}$/.test(request_sha256)&&
      integer(response_reservation,64*MIB)&&response_reservation>0,'Exact visible envelope reservation required');
    const c=this.caseUsage(),t=this.totals;
    assert(t.calls+1<=this.limits.calls&&c.calls+1<=this.limits.case_calls&&
      t.request_bytes+request_bytes<=this.limits.request_bytes&&c.request_bytes+request_bytes<=this.limits.case_request_bytes&&
      t.response_charged_bytes+response_reservation<=this.limits.response_bytes&&
      c.response_charged_bytes+response_reservation<=this.limits.case_response_bytes,'Cannot reserve shared complete visible envelopes');
    t.calls++;t.request_bytes+=request_bytes;t.response_charged_bytes+=response_reservation;
    t.unknown_response_bytes+=response_reservation;t.unknown_response_count++;
    const row={ordinal:this.records.length,case_ordinal:this.caseOrdinal,tool,label,request_bytes,request_sha256,
      response_reserved_bytes:response_reservation,response_unknown:true,automatic_retry:false};
    this.records.push(row);return row.ordinal;
  }
  reserveUnknownRequest({tool,request_reservation,request_intent_sha256,response_reservation,label='actual_courier_delivery'}) {
    const token=this.reserve({tool,request_bytes:request_reservation,request_sha256:request_intent_sha256,
      response_reservation,label}),row=this.records[token];
    Object.assign(row,{request_reserved_bytes:request_reservation,request_unknown:true,
      request_intent_sha256});return token;
  }
  reconcileRequest(ordinal,requestJson) {
    const row=this.records[ordinal];assert(row&&row.request_unknown&&typeof requestJson==='string',
      'One pre-reserved actual courier request required');
    const bytes=Buffer.byteLength(requestJson);
    assert(bytes<=row.request_reserved_bytes,'Actual courier request exceeded prospective reservation');
    this.totals.request_bytes+=bytes-row.request_reserved_bytes;
    Object.assign(row,{request_unknown:false,request_bytes:bytes,request_sha256:sha(requestJson)});
    return {bytes,sha256:row.request_sha256};
  }
  complete(ordinal,raw,{checkDeadline=true}={}) {
    const row=this.records[ordinal];assert(row&&row.response_unknown,'One exact pending acknowledgement required');
    const json=JSON.stringify(raw);assert(typeof json==='string','Complete raw visible envelope required');
    const bytes=Buffer.byteLength(json),t=this.totals;
    t.response_bytes+=bytes;t.response_charged_bytes+=bytes-row.response_reserved_bytes;
    t.unknown_response_bytes-=row.response_reserved_bytes;t.unknown_response_count--;
    Object.assign(row,{response_unknown:false,response_bytes:bytes,response_sha256:sha(json),
      response_charged_bytes:bytes});
    if(bytes>row.response_reserved_bytes){this.stopped=true;
      if(checkDeadline)throw Error('Raw visible reply exceeded reservation');}
    if(checkDeadline)this.check();return {json,bytes,sha256:row.response_sha256};
  }
  stop(error) {this.stopped=true;this.stopReason=String(error);}
  caseUsage() {return Object.fromEntries(Object.entries(this.totals).map(([k,v])=>[k,v-(this.base[k]||0)]));}
  usage() {return {schema:SCHEMA,...this.totals,cases:this.caseOrdinal+1,
    elapsed_seconds:(this.clock()-this.started)/1000,automatic_retry:false,
    visible_tool_objects_only:false,hidden_http_bytes_known:false,
    conservatively_counted_local_process_calls:this.records.filter(r=>r.label==='conservatively_counted_local_git_process').length,
    actual_visible_tool_calls:this.records.filter(r=>r.label!=='conservatively_counted_local_git_process').length};}
}

// No second 36-MiB request file. The params value is a contiguous range of the
// already sealed canonical worker request. Only the descriptor is new storage.
function makeRequestView({tool,packet,path,bytes,sha256}) {
  assert(/^mcp__codex_apps__github_(fetch|create_tree|create_commit|update_ref)$/.test(tool),
    'Approved exact connector required');
  assert(packet&&typeof packet==='object'&&packet.params&&typeof packet.params==='object','Worker packet required');
  const checked=hashFile(path);assert(checked.bytes===bytes&&checked.sha256===sha256,'Immutable worker source pin differs');
  const withNull=h.canonical({...packet,params:null}),marker='"params":null',at=withNull.indexOf(marker);
  assert(at>=0&&withNull.indexOf(marker,at+1)===-1,'Unique worker params field required');
  const prefix=withNull.slice(0,at)+'"params":',suffix=withNull.slice(at+marker.length),offset=Buffer.byteLength(prefix),
    paramsBytes=bytes-offset-Buffer.byteLength(suffix);
  assert(paramsBytes>=2&&readRange(path,0,offset).toString('ascii')===prefix&&
    readRange(path,offset+paramsBytes,Buffer.byteLength(suffix)).toString('ascii')===suffix,
    'Worker params framing differs');
  const paramsPin=hashFile(path,offset,paramsBytes),paramsJson=JSON.stringify(packet.params);
  assert(Buffer.byteLength(paramsJson)===paramsBytes&&sha(paramsJson)===paramsPin.sha256,'Canonical worker params differ');
  const requestPrefix='{"tool":'+JSON.stringify(tool)+',"arguments":',requestSuffix='}';
  const hash=crypto.createHash('sha256').update(requestPrefix),{fd}=openRegular(path);
  try{const buffer=Buffer.alloc(32768);let used=0;while(used<paramsBytes){const n=fs.readSync(fd,buffer,0,
    Math.min(buffer.length,paramsBytes-used),offset+used);assert(n>0,'Worker params truncated');hash.update(buffer.subarray(0,n));used+=n;}}
  finally{fs.closeSync(fd);}hash.update(requestSuffix);
  return {schema:'radio-native-v2-existing-request-view-v1',path,source_bytes:bytes,source_sha256:sha256,
    offset,bytes:paramsBytes,sha256:paramsPin.sha256,request_prefix:requestPrefix,request_suffix:requestSuffix,
    request_bytes:Buffer.byteLength(requestPrefix)+paramsBytes+1,request_sha256:hash.digest('hex')};
}

// Preserve the observed property order. All fields, including token metadata,
// stay in the reconstruction; output is replaced only by an immutable source
// range. The full raw envelope hash and length are supplied independently.
function makeReadDescriptor(raw,{path,offset,bytes,source_sha256}) {
  assert(raw&&typeof raw==='object'&&!Array.isArray(raw)&&typeof raw.output==='string'&&
    raw.exit_code===0&&raw.session_id===undefined,'Completed read tool envelope required');
  const entries=Object.entries(raw).map(([key,value])=>[key,key==='output'?null:value]);
  assert(entries.length<=16&&Buffer.byteLength(JSON.stringify(entries))<=8192,'Bounded full envelope metadata required');
  const rawJson=JSON.stringify(raw);
  return {schema:'radio-native-v2-reconstructed-read-receipt-v1',path,offset,bytes,source_sha256,
    envelope_entries:entries,envelope_bytes:Buffer.byteLength(rawJson),envelope_sha256:sha(rawJson)};
}
function reconstructReadEnvelope(descriptor,expectedView) {
  exact(descriptor,['schema','path','offset','bytes','source_sha256','envelope_entries','envelope_bytes','envelope_sha256']);
  assert(descriptor.schema==='radio-native-v2-reconstructed-read-receipt-v1'&&
    /^[0-9a-f]{64}$/.test(descriptor.source_sha256)&&integer(descriptor.envelope_bytes,2*READ_BYTES+16384)&&
    /^[0-9a-f]{64}$/.test(descriptor.envelope_sha256)&&Array.isArray(descriptor.envelope_entries)&&
    descriptor.envelope_entries.length<=16,'Exact reconstructed receipt pins required');
  assert(Buffer.byteLength(JSON.stringify(descriptor.envelope_entries))<=8192,
    'Bounded complete raw envelope metadata required');
  const source=hashFile(descriptor.path);
  assert(source.sha256===descriptor.source_sha256,'Whole immutable source file pin differs');
  if(expectedView!==undefined){
    assert(expectedView&&descriptor.path===expectedView.path&&descriptor.source_sha256===expectedView.source_sha256&&
      descriptor.offset>=expectedView.offset&&descriptor.offset+descriptor.bytes<=expectedView.offset+expectedView.bytes,
      'Courier read receipt outside pre-reserved outgoing view');
    if(expectedView.next_offset!==undefined)assert(descriptor.offset===expectedView.next_offset,
      'Courier read receipt cursor differs from pinned sequential plan');
  }
  const data=readRange(descriptor.path,descriptor.offset,descriptor.bytes);
  assert(data.every(n=>n<128),'ASCII pinned outgoing JSON required');
  const raw={},seen=new Set();let outputCount=0;
  for(const entry of descriptor.envelope_entries) {
    assert(Array.isArray(entry)&&entry.length===2&&typeof entry[0]==='string'&&
      entry[0]!=='__proto__'&&!seen.has(entry[0]),'Unique exact raw envelope fields required');
    seen.add(entry[0]);if(entry[0]==='output'){assert(entry[1]===null,'Output range sentinel required');
      raw.output=data.toString('ascii');outputCount++;}else Object.defineProperty(raw,entry[0],
        {value:entry[1],enumerable:true,writable:false,configurable:false});
  }
  assert(outputCount===1&&raw.exit_code===0&&raw.session_id===undefined,'Complete successful read envelope required');
  const json=JSON.stringify(raw);assert(Buffer.byteLength(json)===descriptor.envelope_bytes&&
    sha(json)===descriptor.envelope_sha256,'Reconstructed full visible raw envelope differs');
  return {raw,json,bytes:descriptor.envelope_bytes,sha256:descriptor.envelope_sha256};
}

function makeCourierReadPlan(view,{python,ledger}) {
  assert(view&&view.schema==='radio-native-v2-existing-request-view-v1'&&ledger instanceof SharedLedger,
    'Pinned outgoing request view and shared ledger required');safeFile(python);
  assert(hashFile(view.path).sha256===view.source_sha256&&hashFile(view.path,view.offset,view.bytes).sha256===view.sha256,
    'Prospective outgoing source changed');
  const quote=value=>"'"+value.replace(/'/g,"'\\''")+"'";
  const source='import os,sys; f=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW); '+
    'n=int(sys.argv[3]); b=os.pread(f,n,int(sys.argv[2])); '+
    'assert len(b)==n; sys.stdout.buffer.write(b); os.close(f)';
  const plan=[];
  for(let relative=0;relative<view.bytes;relative+=READ_BYTES){
    const bytes=Math.min(READ_BYTES,view.bytes-relative),offset=view.offset+relative,
      args={cmd:quote(python)+' -I -S -B -c '+quote(source)+' '+quote(view.path)+' '+offset+' '+bytes,
        max_output_tokens:400000,yield_time_ms:1000},requestJson=JSON.stringify({tool:'exec_command',arguments:args}),
      data=readRange(view.path,offset,bytes);
    assert(data.every(n=>n<128),'ASCII outgoing request view required');
    // All extraction replies are outstanding until the one batched return.
    // This exact source-dependent escaping bound is reserved simultaneously.
    const responseReservation=Buffer.byteLength(JSON.stringify({output:data.toString('ascii')}))+8192,
      token=ledger.reserve({tool:'exec_command',request_bytes:Buffer.byteLength(requestJson),request_sha256:sha(requestJson),
        response_reservation:responseReservation,label:'actual_courier_read'});
    plan.push({ordinal:plan.length,ledger_token:token,tool:'exec_command',arguments:args,request_json:requestJson,
      path:view.path,offset,bytes,source_sha256:view.source_sha256,output_sha256:sha(data),
      response_reserved_bytes:responseReservation});
  }
  return plan;
}

function capacityRecord() {
  const createTreeBytes=37923633,reads=Math.ceil(createTreeBytes/READ_BYTES),connectors=6,
    // launch, final custody/status, each connector acknowledgement delivery,
    // and three explicit Git operations (candidate fetch, readback fetch,batch).
    calls=reads+connectors+connectors+3+2;
  return {schema:'radio-native-v2-local-courier-capacity-v1',maximum_request_fixture_bytes:createTreeBytes,
    read_bytes:READ_BYTES,outgoing_read_calls:reads,connector_calls:connectors,
    explicit_git_operations:3,courier_delivery_calls:connectors,control_calls:2,
    calls_per_case:calls,calls_eight_cases:calls*8,old_per_case_calls:64,old_total_calls:512,
    request_payload_crosses_tool_boundary_once:true,outgoing_request_source_copied:false,
    normalized_readback_crosses_tool_boundary:false,supporting_read_receipts_reconstructed_from_pinned_source:true,
    raw_connector_delivery_reservation_bytes:3*RESERVATIONS.fetch+RESERVATIONS.create_tree+
      RESERVATIONS.create_commit+RESERVATIONS.update_ref,
    status:'PROSPECTIVE_LOWER_LEVEL_COMPONENT_ONLY',execution_authorized:false,
    rng_draws:0,telescope_reads:0,case_reservations:0};
}

function createLocalBrokerHost(options) {
  assert(options&&options.localGit&&typeof options.localGit.immutableRead==='function'&&
    typeof options.localGit.expectedTree==='function'&&typeof options.localGit.withDeadline==='function'&&typeof options.courier==='function'&&
    typeof options.persistRaw==='function'&&typeof options.groupedGitReadback==='function'&&
    typeof options.runGit==='function','Concrete pinned local host dependencies required');
  const ledger=options.ledger||new SharedLedger(),clock=options.clock||Date.now;
  assert(options.fixture_namespace===undefined||options.fixture_namespace===FIXTURE_PREFIX,'Only the fixed prospective fixture namespace is permitted');
  const allowedPrefix=options.fixture_namespace||h.PREFIX;
  const repoPath=safeFile(options.repoPath),spoolRoot=safeFile(options.spoolRoot),gitPath=safeFile(options.gitPath||'/usr/bin/git');
  const completed=[],records=[];let freeze=null,phase={},source=null,busy=false,stopped=false,
    workerDeadline=null,receiptBytes=0,caseReceiptBase=0,gitSpoolBytes=0,caseSpoolBase=0,receiptReserved=0,
    gitSpoolUnknown=0,toolArgumentBytes=0,caseArgumentBase=0;
  const close=error=>{stopped=true;ledger.stop(error);return error;};
  const left=()=>Math.min(120000,ledger.left(),workerDeadline===null?Infinity:workerDeadline-clock());
  const check=()=>{assert(!stopped&&freeze&&left()>0,'Pinned local host closed or worker deadline exhausted');ledger.check();};
  const usage=()=>({...ledger.usage(),receipt_bytes:receiptBytes,receipt_charged_bytes:receiptBytes+receiptReserved,
    unknown_receipt_bytes:receiptReserved,git_spool_bytes:gitSpoolBytes,git_spool_charged_bytes:gitSpoolBytes+gitSpoolUnknown,
    unknown_git_spool_bytes:gitSpoolUnknown,tool_argument_bytes:toolArgumentBytes,
    local_git_metadata:options.localGit.snapshot?options.localGit.snapshot():null});
  async function boundedTask(fn) {
    check();let timer;
    const timeout=new Promise((resolve,reject)=>{timer=setTimeout(()=>reject(close(Error('Local host deadline exceeded; result uncertain'))),left());});
    try{return await Promise.race([Promise.resolve().then(()=>{check();return fn();}),timeout]);}
    catch(error){throw close(error);}finally{clearTimeout(timer);}
  }
  async function saveRaw(tool,args,raw,label,token,requestJson,checkAfter=true) {
    const observed=ledger.complete(token,raw,{checkDeadline:false}),request=requestJson||JSON.stringify({tool,arguments:args});
    const storage=JSON.stringify({request_json:request,response_json:observed.json}),bytes=Buffer.byteLength(storage),
      expected={request_bytes:Buffer.byteLength(request),request_sha256:sha(request),
        response_bytes:observed.bytes,response_sha256:observed.sha256,stored_bytes:bytes,stored_sha256:sha(storage)};
    assert(receiptBytes+receiptReserved<=1536*MIB&&receiptBytes-caseReceiptBase+receiptReserved<=192*MIB,
      'Independent local full receipt storage exhausted');
    const saved=await options.persistRaw({ordinal:records.length,operation:label,tool,request_json:request,
      response_json:observed.json,storage_json:storage,raw_result:raw});
    exact(saved,Object.keys(expected));assert(Object.entries(expected).every(([k,v])=>saved[k]===v),
      'Exact untouched raw host receipt durability differs');
    receiptBytes+=bytes;
    records.push({tool,label,...expected,durable:true});if(checkAfter)check();
    return JSON.parse(observed.json);
  }
  async function connector(operation,args) {
    check();const tool='mcp__codex_apps__github_'+operation,requestJson=JSON.stringify({tool,arguments:args}),
      reservation=RESERVATIONS[operation];
    const token=ledger.reserve({tool,request_bytes:Buffer.byteLength(requestJson),request_sha256:sha(requestJson),
      response_reservation:reservation,label:'connector'});
    toolArgumentBytes+=Buffer.byteLength(JSON.stringify(args));
    // Durability is independently reserved before the courier can dispatch.
    const localReserve=Buffer.byteLength(JSON.stringify({request_json:requestJson,response_json:''}))+2*reservation;
    assert(receiptBytes+receiptReserved+localReserve<=1536*MIB&&
      receiptBytes-caseReceiptBase+receiptReserved+localReserve<=192*MIB,'Cannot reserve complete durable connector receipt');
    receiptReserved+=localReserve;
    let view=null;
    if(operation==='create_tree') {
      assert(source&&source.packet.params===args,'Pinned current immutable worker request source required');
      view=makeRequestView({tool,...source});assert(view.request_bytes===Buffer.byteLength(requestJson)&&
        view.request_sha256===sha(requestJson),'Courier request view differs from actual connector arguments');
    }
    let timer;const milliseconds=left();
    try {
      const timeout=new Promise((resolve,reject)=>{timer=setTimeout(()=>reject(close(Error('Connector deadline exhausted; acknowledgement unknown'))),milliseconds);});
      const task=Promise.resolve().then(async()=>{
        check();if(operation==='update_ref')phase.updateDispatched=true;
        const raw=await options.courier(tool,args,{request_view:view,ledger_token:token,
          response_reserved_bytes:reservation,deadline_ms:left(),ledger});
        const value=await saveRaw(tool,args,raw,'connector:'+operation,token,requestJson,false);
        receiptReserved-=localReserve;check();return value;
      });
      return await Promise.race([task,timeout]);
    }catch(error){throw close(error);}finally{clearTimeout(timer);}
  }
  async function localProcess(kind,plan) {
    check();const tool='local_git_process',requestJson=JSON.stringify({tool,arguments:plan}),
      token=ledger.reserve({tool,request_bytes:Buffer.byteLength(requestJson),request_sha256:sha(requestJson),
        response_reservation:RESERVATIONS[kind],label:'conservatively_counted_local_git_process'});
    toolArgumentBytes+=Buffer.byteLength(JSON.stringify(plan));
    const localReserve=Buffer.byteLength(JSON.stringify({request_json:requestJson,response_json:''}))+2*RESERVATIONS[kind];
    assert(receiptBytes+receiptReserved+localReserve<=1536*MIB&&
      receiptBytes-caseReceiptBase+receiptReserved+localReserve<=192*MIB,'Cannot reserve complete durable local process receipt');
    receiptReserved+=localReserve;
    return boundedTask(async()=>{
      const raw=await options.runGit(kind,plan,left());
      const saved=await saveRaw(tool,plan,raw,'local_git:'+kind,token,requestJson,false);
      receiptReserved-=localReserve;
      assert(raw&&raw.exit_code===0&&raw.session_id===undefined&&typeof raw.output==='string','Bounded local Git operation incomplete');
      check();return saved;
    });
  }
  const parse=(raw,operation)=>{
    assert(raw&&typeof raw==='object'&&raw.isError!==true&&raw.structuredContent,'Complete connector reply required');
    const value=operation==='fetch'?JSON.parse(raw.structuredContent.content):raw.structuredContent;
    assert(value&&typeof value==='object'&&!Array.isArray(value),'Structured connector object required');return value;
  };
  const gitSha=value=>{assert(typeof value==='string'&&/^[0-9a-f]{40}$/.test(value),'Immutable full Git SHA required');return value;};
  const safePath=value=>{assert(typeof value==='string'&&/^[\x20-\x7e]+$/.test(value)&&!value.includes('\\')&&
    value.split('/').every(p=>p&&p!=='.'&&p!=='..'),'Safe ASCII archive path required');return value;};
  function beginCase(freezeJson,expectedBundleSha256) {
    try{
      assert(!stopped&&!busy&&!freeze&&typeof freezeJson==='string'&&/^[\x20-\x7e]+$/.test(freezeJson)&&
        sha(freezeJson)===expectedBundleSha256,'Independently pinned canonical broker freeze required');
      const value=JSON.parse(freezeJson);assert(h.canonical(value)===freezeJson,'Canonical broker freeze required');
      exact(value,['schema','mode','broker_protocol','repository','branch','ordinal','prefix','parent','parent_tree',
        'limits','files','manifest_sha256','per_operation_response_reservations','single_inline_tree_request',
        'single_grouped_readback','force','automatic_retry','execution_restart_authorized','scientific_admission_authorized']);
      assert(value.schema==='radio-native-v2-inline-terminal-archive-v1'&&value.mode==='ENGINEERING_ONLY'&&
        value.broker_protocol===h.BROKER_PROTOCOL&&value.repository===h.REPOSITORY&&value.branch===h.BRANCH&&
        value.single_inline_tree_request===true&&value.single_grouped_readback===true&&value.force===false&&
        value.automatic_retry===false&&value.execution_restart_authorized===false&&value.scientific_admission_authorized===false,
        'Existing non-scientific broker freeze required');
      exact(value.limits,['calls','request_bytes','response_bytes','stored_bytes','files','seconds','peak_rss_bytes']);
      const limitHard={calls:64,request_bytes:48*MIB,response_bytes:64*MIB,stored_bytes:36*MIB,files:28,seconds:600,peak_rss_bytes:512*MIB};
      for(const [key,n] of Object.entries(value.limits))assert(integer(n,limitHard[key])&&n>0,'Old broker numeric allocation required');
      assert(h.canonical(value.per_operation_response_reservations)===h.canonical({fetch:4*MIB,create_tree:MIB,
        create_commit:65536,update_ref:16384,fetch_files:48*MIB}),'Old normalized broker reservations required');
      assert(integer(value.ordinal,7)&&value.ordinal===completed.length&&new RegExp('^'+allowedPrefix+'/case'+
        String(value.ordinal).padStart(2,'0')+'-[0-9a-f]{16}$').test(value.prefix),'Ordered immutable engineering case namespace required');
      gitSha(value.parent);gitSha(value.parent_tree);
      if(completed.length)assert(value.parent===completed[completed.length-1].commit,'Previous case parent differs');
      assert(value.files&&typeof value.files==='object'&&Object.keys(value.files).length>=2&&
        Object.keys(value.files).length<=value.limits.files,'Exact bounded frozen file inventory required');
      for(const [path,pin] of Object.entries(value.files)){
        safePath(path);assert(path.startsWith(value.prefix+'/'),'Out-of-case archive path refused');
        exact(pin,['bytes','sha256','blob']);gitSha(pin.blob);
        assert(integer(pin.bytes,36*MIB)&&/^[0-9a-f]{64}$/.test(pin.sha256),'Exact file pins required');
      }
      assert(Object.values(value.files).reduce((sum,pin)=>sum+pin.bytes,0)<=value.limits.stored_bytes&&
        value.files[value.prefix+'/HEAD']?.bytes===65&&
        value.files[value.prefix+'/manifest.json']?.sha256===value.manifest_sha256,'Exact bounded manifest/HEAD binding required');
      ledger.beginCase(value.ordinal);freeze=JSON.parse(freezeJson);caseReceiptBase=receiptBytes;caseSpoolBase=gitSpoolBytes;
      caseArgumentBase=toolArgumentBytes;
      phase={bundleSha256:expectedBundleSha256,head:null,parentChecked:false,tree:null,candidate:null,
        candidateChecked:false,lateParentChecked:false,updated:false,grouped:false,
        permittedTrees:new Set([freeze.parent_tree])};check();
    }catch(error){throw close(error);}
  }
  function setRequestSource(value) {
    assert(!stopped&&value&&value.packet&&typeof value.path==='string'&&integer(value.bytes,64*MIB)&&
      /^[0-9a-f]{64}$/.test(value.sha256),'Pinned sealed worker request source required');source=value;
  }
  async function withWorkerDeadline(deadlineMs,fn) {
    assert(!stopped&&Number.isFinite(deadlineMs)&&deadlineMs>clock()&&typeof fn==='function',
      'Finite absolute claimed worker deadline required');
    const previous=workerDeadline;workerDeadline=previous===null?deadlineMs:Math.min(previous,deadlineMs);
    try{return await fn();}finally{workerDeadline=previous;}
  }
  function prepareCourierReads(view,{python}) {
    check();assert(view&&source&&view.path===source.path&&view.source_sha256===source.sha256,
      'Only current pinned worker request may be extracted');
    const plan=makeCourierReadPlan(view,{python,ledger});
    for(const row of plan){row.local_receipt_reserved_bytes=Buffer.byteLength(JSON.stringify({request_json:row.request_json,response_json:''}))+
      2*row.response_reserved_bytes;receiptReserved+=row.local_receipt_reserved_bytes;
      toolArgumentBytes+=Buffer.byteLength(JSON.stringify(row.arguments));}
    assert(receiptBytes+receiptReserved<=1536*MIB&&receiptBytes-caseReceiptBase+receiptReserved<=192*MIB,
      'Cannot reserve complete supporting read custody before dispatch');
    return plan;
  }
  async function completeCourierReads(plan,descriptors) {
    assert(Array.isArray(plan)&&Array.isArray(descriptors)&&plan.length===descriptors.length&&plan.length<=64,
      'One exact complete supporting read transcript required');
    assert(typeof options.persistRawBatch==='function','Pinned one-process supporting receipt batch sink required');
    const rows=[],expected=[];
    for(let i=0;i<plan.length;i++){
      const p=plan[i],d=descriptors[i];assert(p.ordinal===i&&d.path===p.path&&d.offset===p.offset&&d.bytes===p.bytes&&
        d.source_sha256===p.source_sha256,'Supporting read receipt differs from pre-reserved ordered plan');
      const reconstructed=reconstructReadEnvelope(d,{path:p.path,source_sha256:p.source_sha256,
        offset:p.offset,bytes:p.bytes,next_offset:p.offset});
      assert(sha(reconstructed.raw.output)===p.output_sha256,'Supporting output differs from pinned extraction');
      const observed=ledger.complete(p.ledger_token,reconstructed.raw,{checkDeadline:false}),
        storage=JSON.stringify({request_json:p.request_json,response_json:observed.json}),storedBytes=Buffer.byteLength(storage);
      assert(storedBytes<=p.local_receipt_reserved_bytes,'Supporting exact full receipt exceeded storage reservation');
      rows.push({ordinal:records.length+i,operation:'courier_read',tool:'exec_command',request_json:p.request_json,
        response_json:observed.json,storage_json:storage});
      expected.push({request_bytes:Buffer.byteLength(p.request_json),request_sha256:sha(p.request_json),
        response_bytes:observed.bytes,response_sha256:observed.sha256,stored_bytes:storedBytes,stored_sha256:sha(storage)});
    }
    const saved=await options.persistRawBatch(rows);assert(Array.isArray(saved)&&saved.length===expected.length,'Exact batch durability acknowledgement required');
    for(let i=0;i<saved.length;i++){exact(saved[i],Object.keys(expected[i]));assert(Object.entries(expected[i]).every(([k,v])=>saved[i][k]===v),
      'Supporting full raw batch receipt differs');receiptBytes+=expected[i].stored_bytes;
      receiptReserved-=plan[i].local_receipt_reserved_bytes;records.push({tool:'exec_command',label:'actual_courier_read',...expected[i],durable:true});}
    check();return {items:saved.length,bytes:expected.reduce((sum,row)=>sum+row.stored_bytes,0),durable:true};
  }
  async function invoke(operation,params) {
    assert(!busy&&!stopped,'Sequential local host only; no retry');busy=true;
    try{
      check();assert(workerDeadline!==null,'Claimed finite worker deadline required before broker invocation');let value;
      if(operation==='fetch') {
        exact(params,['url']);const base='https://api.github.com/repos/'+h.REPOSITORY+'/git/';
        assert(typeof params.url==='string'&&params.url.startsWith(base),'Approved immutable repository endpoint required');
        const suffix=params.url.slice(base.length),head=suffix==='ref/heads/'+encodeURIComponent(h.BRANCH);
        assert(head||/^(commits|trees)\/[0-9a-f]{40}$/.test(suffix),'Exact head or immutable Git object required');
        if(head) {
          value=parse(await connector('fetch',params),'fetch');
          assert(value.ref==='refs/heads/'+h.BRANCH&&value.object?.type==='commit','Exact live branch ref required');
          phase.head=gitSha(value.object.sha);assert(phase.head===(phase.updated?phase.candidate:freeze.parent),'Frozen live parent/head conflict');
          if(phase.candidateChecked&&!phase.updated)phase.lateParentChecked=true;
          if(phase.updated&&phase.grouped)phase.finalHeadChecked=true;
        }else{
          const object=suffix.slice(suffix.indexOf('/')+1);
          if(suffix.startsWith('commits/'))assert(object===freeze.parent||object===phase.candidate,'Unobserved commit refused');
          else assert(phase.permittedTrees.has(object),'Unobserved tree refused');
          if(object===phase.candidate&&!phase.candidateFetched){
            await localProcess('git_fetch',{executable:gitPath,args:['--no-replace-objects','-c','core.hooksPath=/dev/null',
              '-c','gc.auto=0','fetch','--no-tags','--no-write-fetch-head','--','https://github.com/'+h.REPOSITORY+'.git',phase.candidate],
              cwd:repoPath,maximum_output_bytes:MIB});phase.candidateFetched=true;
          }
          value=options.localGit.withDeadline(left(),()=>options.localGit.immutableRead(params.url));
          assert(value.sha===object,'Authenticated local object identity differs');
          if(suffix.startsWith('commits/')){
            if(object===freeze.parent){assert(value.tree.sha===freeze.parent_tree,'Frozen parent tree differs');phase.parentChecked=true;}
            else{assert(value.tree.sha===phase.tree&&Array.isArray(value.parents)&&value.parents.length===1&&
              value.parents[0].sha===freeze.parent,'Actual candidate single parent/tree differs');phase.candidateChecked=true;}
          }else{
            assert(value.truncated===false&&Array.isArray(value.tree),'Complete local immutable tree required');
            for(const row of value.tree)if(row.type==='tree')phase.permittedTrees.add(gitSha(row.sha));
          }
        }
      }else if(operation==='create_tree'){
        exact(params,['repository_full_name','base_tree_sha','tree_elements']);
        assert(params.repository_full_name===h.REPOSITORY&&params.base_tree_sha===freeze.parent_tree&&
          phase.head===freeze.parent&&phase.parentChecked&&phase.tree===null&&Array.isArray(params.tree_elements)&&
          params.tree_elements.length===Object.keys(freeze.files).length,'One frozen inline tree operation required');
        const seen=new Set();for(const row of params.tree_elements){exact(row,['path','mode','type','content']);
          const pin=freeze.files[row.path];assert(pin&&!seen.has(row.path)&&row.mode==='100644'&&row.type==='blob'&&
            typeof row.content==='string'&&/^[\x00-\x7f]*$/.test(row.content)&&Buffer.byteLength(row.content)===pin.bytes&&
            sha(row.content)===pin.sha256,'Exact frozen inline archive content differs');seen.add(row.path);}
        const expectedTree=options.localGit.withDeadline(left(),()=>options.localGit.expectedTree(freeze.parent_tree,params.tree_elements));
        value=parse(await connector(operation,params),operation);phase.tree=gitSha(value.sha);
        assert(phase.tree===expectedTree,'Connector tree differs from independently reconstructed immutable tree');
        phase.permittedTrees.add(phase.tree);
      }else if(operation==='create_commit'){
        exact(params,['repository_full_name','parent_sha','tree_sha','message']);
        assert(params.repository_full_name===h.REPOSITORY&&params.parent_sha===freeze.parent&&params.tree_sha===phase.tree&&
          phase.tree!==null&&phase.candidate===null&&typeof params.message==='string'&&Buffer.byteLength(params.message)<=1024,
          'One bounded frozen-parent commit required');
        value=parse(await connector(operation,params),operation);phase.candidate=gitSha(value.sha);
      }else if(operation==='update_ref'){
        exact(params,['repository_full_name','branch_name','sha','force']);
        assert(params.repository_full_name===h.REPOSITORY&&params.branch_name===h.BRANCH&&params.force===false&&
          params.sha===phase.candidate&&phase.candidateChecked&&phase.lateParentChecked&&!phase.updated,
          'Exact checked candidate and nonforced update required');
        value=parse(await connector(operation,params),operation);assert(value.success===true,'Unconfirmed single update');phase.updated=true;
      }else if(operation==='fetch_files'){
        exact(params,['repository_full_name','ref','paths','encoding']);
        assert(params.repository_full_name===h.REPOSITORY&&params.ref===phase.candidate&&phase.updated&&!phase.grouped&&
          params.encoding==='base64'&&h.canonical(params.paths)===h.canonical(Object.keys(freeze.files).sort()),
          'Exact post-publication immutable grouped readback required');
        const spoolPath=spoolRoot+'/case'+String(freeze.ordinal).padStart(2,'0')+'-'+phase.bundleSha256+'.git-batch',
          spoolReserve=h.gitBatchBytes(freeze.files);
        assert(gitSpoolBytes+gitSpoolUnknown+spoolReserve<=320*MIB&&gitSpoolBytes-caseSpoolBase+gitSpoolUnknown+spoolReserve<=40*MIB,
          'Independent exact raw Git spool reservation exhausted');
        // A lost acknowledgement never credits or removes this reservation.
        gitSpoolUnknown+=spoolReserve;
        const plans={git_fetch:{executable:gitPath,args:['--no-replace-objects','-c','core.hooksPath=/dev/null','-c','gc.auto=0',
          'fetch','--no-tags','--no-write-fetch-head','--','https://github.com/'+h.REPOSITORY+'.git',phase.candidate],
          cwd:repoPath,maximum_output_bytes:MIB},
          git_cat_file_batch:{executable:gitPath,args:['--no-replace-objects','-c','core.hooksPath=/dev/null','cat-file','--batch'],
            cwd:repoPath,stdout_path:spoolPath,stdin_text:params.paths.map(path=>phase.candidate+':'+path).join('\n')+'\n',
            maximum_output_bytes:MIB}};
        let sequence=0;
        const callGit=async(kind,plan)=>{assert(kind===['git_fetch','git_cat_file_batch'][sequence++]&&sequence<=2,
          'Exactly post-update fetch and grouped batch required');
          if(plan!==undefined)assert(h.canonical(plan)===h.canonical(plans[kind]),'Only pinned generated Git plan required');
          return localProcess(kind,plans[kind]);};
        const grouped=await boundedTask(()=>options.groupedGitReadback({commit:phase.candidate,paths:params.paths.slice(),files:freeze.files,
          callGit,git_plan:plans,spool_path:spoolPath,raw_git_reserved_bytes:spoolReserve,deadline_ms:left()}));
        assert(grouped&&grouped.commit===phase.candidate&&grouped.single_cat_file_batch===true&&sequence===2,
          'Exact immutable grouped operation closure required');
        const receipt=grouped.raw_git_receipt,p=grouped.local_projection,v=grouped.projection_verification;
        exact(receipt,['path','bytes','sha256','durable']);assert(receipt.path===spoolPath&&receipt.bytes===spoolReserve&&
          /^[0-9a-f]{64}$/.test(receipt.sha256)&&receipt.durable===true,'Exact durable raw Git spool differs');
        exact(p,['id','path','bytes','sha256','durable']);assert(typeof p.id==='string'&&p.durable===true&&integer(p.bytes,48*MIB)&&
          p.bytes>0&&/^[0-9a-f]{64}$/.test(p.sha256)&&safeFile(p.path),'Sealed bounded local projection required');
        exact(v,['schema','commit','paths_sha256','file_pins_sha256','raw_git_sha256','projection_sha256',
          'exact_frozen_blob_sha256','exact_git_blob_identity','exact_batch_framing']);
        assert(v.schema==='radio-native-v2-local-projection-verification-v1'&&v.commit===phase.candidate&&
          v.paths_sha256===sha(h.canonical(params.paths))&&v.file_pins_sha256===sha(h.canonical(freeze.files))&&
          v.raw_git_sha256===receipt.sha256&&v.projection_sha256===p.sha256&&v.exact_frozen_blob_sha256===true&&
          v.exact_git_blob_identity===true&&v.exact_batch_framing===true,'Pinned Python projection proof differs');
        gitSpoolUnknown-=spoolReserve;gitSpoolBytes+=receipt.bytes;
        phase.grouped=true;phase.rawGitReceipt=receipt;phase.localProjection=p;
        value={schema:'radio-native-v2-local-projection-reply-v1',projection:p};
      }else throw Error('Unsupported existing broker operation');
      check();return value;
    }catch(error){throw close(error);}finally{busy=false;source=null;}
  }
  function finishCase(){try{check();assert(!busy&&phase.updated&&phase.grouped&&phase.finalHeadChecked,
    'Exact publication and local worker readback incomplete');
    const receipt={ordinal:freeze.ordinal,parent:freeze.parent,commit:phase.candidate,tree:phase.tree,
      bundle_sha256:phase.bundleSha256,actual_tool_usage:{...ledger.caseUsage(),
        tool_argument_bytes:toolArgumentBytes-caseArgumentBase,receipt_bytes:receiptBytes-caseReceiptBase,
        receipt_charged_bytes:receiptBytes-caseReceiptBase+receiptReserved,unknown_receipt_bytes:receiptReserved,
        git_spool_bytes:gitSpoolBytes-caseSpoolBase,git_spool_charged_bytes:gitSpoolBytes-caseSpoolBase+gitSpoolUnknown,
        unknown_git_spool_bytes:gitSpoolUnknown},raw_git_receipt:phase.rawGitReceipt,
      local_projection:phase.localProjection,explicit_git_operations:3,automatic_retry:false};
    completed.push(receipt);freeze=null;return receipt;}catch(error){throw close(error);}}
  return {beginCase,invoke,finishCase,setRequestSource,withWorkerDeadline,prepareCourierReads,completeCourierReads,usage,ledger,
    state:()=>({stopped,busy,candidate:phase.candidate||null,update_may_have_landed:phase.updated===true||phase.updateDispatched===true,
      records:records.map(row=>({...row})),completed:completed.slice()}),
    capabilityManifest:()=>({schema:SCHEMA,status:'COMPONENT_ONLY_NOT_EXECUTABLE',limits:HARD,namespace:allowedPrefix,
      native_case_execution:false,
      complete_response_reservations:RESERVATIONS,immutable_git_metadata_local:true,
      independent_candidate_tree_hash:true,candidate_commit_fetched_before_update:true,explicit_git_operations:3,
      file_backed_readback_to_python:true,normalized_readback_tool_bytes:0,courier_runtime_trusted:false,
      supporting_read_receipt_custody:'EXACT_RECONSTRUCTION_FROM_PINNED_SOURCE_AND_OBSERVED_ENVELOPE_METADATA',
      all_execution_qualification_flags:false,execution_authorized:false,reservation_authorized:false,
      rng_draws:0,telescope_reads:0,case_reservations:0,scientific_admission_authorized:false,
      unqualified_external_boundaries:['actual shared courier transcript','integrated full-size RSS and disk',
        'public runtime freeze and exact readback','trusted freeze/reservation verifier']})};
}

module.exports={SCHEMA,FIXTURE_PREFIX,HARD,RESERVATIONS,READ_BYTES,sha,hashFile,readRange,
  SharedLedger,makeRequestView,makeReadDescriptor,reconstructReadEnvelope,makeCourierReadPlan,capacityRecord,createLocalBrokerHost};
