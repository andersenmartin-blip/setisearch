#!/usr/bin/env node
'use strict';
// Deterministic full-size offline measurement. Never contacts GitHub, creates
// case reservations, constructs an RNG, or reads telescope data. The direct
// local baseline is deliberately distinct from the functions/Python bridge.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const h = require('./radio_native_v2_broker_host');
const MIB = 1024 * 1024;
const CHUNK = 32768;
const RSS_CAP = 512 * MIB;
const SCHEMA = 'radio-native-v2-full-size-offline-capacity-v1';
const PYTHON_STORE_MEASUREMENT = String.raw`
import hashlib,json,os,resource,sys,time
from pathlib import Path
from seti_repeater.empty_null_radio import canonical
from seti_repeater.native_v2_bridge_radio import Store,Worker,git_projection,CHUNK_BYTES,READ_BYTES
print(json.dumps({'capacity_proc_pid':int(os.readlink('/proc/self'))}),flush=True)
started=time.monotonic()
fixture_root=Path(sys.argv[1]);fixture=json.loads((fixture_root/'capacity_fixture.json').read_bytes())
if fixture['profile']!='broker_capacity': raise ValueError('Actual broker capacity shape required')
freeze=fixture['freeze'];spool=next((fixture_root/'git-spool').glob('*.git-batch'))
store=Store.create(str(fixture_root/'python-store'))
host_file=max((fixture_root/'raw-tool-receipts').glob('*.json'),key=lambda p:p.stat().st_size)
host_raw=host_file.read_bytes();host_receipt=store.write('host-full-request','host_receipt',host_raw,case_ordinal=0)
del host_raw
projected=git_projection(store,'git-projection',str(spool),'1'*40,sorted(freeze['files']),freeze['files'],case_ordinal=0)
raw=store.payload('git-projection');result=json.loads(raw)
if canonical(result)!=raw: raise ValueError('Full-size projection canonical bytes differ')
response=store.write('response-000000','response',raw,case_ordinal=0)
store.reserve('python-000000','python_receipt',48*1024**2,case_ordinal=0)
worker=Worker(store);worker.case_ordinal=0
request=canonical({'fixture':'full-size-offline-normalized-readback'})
# Exact callback setup is isolated from Worker._call and its external host IPC.
worker.receipts[0]={'id':'python-000000','operation':'fetch_files','invoke_ordinal':0,
                  'request':request,'response_id':'response-000000'}
receipt=worker.persist(0,'fetch_files',request,result)
state={'schema':'radio-native-v2-capacity-state-v1','engineering_only':True,'padding':''}
state['padding']='x'*(2*1024**2-len(canonical(state)))
state_receipt=worker.persist_state(state)
if state_receipt['bytes']!=2*1024**2: raise ValueError('Exact maximal state callback differs')
status=store.status();disk_rows=[]
for file in sorted((fixture_root/'python-store').rglob('*')):
    if file.is_file(): disk_rows.append({'path':str(file.relative_to(fixture_root/'python-store')),'bytes':file.stat().st_size})
payloads={}
for item in ('host-full-request','git-projection','response-000000','python-000000','state-000000'):
    file=fixture_root/'python-store'/'items'/item/'part'
    with file.open('rb') as stream:
        sha=hashlib.sha256()
        while block:=stream.read(32768):sha.update(block)
    payloads[item]={'bytes':file.stat().st_size,'sha256':sha.hexdigest()}
if payloads['git-projection']!=payloads['response-000000'] or payloads['git-projection']!=payloads['python-000000']:
    raise ValueError('Concrete durable normalized response/callback bytes differ')
peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
if peak>512*1024**2: raise ValueError('Python store/callback process exceeds512MiB')
elapsed=time.monotonic()-started
if elapsed>600:raise ValueError('Concrete storage/callback case exceeds600s')
print(json.dumps({'schema':'radio-native-v2-full-size-python-storage-v1','status':'PASS',
    'python_runtime':{'version':sys.version,'executable':sys.executable,'bytecode_write_disabled':sys.dont_write_bytecode},
    'profile':fixture['profile'],'host_receipt_bytes':host_receipt['bytes'],
    'projected_response_bytes':projected['projection']['bytes'],
    'python_callback_receipt_bytes':receipt['bytes'],'state_callback_bytes':state_receipt['bytes'],
    'append_chunk_bytes':CHUNK_BYTES,'read_chunk_bytes':READ_BYTES,'store_status':status,
    'payloads':payloads,'disk':{'files':len(disk_rows),'bytes':sum(row['bytes'] for row in disk_rows),'rows':disk_rows},
    'python_kernel_peak_rss_bytes':peak,'elapsed_seconds':elapsed,
    'fsync_exclusive_store_real':True,'real_python_callbacks_exercised':True,
    'worker_call_protocol_exercised':False,'functions_tool_ipc_measured':False,
    'execution_authorized':False,'scientific_admission_authorized':False,
    'automatic_retry':False,'rng_draws':0,'telescope_reads':0,'case_reservations':0}),flush=True)
`;
const digest = data => crypto.createHash('sha256').update(data).digest('hex');
const gitBlob = data => crypto.createHash('sha1').update('blob '+Buffer.byteLength(data)+'\0').update(data).digest('hex');
const exact = (ok, message) => { if (!ok) throw new Error(message); };
const gitEnv = { ...process.env, GIT_CONFIG_NOSYSTEM:'1', GIT_CONFIG_GLOBAL:'/dev/null',
  GIT_AUTHOR_NAME:'Offline capacity fixture', GIT_AUTHOR_EMAIL:'fixture@example.invalid',
  GIT_COMMITTER_NAME:'Offline capacity fixture', GIT_COMMITTER_EMAIL:'fixture@example.invalid',
  GIT_AUTHOR_DATE:'2000-01-01T00:00:00Z', GIT_COMMITTER_DATE:'2000-01-01T00:00:00Z' };
