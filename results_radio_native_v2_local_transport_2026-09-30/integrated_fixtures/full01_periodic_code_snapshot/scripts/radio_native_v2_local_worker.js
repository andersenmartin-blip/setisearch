// Local Node/Python filesystem custody, with no functions tool calls.
// This uses the unchanged Store limits and grants no execution authority.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process');
const LOCAL_WORKER_SCHEMA='radio-native-v2-local-worker-v1';
const LOCAL_PROJECTION_REPLY='radio-native-v2-local-projection-reply-v1';
const MIB=1024*1024;
const LOCAL_WORKER_LIMITS=Object.freeze({helper_calls:4096,helper_seconds:30,seconds:4800,
  stdin_payload_bytes:64*MIB,stdout_bytes:MIB,stderr_bytes:65536});
const RESPONSE_RESERVATIONS=Object.freeze({'invoke:fetch':4*MIB,'invoke:create_tree':MIB,
  'invoke:create_commit':65536,'invoke:update_ref':16384,'invoke:fetch_files':48*MIB,
  prepare_transport:MIB,finish_transport:MIB,transport_usage:MIB});
const sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const assert=(value,message)=>{if(!value)throw Error(message);};
const safeAbsolute=value=>{
  assert(typeof value==='string'&&value.startsWith('/')&&value!=='/'&&
    value.slice(1).split('/').every(v=>v&&v!=='.'&&v!=='..')&&!/[\\\x00-\x1f]/.test(value),
    'Canonical absolute local worker path required');return value;
};

