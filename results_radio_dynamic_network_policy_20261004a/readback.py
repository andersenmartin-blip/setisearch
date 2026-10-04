"""One admitted, bounded public-Git metadata read under a new network policy."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import network_policy as n

REPOSITORY='andersenmartin-blip/setisearch'
BRANCH='m43-support-qualification'
URL='https://github.com/'+REPOSITORY+'.git'
SELECTED_PATHS={'results_radio_contents_cas_probe_20261004c/scope.json',
    'results_radio_scientific_execution_prospective_20261003a/scientific_store.py'}


def directory(path):
    need=n.need;need(type(path) is str and path.startswith('/') and path==os.path.normpath(path),
                     'canonical absolute directory required')
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
    fd=os.open('/',flags)
    try:
        for name in path.split('/')[1:]:
            need(name not in ('','.','..'),'ordinary directory component required')
            nxt=os.open(name,flags,dir_fd=fd);os.close(fd);fd=nxt
        return fd
    except BaseException:
        os.close(fd);raise


def write(fd,name,raw):
    out=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o400,dir_fd=fd)
    try:
        offset=0
        while offset<len(raw):
            count=os.write(out,raw[offset:]);n.need(count>0,'short original evidence write');offset+=count
        os.fsync(out)
    finally:os.close(out)
    os.fsync(fd)


def storage(root):
    logical=allocated=count=0
    for current,dirs,files in os.walk(root,followlinks=False):
        for name in ['.',*files]:
            path=Path(current)/name;s=path.lstat()
            n.need(not stat.S_ISLNK(s.st_mode),'symlink in original storage refused')
            n.need(stat.S_ISDIR(s.st_mode) if name=='.' else stat.S_ISREG(s.st_mode),
                   'ordinary original storage required')
            logical+=s.st_size;allocated+=s.st_blocks*512;count+=name!='.'
        n.need(all(not (Path(current)/name).is_symlink() for name in dirs),
               'symlink directory in original storage refused')
    return {'logical_bytes_including_directories':logical,
            'allocated_bytes_including_directories':allocated,'files':count}


def load_retention(pin):
    n.file_pin(pin)
    spec=importlib.util.spec_from_file_location('network_selected_retention',pin['path'])
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


def prefix(scope):
    cert=scope['policy']['trust_file']['path']
    pairs=('core.hooksPath=/dev/null','credential.helper=','http.followRedirects=false',
           'http.sslVerify=true','http.sslCAInfo='+cert,'protocol.file.allow=never',
           'protocol.ext.allow=never','maintenance.auto=false','gc.auto=0',
           'fetch.writeCommitGraph=false','init.defaultBranch=metadata')
    return [scope['runtime_pins']['git']['path'],*sum((['-c',p] for p in pairs),[]),
            '--git-dir='+scope['artifact_root']['path']+'/sandbox.git']


def route(scope,publication):
    root=scope['artifact_root']['path'];paths=list(scope['selected_files'])
    return [('init',['init','--bare','--template='+root+'/empty-template',root+'/sandbox.git']),
            ('fetch',['fetch','--no-tags','--no-recurse-submodules','--no-auto-maintenance',URL,
                      'refs/heads/'+BRANCH+':refs/remotes/observed/'+BRANCH]),
            ('head',['rev-parse','refs/remotes/observed/'+BRANCH]),
            ('commit',['cat-file','-p',publication]),
            ('members',['ls-tree','-r','--full-tree',publication,'--',*paths]),
            *[(f'blob{i}',['cat-file','blob',publication+':'+path]) for i,path in enumerate(paths)]]


def validate_git(scope,publication,outputs):
    n.need(outputs['head'].decode('ascii').strip()==publication,'fetched public head differs')
    raw=outputs['commit']
    n.need(hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==publication,
           'intrinsic public commit identity differs')
    header=raw.split(b'\n\n',1)[0].splitlines()
    parents=[x[7:].decode('ascii') for x in header if x.startswith(b'parent ')]
    trees=[x[5:].decode('ascii') for x in header if x.startswith(b'tree ')]
    n.need(parents==[scope['base_commit']] and len(trees)==1 and re.fullmatch('[0-9a-f]{40}',trees[0]),
           'publication sole parent/tree differs')
    entries={}
    for line in outputs['members'].decode('ascii').splitlines():
        meta,path=line.split('\t',1);mode,kind,blob=meta.split()
        n.need(path in scope['selected_files'] and path not in entries and mode=='100644' and kind=='blob',
               'exact regular selected member required');entries[path]=blob
    n.need(set(entries)==set(scope['selected_files']),'complete selected member inventory differs')
    selected={}
    for i,(path,expected) in enumerate(scope['selected_files'].items()):
        raw=outputs['blob'+str(i)];blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        n.need(n.pin(raw)==expected['raw_pin'] and blob==expected['git_blob']==entries[path],
               'selected public blob bytes/identity differ')
        selected[path]={'raw_pin':n.pin(raw),'git_blob':blob}
    return {'commit':publication,'parent':parents[0],'tree':trees[0],'selected_files':selected}


def execute(scope,scope_hash,publication,*,capture=None,source=None):
    n.need(scope['domain']=='public-git-metadata-engineering'
           and scope['scientific_execution_authorized'] is False
           and scope['repository']==REPOSITORY and scope['branch']==BRANCH
           and scope['retry_or_resume_allowed'] is False and scope['allocated_invocations']==1,
           'fixed metadata-only single scope required')
    n.need(set(scope['selected_files'])==SELECTED_PATHS
           and scope['prior_scope_path']=='results_radio_contents_cas_probe_20261004c/scope.json',
           'only two explicit public metadata/code files permitted')
    n.need(re.fullmatch('[0-9a-f]{40}',publication) and re.fullmatch('[0-9a-f]{64}',scope_hash),
           'exact publication/scope identities required')
    for pin in [*scope['code_pins'].values(),*scope['runtime_pins'].values(),scope['retention_pin']]:n.file_pin(pin)
    retained=load_retention(scope['retention_pin']);actual=retained.capture if capture is None else capture
    root=scope['artifact_root'];fd=directory(root['path']);current=os.fstat(fd)
    try:
        n.need((current.st_dev,current.st_ino)==(root['device'],root['inode']) and not os.listdir(fd),
               'original pinned empty root required; no replay')
        marker={'schema':'radio-dynamic-network-single-admission-v1','scope_sha256':scope_hash,
                'publication':publication,'identity':scope['identity'],
                'original_root_device':current.st_dev,'original_root_inode':current.st_ino,
                'scientific_execution_authorized':False,'observed_epoch_ns':time.time_ns()}
        write(fd,'attempt-started.json',n.canonical(marker))
        started=time.monotonic()
        state={'schema':'radio-dynamic-network-readback-terminal-v1','status':'CLOSED_FAILED',
               'identity':scope['identity'],'scope_sha256':scope_hash,'publication':publication,
               'operations':[],'scientific_execution_authorized':False,
               'qualified_atomic_expected_revision_cas':False,'complete_hosted_runtime_qualified':False,
               'actual_telescope_reads':0,'identity_permanently_spent':True,'automatic_retry_or_resume':False}
        try:
            env,observation=n.build(scope['policy'],source);state['network_observation']=observation
            obj=scope['object_source'];objfd=directory(obj['path'])
            try:n.need((os.fstat(objfd).st_dev,os.fstat(objfd).st_ino)==(obj['device'],obj['inode']),
                       'selected shared public Git object directory identity differs')
            finally:os.close(objfd)
            os.mkdir('empty-template',0o700,dir_fd=fd)
            outputs={};base=prefix(scope)
            for i,(label,args) in enumerate(route(scope,publication)):
                remaining=scope['helper_deadline_seconds']-(time.monotonic()-started)
                n.need(remaining>0 and i<scope['max_git_processes'],'whole helper admission deadline/process cap')
                destination=root['path']+'/op'+str(i)+'-'+label
                before=time.monotonic_ns()
                result=actual(base+args,destination=destination,repository_root=scope['repository_root'],
                              protected_roots=scope['protected_roots'],stdout_cap=65536,stderr_cap=8192,
                              timeout_seconds=min(remaining,scope['per_operation_timeout_seconds']),env=env)
                record=result.record()
                row={'ordinal':i,'label':label,'before_monotonic_ns':before,
                     'after_monotonic_ns':time.monotonic_ns(),'capture':record}
                state['operations'].append(row);write(fd,'capture'+str(i)+'.json',result.payload)
                n.need(record['strictly_completed'] is True and record['returncode']==0 and record['child_reaped'] is True,
                       'native process/capture failed: '+record['process_status'])
                for stream in ('stdout','stderr'):
                    item=record['streams'][stream]
                    n.need(item['full_stream_retained'] is True and item['file_write_complete'] is True
                           and item['file_fsync_complete'] is True,'full bounded output not retained')
                outputs[label]=retained.reconstruct_raw(record['streams']['stdout']['reconstruction'])
                if label=='init':
                    info=directory(root['path']+'/sandbox.git/objects/info')
                    try:write(info,'alternates',(obj['path']+'\n').encode('ascii'))
                    finally:os.close(info)
                usage=storage(root['path']);state['last_operation_storage']=usage
                n.need(max(usage['logical_bytes_including_directories'],usage['allocated_bytes_including_directories'])
                       +scope['terminal_reserve_bytes']+4096<=scope['retained_original_evidence_ceiling_bytes'],
                       'original storage cap with terminal reserve exceeded')
            state['public_git_proof']=validate_git(scope,publication,outputs)
            old=json.loads(outputs['blob'+str(list(scope['selected_files']).index(scope['prior_scope_path']))])
            differences=[name for name in n.PROXIES if observation['proxies'][name]['sha256']
                         !=old['network_environment_pins'][name]['sha256']]
            n.need(differences==list(n.PROXIES),'all six prior static proxy hashes must actually differ')
            state['changed_prior_static_proxy_names']=differences
            for pin in [*scope['code_pins'].values(),*scope['runtime_pins'].values(),scope['retention_pin']]:n.file_pin(pin)
            n.need(time.monotonic()-started<scope['helper_deadline_seconds'],'whole helper deadline exceeded')
            state['status']='OBSERVED_DYNAMIC_LOOPBACK_GIT_METADATA'
        except (ValueError,OSError,UnicodeError,KeyError) as error:
            state['error']=type(error).__name__+': '+str(error)
        state['elapsed_milliseconds']=int((time.monotonic()-started)*1000)
        state['git_processes']=len(state['operations']);raw=n.canonical(state)
        n.need(len(raw)<=scope['terminal_reserve_bytes'],'terminal reserve exceeded')
        write(fd,'terminal.json',raw)
        usage=storage(root['path'])
        n.need(max(usage['logical_bytes_including_directories'],usage['allocated_bytes_including_directories'])
               <=scope['retained_original_evidence_ceiling_bytes'],'final original storage cap exceeded')
        return state
    finally:os.close(fd)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('scope_path');parser.add_argument('scope_sha256');parser.add_argument('publication')
    args=parser.parse_args();raw=Path(args.scope_path).read_bytes()
    n.need(n.pin(raw)['sha256']==args.scope_sha256 and len(raw)<=65536,'external scope pin differs')
    scope=json.loads(raw);n.need(n.canonical(scope)==raw,'canonical scope required')
    result=execute(scope,args.scope_sha256,args.publication)
    sys.stdout.buffer.write(n.canonical({'status':result['status'],'identity':result['identity'],
          'git_processes':result['git_processes'],'elapsed_milliseconds':result['elapsed_milliseconds'],
          'terminal_pin':n.pin(n.canonical(result)),'scientific_execution_authorized':False}))
    return 0 if result['status']=='OBSERVED_DYNAMIC_LOOPBACK_GIT_METADATA' else 1


if __name__=='__main__':raise SystemExit(main())
