"""Audit posthoc CB catalogue descriptions and final report against sealed records.

No original power arrays are opened or rescored.
"""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import csv,hashlib,json

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    root=Path(__file__).resolve().parents[2];w=root/'work_cb';report=root/'RADIO_PROGRESS_CB_HIP35136_2026-11-01.md'
    d=json.loads((w/'POSTHOC_DESCRIPTION_CB.json').read_text())
    h=json.loads((w/'new_data_discovery/HIP35136_HEADER.json').read_text())
    result=json.loads((w/'results/RESULT_CB.json').read_text())
    review=json.loads((w/'review/NUMERICAL_REVIEW_CB.json').read_text())
    assert review['status']=='PASS_COMPLETE_NUMERICAL_REVIEW'
    for name,digest in d['bound_catalogues'].items():assert sha(w/'results'/name)==digest
    for path,digest in review['bound_input_output_hashes'].items():
        # Identity checks read byte streams only, not science power values.
        assert sha(root/path)==digest
    with (w/'results/SPECTRAL_FEATURES_CB.csv').open() as f:s=list(csv.DictReader(f))
    with (w/'results/TEMPORAL_FEATURES_CB.csv').open() as f:t=list(csv.DictReader(f))
    grid_ids={int(r['component']) for r in s if (int(r['peak_channel'])-512)%1024==0}
    hi_ids={int(r['component']) for r in s if 1419.5<=float(r['peak_frequency_MHz'])<=1421.5}
    other=[r for r in s if int(r['component']) not in grid_ids|hi_ids]
    assert len(s)==d['spectral_groups']==74
    assert len(grid_ids)==d['grid_aligned_peak_groups']==64
    assert len(hi_ids)==d['HI_window_groups']==2
    assert sorted(hi_ids)==d['HI_component_numbers']==[32,33]
    assert len(grid_ids&hi_ids)==d['HI_window_and_grid_overlap_groups']==1
    assert len(hi_ids-grid_ids)==d['HI_window_non_grid_groups']==1
    assert len(other)==d['other_spectral_groups']==9
    assert len(grid_ids)+len(hi_ids-grid_ids)+len(other)==len(s)
    assert [float(r['peak_frequency_MHz']) for r in other]==d['other_spectral_frequencies_MHz']
    assert all(int(r['channels'])==1 for r in other)
    assert d['grid_spacing_MHz']==1024*abs(h['foff'])==2.9296875
    peak=sorted(t,key=lambda r:-float(r['peak_score']))[0]
    event=d['largest_temporal_score_component'];start=int(peak['first_row']);end=int(peak['last_row'])
    assert int(peak['component'])==event['component']==278
    assert int(peak['pixels'])==event['pixels']==2321
    assert start==event['first_row']==267 and end==event['last_row']==272
    assert end-start+1==event['observed_integrations']==6
    assert event['observed_integration_duration_seconds']==(end-start+1)*h['tsamp']
    assert event['frequency_bounding_box_width_MHz']==(int(peak['last_channel'])-int(peak['first_channel'])+1)*abs(h['foff'])
    assert event['time_bounding_box_start_seconds']==start*h['tsamp']
    assert event['peak_frequency_MHz']==float(peak['peak_frequency_MHz'])
    assert event['touches_end_of_file'] is True and end==h['complete_time_rows']-1
    assert result['spectral_eligible_channels']==64768
    assert result['spectral_eligible_channels']*abs(h['foff'])==185.302734375
    assert result['samples']==17891328 and result['spectral_flagged_channels']==269
    assert result['temporal_components']==310 and result['temporal_flagged_pixels']==4964
    date=datetime(1858,11,17,tzinfo=timezone.utc)+timedelta(days=h['tstart'])
    assert date.strftime('%Y-%m-%dT%H:%M:%S')=='2016-06-24T19:24:22'
    notebook=json.loads((w/'new_data_discovery/Filterbank_Tutorial_original.ipynb').read_text())
    source_text='\n'.join(''.join(c.get('source',[])) for c in notebook['cells'])
    assert 'artifacts caused by' in source_text and 'band-pass filters' in source_text
    assert 'emission line of hydrogen' in source_text and 'HIP35136' in source_text
    text=report.read_text()
    checks={
      'target_epoch_and_sample_counts_match_sealed_records':True,
      'spectral_partition_is_disjoint_64_plus1_plus9':True,
      'HI_overlap_explicit_and_not_double_counted':True,
      'all_nine_other_groups_are_one_native_channel':True,
      'strongest_temporal_component_metrics_match_sealed_catalogue':True,
      'duration_described_as_observed_integrations_and_full_duration_unknown':'fulde varighed' in text and 'integrationstid' in text,
      'bandwidth_described_as_frequency_extent_not_occupied_bandwidth':'frekvensafgrænsning' in text,
      'posthoc_labels_separated_from_fixed_masks':'efter analysen' in text and 'ændrer ingen' in text,
      'coarse_resolution_and_missing_OFF_limits_explicit':'manglende OFF-scanning' in text and 'grove opløsning' in text,
      'no_qualified_SETI_candidate_claim':'ingen\nkvalificeret SETI-kandidat' in text,
      'source_attribution_not_claimed_for_HIP35136_emission':'ikke emission som kommende fra selve HIP35136' in text,
      'novelty_check_bounded_not_exhaustive':'en afgrænset gennemgang' in text,
      'no_change_to_BA_coverage':'ændrer ikke BA' in text,
      'prior_source_tutorial_supports_context_labels':True}
    assert all(checks.values()),checks
    paths=[report,w/'POSTHOC_DESCRIPTION_CB.json',w/'describe_and_plot_cb.py',w/'results/RESULT_CB.json',
           w/'results/SPECTRAL_FEATURES_CB.csv',w/'results/TEMPORAL_FEATURES_CB.csv',
           w/'review/NUMERICAL_REVIEW_CB.json',w/'review/BINDING_REVIEW_CB.json',
           w/'new_data_discovery/PROVENANCE_CB.md',w/'new_data_discovery/Filterbank_Tutorial_original.ipynb',
           w/'inventory/UNSEARCHED_DATA_INVENTORY_CB.json']
    out={'schema':'SETI_CB_REPORT_AND_POSTHOC_CLAIMS_REVIEW_V1','status':'PASS_CLAIMS_REVIEW',
      'required_corrections':[],'checks':checks,'original_masks_and_catalogues_remain_unchanged':True,
      'posthoc_counts':{'spectral':74,'grid':64,'HI_only':1,'other':9,'HI_grid_overlap':1},
      'event':event,'bound_files_sha256':{str(p.relative_to(root)):sha(p) for p in paths},
      'reviewer_sha256':sha(__file__),'original_power_values_rescored':0,
      'limits':['Catalogue arithmetic checked independently against sealed CSVs; scientific source labels remain source-supported interpretations.',
                'No independent physical source classification,blind detection significance,or true event end time is established.',
                'Figure appearance is not reviewed by this catalogue/report audit.']}
    (w/'review/CLAIMS_REVIEW_CB.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'status':out['status'],'required_corrections':out['required_corrections'],'checks':len(checks)}))

if __name__=='__main__':main()
