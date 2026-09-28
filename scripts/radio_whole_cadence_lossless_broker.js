// Run in the authorized functions tool runtime. repoPath and rpcPath are
// supplied by the supervisor (repoPath and rpcPath); all remote destinations are fixed below.
// This is a tool broker, not an HTTP client and not a scientific executor.
const repo = 'andersenmartin-blip/setisearch';
const branch = 'm43-support-qualification';
const prefix = 'results_radio_whole_cadence_lossless_2026-09-28/live01/';
const allowed = ['fetch','fetch_file','create_blob','create_tree','create_commit','update_ref'];
let sequence = 1;
const timings=[]; const brokerStarted=Date.now();
let finished = false;
const shellQuote = value => "'" + value.replace(/'/g, "'\"'\"'") + "'";
while (!finished && sequence <= 220) {
  const requestPath = rpcPath + '/request' + String(sequence).padStart(4,'0') + '.json';
  const framing = await tools.exec_command({cmd:'PYTHONPATH=src:scripts python scripts/radio_lossless_handoff.py '+shellQuote(rpcPath)+' '+sequence,workdir:repoPath,max_output_tokens:50000,yield_time_ms:30000});
  if (framing.exit_code !== 0) throw new Error('Request/done framing failed: '+framing.output);
  const header = JSON.parse(framing.output.trim());
  if (header.kind==='done') {finished=true;notify(header.result);break;}
  const size=header.bytes;
  if (!Number.isInteger(size)||size<1||size>600000) throw new Error('Request framing cap');
  let requestText=header.first;
  for (let offset=48000;offset<size;offset+=48000) {
    const code='from pathlib import Path; import json; print(json.dumps(Path('+JSON.stringify(requestPath)+').read_text()['+offset+':'+(offset+48000)+']))';
    const chunk=await tools.exec_command({cmd:'python -c '+shellQuote(code),max_output_tokens:50000});
    if (chunk.exit_code!==0) throw new Error('Request chunk read failed');
    requestText+=JSON.parse(chunk.output.trim());
  }
  if (requestText.length!==size) throw new Error('Request framing differs');
  const request = JSON.parse(requestText);
  const {method,params,id} = request;
  if (id!==sequence || !allowed.includes(method)) throw new Error('Broker sequence/method changed');
  if (method==='fetch') {
    if (!params.url.startsWith('https://api.github.com/repos/'+repo+'/git/')) throw new Error('Unapproved read destination');
  } else if (params.repository_full_name!==repo) throw new Error('Repository changed');
  if (method==='fetch_file' && (!params.path.startsWith(prefix)||params.encoding!=='base64'||!/^[0-9a-f]{40}$/.test(params.ref))) throw new Error('Unsafe immutable file read');
  if (method==='update_ref' && (params.branch_name!==branch || params.force!==false)) throw new Error('Unsafe branch update');
  if (method==='create_tree' && params.tree_elements.some(e=>!e.path.startsWith(prefix)||e.path.split('/').some(p=>p==='..'||p==='.'||p==='')||e.mode!=='100644'||e.type!=='blob'||'content' in e)) throw new Error('Unsafe evidence tree');
  let reply; const callStart=Date.now();
  try {
    const response = await tools['mcp__codex_apps__github_'+method](params);
    if (response.isError) throw new Error('GitHub tool returned isError');
    const result = method==='fetch' ? JSON.parse(response.structuredContent.content) : response.structuredContent;
    if (!result || typeof result!=='object') throw new Error('Structured GitHub result absent');
    reply={id,ok:true,result};
  } catch(error) { reply={id,ok:false,error:String(error),automatic_retry:false}; }
  timings.push({id,method,tool_milliseconds:Date.now()-callStart,ok:reply.ok});
  const responsePath=rpcPath+'/response'+String(sequence).padStart(4,'0')+'.json';
  const patch='*** Begin Patch\n*** Add File: '+responsePath+'.tmp\n+'+JSON.stringify(reply)+'\n*** End Patch';
  const written=await tools.apply_patch(patch);
  const moved=await tools.exec_command({cmd:'python -c '+shellQuote('from pathlib import Path; p=Path('+JSON.stringify(responsePath)+'); assert not p.exists(); Path(str(p)+".tmp").rename(p)'),max_output_tokens:1000});
  if (moved.exit_code!==0) throw new Error('Atomic tool response handoff failed');
  if (sequence%10===0) {notify({git_tool_requests_completed:sequence});await yield_control();}
  sequence++;
}
if (!finished) throw new Error('Broker request cap reached without completion');
return {requests:sequence-1,worker_finished:finished,timings,broker_elapsed_seconds:(Date.now()-brokerStarted)/1000};
