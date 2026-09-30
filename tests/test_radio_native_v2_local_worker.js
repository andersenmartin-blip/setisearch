// Real local Node/Python IPC; no connector, RNG, native case or telescope data.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),
  os=require('node:os'),cp=require('node:child_process'),crypto=require('node:crypto');
const h=require('../scripts/radio_native_v2_broker_host'),local=require('../scripts/radio_native_v2_local_worker');
const repo=path.resolve(__dirname,'..'),python=process.env.CODEX_PRIMARY_RUNTIME_PYTHON||'/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python';
const hash=value=>crypto.createHash('sha256').update(value).digest('hex');
function fixture(t,options={}) {
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'seti-local-worker-')),root=path.join(directory,'store');
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  return{directory,root,adapter:local.createLocalWorker({root,python,sourceRoot:path.join(repo,'src'),hostLibrary:h,...options})};
}
function runPython(t,f,program) {
  const child=cp.spawn(python,['-B','-c',program,f.root],{env:{...process.env,PYTHONPATH:path.join(repo,'src')},stdio:['ignore','pipe','pipe']});
  let stdout='',stderr='',done=false,code;
  child.stdout.on('data',raw=>stdout+=raw);child.stderr.on('data',raw=>stderr+=raw);
  const completion=new Promise(resolve=>child.on('close',value=>{done=true;code=value;resolve();}));
  t.after(()=>{if(!done)child.kill('SIGKILL');});
  return{child,completion,get done(){return done;},result:()=>{assert.equal(code,0,stderr);return JSON.parse(stdout);}};
}
async function serviceUntilDone(f,worker,host) {
  const end=Date.now()+15000;let count=0;
  while(!worker.done&&Date.now()<end) {
    const receipt=await f.adapter.serviceOne(host);if(receipt.serviced)count++;
    await new Promise(resolve=>setTimeout(resolve,5));
  }
  assert.equal(worker.done,true,'Bounded real Worker completion');await worker.completion;return count;
}

test('one local subprocess streams a multimegabyte raw receipt with no tool calls',async t=>{
  const f=fixture(t);await f.adapter.action({action:'create'});
  const request=JSON.stringify({fixture:'x'.repeat(4*1024*1024),unicode:'λ 🎯'}),response=JSON.stringify({content:[{text:'untouched framing'}]});
  const storage=JSON.stringify({request_json:request,response_json:response});
  const receipt=await f.adapter.persistRaw({request_json:request,response_json:response,storage_json:storage});
  assert.equal(receipt.stored_sha256,hash(storage));
  const item={id:'host_receipt-00000000',bytes:receipt.stored_bytes,sha256:receipt.stored_sha256};
  assert.equal(f.adapter.read(item).toString('utf8'),storage);
  const usage=f.adapter.usage();assert.equal(usage.helper_calls,2);assert.equal(usage.functions_tool_calls,0);
  assert.ok(usage.helper_max_rss_kib>0);assert.ok(usage.helper_stdin_bytes>4*1024*1024);
  assert.equal(f.adapter.capabilityManifest().execution_authorized,false);
});

test('a supporting receipt batch uses one helper and retains every original envelope',async t=>{
  const f=fixture(t);await f.adapter.action({action:'create'});
  const records=Array.from({length:7},(_,index)=>{
    const request_json=JSON.stringify({fixture:index}),response_json=JSON.stringify({output:'x'.repeat(131072),index});
    return{request_json,response_json,storage_json:JSON.stringify({request_json,response_json})};
  });
  const receipts=await f.adapter.persistRawBatch(records);assert.equal(receipts.length,records.length);
  assert.equal(f.adapter.usage().helper_calls,2);assert.equal(f.adapter.usage().functions_tool_calls,0);
  for(let index=0;index<records.length;index++) {
    const receipt=receipts[index],stored=f.adapter.read({id:'host_receipt-'+String(index).padStart(8,'0'),
      bytes:receipt.stored_bytes,sha256:receipt.stored_sha256});
    assert.equal(stored.toString('utf8'),records[index].storage_json);
  }
  const state=await f.adapter.action({action:'status'});assert.equal(state.buckets.host_receipt.items,7);
  assert.equal(state.buckets.host_receipt.unknown_bytes,0);
});

