#!/usr/bin/env python3
"""One bounded read of accepted JSON summaries; no scientific arrays/helpers."""
import hashlib,json,math,resource,time
from collections import Counter
from pathlib import Path

START=0.0
BASE=Path('/workspace/scratch/a8d1e29996d0/setisearch_fullpower')
FAMILY='radio_s2017_cross_on_profile_recovery_20261010'
STAGE=BASE/'results'/FAMILY
HERE=Path(__file__).parent
SCANS=('epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off')
ONS=SCANS[::2];OFFS=SCANS[1::2]
ADJ={'epoch1_on':['epoch1_off'],'epoch2_on':['epoch1_off','epoch2_off'],'epoch3_on':['epoch2_off','epoch3_off']}
resource.setrlimit(resource.RLIMIT_CPU,(10,12))
resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912))
PINS={}

def read(path):
    raw=path.read_bytes()
    PINS[str(path)]={'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    return json.loads(raw)

def admitted(path,manifest):
    value=read(path)
    assert manifest[str(path)]==PINS[str(path)]
    return value

def write(path,value):
    with path.open('x') as handle:
        json.dump(value,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')

failure=read(HERE/'DESCRIPTIVE_READING_FAILURE_RECEIPT.json')
assert failure['status']=='FAILED_SAVED_JSON_READER_SERIALIZATION_RESOURCE_FIELD_LOOKUP'
rules=read(HERE/'DESCRIPTIVE_READING_RULES.json')
assert rules['status']=='FIXED_BEFORE_NEW_PROFILE_METRICS_READ'
write(HERE/'DESCRIPTIVE_READ_V2_STARTED_ONCE.json',{'status':'STARTED_SAVED_JSON_ONLY','rules_pin':PINS[str(HERE/'DESCRIPTIVE_READING_RULES.json')]})
qa=read(STAGE/'review/QA_RECEIPT.json')
assert qa['family_id']==FAMILY and qa['status']=='PASS_635_TRIPLES_11430_FIXED_PROFILE_OUTPUTS_AND23465616_RAW_CELL_OCCURRENCE_DIGESTS'
assert qa['all_input_end_readbacks_exact'] is True and qa['selected_raw_row_SHA256_digests_independently_matched'] is True
manifest={p['path']:p for p in qa['all_input_byte_pins']}
assert len(manifest)==len(qa['all_input_byte_pins'])
execution=admitted(STAGE/'measurement/EXECUTION_RECEIPT.json',manifest)
outer=admitted(STAGE/'ROOT_OUTER_EXECUTION_RECEIPT.json',manifest)
index=admitted(STAGE/'measurement/FIXED_ALL_SIX_PROFILES.json',manifest)
assert execution['status']=='COMPLETE_635_S2017_MATCHED_TRIPLES_ALL_SIX_FIXED_PROFILES_EXPLORATORY_ONLY'
assert outer['status']=='PASS_ONE_CHILD_CLOSED_COMPLETE_AND_OUTER_RESOURCE_CAPS' and outer['child_exit_code']==0
assert qa['execution_receipt_sha256']==PINS[str(STAGE/'measurement/EXECUTION_RECEIPT.json')]['sha256']
assert qa['outer_execution_receipt_sha256']==PINS[str(STAGE/'ROOT_OUTER_EXECUTION_RECEIPT.json')]['sha256']
assert index['selected_triples']==635 and index['selected_members']==1905 and index['logical_scan_profiles']==11430
all_records=[]
for entry in index['origin_record_files']:
    p=Path(entry['file_pin']['path']);value=admitted(p,manifest)
    assert entry['file_pin']==PINS[str(p)] and value['family_id']==FAMILY
    assert value['originating_ON'] in ONS and len(value['records'])==635
    all_records.extend(value['records'])
assert len(all_records)==1905 and len({r['logical_member_index'] for r in all_records})==1905
by_origin={o:Counter() for o in ONS}
by_scan={s:Counter({k:0 for k in ['logical_profiles','mean_positive','mean_zero','mean_negative','both_half_means_positive','all16_rows_positive']}) for s in SCANS}
by_triple={}
rank2=[]
for r in all_records:
    origin=r['member_scan_id'];profiles=r['scan_profiles']
    assert origin in ONS and [p['scan_id'] for p in profiles]==list(SCANS)
    means={p['scan_id']:p['metrics']['mean'] for p in profiles}
    for p in profiles:
        m=p['metrics'];assert set(m)=={'mean','median','positive_rows','first_eight_mean','last_eight_mean','minimum_half_mean'}
        assert all(math.isfinite(v) for v in m.values()) and type(m['positive_rows']) is int and 0<=m['positive_rows']<=16
        c=by_scan[p['scan_id']];c['logical_profiles']+=1
        c['mean_positive' if m['mean']>0 else 'mean_zero' if m['mean']==0 else 'mean_negative']+=1
        c['both_half_means_positive']+=m['minimum_half_mean']>0
        c['all16_rows_positive']+=m['positive_rows']==16
    om=means[origin]
    flags={'originON_mean_positive':om>0,'all_three_ON_means_positive':all(means[s]>0 for s in ONS),
        'any_OFF_mean_positive':any(means[s]>0 for s in OFFS),'all_three_OFF_means_positive':all(means[s]>0 for s in OFFS),
        'any_OFF_mean_at_least_originON':any(means[s]>=om for s in OFFS),
        'all_three_OFF_means_at_least_originON':all(means[s]>=om for s in OFFS),
        'any_adjacent_OFF_mean_at_least_originON':any(means[s]>=om for s in ADJ[origin]),
        'all_adjacent_OFF_means_at_least_originON':all(means[s]>=om for s in ADJ[origin]),
        'originON_both_half_means_positive':next(p for p in profiles if p['scan_id']==origin)['metrics']['minimum_half_mean']>0}
    by_origin[origin]['logical_members']+=1
    for k,v in flags.items():by_origin[origin][k]+=v
    if r['match_id'] not in by_triple:by_triple[r['match_id']]={}
    assert origin not in by_triple[r['match_id']]
    by_triple[r['match_id']][origin]=flags
    if r['original_display_rank']==2:
        rank2.append({'match_id':r['match_id'],'original_display_rank':2,'member_scan_id':origin,
            'original_key':r['original_member']['original_key'],
            'original_reference_frequency_hz':r['original_member']['original_reference_frequency_hz'],
            'core_q':r['original_member']['core_q'],
            'scan_profiles':profiles})
assert len(by_triple)==635 and all(set(v)==set(ONS) for v in by_triple.values()) and len(rank2)==3
hist={key:Counter({i:0 for i in range(4)}) for key in ['positive_originON_members','members_with_any_OFF_at_least_own_ON','members_with_all_OFF_means_positive']}
for t in by_triple.values():
    hist['positive_originON_members'][sum(v['originON_mean_positive'] for v in t.values())]+=1
    hist['members_with_any_OFF_at_least_own_ON'][sum(v['any_OFF_mean_at_least_originON'] for v in t.values())]+=1
    hist['members_with_all_OFF_means_positive'][sum(v['all_three_OFF_means_positive'] for v in t.values())]+=1
total=Counter()
for c in by_origin.values():total.update(c)
for p in PINS.values():
    raw=Path(p['path']).read_bytes();assert len(raw)==p['bytes'] and hashlib.sha256(raw).hexdigest()==p['sha256']
result={'schema':'S2017_PROFILE_SAVED_JSON_DESCRIPTIVE_INTERPRETATION_V1','status':'COMPLETE_SAVED_JSON_ONLY_DESCRIPTIVE_READING',
    'family_id':FAMILY,'profile_freeze_commit':execution['public_freeze_commit'],'QA_freeze_commit':qa['public_QA_freeze_commit'],
    'rules_pin':PINS[str(HERE/'DESCRIPTIVE_READING_RULES.json')],'source_pins':list(PINS.values()),
    'counts':{'selected_triples':635,'logical_members':1905,'logical_scan_profiles':11430,'logical_rows':182880,
        'unique_geometries':11369,'new_geometry_aliases':61,'independent_new_hypothesis_combinations':0},
    'by_origin':by_origin,'by_target_scan':by_scan,'all_logical_member_counts':total,'triple_histograms':hist,
    'original_display_rank2_all_three_members':rank2,
    'actual_resources':{'worker_outer_CPU_seconds':outer['child_process_CPU_seconds'],'worker_outer_RSS_bytes':outer['child_peak_RSS_bytes'],
        'independent_QA_CPU_seconds':qa['process_CPU_seconds_including_imports'],'independent_QA_RSS_bytes':qa['peak_RSS_bytes']},
    'array_or_source_files_opened':False,'profile_or_detector_or_median_reexecuted':False,
    'new_ranking_threshold_veto_or_classification':False,'limitations':rules['limitations']+qa['limits'],
    'reader_CPU_seconds_before_serialization':time.process_time()-START}
write(HERE/'SAVED_PROFILE_DESCRIPTIVE_ANALYSIS.json',result)
cpu=time.process_time()-START
receipt={'status':'PASS_CORRECTED_SAVED_JSON_V2_READING_AND_SERIALIZATION','script_pin':{'path':str(Path(__file__)),
    'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'bytes':Path(__file__).stat().st_size},
    'analysis_pin':{'path':str(HERE/'SAVED_PROFILE_DESCRIPTIVE_ANALYSIS.json'),
    'sha256':hashlib.sha256((HERE/'SAVED_PROFILE_DESCRIPTIVE_ANALYSIS.json').read_bytes()).hexdigest(),
    'bytes':(HERE/'SAVED_PROFILE_DESCRIPTIVE_ANALYSIS.json').stat().st_size},'process_CPU_seconds':cpu,
    'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'numpy_HDF5_NPZ_or_scientific_helpers_used':False}
assert cpu<10
write(HERE/'DESCRIPTIVE_READING_V2_RECEIPT.json',receipt)
print(json.dumps({'all_logical_member_counts':total,'by_origin':by_origin,'by_target_scan':by_scan,'triple_histograms':hist,
    'rank2_fixed_means':[{r['member_scan_id']:{p['scan_id']:p['metrics']['mean'] for p in r['scan_profiles']}} for r in rank2],
    'receipt':receipt},sort_keys=True))
