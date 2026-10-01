// Deterministic component tests only. No connector, Git, RNG or science runs.
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const vm = require('node:vm');
const h = require('../scripts/radio_native_v2_broker_host');
const MIB = 1024 * 1024;
const digest = s => crypto.createHash('sha256').update(s).digest('hex');
const blob = s => crypto.createHash('sha1').update('blob '+Buffer.byteLength(s)+'\0').update(s).digest('hex');

function fixture(overrides = {}) {
  const parent = 'a'.repeat(40), parentTree = 'b'.repeat(40), tree = 'c'.repeat(40), candidate = 'd'.repeat(40);
  const prefix = h.PREFIX+'/case00-'+ '1'.repeat(16);
  const manifest = '{"engineering_only":true}', contents = {
    [prefix+'/HEAD']:digest(manifest)+'\n', [prefix+'/manifest.json']:manifest
  };
  const files = Object.fromEntries(Object.entries(contents).map(([path,content]) => [path,
    {bytes:Buffer.byteLength(content),sha256:digest(content),blob:blob(content)}]));
  const freeze = {schema:'radio-native-v2-inline-terminal-archive-v1',mode:'ENGINEERING_ONLY',
    repository:h.REPOSITORY,branch:h.BRANCH,broker_protocol:h.BROKER_PROTOCOL,
    ordinal:0,prefix,parent,parent_tree:parentTree,files,manifest_sha256:digest(manifest),
    limits:{calls:64,request_bytes:48*MIB,response_bytes:64*MIB,stored_bytes:36*MIB,
      files:28,seconds:600,peak_rss_bytes:512*MIB},
    per_operation_response_reservations:{fetch:4*MIB,create_tree:MIB,create_commit:65536,update_ref:16384,fetch_files:48*MIB},
    single_inline_tree_request:true,single_grouped_readback:true,force:false,automatic_retry:false,
    execution_restart_authorized:false,scientific_admission_authorized:false};
  const calls = [], saved = [], order = [], timers = [];
  let head = parent, tick = 0;
  const api = 'https://api.github.com/repos/'+h.REPOSITORY+'/git/';
  const envelope = value => ({content:[{type:'text',text:'visible raw framing 🎯'}],
    structuredContent:value,_meta:{complete:true},isError:false});
  const tools = {
    mcp__codex_apps__github_fetch: async args => {
      calls.push(['fetch',args]);order.push('tool:fetch');
      if (overrides.fetch) return overrides.fetch(args);
      let value;
      if (args.url === api+'ref/heads/'+encodeURIComponent(h.BRANCH)) value = {ref:'refs/heads/'+h.BRANCH,object:{type:'commit',sha:head}};
      else if (args.url === api+'commits/'+parent) value = {sha:parent,tree:{sha:parentTree},parents:[]};
      else if (args.url === api+'commits/'+candidate) value = {sha:candidate,tree:{sha:tree},parents:[{sha:parent}]};
      else if (args.url.startsWith(api+'trees/')) value = {sha:args.url.slice(-40),truncated:false,tree:overrides.treeRows || []};
      else throw Error('Unexpected fixture read');
      return envelope({content:JSON.stringify(value)});
    },
    mcp__codex_apps__github_create_tree: async args => {calls.push(['create_tree',args]);return envelope({sha:tree});},
    mcp__codex_apps__github_create_commit: async args => {calls.push(['create_commit',args]);return envelope({sha:candidate});},
    mcp__codex_apps__github_update_ref: async args => {
      calls.push(['update_ref',args]);head=candidate;
      if (overrides.lostUpdate) throw Error('lost acknowledgement');
      return envelope({success:true});
    },
    exec_command:async args => {calls.push(['exec_command',args]);return {exit_code:0,output:'bounded Git metadata\n',wall_time_seconds:0};}
  };
  const persistRaw = async record => {
    order.push('persist:'+record.operation);saved.push({...record});
    const receipt = {request_bytes:Buffer.byteLength(record.request_json),request_sha256:digest(record.request_json),
      response_bytes:Buffer.byteLength(record.response_json),response_sha256:digest(record.response_json),
      stored_bytes:Buffer.byteLength(record.storage_json),stored_sha256:digest(record.storage_json)};
    if (overrides.persist) return overrides.persist(record,receipt);
    return receipt;
  };
  const groupedGitReadback = async job => {
    if (overrides.grouped) return overrides.grouped(job);
    await job.callGit('git_fetch');await job.callGit('git_cat_file_batch');
    const result = Object.fromEntries(job.paths.map(path => [path,{sha:files[path].blob,content:Buffer.from(contents[path]).toString('base64')}]));
    const batch = job.paths.map(path => files[path].blob+' blob '+files[path].bytes+'\n'+contents[path]+'\n').join('');
    return {commit:job.commit,single_cat_file_batch:true,result,
      raw_git_receipt:{path:job.spool_path,bytes:Buffer.byteLength(batch)+(overrides.spoolExcess || 0),sha256:digest(batch),durable:true}};
  };
  const host = h.createBrokerHost({tools,persistRaw,groupedGitReadback,repoPath:'/fixture/repo',spoolRoot:'/fixture/spool',
    clock:()=>tick,setTimer:(callback,ms)=> {const timer={callback,ms,active:true};timers.push(timer);return timer;},
    clearTimer:timer=>{timer.active=false;},...overrides.options});
  const freezeJson = h.canonical(freeze), bundleSha = digest(freezeJson);
  const begin = () => host.beginCase(freezeJson,bundleSha);
  const get = suffix => host.invoke('fetch',{url:api+suffix});
  const toUpdate = async () => {
    await get('ref/heads/'+encodeURIComponent(h.BRANCH));await get('commits/'+parent);await get('trees/'+parentTree);
    await host.invoke('create_tree',{repository_full_name:h.REPOSITORY,base_tree_sha:parentTree,
      tree_elements:Object.entries(contents).map(([path,content])=>({path,mode:'100644',type:'blob',content}))});
    await get('trees/'+tree);
    await host.invoke('create_commit',{repository_full_name:h.REPOSITORY,parent_sha:parent,tree_sha:tree,message:'Engineering fixture'});
    await get('commits/'+candidate);await get('ref/heads/'+encodeURIComponent(h.BRANCH));
    return host.invoke('update_ref',{repository_full_name:h.REPOSITORY,branch_name:h.BRANCH,sha:candidate,force:false});
  };
  const readback = () => host.invoke('fetch_files',{repository_full_name:h.REPOSITORY,ref:candidate,
    paths:Object.keys(files).sort(),encoding:'base64'});
  return {host,calls,saved,order,timers,freeze,freezeJson,bundleSha,begin,get,toUpdate,readback,files,contents,
    parent,parentTree,tree,candidate,setTick:value=>{tick=value;}};
}