function git(repo, args, input) {
  return cp.execFileSync('git', ['--no-replace-objects','-c','core.hooksPath=/dev/null',
    '-c','gc.auto=0',...args], {cwd:repo,env:gitEnv,input,encoding:'utf8',maxBuffer:8*MIB}).trim();
}
function durableWrite(filename, data) {
  fs.mkdirSync(path.dirname(filename),{recursive:true,mode:0o700});
  const fd = fs.openSync(filename,'wx',0o600);
  try { fs.writeFileSync(fd,data); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
  const parent = fs.openSync(path.dirname(filename),'r');
  try { fs.fsyncSync(parent); } finally { fs.closeSync(parent); }
}
function inventory(root) {
  const rows = [];
  function walk(dir) {
    for (const entry of fs.readdirSync(dir,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name))) {
      const file=path.join(dir,entry.name);
      if(entry.isDirectory())walk(file);
      else if(entry.isFile())rows.push({path:path.relative(root,file),bytes:fs.statSync(file).size});
      else throw Error('Capacity fixture contains non-file/non-directory entry');
    }
  }
  if(fs.existsSync(root))walk(root);
  return {files:rows.length,bytes:rows.reduce((sum,row)=>sum+row.bytes,0),rows};
}

// The only projection input is a <=32KiB filesystem read. Base64 is streamed
// with carry <=2 bytes, never by loading the whole raw Git batch into memory.
async function projectBatch(filename, paths, pins) {
  const stream=fs.createReadStream(filename,{highWaterMark:CHUNK});
  const hash=crypto.createHash('sha256');
  const result={};
  let bytes=0,maximumChunk=0,index=0,header='',remaining=null,pieces=[],carry=Buffer.alloc(0),contentHash=null;
  let separator=false;
  for await(const chunk of stream) {
    maximumChunk=Math.max(maximumChunk,chunk.length);bytes+=chunk.length;hash.update(chunk);
    let offset=0;
    while(offset<chunk.length) {
      exact(index<paths.length,'Extra bytes after final Git object');
      const pin=pins[paths[index]];
      if(separator) {
        exact(chunk[offset++]===10,'Git object separator differs');
        if(carry.length)pieces.push(carry.toString('base64'));
        exact(contentHash.digest('hex')===pin.sha256,'Projected immutable file SHA256 differs');
        result[paths[index]]={sha:pin.blob,content:pieces.join('')};
        index++;header='';remaining=null;pieces=[];carry=Buffer.alloc(0);contentHash=null;separator=false;
      } else if(remaining===null) {
        const newline=chunk.indexOf(10,offset),end=newline<0?chunk.length:newline;
        header+=chunk.subarray(offset,end).toString('ascii');offset=end+(newline<0?0:1);
        exact(header.length<=128,'Unbounded Git batch header');
        if(newline>=0) {
          exact(header===pin.blob+' blob '+pin.bytes,'Git immutable object header differs');
          remaining=pin.bytes;contentHash=crypto.createHash('sha256');
          if(remaining===0)separator=true;
        }
      } else {
        const take=Math.min(remaining,chunk.length-offset),part=chunk.subarray(offset,offset+take);
        contentHash.update(part);offset+=take;remaining-=take;
        const combined=carry.length?Buffer.concat([carry,part]):part;
        const aligned=combined.length-combined.length%3;
        if(aligned)pieces.push(combined.subarray(0,aligned).toString('base64'));
        carry=Buffer.from(combined.subarray(aligned));
        if(remaining===0)separator=true;
      }
    }
  }
  exact(index===paths.length&&remaining===null&&!separator&&!header,'Truncated Git batch');
  return {result,bytes,sha256:hash.digest('hex'),maximum_chunk_bytes:maximumChunk};
}

