"""Meter bounded deterministic planning arithmetic; never searches data."""
import argparse,json,os,resource,subprocess,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args();out=Path(__file__).resolve().parent
    destination=out/f'resource_{a.label}.json'
    if destination.exists():raise SystemExit('Existing job receipt must be preserved')
    existing=[json.loads(f.read_text()) for f in out.glob('resource_*.json')]
    def measured_component(f):
        if 'whole_job_cpu_s' in f:return f['whole_job_cpu_s']
        if 'whole_child_cpu_s' in f:return f['whole_child_cpu_s']+f.get('wrapper_cpu_s_through_resource_record_preparation',0)
        raise ValueError('Unsupported resource-receipt schema')
    used=sum(measured_component(f) for f in existing)
    if used+30>100:raise SystemExit('Insufficient remaining planning reservation')
    first=resource.getrusage(resource.RUSAGE_SELF);child_first=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.monotonic()
    def limits():
        resource.setrlimit(resource.RLIMIT_AS,(4294967296,4294967296))
        resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    with (out/f'job_{a.label}.log').open('w') as log:
        proc=subprocess.Popen(a.command,stdout=log,stderr=subprocess.STDOUT,env=env,preexec_fn=limits)
        try:status=proc.wait(timeout=60)
        except subprocess.TimeoutExpired:proc.kill();status=proc.wait()
    child_last=resource.getrusage(resource.RUSAGE_CHILDREN);last=resource.getrusage(resource.RUSAGE_SELF)
    ccpu=child_last.ru_utime+child_last.ru_stime-child_first.ru_utime-child_first.ru_stime
    wcpu=last.ru_utime+last.ru_stime-first.ru_utime-first.ru_stime
    receipt={'label':a.label,'command':a.command,'exit_code':status,'wall_s':time.monotonic()-start,'child_cpu_s':ccpu,'wrapper_cpu_s':wcpu,'whole_job_cpu_s':ccpu+wcpu,'child_peak_RSS_bytes':child_last.ru_maxrss*1024,'CPU_cap_child_s':30,'wall_cap_s':60,'address_space_cap_bytes':4294967296,'component_of_conservative100_CPU_s_reservation':True,'not_an_additional_debit':True}
    destination.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));raise SystemExit(status)

if __name__=='__main__':main()
