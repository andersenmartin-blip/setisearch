"""Meter read-only analysis jobs; never invokes a detector or generator."""
import argparse, json, os, resource, subprocess, time
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--label',required=True); p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args(); out=Path(__file__).resolve().parent
    existing=list(out.glob('resource_*.json'))
    charged=sum(json.loads(x.read_text())['whole_job_cpu_s'] for x in existing)
    if charged+45>200: raise SystemExit('Closed analysis allocation insufficient for another capped job')
    receipt=out/f'resource_{a.label}.json'
    if receipt.exists(): raise SystemExit('Do not overwrite a previous job receipt')
    before=resource.getrusage(resource.RUSAGE_SELF); children=resource.getrusage(resource.RUSAGE_CHILDREN); start=time.monotonic()
    env=os.environ.copy(); env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',MPLBACKEND='Agg')
    def limits():
        resource.setrlimit(resource.RLIMIT_AS,(4294967296,4294967296)); resource.setrlimit(resource.RLIMIT_CPU,(45,45))
    with (out/f'job_{a.label}.log').open('w') as log:
        child=subprocess.Popen(a.command,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits)
        try: status=child.wait(timeout=120)
        except subprocess.TimeoutExpired: child.kill(); status=child.wait()
    child_after=resource.getrusage(resource.RUSAGE_CHILDREN); self_after=resource.getrusage(resource.RUSAGE_SELF)
    child_cpu=child_after.ru_utime+child_after.ru_stime-children.ru_utime-children.ru_stime
    wrapper_cpu=self_after.ru_utime+self_after.ru_stime-before.ru_utime-before.ru_stime
    record={'label':a.label,'command':a.command,'exit_code':status,'wall_s':time.monotonic()-start,'child_cpu_s':child_cpu,'wrapper_cpu_s':wrapper_cpu,'whole_job_cpu_s':child_cpu+wrapper_cpu,'child_peak_rss_bytes':child_after.ru_maxrss*1024,'wrapper_peak_rss_bytes':self_after.ru_maxrss*1024,'cpu_cap_child_s':45,'wall_cap_s':120,'address_space_cap_bytes':4294967296,'allocated_analysis_reserve_s':200,'already_measured_components_s':charged,'charged_against_new_analysis_reserve':True}
    receipt.write_text(json.dumps(record,indent=2)+'\n'); print(json.dumps(record)); raise SystemExit(status)
if __name__=='__main__': main()
