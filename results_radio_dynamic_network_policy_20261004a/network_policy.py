"""Prospective platform loopback networking; never a scientific admission."""
import hashlib
import json
import os
from pathlib import Path
import re

PROXIES = ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy')
FIXED = {'PATH':'/usr/local/bin:/usr/bin:/bin','LC_ALL':'C','GIT_TERMINAL_PROMPT':'0',
         'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null',
         'GIT_CONFIG_NOSYSTEM':'1','GIT_NO_REPLACE_OBJECTS':'1'}


def need(value, reason):
    if not value:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,
                      allow_nan=False).encode()+b'\n'


def pin(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def proxy(value, scheme):
    # Full canonical grammar excludes userinfo, remote hosts, escapes and suffixes.
    need(type(value) is str and len(value)<=64,'bounded proxy string required')
    match=re.fullmatch(re.escape(scheme)+r'://127\.0\.0\.1:([1-9][0-9]{3,4})',value)
    need(match is not None,'canonical permitted loopback proxy required')
    port=int(match.group(1))
    need(1024<=port<=65535,'unprivileged dynamic proxy port required')
    return {'scheme':scheme,'host':'127.0.0.1','port':port,**pin(value.encode())}


def file_pin(expected):
    path=Path(expected['path'])
    need(path.is_absolute() and not path.is_symlink(),'ordinary absolute pinned file required')
    stat=path.stat();raw=path.read_bytes()
    need(stat.st_mode&0o777==expected['mode'] and pin(raw)=={k:expected[k] for k in ('bytes','sha256')},
         'selected file pin differs')
    return raw


def build(policy, source=None):
    source=os.environ if source is None else source
    need(set(policy)=={'schema','proxy_names','host','http_scheme','all_scheme','port_min','port_max',
                      'no_proxy_pin','trust_file','git_exec_path','fixed_environment','forbidden_names'},
         'exact policy fields required')
    need(policy['schema']=='radio-dynamic-loopback-network-policy-v1'
         and policy['proxy_names']==list(PROXIES) and policy['host']=='127.0.0.1'
         and policy['http_scheme']=='http' and policy['all_scheme']=='socks5h'
         and policy['port_min']==1024 and policy['port_max']==65535
         and policy['fixed_environment']==FIXED
         and policy['forbidden_names']==['SSL_CERT_DIR','GIT_SSL_CAINFO'],
         'fixed local endpoint policy required')
    need(all(name not in source for name in policy['forbidden_names']),
         'additional trust configuration refused')
    descriptors={}
    for name in PROXIES:
        need(name in source,'all frozen proxy names must be present')
        descriptors[name]=proxy(source[name],'socks5h' if name.lower()=='all_proxy' else 'http')
    for a,b in (('HTTP_PROXY','http_proxy'),('HTTPS_PROXY','https_proxy'),('ALL_PROXY','all_proxy')):
        need(source[a]==source[b],'case-paired proxy endpoints disagree')
    need(source['HTTP_PROXY']==source['HTTPS_PROXY'],'HTTP and HTTPS endpoints disagree')
    no_proxy={}
    for name in ('NO_PROXY','no_proxy'):
        value=source.get(name)
        need(type(value) is str and pin(value.encode())==policy['no_proxy_pin'],
             'frozen proxy bypass list differs')
        no_proxy[name]=pin(value.encode())
    need(source.get('SSL_CERT_FILE')==policy['trust_file']['path'],
         'frozen trust-file location differs')
    file_pin(policy['trust_file'])
    need(Path(policy['git_exec_path']).is_absolute(),'absolute selected Git exec path required')
    env={**FIXED,'GIT_EXEC_PATH':policy['git_exec_path'],
         **{name:source[name] for name in (*PROXIES,'NO_PROXY','no_proxy','SSL_CERT_FILE')}}
    proof={'schema':'radio-dynamic-loopback-environment-observation-v1',
           'policy_pin':pin(canonical(policy)),'proxies':descriptors,'no_proxy':no_proxy,
           'trust_file':policy['trust_file'],'fixed_environment':FIXED,
           'git_exec_path':policy['git_exec_path'],'actual_environment_names':sorted(env),
           'actual_environment_pin':pin(canonical(env)),
           'raw_proxy_strings_published':False,'unrelated_environment_inherited':False,
           'scientific_execution_authorized':False}
    return env,proof
