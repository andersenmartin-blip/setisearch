"""Pure mocked/static review; no sockets, TLS context, packages, scientific IO."""
import base64
import json
import os
from pathlib import Path
import shutil
import time
from unittest import mock

HERE=Path(__file__).resolve().parent
SNAP=HERE/'snapshot-03'
T={'__name__':'review_test_fixtures','__file__':str(SNAP/'test_bootstrap_gate.py')}
exec(compile((SNAP/'test_bootstrap_gate.py').read_bytes(),T['__file__'],'exec'),T)
G=T['G']

case=T['MockedPipelineGuards']()
case.setUp()
clock={'expired':False}
real_time=G['time'].monotonic_ns
now=real_time()
def fake_time():
    return now+271*10**9 if clock['expired'] else now
base_modules=case.fake_transport_modules()
def fail_after_deadline(wheel,fd,budget,deadline,opener=None):
    case.acquired+=1
    clock['expired']=True
    opener.receipt.update({'status':'CLOSED_FAILED','received_connect_prefix_base64':base64.b64encode(b'HTTP/1.1 200 OK\r\n').decode(),'received_connect_prefix_bytes':17})
    exc=G['Refusal']('synthetic genuine-shaped acquisition deadline')
    exc.receipt={'status':'CLOSED_FAILED','fixture':True,'received_body_bytes':0,'raw_observed':'synthetic prefix retained only in memory'}
    raise exc
base_modules['wheel_io'].acquire_wheel=fail_after_deadline
try:
    with mock.patch.dict(G,{'pin_read':case.fake_pin,'compile_verified':case.fake_compile,'validate_transport_descriptor':lambda *a:{'proxy_selection':{'environment_name':'PIP_PROXY'},'trust_binding':{}},'compile_transport_modules':lambda *a:base_modules,'native_transport_bindings':lambda *a:(lambda *a:None,lambda *a:None)}), mock.patch.object(G['time'],'monotonic_ns',side_effect=fake_time):
        try:
            result=case.run_fixture()
            outcome='returned '+result['report']['status']
        except Exception as exc:
            outcome=type(exc).__name__+':'+str(exc)
    target=HERE/'repro-cutoff-fixed-artifacts'
    if target.exists(): shutil.rmtree(target)
    shutil.copytree(case.root,target)
    files=sorted(p.name for p in case.root.iterdir())
    print(json.dumps({'repro':'corrected operating cutoff preserves raw receipts and terminal result','outcome':outcome,'acquired':case.acquired,'spent_retained':(case.root/'spent.json').exists(),'acquisition_receipt_retained':(case.root/'acquisition-numpy.json').exists(),'transport_receipt_retained':(case.root/'transport-numpy.json').exists(),'terminal_report_retained':(case.root/'supervisor-result.json').exists(),'artifact_names':files},indent=2))
finally:
    case.tearDown()

# A separate real bounded regular-file read validates corrected precharging.
import tempfile
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp); os.chmod(root,0o700)
    fd,fds,bindings=G['hold_root'](str(root)); st=root.stat()
    budget=G['Budget'](dict(G['CEILINGS']),str(root),fd,{'device':st.st_dev,'inode':st.st_ino,'mode':'0700'},time.monotonic_ns()+30*10**9,bindings=bindings)
    trust_path=root/'synthetic-trust-bytes.txt'; trust_path.write_bytes(b'abcde')
    budget.debit_read(6)
    requests=[]; real_read=os.read
    def short_read(fd,n):
        requests.append(n)
        return real_read(fd,min(n,2))
    try:
        with mock.patch.object(G['os'],'read',side_effect=short_read):
            raw=G['read_precharged_trust'](str(trust_path),6,budget)
        print(json.dumps({'repro':'corrected trust_read precharges every request using prepaid allowance once','raw_bytes':len(raw),'charged_bytes':budget.bytes,'actual_syscall_requests':requests,'actual_requested_sum':sum(requests),'received_sum':sum(budget.received.values())},indent=2))
    finally:
        for opened in reversed(fds): os.close(opened)
