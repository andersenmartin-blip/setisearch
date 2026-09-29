// Authorized functions runtime. repoPath and rpcPath supplied by supervisor.
// One new pinned engineering scope; no retries, no credentials or direct network.
const repo='andersenmartin-blip/setisearch',branch='m43-support-qualification';
const prefix='results_radio_incremental_journal_2026-09-29/';
const allowed=['fetch','fetch_file','create_tree','create_commit','update_ref'];
const quote=s=>"'"+s.replace(/'/g,"'\"'\"'")+"'";
const timings=[];const started=Date.now();let sequence=1,finished=false;
async function handoff(n,deliver){
  const run=await tools.exec_command({cmd:'PYTHONPATH=src:scripts python scripts/radio_batch_handoff.py '+quote(rpcPath)+' '+n+(deliver?' --deliver':''),workdir:repoPath,max_output_tokens:50000,yield_time_ms:30000});
  if(run.exit_code!==0)throw new Error('Atomic response/next request failed: '+run.output);
  return JSON.parse(run.output.trim());
}
let header=await handoff(1,false);
while(sequence<=240){
  if(header.kind==='done'){finished=true;notify(header.result);break;}
  const size=header.bytes,requestPath=rpcPath+'/request'+String(sequence).padStart(4,'0')+'.json';
  if(header.kind!=='request'||!Number.isInteger(size)||size<1||size>66000)throw new Error('Bounded request framing differs');
  let requestText=header.first;
  const offsets=[];for(let o=48000;o<size;o+=48000)offsets.push(o);
  for(let start=0;start<offsets.length;start+=8){
    const reads=await Promise.allSettled(offsets.slice(start,start+8).map(async offset=>{
      const code='from pathlib import Path; import json; print(json.dumps(Path('+JSON.stringify(requestPath)+').read_text()['+offset+':'+(offset+48000)+']))';
      const run=await tools.exec_command({cmd:'python -c '+quote(code),max_output_tokens:50000});
      if(run.exit_code!==0)throw new Error('Immutable request chunk failed');
      return JSON.parse(run.output.trim());
    }));
    for(const r of reads){if(r.status!=='fulfilled')throw r.reason;requestText+=r.value;}
  }
  if(requestText.length!==size)throw new Error('Request length differs');
  const {id,method,params}=JSON.parse(requestText);
  if(id!==sequence||!allowed.includes(method))throw new Error('Sequence/method differs');
  if(method==='fetch'){
    if(!params.url.startsWith('https://api.github.com/repos/'+repo+'/git/'))throw new Error('Read destination differs');
  }else if(params.repository_full_name!==repo)throw new Error('Repository changed');
  if(method==='fetch_file'&&(!params.path.startsWith(prefix)||params.encoding!=='base64'||!/^[0-9a-f]{40}$/.test(params.ref)))throw new Error('Unsafe immutable read');
  if(method==='update_ref'&&(params.branch_name!==branch||params.force!==false))throw new Error('Unsafe branch update');
  if(method==='create_tree'){
    const es=params.tree_elements;
    if(!es.length||es.length>3||new Set(es.map(e=>e.path)).size!==es.length)throw new Error('Invalid batch inventory');
    if(es.some(e=>Object.keys(e).sort().join(',')!=='content,mode,path,type'||!e.path.startsWith(prefix)||e.path.split('/').some(x=>['','.','..'].includes(x))||e.mode!=='100644'||e.type!=='blob'||typeof e.content!=='string'||/[^\x00-\x7F]/.test(e.content)))throw new Error('Unsafe ASCII content batch');
  }
  let reply;const t=Date.now();
  try{
    const response=await tools['mcp__codex_apps__github_'+method](params);
    if(response.isError)throw new Error('GitHub tool returned isError');
    let result=method==='fetch'?JSON.parse(response.structuredContent.content):response.structuredContent;
    if(method==='fetch_file')result={sha:result.sha,encoding:result.encoding,content:result.content.replace(/\r?\n/g,'')};
    if(!result||typeof result!=='object')throw new Error('Structured response absent');
    reply={id,ok:true,result};
  }catch(error){reply={id,ok:false,error:String(error),automatic_retry:false};}
  timings.push({id,method,tool_milliseconds:Date.now()-t,ok:reply.ok});
  const responsePath=rpcPath+'/response'+String(sequence).padStart(4,'0')+'.json.tmp';
  await tools.apply_patch('*** Begin Patch\n*** Add File: '+responsePath+'\n+'+JSON.stringify(reply)+'\n*** End Patch');
  header=await handoff(sequence,true);
  if(sequence%10===0)notify({incremental_git_requests_completed:sequence});
  sequence++;
}
if(!finished)throw new Error('Scope ended without done frame; no retry');
return {requests:sequence-1,worker_finished:finished,timings,broker_elapsed_seconds:(Date.now()-started)/1000};
