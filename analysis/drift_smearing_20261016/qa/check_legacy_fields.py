#!/usr/bin/env python3
"""Supplemental hash-pinned old central-row and summed-score compatibility."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
QA=Path(__file__).resolve().parent


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    scope_bytes=(ROOT/'SCOPE.json').read_bytes()
    assert sha(scope_bytes)=='115273d98a97fbad32cf6f2969340a73dc517e96d56ad613684bc7c1828079d2'
    scope=json.loads(scope_bytes)
    metadata_bytes=(ROOT/'SOURCE_METADATA.json').read_bytes()
    assert sha(metadata_bytes)==scope['source_metadata']['sha256']
    metadata=json.loads(metadata_bytes)
    old={p['profile_id']:p for p in metadata['profiles']}
    qa=json.loads((QA/'QA_RECEIPT.json').read_bytes())
    assert qa['status']=='PASS_INDEPENDENT_RAW_RECONSTRUCTION'
    assert qa['maximum_absolute_differences']['per_row_central_standardized']==0
    results=json.loads((ROOT/'results/RESULTS.json').read_bytes())
    assert sha((ROOT/'results/RESULTS.json').read_bytes())==qa['primary_result_pin']['sha256']
    max_row_error=max_fixed4_error=max_full16_error=max_original_origin_error=0.0
    rows_checked=0
    for p,new in zip(scope['profiles'],results['profiles']):
        assert p['profile_id']==new['profile_id']
        prior=old[p['source_profile_id']]
        assert p['original_fixed4_score']==prior['fixed_four_row_score']
        spectra_path=ROOT/new['spectra']['path']
        assert sha(spectra_path.read_bytes())==new['spectra']['sha256']
        with np.load(spectra_path,allow_pickle=False) as data:
            z=data['per_row_central_standardized'][0]
            old_z=np.asarray(prior['row_standardized_box_sum'])
            error=float(np.max(np.abs(z-old_z)))
            max_row_error=max(max_row_error,error)
            assert error<1e-12
            assert list(data['rounded_centers'][0])==prior['rounded_absolute_centers']
            score4=math.fsum(z[p['original_four_rows']])/2
            score16=math.fsum(z)/4
            error4=abs(score4-prior['fixed_four_row_score'])
            error16=abs(score16-prior['fixed_full16_score'])
            max_fixed4_error=max(max_fixed4_error,error4)
            max_full16_error=max(max_full16_error,error16)
            assert error4<1e-12 and error16<1e-12
            if p['origin_scan_id']==p['context_scan_id']:
                origin_error=abs(score4-prior['selected_track']['score'])
                max_original_origin_error=max(max_original_origin_error,origin_error)
                assert origin_error<1e-12
            rows_checked+=len(z)
    assert rows_checked==864
    out=dict(status='PASS_LEGACY_ROW_AND_SUM_COMPATIBILITY',profiles_checked=54,
        zero_offset_central_rows_checked=rows_checked,original4_scores_checked=54,
        full16_scores_checked=54,own_origin_primary_scores_checked=9,
        maximum_row_error=max_row_error,maximum_original4_error=max_fixed4_error,
        maximum_full16_error=max_full16_error,maximum_origin_primary_score_error=max_original_origin_error,
        source_code_sha256=sha(Path(__file__).read_bytes()),
        source_metadata_sha256=sha(metadata_bytes),parent_QA_receipt_sha256=sha((QA/'QA_RECEIPT.json').read_bytes()),
        qualification_changed=False)
    with (QA/'LEGACY_COMPATIBILITY_RECEIPT.json').open('x') as f:
        json.dump(out,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(out,indent=2))


if __name__=='__main__':
    main()
