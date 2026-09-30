'use strict';
// Single-case prospective courier controller. It cannot activate native cases.
const fs=require('node:fs'),cp=require('node:child_process'),crypto=require('node:crypto');
const transport=require('./radio_native_v2_local_transport'),
  workerModule=require('./radio_native_v2_local_worker'),
  {LocalGit}=require('./radio_native_v2_local_git');
const SCHEMA='radio-native-v2-local-tool-courier-v1',MIB=1024*1024;
const hash=value=>crypto.createHash('sha256').update(value).digest('hex');
const assert=(ok,message)=>{if(!ok)throw Error(message);};
const CONTROL_REPLY_BYTES=128*1024;

class BoundedLines {
  constructor(deliver,maxBytes=9*MIB){this.deliver=deliver;this.maxBytes=maxBytes;this.parts=[];this.bytes=0;}
  accept(raw){
    assert(Buffer.isBuffer(raw),'Exact stdin byte chunks required');
    let at=0;
    while(at<raw.length){
      const newline=raw.indexOf(10,at),end=newline<0?raw.length:newline,part=raw.subarray(at,end);
      assert(this.bytes+part.length<=this.maxBytes,'Prospective stdin frame exceeds bounded allocation');
      this.parts.push(part);this.bytes+=part.length;
      if(newline<0)return;
      const line=Buffer.concat(this.parts,this.bytes).toString('utf8');
      assert(Buffer.byteLength(line)===this.bytes,'Exact UTF-8 stdin required');
      this.parts=[];this.bytes=0;this.deliver(line);at=newline+1;
    }
  }
}

function deliveryRequest(line,argumentsWithoutChars) {
  assert(argumentsWithoutChars&&Number.isSafeInteger(argumentsWithoutChars.session_id)&&
    argumentsWithoutChars.max_output_tokens===400000&&argumentsWithoutChars.yield_time_ms===1000&&
    Object.keys(argumentsWithoutChars).sort().join()==='max_output_tokens,session_id,yield_time_ms',
    'Exact visible delivery arguments required');
  return JSON.stringify({tool:'write_stdin',arguments:{session_id:argumentsWithoutChars.session_id,
    chars:line+'\n',max_output_tokens:400000,yield_time_ms:1000}});
}

