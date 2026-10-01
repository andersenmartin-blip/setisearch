const test=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto'),
  fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {SharedLedger}=require('../scripts/radio_native_v2_local_transport'),
  {SCHEMA,ToolCourier,deliveryRequest,BoundedLines,initializeControlStore,NETWORK_SCHEMA,PROXY_POLICY,CA_PATH,
    GIT_NETWORK_BASE,validateRuntimeProxy,loadGitNetworkConfig,runGit}=require('../scripts/radio_native_v2_local_courier');
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

test('control startup awaits exclusive durable Store creation before any polling',async t=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'seti-courier-startup-')),root=path.join(directory,'store');
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const calls=[];let release;
  const worker={action:async command=>{calls.push(command);await new Promise(resolve=>{release=resolve;});
    return{schema:'radio-native-v2-filesystem-bridge-v1',created:true,execution_authorized:false};}};
  let ready=false;const startup=initializeControlStore(worker,root).then(()=>{ready=true;});
  await new Promise(resolve=>setImmediate(resolve));assert.equal(ready,false);
  assert.deepEqual(calls,[{action:'create'}]);release();await startup;assert.equal(ready,true);
});

test('real local control Store is ready for pending polling and rejects scope reuse',async t=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'seti-courier-store-')),root=path.join(directory,'store');
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const {createLocalWorker}=require('../scripts/radio_native_v2_local_worker'),repo=path.resolve(__dirname,'..'),
    python=process.env.CODEX_PRIMARY_RUNTIME_PYTHON||'/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python';
  const worker=createLocalWorker({root,python,sourceRoot:path.join(repo,'src')});
  const initialized=await initializeControlStore(worker,root);
  assert.equal(initialized.execution_authorized,false);assert.equal(initialized.reservation_authorized,false);
  const pending=await worker.action({action:'pending'});assert.equal(pending.pending_count,0);assert.equal(pending.stopped,false);
  const calls=worker.usage().helper_calls;
  await assert.rejects(initializeControlStore(worker,root),/no retry or reuse/);
  assert.equal(worker.usage().helper_calls,calls,'Existing Store rejected before another helper dispatch');
  assert.equal(fs.existsSync(path.join(root,'STOPPED.json')),false,'The existing evidence Store remains unchanged');
});

