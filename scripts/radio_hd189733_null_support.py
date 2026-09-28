#!/usr/bin/env python3
"""Single bounded diagnosis from retained score bytes; no realization renderer."""
import hashlib
import json
from pathlib import Path
import resource
import time

import numpy as np

from seti_repeater import mask_m43u as masks
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43g as native

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results_radio_hd189733_panel_2026-09-28'


def main():
    out=BASE/'diagnosis01';out.mkdir(exist_ok=False);start=time.monotonic()
    cfg=json.loads((ROOT/'config/radio_hd189733_panel_20260928.json').read_text())
    result=json.loads((BASE/'attempt01/result.json').read_text())
    if result['status']!='CALIBRATION_FAILED_EVALUATIONS_UNOPENED':
        raise ValueError('This fixed scope requires the empty-support calibration failure')
    summaries=[];checked=0
    for i in range(3):
        record_path=BASE/f'attempt01/calibration{i:02d}.json';record=json.loads(record_path.read_text())
        archive=ROOT/record['scores']['path'];raw=archive.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=record['scores']['sha256']:raise ValueError('Archive pin mismatch')
        arrays={}
        with np.load(archive,allow_pickle=False) as data:
            if set(data.files)!={str(j) for j in range(len(record['scores']['keys']))}:raise ValueError('Archive inventory mismatch')
            for j,k in enumerate(record['scores']['keys']):
                value=data[str(j)];receipt=record['scores']['vectors'][j]
                if list(k)!=receipt['key'] or native.array_hash(value)!=receipt['payload_sha256']:raise ValueError('Vector pin mismatch')
                if value.dtype!=np.dtype('<f4') or value.shape!=(3,99):raise ValueError('Vector schema mismatch')
                if not np.isfinite(value).all():raise ValueError('Nonfinite retained score')
                ident=native.digest({'provenance':record['scores']['score_provenance'],'key':k,'payload':native.array_hash(value)})
                if ident!=receipt['id']:raise ValueError('Vector ancestry mismatch')
                arrays[tuple(k)]=value;checked+=1
        tables=[(0,0,0)]+cfg['scramble_tables'][i]
        counts=np.zeros(len(tables),dtype=np.int64);per=[];masked=0
        for t in range(81):
            full={w:arrays['on',t,w] for w in core.M37_SPECTRAL_WIDTHS}
            mask=masks.build_mask(full.__getitem__,'neighbor9')[:,9:90]
            if hashlib.sha256(mask.tobytes()).hexdigest()!=record['support']['mask_sha256s'][str(t)]:raise ValueError('Mask pin mismatch')
            masked+=int(mask.sum())
            for w in core.M37_SPECTRAL_WIDTHS:
                values=full[w][:,9:90];above=values>=3.;eligible=above&~mask
                local=[]
                for j,shifts in enumerate(tables):
                    shifted=np.stack([np.roll(eligible[e],shift) for e,shift in enumerate(shifts)])
                    n=sum(int(np.all(shifted[list(subset)],axis=0).sum()) for subset in core.M37_ACTIVITY_SUBSETS)
                    local.append(n);counts[j]+=n
                per.append({'template':t,'width':w,'maximum_score_by_epoch':values.max(axis=1).tolist(),
                    'above_active_floor_by_epoch':above.sum(axis=1).tolist(),
                    'eligible_after_mask_by_epoch':eligible.sum(axis=1).tolist(),
                    'eligible_observed_hypothesis_cells':local[0],
                    'eligible_shifted_hypothesis_cells':local[1:]})
            if time.monotonic()-start>120 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>256*1024**2:
                raise RuntimeError('Diagnosis resource cap')
        observed=record['support']['observed_maximum'] is not None
        retained=[x is not None for x in record['support']['null_maxima']]
        if bool(counts[0])!=observed or (counts[1:]>0).tolist()!=retained:raise ValueError('Independent eligibility coverage disagrees')
        evidence={'schema':'radio-receiver-retained-null-support-diagnosis-v1','calibration_index':i,
            'input_record_sha256':hashlib.sha256(record_path.read_bytes()).hexdigest(),
            'score_archive_sha256':record['scores']['sha256'],'masked_cells':masked,
            'eligible_observed_hypothesis_cells':int(counts[0]),
            'eligible_shifted_hypothesis_cells':counts[1:].tolist(),
            'empty_shift_indices':np.flatnonzero(counts[1:]==0).tolist(),
            'empty_shift_triples':[cfg['scramble_tables'][i][j] for j in np.flatnonzero(counts[1:]==0)],
            'all_retained_support_flags_reproduced':True,'per_template_width':per}
        path=out/f'calibration{i:02d}.json';path.write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
        summaries.append({k:v for k,v in evidence.items() if k not in ('per_template_width','empty_shift_triples','eligible_shifted_hypothesis_cells')})
    summary={'schema':'radio-receiver-null-support-diagnosis-result-v1','status':'EMPTY_SUPPORT_EXPLAINED_BY_FIXED_ELIGIBILITY',
        'calibrations':summaries,'score_vectors_verified':checked,
        'null_support_flags_independently_compared':381,'diagnosis_attempts_consumed':1,
        'settings_changed':False,'threshold_computed':False,'new_calibrations':0,'evaluation_values_opened':0,
        'new_source_requests':0,'active_seconds':time.monotonic()-start,
        'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'missing_capability':'A prospectively justified calibration treatment of the no-eligible-hypothesis probability mass and a fresh authorized validation allocation; finite conditional-tail qualification is absent.',
        'repair_or_replacement_authorized':False,
        'scope_sha256':hashlib.sha256((ROOT/'RADIO_HD189733_NULL_SUPPORT_2026-09-28_SCOPE.md').read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    if sum(p.stat().st_size for p in out.iterdir())>16*1024**2:raise RuntimeError('Diagnosis evidence cap')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
