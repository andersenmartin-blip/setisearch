(async function ({tools, scope, artifactRoot, freezePublicCommit, scopeSha256}) {
  // Visible connector-boundary observation only. No raw HTTP/RSS/SDK certificate.
  // This own, pinned source is loaded only after full prospective Git readback.
  const repo = scope.repository;
  const branch = scope.branch;
  const api = 'https://api.github.com/repos/' + repo;
  const state = {schema:'radio-contents-cas-visible-probe-state-v1',
    probe_identity:scope.probe_identity, domain:'synthetic-service-probe-only',
    status:'CLOSED_FAILED', operations:[], facts:{},
    scientific_execution_authorized:false, actual_telescope_reads:0,
    qualified_atomic_expected_revision_cas:false, complete_hosted_transport_qualified:false,
    git_readbacks:[]};
  const started = Date.now();
  let responseBytes=0;
  const ascii64 = value => {
    if (!/^[\x00-\x7f]*$/.test(value)) throw Error('ASCII fixture only');
    const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    let output='';
    for(let i=0;i<value.length;i+=3) {
      const a=value.charCodeAt(i), b=value.charCodeAt(i+1)||0, c=value.charCodeAt(i+2)||0;
      output+=alphabet[a>>2]+alphabet[((a&3)<<4)|(b>>4)]+(i+1<value.length?alphabet[((b&15)<<2)|(c>>6)]:'=')+(i+2<value.length?alphabet[c&63]:'=');
    }
    return output;
  };
  const canonical = value => JSON.stringify(Object.fromEntries(Object.entries(value).sort(([a],[b])=>a<b?-1:a>b?1:0)))+'\n';
  const need=(condition, reason)=>{if(!condition)throw Error(reason);};
  const ok=result=>result && !result.isError && !result.call_error;
  const body=result=>{
    need(ok(result),'unexpected connector error');
    const value=result.structuredContent;
    need(value && typeof value==='object','structured tool result required');
    return typeof value.content==='string' && value.encoding!=='base64' ? JSON.parse(value.content) : value;
  };
  const errorStatus=result=>{
    if(ok(result))return null;
    const raw=JSON.stringify(result);
    const got=raw.match(/(?:HTTP\s*|status(?:_code)?["'\s:]+|\b)(404|409)\b/);
    return got?Number(got[1]):null;
  };
  const commit=result=>{
    const value=body(result); const sha=value.commit_sha||value.sha;
    need(typeof sha==='string' && /^[0-9a-f]{40}$/.test(sha),'exact returned commit SHA required');
    return sha;
  };
  const persist=async(name,value)=>{
    const raw=JSON.stringify(value)+'\n';
    await tools.apply_patch('*** Begin Patch\n*** Add File: '+artifactRoot+'/'+name+'\n+'+raw.trimEnd()+'\n*** End Patch');
  };
  const call=async(label,tool,args)=>{
    need(state.operations.length<scope.max_visible_connector_calls,'call budget exhausted');
    need(Date.now()-started<scope.admission_deadline_milliseconds,'visible admission deadline exceeded');
    const ordinal=state.operations.length, before=Date.now(); let result;
    try {result=await tools[tool](args);} catch(error) {result={call_error:String(error)};}
    const after=Date.now(), serialized=JSON.stringify(result);
    responseBytes+=serialized.length;
    const row={ordinal,label,tool,args,before_epoch_milliseconds:before,
      after_epoch_milliseconds:after,serialized_response_characters:serialized.length,result};
    state.operations.push(row);
    await persist('op-'+String(ordinal).padStart(2,'0')+'-'+label+'.json',row);
    need(after>=before && after-started<scope.admission_deadline_milliseconds,'visible clock/deadline failed');
    need(responseBytes<=scope.serialized_response_ceiling_characters,'serialized response ceiling exceeded');
    return result;
  };
  const get=(label,url)=>call(label,'mcp__codex_apps__github_fetch',{url});
  const head=(label)=>get(label,api+'/branches/'+branch);
  const rawContents=(label,path,revision)=>get(label,api+'/contents/'+path+'?ref='+revision);
  const verifyContents=(result,path,revision,raw)=>{
    need(ok(result),'normalized contents read failed');
    const value=result.structuredContent;
    const url=api+'/contents/'+path+'?ref='+revision;
    need(value.content===raw && value.url===url && value.title===path.split('/').at(-1)
      && value.structuredContent.content===raw && value.structuredContent.display_url===url,
      'complete normalized immutable contents mismatch');
    return raw;
  };
  const nativeReadback=async(phase,revision,parent)=>{
    need(Date.now()-started<scope.admission_deadline_milliseconds,'native readback admission deadline exhausted');
    const sq=value=>"'"+value.replace(/'/g,"'\\''")+"'";
    const helper=scope.code_pins['git_probe_readback.py'].path;
    const args={cmd:[scope.python_executable.path,helper,scope.scope_path,scopeSha256,phase,revision,parent].map(sq).join(' '),
      workdir:scope.repository_root,max_output_tokens:20000,yield_time_ms:30000};
    const before=Date.now();let response;
    try {response=await tools.exec_command(args);}catch(error){response={call_error:String(error)};}
    // A returned session would require a separate observer/protocol: close here.
    const row={phase,args,before_epoch_milliseconds:before,after_epoch_milliseconds:Date.now(),response};
    state.git_readbacks.push(row);await persist('git-'+phase+'.json',row);
    need(response.exit_code===0 && !response.session_id,'native command not completed within selected call; no polling/retry');
    const checked=JSON.parse(response.output);
    need(checked.status==='SELECTED_GIT_BYTES_VERIFIED' && checked.expected_commit===revision
      && checked.expected_parent===parent && checked.phase===phase && checked.git_processes<=6
      && checked.scientific_execution_authorized===false,'native immutable Git proof failed');
    need(Date.now()-started<scope.admission_deadline_milliseconds,'whole visible deadline exceeded after native readback');
    return checked;
  };
  const verifyCommit=(result,id,parent)=>{
    const value=body(result);
    need(value.sha===id && value.parents.length===1 && value.parents[0].sha===parent,
      'immutable commit exact parent mismatch');
  };
  try {
    need(scope.domain==='synthetic-service-probe-only' && scope.scientific_execution_authorized===false
      && /^radio-contents-cas-probe-20261004b$/.test(branch), 'fixed synthetic scope only');
    const absence=await head('branch_absence');
    need(errorStatus(absence)===404,'fresh probe branch absence not proven; no mutation');
    const made=await call('branch_create','mcp__codex_apps__github_create_branch',
      {repository_full_name:repo,branch_name:branch,sha:scope.base_commit});
    need(ok(made),'branch creation failed; never retry');
    need(body(await head('branch_initial_read')).commit.sha===scope.base_commit,'initial branch differs');
    const initial=scope.initial_record_raw, path=scope.ledger_path;
    const r0=commit(await call('ledger_create','mcp__codex_apps__github_create_file',
      {repository_full_name:repo,branch,path,content:initial,message:'Create synthetic file-CAS probe initial record'}));
    state.facts.initial_commit=r0;
    verifyCommit(await get('ledger_commit_read',api+'/git/commits/'+r0),r0,scope.base_commit);
    verifyContents(await rawContents('ledger_initial_read',path,r0),path,r0,initial);
    const native0=await nativeReadback('initial',r0,scope.base_commit);
    need(native0.selected_files[path].raw_ascii===initial,'initial native Git bytes differ');
    const b0=native0.selected_files[path].git_blob;
    state.facts.initial_blob=b0;
    const r1=commit(await call('interference_create','mcp__codex_apps__github_create_file',
      {repository_full_name:repo,branch,path:scope.interference_path,content:scope.interference_raw,
        message:'Advance synthetic probe branch without changing ledger file'}));
    state.facts.interference_commit=r1;
    verifyCommit(await get('interference_commit_read',api+'/git/commits/'+r1),r1,r0);
    verifyContents(await rawContents('ledger_after_interference_read',path,r1),path,r1,initial);
    const native1=await nativeReadback('interference',r1,r0);
    need(native1.selected_files[path].raw_ascii===initial && native1.selected_files[path].git_blob===b0
      && native1.selected_files[scope.interference_path].raw_ascii===scope.interference_raw,
      'interference native Git file identity differs');
    need(body(await head('branch_after_interference_read')).commit.sha===r1,'interference branch head differs');
    const update=canonical({schema:'radio-contents-cas-probe-record-v1',domain:scope.domain,
      probe_identity:scope.probe_identity,revision:1,expected_branch_revision:r0,
      scientific_execution_authorized:false});
    state.facts.accepted_record_raw=update;
    const updated=await call('ledger_update','mcp__codex_apps__github_update_file',
      {repository_full_name:repo,branch,path,sha:b0,content:update,
        message:'Probe current file blob with stale observed branch revision'});
    const r2=commit(updated); state.facts.updated_commit=r2;
    verifyCommit(await get('ledger_update_commit_read',api+'/git/commits/'+r2),r2,r1);
    const rejected=canonical({schema:'radio-contents-cas-probe-record-v1',domain:scope.domain,
      probe_identity:scope.probe_identity,revision:2,expected_branch_revision:r2,
      scientific_execution_authorized:false});
    state.facts.rejected_record_raw=rejected;
    const stale=await call('stale_blob_update','mcp__codex_apps__github_update_file',
      {repository_full_name:repo,branch,path,sha:b0,content:rejected,
        message:'Negative probe of stale file blob; expected conflict'});
    need(errorStatus(stale)===409,'stale blob was not positively observed as conflict');
    state.facts.stale_blob_status=409;
    need(body(await head('branch_final_read')).commit.sha===r2,'negative probe changed branch');
    verifyContents(await rawContents('ledger_final_read',path,r2),path,r2,update);
    verifyContents(await rawContents('interference_final_read',scope.interference_path,r2),scope.interference_path,r2,scope.interference_raw);
    const native2=await nativeReadback('final',r2,r1);
    need(native2.selected_files[path].raw_ascii===update
      && native2.selected_files[scope.interference_path].raw_ascii===scope.interference_raw,
      'final native Git file bytes differ');
    const b1=native2.selected_files[path].git_blob;
    state.facts.updated_blob=b1;
    need(b1!==b0,'positive replacement did not change blob identity');
    const science=body(await get('science_head_final_read',api+'/branches/m43-support-qualification'));
    need(science.commit.sha===freezePublicCommit,'primary branch moved during probe');
    state.status='OBSERVED_FILE_BLOB_CAS_ONLY';
  } catch(error) {state.error=String(error);}
  state.visible_connector_calls=state.operations.length;
  state.serialized_response_characters=responseBytes;
  state.elapsed_visible_milliseconds=Date.now()-started;
  state.hidden_http_bytes_measured=false;
  state.hidden_sdk_retries_measured=false;
  state.interruption_of_hung_connector_guaranteed=false;
  state.automatic_retry_or_resume=false;
  state.probe_identity_permanently_spent=true;
  await persist('terminal.json',state);
  return state;
})