test('UTF-8 count and fixed-block SHA256 match native UTF-8 including surrogates', () => {
  for (const s of ['', 'abc','æøå λ 🎯','\ud800','\udc00',JSON.stringify({x:'🎯\nλ'}),
    ...[55,56,63,64,65,127,128,129,10000].map(n=>'x'.repeat(n))]) {
    assert.equal(h.utf8Bytes(s),Buffer.byteLength(s));assert.equal(h.sha256(s),digest(s));
  }
});

test('host hash works in ECMAScript without Node, Buffer or TextEncoder', () => {
  const context = vm.createContext({});vm.runInContext(fs.readFileSync('scripts/radio_native_v2_broker_host.js','utf8'),context);
  assert.equal(vm.runInContext("sha256('æ🎯\\ud800')",context),digest('æ🎯\ud800'));
  assert.equal(vm.runInContext("sha256Chunks(['','a','bc',''])",context),digest('abc'));
});

test('incremental ASCII SHA256 crosses awkward chunk and padding boundaries without joining', () => {
  const source=Array.from({length:513},(_,i)=>String.fromCharCode(i%128)).join('');
  for(const size of [1,2,7,31,55,56,63,64,65,127,128,129]){
    const chunks=[''];for(let offset=0;offset<source.length;offset+=size)chunks.push(source.slice(offset,offset+size),'');
    chunks.join=()=>{throw Error('Incremental hash must not join chunks');};
    assert.equal(h.sha256Chunks(chunks),digest(source),'Chunk boundary '+size);
  }
  assert.equal(h.sha256Chunks([]),digest(''));
  assert.equal(h.sha256Chunks(['','','']),digest(''));
});

test('incremental header and one MiB deterministic ASCII source match native streaming SHA256', () => {
  const source=Buffer.alloc(MIB);for(let i=0;i<source.length;i++)source[i]=(i*17+33)&127;
  const text=source.toString('ascii'),header='{"tool":"fixture","arguments":',suffix='}',pieces=[header];
  for(let offset=0;offset<text.length;offset+=65521)pieces.push(text.slice(offset,offset+65521));
  pieces.push(suffix);
  const expected=crypto.createHash('sha256');for(const piece of pieces)expected.update(piece,'ascii');
  assert.equal(h.sha256Chunks(pieces),expected.digest('hex'));
  assert.equal(h.sha256(text),digest(text),'Original one-string path remains unchanged');
});

test('incremental SHA256 refuses Unicode and non-string or non-array chunks', () => {
  for(const bad of [null,'abc',{},new Uint8Array([65]),[1],[null],[undefined],['ascii','æ'],
    ['🎯'],['\ud800'],['\udc00'],['\u0080']])assert.throws(()=>h.sha256Chunks(bad),/ASCII string chunks/);
  assert.equal(h.sha256Chunks(['\x00\x01\x7f']),digest('\x00\x01\x7f'));
});

