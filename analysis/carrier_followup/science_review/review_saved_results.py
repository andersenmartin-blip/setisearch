#!/usr/bin/env python3
"""Describe authenticated saved selector results; never reopen NPZ score maps."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'carrier_followup'
OUT=Path(__file__).resolve().parent
PINS={}
def read(path):
    raw=path.read_bytes()
    PINS[str(path.relative_to(ROOT))]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    return json.loads(raw)
def identity(r):
    return tuple(r[k] for k in ('phase','primary_target','native_chunk_index','core_q',
        'carrier_index_in_core','reference_source_channel','frequency_hz_at_own_first_midpoint',
        'reference_time_mjd','drift_hz_s','width_channels','score'))
def key(r):
    return (-r['score'],r['frequency_hz_at_own_first_midpoint'],r['drift_hz_s'],r['width_channels'],
        r['native_chunk_index'],r['core_q'],r['carrier_index_in_core'])
def record_summary(r):
    return {k:r[k] for k in ('primary_target','native_chunk_index','core_q','carrier_index_in_core',
        'reference_source_channel','frequency_hz_at_own_first_midpoint','drift_hz_s','width_channels','score')}

scope=read(BASE/'ranking/scope.json')
aggregate=read(BASE/'ranking/SELECTED_TOP9.json')
aggregate_receipt=read(BASE/'ranking/AGGREGATION_RECEIPT.json')
previous=read(ROOT/'next_dc/ranking/SELECTED_TOP9.json')
previous_science=read(ROOT/'next_dc/science_review/FINAL_REVIEW.json')
target_summaries=[]
recovered_best=[]
selected_overlap=[]
for target in scope['targets']:
    folder=BASE/'ranking'/target
    receipt=read(folder/'EXECUTION_RECEIPT.json')
    assert receipt['status']=='PASS_ONCE_CACHED_CARRIER_STREAMING_TARGET'
    for p in receipt['outputs']:
        data=(ROOT/p['path']).read_bytes()
        assert len(data)==p['bytes'] and hashlib.sha256(data).hexdigest()==p['sha256']
    result=read(folder/'RESULT.json')
    raw=result['raw_TOP100'];sep=result['frequency_separated_TOP100'];raw700=result['raw_TOP700']
    assert len(raw)==100 and len(sep)==100 and len(raw700)==700
    assert raw==raw700[:100]
    assert all(key(a)<=key(b) for a,b in zip(raw700,raw700[1:]))
    assert all(abs(a['reference_source_channel']-b['reference_source_channel'])>3
               for i,a in enumerate(sep) for b in sep[:i])
    assert sep[-1]['raw_rank']<=694
    assert all(r['eligible_DC_untouched'] for r in raw700)
    dirty=[r for r in result['core_summaries'] if r['original_coremax_DC_contact']]
    assert len(dirty)==5
    assert sum(r['eligible_DC_untouched_carriers'] for r in dirty)==18513
    best=None
    for core in dirty:
        candidate=core['eligible_maximum']
        if candidate is not None and (best is None or key(candidate)<key(best)):
            best=candidate
    assert best is not None
    entry=record_summary(best)
    entry['raw_TOP700_rank']=next((r['raw_rank'] for r in raw700 if identity(r)==identity(best)),None)
    entry['raw_TOP100_rank']=next((r['raw_rank'] for r in raw if identity(r)==identity(best)),None)
    entry['separated_TOP100_rank']=next((r['frequency_separated_rank'] for r in sep if identity(r)==identity(best)),None)
    recovered_best.append(entry)
    for r in result['TOP3']:
        old=next(x for x in previous['records'] if identity(x)==identity(r))
        assert old['exploratory_selection_rank']==r['exploratory_selection_rank']
        selected_overlap.append({'target':target,'new_rank':r['exploratory_selection_rank'],
            'previous_rank':old['exploratory_selection_rank'],'identical_original_tuple':True})
    target_summaries.append({'target':target,'counts':result['counts'],
        'raw_TOP100_noncoremax_entries':sum(not r['is_original_coremax_winner'] for r in raw),
        'separated_TOP100_noncoremax_entries':sum(not r['is_original_coremax_winner'] for r in sep),
        'raw100_and_separated100_common_reference_channels':len({r['reference_source_channel'] for r in raw}&{r['reference_source_channel'] for r in sep}),
        'raw_TOP100_score_range':[raw[-1]['score'],raw[0]['score']],
        'separated_TOP100_score_range':[sep[-1]['score'],sep[0]['score']],
        'actual_raw_rank_of100th_separated_entry':sep[-1]['raw_rank'],
        'old_DC_contact_coremax_domains':5,'eligible_carrier_winners_in_these_domains':18513,
        'producer_CPU_seconds':receipt['CPU_seconds'],'producer_wall_seconds':receipt['wall_seconds'],
        'producer_peak_RSS_KiB':receipt['maximum_RSS_KiB']})

assert len(selected_overlap)==9 and len(aggregate['records'])==9
assert {identity(r) for r in aggregate['records']}=={identity(r) for r in previous['records']}
counts=aggregate['counts']
assert counts['cached_carriers']==9375744 and counts['maps']==2289
assert counts['eligible_DC_untouched_carriers']==9369843
assert counts['DC_contacting_cached_winner_carriers']==5901
assert counts['eligible_DC_untouched_carriers']+counts['DC_contacting_cached_winner_carriers']==counts['cached_carriers']
strongest=next(r for r in recovered_best if r['score']==max(x['score'] for x in recovered_best))
assert strongest['score']==5.903766057920848
script_raw=Path(__file__).read_bytes()
PINS[str(Path(__file__).resolve().relative_to(ROOT))]={'bytes':len(script_raw),'sha256':hashlib.sha256(script_raw).hexdigest()}
review={
 'schema':'SETI_CACHED_CARRIER_SELECTION_FINAL_SCIENTIFIC_REVIEW_V1',
 'status':'PASS_SAVED_SELECTOR_RESULTS_AND_LIMITED_COMPLETENESS_INTERPRETATION',
 'input_pins':PINS,
 'counts':counts,
 'per_target_descriptive_lists':target_summaries,
 'raw_TOP100_alltargets_noncoremax_entries':sum(x['raw_TOP100_noncoremax_entries'] for x in target_summaries),
 'separated_TOP100_alltargets_noncoremax_entries':sum(x['separated_TOP100_noncoremax_entries'] for x in target_summaries),
 'recovered_from15_old_DC_coremax_domains':{'domain_count':15,'eligible_carrier_winners':55539,
     'meaning':'Previously saved carrier winners now explicitly retained in15cores whose overall maxima were rejected by the prior DC-aware coremax-only selection. These are not55539new physical signals or observations.',
     'strongest_per_target':recovered_best,'strongest_overall':strongest,
     'strongest_recovered_is_not_new_TOP3':True},
 'prior_selected_overlap':{'identical_tuples':9,'total_selected':9,'all_selection_ranks_unchanged':True,'records':selected_overlap},
 'established_completeness':[
    'Every one of9375744stored per-carrier winners in the declared2289unique mapdomains was examined under the frozen own-window16row DC eligibility rule.',
    'RawTOP700/rawTOP100 are exact ordered prefixes among the9369843eligible saved winners, conditional on the authenticated original maparrays and selector implementation.',
    'The greedily reference-separatedTOP100 and its first3perOFFtarget are exact under the frozen>3channel rule. The700prefix proof uses unique reference channels and at most7blockedchannels perprevious pick; observed100thraw ranks110/104/105are below694.',
    'The earlier nine coremax-selected tuples are also the exact finalnine under this broader cached-carrier-winner rule. No eligible stored carrier winner displaced one of thoseTOP3positions.'
 ],
 'not_established':[
    'Completeness over other width/drift hypotheses at a carrier whose stored winning hypothesis is DC-contacting; such clean nonwinning hypotheses remain unavailable in the maxima-only arrays.',
    'Completeness over omitted native171cores64/128/192, outer native170q0/native172q255, nonlinear tracks, other widths/drifts or unrecorded source observations.',
    'Physical-source uniqueness from>3reference-channel separation or from differing own-reference frequencies; distinct gridded paths can represent one underlying interference feature.',
    'Physical-path equality from equal reference frequency alone. Correct rawgeometry identity includes scan,width,all16absolute centers; normalized-score equivalence additionally requires the original normalizationcore and matching terms.',
    'Calibrated SNR/FAP, a qualified sky detection, qualified OFF veto, independent repeated visit, sensitivity or flux/EIRP constraints.'
 ],
 'context_followup_disposition':{
    'new_selected_original_templates':0,
    'unchanged_previous_measurement_templates':8,
    'previous_logical_profiles_available':54,
    'previous_distinct_physical_profiles_available':48,
    'new_raw_queries_needed_for_TOP9':0,
    'recommendation':'Reuse the existing hash-pinned, independently verified54logical/48physical context profiles for the unchangednine tuples; preserve their original scopes and numerical receipts. Recomputing their raw scores adds no independent confirmation.',
    'interpretation_unchanged':'The common2300MHz stationary template remains shared acrosspointings; sevenother templates remain unconfirmed exposed selections. The enlarged ranking domain does not convert them into independent detections.'},
 'QA_scope':'This review checks saved scalar counts, result/CSVoutput hashes, original tuple overlap and descriptive list consistency. It does not reopen cachedNPZarrays or independently reproduce all9million eligibility/heapoperations; the outcome numerical QA is a separate release check.',
 'review_activity':{'new_cached_map_or_raw_power_queries':0,'new_detector_scores':0,'new_winner_ranking':False,'saved_result_diagnostic_comparisons_only':True},
 'preserved_limits':{'original_AB':'FAIL_CLOSED_UNCHANGED','protected2016':'CLOSED','closed2019_transport':'UNCHANGED','new_telescope_HTTP':0,'new_observation_or_frequency_coverage':False,'cost_DKK':0},
 'remaining_scientific_corrections':[]
}
(OUT/'FINAL_REVIEW.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'status':review['status'],'eligible':9369843,'DC_contacting':5901,
    'TOP9_unchanged':True,'recovered_eligible_in15priorDCcores':55539,
    'strongest_recovered_score':strongest['score']},indent=2))
