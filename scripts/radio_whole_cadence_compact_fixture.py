#!/usr/bin/env python3
"""Two fixed compact archive audits using published score/receipt bytes only."""
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import time
import traceback
from unittest.mock import patch
from radio_receiver_adapter_common import ROOT,context
from seti_repeater.pipeline_receiver_radio import NativeRun
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.empty_null_radio import canonical
from seti_repeater import whole_cadence_compact_radio as c

OUT=ROOT/'results_radio_whole_cadence_compact_2026-09-28'
JOURNAL=ROOT/'results_radio_whole_cadence_journal_2026-09-28/native01'
RENDER=ROOT/'results_radio_whole_cadence_physical_2026-09-28/render01'


def inputs(index):
    paths={'sources.json':JOURNAL/f'case{index}/source_metadata.json',
        'scores.json':JOURNAL/f'case{index}/score_metadata.json','scores.npz':JOURNAL/f'case{index}/scores.npz',
        'maximum.json':JOURNAL/f'case{index}/maximum.json','renderer.json':RENDER/f'case{index}_receipt.json'}
    parts={name:p.read_bytes() for name,p in paths.items()}
    renderer=json.loads(parts['renderer.json']);source=json.loads(parts['sources.json'])
    ctx=context('calibration' if index==0 else 'validation')
    binding={'case_identity':source['case_identity'],'plan_sha256':renderer['draw_plan_sha256'],
        'context_sha256':ctx.identity,'source_contract_sha256':hashlib.sha256(ctx.factor_contract.source_contract_bytes).hexdigest(),
        'noise_law_sha256':source['noise_law_sha256']}
    return ctx,binding,parts,paths


def write(name,value):
    with (OUT/name).open('xb') as f:f.write(canonical(value))


def main():
    start=time.monotonic();OUT.mkdir(exist_ok=False)
    try:
        all_inputs=[]
        for i in range(2):
            ctx,binding,parts,paths=inputs(i)
            pins={name:hashlib.sha256(data).hexdigest() for name,data in parts.items()}
            for name,p in paths.items():
                original=subprocess.check_output(['git','show','521e1c128fb21fc8fe8ae5d99b6fa1e17a805bda:'+str(p.relative_to(ROOT))],cwd=ROOT)
                if original!=parts[name]:raise ValueError('Published compact input differs: '+name)
            all_inputs.append({'case_index':i,'binding':binding,'artifact_sha256s':pins,
                'published_commit':'521e1c128fb21fc8fe8ae5d99b6fa1e17a805bda',
                'artifact_paths':{name:str(p.relative_to(ROOT)) for name,p in paths.items()},'cap_bytes':4*c.MIB if i==0 else 18*c.MIB})
        write('fixed_inputs_before_audit.json',all_inputs)
        results=[]
        with patch('numpy.random.Generator',side_effect=AssertionError('No RNG')), \
             patch.object(NativeRun,'__init__',side_effect=AssertionError('No NativeRun reconstruction')), \
             patch.object(NativeRun,'build_store',side_effect=AssertionError('No scores')), \
             patch.object(NativeRun,'cache',side_effect=AssertionError('No cache')):
            for i in range(2):
                ctx,binding,parts,paths=inputs(i);info=all_inputs[i]
                result=c.audit(ctx,binding,parts,expected_sha256s=info['artifact_sha256s'],byte_cap=info['cap_bytes'])
                write(f'case{i}_audit.json',result);results.append(result)
        raw=(ROOT/'config/radio_whole_cadence_null_proposal_20260928.json').read_bytes()
        budget=c.phase_budget(raw);write('phase_budget_proposed.json',budget)
        for case in budget['cases']:
            if c.reservation(raw,budget,case['case_identity'])!=case:raise ValueError('Budget case reservation differs')
        # Exact worst-case payload for np.savez uncompressed scores, before metadata;
        # no Gaussian compression assumption or real source draw is used.
        result={'schema':'radio-whole-cadence-compact-engineering-result-v1',
            'status':'TWO_COMPACT_SCORE_RECEIPT_AUDITS_PASS','cases':[
                {'case_index':i,'bytes':r['total_bytes'],'cap_bytes':r['byte_cap'],'score_vectors':r['score_vectors'],
                 'score_values':r['score_values'],'source_rows':r['row_receipts_bound'],
                 'original_maximum_receipt_sha256':r['original_native_maximum_sha256']} for i,r in enumerate(results)],
            'all_score_values_preserved':True,'omitted_source_arrays_restorable_from_this_format':False,
            'old_full_archives_preserved':True,'gaussian_compression_ratio_assumed':False,
            'phase_budget_sha256':budget['budget_sha256'],'prospective_seconds':budget['total_milliseconds']/1000,
            'prospective_evidence_bytes':budget['total_evidence_bytes'],
            'new_allocations':0,'new_source_values':0,'new_score_values_computed':0,'new_gaussian_values':0,
            'active_seconds':time.monotonic()-start,'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'external_store_and_runtime_freeze_qualified':False,'proposal_status':'PROPOSED_NOT_ACTIVATED'}
        write('result.json',result);print(json.dumps(result,indent=2))
    except BaseException as error:
        write('error.json',{'error':repr(error),'traceback':traceback.format_exc(),'automatic_retry_authorized':False});raise


if __name__=='__main__':main()