test('exact component publication charges all visible Git and connector envelopes', async () => {
  const f=fixture();f.begin();await f.toUpdate();await f.readback();await f.get('ref/heads/'+encodeURIComponent(h.BRANCH));
  const receipt=f.host.finishCase(),usage=f.host.usage();
  assert.equal(receipt.bundle_sha256,f.bundleSha);assert.equal(receipt.commit,f.candidate);
  assert.equal(usage.calls,12);assert.equal(f.saved.length,12);assert.equal(usage.cases,1);
  assert.equal(usage.response_bytes,f.saved.reduce((sum,row)=>sum+Buffer.byteLength(row.response_json),0));
  assert.equal(usage.receipt_bytes,f.saved.reduce((sum,row)=>sum+Buffer.byteLength(row.storage_json),0));
  assert.equal(usage.git_spool_bytes,h.gitBatchBytes(f.files));
  assert.equal(usage.receipt_charged_bytes,usage.receipt_bytes);assert.equal(usage.git_spool_charged_bytes,usage.git_spool_bytes);
  for (const key of ['unknown_response_bytes','unknown_response_count','unknown_receipt_bytes','unknown_git_spool_bytes']) assert.equal(usage[key],0);
  assert.equal(f.calls.filter(([name])=>name==='update_ref').length,1);
  assert.equal(f.calls.filter(([name])=>name==='exec_command').length,2);
  const manifests=f.host.capabilityManifest();assert.equal(manifests.status,'COMPONENT_ONLY_NOT_EXECUTABLE');
  assert.equal(manifests.scientific_admission_authorized,false);assert.equal(manifests.full_size_integrated_storage_and_memory_qualified,false);
  assert.ok(manifests.unqualified_external_boundaries.length);
});

test('complete untouched raw envelope is durable before malformed payload parsing fails', async () => {
  const raw={structuredContent:{content:'invalid JSON'},content:[{type:'text',text:'extra framing'}],_meta:{extra:77}};
  const f=fixture({fetch:async()=>raw});f.begin();await assert.rejects(f.get('ref/heads/'+encodeURIComponent(h.BRANCH)));
  assert.deepEqual(JSON.parse(f.saved[0].response_json),raw);assert.equal(f.host.state().records[0].raw_receipt_durable,true);
  assert.deepEqual(f.order,['tool:fetch','persist:fetch']);await assert.rejects(f.get('commits/'+f.parent),/no retry/);
  assert.equal(f.calls.length,1);
});

test('wrong durable receipt stops before caller sees parsed result', async () => {
  const f=fixture({persist:(record,receipt)=>({...receipt,stored_sha256:'0'.repeat(64)})});f.begin();
  await assert.rejects(f.get('commits/'+f.parent),/receipt differs/);assert.equal(f.host.usage().unknown_response_count,0);
  assert.ok(f.host.usage().unknown_receipt_bytes>0);assert.equal(f.host.state().records[0].raw_receipt_durable,undefined);
  await assert.rejects(f.get('commits/'+f.parent),/no retry/);assert.equal(f.calls.length,1);
});

test('independent bundle pin, canonical bytes and fixed ordinal are required before any tool', () => {
  for (const failure of ['hash','canonical','ordinal','manifest','authority']) {
    const f=fixture();let text=f.freezeJson,pin=f.bundleSha;
    if (failure==='hash') pin='0'.repeat(64);
    else if (failure==='canonical') {text=JSON.stringify(f.freeze);pin=digest(text);}
    else {const freeze=JSON.parse(text);if(failure==='ordinal')freeze.ordinal=1;
      else if(failure==='manifest')freeze.manifest_sha256='0'.repeat(64);
      else freeze.scientific_admission_authorized=true;text=h.canonical(freeze);pin=digest(text);}
    assert.throws(()=>f.host.beginCase(text,pin));assert.equal(f.calls.length,0);assert.equal(f.host.state().stopped,true);
  }
});

test('caller changes after begin do not alter pinned immutable inventory', async () => {
  const f=fixture();f.begin();f.freeze.files={};await f.get('commits/'+f.parent);
  assert.equal(f.host.state().stopped,false);
});

test('lower receipt storage cap refuses allocation before dispatch', async () => {
  const f=fixture({options:{localLimits:{...h.LOCAL_LIMITS,case_receipt_bytes:1}}});f.begin();
  await assert.rejects(f.get('commits/'+f.parent),/reserve/);assert.equal(f.calls.length,0);assert.equal(f.host.usage().calls,0);
});

test('lower visible reply cap refuses whole envelope reservation before dispatch', async () => {
  const f=fixture({options:{limits:{...h.HOST_LIMITS,case_response_bytes:1}}});f.begin();
  await assert.rejects(f.get('commits/'+f.parent),/reserve/);assert.equal(f.calls.length,0);
});