// The unknown delivery body is reserved before either source extraction or
// connector dispatch. Reconcile against the exact observed stdin bytes once.
class ToolCourier {
  constructor({ledger,persistRaw,persistRawBatch,python,startRequest,emit}) {
    assert(ledger instanceof transport.SharedLedger&&typeof persistRaw==='function'&&
      typeof persistRawBatch==='function'&&typeof emit==='function','Concrete courier dependencies required');
    this.ledger=ledger;this.persistRaw=persistRaw;this.persistRawBatch=persistRawBatch;
    this.python=python;this.startRequest=startRequest;this.emit=emit;this.sequence=0;
    this.pending=null;this.previous=null;this.startToken=null;this.started=false;this.stopped=false;this.host=null;
    this.controlStorageBytes=0;this.controlStorageItems=0;
  }
  bindHost(host){assert(!this.host,'Courier host already bound');this.host=host;}
  reserveStart() {
    assert(!this.started&&this.startToken===null&&typeof this.startRequest==='string','One predeclared startup request required');
    this.startToken=this.ledger.reserve({tool:'exec_command',request_bytes:Buffer.byteLength(this.startRequest),
      request_sha256:hash(this.startRequest),response_reservation:CONTROL_REPLY_BYTES,label:'actual_controller_start'});this.started=true;
  }
  async saveControl(token,requestJson,raw,label) {
    const observed=this.ledger.complete(token,raw,{checkDeadline:false}),storage_json=JSON.stringify({
      request_json:requestJson,response_json:observed.json});
    const saved=await this.persistRaw({operation:label,tool:label==='controller_start'?'exec_command':'write_stdin',
      request_json:requestJson,response_json:observed.json,storage_json});
    assert(Object.keys(saved).sort().join()==='request_bytes,request_sha256,response_bytes,response_sha256,stored_bytes,stored_sha256'&&
      saved.stored_bytes===Buffer.byteLength(storage_json)&&saved.stored_sha256===hash(storage_json)&&
      saved.request_bytes===Buffer.byteLength(requestJson)&&saved.response_bytes===observed.bytes&&
      saved.request_sha256===hash(requestJson)&&saved.response_sha256===observed.sha256,
      'Exact full control receipt custody differs');
    this.controlStorageBytes+=saved.stored_bytes;this.controlStorageItems++;
  }
  async request(tool,args,context) {
    assert(!this.stopped&&!this.pending&&this.host,'One concrete courier request at a time');
    if(!this.started)this.reserveStart();
    const reads=context.request_view?this.host.prepareCourierReads(context.request_view,{python:this.python}):[];
    const intent={schema:SCHEMA,ordinal:this.sequence,tool,connector_response_reserved_bytes:context.response_reserved_bytes},
      reservation=2*context.response_reserved_bytes+reads.length*(2*8192+1024)+
        2*CONTROL_REPLY_BYTES*(this.previous?1:0)+2*CONTROL_REPLY_BYTES*(this.startToken!==null?1:0)+8192,
      token=this.ledger.reserveUnknownRequest({tool:'write_stdin',request_reservation:reservation,
        request_intent_sha256:hash(JSON.stringify(intent)),response_reservation:CONTROL_REPLY_BYTES,
        label:'actual_courier_delivery'});
    const outgoing={schema:SCHEMA,kind:'request',ordinal:this.sequence++,tool,
      arguments:context.request_view?null:args,request_view:context.request_view,reads,
      delivery_token:token,delivery_request_reserved_bytes:reservation,
      deadline_ms:context.deadline_ms,automatic_retry:false};
    assert(Buffer.byteLength(JSON.stringify(outgoing))<=112*1024,'Bounded outgoing control transcript required');
    return await new Promise((resolve,reject)=>{
      this.pending={outgoing,token,reads,resolve,reject};this.emit(outgoing);
    });
  }
  async receive(line) {
    assert(typeof line==='string'&&Buffer.byteLength(line)<=9*MIB&&this.pending&&!this.stopped,
      'One bounded pending courier delivery required');
    const packet=JSON.parse(line),p=this.pending;
    assert(packet.schema===SCHEMA&&packet.ordinal===p.outgoing.ordinal&&packet.automatic_retry===false&&
      packet.raw_connector_result&&Array.isArray(packet.read_descriptors),
      'Exact ordered actual connector envelope required');
    const requestJson=deliveryRequest(line,packet.delivery_arguments);
    this.ledger.reconcileRequest(p.token,requestJson);
    if(this.startToken!==null){
      assert(packet.start_raw&&this.previous===null,'Actual startup envelope required exactly once');
      await this.saveControl(this.startToken,this.startRequest,packet.start_raw,'controller_start');this.startToken=null;
    }else assert(packet.start_raw===null,'Duplicate startup envelope refused');
    if(this.previous){
      assert(packet.previous_delivery_raw,'Full prior delivery envelope required');
      await this.saveControl(this.previous.token,this.previous.requestJson,packet.previous_delivery_raw,'courier_delivery');
    }else assert(packet.previous_delivery_raw===null,'Unexpected previous delivery envelope refused');
    if(p.reads.length)await this.host.completeCourierReads(p.reads,packet.read_descriptors);
    else assert(packet.read_descriptors.length===0,'Unplanned supporting extraction refused');
    this.previous={token:p.token,requestJson};this.pending=null;
    p.resolve(packet.raw_connector_result);
  }
  fail(error){this.stopped=true;this.ledger.stop(error);if(this.pending)this.pending.reject(error);}
  terminalRecord(){return {schema:SCHEMA,status:'SINGLE_CASE_COMPONENT_ONLY',connector_requests:this.sequence,
    control_receipt_stored_bytes:this.controlStorageBytes,control_receipt_items:this.controlStorageItems,
    last_delivery_acknowledgement_durable:false,last_delivery_ledger_token:this.previous?.token??null,
    late_envelope_durability_qualified:false,execution_authorized:false,reservation_authorized:false,
    scientific_execution_authorized:false,rng_draws:0,telescope_reads:0};}
}

