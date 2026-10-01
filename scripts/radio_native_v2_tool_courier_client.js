'use strict';
// Portable functions-runtime courier. All processing happens in one awaited
// run; this client does not grant native, RNG or scientific authority.
const CLIENT_SCHEMA='radio-native-v2-single-exec-tool-courier-v1';
const CONTROLLER_SCHEMA='radio-native-v2-local-tool-courier-v1';
const CLIENT_MIB=1024*1024;
const CLIENT_CORE=Object.freeze({mcp__codex_apps__github_fetch:65536,
  mcp__codex_apps__github_create_tree:64*1024,
  mcp__codex_apps__github_create_commit:256*1024,
  mcp__codex_apps__github_update_ref:65536});
const CLIENT_SEQUENCE=Object.freeze(['fetch','create_tree','create_commit','fetch','update_ref','fetch']);
const CLIENT_LIMITS=Object.freeze({actual_calls:60,conservative_git_processes:4,
  request_bytes:48*CLIENT_MIB,response_bytes:64*CLIENT_MIB,seconds:600,
  support_response:256*1024,read_bytes:CLIENT_MIB-65536,output_tokens:400000});
const QUALIFIED_SUPPORT_YIELD_MS=30000;
const QUALIFIED_RUNNER_LIMITS=Object.freeze({actual_calls:59,request_bytes:40*CLIENT_MIB,
  response_bytes:64*CLIENT_MIB-256*1024,caller_tail_calls:1,
  caller_tail_request_bytes:8*CLIENT_MIB,caller_tail_response_bytes:256*1024});

