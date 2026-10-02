import os,sys,json,hashlib,types,stat
from pathlib import Path
root=Path('/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002')
out=root/'results_radio_native_v2_control_activation_20261002c'
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
def write(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
    try:
        with os.fdopen(fd,'wb',closefd=False) as f: f.write(raw);f.flush();os.fsync(fd)
        st=os.fstat(fd); named=os.stat(path,follow_symlinks=False)
        assert (st.st_dev,st.st_ino)==(named.st_dev,named.st_ino)
    finally: os.close(fd)
    d=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(d);os.close(d)
    assert path.read_bytes()==raw
def held_module(rel,n,sha):
    p=root/rel;fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        raw=os.read(fd,n+1);st=os.fstat(fd);named=os.stat(p,follow_symlinks=False)
        assert stat.S_ISREG(st.st_mode) and len(raw)==n and hashlib.sha256(raw).hexdigest()==sha
        assert (st.st_dev,st.st_ino)==(named.st_dev,named.st_ino)
        m=types.ModuleType(rel);m.__file__=str(p);exec(compile(raw,str(p),'exec'),m.__dict__);return m
    finally:os.close(fd)
scope=root/'results_radio_native_v2_compact_control_20261002c'
ledger=root/'.radio-native-v2-invocation-ledger-20261002c'
assert not os.path.lexists(scope) and not os.path.lexists(ledger)
a=held_module('scripts/radio_native_v2_control_activation.py',20022,'b0fc36e2ed4b925f0ff51e812b18c79ef8e8f3d93ea4f6091159dc6cfc0bfb6a')
receipt=a.verify_marker_checkout(root,plan_path='config/radio_native_v2_compact_eight_input_control_20261002r.plan.json',freeze_path='config/radio_native_v2_control_integration_20261002a.runtime.json',preread_path='config/radio_native_v2_compact_control_20261002c.execution-preread.json',activation_readback_path=out/'activation-public-readback.json',activation_commit='f514d782a0f807223e4bc47cb0b330b4b46a198f',execution_scope=str(scope))
write(out/'marker-checkout-receipt.json',canonical(receipt))
review=json.loads((out/'expected-sidecar-protocol-review.json').read_bytes())
config=review['expected_B_fixed_launch_config']['value']
for name,pin in config['inputs'].items():
    raw=(root/pin['path']).read_bytes();assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],name
l=held_module('scripts/radio_native_v2_compact_control_launch.py',34274,'0db793b74b64f4b5f201d1c7d7e10f273eaf75623c6d4150033cf52f40e5cdf8')
l.validate_launch_config(config)
raw=canonical(config);assert len(raw)==1123 and hashlib.sha256(raw).hexdigest()=='462456127bcbc7a4e90cd0dcafb62cca7b6e47d9d445868730f5346a781ac33f'
write(root/'config/radio_native_v2_compact_control_launch_20261002c.launch.json',raw)
assert not os.path.lexists(scope) and not os.path.lexists(ledger)
summary={'schema':'radio-native-v2-c-sidecars-build-v1','status':'MARKER_CHECKOUT_AND_FIXED_CONFIG_VERIFIED_NO_CONTROL_INVOKED','activation_commit':receipt['activation_commit'],'activation_only_runtime_complete':receipt['activation_only_runtime_complete'],'config_bytes':len(raw),'config_sha256':hashlib.sha256(raw).hexdigest(),'protected_scope_absent':True,'private_ledger_absent':True,'protected_control_invocations':0,'scientific_execution_authorized':False}
write(out/'sidecars-build-summary.json',canonical(summary));print(canonical(summary).decode(),end='')
