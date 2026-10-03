"""Prepare new blocked metadata from 25 independently pinned original inputs.

No project source is imported and no spectral, fixture or reservation file is
opened. CLI pins are mandatory; output is exclusive and is never admission.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path,cap):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if before.st_size>cap:raise ValueError('Bounded metadata file required')
        chunks=[];total=0
        while True:
            part=os.read(fd,min(65536,cap+1-total))
            if not part:break
            total+=len(part)
            if total>cap:raise ValueError('Metadata file exceeded actual read cap')
            chunks.append(part)
        after=os.fstat(fd)
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise ValueError('Metadata changed during read')
        return b''.join(chunks)
    finally:os.close(fd)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--pin-map-sha256',required=True)
    parser.add_argument('--admission-code-sha256',required=True)
    args=parser.parse_args();root=Path(args.root);out=Path(__file__).parent
    pinpath='results_radio_hd189733_metadata_preparation_20261002a/evidence_pins.json'
    pinraw=read(root/pinpath,32768)
    if sha(pinraw)!=args.pin_map_sha256:raise ValueError('Independent original pin-map SHA differs')
    pins=json.loads(pinraw);docs={};checked=[]
    if len(pins)!=25:raise ValueError('Exact retained 25-input closure required')
    for path,pin in sorted(pins.items()):
        if path.startswith('/') or any(p in ('','..','.') for p in path.split('/')):raise ValueError('Unsafe original input path')
        raw=read(root/path,524288)
        if set(pin)!={'bytes','sha256'} or type(pin['bytes']) is not int or len(raw)!=pin['bytes'] or sha(raw)!=pin['sha256']:
            raise ValueError('Original independent raw pin differs: '+path)
        checked.append({'path':path,**pin})
        if path.endswith('.json'):docs[path]=json.loads(raw)
    sourcepath='config/radio_hd189733_source_preparation_20260927.json';proposalpath='config/radio_whole_cadence_null_proposal_20260928.json'
    designpath='results_radio_hd189733_geometry_2026-09-27/window_geometry.json';windowpath='results_radio_hd189733_geometry_2026-09-27/window_identity_contract_v2.json'
    bankpath='results_radio_hd189733_receiver_2026-09-28/bank_records.json'
    source,proposal,design,windows,banks=[docs[k] for k in (sourcepath,proposalpath,designpath,windowpath,bankpath)]
    if (source['cadence_id']!=85030 or source['archive_target']!='HIP98505'
        or source['source_inventory_sha256']!=sha(canonical(source['scans'])+b'\n')
        or proposal['status']!='PROPOSED_NOT_ACTIVATED' or len(proposal['cases'])!=151):
        raise ValueError('Preserved source/proposal semantics differ')
    for case in proposal['cases']:
        if (sha(canonical({k:v for k,v in case.items() if k!='identity'}))!=case['identity']
            or case['source_contract_sha256']!=pins[sourcepath]['sha256'] or case['executed'] is not False or case['budget_charged'] is not False):
            raise ValueError('Original proposal case differs')
    basis={'source_inventory_sha256':source['source_inventory_sha256'],'source_metadata_sha256':pins[sourcepath]['sha256'],
        'window_design_sha256':pins[designpath]['sha256'],'window_contract_sha256':pins[windowpath]['sha256'],
        'receiver_bank_records_sha256':pins[bankpath]['sha256'],'proposal_sha256':pins[proposalpath]['sha256'],
        'window_identities':{row['role']:row['identity'] for row in design['windows']},
        'receiver_bank_sha256s':{row['provenance']['role']:row['bank_identity'] for row in banks},
        'receiver_context_sha256s':{r:next(c['context_sha256'] for c in proposal['cases'] if c['role']==('calibration' if r=='calibration' else 'evaluation')) for r in ('calibration','validation')},
        'ordered_case_identities':[c['identity'] for c in proposal['cases']],
        'case_bindings':[{**{k:c[k] for k in ('identity','role','context_sha256','source_contract_sha256','noise_law_sha256','seed')},
            'recipe_kind':c['recipe']['kind'],'recipe_sha256':sha(canonical(c['recipe']))} for c in proposal['cases']]}
    code=out/'scientific_admission.py';code_raw=read(code,131072)
    if sha(code_raw)!=args.admission_code_sha256:raise ValueError('Independent admission source pin differs')
    spec=importlib.util.spec_from_loader('held_prospective_admission',loader=None)
    a=importlib.util.module_from_spec(spec);sys.modules[spec.name]=a
    exec(compile(code_raw,str(code),'exec'),a.__dict__)
    a._basis(basis)
    basisdoc={'schema':'radio-preserved-scientific-basis-v1','evidence_domain':'preserved-metadata-only','basis':basis}
    limits={'schema':'radio-source-scientific-exact-limits-v1','evidence_domain':'prospective-preparation-only','scientific':a.SCIENTIFIC_LIMITS,
        'acquisition':a.ACQUISITION_LIMITS,'stop_date':'2026-10-09','refund_policy':'no-refund-no-retry-no-resume'}
    limitsraw=canonical(limits)+b'\n'
    protocol={'schema':'radio-source-specific-detached-trial-protocol-v1','evidence_domain':'prospective-preparation-only','basis_sha256':a.digest(basis),
        'limits_sha256':sha(limitsraw),'source_inventory_sha256':source['source_inventory_sha256'],'status':'PENDING_EXTERNAL_QUALIFICATION',
        'search':{'rate_tenths':list(range(-40,41)),'widths_channels':[1,3,5,9,17,33,65,129],'activity_subsets':[[0,1],[0,2],[1,2],[0,1,2]],'minimum_active_epoch_snr':3,'stack_statistic':'sum','primary':'neighbor9'},
        'rank':{'reference_count':127,'denominator':128,'floor_snr':10,'inclusive_numerator':'1 + count(reference >= observed member)','ceiling':[1,100],'keep_every_empty':True,'ties_randomized':False},
        'evaluation_recipes':{'on_signal':10,'matched_on_off':10,'single_adjacent_off':2,'noise_null':2},
        'pilot':{'source':'HIP98505','cadence_id':85030,'role':'pilot','scans':list(a.LABELS),'maximum_trials':1,'settings_selected_by_evaluation':False,'flux_or_eirp_claim_authorized':False}}
    files={'preserved-basis.json':canonical(basisdoc)+b'\n','prospective-exact-limits.json':limitsraw,'prospective-source-specific-protocol.json':canonical(protocol)+b'\n'}
    artifact_pins=[]
    for name,raw in files.items():
        with (out/name).open('xb') as stream:
            if stream.write(raw)!=len(raw):raise OSError('Short metadata write')
        artifact_pins.append({'path':str((out/name).relative_to(root)),'bytes':len(raw),'sha256':sha(raw)})
    original=read(root/'src/seti_repeater/prospective_source_metadata_radio.py',65536)
    if len(original)!=31819 or sha(original)!='2852d23d30619e2406c36f46ffee2452fd64cd3834e31f18a7bb1f0ac8081360':
        raise ValueError('Original permanently blocked constructor changed')
    receipt={'schema':'radio-detached-scientific-protocol-preparation-receipt-v1','status':'PROSPECTIVE_METADATA_PREPARED_EXECUTION_BLOCKED',
        'external_pin_map':{'path':pinpath,'bytes':len(pinraw),'sha256':sha(pinraw)},'checked_original_inputs':checked,'checked_input_count':len(checked),
        'preserved_case_count':151,'ordered_calibration_count':127,'ordered_evaluation_count':24,'preserved_source_inventory_sha256':source['source_inventory_sha256'],
        'preserved_basis_sha256':a.digest(basis),'artifacts':artifact_pins,'scientific_readiness':False,
        'workload_counters':{'native_reservations':0,'scientific_allocations':0,'telescope_reads':0,'rng_draws':0},
        'actual_codec_or_transport_or_scientific_certificate_issued':False,'original_constructor':{'bytes':len(original),'sha256':sha(original),'unchanged':True},
        'generator_code_sha256':sha(read(Path(__file__),131072)),'admission_code_sha256':args.admission_code_sha256}
    with (out/'protocol-preparation-receipt.json').open('xb') as stream:stream.write(canonical(receipt)+b'\n')
    print(json.dumps({'status':receipt['status'],'checked_inputs':len(checked),'preserved_cases':151,'written_files':4,'scientific_readiness':False}))


if __name__=='__main__':
    main()
