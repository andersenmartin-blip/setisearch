"""Capture whole child usage for restoration or the single saved-result audit."""
import argparse,json,os,resource,signal,subprocess,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--cpu',type=int,required=True);p.add_argument('--wall',type=int,required=True);p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args();d=Path(__file__).resolve().parent;receipt=d/f'resource_{a.label}.json'
    if receipt.exists():raise SystemExit('Existing receipt: do not repeat a closed job')
    if a.label=='verification':
        if a.cpu!=60 or a.wall!=120:raise SystemExit('Frozen verifier limits required')
        if Path('pilot_protocol_20261008/review/METHOD_SAVED_CASE_000_REPRODUCTION.json').exists():raise SystemExit('Bounded output already exists; no verifier invocation permitted')
        claim=d/'VERIFIER_INVOCATION.json'
        with claim.open('x') as f:json.dump({'case_id':'SETI_RADIO_PILOT_20261008_METHOD_STUDY:method_signal:000','actual_date':'2026-10-08','only_invocation_reserved':True,'no_retry':True},f,indent=2)
    previous=sum(json.loads(f.read_text())['whole_job_CPU_s'] for f in d.glob('resource_*.json'))
    if previous+a.cpu+5>150:raise SystemExit('Planning reservation insufficient')
    s=resource.getrusage(resource.RUSAGE_SELF);c=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.monotonic()
    def limits():
        resource.setrlimit(resource.RLIMIT_AS,(4294967296,4294967296))
        resource.setrlimit(resource.RLIMIT_CPU,(a.cpu,a.cpu))
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    error=None
    with (d/f'job_{a.label}.log').open('x') as log:
        try:
            child=subprocess.Popen(a.command,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,start_new_session=True)
            try:status=child.wait(timeout=a.wall)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);status=child.wait();error='WALL_TIMEOUT_GROUP_KILLED_CHILD_REAPED'
        except Exception as e:status=125;error=repr(e);log.write(error+'\n')
    z=resource.getrusage(resource.RUSAGE_CHILDREN);e=resource.getrusage(resource.RUSAGE_SELF)
    cc=z.ru_utime+z.ru_stime-c.ru_utime-c.ru_stime;wc=e.ru_utime+e.ru_stime-s.ru_utime-s.ru_stime
    x={'label':a.label,'command':a.command,'exit_code':status,'error':error,'child_CPU_s':cc,'wrapper_CPU_s_through_measurement':wc,'whole_job_CPU_s':cc+wc,'wall_s':time.monotonic()-start,'child_peak_RSS_bytes':z.ru_maxrss*1024,'child_CPU_cap_s':a.cpu,'wall_cap_s':a.wall,'address_space_cap_bytes':4294967296,'closed_child':True,'conservative150_reservation_component_not_extra_debit':True,'post_measurement_record_serialization_API_overhead_not_fully_metered':True}
    with receipt.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
    print(json.dumps(x));raise SystemExit(status)

if __name__=='__main__':main()