async function runToolCourier(tools,options) {
  const h=options.hostLibrary||options.h,assert=(ok,message)=>{if(!ok)throw Error(message);};
  assert(h&&typeof h.sha256==='function'&&typeof h.utf8Bytes==='function',
    'Pinned portable hash and UTF-8 byte functions required');
  assert(tools&&typeof tools.exec_command==='function'&&typeof tools.write_stdin==='function',
    'Actual execution tools required');
  const maxCalls=options.max_actual_calls===undefined?60:options.max_actual_calls;
  assert(Number.isSafeInteger(maxCalls)&&maxCalls>0&&maxCalls<=60,'Actual call ceiling cannot exceed60 plus4Git');
  const requestCap=options.max_request_bytes===undefined?CLIENT_LIMITS.request_bytes:options.max_request_bytes,
    responseCap=options.max_response_bytes===undefined?CLIENT_LIMITS.response_bytes:options.max_response_bytes;
  assert(Number.isSafeInteger(requestCap)&&requestCap>0&&requestCap<=CLIENT_LIMITS.request_bytes&&
    Number.isSafeInteger(responseCap)&&responseCap>0&&responseCap<=CLIENT_LIMITS.response_bytes,
    'Actual client byte ceilings cannot enlarge the shared allocation');
  // Historical component fixtures default to their frozen 10-second wait.
  // A future runner qualification must opt into the 30-second value and pin
  // it in its own prospective contract.
  const supportYield=options.support_yield_time_ms===undefined?10000:options.support_yield_time_ms;
  assert([1000,10000,QUALIFIED_SUPPORT_YIELD_MS].includes(supportYield),
    'Only a prospectively bounded supporting wait is permitted');
  const tailCalls=options.caller_tail_calls===undefined?1:options.caller_tail_calls;
  assert(tailCalls===1||tailCalls===2,'One or two prospectively reserved tail calls required');
  if(tailCalls===2)assert(maxCalls<=58&&requestCap<=40*CLIENT_MIB&&
    responseCap<=64*CLIENT_MIB-256*1024&&supportYield===QUALIFIED_SUPPORT_YIELD_MS,
    'Two-call tail must be reserved inside unchanged shared allocations before startup');
  const clock=options.clock||Date.now,started=clock(),setTimer=options.setTimer||setTimeout,
    clearTimer=options.clearTimer||clearTimeout,records=[],events=[];
  const usage={calls:0,request_bytes:0,response_bytes:0,response_charged_bytes:0,
    unknown_response_bytes:0,unknown_response_count:0};
  let stopped=false,reason=null,session=null,stdout='',ordinal=0,startRaw=null,
    previousDeliveryRaw=null,lastRaw=null,lastDispatchAt=started,terminal=null,pendingDelivery=null;
  const stop=error=>{stopped=true;reason=String(error);return error;};
  const check=deadline=>{
    assert(!stopped&&clock()-started<CLIENT_LIMITS.seconds*1000&&
      (deadline===undefined||clock()<deadline),'Actual courier closed or deadline expired');
  };
  const progress=event=>{events.push(event);if(typeof options.onProgress==='function')options.onProgress(event);};
  async function call(tool,args,reservation,kind,deadline) {
    check(deadline);assert(typeof tools[tool]==='function','Actual approved tool unavailable: '+tool);
    const requestJson=JSON.stringify({tool,arguments:args}),requestBytes=h.utf8Bytes(requestJson);
    assert(usage.calls<maxCalls&&usage.request_bytes+requestBytes<=requestCap&&
      usage.response_charged_bytes+reservation<=responseCap,
      'Cannot reserve complete actual courier envelopes inside old64/48/64 allocations');
    const row={ordinal:records.length,tool,kind,request_json:requestJson,request_bytes:requestBytes,
      request_sha256:h.sha256(requestJson),response_reserved_bytes:reservation,response_unknown:true,
      response_charged_bytes:reservation,dispatch_at_epoch_ms:clock(),automatic_retry:false};
    records.push(row);usage.calls++;usage.request_bytes+=requestBytes;usage.response_charged_bytes+=reservation;
    usage.unknown_response_bytes+=reservation;usage.unknown_response_count++;
    let timer;
    try {
      const remaining=Math.min(120000,CLIENT_LIMITS.seconds*1000-(clock()-started),
        deadline===undefined?Infinity:deadline-clock());
      assert(remaining>0,'No actual dispatch after deadline');
      const timeout=new Promise((resolve,reject)=>{timer=setTimer(()=>reject(stop(Error('Actual tool acknowledgement deadline lost; no retry'))),remaining);});
      const work=Promise.resolve().then(async()=>{
        check(deadline);const raw=await tools[tool](args),json=JSON.stringify(raw);
        assert(typeof json==='string','Complete visible raw tool envelope required');
        const bytes=h.utf8Bytes(json);
        usage.response_bytes+=bytes;usage.response_charged_bytes+=bytes-reservation;
        usage.unknown_response_bytes-=reservation;usage.unknown_response_count--;
        Object.assign(row,{raw_result:raw,response_json:json,response_bytes:bytes,
          response_sha256:h.sha256(json),response_unknown:false,response_charged_bytes:bytes,
          returned_at_epoch_ms:clock()});
        assert(bytes<=reservation&&usage.response_charged_bytes<=responseCap,
          'Actual whole tool reply exceeded reservation');check(deadline);return raw;
      });
      return await Promise.race([work,timeout]);
    }catch(error){row.error=String(error);throw stop(error);}finally{clearTimer(timer);}
  }
  function messages(raw,dispatchedAt) {
    assert(raw&&typeof raw.output==='string'&&raw.isError!==true,'Complete supporting execution envelope required');
    lastRaw=raw;lastDispatchAt=dispatchedAt;
    if(raw.session_id!==undefined){assert(Number.isSafeInteger(raw.session_id)&&raw.session_id>0,'Exact running session required');
      if(session!==null)assert(session===raw.session_id,'Persistent controller session changed');session=raw.session_id;}
    stdout+=raw.output;assert(h.utf8Bytes(stdout)<=CLIENT_LIMITS.support_response,'Bounded complete controller stdout required');
    const chunks=stdout.split('\n');stdout=chunks.pop();const parsed=[],parseErrors=[];
    for(const line of chunks)if(line.trim()){
      try{parsed.push(JSON.parse(line));}catch(error){parseErrors.push(error);}
    }
    // A failure in the same returned envelope wins over an earlier request.
    for(const item of parsed){assert(item&&item.schema===CONTROLLER_SCHEMA,'Only pinned controller JSON frames required');
      if(item.kind==='failed')throw stop(Error('Controller closed before dispatch: '+String(item.error)));}
    assert(parseErrors.length===0,'Non-JSON controller output; full raw envelope retained and scope closed');
    assert(parsed.filter(x=>x.kind==='request').length<=1&&parsed.filter(x=>x.kind==='terminal').length<=1,
      'One sequential controller frame required');
    const result=parsed.find(x=>x.kind==='terminal')||parsed.find(x=>x.kind==='request');
    assert(!parsed.some(x=>x.kind==='terminal')||!parsed.some(x=>x.kind==='request'),'Terminal/request ambiguity refused');
    if(result)return {packet:result,dispatchedAt};
    assert(raw.exit_code===undefined&&session!==null,'Controller ended without a terminal record');return null;
  }
  async function poll() {
    check();assert(session!==null,'Running controller session required for read-only poll');
    const args={session_id:session,chars:'',max_output_tokens:400000,yield_time_ms:supportYield},at=clock(),
      raw=await call('write_stdin',args,CLIENT_LIMITS.support_response,'actual_idle_poll');
    progress({kind:'poll',calls:usage.calls});return messages(raw,at);
  }
  function approvedCore(packet,args) {
    assert(packet.ordinal===ordinal&&packet.automatic_retry===false&&Object.hasOwn(CLIENT_CORE,packet.tool),
      'Exact next approved connector operation required');
    assert(ordinal<CLIENT_SEQUENCE.length&&packet.tool==='mcp__codex_apps__github_'+CLIENT_SEQUENCE[ordinal],
      'Only the six ordered single-case connector operations are permitted');
    assert(args&&typeof args==='object'&&!Array.isArray(args),'Concrete connector arguments required');
    if(packet.tool.endsWith('_fetch'))assert(args.url==='https://api.github.com/repos/andersenmartin-blip/setisearch/git/ref/heads/m43-support-qualification',
      'Only the selected branch head is delegated to the actual connector');
    else{
      assert(args.repository_full_name==='andersenmartin-blip/setisearch','Exact public engineering repository required');
      if(packet.tool.endsWith('_update_ref'))assert(args.branch_name==='m43-support-qualification'&&args.force===false,
        'Only one selected nonforced branch update permitted');
    }
  }
  async function extract(packet,deadline) {
    const view=packet.request_view,reads=packet.reads;
    assert(view&&view.schema==='radio-native-v2-existing-request-view-v1'&&packet.arguments===null&&
      Array.isArray(reads)&&reads.length>0&&reads.length<=61&&Number.isSafeInteger(view.offset)&&view.offset>=0&&
      Number.isSafeInteger(view.bytes)&&view.bytes>0&&view.bytes<=48*CLIENT_MIB&&
      typeof view.path==='string'&&/^\/[A-Za-z0-9_./-]+$/.test(view.path)&&
      view.path.slice(1).split('/').every(p=>p&&p!=='.'&&p!=='..')&&/\/items\/request-[0-9]{6}\/part$/.test(view.path)&&
      /^[0-9a-f]{64}$/.test(view.sha256)&&/^[0-9a-f]{64}$/.test(view.source_sha256),
      'Exact prospective existing-worker request view required');
    assert(typeof options.python==='string'&&/^\/[A-Za-z0-9_./-]+$/.test(options.python),
      'Pinned Python executable required for source extraction');
    const quote=value=>"'"+value.replace(/'/g,"'\\''")+"'",source='import os,sys; f=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW); '+
      'n=int(sys.argv[3]); b=os.pread(f,n,int(sys.argv[2])); '+
      'assert len(b)==n; sys.stdout.buffer.write(b); os.close(f)';
    let cursor=view.offset,sumRequests=0,sumReservations=0;
    for(let i=0;i<reads.length;i++){
      const p=reads[i];assert(p.ordinal===i&&p.tool==='exec_command'&&p.path===view.path&&p.offset===cursor&&
        p.source_sha256===view.source_sha256&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.bytes<=CLIENT_LIMITS.read_bytes&&
        /^[0-9a-f]{64}$/.test(p.output_sha256)&&Number.isSafeInteger(p.response_reserved_bytes)&&
        p.response_reserved_bytes>=p.bytes&&p.response_reserved_bytes<=2*CLIENT_LIMITS.read_bytes+8192,
        'Exact sequential pre-reserved source extraction required');
      const expected={cmd:quote(options.python)+' -I -S -B -c '+quote(source)+' '+quote(view.path)+' '+p.offset+' '+p.bytes,
        max_output_tokens:400000,yield_time_ms:1000};
      assert(JSON.stringify(p.arguments)===JSON.stringify(expected),'Only the pinned bounded source reader command permitted');
      sumRequests+=h.utf8Bytes(JSON.stringify({tool:'exec_command',arguments:p.arguments}));sumReservations+=p.response_reserved_bytes;
      cursor+=p.bytes;
    }
    assert(cursor===view.offset+view.bytes&&usage.calls+reads.length<=maxCalls&&
      usage.request_bytes+sumRequests<=requestCap&&
      usage.response_charged_bytes+sumReservations<=responseCap,
      'Whole readonly extraction batch cannot fit original actual allocations');
    const settled=await Promise.allSettled(reads.map(p=>call('exec_command',p.arguments,p.response_reserved_bytes,'actual_source_read',deadline)));
    const parts=[],descriptors=[];
    for(let i=0;i<settled.length;i++){
      const result=settled[i];assert(result.status==='fulfilled','Source extraction failed; whole scope closed');
      const raw=result.value,p=reads[i];assert(raw.exit_code===0&&raw.session_id===undefined&&typeof raw.output==='string'&&
        h.utf8Bytes(raw.output)===p.bytes&&h.sha256(raw.output)===p.output_sha256,'Exact complete source bytes differ');
      parts.push(raw.output);const entries=Object.entries(raw).map(([k,v])=>[k,k==='output'?null:v]),rawJson=JSON.stringify(raw);
      assert(entries.length<=16&&h.utf8Bytes(JSON.stringify(entries))<=8192,'Bounded complete observed read envelope metadata required');
      descriptors.push({schema:'radio-native-v2-reconstructed-read-receipt-v1',path:p.path,offset:p.offset,bytes:p.bytes,
        source_sha256:p.source_sha256,envelope_entries:entries,envelope_bytes:h.utf8Bytes(rawJson),envelope_sha256:h.sha256(rawJson)});
    }
    const params=parts.join('');assert(h.utf8Bytes(params)===view.bytes&&h.sha256(params)===view.sha256,'Independent complete params pin differs');
    assert(view.request_prefix==='{"tool":'+JSON.stringify(packet.tool)+',"arguments":'&&
      view.request_suffix==='}'&&typeof h.sha256Chunks==='function',
      'Exact connector wrapper and pinned streaming ASCII hash required');
    // Hash the already retained immutable fragments without allocating a
    // second full-size wrapper string. Parse the argument object directly.
    assert(h.utf8Bytes(view.request_prefix)+view.bytes+h.utf8Bytes(view.request_suffix)===view.request_bytes&&
      h.sha256Chunks([view.request_prefix,...parts,view.request_suffix])===view.request_sha256,
      'Actual complete connector request pin differs');
    const args=JSON.parse(params);assert(args&&typeof args==='object'&&!Array.isArray(args),
      'Exact connector argument object reconstruction required');
    return {args,descriptors};
  }
  try {
    assert(options.startup_arguments&&typeof options.startup_arguments.cmd==='string'&&
      options.startup_arguments.max_output_tokens===400000&&[1000,10000,QUALIFIED_SUPPORT_YIELD_MS].includes(options.startup_arguments.yield_time_ms),
      'Concrete bounded single-controller startup arguments required');
    const startAt=clock();startRaw=await call('exec_command',options.startup_arguments,
      CLIENT_LIMITS.support_response,'actual_controller_start');let current=messages(startRaw,startAt);
    while(true){
      while(!current)current=await poll();const packet=current.packet;
      if(packet.kind==='terminal'){assert(ordinal===CLIENT_SEQUENCE.length,'Controller terminated before six complete connector exchanges');terminal=packet;break;}
      assert(packet.kind==='request'&&packet.ordinal===ordinal,'Fresh single controller request required');
      // Absolute worker time is preferred; fallback starts at the supporting
      // dispatch, conservatively including the SDK's entire observed wait.
      const deadline=Number.isFinite(packet.worker_deadline_epoch_ms)?packet.worker_deadline_epoch_ms:
        current.dispatchedAt+packet.deadline_ms;
      assert(Number.isFinite(deadline)&&deadline>clock(),'Worker deadline expired before any delegated dispatch');
      let args=packet.arguments,descriptors=[];
      if(packet.request_view){const extracted=await extract(packet,deadline);args=extracted.args;descriptors=extracted.descriptors;}
      else assert(Array.isArray(packet.reads)&&packet.reads.length===0,'Unplanned source reads refused');
      approvedCore(packet,args);check(deadline);
      assert(Number.isSafeInteger(packet.delivery_request_reserved_bytes)&&packet.delivery_request_reserved_bytes>0&&
        packet.delivery_request_reserved_bytes<=requestCap,'Exact pre-dispatch controller ingress reservation required');
      const coreRequestBytes=h.utf8Bytes(JSON.stringify({tool:packet.tool,arguments:args}));
      assert(usage.calls+2<=maxCalls&&usage.request_bytes+coreRequestBytes+packet.delivery_request_reserved_bytes<=requestCap&&
        usage.response_charged_bytes+CLIENT_CORE[packet.tool]+CLIENT_LIMITS.support_response<=responseCap,
        'Cannot reserve connector and following complete ingress before external dispatch');
      pendingDelivery={ordinal,request_reserved_bytes:packet.delivery_request_reserved_bytes,
        response_reserved_bytes:CLIENT_LIMITS.support_response,dispatch_attempted:false};
      const raw=await call(packet.tool,args,CLIENT_CORE[packet.tool],'actual_connector',deadline);
      assert(raw&&raw.isError!==true,'Actual connector returned an error; no retry');
      progress({kind:'connector',ordinal,tool:packet.tool,calls:usage.calls});
      const deliveryArgs={session_id:session,max_output_tokens:400000,yield_time_ms:supportYield},
        body={schema:CONTROLLER_SCHEMA,ordinal,automatic_retry:false,delivery_arguments:deliveryArgs,
          raw_connector_result:raw,read_descriptors:descriptors,start_raw:ordinal===0?startRaw:null,
          previous_delivery_raw:previousDeliveryRaw},line=JSON.stringify(body),
        actualArgs={session_id:session,chars:line+'\n',max_output_tokens:400000,yield_time_ms:supportYield},
        actualRequest=JSON.stringify({tool:'write_stdin',arguments:actualArgs});
      assert(h.utf8Bytes(actualRequest)<=packet.delivery_request_reserved_bytes,
        'Actual delivery exceeds the controller pre-dispatch ingress reservation');
      pendingDelivery.dispatch_attempted=true;
      const at=clock(),delivered=await call('write_stdin',actualArgs,CLIENT_LIMITS.support_response,'actual_delivery',deadline);
      pendingDelivery=null;previousDeliveryRaw=delivered;ordinal++;current=messages(delivered,at);
    }
  }catch(error){stop(error);}
  return {schema:CLIENT_SCHEMA,status:stopped?'CLOSED_FAILED':'SINGLE_CASE_COMPONENT_COMPLETE',reason,
    usage:{...usage,conservatively_charged_local_git_processes:4,
      calls_including_declared_git_processes:usage.calls+4,elapsed_seconds:(clock()-started)/1000,
      hidden_http_bytes_known:false,all_actual_start_poll_read_connector_delivery_calls_counted:true},
    prospective_caps:{actual_calls:maxCalls,request_bytes:requestCap,response_bytes:responseCap,
      support_yield_time_ms:supportYield,caller_tail_calls:tailCalls,
      caller_tail_request_bytes:QUALIFIED_RUNNER_LIMITS.caller_tail_request_bytes,
      caller_tail_response_bytes:QUALIFIED_RUNNER_LIMITS.caller_tail_response_bytes},
    controller_terminal:terminal,session_id:session,connector_requests:ordinal,records,events,
    pending_delivery_reservation:pendingDelivery,
    last_supporting_acknowledgement_durable:false,controller_poll_receipts_joined_into_host_ledger:false,
    actual_client_runtime_rss_known:false,execution_authorized:false,reservation_authorized:false,
    scientific_execution_authorized:false,rng_draws:0,telescope_reads:0,automatic_retry:false};
}
if(typeof module!=='undefined')module.exports={CLIENT_SCHEMA,CONTROLLER_SCHEMA,CLIENT_CORE,CLIENT_SEQUENCE,
  CLIENT_LIMITS,QUALIFIED_SUPPORT_YIELD_MS,QUALIFIED_RUNNER_LIMITS,runToolCourier};
