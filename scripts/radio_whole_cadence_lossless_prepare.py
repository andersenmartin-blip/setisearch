"""Build prospective fixed engineering recipe, full executable freeze and genesis."""
import hashlib
import json
from pathlib import Path
import resource
import time
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_runtime_radio import capture
from seti_repeater.whole_cadence_lossless_radio import PREFIX,genesis
from radio_whole_cadence_lossless_live import definitions,RECIPE,FREEZE
ROOT=Path(__file__).resolve().parents[1]
def main():
    started=time.monotonic()
    witness={'schema':'radio-lossless-fixed-witness-v1','namespace':PREFIX,'source_requests':0,
        'scientific_allocations':0,'purpose':'exact ASCII transport and atomic two-artifact seal'}
    data={'witness.json':canonical(witness),'payload.bin':bytes((i*29+11)%256 for i in range(524305))}
    recipe={'schema':'radio-lossless-fixed-engineering-recipe-v1','namespace':PREFIX,'mode':'ENGINEERING_ONLY',
        'witness':witness,'payload_rule':'bytes((i*29+11)%256 for i in range(524305))',
        'artifacts':{k:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for k,v in data.items()},
        'second_case':{'payload_rule':"b'x'*1024",'normal_physical_cap':256,'failure_reserve':8192,
            'expected_outcome':'failed','failure':'physical_normal_quota_exceeded'},
        'old_scope':{'calls':103,'active_seconds_charged':964.719075146,'spent_case_milliseconds':1500000,
            'spent_case_bytes':1048576,'closed_incomplete_not_resumed':True}}
    (ROOT/RECIPE).write_bytes(canonical(recipe))
    inputs=[RECIPE,'RADIO_WHOLE_CADENCE_LOSSLESS_2026-09-28_SCOPE.md',
        'scripts/radio_whole_cadence_lossless_broker.js','tests/test_radio_whole_cadence_lossless.py',
        'tests/test_radio_lossless_handoff.py','results_radio_whole_cadence_lossless_2026-09-28/new_tests.txt',
        'results_radio_whole_cadence_remote_2026-09-28/disposition.json',
        'results_radio_whole_cadence_remote_2026-09-28/postflight.json']
    freeze=capture(ROOT,inputs);raw=canonical(freeze);(ROOT/FREEZE).write_bytes(raw)
    sha=hashlib.sha256(raw).hexdigest();m=definitions(sha,recipe)
    dest=ROOT/PREFIX;dest.mkdir(parents=True,exist_ok=True)
    if (dest/'ledger.json').exists():raise ValueError('Never replace existing genesis')
    (dest/'ledger.json').write_bytes(canonical(genesis(m)))
    result={'freeze_sha256':sha,'code_files':len(freeze['code_sha256s']),
        'runtime_files':len(freeze['runtime_sha256s']),'input_files':len(freeze['input_sha256s']),
        'case_identities':[c['case_identity'] for c in m['cases']],
        'elapsed_seconds':time.monotonic()-started,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'scientific_execution_authorized':False}
    (ROOT/'results_radio_whole_cadence_lossless_2026-09-28/preparation.json').write_bytes(canonical(result))
    print(json.dumps(result))
if __name__=='__main__':main()
