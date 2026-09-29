#!/usr/bin/env python3
"""Read-only lower bound on the known native workload's receiver evidence.

Reads an immutable public archive. No project modules, RNG, detector, physical
decisions, scientific allocation or artificial receiver report are constructed.
All unknown numeric receiver fields contribute just one JSON byte to the bound.
"""
import base64
import hashlib
import io
import json
import lzma
from pathlib import Path
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]
BASE='f6a91931282bcd38a12a48625dfe784e6c8f0172'
ARCHIVE='results_radio_native_chain_engineering_2026-09-29/'
SOURCE='live01/partial_physical_or_retention.json'
SOURCE_SHA='6a205b43d53f0a582d73d6d88c1501a0d4d8cd992a974dc8ff6328d300296dfd'


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def sha(data):return hashlib.sha256(data).hexdigest()


def git_blobs(paths):
    raw=subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,
        input=''.join(BASE+':'+p+'\n' for p in paths).encode())
    result={};offset=0
    for path in paths:
        end=raw.index(b'\n',offset);header=raw[offset:end].split()
        if len(header)!=3 or header[1]!=b'blob':raise ValueError('Missing pinned Git blob: '+path)
        size=int(header[2]);data=raw[end+1:end+1+size];offset=end+size+2
        if len(data)!=size or raw[offset-1:offset]!=b'\n':raise ValueError('Git framing differs')
        if hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest()!=header[0].decode():
            raise ValueError('Git object hash differs')
        result[path]=data
    if offset!=len(raw):raise ValueError('Trailing Git bytes')
    return result


