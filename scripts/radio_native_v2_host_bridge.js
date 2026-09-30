// Concrete bounded tools.exec_command <-> durable Python filesystem adapter.
// Loading this adapter grants no execution, reservation or scientific authority.
const BRIDGE_SCHEMA = 'radio-native-v2-host-worker-bridge-v1';
const BRIDGE_LIMITS = Object.freeze({ calls:40000, request_bytes:3*1024*1024*1024,
  response_bytes:2*1024*1024*1024, seconds:4800, operation_seconds:120,
  response_reservation_bytes:65536, max_read_bytes:32768, max_append_bytes:24576 });

function createHostWorkerBridge(options) {
  const host = options.hostLibrary || (typeof require === 'function' ? require('./radio_native_v2_broker_host') : null);
  if (!host || typeof host.sha256 !== 'function') throw Error('Pinned host library required');
  const { sha256,utf8Bytes,canonical } = host;
  const assert = (ok,message) => { if (!ok) throw Error(message); };
  const safeAbsolute = value => {
    assert(typeof value === 'string' && /^\/[A-Za-z0-9_./-]+$/.test(value) &&
      value.split('/').slice(1).every(part => part && part !== '.' && part !== '..'), 'Canonical absolute helper path required');
    return value;
  };
  const root = safeAbsolute(options.root), python = safeAbsolute(options.python),
    helper = safeAbsolute(options.helper), sourceRoot = safeAbsolute(options.sourceRoot);
  assert(options.tools && typeof options.tools.exec_command === 'function', 'Actual exec_command tool required');
  const limits = { ...BRIDGE_LIMITS,...options.limits };
  assert(Object.keys(limits).sort().join() === Object.keys(BRIDGE_LIMITS).sort().join(), 'Exact bridge limits required');
  for (const [key,value] of Object.entries(limits)) assert(Number.isSafeInteger(value) && value > 0 &&
    value <= BRIDGE_LIMITS[key], 'Finite hard bounded bridge limits required');
  const clock = options.clock || Date.now, setTimer = options.setTimer || setTimeout,
    clearTimer = options.clearTimer || clearTimeout;
  const started = clock(), records = [];
  const counters = { calls:0,request_bytes:0,response_bytes:0,response_charged_bytes:0,
    unknown_response_bytes:0,unknown_response_count:0,append_bytes:0,read_bytes:0,
    supporting_receipt_pending_bytes:0,supporting_receipt_durable_bytes:0 };
  let stopped = false, busy = false, stopReason = null, itemOrdinal = 0, workerOrdinal = 0, currentCase = null;
  // An immutable in-memory copy retains the final acknowledgement. It is
  // reported separately: this same exec boundary cannot durably save its own
  // last reply without producing another unobserved acknowledgement.
  let pending = [];
  const stop = error => { stopped=true;stopReason=String(error);return error; };
  const left = () => Math.min(limits.operation_seconds*1000,limits.seconds*1000-(clock()-started));
  const check = () => {
    assert(!stopped && left() > 0, 'Bridge permanently stopped or deadline exhausted; no retry');
    assert(counters.calls <= limits.calls && counters.request_bytes <= limits.request_bytes &&
      counters.response_charged_bytes <= limits.response_bytes, 'Supporting tool envelope budget exhausted');
  };
  const quote = value => "'"+value.replace(/'/g,"'\\''")+"'";
  async function action(payload) {
    assert(!busy && !stopped, 'Sequential bridge only; no retry'); busy=true;
    let timer,record;
    try {
      check();
      const incoming = pending.slice();
      // Only the returned raw envelope is carried forward. Sending the full
      // preceding command would recursively embed all earlier commands.
      const request = { ...payload,root };
      if (incoming.length) request.support_receipts = incoming.map(row => ({ ordinal:row.ordinal,
        request_bytes:row.request_bytes,request_sha256:row.request_sha256,
        response_json:row.response_json,response_bytes:row.response_bytes,
        response_sha256:row.response_sha256 }));
      const input = canonical(request);
      assert(utf8Bytes(input) <= 98304, 'Bounded helper request exceeded');
      const args = {cmd:'PYTHONPATH='+quote(sourceRoot)+' '+quote(python)+' -B '+quote(helper)+
        " <<'SETI_NATIVE_V2_BRIDGE_JSON'\n"+input+'\nSETI_NATIVE_V2_BRIDGE_JSON',
        max_output_tokens:100000,yield_time_ms:1000};
      const requestJson = JSON.stringify({tool:'exec_command',arguments:args}), requestBytes=utf8Bytes(requestJson),
        reserve=limits.response_reservation_bytes;
      assert(counters.calls < limits.calls && counters.request_bytes+requestBytes <= limits.request_bytes &&
        counters.response_charged_bytes+reserve <= limits.response_bytes, 'Cannot reserve complete supporting tool envelopes');
      counters.calls++;counters.request_bytes+=requestBytes;counters.response_charged_bytes+=reserve;
      counters.unknown_response_bytes+=reserve;counters.unknown_response_count++;
      record={ordinal:records.length,action:payload.action,request_bytes:requestBytes,request_sha256:sha256(requestJson),
        response_reserved_bytes:reserve,response_unknown:true,dispatch_started:false,automatic_retry:false};
      records.push(record);
      const timeout = new Promise((resolve,reject) => {timer=setTimer(() => reject(stop(Error('Supporting helper deadline exceeded; acknowledgement uncertain'))),left());});
      const work=Promise.resolve().then(async () => {
        check();record.dispatch_started=true;
        const raw=await options.tools.exec_command(args);
        const responseJson=JSON.stringify(raw);
        assert(typeof responseJson==='string', 'Complete supporting tool envelope required');
        const bytes=utf8Bytes(responseJson),digest=sha256(responseJson);
        counters.response_bytes+=bytes;counters.response_charged_bytes+=bytes-reserve;
        counters.unknown_response_bytes-=reserve;counters.unknown_response_count--;
        Object.assign(record,{response_unknown:false,response_bytes:bytes,response_sha256:digest,
          response_charged_bytes:bytes});
        pending.push({ordinal:record.ordinal,request_bytes:requestBytes,request_sha256:record.request_sha256,
          response_json:responseJson,response_bytes:bytes,response_sha256:digest});
        counters.supporting_receipt_pending_bytes=pending.reduce((sum,row)=>sum+row.response_bytes,0);
        assert(bytes <= reserve, 'Supporting raw envelope exceeded reservation');check();
        // A yielded process is an uncertain acknowledgement, never polled or
        // retried. The helper intent/staging files remain charged and retained.
        assert(raw.exit_code===0 && raw.session_id===undefined && typeof raw.output==='string',
          'Supporting helper incomplete; no retry');
        const result=JSON.parse(raw.output);
        assert(result && typeof result==='object' && !Array.isArray(result), 'Bounded helper JSON acknowledgement required');
        if (incoming.length) {
          assert(result.support_receipts_persisted===incoming.length, 'Prior supporting raw envelope durability unconfirmed');
          const incomingOrdinals=new Set(incoming.map(row=>row.ordinal));
          pending=pending.filter(row=>!incomingOrdinals.has(row.ordinal));
          counters.supporting_receipt_durable_bytes+=incoming.reduce((sum,row)=>sum+row.response_bytes,0);
          counters.supporting_receipt_pending_bytes=pending.reduce((sum,row)=>sum+row.response_bytes,0);
        }
        return result.result === undefined ? result : result.result;
      });
      return await Promise.race([work,timeout]);
    } catch (error) { if(record)record.error=String(error);throw stop(error); }
    finally { clearTimer(timer);busy=false; }
  }
  function base64(bytes) {
    const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';let out='';
    for(let i=0;i<bytes.length;i+=3) {
      const a=bytes[i],b=bytes[i+1],c=bytes[i+2],n=(a<<16)|((b||0)<<8)|(c||0);
      out+=alphabet[n>>>18]+alphabet[n>>>12&63]+(b===undefined?'=':alphabet[n>>>6&63])+(c===undefined?'=':alphabet[n&63]);
    }return out;
  }
  function decode64(text) {
    assert(typeof text==='string' && /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(text),
      'Canonical bounded base64 required');
    const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',out=[];
    for(let i=0;i<text.length;i+=4) {const n=alphabet.indexOf(text[i])<<18|alphabet.indexOf(text[i+1])<<12|
      (text[i+2]==='='?0:alphabet.indexOf(text[i+2]))<<6|(text[i+3]==='='?0:alphabet.indexOf(text[i+3]));
      out.push(n>>>16&255);if(text[i+2]!=='=')out.push(n>>>8&255);if(text[i+3]!=='=')out.push(n&255);
    }return out;
  }
  function* chunks(value) {
    let bytes=[];
    for(const ch of value) {
      let cp=ch.codePointAt(0);if(cp>=0xd800&&cp<=0xdfff)cp=0xfffd;
      const next=cp<=0x7f?[cp]:cp<=0x7ff?[0xc0|cp>>6,0x80|cp&63]:cp<=0xffff?
        [0xe0|cp>>12,0x80|cp>>6&63,0x80|cp&63]:[0xf0|cp>>18,0x80|cp>>12&63,0x80|cp>>6&63,0x80|cp&63];
      if(bytes.length+next.length>limits.max_append_bytes) {yield bytes;bytes=[];}bytes.push(...next);
    }if(bytes.length)yield bytes;
  }
  function id(kind) { return kind+'-'+String(itemOrdinal++).padStart(8,'0'); }
  async function put(kind,value,caseOrdinal=0) {
    assert(typeof value==='string','Exact UTF-8 string payload required');
    const identifier=id(kind),bytes=utf8Bytes(value),digest=sha256(value);
    await action({action:'reserve',kind,id:identifier,bytes,sha256:digest,case_ordinal:caseOrdinal});
    let offset=0;
    for(const chunk of chunks(value)) {
      await action({action:'append',id:identifier,offset,content_base64:base64(chunk)});
      offset+=chunk.length;counters.append_bytes+=chunk.length;
    }
    const receipt=await action({action:'seal',id:identifier});
    assert(receipt.bytes===bytes && receipt.sha256===digest && receipt.durable===true,
      'Exact durable helper payload differs');
    return { ...receipt,id:identifier };
  }
  async function read(item) {
    assert(item && Number.isSafeInteger(item.bytes) && item.bytes>=0 && /^[0-9a-f]{64}$/.test(item.sha256),
      'Exact immutable item receipt required');
    // Projection is ASCII JSON, so each decoded byte maps exactly to a code
    // point. Do not decode arbitrary UTF-8 chunks independently.
    const parts=[];
    for(let offset=0;offset<item.bytes;) {
      const length=Math.min(limits.max_read_bytes,item.bytes-offset);
      const chunk=await action({action:'read',id:item.id,offset,length});
      assert(chunk.offset===offset && chunk.bytes===length && chunk.total_bytes===item.bytes && chunk.next_offset===offset+length &&
        chunk.sha256===item.sha256, 'Bounded immutable chunk offset/length/pin differs');
      const bytes=decode64(chunk.content_base64);assert(bytes.length===length && bytes.every(n=>n<128),
        'ASCII immutable projection required');
      const decoded=[];
      for(let start=0;start<bytes.length;start+=8192)decoded.push(String.fromCharCode(...bytes.slice(start,start+8192)));
      parts.push(decoded.join(''));
      offset+=length;counters.read_bytes+=length;
    }
    const output=parts.join('');
    assert(utf8Bytes(output)===item.bytes && sha256(output)===item.sha256, 'Read immutable projection differs');
    return output;
  }
  async function persistRaw(record) {
    await put('host_receipt',record.storage_json,options.caseOrdinal ? options.caseOrdinal() : currentCase);
    return {request_bytes:utf8Bytes(record.request_json),request_sha256:sha256(record.request_json),
      response_bytes:utf8Bytes(record.response_json),response_sha256:sha256(record.response_json),
      stored_bytes:utf8Bytes(record.storage_json),stored_sha256:sha256(record.storage_json)};
  }
  async function groupedGitReadback(job) {
    await job.callGit('git_fetch');await job.callGit('git_cat_file_batch');
    const identifier=id('git_projection');
    const verified=await action({action:'git_projection',id:identifier,spool_path:job.spool_path,
      commit:job.commit,paths:job.paths,files:job.files,case_ordinal:options.caseOrdinal ? options.caseOrdinal() : currentCase});
    const projection={...verified.projection,id:identifier};
    return {commit:job.commit,single_cat_file_batch:true,raw_git_receipt:verified.raw_git_receipt,
      result:JSON.parse(await read(projection))};
  }
  async function serviceOne(brokerHost) {
    try {
      check();
      const state=await action({action:'pending'});
      assert(state.stopped===false && Array.isArray(state.pending) && state.pending.length<=1,
        'Exactly sequential outstanding worker request required');
      assert(state.pending_count===state.pending.length,'Multiple outstanding worker requests refused');
      if(state.pending.length===0)return {serviced:false};
      const item=state.pending[0],packet=JSON.parse(await read(item));
      const responseReservations={'invoke:fetch':4*1024*1024,'invoke:create_tree':1024*1024,
        'invoke:create_commit':65536,'invoke:update_ref':16384,'invoke:fetch_files':48*1024*1024,
        prepare_transport:1024*1024,finish_transport:1024*1024,transport_usage:1024*1024};
      assert(packet.schema==='radio-native-v2-filesystem-bridge-v1' && packet.ordinal===workerOrdinal &&
        item.id==='request-'+String(workerOrdinal).padStart(6,'0') &&
        packet.response_id==='response-'+String(workerOrdinal).padStart(6,'0') &&
        packet.automatic_retry===false && responseReservations[packet.operation]===packet.response_reserved_bytes &&
        Object.keys(packet).sort().join()===['schema','ordinal','operation','params','response_id',
          'response_reserved_bytes','case_ordinal','automatic_retry','deadline_monotonic_seconds'].sort().join(),
        'Fresh exact worker protocol identity required');
      const claimedAt=clock(),claim=await action({action:'claim',id:item.id});
      const remaining=claim.remaining_seconds*1000-(clock()-claimedAt);
      assert(claim.claimed===true && claim.request_sha256===item.sha256 &&
        Number.isFinite(remaining) && remaining>0,'Fresh single worker claim/deadline required');
      const operation=async () => {
      let result;
      if(packet.operation==='prepare_transport') {
        currentCase=packet.case_ordinal;
        assert(Number.isSafeInteger(currentCase) && currentCase>=0 && currentCase<8,
          'Exact ordered worker case required');
        assert(JSON.parse(packet.params.freeze_json).ordinal===currentCase,'Worker case differs from pinned host freeze');
        brokerHost.beginCase(packet.params.freeze_json,packet.params.bundle_sha256);result={prepared:true};
      } else if(packet.operation==='finish_transport')result=brokerHost.finishCase();
      else if(packet.operation==='transport_usage')result=brokerHost.usage();
      else {
        assert(typeof packet.operation==='string' && /^invoke:(fetch|create_tree|create_commit|update_ref|fetch_files)$/.test(packet.operation),
          'Existing worker broker operation required');
        assert(packet.case_ordinal===currentCase,'Worker case binding differs');
        result=await brokerHost.invoke(packet.operation.slice(7),packet.params);
      }
      // Python's canonical format escapes Unicode. Every protocol key and
      // numeric field here is fixed ASCII/integer or millisecond-derived.
      const response=canonical(result).replace(/[^\x20-\x7e]/g,ch=>'\\u'+ch.charCodeAt(0).toString(16).padStart(4,'0'));
      const bytes=utf8Bytes(response),digest=sha256(response);
      assert(bytes<=packet.response_reserved_bytes,'Worker immutable reply reservation exceeded');
      let offset=0;
      for(const chunk of chunks(response)) {
        await action({action:'append',id:packet.response_id,offset,content_base64:base64(chunk)});
        offset+=chunk.length;counters.append_bytes+=chunk.length;
      }
      const receipt=await action({action:'seal',id:packet.response_id,bytes,sha256:digest});
      assert(receipt.bytes===bytes && receipt.sha256===digest && receipt.durable===true,
        'Worker response durability unconfirmed');
      workerOrdinal++;return {serviced:true,ordinal:packet.ordinal,operation:packet.operation,response:receipt};
      };
      let workerTimer;
      try {
        const timeout=new Promise((resolve,reject)=>{workerTimer=setTimer(()=>reject(stop(Error('Claimed worker deadline exceeded; response uncertain'))),remaining);});
        return await Promise.race([Promise.resolve().then(operation),timeout]);
      } finally {clearTimer(workerTimer);}
    } catch(error) {throw stop(error);}
  }
  return { action,put,read,persistRaw,groupedGitReadback,serviceOne,
    usage:() => ({schema:BRIDGE_SCHEMA,...counters,elapsed_seconds:(clock()-started)/1000,
      automatic_retry:false,final_support_acknowledgement_durable:false}),
    state:() => ({stopped,busy,stop_reason:stopReason,records:records.map(row=>({...row})),
      final_support_acknowledgement:pending.length?{...pending[pending.length-1]}:null,
      outstanding_support_acknowledgements:pending.map(row=>({...row}))}),
    capabilityManifest:() => ({schema:BRIDGE_SCHEMA,status:'CONCRETE_BRIDGE_NOT_EXECUTION_QUALIFIED',limits,
      core_connector_raw_receipts_durable_before_projection:true,supporting_raw_reply_forwarded_next_action:true,
      final_support_acknowledgement_durable:false,supporting_request_full_bytes_durable:false,
      worker_claim_is_irrevocable_dispatch_attempt:true,worker_deadline_propagated_inside_broker_host:false,
      host_rss_measured:false,actual_host_runtime_frozen:false,automatic_retry:false,
      execution_authorized:false,scientific_admission_authorized:false,rng_draws:0,telescope_reads:0}) };
}

if(typeof module!=='undefined')module.exports={BRIDGE_SCHEMA,BRIDGE_LIMITS,createHostWorkerBridge};