function networkFixture(t) {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'seti-courier-network-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));fs.mkdirSync(root+'/config');
  const certificate='fixed harmless certificate fixture\n',caPath=root+'/'+CA_PATH,
    configPath=root+'/config/radio_native_v2_local_git_network_20260930.json';
  fs.writeFileSync(caPath,certificate);
  const config={schema:NETWORK_SCHEMA,repository:'andersenmartin-blip/setisearch',operation:'git_fetch',
    proxy_policy:{...PROXY_POLICY},tls_ca:{path:CA_PATH,bytes:Buffer.byteLength(certificate),sha256:hash(certificate)},
    automatic_retry:false,execution_authorized:false,reservation_authorized:false,scientific_execution_authorized:false},
    canonical=require('../scripts/radio_native_v2_broker_host').canonical,
    baseline=Object.freeze({PATH:'/usr/bin:/bin',LANG:'C',LC_ALL:'C',GIT_CONFIG_NOSYSTEM:'1',
      GIT_CONFIG_SYSTEM:'/dev/null',GIT_CONFIG_GLOBAL:'/dev/null',GIT_NO_REPLACE_OBJECTS:'1',
      GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0',GIT_OPTIONAL_LOCKS:'0'});
  const write=()=>{const raw=canonical(config);fs.writeFileSync(configPath,raw);return hash(raw);};
  let configSha=write();
  const load=()=>loadGitNetworkConfig(root,configPath,configSha,'http://127.0.0.1:12345',baseline);
  return {root,certificate,caPath,configPath,config,baseline,load,
    refresh:()=>{configSha=write();},localGit:{env:baseline,snapshot:()=>({git_metadata_inputs:[]})}};
}
function mockGitSpawn(inspect,emit=()=>{}) {
  return(executable,args,options)=>{
    const {EventEmitter}=require('node:events'),{PassThrough}=require('node:stream'),child=new EventEmitter();
    child.stdout=new PassThrough();child.stderr=new PassThrough();child.stdin=new PassThrough();child.kill=()=>{};
    inspect(executable,args,options);setImmediate(()=>{emit(child);child.emit('close',0,null);});return child;
  };
}
function networkFetchPlan(f,network) {
  return{executable:'/usr/bin/git',args:[...GIT_NETWORK_BASE,'fetch','--filter=blob:none','--depth=1','--no-tags',
    '--no-write-fetch-head','--','https://github.com/andersenmartin-blip/setisearch.git','a'.repeat(40),'b'.repeat(40)],
    cwd:f.root,maximum_output_bytes:65536,environment:{...network.environment}};
}
test('network policy rejects credentials, alternate routes and authority or environment expansion',t=>{
  const f=networkFixture(t),pin=f.load();assert.equal(pin.environment.HTTPS_PROXY,'http://127.0.0.1:12345');
  assert.equal(pin.environment.GIT_SSL_CAINFO,f.caPath);assert.equal(pin.execution_authorized,false);
  assert.equal(f.baseline.HTTPS_PROXY,undefined);
  for(const proxy of['http://user:secret@127.0.0.1:123','http://localhost:123','http://10.0.0.1:123',
    'https://127.0.0.1:123','socks5h://127.0.0.1:123','http://127.0.0.1:0','http://127.0.0.1:65536',
    'http://127.0.0.1:0123','http://127.0.0.1:123/','http://127.0.0.1:123?route=x','http://127.0.0.1:123#x'])
    assert.throws(()=>validateRuntimeProxy(proxy),/exact loopback/);
  f.config.proxy_policy.extra='ALL_PROXY';f.refresh();assert.throws(f.load,/non-authorizing/);delete f.config.proxy_policy.extra;
  f.config.execution_authorized=true;f.refresh();assert.throws(f.load,/non-authorizing/);f.config.execution_authorized=false;
  f.refresh();assert.throws(()=>loadGitNetworkConfig(f.root,f.configPath,hash(fs.readFileSync(f.configPath)),
    'http://127.0.0.1:12345',{...f.baseline,GIT_SSL_NO_VERIFY:'1'}),/metadata environment/);
});
test('network inputs reject hash drift, symlinks and hardlinks before process dispatch',t=>{
  const f=networkFixture(t);fs.appendFileSync(f.caPath,'changed');assert.throws(f.load,/pinned input|drifted/);
  fs.writeFileSync(f.caPath,f.certificate);fs.linkSync(f.caPath,f.caPath+'.second');assert.throws(f.load,/sole pinned/);
  fs.unlinkSync(f.caPath+'.second');fs.renameSync(f.caPath,f.caPath+'.original');fs.symlinkSync(f.caPath+'.original',f.caPath);
  assert.throws(f.load);fs.unlinkSync(f.caPath);fs.renameSync(f.caPath+'.original',f.caPath);
  fs.appendFileSync(f.configPath,'\n');assert.throws(f.load,/drifted/);
});
test('Git fetch receives exact receipted network environment while cat-file stays isolated',async t=>{
  const f=networkFixture(t),network=f.load(),fetch=networkFetchPlan(f,network),spawns=[];
  const spawn=mockGitSpawn((_,args,options)=>spawns.push({args,environment:{...options.env}}));
  assert.equal((await runGit('git_fetch',fetch,1000,f.localGit,network,spawn)).exit_code,0);
  const batch={executable:'/usr/bin/git',args:['cat-file','--batch'],cwd:f.root,maximum_output_bytes:65536};
  assert.equal((await runGit('git_cat_file_batch',batch,1000,f.localGit,network,spawn)).exit_code,0);
  assert.deepEqual(spawns[0].environment,network.environment);assert.deepEqual(spawns[1].environment,f.baseline);
  assert.equal(spawns[1].environment.HTTPS_PROXY,undefined);assert.equal(spawns[1].environment.GIT_SSL_CAINFO,undefined);
  assert.throws(()=>runGit('git_fetch',{...fetch,environment:{...fetch.environment,HTTP_PROXY:'http://127.0.0.1:12345'}},
    1000,f.localGit,network,spawn),/receipted/);
  assert.throws(()=>runGit('git_cat_file_batch',{...batch,environment:network.environment},1000,f.localGit,network,spawn),/restricted/);
  assert.equal(spawns.length,2,'Rejected environment plans cannot spawn');
  assert.throws(()=>runGit('git_fetch',{...fetch,args:fetch.args.filter(arg=>arg!=='--filter=blob:none')},
    1000,f.localGit,network,spawn),/filtered archive/);
  const capability={...fetch,args:[...GIT_NETWORK_BASE,'ls-remote','--refs','--',
    'https://github.com/andersenmartin-blip/setisearch.git'],environment:{...network.environment,GIT_TRACE_PACKET:'1'}};
  assert.equal((await runGit('git_protocol_capability',capability,1000,f.localGit,network,spawn)).exit_code,0);
  assert.deepEqual(spawns[2].environment,capability.environment);
  assert.throws(()=>runGit('git_fetch',{...fetch,environment:capability.environment},1000,f.localGit,network,spawn),/receipted/);
});
test('certificate drift during Git fetch produces a failed local process result',async t=>{
  const f=networkFixture(t),network=f.load(),plan=networkFetchPlan(f,network),
    spawn=mockGitSpawn(()=>fs.writeFileSync(f.caPath,'changed certificate\n'));
  const result=await runGit('git_fetch',plan,1000,f.localGit,network,spawn);
  assert.equal(result.exit_code,1);assert.match(result.io_error,/pinned input|drifted/);
});

test('Git stdout overflow fails despite a successful child exit and counts all observed chunks',async t=>{
  const f=networkFixture(t),network=f.load(),plan={...networkFetchPlan(f,network),maximum_output_bytes:4};
  let kills=0;
  const spawn=mockGitSpawn(()=>{},child=>{
    child.kill=()=>{kills++;return false;};
    child.stdout.write('abcd');child.stdout.write('e');child.stdout.write('fg');child.stderr.write('ok');
  });
  const result=await runGit('git_fetch',plan,1000,f.localGit,network,spawn);
  assert.equal(result.process_exit_code,0);assert.equal(result.exit_code,1);assert.equal(kills,2);
  assert.equal(result.stdout_observed_bytes,7);assert.equal(result.stdout_retained_bytes,4);
  assert.equal(result.stderr_observed_bytes,2);assert.equal(result.stderr_retained_bytes,2);
  assert.equal(result.stdout_limit_bytes,4);assert.equal(result.stderr_limit_bytes,4);
  assert.equal(result.output,'abcd');assert.equal(result.stderr,'ok');
  assert.equal(result.stdout_truncated,true);assert.equal(result.stderr_truncated,false);
  assert.equal(result.output_limit_exceeded,true);assert.match(result.io_error,/stdout.*bounded output/);
});

test('Git capability stderr overflow cannot qualify a retained valid capability prefix',async t=>{
  const f=networkFixture(t),network=f.load(),prefix='packet: git< version 2\npacket: git< fetch=shallow filter\n',
    plan={...networkFetchPlan(f,network),maximum_output_bytes:Buffer.byteLength(prefix),
      args:[...GIT_NETWORK_BASE,'ls-remote','--refs','--','https://github.com/andersenmartin-blip/setisearch.git'],
      environment:{...network.environment,GIT_TRACE_PACKET:'1'}};
  const spawn=mockGitSpawn(()=>{},child=>{
    child.kill=()=>false;child.stderr.write(prefix);child.stderr.write('x');child.stderr.write('yz');
  });
  const result=await runGit('git_protocol_capability',plan,1000,f.localGit,network,spawn);
  assert.equal(result.process_exit_code,0);assert.equal(result.exit_code,1);assert.equal(result.stderr,prefix);
  assert.equal(result.stderr_observed_bytes,Buffer.byteLength(prefix)+3);
  assert.equal(result.stderr_retained_bytes,Buffer.byteLength(prefix));
  assert.equal(result.stdout_observed_bytes,0);assert.equal(result.stdout_truncated,false);
  assert.equal(result.stderr_truncated,true);assert.equal(result.output_limit_exceeded,true);
  assert.match(result.io_error,/stderr.*bounded output/);
  assert.throws(()=>require('../scripts/radio_native_v2_local_transport').filterCapabilityProof(result),/Complete bounded/);
});

test('Git spool overflow reports written bytes separately from all observed bytes',async t=>{
  const f=networkFixture(t),network=f.load(),maximum=40*1024*1024,
    plan={executable:'/usr/bin/git',args:['cat-file','--batch'],cwd:f.root,maximum_output_bytes:65536,
      stdout_path:f.root+'/bounded.git-batch'},
    spawn=mockGitSpawn(()=>{},child=>{
      child.kill=()=>false;child.stdout.write('abc');child.stdout.write(Buffer.alloc(maximum-1,120));
    });
  const result=await runGit('git_cat_file_batch',plan,1000,f.localGit,network,spawn);
  assert.equal(result.process_exit_code,0);assert.equal(result.exit_code,1);
  assert.equal(result.stdout_observed_bytes,maximum+2);assert.equal(result.stdout_retained_bytes,3);
  assert.equal(result.stdout_file_bytes,3);assert.equal(fs.statSync(plan.stdout_path).size,3);
  assert.equal(fs.readFileSync(plan.stdout_path,'utf8'),'abc');
  assert.equal(result.stdout_limit_bytes,maximum);assert.equal(result.stdout_truncated,true);
  assert.equal(result.output_limit_exceeded,true);
});