function createLocalWorker(options) {
  const h=options.hostLibrary||require('./radio_native_v2_broker_host');
  const canonical=value=>h.canonical(value).replace(/[\u0080-\uffff]/g,ch=>'\\u'+ch.charCodeAt(0).toString(16).padStart(4,'0'));
  const root=safeAbsolute(options.root),python=safeAbsolute(options.python),sourceRoot=safeAbsolute(options.sourceRoot),
    helper=safeAbsolute(options.helper||path.join(__dirname,'radio_native_v2_local_worker_helper.py'));
  const limits={...LOCAL_WORKER_LIMITS,...options.limits};
  assert(Object.keys(limits).sort().join()===Object.keys(LOCAL_WORKER_LIMITS).sort().join()&&
    Object.entries(limits).every(([k,v])=>Number.isSafeInteger(v)&&v>0&&v<=LOCAL_WORKER_LIMITS[k]),
    'Complete fixed local worker limits required');
  const clock=options.clock||Date.now,started=clock(),records=[];
  const counters={helper_calls:0,helper_stdin_bytes:0,helper_stdout_bytes:0,helper_stderr_bytes:0,
    helper_max_rss_kib:0,local_read_bytes:0,local_write_bytes:0,local_stop_bytes:0,worker_requests:0,functions_tool_calls:0};
  let stopped=false,busy=false,workerOrdinal=0,itemOrdinal=0,currentCase=null,workerDeadline=null,stopReason=null,durableStopConfirmed=false;
  const stop=error=>{
    stopped=true;stopReason=String(error);
    // A local fatal error must be visible to every future Store participant.
    // This fixed bounded ledger tail is already charged by Store._status().
    try {
      if(fs.lstatSync(root).isDirectory()) {
        const name=root+'/STOPPED.json',raw=canonical({schema:'radio-native-v2-filesystem-bridge-v1',
          reason:stopReason.slice(0,256),automatic_retry:false});
        let fd;
        try {fd=fs.openSync(name,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o400);
          fs.writeFileSync(fd,raw);fs.fsyncSync(fd);counters.local_stop_bytes+=Buffer.byteLength(raw);
        }catch(failure){if(failure.code!=='EEXIST')throw failure;
          const existing=readMetadata(name);assert(existing.schema==='radio-native-v2-filesystem-bridge-v1'&&
            existing.automatic_retry===false,'Existing stop marker differs');}
        finally{if(fd!==undefined)fs.closeSync(fd);}
        const directory=fs.openSync(root,fs.constants.O_RDONLY|fs.constants.O_DIRECTORY|fs.constants.O_NOFOLLOW);
        try{fs.fsyncSync(directory);}finally{fs.closeSync(directory);}durableStopConfirmed=true;
      }
    }catch(failure){durableStopConfirmed=false;}
    return error;
  };
  const left=()=>Math.min(limits.helper_seconds*1000,started+limits.seconds*1000-clock(),
    workerDeadline===null?Infinity:workerDeadline-clock());
  const check=()=>assert(!stopped&&left()>0,'Local worker stopped or deadline exhausted; no retry');
  const identity=kind=>kind+'-'+String(itemOrdinal++).padStart(8,'0');
  function readMetadata(filename) {
    const fd=fs.openSync(filename,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
    try {
      const stat=fs.fstatSync(fd);assert(stat.isFile()&&stat.nlink===1&&stat.size<=4096,'Bounded sole local metadata file required');
      const raw=fs.readFileSync(fd);assert(raw.length===stat.size,'Immutable local metadata size differs');
      return JSON.parse(raw.toString('utf8'));
    }finally{fs.closeSync(fd);}
  }

  async function action(value,payload=null) {
    check();assert(!busy,'Sequential local helper only');busy=true;
    let child,timer,record;
    try {
      assert(counters.helper_calls<limits.helper_calls,'Local helper call cap exhausted');
      const pieces=payload===null?[]:Array.isArray(payload)?payload:[payload];
      assert(pieces.every(p=>typeof p==='string'),'Exact raw UTF-8 local payload frames required');
      const header=canonical({...value,root})+'\n',headerBytes=Buffer.byteLength(header),
        payloadBytes=pieces.reduce((sum,p)=>sum+Buffer.byteLength(p),0);
      assert(headerBytes<=MIB&&payloadBytes<=limits.stdin_payload_bytes,
        'Bounded local helper stdin required');
      assert(payload===null||['write_utf8','fill_utf8','write_frames'].includes(value.action),'Raw stdin only for reserved payload write');
      const bootstrap='import runpy,sys;sys.path.insert(0,sys.argv[1]);runpy.run_path(sys.argv[2],run_name="__main__")';
      const launch=typeof options.helperLaunch==='function'?await options.helperLaunch():options.helperLaunch;
      const args=launch?launch.args:['-I','-B','-c',bootstrap,sourceRoot,helper];
      if(launch)assert(launch.executable===python&&Array.isArray(args)&&args.slice(0,3).join()==='-I,-S,-B'&&
        args.every(v=>typeof v==='string'&&!v.includes('\0'))&&launch.env&&
        /^[0-9a-f]{64}$/.test(launch.source_loader_sha256)&&/^[0-9a-f]{64}$/.test(launch.source_policy_sha256)&&
        /^[0-9a-f]{64}$/.test(launch.freeze_sha256),
        'Pinned isolated source-only helper launch plan required');
      record={ordinal:records.length,classification:'LOCAL_FS_HELPER_NOT_TOOL',action:value.action,
        stdin_bytes:headerBytes+payloadBytes,header_sha256:sha(header),payload_sha256:payload===null?null:
          pieces.reduce((hasher,p)=>hasher.update(p),crypto.createHash('sha256')).digest('hex'),
        automatic_retry:false,started_ms:clock()-started,child_pid:null,stdout_bytes:0,stderr_bytes:0};
      records.push(record);counters.helper_calls++;counters.helper_stdin_bytes+=headerBytes+payloadBytes;
      const result=await new Promise((resolve,reject)=>{
        let stdout=[],stderr=[],stdoutBytes=0,stderrBytes=0,finished=false;
        const fail=error=>{if(finished)return;finished=true;if(child)child.kill('SIGKILL');reject(error);};
        timer=setTimeout(()=>fail(Error('Local helper deadline exceeded; no retry')),left());
        child=cp.spawn(python,args,{stdio:['pipe','pipe','pipe'],env:launch?launch.env:{...process.env,PYTHONPATH:undefined}});
        record.child_pid=child.pid;
        child.on('error',fail);child.stdin.on('error',fail);
        child.stdout.on('data',raw=>{stdoutBytes+=raw.length;counters.helper_stdout_bytes+=raw.length;
          record.stdout_bytes=stdoutBytes;if(stdoutBytes>limits.stdout_bytes)fail(Error('Bounded local helper stdout exceeded'));
          else stdout.push(raw);});
        child.stderr.on('data',raw=>{stderrBytes+=raw.length;counters.helper_stderr_bytes+=raw.length;
          record.stderr_bytes=stderrBytes;if(stderrBytes>limits.stderr_bytes)fail(Error('Bounded local helper stderr exceeded'));
          else stderr.push(raw);});
        child.on('close',(code,signal)=>{
          record.exit_code=code;record.signal=signal;record.elapsed_ms=clock()-started-record.started_ms;
          if(finished)return;finished=true;clearTimeout(timer);
          const raw=Buffer.concat(stdout),err=Buffer.concat(stderr);record.stdout_sha256=sha(raw);record.stderr_sha256=sha(err);
          if(code!==0||signal){reject(Error('Local helper failed; no retry: '+err.toString('utf8').slice(0,1024)));return;}
          try {
            const parsed=JSON.parse(raw.toString('utf8'));
            assert(parsed&&typeof parsed==='object'&&parsed.local_process&&
              parsed.local_process.pid===child.pid&&Number.isSafeInteger(parsed.local_process.max_rss_kib)&&
              parsed.local_process.max_rss_kib>=0,
              'Measured local subprocess acknowledgement required');
            record.reported_pid=parsed.local_process.pid;record.max_rss_kib=parsed.local_process.max_rss_kib;
            counters.helper_max_rss_kib=Math.max(counters.helper_max_rss_kib,record.max_rss_kib);
            if(launch) {
              const proof=parsed.source_loader_preflight;
              assert(proof&&proof.schema==='radio-native-v2-source-loader-preflight-v1'&&
                proof.entrypoint_sha256===launch.source_loader_sha256&&proof.freeze_sha256===launch.freeze_sha256&&
                proof.helper_bootstrap_sha256===launch.source_policy_sha256&&
                Array.isArray(proof.modules)&&proof.modules.length===1&&proof.modules[0]===path.basename(helper,'.py')&&
                proof.source_only_imports_verified===true&&proof.site_hooks_disabled===true&&
                proof.environment_isolated===true&&proof.bytecode_cache_read===false&&proof.bytecode_cache_write===false&&
                ['reservation_authorized','rng_authorized','execution_authorized','scientific_execution_authorized',
                  'restart_authorized','transport_integration_qualified'].every(k=>proof[k]===false),
                'Actual source-only helper preflight binding required');
              record.source_loader_verified=true;record.source_loader_sha256=proof.entrypoint_sha256;
              record.source_loader_freeze_sha256=proof.freeze_sha256;
            }else record.source_loader_verified=false;
            resolve(parsed.result);
          }catch(error){reject(error);}
        });
        child.stdin.write(header);for(const piece of pieces)child.stdin.write(piece);child.stdin.end();
      });
      return result;
    }catch(error){if(record)record.error=String(error);throw stop(error);}
    finally{clearTimeout(timer);busy=false;}
  }

  // The qualification scope is a stable private filesystem: sealed files are
  // opened NOFOLLOW, independently hashed and never trusted by pathname alone.
  function read(item) {
    check();assert(item&&/^[a-z0-9_-]{1,80}$/.test(item.id)&&Number.isSafeInteger(item.bytes)&&
      item.bytes>=0&&item.bytes<=64*MIB&&/^[0-9a-f]{64}$/.test(item.sha256),'Exact bounded sealed item receipt required');
    const filename=root+'/items/'+item.id+'/part';
    let current='';for(const component of path.dirname(filename).split('/').filter(Boolean)) {
      current+='/'+component;assert(fs.lstatSync(current).isDirectory(),'Private Store ancestors must be actual directories');
    }
    const marker=readMetadata(root+'/items/'+item.id+'/sealed.json');
    assert(marker.id===item.id&&marker.bytes===item.bytes&&marker.sha256===item.sha256&&marker.durable===true,
      'Local sealed marker differs');
    const fd=fs.openSync(filename,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
    try {
      const stat=fs.fstatSync(fd);assert(stat.isFile()&&stat.nlink===1&&stat.size===item.bytes,
        'Exact sole sealed regular part required');
      const raw=fs.readFileSync(fd);counters.local_read_bytes+=raw.length;
      assert(raw.length===item.bytes&&sha(raw)===item.sha256&&fs.fstatSync(fd).size===item.bytes,
        'Independently hashed local sealed part differs');return raw;
    }finally{fs.closeSync(fd);}
  }

  async function put(kind,value,caseOrdinal=currentCase) {
    assert(typeof value==='string','Exact UTF-8 raw local value required');
    const id=identity(kind),bytes=Buffer.byteLength(value),digest=sha(value);
    const receipt=await action({action:'write_utf8',id,kind,bytes,sha256:digest,case_ordinal:caseOrdinal},value);
    assert(receipt.bytes===bytes&&receipt.sha256===digest&&receipt.durable===true,'Exact local durable write differs');
    counters.local_write_bytes+=bytes;return{...receipt,id};
  }

  async function persistRaw(record) {
    assert(typeof record.request_json==='string'&&typeof record.response_json==='string'&&
      record.storage_json===JSON.stringify({request_json:record.request_json,response_json:record.response_json}),
      'Untouched complete connector request/reply receipt required');
    const receipt=await put('host_receipt',record.storage_json);
    return{request_bytes:Buffer.byteLength(record.request_json),request_sha256:sha(record.request_json),
      response_bytes:Buffer.byteLength(record.response_json),response_sha256:sha(record.response_json),
      stored_bytes:receipt.bytes,stored_sha256:receipt.sha256};
  }

  async function persistRawBatch(rawRecords) {
    assert(Array.isArray(rawRecords)&&rawRecords.length>0&&rawRecords.length<=128,'Bounded local raw receipt batch required');
    const frames=rawRecords.map(record=>{
      assert(typeof record.request_json==='string'&&typeof record.response_json==='string'&&
        record.storage_json===JSON.stringify({request_json:record.request_json,response_json:record.response_json}),
        'Untouched complete raw receipt batch required');
      return{id:identity('host_receipt'),kind:'host_receipt',bytes:Buffer.byteLength(record.storage_json),
        sha256:sha(record.storage_json),case_ordinal:currentCase};
    });
    const receipts=await action({action:'write_frames',frames},rawRecords.map(record=>record.storage_json));
    assert(Array.isArray(receipts)&&receipts.length===frames.length&&receipts.every((receipt,index)=>
      receipt.id===frames[index].id&&receipt.bytes===frames[index].bytes&&receipt.sha256===frames[index].sha256&&receipt.durable===true),
      'Exact local batch receipt durability required');
    counters.local_write_bytes+=frames.reduce((sum,frame)=>sum+frame.bytes,0);
    return rawRecords.map((record,index)=>({request_bytes:Buffer.byteLength(record.request_json),request_sha256:sha(record.request_json),
      response_bytes:Buffer.byteLength(record.response_json),response_sha256:sha(record.response_json),
      stored_bytes:receipts[index].bytes,stored_sha256:receipts[index].sha256}));
  }

  async function groupedGitReadback(job) {
    await job.callGit('git_fetch');await job.callGit('git_cat_file_batch');
    const id=identity('git_projection');
    const verified=await action({action:'git_projection',id,spool_path:job.spool_path,commit:job.commit,
      paths:job.paths,files:job.files,case_ordinal:currentCase});
    return{commit:job.commit,single_cat_file_batch:true,raw_git_receipt:verified.raw_git_receipt,
      projection_verification:verified.projection_verification,
      local_projection:{id,path:verified.projection.path,bytes:verified.projection.bytes,
        sha256:verified.projection.sha256,durable:verified.projection.durable}};
  }

  async function serviceOne(brokerHost) {
    let requestClaimed=false;
    try {
      check();const state=await action({action:'pending'});
      assert(state.stopped===false&&state.pending_count===state.pending.length&&state.pending.length<=1,
        'Exactly one outstanding local worker request required');
      if(!state.pending.length)return{serviced:false};
      const item=state.pending[0],raw=read(item),packet=JSON.parse(raw.toString('utf8'));
      assert(packet.schema==='radio-native-v2-filesystem-bridge-v1'&&
        packet.ordinal===workerOrdinal&&item.id==='request-'+String(workerOrdinal).padStart(6,'0')&&
        packet.response_id==='response-'+String(workerOrdinal).padStart(6,'0')&&packet.automatic_retry===false&&
        RESPONSE_RESERVATIONS[packet.operation]===packet.response_reserved_bytes&&
        Object.keys(packet).sort().join()===['schema','ordinal','operation','params','response_id','response_reserved_bytes',
          'case_ordinal','automatic_retry','deadline_monotonic_seconds'].sort().join(),
        'Exact canonical fresh local worker packet required');
      const claimedAt=clock(),claim=await action({action:'claim',id:item.id}),remaining=claim.remaining_seconds*1000-(clock()-claimedAt);
      assert(claim.claimed===true&&claim.request_sha256===item.sha256&&Number.isFinite(remaining)&&remaining>0,
        'Irrevocable fresh Store request claim required');
      requestClaimed=true;workerDeadline=clock()+remaining;
      // Store.claim has independently reserialized the complete packet and
      // verified its canonical bytes. Reuse the sole immutable params slice;
      // do not serialize another 37 MiB create_tree request inside Node.
      const paramsOffset=raw.indexOf(Buffer.from(',"params":'))+10,
        paramsEnd=raw.lastIndexOf(Buffer.from(',"response_id":'));
      assert(paramsOffset>=10&&paramsEnd>=paramsOffset,'Contiguous canonical packet params range required');
      const params=raw.subarray(paramsOffset,paramsEnd);
      const source={packet,path:root+'/items/'+item.id+'/part',bytes:item.bytes,sha256:item.sha256,
        params_offset:paramsOffset,params_bytes:params.length,params_sha256:sha(params)};
      if(typeof brokerHost.setRequestSource==='function')brokerHost.setRequestSource(source);
      if(options.onClaim)await options.onClaim(source);
      const operation=async()=>{
        check();let result;
        if(packet.operation==='prepare_transport') {
          currentCase=packet.case_ordinal;assert(Number.isSafeInteger(currentCase)&&currentCase>=0&&currentCase<8&&
            JSON.parse(packet.params.freeze_json).ordinal===currentCase,'Exact worker/host case binding required');
          brokerHost.beginCase(packet.params.freeze_json,packet.params.bundle_sha256);result={prepared:true};
        }else if(packet.operation==='finish_transport')result=brokerHost.finishCase();
        else if(packet.operation==='transport_usage')result=brokerHost.usage();
        else {
          assert(/^invoke:(fetch|create_tree|create_commit|update_ref|fetch_files)$/.test(packet.operation)&&
            packet.case_ordinal===currentCase,'Fixed case-bound worker operation required');
          result=await brokerHost.invoke(packet.operation.slice(7),packet.params);
        }
        check();let receipt;
        if(result&&result.schema===LOCAL_PROJECTION_REPLY) {
          assert(packet.operation==='invoke:fetch_files'&&Object.keys(result).sort().join()==='projection,schema'&&
            result.projection.bytes<=packet.response_reserved_bytes,'Exact deferred fetch_files-only result required');
          receipt=await action({action:'ingest_pinned_file',id:packet.response_id,source:result.projection});
        }else {
          const response=canonical(result),bytes=Buffer.byteLength(response),digest=sha(response);
          assert(bytes<=packet.response_reserved_bytes,'Fixed pre-reserved worker reply exceeded');
          // The response reservation already exists, so fill its sole part.
          receipt=await action({action:'fill_utf8',id:packet.response_id,bytes,sha256:digest},response);
        }
        assert(receipt.durable===true,'Immutable local Worker response durability unconfirmed');
        counters.worker_requests++;workerOrdinal++;
        return{serviced:true,ordinal:packet.ordinal,operation:packet.operation,response:receipt};
      };
      if(typeof brokerHost.withWorkerDeadline==='function')return await brokerHost.withWorkerDeadline(workerDeadline,operation);
      return await operation();
    }catch(error){throw stop(error);}
    finally{workerDeadline=null;if(requestClaimed&&typeof brokerHost.clearRequestSource==='function')brokerHost.clearRequestSource();}
  }

  return{action,put,read,persistRaw,persistRawBatch,groupedGitReadback,serviceOne,
    usage:()=>({schema:LOCAL_WORKER_SCHEMA,...counters,elapsed_seconds:(clock()-started)/1000,automatic_retry:false}),
    state:()=>({stopped,busy,stop_reason:stopReason,durable_stop_confirmed:durableStopConfirmed,records:records.map(row=>({...row}))}),
    capabilityManifest:()=>({schema:LOCAL_WORKER_SCHEMA,status:'LOCAL_COMPONENT_NOT_EXECUTION_QUALIFIED',limits,
      store_limits_unchanged:true,local_helper_is_not_functions_tool:true,large_projection_stays_local:true,
      private_stable_filesystem_scope:true,helper_entrypoint_source_qualified:records.length>0&&records.every(r=>r.source_loader_verified===true),
      execution_authorized:false,scientific_execution_authorized:false,automatic_retry:false,rng_draws:0,telescope_reads:0})};
}
module.exports={LOCAL_WORKER_SCHEMA,LOCAL_PROJECTION_REPLY,LOCAL_WORKER_LIMITS,createLocalWorker};
