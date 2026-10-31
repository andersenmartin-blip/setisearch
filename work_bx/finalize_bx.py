"""Close BX data-source evaluation without awarding SETI search credit."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1];BX=ROOT/'work_bx';TMP=Path('/dev/shm/seti_bx_ata_20261031')
def read(p):return json.loads(Path(p).read_text())
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
captures=[]
for phase in ['production','audit']:
    p=BX/'ata/execution'/phase;r=read(p/'RESULT.json')
    assert r['status']=='PASS' and r['actual_exit_code']==0 and r['child_wait_completed'] and r['natural_stdout_eof'] and not r['killed'] and not r['errors']
    assert r['pins_before']==r['pins_after']==r['pins_after_export']
    zpath=p/'EVIDENCE.zip';assert sha(zpath)==r['archive']['sha256']
    with zipfile.ZipFile(zpath) as z:
        assert z.testzip() is None
        for m in r['archive']['members']:
            raw=z.read(m['path']);assert len(raw)==m['bytes'] and hashlib.sha256(raw).hexdigest()==m['sha256']
    captures.append(dict(phase=phase,actual_exit_code=0,natural_stdout_eof=True,wall_seconds=r['wall_seconds'],capture_sha256=sha(p/'RESULT.json'),archive_path=str(zpath),archive_bytes=zpath.stat().st_size,archive_sha256=sha(zpath)))
s=read(TMP/'production/outputs/SUMMARY_ATA_BX.json');a=read(TMP/'audit/outputs/REVIEW_ATA_BX.json')
assert a['status']=='PASS_INDEPENDENT_ALL_CELL_QA' and a['summary_sha256']==sha(TMP/'production/outputs/SUMMARY_ATA_BX.json')
assert a['all_original_visibility_cells_checked']==sum(f['total_cells'] for f in s['files'])==51968
assert a['all_bound_bytes_unchanged'] and s['status']=='PASS_DESCRIPTIVE_QA'
files=[]
for i,f in enumerate(s['files']):
    h=f['header'];k=['input_identity','canonical_shape','frequency_min_hz','frequency_max_hz','channel_width_min_hz','unique_times','unique_ordered_baselines','polarization_codes','total_cells','valid_cells','flagged_cells','nonfinite_visibility_cells','nonfinite_sample_cells','nonpositive_finite_sample_cells','invalid_cells','time_start_utc','header_dates_match_maintainer_reported_date']
    row={key:f[key] for key in k};row.update(file=i,antennas=h['Nants_data'],integration_seconds=sorted(set(h['integration_time'])),all_temporal_coherence_undefined=a['files'][i]['all_temporal_coherence_undefined']);files.append(row)
result=dict(schema='SETI_BX_DATA_SOURCE_EVALUATION_RESULT_V1',status='ATA_QA_COMPLETE_INELIGIBLE_FOR_SETI_TOP8_PAYLOAD_UNAVAILABLE',
    parent_BW_index='libfile_be9824abb8cc8191bd02b787c6222203',public_freeze_commit=read(BX/'ata/PUBLIC_FREEZE_ATA_BX.json')['public_commit'],
    plan_sha256=sha(BX/'ata/PLAN_ATA_BX.json'),ATA=dict(original_source_repository='RadioAstronomySoftwareGroup/rasg-datasets',original_source_commit='55bd68b28fabe0936011bd9540cbaef9e20809db',new_files_acquired=2,source_bytes=559008,one_observation_two_subbands=True,source='3c286',total_complex_visibility_cells=51968,valid_cells=0,files=files,subband_comparison=s['subband_comparison'],weights=read(BX/'ata/POSTHOC_WEIGHT_DETAIL_BX.json'),interpretation='All exported nsamples are negative. These downselected normalized test files are unsuitable for the preregistered validity mask. This is not a claim that the original telescope observation failed. Only one integration and 500kHz channels; no narrowband drift/cadence search is possible.',quality_analysis_completed=True,scientifically_eligible_for_SETI=False,metadata_date_conflict='Header and filename indicate2024-12-03; maintainer README says2024-12-12. Retained unresolved.',runtime=s['runtime']),
    independent_review=dict(status=a['status'],source_sha256=a['reviewer_sha256'],review_sha256=sha(TMP/'audit/outputs/REVIEW_ATA_BX.json'),all_cells_checked=a['all_original_visibility_cells_checked'],all_groups_checked=a['all_baseline_polarization_groups_checked'],maximum_profile_absolute_error=a['maximum_profile_absolute_error'],shared_decoder_limitation=a['limits'][0]),
    captures=captures,TOP8=read(BX/'acquisition/TOP8_STATUS_BX.json'),
    literature_context=dict(primary_paper='https://arxiv.org/html/2308.02712v4',published_RFI_classifications=['MLc3','MLc4','MLc5','MLc7','MLc8'],not_examined_in_that_followup=['MLc1','MLc2','MLc6'],our_independent_raw_data_confirmation=False),
    original_SETI_authority=dict(unique_archive_ids=486,technical_MHz_visits=268.50128173828125,qualified_astronomical_sensitivity_MHz_visits=0,BU_BV_BW_cached_carrier_q='1..254',BU_BV_BW_partial_carrier_width_MHz=2.90679931640625,full_cadence_status='NOT_EVALUABLE_MISSING_OFF5'),
    new_SETI_searches=0,new_original_unique_archive_ids=0,new_original_technical_MHz_visits=0,queue_advanced=False,background_jobs_running=False,
    next_action='Resume original missing OFF5 only with normal permitted archive access and full BB/BC/BE proof gates, or acquire a genuinely eligible independent ON/OFF dataset. Do not repeat closed cached searches or count calibration/test files as survey coverage. If access remains unchanged, a separately frozen injection/recovery efficiency study on retained data is the next useful local methodology task; simulated controls must be labelled explicitly.')
assert all(x['maximum'] < 0 for x in result['ATA']['weights']['files']) and all(f['valid_cells']==0 for f in files)
with (BX/'SUMMARY_BX.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
print(json.dumps(dict(status=result['status'],summary_sha256=sha(BX/'SUMMARY_BX.json'),new_ATA_files=2,all_cells=51968,valid_cells=0,new_SETI_searches=0)))