test('known oversized visible envelope is persisted and charged before stopping', async () => {
  const raw={structuredContent:{content:'{}'},content:[{type:'text',text:'x'.repeat(2000)}]};
  const f=fixture({fetch:async()=>raw,options:{responseReservations:{...h.TOOL_RESERVATIONS,fetch:1024}}});f.begin();
  await assert.rejects(f.get('commits/'+f.parent),/exceeded reservation/);
  assert.equal(f.host.usage().response_charged_bytes,Buffer.byteLength(JSON.stringify(raw)));
  assert.equal(f.saved.length,1);assert.equal(f.host.usage().unknown_response_count,0);
});

test('case time exhaustion prevents any new dispatch', async () => {
  const f=fixture();f.begin();f.setTick(600001);
  await assert.rejects(f.get('commits/'+f.parent),/deadline exhausted/);assert.equal(f.calls.length,0);
});

test('deadline is installed before dispatch and late full envelope is still durable', async () => {
  let release;const pending=new Promise(resolve=>{release=resolve;});
  const f=fixture({fetch:()=>pending});f.begin();
  const operation=f.get('commits/'+f.parent);await Promise.resolve();await Promise.resolve();
  assert.equal(f.calls.length,1);assert.equal(f.timers[0].active,true);f.timers[0].callback();
  await assert.rejects(operation,/deadline exceeded/);assert.equal(f.host.usage().unknown_response_count,1);
  const raw={structuredContent:{content:JSON.stringify({sha:f.parent,tree:{sha:f.parentTree}})},content:[{type:'text',text:'late extra'}]};
  release(raw);await new Promise(resolve=>setImmediate(resolve));
  assert.equal(f.saved.length,1);assert.deepEqual(JSON.parse(f.saved[0].response_json),raw);
  assert.equal(f.host.usage().unknown_response_count,0);assert.equal(f.host.state().stopped,true);
  await assert.rejects(f.get('commits/'+f.parent),/no retry/);assert.equal(f.calls.length,1);
});

test('lost update retains unknown reply and receipt reservations with no retry', async () => {
  const f=fixture({lostUpdate:true});f.begin();await assert.rejects(f.toUpdate(),/lost acknowledgement/);
  const usage=f.host.usage();assert.equal(usage.unknown_response_count,1);assert.equal(usage.unknown_response_bytes,h.TOOL_RESERVATIONS.update_ref);
  assert.ok(usage.unknown_receipt_bytes>0);assert.equal(f.host.state().update_may_have_landed,true);
  await assert.rejects(f.toUpdate(),/no retry/);assert.equal(f.calls.filter(([name])=>name==='update_ref').length,1);
});

test('raw Git spool is independently reserved before entering external bridge', async () => {
  let entered=false;const f=fixture({grouped:()=>{entered=true;},options:{localLimits:{...h.LOCAL_LIMITS,case_git_spool_bytes:1}}});
  f.begin();await f.toUpdate();await assert.rejects(f.readback(),/reserve complete raw Git batch/);
  assert.equal(entered,false);assert.equal(f.calls.filter(([name])=>name==='exec_command').length,0);
});

test('arbitrary shell command containing candidate SHA cannot cross Git boundary', async () => {
  const f=fixture({grouped:job=>job.callGit('git_fetch',{...job.git_plan.git_fetch,cmd:'touch /tmp/unapproved '+job.commit})});
  f.begin();await f.toUpdate();await assert.rejects(f.readback(),/host-generated/);
  assert.equal(f.calls.filter(([name])=>name==='exec_command').length,0);assert.ok(f.host.usage().unknown_git_spool_bytes>0);
});

test('spool byte mismatch fails after retaining actual durable spool charge', async () => {
  const f=fixture({spoolExcess:1});f.begin();await f.toUpdate();await assert.rejects(f.readback(),/byte length differs/);
  assert.equal(f.host.usage().git_spool_bytes,h.gitBatchBytes(f.files)+1);assert.equal(f.host.usage().unknown_git_spool_bytes,0);
});

test('only observed immutable tree descendants are accepted', async () => {
  const child='e'.repeat(40),f=fixture({treeRows:[{path:'dir',mode:'040000',type:'tree',sha:child}]});f.begin();
  await f.get('trees/'+f.parentTree);await f.get('trees/'+child);
  const before=f.calls.length;await assert.rejects(f.get('trees/'+'f'.repeat(40)),/observed immutable descendants/);assert.equal(f.calls.length,before);
});

test('finish refuses incomplete readback and closes host permanently', async () => {
  const f=fixture();f.begin();await f.toUpdate();assert.throws(()=>f.host.finishCase(),/incomplete/);
  await assert.rejects(f.readback(),/no retry/);
});