test('lazy supporting receipts generate one pinned frame at a time in one helper',async t=>{
  const f=fixture(t);await f.adapter.action({action:'create'});
  const records=Array.from({length:9},(_,index)=>{
    const request_json=JSON.stringify({fixture:index}),response_json=JSON.stringify({output:'x'.repeat(131072),index});
    return{request_json,response_json,storage_json:JSON.stringify({request_json,response_json})};
  });
  const pins=records.map(record=>({request_bytes:Buffer.byteLength(record.request_json),request_sha256:hash(record.request_json),
    response_bytes:Buffer.byteLength(record.response_json),response_sha256:hash(record.response_json),
    stored_bytes:Buffer.byteLength(record.storage_json),stored_sha256:hash(record.storage_json)}));
  const produced=[];
  assert.deepEqual(await f.adapter.persistRawBatchLazy({frames:pins,produce:async index=>{
    produced.push(index);return records[index].storage_json;
  }}),pins);
  assert.deepEqual(produced,records.map((_,index)=>index));assert.equal(f.adapter.usage().helper_calls,2);
  assert.equal(f.adapter.state().records.at(-1).lazy_frames_written,9);
  const state=await f.adapter.action({action:'status'});assert.equal(state.buckets.host_receipt.items,9);
  assert.equal(state.buckets.host_receipt.unknown_bytes,0);
});

test('file-backed request-view raw receipt matches exact nested JSON escaping',async t=>{
  const f=fixture(t);await f.adapter.action({action:'create'});
  const transport=require('../scripts/radio_native_v2_local_transport');
  const args={repository_full_name:'offline/fixture',text:'quoted " and \\ plus \n\t'.repeat(32768)},
    packet={schema:'radio-native-v2-filesystem-bridge-v1',params:args,ordinal:0};
  const raw=h.canonical(packet),stored=await f.adapter.put('request',raw);
  const view=transport.makeRequestView({tool:'mcp__codex_apps__github_create_tree',packet,
    path:stored.path,bytes:stored.bytes,sha256:stored.sha256});
  const request_json=JSON.stringify({tool:'mcp__codex_apps__github_create_tree',arguments:args}),
    response_json=JSON.stringify({content:[{text:'complete raw response λ 🎯'}],structuredContent:{sha:'a'.repeat(40)}}),
    storage=JSON.stringify({request_json,response_json});
  const expected={request_bytes:Buffer.byteLength(request_json),request_sha256:hash(request_json),
    response_bytes:Buffer.byteLength(response_json),response_sha256:hash(response_json),
    stored_bytes:Buffer.byteLength(storage),stored_sha256:hash(storage)};
  assert.deepEqual(await f.adapter.persistRequestViewRaw({view,response_json,expected}),expected);
  assert.equal(f.adapter.read({id:'host_receipt-00000001',bytes:expected.stored_bytes,sha256:expected.stored_sha256}).toString('utf8'),storage);
  assert.ok(f.adapter.state().records.at(-1).stdin_bytes<16384,'Only raw reply and small source descriptor enter helper stdin');
});

test('real Worker request and exact params range are claimed once under its deadline',async t=>{
  const f=fixture(t);await f.adapter.action({action:'create'});
  const worker=runPython(t,f,`import json,sys\nfrom seti_repeater.native_v2_bridge_radio import Store,Worker\nfrom seti_repeater.empty_null_radio import canonical\nw=Worker(Store(sys.argv[1]),seconds=10)\nu=w.transport_usage()\np={'url':'https://example.invalid/fixture','unicode':'λ 🎯'}\nr=w.invoke('fetch',p)\ns=w.persist(0,'fetch',canonical(p),r)\nprint(json.dumps({'usage':u,'saved':s,'result':r}))\n`);
  const sources=[],deadlines=[],calls=[];
  const fakeHost={setRequestSource:source=>sources.push(source),withWorkerDeadline:async(deadline,fn)=>{deadlines.push(deadline);return fn();},
    usage:()=>({fixture:true}),invoke:async(operation,params)=>{calls.push({operation,params});return{sha:'b'.repeat(40),unicode:'λ 🎯'};}};
  const count=await serviceUntilDone(f,worker,fakeHost);assert.equal(count,2);assert.equal(calls.length,1);
  const source=sources[1],raw=fs.readFileSync(source.path),params=raw.subarray(source.params_offset,source.params_offset+source.params_bytes);
  assert.equal(hash(params),source.params_sha256);assert.deepEqual(JSON.parse(params),calls[0].params);
  assert.ok(deadlines.every(deadline=>Number.isFinite(deadline)));
  const result=worker.result();assert.equal(result.result.unicode,'λ 🎯');assert.equal(result.saved.sha256,hash(JSON.stringify({sha:'b'.repeat(40),unicode:'λ 🎯'}).replace(/[\u0080-\uffff]/g,ch=>'\\u'+ch.charCodeAt(0).toString(16).padStart(4,'0'))));
  await assert.rejects(f.adapter.action({action:'claim',id:'request-000001'}),/no retry/);
});

