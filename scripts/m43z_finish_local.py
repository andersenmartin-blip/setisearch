"""During an active session, audit and summarize once the frozen run completes."""
import subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results_m43z_joint_controls'

def main():
    deadline=time.monotonic()+7200
    while not (OUT/'result.json').exists():
        if time.monotonic()>deadline:raise TimeoutError('numerical result did not complete')
        time.sleep(1)
    for script,log in [('m43z_audit_report.py','artifact_validation.log'),('m43z_complete_report.py','interpretation.log')]:
        with (OUT/log).open('w') as out:
            code=subprocess.call([sys.executable,str(ROOT/'scripts'/script)],stdout=out,stderr=subprocess.STDOUT,cwd=ROOT)
        if code:raise SystemExit(code)
    print('M43Z local audit and report complete',flush=True)
if __name__=='__main__':main()
