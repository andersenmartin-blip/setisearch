#!/usr/bin/env python3
"""One fixed exact method audit; no old scores or new random data are read."""
from fractions import Fraction
from itertools import combinations_with_replacement
import hashlib
import json
from pathlib import Path
import resource
import time

from seti_repeater import empty_null_radio as method

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_radio_empty_null_method_2026-09-28/exact01'


def write(name,value):
    path=OUT/name
    with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')


def ratio(value):return {'numerator':value.numerator,'denominator':value.denominator}


def main():
    OUT.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    alphabet=[method.EMPTY]+[method.Maximum('finite',x) for x in (-2,0,1,3)]
    cases=[];rank_queries=inequalities=0
    for n in range(2,9):
        for symbols in combinations_with_replacement(range(5),n):
            samples=[alphabet[j] for j in symbols]
            ranks=[method.inclusive_rank(samples[i],samples[:i]+samples[i+1:]) for i in range(n)]
            rank_queries+=n
            actual=[]
            for k in range(n+1):
                rejected=sum(r<=Fraction(k,n) for r in ranks)
                # Independently of rank code, an exchangeable distinguished
                # position is uniform over n slots. The theorem's bound is k.
                if rejected>k:raise AssertionError(('rank bound',symbols,k,rejected))
                inequalities+=1;actual.append(rejected)
            cases.append({'symbols':list(symbols),'sample_size':n,
                'upper_rank_numerators':[int(r*n) for r in ranks],
                'rejected_positions_by_cutoff_k_over_n':actual})
        if time.monotonic()-start>600:raise RuntimeError('Exact audit time cap')
    write('exchangeable_histograms.json',{'alphabet':[x.record() for x in alphabet],
        'observed_position_uniform_given_multiset':True,'cases':cases})

    # Explicit sampling-universe audit, not a demand that a sampled subset
    # itself form a group. Random uniform subsets of a valid group may work.
    universe={(0,0)}|{(a,b) for a in range(32,49) for b in range(32,49)}
    add=lambda a,b:tuple((x+y)%81 for x,y in zip(a,b))
    witness=(32,32);summed=add(witness,witness);inverse=(49,49)
    assert summed not in universe and inverse not in universe
    group={'ambient_group':'Z_81 x Z_81','ambient_size':81**2,
        'guarded_sampling_universe_including_identity_size':len(universe),
        'addition_witness':{'a':list(witness),'b':list(witness),'sum':list(summed),'sum_in_universe':False},
        'inverse_witness':{'element':list(witness),'inverse':list(inverse),'inverse_in_universe':False},
        'sample_subset_closure_required_by_standard_random_permutation_theorem':False,
        'required_bridge_missing':'uniform group sampling plus null-law invariance, or another specific validity proof',
        'actual_detector_false_alarm_rate_measured':False}
    write('guarded_shift_assumptions.json',group)

    # Fixed abstract counterexample to arbitrary-transform ranks.
    values=[method.Maximum('finite',x) for x in (4,3,2,1,0)]
    ranks=[method.inclusive_rank(values[g],[values[(g+1)%5]]) for g in range(5)]
    rejection=Fraction(sum(x<=Fraction(1,2) for x in ranks),5)
    assert rejection==Fraction(4,5)
    write('restricted_transform_counterexample.json',{'uniform_observed_origins':list(range(5)),
        'statistic':[4,3,2,1,0],'reference_transformation':'next origin modulo 5',
        'inclusive_ranks':[ratio(x) for x in ranks],'nominal_level':ratio(Fraction(1,2)),
        'actual_rejection_probability':ratio(rejection),
        'is_actual_receiver_pipeline_or_observed_data':False})

    # Unit-variance raw variables; overlap/w is exact boxcar covariance.
    covariance=lambda i,j:Fraction(max(0,3-abs(i-j)),3)
    original=covariance(0,1);rolled=covariance(80,0)
    assert original==Fraction(2,3) and rolled==0
    write('nonperiodic_boxcar_covariance.json',{'raw_model':'independent mean-zero unit-variance variables',
        'width':3,'score_axis_length':81,'before_roll_pair':[0,1],
        'before_roll_covariance':ratio(original),'after_roll_pair':[80,0],
        'after_roll_covariance':ratio(rolled),'cyclic_score_law_invariant':False,
        'robust_normalization_mask_or_full_bank_included':False,
        'inference':'Raw iid noise alone does not imply cyclic invariance of a finite filtered score axis.'})
    examples=[]
    for b in (3,99,127):
        for observed in (method.EMPTY,method.Maximum('finite',20)):
            examples.append(method.arithmetic_screen(observed,[method.EMPTY]*b))
    write('fixed_arithmetic_examples.json',examples)
    result={'schema':'radio-empty-null-exact-method-result-v1','status':'EXACT_METHOD_CHECKS_COMPLETE',
        'histograms':len(cases),'distinguished_position_ranks':rank_queries,
        'exact_rank_bound_inequalities':inequalities,'rank_bound_violations':0,
        'restricted_transform_rejection':ratio(rejection),'boxcar_covariance_counterexample':True,
        'new_native_or_noise_realizations':0,'calibration_attempts':0,'evaluation_attempts':0,
        'closed_score_archives_read':False,'settings_changed':False,'telescope_requests':0,
        'detector_ready_claimed':False,'runtime_seconds':time.monotonic()-start,
        'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'scope_sha256':hashlib.sha256((ROOT/'RADIO_EMPTY_NULL_METHOD_2026-09-28_SCOPE.md').read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'module_sha256':hashlib.sha256((ROOT/'src/seti_repeater/empty_null_radio.py').read_bytes()).hexdigest()}
    write('result.json',result)
    if result['peak_process_rss_bytes']>256*1024**2 or sum(p.stat().st_size for p in OUT.iterdir())>16*1024**2:
        raise RuntimeError('Exact method resource cap')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
