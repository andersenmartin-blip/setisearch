"""Bounded public HTTPS Git readback for a fresh synthetic Contents probe.

No writes to a remote, no forced fetch, no credentials, no scientific services.
The only fetched ref is the fixed fresh probe branch. Captures every selected
Git process output exactly. This is not an RSS/ELF/whole-runtime certificate.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

NETWORK_ENVIRONMENT_NAMES = ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY',
    'http_proxy','https_proxy','all_proxy','no_proxy','SSL_CERT_FILE','SSL_CERT_DIR','GIT_SSL_CAINFO')


def environment_pins(source):
    return {name:({'present':True,**raw_pin(source[name].encode())}
                  if name in source else {'present':False,'bytes':0,'sha256':None})
            for name in NETWORK_ENVIRONMENT_NAMES}


def bounded_environment(scope, source=None):
    source=os.environ if source is None else source
    observed=environment_pins(source)
    need(scope['network_environment_pins']==observed,
         'frozen allowed network environment differs; no Git process admitted')
    env={'PATH':os.defpath,'LC_ALL':'C','GIT_TERMINAL_PROMPT':'0'}
    env.update({name:source[name] for name in NETWORK_ENVIRONMENT_NAMES if name in source})
    return env,observed


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,
                      allow_nan=False).encode()+b'\n'


def need(value,reason):
    if not value:raise ValueError(reason)


def raw_pin(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def git_blob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def read(scope,phase,expected_commit,expected_parent,*,invoke=None):
    need(phase in ('initial','interference','final'),'fixed native readback phase required')
    need(all(type(v) is str and re.fullmatch('[0-9a-f]{40}',v) for v in (expected_commit,expected_parent)),
         'fixed exact Git identities required')
    need(scope['domain']=='synthetic-service-probe-only' and scope['scientific_execution_authorized'] is False
         and scope['repository']=='andersenmartin-blip/setisearch'
         and scope['branch']=='radio-contents-cas-probe-20261004c','fixed fresh synthetic branch only')
    root=scope['repository_root']; need(type(root) is str and Path(root).is_absolute(),'fixed repository root required')
    paths=(scope['ledger_path'],scope['interference_path'])
    need(all(re.fullmatch(r'synthetic_contents_cas_probe_20261004c/[a-z]+\.json',v) for v in paths),
         'fixed two selected synthetic paths required')
    operations=[];started=time.monotonic();total=0;environment=None
    actual=subprocess.run if invoke is None else invoke
    def git(*args):
        nonlocal total
        remaining=30-(time.monotonic()-started);need(remaining>0,'native helper deadline exhausted')
        need(len(operations)<6,'native process budget exhausted')
        argv=['git',*args]
        try:
            result=actual(argv,cwd=root,env=environment,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=remaining,check=False)
            out,err=result.stdout,result.stderr;code=result.returncode
        except subprocess.TimeoutExpired as e:
            out,err=e.stdout or b'',e.stderr or b'';code=None
        total+=len(out)+len(err)
        row={'argv':argv,'returncode':code,
             'stdout':{**raw_pin(out),'base64':base64.b64encode(out).decode()},
             'stderr':{**raw_pin(err),'base64':base64.b64encode(err).decode()}}
        operations.append(row)
        need(total<=65536,'native helper total output cap exceeded')
        need(code==0,'native Git process failed or timed out; original output retained')
        return out
    result={'schema':'radio-contents-cas-native-readback-v1','phase':phase,
        'expected_commit':expected_commit,'expected_parent':expected_parent,'status':'CLOSED_FAILED',
        'operations':operations,'qualified_atomic_expected_revision_cas':False,
        'complete_hosted_transport_qualified':False,'scientific_execution_authorized':False}
    try:
        environment,fingerprints=bounded_environment(scope)
        result['network_environment_pins']=fingerprints
        branch=scope['branch']
        git('fetch','--no-tags','https://github.com/andersenmartin-blip/setisearch.git',
            'refs/heads/'+branch+':refs/remotes/origin/'+branch)
        need(git('rev-parse','refs/remotes/origin/'+branch).decode().strip()==expected_commit,
             'fetched actual branch head differs; never switch expected revision')
        commit=git('cat-file','-p',expected_commit)
        need(hashlib.sha1(b'commit '+str(len(commit)).encode()+b'\0'+commit).hexdigest()==expected_commit,
             'actual raw Git commit identity differs (including replacement objects)')
        header=commit.split(b'\n\n',1)[0].splitlines()
        parents=[line[7:].decode() for line in header if line.startswith(b'parent ')]
        trees=[line[5:].decode() for line in header if line.startswith(b'tree ')]
        need(parents==[expected_parent] and len(trees)==1 and re.fullmatch('[0-9a-f]{40}',trees[0]),
             'actual commit exact parent/tree differs')
        entries=git('ls-tree','-r','--full-tree',expected_commit,'--',*paths)
        found={}
        for line in entries.decode().splitlines():
            info,path=line.split('\t',1);mode,kind,sha=info.split()
            need(path in paths and path not in found and mode=='100644' and kind=='blob'
                 and re.fullmatch('[0-9a-f]{40}',sha),'ordinary distinct selected Git member required')
            found[path]=sha
        expected_paths={paths[0]} if phase=='initial' else set(paths)
        need(set(found)==expected_paths,'complete selected presence/absence differs')
        files={}
        for path in paths:
            if path not in found:continue
            raw=git('cat-file','blob',expected_commit+':'+path)
            need(git_blob(raw)==found[path] and 0<len(raw)<=2048,'actual blob raw pin or tiny size differs')
            files[path]={'git_blob':found[path],**raw_pin(raw),'raw_ascii':raw.decode('ascii')}
        result.update(status='SELECTED_GIT_BYTES_VERIFIED',actual_tree=trees[0],selected_files=files)
    except (ValueError,OSError,UnicodeError) as error:
        result['error']=type(error).__name__+': '+str(error)
    result.update(git_processes=len(operations),captured_output_bytes=total,
                  elapsed_milliseconds=int((time.monotonic()-started)*1000))
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('scope_path');p.add_argument('scope_sha256');
    p.add_argument('phase');p.add_argument('expected_commit');p.add_argument('expected_parent');a=p.parse_args()
    raw=Path(a.scope_path).read_bytes();need(hashlib.sha256(raw).hexdigest()==a.scope_sha256,'external scope raw pin differs')
    result=read(json.loads(raw),a.phase,a.expected_commit,a.expected_parent)
    sys.stdout.buffer.write(canonical(result));return 0 if result['status']=='SELECTED_GIT_BYTES_VERIFIED' else 1


if __name__=='__main__':raise SystemExit(main())