async function measureLocalBaseline(root,profile='host_ceiling') {
  exact(['host_ceiling','broker_capacity'].includes(profile),'Known immutable capacity profile required');
  const started=process.hrtime.bigint(),repo=path.join(root,'offline-repo');
  const receiptsRoot=path.join(root,'raw-tool-receipts'),spoolRoot=path.join(root,'git-spool');
  fs.mkdirSync(repo,{recursive:true,mode:0o700});fs.mkdirSync(spoolRoot,{mode:0o700});
  git(repo,['init','-q']);
  const baseBlob=git(repo,['hash-object','-w','--stdin'],'engineering-only capacity fixture\n');
  git(repo,['update-index','--add','--cacheinfo','100644,'+baseBlob+',fixture.txt']);
  const parentTree=git(repo,['write-tree']);
  const parent=git(repo,['commit-tree',parentTree], 'Deterministic offline fixture parent\n');
  const prefix=h.PREFIX+'/case00-'+ (profile==='host_ceiling'?'f':'e').repeat(16);
  let manifest=h.canonical({schema:'radio-native-v2-capacity-fixture-v1',engineering_only:true,
    synthetic_bytes:true,rng_draws:0,telescope_reads:0,case_reservations:0,
    stored_target_bytes:36*MIB,file_count:28});
  if(profile==='broker_capacity') {
    const record=JSON.parse(manifest);record.padding='';
    record.padding=' '.repeat(512*1024-Buffer.byteLength(h.canonical(record)));
    manifest=h.canonical(record);exact(Buffer.byteLength(manifest)===512*1024,'Exact broker manifest reserve differs');
  }
  const contents={[prefix+'/HEAD']:digest(manifest)+'\n',[prefix+'/manifest.json']:manifest};
  const targetStored=profile==='host_ceiling'?36*MIB:26*(4*Math.ceil(MIB/3))+512*1024+65;
  let remaining=targetStored-Buffer.byteLength(manifest)-65;
  for(let i=0;i<26;i++) {
    if(profile==='host_ceiling') {
      const size=Math.floor(remaining/(26-i));remaining-=size;
      contents[prefix+'/payload'+String(i).padStart(2,'0')+'.txt']=String.fromCharCode(65+i).repeat(size);
    } else contents[prefix+'/chunk'+String(i).padStart(4,'0')+'.b64']=Buffer.alloc(MIB,65+i).toString('base64');
  }
  const files=Object.fromEntries(Object.entries(contents).map(([name,content])=>[name,
    {bytes:Buffer.byteLength(content),sha256:digest(content),blob:gitBlob(content)}]));
  exact(Object.keys(files).length===28&&Object.values(files).reduce((sum,pin)=>sum+pin.bytes,0)===targetStored,
    'Maximal frozen fixture size differs');
  const freeze={schema:'radio-native-v2-inline-terminal-archive-v1',mode:'ENGINEERING_ONLY',
    repository:h.REPOSITORY,branch:h.BRANCH,broker_protocol:h.BROKER_PROTOCOL,
    ordinal:0,prefix,parent,parent_tree:parentTree,files,manifest_sha256:digest(manifest),
    limits:{calls:64,request_bytes:48*MIB,response_bytes:64*MIB,stored_bytes:36*MIB,
      files:28,seconds:600,peak_rss_bytes:RSS_CAP},
    per_operation_response_reservations:{fetch:4*MIB,create_tree:MIB,create_commit:65536,update_ref:16384,fetch_files:48*MIB},
    single_inline_tree_request:true,single_grouped_readback:true,force:false,automatic_retry:false,
    execution_restart_authorized:false,scientific_admission_authorized:false};
  durableWrite(path.join(root,'capacity_fixture.json'),JSON.stringify({profile,freeze},null,2)+'\n');
  const api='https://api.github.com/repos/'+h.REPOSITORY+'/git/';
  let head=parent,tree=null,candidate=null,receiptOrdinal=0,gitFetchMockCount=0,catFileCount=0,projection;
  const envelope=value=>({content:[{type:'text',text:'Complete offline mocked connector envelope'}],
    structuredContent:value,_meta:{offline_fixture:true},isError:false});
  const tools={
    mcp__codex_apps__github_fetch:async args=>{
      const suffix=args.url.slice(api.length);let value;
      if(suffix==='ref/heads/'+encodeURIComponent(h.BRANCH))value={ref:'refs/heads/'+h.BRANCH,object:{type:'commit',sha:head}};
      else if(suffix==='commits/'+parent)value={sha:parent,tree:{sha:parentTree},parents:[]};
      else if(suffix==='commits/'+candidate)value={sha:candidate,tree:{sha:tree},parents:[{sha:parent}]};
      else if(suffix.startsWith('trees/')) {
        const sha=suffix.slice(6),rows=git(repo,['ls-tree',sha]).split('\n').filter(Boolean).map(line=>{
          const [entry,name]=line.split('\t'),[mode,type,object]=entry.split(' ');return {path:name,mode,type,sha:object};
        });value={sha,truncated:false,tree:rows};
      } else throw Error('Unexpected offline Git endpoint');
      return envelope({content:JSON.stringify(value)});
    },
    mcp__codex_apps__github_create_tree:async args=>{
      git(repo,['read-tree',parentTree]);
      for(const row of args.tree_elements) {
        const actual=git(repo,['hash-object','-w','--stdin'],row.content);
        exact(actual===files[row.path].blob,'Offline Git blob differs');
        git(repo,['update-index','--add','--cacheinfo','100644,'+actual+','+row.path]);
      }
      tree=git(repo,['write-tree']);return envelope({sha:tree});
    },
    mcp__codex_apps__github_create_commit:async args=>{
      candidate=git(repo,['commit-tree',args.tree_sha,'-p',args.parent_sha],args.message+'\n');return envelope({sha:candidate});
    },
    mcp__codex_apps__github_update_ref:async()=>{head=candidate;return envelope({success:true});},
    exec_command:async args=>{
      const begin=process.hrtime.bigint();
      if(args.cmd.startsWith('git --no-replace-objects -c core.hooksPath=/dev/null -c gc.auto=0 fetch ')) {
        // The immutable commit is already local. There is deliberately no network call.
        gitFetchMockCount++;
      } else {
        exact(args.cmd.startsWith('set -eu\numask 077\nset -C\ngit --no-replace-objects '),'Unexpected offline shell command');
        cp.execFileSync('/bin/bash',['-c',args.cmd],{cwd:args.workdir,env:gitEnv,encoding:'utf8',maxBuffer:1024});
        catFileCount++;
      }
      return {exit_code:0,output:'Offline Git operation completed; raw batch remains on disk\n',wall_time_seconds:Number(process.hrtime.bigint()-begin)/1e9};
    }
  };
  const persistRaw=async record=>{
    const filename=path.join(receiptsRoot,String(receiptOrdinal++).padStart(4,'0')+'.json');
    durableWrite(filename,record.storage_json);
    exact(fs.statSync(filename).size===Buffer.byteLength(record.storage_json),'Durable raw receipt size differs');
    return {request_bytes:Buffer.byteLength(record.request_json),request_sha256:digest(record.request_json),
      response_bytes:Buffer.byteLength(record.response_json),response_sha256:digest(record.response_json),
      stored_bytes:Buffer.byteLength(record.storage_json),stored_sha256:digest(record.storage_json)};
  };
  const groupedGitReadback=async job=>{
    await job.callGit('git_fetch');await job.callGit('git_cat_file_batch');
    const fd=fs.openSync(job.spool_path,'r');try{fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
    const dir=fs.openSync(spoolRoot,'r');try{fs.fsyncSync(dir);}finally{fs.closeSync(dir);}
    projection=await projectBatch(job.spool_path,job.paths,job.files);
    exact(projection.bytes===job.raw_git_reserved_bytes,'Frozen raw Git spool reservation differs');
    return {commit:job.commit,single_cat_file_batch:true,result:projection.result,
      raw_git_receipt:{path:job.spool_path,bytes:projection.bytes,sha256:projection.sha256,durable:true}};
  };
  const host=h.createBrokerHost({tools,persistRaw,groupedGitReadback,repoPath:repo,spoolRoot});
  const freezeJson=h.canonical(freeze);host.beginCase(freezeJson,digest(freezeJson));
  const get=suffix=>host.invoke('fetch',{url:api+suffix});
  await get('ref/heads/'+encodeURIComponent(h.BRANCH));await get('commits/'+parent);await get('trees/'+parentTree);
  await host.invoke('create_tree',{repository_full_name:h.REPOSITORY,base_tree_sha:parentTree,
    tree_elements:Object.entries(contents).map(([name,content])=>({path:name,mode:'100644',type:'blob',content}))});
  await get('trees/'+tree);
  await host.invoke('create_commit',{repository_full_name:h.REPOSITORY,parent_sha:parent,tree_sha:tree,message:'Full-size deterministic offline capacity fixture'});
  await get('commits/'+candidate);await get('ref/heads/'+encodeURIComponent(h.BRANCH));
  await host.invoke('update_ref',{repository_full_name:h.REPOSITORY,branch_name:h.BRANCH,sha:candidate,force:false});
  const readback=await host.invoke('fetch_files',{repository_full_name:h.REPOSITORY,ref:candidate,paths:Object.keys(files).sort(),encoding:'base64'});
  for(const name of Object.keys(files)) {
    const decoded=Buffer.from(readback[name].content,'base64');
    exact(decoded.length===files[name].bytes&&digest(decoded)===files[name].sha256,'Full-size independent returned byte check failed');
  }
  await get('ref/heads/'+encodeURIComponent(h.BRANCH));const finish=host.finishCase(),usage=host.usage();
  const receiptInventory=inventory(receiptsRoot),spoolInventory=inventory(spoolRoot),gitInventory=inventory(path.join(repo,'.git'));
  exact(usage.cases===1&&usage.calls===12&&receiptOrdinal===12&&gitFetchMockCount===1&&catFileCount===1,'Exact baseline operation count differs');
  exact(usage.receipt_bytes===receiptInventory.bytes&&usage.git_spool_bytes===spoolInventory.bytes,'Actual disk/accounting disagreement');
  exact(projection.maximum_chunk_bytes<=CHUNK,'Git projection read exceeds bounded chunk');
  const elapsed=Number(process.hrtime.bigint()-started)/1e9;
  const peakRss=process.resourceUsage().maxRSS*1024;
  exact(peakRss<=RSS_CAP,'Node host exceeded frozen512MiB process RSS cap');
  exact(elapsed<=600,'Maximal baseline exceeded600s case deadline');
  const encodedBytes=Object.values(readback).reduce((sum,row)=>sum+row.content.length,0);
  const projectionBytes=2+Math.max(0,Object.keys(readback).length-1)+Object.entries(readback).reduce((sum,[name,row])=>
    sum+Buffer.byteLength(JSON.stringify(name))+1+Buffer.byteLength(JSON.stringify({sha:row.sha,content:''}))+row.content.length,0);
  const hostAppendChunks=Math.ceil(usage.receipt_bytes/24576);
  const readProjectionChunks=Math.ceil(projectionBytes/32768);
  return {schema:SCHEMA,scope:'DIRECT_LOCAL_HOST_FS_GIT_BASELINE',profile,status:'PASS',
    synthetic_ascii_payload_bytes:targetStored,frozen_archive_files:28,
    fixture_represents_actual_case:false,broker_capacity_record_shape:profile==='broker_capacity',
    maximal_fixture:{stored_bytes:targetStored,request_cap_bytes:48*MIB,response_cap_bytes:64*MIB,
      case_receipt_cap_bytes:192*MIB,case_git_spool_cap_bytes:40*MIB,case_calls_cap:64,process_rss_cap_bytes:RSS_CAP},
    actual_tool_usage:usage,finish_receipt:{...finish,raw_git_receipt:{...finish.raw_git_receipt,path:path.relative(root,finish.raw_git_receipt.path)}},
    full_size_readback_encoded_content_bytes:encodedBytes,normalized_readback_json_bytes:projectionBytes,
    normalized_fetch_files_reservation_bytes:48*MIB,
    normalized_readback_fits_fetch_files_reservation:projectionBytes<=48*MIB,
    bridge_lower_bound:{raw_receipt_append_chunk_bytes:24576,projection_read_chunk_bytes:32768,
      raw_receipt_append_calls_at_least:hostAppendChunks,projection_read_calls_at_least:readProjectionChunks,
      combined_broker_and_support_calls_at_least:usage.calls+hostAppendChunks+readProjectionChunks,
      original_case_tool_call_cap:64,original_cumulative_tool_call_cap:512,
      original_caps_fit_one_maximal_case:false,
      supporting_raw_reply_custody_items_at_least:hostAppendChunks+readProjectionChunks-1,
      original_bridge_store_item_cap:2048,original_store_items_fit_one_maximal_case:false,
      original_budget_status:'FAIL_PRE_DISPATCH_STATIC_LOWER_BOUND',
      rationale:'Strict lower bound excludes reserve/seal/create/projection/status and custody acknowledgements; no supporting call was dispatched'},
    projection_maximum_read_chunk_bytes:projection.maximum_chunk_bytes,
    disk:{raw_tool_receipts:receiptInventory,git_spool:spoolInventory,offline_git_objects:gitInventory},
    elapsed_seconds:elapsed,node_host_kernel_peak_rss_bytes:peakRss,
    offline_git_fetch_mocked:true,offline_git_cat_file_real:true,fsync_raw_receipts_and_spool:true,
    original_integrated_tool_call_cap_qualified:false,functions_to_python_bridge_qualified:false,
    host_runtime_qualified:false,execution_authorized:false,scientific_admission_authorized:false,
    automatic_retry:false,rng_draws:0,telescope_reads:0,case_reservations:0,
    limitations:['Direct local filesystem sink and local Git baseline; no functions/tool IPC measured',
      'One maximum-size case; eight-case cumulative live bridge remains unqualified',
      'Actual Git fetch and connector tools mocked; hidden network and hosted V8 not measured']};
}

function rssTree(pid) {
  const rows=[];
  function visit(id) {
    try {
      const text=fs.readFileSync('/proc/'+id+'/status','utf8');
      const match=text.match(/^VmRSS:\s+(\d+) kB$/m),name=text.match(/^Name:\s+(.+)$/m);
      rows.push({pid:id,name:name?name[1]:'unknown',rss_bytes:match?Number(match[1])*1024:0});
      const children=fs.readFileSync('/proc/'+id+'/task/'+id+'/children','utf8').trim();
      if(children)children.split(/\s+/).forEach(child=>visit(Number(child)));
    } catch(error) {if(error.code!=='ENOENT'&&error.code!=='ESRCH')throw error;}
  }
  visit(pid);return rows;
}
async function measurePythonStore(root,python) {
  const started=process.hrtime.bigint();
  const child=cp.spawn(python,['-B','-c',PYTHON_STORE_MEASUREMENT,root],{env:{...process.env,
    PYTHONPATH:path.resolve(__dirname,'../src')},stdio:['ignore','pipe','pipe']});
  let stdout='',stderr='',announced=false;
  child.stdout.on('data',chunk=>{
    stdout+=chunk;exact(Buffer.byteLength(stdout)<=256*1024,'Unbounded Python store report');
    if(!announced&&stdout.includes('\n')) {
      const newline=stdout.indexOf('\n'),first=JSON.parse(stdout.slice(0,newline));
      exact(Number.isSafeInteger(first.capacity_proc_pid),'Concrete Python process identity required');
      if(typeof process.send==='function')process.send({proc_pid:first.capacity_proc_pid});
      stdout=stdout.slice(newline+1);announced=true;
    }
  });
  child.stderr.on('data',chunk=>{stderr+=chunk;exact(Buffer.byteLength(stderr)<=256*1024,'Unbounded Python store errors');});
  const outcome=await new Promise((resolve,reject)=>{child.on('error',reject);child.on('exit',(code,signal)=>resolve({code,signal}));});
  const report=outcome.code===0?JSON.parse(stdout):{schema:SCHEMA,status:'FAIL',scope:'PYTHON_STORE_AND_CALLBACK_COMPONENT',
    error:'Concrete Python component failed',stdout,stderr,execution_authorized:false,scientific_admission_authorized:false,
    rng_draws:0,telescope_reads:0,case_reservations:0};
  report.python_exit=outcome;report.supervisor_elapsed_seconds=Number(process.hrtime.bigint()-started)/1e9;
  return report;
}
async function supervise(output,profile,python,fixtureRoot) {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'seti-native-v2-capacity-'));
  const workerArgs=fixtureRoot?['--python-store-worker',fixtureRoot,python]:['--worker',root,profile];
  const child=cp.spawn(process.execPath,[__filename,...workerArgs],{stdio:['ignore','pipe','pipe','ipc']});
  // /proc exposes host PIDs in this execution profile while process.pid and
  // child.pid use a nested namespace. Resolve the actual children through the
  // supervisor's /proc/self link before sampling, never assume child.pid.
  const workerProcPids=new Set();
  child.on('message',message=>{if(message&&Number.isSafeInteger(message.proc_pid))workerProcPids.add(message.proc_pid);});
  let stdout='',stderr='',peakCombined=0,samples=0;const peaks={};
  child.stdout.on('data',data=>{stdout+=data;exact(Buffer.byteLength(stdout)<=256*1024,'Unbounded worker report');});
  child.stderr.on('data',data=>{stderr+=data;exact(Buffer.byteLength(stderr)<=256*1024,'Unbounded worker errors');});
  const timer=setInterval(()=>{
    const unique=new Map();for(const id of workerProcPids)for(const row of rssTree(id))unique.set(row.pid,row);
    const rows=[...unique.values()];
    samples++;peakCombined=Math.max(peakCombined,rows.reduce((sum,row)=>sum+row.rss_bytes,0));
    for(const row of rows) {
      const key=String(row.pid);if(!peaks[key]||peaks[key].rss_bytes<row.rss_bytes)peaks[key]=row;
    }
  },5);
  const outcome=await new Promise((resolve,reject)=>{child.on('error',reject);child.on('exit',(code,signal)=>resolve({code,signal}));});
  clearInterval(timer);
  let report;try {report=JSON.parse(stdout);}catch(error){report={schema:SCHEMA,status:'FAIL',error:'Worker did not return bounded JSON',stdout,stderr};}
  report.supervision={exit_code:outcome.code,signal:outcome.signal,sampling_interval_ms:5,samples,
    sampled_combined_process_tree_peak_rss_bytes:peakCombined,process_peak_samples:Object.values(peaks),
    combined_sampling_is_lower_bound:true,git_subprocess_rss_kernel_proven:false,
    proc_pid_namespace_resolved:workerProcPids.size>0,fixture_root:fixtureRoot||root};
  const sourceRoot=path.resolve(__dirname,'../src');
  report.measurement_source_sha256=Object.fromEntries([
    __filename,path.join(__dirname,'radio_native_v2_broker_host.js'),
    path.join(__dirname,'radio_native_v2_host_bridge.js'),path.join(__dirname,'radio_native_v2_bridge.py'),
    path.join(sourceRoot,'seti_repeater/native_v2_bridge_radio.py')
  ].map(file=>[path.relative(path.resolve(__dirname,'..'),file),digest(fs.readFileSync(file))]));
  report.node_runtime={version:process.version,executable:process.execPath,platform:process.platform,arch:process.arch};
  if(outcome.code!==0||Object.values(peaks).some(row=>row.rss_bytes>RSS_CAP))report.status='FAIL';
  if(output)durableWrite(path.resolve(output),JSON.stringify(report,null,2)+'\n');
  process.stdout.write(JSON.stringify(report,null,2)+'\n');
  if(report.status!=='PASS')process.exitCode=1;
}
if(require.main===module) {
  if(process.argv[2]==='--python-store-worker') {
    if(typeof process.send==='function')process.send({proc_pid:Number(fs.readlinkSync('/proc/self'))});
    measurePythonStore(process.argv[3],process.argv[4]).then(report=>process.stdout.write(JSON.stringify(report)+'\n'))
      .catch(error=>{process.stdout.write(JSON.stringify({schema:SCHEMA,status:'FAIL',error:String(error)})+'\n');process.exitCode=1;});
  } else if(process.argv[2]==='--worker') {
    if(typeof process.send==='function')process.send({proc_pid:Number(fs.readlinkSync('/proc/self'))});
    measureLocalBaseline(process.argv[3],process.argv[4]).then(report=>process.stdout.write(JSON.stringify(report)+'\n')).catch(error=>{
      process.stdout.write(JSON.stringify({schema:SCHEMA,status:'FAIL',scope:'DIRECT_LOCAL_HOST_FS_GIT_BASELINE',
        error:String(error),stack:error.stack,node_host_kernel_peak_rss_bytes:process.resourceUsage().maxRSS*1024,
        execution_authorized:false,scientific_admission_authorized:false,rng_draws:0,telescope_reads:0,case_reservations:0})+'\n');process.exitCode=1;
    });
  } else {
    let output=null,profile='host_ceiling',fixtureRoot=null,python=process.env.CODEX_PRIMARY_RUNTIME_PYTHON||'python3';
    for(let index=2;index<process.argv.length;index+=2) {
      exact(index+1<process.argv.length&&['--output','--profile','--python','--python-store-fixture'].includes(process.argv[index]),
        'Usage: node radio_native_v2_bridge_capacity.js [--profile host_ceiling|broker_capacity] [--python-store-fixture FIXTURE] [--python EXECUTABLE] [--output NEW_PATH]');
      if(process.argv[index]==='--output')output=process.argv[index+1];
      else if(process.argv[index]==='--python-store-fixture')fixtureRoot=path.resolve(process.argv[index+1]);
      else if(process.argv[index]==='--python')python=process.argv[index+1];
      else profile=process.argv[index+1];
    }
    supervise(output,profile,python,fixtureRoot).catch(error=>{process.stderr.write(String(error)+'\n');process.exitCode=1;});
  }
}
module.exports={SCHEMA,CHUNK,RSS_CAP,projectBatch,measureLocalBaseline,measurePythonStore,rssTree};
