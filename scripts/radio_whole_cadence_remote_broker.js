// Run in the authorized functions tool runtime. rpcPath and sessionId are
// supplied by the supervisor; all remote destinations are fixed below.
// This is a tool broker, not an HTTP client and not a scientific executor.
const repo = 'andersenmartin-blip/setisearch';
const branch = 'm43-support-qualification';
const prefix = 'results_radio_whole_cadence_remote_2026-09-28/live01/';
const allowed = ['fetch','create_blob','create_tree','create_commit','update_ref'];
let sequence = 1;
let finished = false;
const shellQuote = value => "'" + value.replace(/'/g, "'\"'\"'") + "'";
while (!finished && sequence <= 300) {
  const requestPath = rpcPath + '/request' + String(sequence).padStart(4,'0') + '.json';
  const sizeRun = await tools.exec_command({cmd:'python -c '+shellQuote('from pathlib import Path; print(Path('+JSON.stringify(requestPath)+').stat().st_size)'),max_output_tokens:1000});
  if (sizeRun.exit_code !== 0) throw new Error('Expected bounded worker request absent: '+sizeRun.output);
  const size = Number(sizeRun.output.trim());
  if (!Number.isInteger(size) || size < 1 || size > 600000) throw new Error('Request size exceeds engineering bound');
  let requestText = '';
  for (let offset=0; offset<size; offset+=48000) {
    const code = 'from pathlib import Path; import json; print(json.dumps(Path('+JSON.stringify(requestPath)+').read_text()['+offset+':'+(offset+48000)+']))';
    const chunk = await tools.exec_command({cmd:'python -c '+shellQuote(code),max_output_tokens:50000});
    if (chunk.exit_code!==0) throw new Error('Request read failed');
    requestText += JSON.parse(chunk.output.trim());
  }
  if (requestText.length !== size) throw new Error('Request framing differs');
  const request = JSON.parse(requestText);
  const {method,params,id} = request;
  if (id!==sequence || !allowed.includes(method)) throw new Error('Broker sequence/method changed');
  if (method==='fetch') {
    if (!params.url.startsWith('https://api.github.com/repos/'+repo+'/git/')) throw new Error('Unapproved read destination');
  } else if (params.repository_full_name!==repo) throw new Error('Repository changed');
  if (method==='update_ref' && (params.branch_name!==branch || params.force!==false)) throw new Error('Unsafe branch update');
  if (method==='create_tree' && params.tree_elements.some(e=>!e.path.startsWith(prefix)||e.path.split('/').some(p=>p==='..'||p==='.'||p==='')||e.mode!=='100644'||e.type!=='blob'||'content' in e)) throw new Error('Unsafe evidence tree');
  let reply;
  try {
    const response = await tools['mcp__codex_apps__github_'+method](params);
    if (response.isError) throw new Error('GitHub tool returned isError');
    const result = method==='fetch' ? JSON.parse(response.structuredContent.content) : response.structuredContent;
    if (!result || typeof result!=='object') throw new Error('Structured GitHub result absent');
    reply={id,ok:true,result};
  } catch(error) { reply={id,ok:false,error:String(error),automatic_retry:false}; }
  const responsePath=rpcPath+'/response'+String(sequence).padStart(4,'0')+'.json';
  const patch='*** Begin Patch\n*** Add File: '+responsePath+'.tmp\n+'+JSON.stringify(reply)+'\n*** End Patch';
  const written=await tools.apply_patch(patch);
  const moved=await tools.exec_command({cmd:'python -c '+shellQuote('from pathlib import Path; p=Path('+JSON.stringify(responsePath)+'); assert not p.exists(); Path(str(p)+".tmp").rename(p)'),max_output_tokens:1000});
  if (moved.exit_code!==0) throw new Error('Atomic tool response handoff failed');
  let output=await tools.write_stdin({session_id:sessionId,chars:'',yield_time_ms:1000,max_output_tokens:2000});
  while (output.session_id && !output.output.includes('RPC '+(sequence+1))) {
    if (output.output.trim()) notify({worker_output:output.output});
    output=await tools.write_stdin({session_id:sessionId,chars:'',yield_time_ms:1000,max_output_tokens:2000});
  }
  if (!output.session_id) {finished=true;notify({worker_exit_code:output.exit_code,output:output.output});}
  if (sequence%10===0) {notify({git_tool_requests_completed:sequence});await yield_control();}
  if (!reply.ok && !finished) throw new Error('Worker has not stopped after transport failure');
  sequence++;
}
if (!finished) throw new Error('Broker request cap reached without completion');
return {requests:sequence-1,worker_finished:finished};
