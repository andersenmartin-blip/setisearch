from pathlib import Path
import hashlib,json,subprocess,sys,time
mode=sys.argv[1];out=Path(sys.argv[2]);pin=Path(sys.argv[3])
if mode=='timeout':time.sleep(5)
out.mkdir()
value={'status':'PASS','fixture':'BO_E05_FIXED_BYTES_V1','mode':mode}
full=(json.dumps(value,sort_keys=True)+'\n').encode()
(out/'RESULT.json').write_bytes(b'{"status":' if mode=='truncated_result' else full)
if mode=='pin_change':pin.write_bytes(b'AFTER\n')
if mode=='missing_eof':
    subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(5)'],stdout=sys.stdout,stderr=sys.stderr)
terminal={'event':'GATE_TERMINAL_EOF','status':'PASS','result_sha256':hashlib.sha256(full).hexdigest()}
sys.stdout.write(json.dumps(terminal,sort_keys=True)+('' if mode=='truncated_stdout' else '\n'));sys.stdout.flush()
if mode=='nonzero':sys.exit(7)