function verifyGitMetadata(localGit) {
  for(const pin of localGit.snapshot().git_metadata_inputs){
    const filename=localGit.repoPath+'/'+pin.path;
    if(!pin.exists){assert(!fs.existsSync(filename),'Pinned Git configuration appeared');continue;}
    const fd=fs.openSync(filename,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
    try{const stat=fs.fstatSync(fd);assert(stat.isFile()&&stat.size===pin.bytes&&stat.size<=65536,
      'Pinned Git configuration size differs');assert(hash(fs.readFileSync(fd))===pin.sha256,'Pinned Git configuration drifted');}
    finally{fs.closeSync(fd);}
  }
}

function runGit(kind,plan,milliseconds,localGit=null) {
  assert(['git_fetch','git_cat_file_batch'].includes(kind)&&Number.isFinite(milliseconds)&&milliseconds>0,
    'Bounded generated Git operation required');
  if(localGit)verifyGitMetadata(localGit);
  return new Promise((resolve,reject)=>{
    const started=Date.now(),stdout=[],stderr=[];let outputBytes=0,errorBytes=0,fd=null,done=false,ioError=null;
    if(plan.stdout_path)fd=fs.openSync(plan.stdout_path,fs.constants.O_WRONLY|fs.constants.O_CREAT|
      fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o400);
    const child=cp.spawn(plan.executable,plan.args,{cwd:plan.cwd,stdio:['pipe','pipe','pipe'],
      env:localGit?localGit.env:{PATH:'/usr/bin:/bin',LANG:'C',LC_ALL:'C',GIT_NO_REPLACE_OBJECTS:'1',
        GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0',GIT_CONFIG_NOSYSTEM:'1',
        GIT_CONFIG_SYSTEM:'/dev/null',GIT_CONFIG_GLOBAL:'/dev/null',GIT_OPTIONAL_LOCKS:'0'}});
    const timer=setTimeout(()=>{if(!done)child.kill('SIGKILL');},Math.min(milliseconds,120000));
    child.on('error',error=>{clearTimeout(timer);if(fd!==null)fs.closeSync(fd);done=true;reject(error);});
    child.stdout.on('data',data=>{
      outputBytes+=data.length;
      if(fd!==null){if(outputBytes>40*MIB)child.kill('SIGKILL');else {
        try{let at=0;while(at<data.length){const written=fs.writeSync(fd,data,at,data.length-at);
          assert(written>0,'Raw Git spool short write');at+=written;}}
        catch(error){ioError=String(error);child.kill('SIGKILL');}
      }}
      else if(outputBytes>plan.maximum_output_bytes)child.kill('SIGKILL');else stdout.push(data);
    });
    child.stderr.on('data',data=>{errorBytes+=data.length;if(errorBytes>plan.maximum_output_bytes)child.kill('SIGKILL');else stderr.push(data);});
    child.on('close',(code,signal)=>{
      if(done)return;done=true;clearTimeout(timer);
      if(fd!==null){try{fs.fsyncSync(fd);fs.closeSync(fd);const directory=fs.openSync(plan.stdout_path.slice(0,plan.stdout_path.lastIndexOf('/')),
        fs.constants.O_RDONLY|fs.constants.O_DIRECTORY);try{fs.fsyncSync(directory);}finally{fs.closeSync(directory);}}
        catch(error){ioError=String(error);}}
      if(localGit){try{verifyGitMetadata(localGit);}catch(error){ioError=String(error);}}
      resolve({schema:'radio-native-v2-local-git-process-result-v1',classification:'LOCAL_PROCESS_NOT_TOOL_ENVELOPE',
        exit_code:ioError?1:code,signal,io_error:ioError,output:Buffer.concat(stdout).toString('utf8'),stderr:Buffer.concat(stderr).toString('utf8'),
        stdout_file_bytes:fd===null?0:outputBytes,wall_time_seconds:(Date.now()-started)/1000});
    });
    child.stdin.on('error',()=>{});child.stdin.end(plan.stdin_text||'');
  });
}

async function main(options) {
  assert(globalThis.__radioNativeV2SourcePolicy&&options&&options.fixture_namespace===transport.FIXTURE_PREFIX,
    'Pinned source-only prospective fixture entry required');
  assert(options.cases===1,'This controller is restricted to one prospective fixture case');
  const emit=value=>process.stdout.write(JSON.stringify(value)+'\n'),ledger=new transport.SharedLedger(),
    worker=workerModule.createLocalWorker({root:options.storeRoot,python:options.python,
      sourceRoot:options.root+'/src',helperLaunch:options.helperLaunch}),
    courier=new ToolCourier({ledger,persistRaw:worker.persistRaw,persistRawBatch:worker.persistRawBatch,
      python:options.python,startRequest:options.startRequest,emit}),
    localGit=new LocalGit({repoPath:options.repoPath,gitPath:options.gitPath}),
    host=transport.createLocalBrokerHost({ledger,localGit,courier:(...args)=>courier.request(...args),
      persistRaw:worker.persistRaw,persistRawBatch:worker.persistRawBatch,
      persistRawBatchLazy:worker.persistRawBatchLazy,persistRequestViewRaw:worker.persistRequestViewRaw,
      groupedGitReadback:worker.groupedGitReadback,
      runGit:(kind,plan,ms)=>runGit(kind,plan,ms,localGit),repoPath:options.repoPath,spoolRoot:options.spoolRoot,gitPath:options.gitPath,
      fixture_namespace:options.fixture_namespace});
  courier.bindHost(host);
  assert(options.publisherConfig&&options.publisherConfig.result_path===options.publisherResult,
    'Fixed actual-tool Publisher component configuration required');
  let failed=null,inputBusy=false;
  const receive=line=>{
    if(inputBusy){failed=Error('Overlapping actual courier delivery refused');courier.fail(failed);return;}
    inputBusy=true;courier.receive(line).catch(error=>{failed=error;courier.fail(error);}).finally(()=>{inputBusy=false;});
  };
  const framer=new BoundedLines(receive);
  const data=raw=>{try{framer.accept(raw);}catch(error){failed=error;courier.fail(error);process.stdin.pause();}};
  process.stdin.on('data',data);
  process.stdin.on('end',()=>{if(!fs.existsSync(options.publisherResult)){failed=Error('Courier input EOF before final fixture evidence');courier.fail(failed);}});
  const publisherArgs=options.helperLaunch.args.slice();
  publisherArgs[publisherArgs.length-1]='radio_native_v2_local_courier_publisher';
  const publisherChild=cp.spawn(options.python,publisherArgs,{cwd:options.root,env:options.helperLaunch.env,
    stdio:['pipe','pipe','pipe']});
  let publisherStdoutBytes=0,publisherStderr='';
  publisherChild.stdout.on('data',raw=>{publisherStdoutBytes+=raw.length;if(publisherStdoutBytes>65536)publisherChild.kill('SIGKILL');});
  publisherChild.stderr.on('data',raw=>{publisherStderr+=raw.toString('utf8');if(Buffer.byteLength(publisherStderr)>65536)publisherChild.kill('SIGKILL');});
  publisherChild.on('error',error=>{failed=error;courier.fail(error);});
  publisherChild.on('close',code=>{if(code!==0&&!fs.existsSync(options.publisherResult)){
    failed=Error('Pinned Publisher component failed: '+publisherStderr.slice(0,2048));courier.fail(failed);}});
  publisherChild.stdin.on('error',error=>{failed=error;courier.fail(error);});
  const h=require('./radio_native_v2_broker_host');
  publisherChild.stdin.end(h.canonical(options.publisherConfig)+'\n');
  try {
    while(!fs.existsSync(options.publisherResult)){
      if(failed)throw failed;
      await worker.serviceOne(host);
      await new Promise(resolve=>setTimeout(resolve,10));
    }
    const publisherFd=fs.openSync(options.publisherResult,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
    let publisher;
    try{const stat=fs.fstatSync(publisherFd);assert(stat.isFile()&&stat.nlink===1&&stat.size<=MIB,'Bounded sole Publisher evidence required');
      publisher=JSON.parse(fs.readFileSync(publisherFd,'utf8'));}finally{fs.closeSync(publisherFd);}
    const proof=publisher.source_loader_preflight,launch=options.helperLaunch;
    assert(proof&&proof.schema==='radio-native-v2-source-loader-preflight-v1'&&
      proof.entrypoint_sha256===launch.source_loader_sha256&&proof.freeze_sha256===launch.freeze_sha256&&
      proof.helper_bootstrap_sha256===launch.source_policy_sha256&&
      JSON.stringify(proof.modules)==='["radio_native_v2_local_courier_publisher"]'&&
      proof.source_only_imports_verified===true&&proof.environment_isolated===true&&
      publisher.python_pid===publisherChild.pid&&publisher.parent_code_commit===options.publisherConfig.code_commit&&
      ['execution_authorized','reservation_authorized','scientific_execution_authorized'].every(k=>publisher[k]===false),
      'Actual pinned Publisher subprocess proof differs');
    const
      record={...courier.terminalRecord(),publisher,host_state:host.state(),host_usage:host.usage(),
        worker_usage:worker.usage(),worker_state:worker.state(),source_policy:globalThis.__radioNativeV2SourcePolicy,
        node_max_rss_bytes:process.resourceUsage().maxRSS*1024};
    // Terminal supporting acknowledgement stays explicitly unconfirmed. The
    // full result is retained locally without claiming an all-known Runner gate.
    const resultFd=fs.openSync(options.resultPath,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o400);
    try{fs.writeFileSync(resultFd,JSON.stringify(record)+'\n');fs.fsyncSync(resultFd);}finally{fs.closeSync(resultFd);}
    const resultDirectory=fs.openSync(options.resultPath.slice(0,options.resultPath.lastIndexOf('/')),
      fs.constants.O_RDONLY|fs.constants.O_DIRECTORY);try{fs.fsyncSync(resultDirectory);}finally{fs.closeSync(resultDirectory);}
    emit({schema:SCHEMA,kind:'terminal',result_path:options.resultPath,result_sha256:hash(fs.readFileSync(options.resultPath)),
      status:record.status,last_delivery_acknowledgement_durable:false});
  }catch(error){courier.fail(error);
    let storeStop=null;try{if(!worker.state().stopped)storeStop=await worker.action({action:'stop',reason:String(error).slice(0,256)});}catch(failure){storeStop={durable:false,error:String(failure)};}
    emit({schema:SCHEMA,kind:'failed',error:String(error),store_stop:storeStop,
    host_state:host.state(),host_usage:host.usage(),worker_state:worker.state(),execution_authorized:false});throw error;}
  finally{process.stdin.off('data',data);process.stdin.pause();if(publisherChild.exitCode===null)publisherChild.kill('SIGKILL');}
}

module.exports={SCHEMA,CONTROL_REPLY_BYTES,BoundedLines,deliveryRequest,ToolCourier,runGit,main};