def main():
    paths=[ARCHIVE+'archive_manifest.json','src/seti_repeater/physical_evidence_radio.py',
           'src/seti_repeater/pipeline_radio.py','src/seti_repeater/pipeline_receiver_radio.py',
           'src/seti_repeater/whole_cadence_physical_radio.py',
           'results_radio_whole_cadence_compact_2026-09-28/phase_budget_proposed.json']
    inputs=git_blobs(paths);manifest=json.loads(inputs[paths[0]])
    parts=git_blobs([ARCHIVE+r['path'] for r in manifest['chunks']]);encoded=[]
    for r in manifest['chunks']:
        data=parts[ARCHIVE+r['path']]
        if len(data)!=r['bytes'] or sha(data)!=r['sha256']:raise ValueError('Archive chunk differs')
        encoded.append(data)
    encoded=b''.join(encoded)
    if len(encoded)!=manifest['base64_bytes']:raise ValueError('Archive base64 length differs')
    xz=base64.b64decode(encoded,validate=True)
    if len(xz)!=manifest['xz_bytes'] or sha(xz)!=manifest['xz_sha256']:raise ValueError('Archive xz differs')
    tar_bytes=lzma.decompress(xz)
    if len(tar_bytes)!=manifest['tar_bytes']:raise ValueError('Archive tar length differs')
    with tarfile.open(fileobj=io.BytesIO(tar_bytes),mode='r:') as archive:
        matches=[m for m in archive.getmembers() if m.name==SOURCE]
        if len(matches)!=1 or not matches[0].isfile():raise ValueError('Unique regular report required')
        source=archive.extractfile(matches[0]).read()
    source_pin=next(r for r in manifest['files'] if r['path']==SOURCE)
    if sha(source)!=SOURCE_SHA or sha(source)!=source_pin['sha256'] or len(source)!=source_pin['bytes']:
        raise ValueError('Closed source report differs')
    report=json.loads(source);members=report['retention']['retained']['on']
    if len({r['record_id'] for r in members})!=len(members):raise ValueError('Duplicate retained member')
    query_count=sum(len(r['active_epochs_zero_based']) for r in members)
    signatures_bytes=2+max(0,len(members)-1);queries_bytes=2+max(0,query_count-1)
    activity_counts={}
    for r in members:
        epochs=r['active_epochs_zero_based'];activity_counts[str(len(epochs))]=activity_counts.get(str(len(epochs)),0)+1
        signature_array_bytes=2+max(0,len(epochs)-1)
        for epoch in epochs:
            # These dictionaries are byte-count terms only. Their zero values
            # are NOT measurements, admissible signatures, receipts or outputs.
            signature_array_bytes+=len(canonical({'epoch_zero_based':epoch,
                'predicted_mid_mhz':0,'peak_frequency_mhz':0,'peak_snr':0,
                'offset_from_prediction_hz':0}))
            queries_bytes+=len(canonical({'record_id':r['record_id'],'scan':f'epoch{epoch+1}_on',
                'adapter':'radio-synthetic-stationary-native-peak-v1',
                'cache_identity':'0'*64,'source_identity':'0'*64,
                'template_index':r['template_index'],'score_index':r['proxy_carrier_index'],
                'width':r['spectral_width_channels'],'local_half_width_hz':100.,
                'raw_start':0,'raw_stop':0,'native_channels':0,'winning_raw_index':0,
                'tie_break':'first ascending native-channel maximum','mask_applied':False}))
        signatures_bytes+=len(canonical(r['record_id']))+1+signature_array_bytes
    # Preserve only the already accumulated upstream fields. Completion uses
    # true (4 bytes), shorter than false (5). Remove the obsolete failure.
    prefix={k:v for k,v in report.items() if k!='failure'};prefix['complete']=True
    prefix_bytes=len(canonical(prefix))
    receipt_bytes=len(b'{"queries":')+queries_bytes+1
    bound=prefix_bytes+1+len(canonical('receiver_signatures'))+1+signatures_bytes
    bound+=1+len(canonical('receiver_receipt'))+1+receipt_bytes
    code=inputs[paths[1]].decode()
    if 'MAX_BYTES = 24*1024**2' not in code or 'if expanded>MAX_BYTES:' not in code:
        raise ValueError('Pinned physical reader bound differs')
    logical_limit=24*1024**2
    budget=json.loads(inputs[paths[-1]])
    scientific_case_limit=budget['phases']['evaluation']['bytes_per_case']
    base_artifacts=[r for r in manifest['files'] if r['path'].startswith('live01/case4/')]
    existing_bytes=sum(r['bytes'] for r in base_artifacts)
    if len(base_artifacts)!=7 or existing_bytes!=2004352:raise ValueError('Seven original base artifacts required')
    if bound<=logical_limit:raise ValueError('Expected conservative obstruction not established')
    result={'schema':'radio-receiver-evidence-lower-bound-v1',
        'status':'CURRENT_READER_CANNOT_RESTORE_OBSERVED_WORKLOAD_WITH_COMPLETE_RECEIVER_EVIDENCE',
        'evidence_commit':BASE,'source_path':ARCHIVE+SOURCE,'source_sha256':SOURCE_SHA,
        'source_bytes':len(source),'input_sha256s':{p:sha(data) for p,data in inputs.items()},
        'archive_xz_sha256':manifest['xz_sha256'],'retained_on_members':len(members),
        'receiver_query_count':query_count,'active_epoch_count_distribution':activity_counts,
        'preserved_prefix_bytes_without_failure_with_shortest_completion_flag':prefix_bytes,
        'signature_mapping_lower_bound_bytes':signatures_bytes,
        'native_query_list_lower_bound_bytes':queries_bytes,
        'physical_report_lower_bound_bytes':bound,
        'current_reader_logical_limit_bytes':logical_limit,
        'logical_limit_excess_bytes':bound-logical_limit,
        'scientific_evaluation_stored_case_limit_bytes':scientific_case_limit,
        'existing_seven_base_artifact_bytes':existing_bytes,
        'uncompressed_case_representation_lower_bound_bytes':existing_bytes+bound,
        'omitted_positive_costs':['receiver source/context receipt fields and bridge wrapper',
            'actual numeric precision','normalized signature hash','identity partition',
            'receiver-alias witnesses','final decisions and clusters','final digest and stage accounting',
            'physical checkpoint descriptors/footer and outer seal/footer'],
        'scope_limits':['Bound for this already observed retained-member workload, not every future draw.',
            'Uncompressed logical lower bound, not a lower bound on a different lossless compressed representation.',
            'No extrapolation to full 151-case storage or runtime.',
            'No synthetic receiver signature or receipt is issued from the counting placeholders.'],
        'new_random_values':0,'new_native_scores':0,'new_receiver_measurements':0,
        'new_telescope_reads':0,'new_allocations':0,'historical_cases_reexecuted':False,
        'limits_changed':False,'scientific_127_24_activated':False}
    print(json.dumps(result,sort_keys=True,indent=2))


if __name__=='__main__':main()
