"""Run one bounded P source cohort and retain exact machine-readable evidence."""
import hashlib, json, os, resource, subprocess, sys, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
started=time.time(); before=resource.getrusage(resource.RUSAGE_CHILDREN)
command=[sys.executable,'-m','unittest','-v',str(HERE/'test_activity.py')]
process=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=60)
after=resource.getrusage(resource.RUSAGE_CHILDREN); elapsed=time.time()-started
report={'schema':'radio-P-source-test-run-v1','cohort':2,'command':command,
        'returncode':process.returncode,'wall_seconds':elapsed,
        'child_user_seconds':after.ru_utime-before.ru_utime,
        'child_system_seconds':after.ru_stime-before.ru_stime,
        'child_max_rss_kib':after.ru_maxrss,
        'stdout':process.stdout,'stderr':process.stderr,
        'limits':{'wall_seconds':60,'cpu_seconds':30,'address_space_mib':256,'fds':96,'evidence_mib':16},
        'native_module_built_or_loaded':False,'telescope_spectra_opened':False}
raw=(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n').encode()
(HERE/'RUN2.json').write_bytes(raw)
print(hashlib.sha256(raw).hexdigest(),len(raw),process.returncode)
raise SystemExit(process.returncode)
