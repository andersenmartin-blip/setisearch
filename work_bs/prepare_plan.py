"""Freeze bounded engineering fixtures and preserved historical evidence."""
from pathlib import Path
import hashlib
import json
import platform
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
import diagnostic


def pin(p):
    return dict(path=str(p.relative_to(REPO)),bytes=p.stat().st_size,sha256=diagnostic.sha(p))


def main():
    sources=sorted(set(list(ROOT.glob('*.py'))+list((ROOT/'tests').glob('*.py'))+
        [ROOT/'PREREG_BS.md',ROOT/'review/FORENSIC_CODE_REVIEW_BS.md',
         ROOT/'review/SOURCE_REVIEW_BS.json',ROOT/'review/TRACING_CAPABILITY.json',REPO/'work_bo/src/capture.py']+
        [REPO/rel for rel,_ in diagnostic.SOURCE_PINS.values()]))
    historical=[REPO/'work_br/SUMMARY_BP_BR.json', REPO/'work_bq/EFFECTIVE_STATUS_BQ.json',
        REPO/'work_bq/review/FORENSIC_REVIEW_BQ.json', REPO/'work_br/review/BR_FAILURE_REVIEW.json',
        REPO/'work_bq/execution/BQ_A04_ASSOC_V1/TERMINAL_BQ.json',
        REPO/'work_br/execution/BR_A04_ASSOC_V1/TERMINAL_BR.json']
    for phase in ['bq','br']:
        root=REPO/('work_'+phase)/'execution'/('BQ_A04_ASSOC_V1' if phase=='bq' else 'BR_A04_ASSOC_V1')
        historical.extend(p for p in root.rglob('*') if p.is_file() and
                          (p.name.endswith('.jsonl') or p.name.endswith('.jsonl.pending')))
    expected=[]
    for stream in range(2):
        digest=hashlib.sha256();size=0
        for number in range(45000):
            raw=diagnostic.encode(diagnostic.fixture_record(stream,number))
            digest.update(raw);size+=len(raw)
        expected.append(dict(stream=stream,records=45000,bytes=size,sha256=digest.hexdigest()))
    plan=dict(schema='SETI_BS_FILE_STABILITY_PLAN_V1',execution_identity='BS_FILE_STABILITY_V1',
        prior_status='23_CONTROLS_PASS_A04_PAIR_CLOSURE_BLOCKED',
        scientific_reexecution_authorized=False,RNG_authorized=False,
        astronomical_powers_authorized=False,new_scan_scores_authorized=False,
        trials=[dict(id='bq_serial',writer='bq',records=45000,pace_ms=0,overlap=False),
                dict(id='br_serial',writer='br',records=45000,pace_ms=0,overlap=False),
                dict(id='br_overlap',writer='br',records=45000,pace_ms=100,overlap=True)],
        expected_streams=expected,
        caps_per_trial=dict(wall_seconds=120,cpu_seconds=90,rss_bytes=512<<20,stored_bytes=384<<20),
        phase_storage_cap_bytes=1<<30,max_trials=3,no_retry=True,
        overlap_witness=dict(source='work_bs/overlap_witness.py',wait_seconds=6,maximum_initial_wait_seconds=5,
          output='work_bs/execution/BS_FILE_STABILITY_V1/OVERLAP_WITNESS.json',
          policy='Read-only payload access; own receipt only; start after overlapping runner yields its first active session'),
        serial_policy='No other agent or root execution command while either serial trial is live; same-session polling only if required',
        runtime=dict(python_version=platform.python_version(),executable_sha256=diagnostic.sha(sys.executable)),
        tracing=dict(strace_preflight='UNAVAILABLE: PTRACE_TRACEME Operation not permitted',
                     method='Python audit-hook file operation events plus inotify and held-fd metadata',
                     limitation='Not a syscall trace: write/fsync calls and external-process attribution are not captured by Python audit.'),
        source_pins=[pin(p) for p in sources],historical_pins=[pin(p) for p in sorted(set(historical))],
        acceptance='Exact expected fixture bytes, hashes, records and unchanged closed identity; natural process success and independent final review. Any observed mutation remains a failed integrity trial.',
        qualification='Engineering evidence only; no A04 pass, no source attribution from absence of a traced syscall, no historical repair.',
        new_observations=0,new_archive_requests=0,new_coverage_credit=0)
    with (ROOT/'BS_FILE_STABILITY_PLAN.json').open('x') as f:
        json.dump(plan,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(plan_sha256=diagnostic.sha(ROOT/'BS_FILE_STABILITY_PLAN.json'),
                         source_pins=len(sources),historical_pins=len(historical),expected_streams=expected)))


if __name__=='__main__':
    main()