test('multimegabyte Git projection stays file-backed until the unchanged Worker reads it',async t=>{
  const f=fixture(t);await f.adapter.action({action:'create'});
  const filename='fixture/archive.json',data=Buffer.from('x'.repeat(2*1024*1024+1)),blob=crypto.createHash('sha1').update('blob '+data.length+'\0').update(data).digest('hex');
  const spool=path.join(f.directory,'case00.git-batch'),batch=Buffer.concat([Buffer.from(blob+' blob '+data.length+'\n'),data,Buffer.from('\n')]);
  fs.writeFileSync(spool,batch,{flag:'wx'});const gitCalls=[];
  const grouped=await f.adapter.groupedGitReadback({commit:'a'.repeat(40),spool_path:spool,paths:[filename],
    files:{[filename]:{bytes:data.length,sha256:hash(data),blob}},callGit:async kind=>gitCalls.push(kind)});
  assert.equal(grouped.result,undefined);assert.deepEqual(gitCalls,['git_fetch','git_cat_file_batch']);
  assert.equal(grouped.raw_git_receipt.sha256,hash(batch));assert.equal(grouped.local_projection.bytes>2*1024*1024,true);
  assert.equal(grouped.projection_verification.exact_frozen_blob_sha256,true);
  const worker=runPython(t,f,`import json,sys,hashlib\nfrom seti_repeater.native_v2_bridge_radio import Store,Worker\nfrom seti_repeater.empty_null_radio import canonical\nw=Worker(Store(sys.argv[1]),seconds=10)\nw.prepare_transport('{"ordinal":0}','0'*64)\np={'fixture':True}\nr=w.invoke('fetch_files',p)\ns=w.persist(0,'fetch_files',canonical(p),r)\nprint(json.dumps({'saved':s,'sha256':hashlib.sha256(canonical(r)).hexdigest(),'content_bytes':len(r['${filename}']['content'])}))\n`);
  const fakeHost={beginCase:()=>{},invoke:async()=>({schema:local.LOCAL_PROJECTION_REPLY,projection:grouped.local_projection})};
  assert.equal(await serviceUntilDone(f,worker,fakeHost),2);
  const result=worker.result();assert.equal(result.saved.sha256,grouped.local_projection.sha256);assert.equal(result.sha256,grouped.local_projection.sha256);
  assert.equal(result.content_bytes,data.toString('base64').length);
  const usage=f.adapter.usage();assert.equal(usage.functions_tool_calls,0);assert.ok(usage.local_read_bytes<4096,
    'Node reads only small Worker requests, never the projected map');
  const status=await f.adapter.action({action:'status'});assert.equal(status.buckets.git_projection.items,1);
  assert.equal(status.buckets.python_receipt.unknown_bytes,0);
});

test('tampered sealed local request is refused before any host dispatch',async t=>{
  const f=fixture(t);await f.adapter.action({action:'create'});
  const packet=JSON.stringify({fixture:true}),receipt=await f.adapter.put('request',packet);
  const filename=path.join(f.root,'items',receipt.id,'part');fs.chmodSync(filename,0o600);fs.writeFileSync(filename,'z'.repeat(packet.length));
  let dispatched=0;await assert.rejects(f.adapter.serviceOne({invoke:async()=>{dispatched++;}}),/hashed local sealed part/);
  assert.equal(dispatched,0);assert.equal(f.adapter.state().stopped,true);
});

