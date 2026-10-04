"""Independent selected transcript checks; no scientific/runtime certificate."""
import base64
import hashlib
import json
import re


def need(value,reason):
    if not value:raise ValueError(reason)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()+b'\n'


def pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def load(raw,expected):
    need(type(raw) is bytes and len(raw)<=1024*1024 and pin(raw)==expected,'external complete raw pin differs')
    def pairs(items):
        result={}
        for key,value in items:
            need(key not in result,'duplicate JSON member');result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
    need(canonical(value)==raw,'canonical original JSON required');return value


def review(scope_raw,scope_pin,terminal_raw,terminal_pin,*,expected_publication):
    scope=load(scope_raw,scope_pin);terminal=load(terminal_raw,terminal_pin)
    need(set(scope['selected_files'])=={'results_radio_contents_cas_probe_20261004c/scope.json',
         'results_radio_scientific_execution_prospective_20261003a/scientific_store.py'},
         'only two fixed metadata/code paths permitted')
    need(scope['domain']=='public-git-metadata-engineering' and scope['scientific_execution_authorized'] is False
         and scope['repository']=='andersenmartin-blip/setisearch' and scope['branch']=='m43-support-qualification'
         and terminal['scientific_execution_authorized'] is False
         and terminal['qualified_atomic_expected_revision_cas'] is False
         and terminal['complete_hosted_runtime_qualified'] is False and terminal['actual_telescope_reads']==0,
         'no scientific/complete service authority permitted')
    need(terminal['status']=='OBSERVED_DYNAMIC_LOOPBACK_GIT_METADATA'
         and terminal['identity']==scope['identity'] and terminal['scope_sha256']==scope_pin['sha256']
         and terminal['publication']==expected_publication and terminal['identity_permanently_spent'] is True
         and terminal['automatic_retry_or_resume'] is False,'complete closed original observation required')
    need(type(terminal['elapsed_milliseconds']) is int and 0<=terminal['elapsed_milliseconds']<scope['helper_deadline_seconds']*1000,
         'helper deadline differs')
    policy=scope['policy'];obs=terminal['network_observation']
    need(obs['schema']=='radio-dynamic-loopback-environment-observation-v1'
         and obs['policy_pin']==pin(canonical(policy)) and obs['trust_file']==policy['trust_file']
         and obs['fixed_environment']==policy['fixed_environment'] and obs['git_exec_path']==policy['git_exec_path']
         and obs['raw_proxy_strings_published'] is False and obs['unrelated_environment_inherited'] is False
         and obs['scientific_execution_authorized'] is False,'complete selected environment proof differs')
    names=('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy')
    need(policy['proxy_names']==list(names) and set(obs['proxies'])==set(names),'exact six local proxies required')
    for name in names:
        value=obs['proxies'][name];scheme='socks5h' if name.lower()=='all_proxy' else 'http'
        need(set(value)=={'scheme','host','port','bytes','sha256'} and value['scheme']==scheme
             and value['host']=='127.0.0.1' and type(value['port']) is int and 1024<=value['port']<=65535,
             'canonical permitted endpoint descriptor differs')
        raw=(scheme+'://127.0.0.1:'+str(value['port'])).encode()
        need(pin(raw)=={k:value[k] for k in ('bytes','sha256')},'actual endpoint value hash differs')
    for a,b in (('HTTP_PROXY','http_proxy'),('HTTPS_PROXY','https_proxy'),('ALL_PROXY','all_proxy'),('HTTP_PROXY','HTTPS_PROXY')):
        need(obs['proxies'][a]==obs['proxies'][b],'case/protocol endpoint equality differs')
    need(obs['no_proxy']=={name:policy['no_proxy_pin'] for name in ('NO_PROXY','no_proxy')},'frozen bypass pins differ')
    need(obs['actual_environment_names']==sorted([*policy['fixed_environment'],'GIT_EXEC_PATH',*names,'NO_PROXY','no_proxy','SSL_CERT_FILE']),
         'unexpected inherited child environment name')
    envpin=obs['actual_environment_pin']
    need(type(envpin['bytes']) is int and 0<envpin['bytes']<4096
         and re.fullmatch('[0-9a-f]{64}',envpin['sha256']),'bounded whole child-environment observation pin required')
    root=scope['artifact_root']['path'];cert=policy['trust_file']['path']
    configs=('core.hooksPath=/dev/null','credential.helper=','http.followRedirects=false',
       'http.sslVerify=true','http.sslCAInfo='+cert,'protocol.file.allow=never','protocol.ext.allow=never',
       'maintenance.auto=false','gc.auto=0','fetch.writeCommitGraph=false','init.defaultBranch=metadata')
    prefix=[scope['runtime_pins']['git']['path'],*sum((['-c',p] for p in configs),[]),'--git-dir='+root+'/sandbox.git']
    paths=list(scope['selected_files']);publication=expected_publication
    requests=[('init',['init','--bare','--template='+root+'/empty-template',root+'/sandbox.git']),
       ('fetch',['fetch','--no-tags','--no-recurse-submodules','--no-auto-maintenance','https://github.com/andersenmartin-blip/setisearch.git',
                 'refs/heads/m43-support-qualification:refs/remotes/observed/m43-support-qualification']),
       ('head',['rev-parse','refs/remotes/observed/m43-support-qualification']),('commit',['cat-file','-p',publication]),
       ('members',['ls-tree','-r','--full-tree',publication,'--',*paths]),
       *[(f'blob{i}',['cat-file','blob',publication+':'+path]) for i,path in enumerate(paths)]]
    rows=terminal['operations'];need(len(rows)==terminal['git_processes']==7<=scope['max_git_processes'],
                                    'exact seven process records required')
    outputs={};previous=0
    for i,(row,(label,args)) in enumerate(zip(rows,requests,strict=True)):
        need(row['ordinal']==i and row['label']==label
             and type(row['before_monotonic_ns']) is int and type(row['after_monotonic_ns']) is int
             and previous<=row['before_monotonic_ns']<=row['after_monotonic_ns'],'ordered process/clock differs')
        previous=row['after_monotonic_ns'];record=row['capture']
        need(record['argv']==prefix+args and record['process_status']=='EXIT_ZERO'
             and type(record['returncode']) is int and record['returncode']==0
             and record['child_reaped'] is True and record['strictly_completed'] is True
             and record['automatic_retry'] is False and record['overwrites_performed'] is False
             and record['whole_descendant_lifetime_qualified'] is False
             and record['scientific_execution_authorized'] is False
             and record['engineering_control_qualified'] is False and record['persistence_errors']==[]
             and record['timed_out'] is False and record['output_limit_exceeded'] is False
             and record['launch_error'] is None and record['capture_error'] is None,
             'exact completed fixed native capture required')
        need(0<record['timeout_seconds']<=scope['per_operation_timeout_seconds']
             and record['destination']['path']==root+'/op'+str(i)+'-'+label
             and record['destination']['exclusively_created'] is True
             and record['disposition_write_complete'] is True and record['disposition_fsync_complete'] is True,
             'exclusive bounded capture/persistence differs')
        first={k:v for k,v in record.items() if k not in ('disposition_file_pin','disposition_write_complete',
              'disposition_fsync_complete','disposition_first_payload_sha256')}
        first_raw=canonical(first)
        need(record['disposition_first_payload_sha256']==pin(first_raw)['sha256']
             and {k:record['disposition_file_pin'][k] for k in ('bytes','sha256')}==pin(first_raw),
             'first immutable disposition pin differs')
        for stream,cap in (('stdout',65536),('stderr',8192)):
            item=record['streams'][stream];proof=item['reconstruction']
            raw=base64.b64decode(proof['data'],validate=True)
            need(proof['encoding']=='base64' and pin(raw)=={k:proof[k] for k in ('bytes','sha256')}
                 and item['cap_bytes']==cap and type(item['observed_bytes']) is int
                 and item['observed_bytes']==len(raw)<=cap and item['eof_observed'] is True
                 and item['truncated'] is False and item['full_stream_retained'] is True
                 and item['file_write_complete'] is True and item['file_fsync_complete'] is True
                 and {k:item['file_pin'][k] for k in ('bytes','sha256')}==pin(raw),
                 'complete bounded raw stream/persistence differs')
            if stream=='stdout':outputs[label]=raw
    need(outputs['head'].decode().strip()==publication,'actual fetched head differs')
    commit=outputs['commit'];oid=hashlib.sha1(b'commit '+str(len(commit)).encode()+b'\0'+commit).hexdigest()
    header=commit.split(b'\n\n',1)[0].splitlines();parents=[x[7:].decode() for x in header if x.startswith(b'parent ')]
    trees=[x[5:].decode() for x in header if x.startswith(b'tree ')]
    need(oid==publication and parents==[scope['base_commit']] and len(trees)==1
         and re.fullmatch('[0-9a-f]{40}',trees[0]),'intrinsic Git commit/parent/tree differs')
    entries={}
    for line in outputs['members'].decode().splitlines():
        meta,path=line.split('\t',1);mode,kind,sha=meta.split()
        need(mode=='100644' and kind=='blob' and path in paths and path not in entries,'actual selected member differs')
        entries[path]=sha
    need(set(entries)==set(paths),'actual complete member inventory differs')
    selected={}
    for i,(path,expected) in enumerate(scope['selected_files'].items()):
        raw=outputs['blob'+str(i)];sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        need(pin(raw)==expected['raw_pin'] and sha==expected['git_blob']==entries[path],'actual immutable blob differs')
        selected[path]={'raw_pin':pin(raw),'git_blob':sha}
    need(terminal['public_git_proof']=={'commit':publication,'parent':parents[0],'tree':trees[0],'selected_files':selected},
         'returned Git summary differs from original raw transcript')
    old=json.loads(outputs['blob'+str(paths.index(scope['prior_scope_path']))])
    changed=[name for name in names if obs['proxies'][name]['sha256']!=old['network_environment_pins'][name]['sha256']]
    need(changed==list(names)==terminal['changed_prior_static_proxy_names'],'six actual prior static proxy changes required')
    return {'schema':'radio-dynamic-network-independent-review-v1','status':'SELECTED_TRANSPORT_OBSERVATION_VERIFIED',
            'identity':scope['identity'],'publication':publication,'native_processes':7,
            'changed_prior_static_proxy_names':changed,'selected_files':selected,
            'scientific_execution_authorized':False,'qualified_atomic_expected_revision_cas':False,
            'complete_hosted_runtime_qualified':False}
