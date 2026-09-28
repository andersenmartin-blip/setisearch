"""Archive one new proposed envelope from fixed retained engineering bytes."""
from pathlib import Path
import hashlib
import json
import resource
import time
from seti_repeater import whole_cadence_ascii_radio as a
from seti_repeater.empty_null_radio import canonical

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_radio_whole_cadence_remote_2026-09-28/ascii01'
INPUT=ROOT/'results_radio_whole_cadence_remote_2026-09-28/run02/case/payload.bin'
CASE='89317409d64880b9afbee488b60273b48697bbf19fd4fc78b311d16f552abd23'


def main():
    started=time.monotonic();raw=INPUT.read_bytes()
    if hashlib.sha256(raw).hexdigest()!='08f24e98d0765b5cf5f4aca1a76b78d130f51706514d7ca87093a3a02bb07f98' or len(raw)!=262161:
        raise ValueError('Retained deterministic payload pin differs')
    args={'case_identity':CASE,'name':'payload.bin','physical_byte_cap':1048576}
    parts,receipt=a.encode(raw,**args);OUT.mkdir(parents=True,exist_ok=False)
    for name,value in parts.items():(OUT/name).write_bytes(value)
    restored={p.name:p.read_bytes() for p in OUT.iterdir()}
    if a.decode(restored,expected_manifest_sha256=receipt['manifest_sha256'],**args)!=raw:raise AssertionError('Exact restoration failed')
    result={**receipt,'input_sha256':a.sha(raw),'input_commit':'b49a315e6312839d423a3be65b08a7935c759b74',
        'original_case_stays_closed_failed':True,'new_source_requests':0,'new_prng_constructions':0,'scientific_allocations':0,
        'encoded_parts_sha256s':{k:a.sha(v) for k,v in parts.items()},'elapsed_seconds':time.monotonic()-started,
        'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'conservative_time_charge_seconds':60,'new_live_scope_authorized':False}
    if result['elapsed_seconds']>60 or result['peak_rss_bytes']>512*1024**2:raise ValueError('Offline preparation cap exceeded')
    (OUT/'result.json').write_bytes(canonical(result));print(json.dumps(result))

if __name__=='__main__':main()
