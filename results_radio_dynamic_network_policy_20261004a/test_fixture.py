"""Explicit synthetic Git/capture fixtures; never actual transport evidence."""
import base64
import hashlib
import json
from pathlib import Path
import types
import network_policy as n
import readback as h
from test_network_policy import fixture as policy_fixture


def file_pin(path):
    path=Path(path).resolve()
    return {'path':str(path),'mode':path.stat().st_mode&0o777,**n.pin(path.read_bytes())}


def setup(root):
    root=Path(root);policy,source=policy_fixture(root);art=root/'original';art.mkdir();st=art.stat()
    objects=root/'objects';objects.mkdir();obj=objects.stat()
    fake_git=root/'frozen-git';fake_git.write_bytes(b'synthetic stub never launched\n')
    paths=sorted(h.SELECTED_PATHS);old=n.canonical({'network_environment_pins':{name:{'sha256':'0'*64} for name in n.PROXIES}})
    raws={paths[0]:old,paths[1]:b'# synthetic store bytes only\n'}
    blob=lambda raw:hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    selected={p:{'raw_pin':n.pin(raw),'git_blob':blob(raw)} for p,raw in raws.items()}
    parent='0'*40;tree='6'*40
    commit=('tree '+tree+'\nparent '+parent+'\nauthor Fixture <fixture@example.invalid> 0 +0000\ncommitter Fixture <fixture@example.invalid> 0 +0000\n\nfixture\n').encode()
    publication=hashlib.sha1(b'commit '+str(len(commit)).encode()+b'\0'+commit).hexdigest()
    scope={'schema':'radio-dynamic-network-prospective-scope-v1','domain':'public-git-metadata-engineering',
      'scientific_execution_authorized':False,'repository':h.REPOSITORY,'branch':h.BRANCH,
      'allocated_invocations':1,'retry_or_resume_allowed':False,'identity':'a'*64,'base_commit':parent,
      'repository_root':str(root/'repository'),'artifact_root':{'path':str(art),'device':st.st_dev,'inode':st.st_ino},
      'protected_roots':[],'policy':policy,'runtime_pins':{'git':file_pin(fake_git),'trust_file':policy['trust_file']},
      'code_pins':{'network_policy.py':file_pin(Path(n.__file__)),'readback.py':file_pin(Path(h.__file__))},
      'retention_pin':file_pin(Path(h.__file__).parent.parent/'results_radio_native_v3_execution_preparation_20261003f/failure_output_retention.py'),
      'object_source':{'path':str(objects),'device':obj.st_dev,'inode':obj.st_ino},
      'selected_files':selected,'prior_scope_path':paths[0],'helper_deadline_seconds':25,
      'per_operation_timeout_seconds':20,'max_git_processes':7,'terminal_reserve_bytes':524288,
      'retained_original_evidence_ceiling_bytes':4*1024**2}
    (root/'repository').mkdir()
    outputs={'init':b'Initialized fixture bare repository\n','fetch':b'',
      'head':(publication+'\n').encode(),'commit':commit,
      'members':''.join('100644 blob '+v['git_blob']+'\t'+p+'\n' for p,v in selected.items()).encode(),
      **{'blob'+str(i):raws[p] for i,p in enumerate(paths)}}
    return scope,source,publication,outputs


def capture_stub(scope,outputs,*,failure=None,on_call=None):
    calls=[];labels=[label for label,_ in h.route(scope,'0'*40)]
    def capture(argv,**kwargs):
        index=len(calls);label=labels[index];calls.append({'argv':argv,'kwargs':kwargs})
        dest=Path(kwargs['destination']);dest.mkdir(mode=0o700);stat=dest.stat()
        if label=='init':(Path(scope['artifact_root']['path'])/'sandbox.git/objects/info').mkdir(parents=True)
        out=outputs[label];err=b'';code=0;status='EXIT_ZERO';eof=True
        if failure=='nonzero' and index==0:err=b'\x00\xff'+b'E'*2998;code=7;status='EXIT_NONZERO'
        if failure=='timeout' and index==0:err=b'partial\0\xff';code=-9;status='TIMEOUT';eof=False
        if failure=='head' and label=='head':out=('f'*40+'\n').encode()
        if failure=='member' and label=='members':out=out.replace(b'100644',b'100755')
        if failure=='blob' and label=='blob0':out=b'mutated'
        if failure=='commit' and label=='commit':out=out+b'changed'
        streams={}
        for stream,raw,cap in (('stdout',out,kwargs['stdout_cap']),('stderr',err,kwargs['stderr_cap'])):
            path=dest/(stream+'.raw');path.write_bytes(raw);path.chmod(0o400);fs=path.stat()
            streams[stream]={'cap_bytes':cap,'observed_bytes':len(raw),'eof_observed':eof,
              'truncated':not eof,'full_stream_retained':eof,'file':path.name,
              'file_pin':{**n.pin(raw),'device':fs.st_dev,'inode':fs.st_ino,'links':1},
              'file_write_complete':True,'file_fsync_complete':True,
              'reconstruction':{'encoding':'base64',**n.pin(raw),'data':base64.b64encode(raw).decode()}}
        record={'schema':'radio-prospective-failure-output-retention-v1','authority':'future-diagnostic-utility-only',
          'destination':{'path':str(dest),'device':stat.st_dev,'inode':stat.st_ino,'exclusively_created':True},
          'argv':argv,'process_status':status,'returncode':code,'child_reaped':True,
          'timeout_seconds':kwargs['timeout_seconds'],'timed_out':status=='TIMEOUT',
          'output_limit_exceeded':False,'launch_error':None,'capture_error':None,'streams':streams,
          'persistence_errors':[],'strictly_completed':status=='EXIT_ZERO','automatic_retry':False,
          'overwrites_performed':False,'whole_descendant_lifetime_qualified':False,
          'scientific_execution_authorized':False,'engineering_control_qualified':False,
          'historical_lost_output_reconstructed':False}
        first=n.canonical(record);p=dest/'disposition.json';p.write_bytes(first);p.chmod(0o400);fs=p.stat()
        record.update(disposition_file_pin={**n.pin(first),'device':fs.st_dev,'inode':fs.st_ino,'links':1},
          disposition_write_complete=True,disposition_fsync_complete=True,
          disposition_first_payload_sha256=n.pin(first)['sha256'])
        if on_call:on_call(index,label,record)
        return types.SimpleNamespace(payload=n.canonical(record),record=lambda:record)
    return capture,calls