test('malformed raw Git spool closes Store and cannot receive an automatic retry',async t=>{
  const f=fixture(t);await f.adapter.action({action:'create'});
  const spool=path.join(f.directory,'broken.git-batch');fs.writeFileSync(spool,'wrong header\n',{flag:'wx'});
  await assert.rejects(f.adapter.groupedGitReadback({commit:'a'.repeat(40),spool_path:spool,paths:['fixture/a'],
    files:{'fixture/a':{bytes:1,sha256:hash('x'),blob:'b'.repeat(40)}},callGit:async()=>{}}),/helper failed/);
  assert.equal(f.adapter.state().stopped,true);assert.equal(fs.existsSync(path.join(f.root,'STOPPED.json')),true);
});

test('real source-only helper launch verifies its loader and preserves raw stdin frames',async t=>{
  const f=fixture(t),frozen=path.join(f.directory,'frozen');
  const codeFiles=['scripts/radio_native_v2_source_loader.py','scripts/radio_native_v2_local_worker_helper.py',
    'src/seti_repeater/__init__.py','src/seti_repeater/empty_null_radio.py','src/seti_repeater/native_v2_bridge_radio.py'];
  for(const name of codeFiles) {
    fs.mkdirSync(path.dirname(path.join(frozen,name)),{recursive:true});fs.copyFileSync(path.join(repo,name),path.join(frozen,name));
  }
  const setup=`import hashlib,json,pathlib,sys,sysconfig\nimport radio_native_v2_source_loader as loader\nr=pathlib.Path(sys.argv[1])\nstdlib=pathlib.Path(sysconfig.get_path('stdlib'))\nruntime={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in stdlib.rglob('*') if p.is_file() and p.suffix in ('.py','.so') and 'site-packages' not in p.relative_to(stdlib).parts and '__pycache__' not in p.parts}\nexe=str(pathlib.Path(sys.executable).resolve());runtime[exe]=hashlib.sha256(pathlib.Path(exe).read_bytes()).hexdigest()\ncode={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*.py')}\nfreeze={'mode':'PROSPECTIVE_ENGINEERING_ONLY',**{k:False for k in loader.DISABLED},'runtime_sha256s':runtime,'code_sha256s':code,'executables':{'python':{'invocation':sys.executable,'resolved':exe,'sha256':runtime[exe],'version':sys.version},'git':{'invocation':'/usr/bin/git'},'node':{'invocation':sys.argv[2]}}}\nraw=json.dumps(freeze,sort_keys=True,separators=(',',':')).encode();p=r/'freeze.json';p.write_bytes(raw)\nprint(json.dumps(loader.prepare_helper_launch(r,p,hashlib.sha256(raw).hexdigest())))\n`;
  const result=cp.spawnSync(python,['-B','-c',setup,frozen,process.execPath],{env:{...process.env,PYTHONPATH:path.join(repo,'scripts')},encoding:'utf8',maxBuffer:1024*1024,timeout:20000});
  assert.equal(result.status,0,result.stderr);const launch=JSON.parse(result.stdout);
  t.after(()=>fs.rmSync(launch.startup_cache_prefix,{recursive:true,force:true}));
  const adapter=local.createLocalWorker({root:f.root,python,sourceRoot:path.join(frozen,'src'),
    helper:path.join(frozen,'scripts/radio_native_v2_local_worker_helper.py'),helperLaunch:launch});
  await adapter.action({action:'create'});
  const request_json=JSON.stringify({fixture:'raw stdin λ 🎯'}),response_json=JSON.stringify({fixture:true});
  const record={request_json,response_json,storage_json:JSON.stringify({request_json,response_json})};
  const receipts=await adapter.persistRawBatch([record,record]);assert.equal(receipts.length,2);
  assert.equal(adapter.capabilityManifest().helper_entrypoint_source_qualified,true);
  assert.equal(adapter.capabilityManifest().execution_authorized,false);
  assert.ok(adapter.state().records.every(r=>r.source_loader_verified===true));
  assert.deepEqual(fs.readdirSync(launch.startup_cache_prefix),[]);
});
