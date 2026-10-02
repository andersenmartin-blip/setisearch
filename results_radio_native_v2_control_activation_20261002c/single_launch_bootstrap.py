import os,json,hashlib,stat,types,time,subprocess
from pathlib import Path
root=Path('/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002')
out=root/'results_radio_native_v2_control_activation_20261002c'
python='/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12'
config_sha='462456127bcbc7a4e90cd0dcafb62cca7b6e47d9d445868730f5346a781ac33f'
scope=root/'results_radio_native_v2_compact_control_20261002c'
ledger=root/'.radio-native-v2-invocation-ledger-20261002c'
def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def raw_pin(p,n,sha):
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        raw=os.read(fd,n+1);s=os.fstat(fd);t=os.stat(p,follow_symlinks=False)
        assert stat.S_ISREG(s.st_mode) and len(raw)==n and hashlib.sha256(raw).hexdigest()==sha
        assert (s.st_dev,s.st_ino)==(t.st_dev,t.st_ino)
        return raw
    finally:os.close(fd)
def write(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
    try:os.write(fd,raw);os.fsync(fd)
    finally:os.close(fd)
    d=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(d);os.close(d)
    assert path.read_bytes()==raw
assert not os.path.lexists(scope) and not os.path.lexists(ledger)
assert not os.path.lexists(out/'single-launch-start.json')
assert subprocess.check_output(['/usr/local/bin/git','-C',str(root),'rev-parse','HEAD'],text=True).strip()=='f514d782a0f807223e4bc47cb0b330b4b46a198f'
raw_pin(Path(python),30894944,'fa67443527ed9647f760d807e2a38f26340757123e643c4639cf273ed15d5ea7')
raw_pin(root/'scripts/radio_native_v2_compact_control_launch.py',34274,'0db793b74b64f4b5f201d1c7d7e10f273eaf75623c6d4150033cf52f40e5cdf8')
config=json.loads(raw_pin(root/'config/radio_native_v2_compact_control_launch_20261002c.launch.json',1123,config_sha))
inputs={name:json.loads(raw_pin(root/p['path'],p['bytes'],p['sha256'])) for name,p in config['inputs'].items()}
raw=raw_pin(root/'scripts/radio_native_v2_activation_environment.py',11741,'059003934a8b51c544f72b488c41c19a6067c0ffb0e65c31afc6eacd35d76bfd')
m=types.ModuleType('held_activation_environment');m.__file__=str(root/'scripts/radio_native_v2_activation_environment.py');exec(compile(raw,m.__file__,'exec'),m.__dict__)
execution_env=m.expected_environment(inputs['plan'],inputs['complete_freeze'])
assert len(execution_env)==10
argv=[python,'-I','-S','-B',str(root/'scripts/radio_native_v2_compact_control_launch.py'),'--run','--config-sha256',config_sha]
record={'schema':'radio-native-v2-c-single-launch-start-v1','status':'ONE_EXACT_ENGINEERING_LAUNCH_NO_AUTOMATIC_RETRY','utc_start':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'public_preread_commit':'f033690f163e10287bfe00a4733edef8ed6c9543','activation_commit':'f514d782a0f807223e4bc47cb0b330b4b46a198f','public_sidecar_commit':'051d6f69bfab9f5989009faf871de5048693ca2f','config_sha256':config_sha,'argv':argv,'environment':execution_env,'scope':str(scope),'private_c_ledger':str(ledger),'control_scope_absent_before_launch':True,'journal_created_empty_before_launcher':True,'automatic_retry':False,'restart_authorized':False,'scientific_execution_authorized':False,'native_execution_authorized':False}
old_umask=os.umask(0o077)
try:os.mkdir(ledger,0o700)
finally:os.umask(old_umask)
s=os.lstat(ledger);assert stat.S_ISDIR(s.st_mode) and stat.S_IMODE(s.st_mode)==0o700 and s.st_uid==os.getuid() and list(ledger.iterdir())==[]
fd=os.open(ledger,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);os.fsync(fd);os.close(fd)
fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);os.fsync(fd);os.close(fd)
write(out/'single-launch-start.json',canonical(record))
stdout_fd=os.open(out/'single-launch-stdout.log',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
stderr_fd=os.open(out/'single-launch-stderr.log',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
os.dup2(stdout_fd,1);os.dup2(stderr_fd,2);os.close(stdout_fd);os.close(stderr_fd)
os.chdir(root)
os.execve(python,argv,execution_env)
